"""M09 (preguntas recibidas) y M06 (preguntas al Presidente del Gobierno), según `docs/metricas.md`.

El modelo de lenguaje solo juzga cada bloque de pregunta: ¿quien pregunta formula una pregunta?
¿a qué cargo se dirige (cita literal)? Todas las cifras las calcula este módulo con código:

- **Destinataria:** quien responde a continuación en el bloque (`decision.roles`), no lo que diga
  el modelo; el cargo literal del modelo solo sirve para separar las preguntas al Presidente del
  Gobierno y como contraste.
- **M09 a)** preguntas recibidas por persona y por género de quien responde.
- **M09 b) normalizada:** preguntas recibidas por cada ministra / por cada ministro. Sin
  normalizar solo reflejaría la composición del Gobierno.
- **M09 c)** las preguntas al Presidente del Gobierno van aparte y no entran en b).
- **Revisión humana:** una decisión con confianza < 0,7 no se cuenta; se lista para revisarla.
- La igualdad (mismas preguntas por ministra que por ministro) es el punto de referencia, no lo
  esperado, y una diferencia es una señal para investigar: las preguntas dependen también de la
  actualidad de cada ministerio (variable de confusión). El informe lo dice siempre.
"""

from __future__ import annotations

import unicodedata
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from contracts import REVIEW_CONFIDENCE_THRESHOLD, Provenance
from decision.gender_cues import _gender_of_window, _tokens, load_rules
from decision.roles import QuestionBlock
from metrics.registry import MetricResult

MIN_VOICES_KNOWN_GENDER = 4  # apartado 4 ter de docs/metricas.md
MIN_KNOWN_GENDER_SECONDS = 600.0
CONFOUNDING_NOTE = (
    "Las preguntas dependen también de la actualidad de cada ministerio: con unas 20 por sesión "
    "no se puede separar ese efecto del género de quien lo dirige. No se sacan conclusiones de "
    "género sin tenerlo en cuenta."
)
PM_KEYWORDS = ("presidente del gobierno", "presidenta del gobierno", "presidencia del gobierno")


@dataclass(frozen=True)
class Judgement:
    """Lo que el modelo (o las reglas) dice de un bloque: `QuestionDecision` ya validada."""

    block_index: int
    is_question: bool
    confidence: float
    cargo_destinatario: str | None = None
    evidence: str | None = None


def _plain(text: str) -> str:
    out = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in out if not unicodedata.combining(c))


def mentioned_gender(cargo: str | None) -> str | None:
    """Género que señala el cargo citado («señora ministra» → mujer), solo por el lenguaje."""
    if not cargo:
        return None
    g = _gender_of_window(_tokens(cargo), load_rules("es"))
    return g.value if g else None


def is_head_of_government(cargo: str | None) -> bool:
    return bool(cargo) and any(k in _plain(cargo or "") for k in PM_KEYWORDS)


def judge_blocks(blocks: Sequence[QuestionBlock], engine) -> list[Judgement]:
    """Pasa el texto de quien pregunta en cada bloque por un motor de preguntas."""
    out = []
    for b in blocks:
        text = b.asker_text
        d = engine.ask(text) if text else None
        out.append(
            Judgement(
                b.index,
                bool(d and d.is_question and d.error is None),
                d.confidence if d else 0.0,
                getattr(d, "cargo_destinatario", None) if d else None,
                d.evidence if d else None,
            )
        )
    return out


def _gender(genders: Mapping[str, str], speaker_id: str | None) -> str:
    return genders.get(speaker_id or "", "desconocido")


def _result(metric_id: str, name: str, value, sample: dict, reason: str | None, details: dict):
    return MetricResult(
        metric_id=metric_id,
        name=name,
        is_example=False,
        value=value,
        conclusive=reason is None,
        reason=reason,
        sample=sample,
        provenance=Provenance.AI_INFERRED,
        details=details,
    )


def compute_m09(
    blocks: Sequence[QuestionBlock],
    genders: Mapping[str, str],
    judgements: Sequence[Judgement],
    *,
    threshold: float = REVIEW_CONFIDENCE_THRESHOLD,
    min_voices: int = MIN_VOICES_KNOWN_GENDER,
    min_seconds: float = MIN_KNOWN_GENDER_SECONDS,
) -> MetricResult:
    """Valor = tasa de preguntas por ministra / tasa por ministro (1 = igualdad)."""
    by_index = {j.block_index: j for j in judgements}
    received: Counter[str] = Counter()
    pm_questions: list[dict] = []
    review: list[int] = []
    mismatches: list[dict] = []
    for b in blocks:
        j = by_index.get(b.index)
        if j is None or not j.is_question or b.answerer is None:
            continue
        if j.confidence < threshold:
            review.append(b.index)  # no se cuenta hasta que una persona lo revise
            continue
        if is_head_of_government(j.cargo_destinatario):
            pm_questions.append({"pregunta": b.index, "pregunta_voz": b.asker,
                                 "responde_voz": b.answerer})  # fmt: skip
            continue
        received[b.answerer] += 1
        said, answered = mentioned_gender(j.cargo_destinatario), _gender(genders, b.answerer)
        if said and answered in ("mujer", "hombre") and said != answered:
            # la pregunta nombra a otra persona de la que responde: cuenta para quien responde
            mismatches.append(
                {
                    "pregunta": b.index,
                    "cargo": j.cargo_destinatario,
                    "genero_mencionado": said,
                    "genero_quien_responde": answered,
                }
            )

    answerers = {b.answerer for b in blocks if b.answerer and b.answerer in received}
    per_gender: dict[str, dict[str, float]] = defaultdict(lambda: {"preguntas": 0, "voces": 0})
    for sid in answerers:
        g = _gender(genders, sid)
        per_gender[g]["preguntas"] += received[sid]
        per_gender[g]["voces"] += 1
    known_voices = sum(per_gender[g]["voces"] for g in ("mujer", "hombre"))
    known_seconds = sum(
        b.seconds(b.answerer) for b in blocks if b.answerer in answerers
        and _gender(genders, b.answerer) in ("mujer", "hombre")
    )  # fmt: skip
    rates = {
        g: per_gender[g]["preguntas"] / per_gender[g]["voces"]
        for g in ("mujer", "hombre")
        if per_gender[g]["voces"]
    }
    value = rates["mujer"] / rates["hombre"] if rates.get("hombre") and "mujer" in rates else None

    reason = None
    if known_voices < min_voices or known_seconds < min_seconds:
        reason = (
            f"no concluyente: muestra insuficiente (voces con género conocido {known_voices} < "
            f"{min_voices} o segundos {known_seconds:.0f} < {min_seconds:.0f})"
        )
    elif value is None:
        reason = (
            "no concluyente: falta un grupo (no hay ministras o no hay ministros que respondan)"
        )
    details = {
        "preguntas_por_persona": {
            sid: {"genero": _gender(genders, sid), "recibidas": n} for sid, n in received.items()
        },
        "por_genero": {g: dict(v) for g, v in per_gender.items()},
        "tasa_por_voz": {g: round(r, 3) for g, r in rates.items()},
        "presidente_del_gobierno": pm_questions,
        "pendientes_de_revision": review,
        "destinatario_distinto_de_quien_responde": mismatches,
        "nota": CONFOUNDING_NOTE,
    }
    sample = {
        "preguntas_validas": sum(received.values()) + len(pm_questions),
        "voces_responden_genero_conocido": known_voices,
        "segundos_genero_conocido": round(known_seconds, 1),
        "pendientes_de_revision": len(review),
    }
    return _result(
        "M09", "M09 Preguntas recibidas por ministra y por ministro", value, sample, reason, details
    )


def compute_m06(
    blocks: Sequence[QuestionBlock],
    genders: Mapping[str, str],
    judgements: Sequence[Judgement],
    *,
    threshold: float = REVIEW_CONFIDENCE_THRESHOLD,
) -> MetricResult:
    """Valor = % de las preguntas al Presidente del Gobierno que formulan mujeres.

    Hay 2 o 3 por sesión: es descriptiva por sesión; la comparación se hace sumando las tres.
    """
    by_index = {j.block_index: j for j in judgements}
    asked = Counter()
    for b in blocks:
        j = by_index.get(b.index)
        if j and j.is_question and j.confidence >= threshold and is_head_of_government(
            j.cargo_destinatario
        ):  # fmt: skip
            asked[_gender(genders, b.asker)] += 1
    total = sum(asked.values())
    value = 100 * asked["mujer"] / total if total else None
    reason = None if total else "no concluyente: ninguna pregunta al Presidente del Gobierno"
    return _result(
        "M06",
        "M06 Preguntas al Presidente del Gobierno por género de quien pregunta",
        value,
        {"preguntas_al_presidente": total},
        reason,
        {"por_genero": dict(asked), "nota": "Descriptiva por sesión; se compara con las 3 juntas."},
    )


def main(argv: Sequence[str] | None = None) -> None:
    """python -m metrics.m09 data/processed/<sesión>/timeline_genero.json [--engine rules|llm]."""
    import argparse
    import json
    from pathlib import Path

    from contracts import AnalysisTimeline
    from decision.questions import get_question_engine
    from decision.roles import question_blocks
    from pipeline.envfile import load_dotenv

    ap = argparse.ArgumentParser(description=main.__doc__)
    ap.add_argument("timeline", type=Path)
    ap.add_argument("--engine", default="rules")
    args = ap.parse_args(argv)
    load_dotenv()
    timeline = AnalysisTimeline.model_validate_json(args.timeline.read_text("utf-8"))
    genders = {s.speaker_id: s.gender.value for s in timeline.speakers}
    blocks = question_blocks(timeline)
    judgements = judge_blocks(blocks, get_question_engine(args.engine))
    out = {
        "preguntas": len(blocks),
        "M09": compute_m09(blocks, genders, judgements).model_dump(mode="json"),
        "M06": compute_m06(blocks, genders, judgements).model_dump(mode="json"),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
