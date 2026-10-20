"""Informe de análisis: audio, vídeo y consumo del modelo de lenguaje (tokens y precio).

Lee `data/processed/*/` (resumen.json, timeline.json, video.json) y el detalle del benchmark
(`data/detalle/detalle_llm.csv`). Solo agrega cifras: no copia texto ni nombres. Los precios salen
de `LLM_PRICE_*` (nunca del código); sin precios, el informe da solo tokens.
Uso: python -m evaluation.informe [--data data] [--out data/informe_analisis.md]
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path
from statistics import mean

from contracts import AnalysisTimeline
from evaluation.cost import Prices, cost
from pipeline.envfile import load_dotenv


def _json(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def audio_section(processed: Path) -> list[str]:
    lines = [
        "## Análisis de audio",
        "",
        "| Sesión | Duración (min) | Voces | Voces con género | Habla (min) | Mujer % | Hombre % |"
        " Desconocido % | Sin atribuir % | Confianza media ASR | Voces a revisión |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for folder in sorted(p for p in processed.glob("*") if (p / "timeline.json").is_file()):
        tl = AnalysisTimeline.model_validate_json((folder / "timeline.json").read_text("utf-8"))
        r = _json(folder / "resumen.json") or {}
        share = {g["gender"]: g["share"] for g in r.get("tiempo_por_genero", [])}
        m = r.get("muestra", {})
        conf = [e.confidence for e in tl.events if e.type == "speech" and e.confidence is not None]
        lines.append(
            f"| {folder.name} | {tl.duration_s / 60:.1f} | {m.get('n_voces', '-')} "
            f"| {m.get('n_voces_genero_conocido', '-')} | {m.get('segundos_habla', 0) / 60:.1f} "
            + "".join(f"| {100 * share.get(g, 0):.1f} " for g in ("mujer", "hombre", "desconocido"))
            + f"| {100 * share.get('sin_atribuir', 0):.1f} | {mean(conf):.3f} "
            f"| {r.get('voces_a_revision', '-')} |"
            if conf
            else f"| {folder.name} | {tl.duration_s / 60:.1f} | sin habla |"
        )
    lines += [
        "",
        "Una sesión con una sola voz fusionada (V001–V003) no permite medir género: sale todo "
        "«desconocido». Tiempo de cómputo medido en OVH (2×V100S): una sesión de 1 h 19 min se "
        "analiza en 7 min 22 s (`docs/PRUEBA_GPU.md`).",
    ]
    return lines


def video_section(processed: Path) -> list[str]:
    lines = [
        "## Análisis de vídeo (sin caras)",
        "",
        "| Sesión | Fotogramas | Personas visibles (máx / mediana) | Sin personas % |"
        " Pantalla mujer % | hombre % | desconocido % | Manos levantadas |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for folder in sorted(p for p in processed.glob("*") if (p / "video.json").is_file()):
        v = _json(folder / "video.json") or {}
        pct = v.get("tiempo_en_pantalla_por_genero_%", {})
        hands = sum(v.get("manos_levantadas_por_zona", {}).values())
        lines.append(
            f"| {folder.name} | {v.get('n_fotogramas')} | {v.get('personas_visibles_max')} / "
            f"{v.get('personas_visibles_mediana')} | {v.get('fotogramas_sin_personas_%')} "
            f"| {pct.get('mujer', 0)} | {pct.get('hombre', 0)} | {pct.get('desconocido', 0)} "
            f"| {hands} |"
        )
    lines += [
        "",
        "Es lo que ve la cámara, no quién hay en la sala. El modelo de pose es de una sola "
        "persona: en planos amplios cuenta de menos. Sin anotación manual no se ha medido su "
        "error.",
    ]
    return lines


def cost_section(detail: Path, prices: Prices | None) -> list[str]:
    lines = ["## Consumo del modelo de lenguaje (tokens y precio)", ""]
    if not detail.is_file():
        return [*lines, "No hay `data/detalle/detalle_llm.csv`: aún no se ha medido."]
    with detail.open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("tokens_in")]
    if not rows:
        return [*lines, "El detalle no trae tokens (la API no devolvió `usage`)."]
    t_in = [int(r["tokens_in"]) for r in rows]
    t_out = [int(r["tokens_out"]) for r in rows]
    lat = [float(r["latencia_s"]) for r in rows if r.get("latencia_s")]
    lines += [
        f"Medido en {len(rows)} llamadas del benchmark sintético (no en sesiones reales).",
        "",
        "| Medida | Valor |",
        "|---|---|",
        f"| Tokens de entrada (total / por llamada) | {sum(t_in)} / {mean(t_in):.0f} |",
        f"| Tokens de salida (total / por llamada) | {sum(t_out)} / {mean(t_out):.0f} |",
        f"| Latencia media por llamada | {mean(lat):.2f} s |" if lat else "| Latencia | n/d |",
    ]
    if prices is None:
        lines.append("| Precio | faltan `LLM_PRICE_*`: solo se informan los tokens |")
        return lines
    per_call = cost(mean(t_in), mean(t_out), prices)
    lines += [
        f"| Precios usados ({prices.currency}/M tokens, tarifario {prices.date or 's/f'}) "
        f"| {prices.in_per_mtok} entrada / {prices.out_per_mtok} salida |",
        f"| Coste de las {len(rows)} llamadas | {cost(sum(t_in), sum(t_out), prices):.6f} "
        f"{prices.currency} |",
        f"| Coste por llamada | {per_call:.6f} {prices.currency} |",
        f"| Estimación: 1 000 turnos | {per_call * 1000:.4f} {prices.currency} |",
    ]
    return lines


def build_report(data: Path, prices: Prices | None) -> str:
    processed = data / "processed"
    parts = [
        ["# Informe de análisis de VIS Open", "", "Cifras calculadas por código. Sin nombres."],
        audio_section(processed),
        video_section(processed),
        cost_section(data / "detalle" / "detalle_llm.csv", prices),
    ]
    return "\n".join("\n".join(p) + "\n" for p in parts)


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", type=Path, default=Path("data"))
    ap.add_argument("--out", type=Path, default=Path("data/informe_analisis.md"))
    args = ap.parse_args(argv)
    load_dotenv()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build_report(args.data, Prices.from_env()), encoding="utf-8")
    print(f"Informe en {args.out}")


if __name__ == "__main__":
    main()
