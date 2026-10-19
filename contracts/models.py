"""Esquemas Pydantic de la línea de tiempo y de las tablas de anotación."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from contracts.enums import (
    REVIEW_CONFIDENCE_THRESHOLD,
    AnnotatorConfidence,
    EventType,
    GenderSource,
    GenderValue,
    Provenance,
)

SPEAKER_ID_PATTERN = r"^SPEAKER_\d{2}$"
SCHEMA_VERSION = "1.0"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GenderEvidence(_Strict):
    """Pista del lenguaje que sostiene (o contradice) el género atribuido a una voz."""

    gender: GenderValue
    method: str = Field(min_length=1)
    phrase: str = Field(min_length=1)
    start_s: float = Field(ge=0)
    event_id: str | None = None
    confidence: float = Field(ge=0, le=1)
    provenance: Provenance = Provenance.AI_INFERRED

    @property
    def minute(self) -> float:
        return round(self.start_s / 60, 2)


class Speaker(_Strict):
    speaker_id: str = Field(pattern=SPEAKER_ID_PATTERN)
    total_speech_s: float = Field(default=0.0, ge=0)
    gender: GenderValue = GenderValue.UNKNOWN
    gender_source: GenderSource = GenderSource.UNKNOWN
    role: str | None = None
    name: str | None = None
    gender_evidence: list[GenderEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def _gender_matches_source(self) -> Speaker:
        known = self.gender != GenderValue.UNKNOWN
        sourced = self.gender_source != GenderSource.UNKNOWN
        if known != sourced:
            raise ValueError(
                "gender y gender_source deben ser ambos 'desconocido' o ambos conocidos"
            )
        return self


class AnalysisEvent(_Strict):
    event_id: str = Field(min_length=1)
    type: EventType
    start_s: float = Field(ge=0)
    end_s: float = Field(ge=0)
    speaker_id: str | None = Field(default=None, pattern=SPEAKER_ID_PATTERN)
    text: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    provenance: Provenance
    source: str | None = None
    zone_id: str | None = None
    granted: bool | None = None

    @model_validator(mode="after")
    def _check(self) -> AnalysisEvent:
        if self.end_s < self.start_s:
            raise ValueError("end_s no puede ser menor que start_s")
        if self.type != EventType.HAND_RAISE and (
            self.zone_id is not None or self.granted is not None
        ):
            raise ValueError("zone_id y granted solo valen para eventos hand_raise")
        return self

    @property
    def needs_review(self) -> bool:
        """True si un dato de IA es poco fiable o no declara confianza."""
        if self.provenance != Provenance.AI_INFERRED:
            return False
        return self.confidence is None or self.confidence < REVIEW_CONFIDENCE_THRESHOLD


class AnalysisTimeline(_Strict):
    schema_version: str = SCHEMA_VERSION
    video_id: str = Field(min_length=1)
    duration_s: float = Field(gt=0)
    speakers: list[Speaker] = Field(default_factory=list)
    events: list[AnalysisEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def _integrity(self) -> AnalysisTimeline:
        speaker_ids = {s.speaker_id for s in self.speakers}
        if len(speaker_ids) != len(self.speakers):
            raise ValueError("speaker_id repetido")
        event_ids = [e.event_id for e in self.events]
        if len(set(event_ids)) != len(event_ids):
            raise ValueError("event_id repetido")
        for e in self.events:
            if e.speaker_id is not None and e.speaker_id not in speaker_ids:
                raise ValueError(f"evento {e.event_id}: speaker_id desconocido")
            if e.end_s > self.duration_s:
                raise ValueError(f"evento {e.event_id}: termina después de la duración")
        return self


class ReviewRow(_Strict):
    """Una fila por voz y por anotadora. Las columnas finales las rellena la persona."""

    video_id: str = Field(min_length=1)
    speaker_id: str = Field(pattern=SPEAKER_ID_PATTERN)
    total_seconds: float = Field(ge=0)
    fragment_1_start_s: float | None = Field(default=None, ge=0)
    fragment_2_start_s: float | None = Field(default=None, ge=0)
    fragment_3_start_s: float | None = Field(default=None, ge=0)
    annotator_id: str | None = None
    gender: GenderValue | None = None
    role: str | None = None
    name: str | None = None
    confidence: AnnotatorConfidence | None = None
    notes: str | None = None


class GestureRow(_Strict):
    """Una fila por gesto de petición de palabra, para la segunda hoja."""

    video_id: str = Field(min_length=1)
    annotator_id: str | None = None
    start_s: float = Field(ge=0)
    speaker_id: str | None = Field(default=None, pattern=SPEAKER_ID_PATTERN)
    zone_id: str | None = None
    granted: bool | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _who(self) -> GestureRow:
        if self.speaker_id is None and self.zone_id is None:
            raise ValueError("indica speaker_id o zone_id")
        return self
