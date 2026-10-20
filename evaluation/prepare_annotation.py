"""Prepara la hoja de turnos que Ivette y Veru anotan a mano (género por pistas del lenguaje).

Lee los `timeline.json` ya seudonimizados de `data/processed/*/`, junta los segmentos seguidos de
una misma voz en turnos y saca una muestra equilibrada, mezclada y sin etiquetar. Escribe dos
ficheros en la carpeta de salida (fuera del repo, `data/` está ignorado):

  turnos_para_anotar.csv   turn_id,context_before,text,label   → es lo único que ve quien anota
  clave_interna.csv        turn_id,video_id,event_id,genero_sistema → no se enseña a quien anota

La hoja no lleva el género que asignó el sistema, para no sesgar. El género del sistema solo
sirve para repartir la muestra (por defecto 60 mujer, 60 hombre, 30 desconocido = 150, con los
30 ambiguos que pide la evaluación); la etiqueta final la pone la persona al leer el texto.
Uso: python -m evaluation.prepare_annotation [--data data] [--out data/anotacion] [--seed 7]
"""

from __future__ import annotations

import argparse
import csv
import random
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from contracts import AnalysisTimeline, EventType

GAP_S = 2.0  # pausa máxima entre segmentos de una misma voz dentro de un turno
MIN_WORDS = 6
MAX_WORDS = 60  # un turno largo se parte en trozos legibles para anotar
CONTEXT_CHARS = 300
QUOTA = {"mujer": 60, "hombre": 60, "desconocido": 30}


@dataclass
class Turn:
    video_id: str
    event_id: str
    speaker_id: str
    text: str
    context_before: str
    gender: str


def build_turns(timeline: AnalysisTimeline) -> list[Turn]:
    gender = {s.speaker_id: s.gender.value for s in timeline.speakers}
    speech = sorted(
        (e for e in timeline.events if e.type == EventType.SPEECH and e.speaker_id and e.text),
        key=lambda e: e.start_s,
    )
    turns: list[Turn] = []
    last_end = 0.0
    for e in speech:
        prev = turns[-1] if turns else None
        if (
            prev
            and prev.speaker_id == e.speaker_id
            and e.start_s - last_end <= GAP_S
            and len(prev.text.split()) < MAX_WORDS
        ):
            prev.text += " " + e.text.strip()
        else:
            context = (prev.text if prev else "")[-CONTEXT_CHARS:]
            turns.append(
                Turn(
                    timeline.video_id,
                    e.event_id,
                    e.speaker_id,
                    e.text.strip(),
                    context,
                    gender.get(e.speaker_id, "desconocido"),
                )
            )
        last_end = e.end_s
    return turns


def sample_turns(turns: Sequence[Turn], seed: int, quota: dict[str, int] = QUOTA) -> list[Turn]:
    rng = random.Random(seed)
    chosen: list[Turn] = []
    for gender, n in quota.items():
        pool = [t for t in turns if t.gender == gender and len(t.text.split()) >= MIN_WORDS]
        rng.shuffle(pool)
        chosen += pool[:n]
    # Si una clase no llega a su cupo, se completa con turnos sobrantes hasta el total pedido.
    taken = {id(t) for t in chosen}
    rest = [t for t in turns if id(t) not in taken and len(t.text.split()) >= MIN_WORDS]
    rng.shuffle(rest)
    chosen += rest[: max(0, sum(quota.values()) - len(chosen))]
    rng.shuffle(chosen)
    return chosen


def write_sheets(turns: Sequence[Turn], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "turnos_para_anotar.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["turn_id", "context_before", "text", "label"])
        for i, t in enumerate(turns, 1):
            w.writerow([f"T{i:03d}", t.context_before, t.text, ""])
    with (out / "clave_interna.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["turn_id", "video_id", "event_id", "genero_sistema"])
        for i, t in enumerate(turns, 1):
            w.writerow([f"T{i:03d}", t.video_id, t.event_id, t.gender])


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", type=Path, default=Path("data"))
    ap.add_argument("--out", type=Path, default=Path("data/anotacion"))
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args(argv)
    turns: list[Turn] = []
    for path in sorted((args.data / "processed").glob("*/timeline.json")):
        turns += build_turns(AnalysisTimeline.model_validate_json(path.read_text("utf-8")))
    chosen = sample_turns(turns, args.seed)
    write_sheets(chosen, args.out)
    counts = {g: sum(t.gender == g for t in chosen) for g in QUOTA}
    print(f"{len(chosen)} turnos de {len(turns)} -> {args.out} (reparto del sistema: {counts})")
    if len(chosen) < sum(QUOTA.values()):
        print("Aviso: no hay turnos suficientes en alguna clase; la muestra es más pequeña.")


if __name__ == "__main__":
    main()
