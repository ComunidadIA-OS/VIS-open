"""Motores de decisión del género de una voz a partir del texto de su turno.

`DecisionEngine` es la interfaz; `RulesEngine` (por defecto) usa las pistas de
`decision/gender_cues.py`; `LLMEngine` (decision/llm_engine.py) las lee con un modelo local.
Todos devuelven un `Decision` cerrado: el texto de la transcripción es siempre dato, nunca
instrucción, y nunca se infiere el género por cara, voz, tono ni nombre propio.
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from contracts import (
    REVIEW_CONFIDENCE_THRESHOLD,
    AnalysisEvent,
    AnalysisTimeline,
    EventType,
    GenderValue,
    Provenance,
    Speaker,
)
from decision.gender_cues import CueRules, assign_genders, load_rules

GenderLabel = Literal["mujer", "hombre", "desconocido"]


class Turn(BaseModel):
    """Un turno a clasificar y, si lo hay, lo dicho justo antes (p. ej. la Presidencia)."""

    model_config = ConfigDict(extra="forbid")
    turn_id: str
    text: str
    context_before: str | None = None


class Decision(BaseModel):
    """Salida de cualquier motor. `needs_review` sigue la regla 4 de CLAUDE.md (< 0,7)."""

    model_config = ConfigDict(extra="forbid")
    gender: GenderLabel = "desconocido"
    confidence: float = Field(default=0.0, ge=0, le=1)
    evidence: str | None = None
    reason: str | None = None
    engine: str = ""
    error: str | None = None
    latency_s: float | None = None

    @property
    def needs_review(self) -> bool:
        return self.error is not None or self.confidence < REVIEW_CONFIDENCE_THRESHOLD


class DecisionEngine(ABC):
    name: str

    @abstractmethod
    def _decide(self, turn: Turn) -> Decision: ...

    def decide(self, turn: Turn) -> Decision:
        """Decide y mide la latencia. Un fallo no rompe: queda `desconocido` + error."""
        start = time.perf_counter()
        try:
            decision = self._decide(turn)
        except Exception as exc:  # noqa: BLE001 - el benchmark no debe caerse por un turno
            decision = Decision(error=f"{type(exc).__name__}: {exc}")
        return decision.model_copy(
            update={"engine": self.name, "latency_s": round(time.perf_counter() - start, 4)}
        )


class RulesEngine(DecisionEngine):
    """Motor por reglas (por defecto): las pistas del lenguaje de `decision/cues/<idioma>.toml`."""

    name = "rules"

    def __init__(self, rules: CueRules | None = None) -> None:
        self.rules = rules or load_rules("es")

    def _decide(self, turn: Turn) -> Decision:
        events, t = [], 0.0
        if turn.context_before:
            events.append(("SPEAKER_00", turn.context_before))
        events.append(("SPEAKER_01", turn.text))
        built = []
        for i, (speaker, text) in enumerate(events):
            built.append(
                AnalysisEvent(
                    event_id=f"e{i}",
                    type=EventType.SPEECH,
                    start_s=t,
                    end_s=t + 1,
                    speaker_id=speaker,
                    text=text,
                    provenance=Provenance.AI_INFERRED,
                    confidence=0.0,
                )  # fmt: skip
            )
            t += 1
        timeline = AnalysisTimeline(
            video_id="turno",
            duration_s=t,
            speakers=[Speaker(speaker_id="SPEAKER_00"), Speaker(speaker_id="SPEAKER_01")],
            events=built,
        )
        a = next(x for x in assign_genders(timeline, self.rules) if x.speaker_id == "SPEAKER_01")
        best = max(a.evidence, key=lambda e: e.confidence, default=None)
        return Decision(
            gender=a.gender.value if a.gender != GenderValue.UNKNOWN else "desconocido",
            confidence=a.confidence or 0.0,
            evidence=best.phrase if best and a.gender != GenderValue.UNKNOWN else None,
            reason=a.reason or (best.method if best else None),
        )


def get_engine(name: str | None = None) -> DecisionEngine:
    """Motor por nombre (`DECISION_ENGINE` si no se da): `rules` o `llm`."""
    name = (name or os.environ.get("DECISION_ENGINE") or "rules").strip().lower()
    if name == "rules":
        return RulesEngine()
    if name == "llm":
        from decision.llm_engine import LLMEngine

        return LLMEngine.from_env()
    raise ValueError(f"motor desconocido: {name!r} (admitidos: rules, llm)")
