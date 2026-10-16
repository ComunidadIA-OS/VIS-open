"""Valores cerrados compartidos por todos los contratos."""

from enum import StrEnum

# Por debajo de esta confianza, un dato inferido por IA pasa a revisión humana.
REVIEW_CONFIDENCE_THRESHOLD = 0.7


class Provenance(StrEnum):
    """Procedencia de cada dato (regla 6 de CLAUDE.md)."""

    OBSERVED = "observed"
    COMPUTED = "computed"
    AI_INFERRED = "ai_inferred"
    HUMAN_VALIDATED = "human_validated"


class GenderValue(StrEnum):
    """Género atribuido, nunca inferido por máquina (regla 2)."""

    WOMAN = "mujer"
    MAN = "hombre"
    UNKNOWN = "desconocido"


class GenderSource(StrEnum):
    """De dónde sale el género atribuido."""

    DECLARED = "declarado"
    PUBLIC_RECORD = "registro_publico"
    PERCEIVED_BY_ANNOTATORS = "anotacion_percibida"
    UNKNOWN = "desconocido"


class EventType(StrEnum):
    SPEECH = "speech"
    QUESTION = "question"
    INTERRUPTION = "interruption"
    HAND_RAISE = "hand_raise"


class AnnotatorConfidence(StrEnum):
    HIGH = "alta"
    MEDIUM = "media"
    LOW = "baja"
