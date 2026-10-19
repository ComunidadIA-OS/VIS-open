"""Generador de datos SINTÉTICOS para montar el panel y probar métricas.

Todo es inventado y reproducible (semilla fija): ninguna persona, voz ni transcripción real.
Cada fichero lleva SINTETICO en el nombre; cada tabla, `origen=SINTETICO`; cada línea de tiempo,
`video_id` y `source` que empiezan por SINTETICO. Incluye casos de género `desconocido`, tiempo
sin atribuir y muestra insuficiente.

Uso: python -m evaluation.synthetic [--out DIR] [--seed N]
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path

from contracts import (
    AnalysisEvent,
    AnalysisTimeline,
    EventType,
    GenderSource,
    GenderValue,
    Provenance,
    ReviewRow,
    Speaker,
    write_rows,
)
from pipeline.timeline import build_review_rows

DEFAULT_SEED = 42
ORIGIN = "SINTETICO"
W, M, U = GenderValue.WOMAN, GenderValue.MAN, GenderValue.UNKNOWN

SPEECH_LINES = [
    "Hoy quiero hablar de los presupuestos de la comunidad.",
    "Creo que esta propuesta necesita más tiempo de debate.",
    "Vamos a votar la enmienda tal y como está redactada.",
    "Agradezco las aportaciones del resto de los grupos.",
    "Pido que se revise el calendario de la tramitación.",
]
SELF_CUE = {
    W: "Estoy muy agradecida por poder intervenir.",
    M: "Estoy muy agradecido por poder intervenir.",
}
FLOOR_GRANT = {
    W: "Tiene la palabra la señora diputada.",
    M: "Tiene la palabra el señor diputado.",
    U: "Tiene la palabra su señoría.",
}


@dataclass(frozen=True)
class Scenario:
    name: str
    voices: tuple[tuple[GenderValue, float], ...]  # (género declarado, peso del tiempo de palabra)
    chair: GenderValue = M
    n_turns: int = 30
    unattributed_p: float = 0.0  # fracción de intervenciones sin voz atribuida
    hand_raises: int = 0


SCENARIOS = {
    s.name: s
    for s in [
        Scenario("equilibrado", ((W, 1), (M, 1), (W, 1), (M, 1))),
        Scenario("pocas_mujeres", ((W, 1), (M, 4), (M, 4), (M, 4), (M, 4))),
        Scenario(
            "con_desconocidos",
            ((W, 2), (M, 3), (U, 1), (U, 1)),
            unattributed_p=0.15,
        ),  # fmt: skip
        Scenario("muestra_insuficiente", ((W, 1), (U, 1)), chair=U, n_turns=3),
        Scenario("con_manos", ((W, 1), (M, 1), (W, 1), (M, 1)), hand_raises=12),
    ]
}


def generate_timeline(scenario: Scenario, seed: int = DEFAULT_SEED) -> AnalysisTimeline:
    rng = random.Random(f"{seed}:{scenario.name}")
    voices = [(f"SPEAKER_{i:02d}", g, w) for i, (g, w) in enumerate(scenario.voices, start=1)]
    gender_of = {"SPEAKER_00": scenario.chair, **{sid: g for sid, g, _ in voices}}
    events: list[AnalysisEvent] = []
    t = 0.0

    def add(kind, start, end, speaker, text=None, conf=None, source="faster-whisper", **extra):
        events.append(
            AnalysisEvent(
                event_id=f"ev_{len(events):05d}",
                type=kind,
                start_s=round(start, 2),
                end_s=round(end, 2),
                speaker_id=speaker,
                text=text,
                confidence=conf,
                provenance=Provenance.AI_INFERRED,
                source=f"{ORIGIN}:{source}",
                **extra,
            )  # fmt: skip
        )

    for _ in range(scenario.n_turns):
        sid, gender, _ = rng.choices(voices, weights=[v[2] for v in voices])[0]
        d = rng.uniform(3, 5)
        add(EventType.SPEECH, t, t + d, "SPEAKER_00", FLOOR_GRANT[gender], 0.92)
        t += d + rng.uniform(0.2, 0.8)
        text = rng.choice(SPEECH_LINES)
        if gender != U and rng.random() < 0.25:
            text = SELF_CUE[gender] + " " + text
        d = rng.uniform(8, 40)
        attributed = rng.random() >= scenario.unattributed_p
        add(EventType.SPEECH, t, t + d, sid if attributed else None, text, rng.uniform(0.55, 0.98))
        t += d + rng.uniform(0.5, 2.0)

    duration = round(t + 1.0, 2)
    for _ in range(scenario.hand_raises):
        start = rng.uniform(0, duration - 3)
        add(
            EventType.HAND_RAISE, start, start + 1.5, None, conf=rng.uniform(0.5, 0.95),
            source="mediapipe-pose", zone_id=f"Z{rng.randint(1, 4)}", granted=rng.random() < 0.6,
        )  # fmt: skip
    events.sort(key=lambda e: (e.start_s, e.end_s))
    events = [e.model_copy(update={"event_id": f"ev_{i:05d}"}) for i, e in enumerate(events)]

    totals: dict[str, float] = {}
    for e in events:
        if e.speaker_id:
            totals[e.speaker_id] = totals.get(e.speaker_id, 0.0) + (e.end_s - e.start_s)
    speakers = [
        Speaker(
            speaker_id=sid,
            total_speech_s=round(secs, 3),
            gender=gender_of[sid],
            gender_source=GenderSource.UNKNOWN if gender_of[sid] == U else GenderSource.DECLARED,
            role="presidencia (SINTETICO)" if sid == "SPEAKER_00" else None,
        )
        for sid, secs in sorted(totals.items())
    ]
    return AnalysisTimeline(
        video_id=f"{ORIGIN}_{scenario.name}", duration_s=duration, speakers=speakers, events=events
    )


EVENT_COLUMNS = [
    "origen", "video_id", "event_id", "type", "start_s", "end_s", "duration_s", "speaker_id",
    "gender", "gender_source", "provenance", "confidence", "zone_id", "granted", "text",
]  # fmt: skip
SUMMARY_COLUMNS = [
    "origen", "video_id", "n_speech_events", "n_voices", "n_voices_known_gender",
    "seconds_mujer", "seconds_hombre", "seconds_desconocido", "seconds_sin_atribuir",
    "share_mujer_sobre_conocido", "unattributed_share", "conclusivo_ejemplo",
]  # fmt: skip
TURN_COLUMNS = ["origen", "turn_id", "context_before", "text", "label"]
# Regla de EJEMPLO solo para que el panel muestre un caso «no concluyente»; no es de Ivette.
EXAMPLE_MIN_KNOWN_VOICES = 2
EXAMPLE_MIN_KNOWN_SECONDS = 60


def event_rows(tl: AnalysisTimeline) -> list[dict]:
    speakers = {s.speaker_id: s for s in tl.speakers}
    rows = []
    for e in tl.events:
        sp = speakers.get(e.speaker_id) if e.speaker_id else None
        rows.append(
            {
                "origen": ORIGIN, "video_id": tl.video_id, "event_id": e.event_id,
                "type": e.type.value, "start_s": e.start_s, "end_s": e.end_s,
                "duration_s": round(e.end_s - e.start_s, 2), "speaker_id": e.speaker_id or "",
                "gender": sp.gender.value if sp else "sin_atribuir",
                "gender_source": sp.gender_source.value if sp else "",
                "provenance": e.provenance.value, "confidence": round(e.confidence or 0, 3),
                "zone_id": e.zone_id or "",
                "granted": "" if e.granted is None else str(e.granted).lower(),
                "text": e.text or "",
            }
        )  # fmt: skip
    return rows


def summary_row(tl: AnalysisTimeline) -> dict:
    rows = [r for r in event_rows(tl) if r["type"] == EventType.SPEECH.value]
    secs = {g: 0.0 for g in ("mujer", "hombre", "desconocido", "sin_atribuir")}
    for r in rows:
        secs[r["gender"]] += r["duration_s"]
    total = sum(secs.values())
    known = secs["mujer"] + secs["hombre"]
    voices = {r["speaker_id"]: r["gender"] for r in rows if r["speaker_id"]}
    known_voices = sum(g in ("mujer", "hombre") for g in voices.values())
    return {
        "origen": ORIGIN, "video_id": tl.video_id, "n_speech_events": len(rows),
        "n_voices": len(voices), "n_voices_known_gender": known_voices,
        **{f"seconds_{g}": round(v, 2) for g, v in secs.items()},
        "share_mujer_sobre_conocido": round(100 * secs["mujer"] / known, 2) if known else "",
        "unattributed_share": round((total - known) / total, 4) if total else "",
        "conclusivo_ejemplo": (
            "si"
            if known_voices >= EXAMPLE_MIN_KNOWN_VOICES and known >= EXAMPLE_MIN_KNOWN_SECONDS
            else "no"
        ),
    }  # fmt: skip


def turn_rows(tl: AnalysisTimeline) -> list[dict]:
    """Turnos con su contexto (la Presidencia dando la palabra) y la etiqueta simulada."""
    speakers = {s.speaker_id: s.gender.value for s in tl.speakers}
    rows, prev = [], None
    for e in tl.events:
        if e.type != EventType.SPEECH:
            continue
        if e.speaker_id == "SPEAKER_00":
            prev = e
        elif prev is not None and e.speaker_id:
            rows.append(
                {
                    "origen": ORIGIN, "turn_id": f"{tl.video_id}_{e.event_id}",
                    "context_before": prev.text, "text": e.text, "label": speakers[e.speaker_id],
                }
            )  # fmt: skip
            prev = None
    return rows


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_dataset(out_dir: Path, seed: int = DEFAULT_SEED) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timelines = [generate_timeline(s, seed) for s in SCENARIOS.values()]
    paths = []
    for tl in timelines:
        p = out_dir / f"{tl.video_id}.timeline.json"
        p.write_text(tl.model_dump_json(indent=2), encoding="utf-8")
        paths.append(p)
    paths.append(
        _write_csv(
            out_dir / f"{ORIGIN}_eventos.csv",
            EVENT_COLUMNS,
            [r for tl in timelines for r in event_rows(tl)],
        )  # fmt: skip
    )
    paths.append(
        _write_csv(
            out_dir / f"{ORIGIN}_resumen_genero.csv",
            SUMMARY_COLUMNS,
            [summary_row(tl) for tl in timelines],
        )  # fmt: skip
    )
    paths.append(
        _write_csv(
            out_dir / f"{ORIGIN}_turnos.csv",
            TURN_COLUMNS,
            [r for tl in timelines for r in turn_rows(tl)],
        )  # fmt: skip
    )
    review = out_dir / f"{ORIGIN}_revision.csv"
    write_rows(
        [r for tl in timelines for r in build_review_rows(tl, "anotadora_1")], ReviewRow, review
    )
    paths.append(review)
    return paths
