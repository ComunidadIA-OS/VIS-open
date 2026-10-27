"""Marco de métricas: registro, resultado y regla de «no concluyente».

NO define M01 a M13 ni sus umbrales: son de Ivette. Una métrica nueva se añade copiando
`metrics/example.py` (ver docs/METRICAS_MARCO.md y SKILLS.md «añadir-metrica»).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from contracts import Provenance
from metrics.frame import Sample, sample_of


class MetricOutput(BaseModel):
    """Lo que devuelve la función de una métrica: valor y margen (si lo hay).

    Si la propia métrica sabe que su resultado no es comparable (por ejemplo, no hay al menos
    dos voces en cada grupo), deja el motivo en `reason`: `run_metric` lo convierte en un
    resultado no concluyente sin valor.
    """

    model_config = ConfigDict(extra="forbid")
    value: float
    margin: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None


class MetricResult(BaseModel):
    """Resultado publicable: siempre con el tamaño de muestra y, si no concluye, el motivo."""

    model_config = ConfigDict(extra="forbid")
    metric_id: str
    name: str
    is_example: bool
    value: float | None
    margin: float | None = None
    conclusive: bool
    reason: str | None = None
    sample: dict[str, float | int]
    provenance: Provenance = Provenance.COMPUTED
    details: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class MetricSpec:
    metric_id: str
    name: str
    description: str
    func: Callable[[pd.DataFrame], MetricOutput]
    # Mínimos de muestra: obligatorios y sin valor por defecto; cada métrica decide los suyos.
    min_speakers_known_gender: int
    min_known_gender_seconds: float
    is_example: bool = False


_REGISTRY: dict[str, MetricSpec] = {}


def metric(
    *,
    metric_id: str,
    name: str,
    min_speakers_known_gender: int,
    min_known_gender_seconds: float,
    is_example: bool = False,
) -> Callable[[Callable[[pd.DataFrame], MetricOutput]], Callable[[pd.DataFrame], MetricOutput]]:
    """Decorador que registra una función pura `DataFrame -> MetricOutput`."""

    def register(func: Callable[[pd.DataFrame], MetricOutput]):
        if metric_id in _REGISTRY:
            raise ValueError(f"métrica ya registrada: {metric_id}")
        _REGISTRY[metric_id] = MetricSpec(
            metric_id=metric_id,
            name=name,
            description=(func.__doc__ or "").strip(),
            func=func,
            min_speakers_known_gender=min_speakers_known_gender,
            min_known_gender_seconds=min_known_gender_seconds,
            is_example=is_example,
        )
        return func

    return register


def get_metric(metric_id: str) -> MetricSpec:
    try:
        return _REGISTRY[metric_id]
    except KeyError:
        raise KeyError(f"métrica no registrada: {metric_id}") from None


def list_metrics() -> list[MetricSpec]:
    return [_REGISTRY[k] for k in sorted(_REGISTRY)]


def _sample_dict(s: Sample) -> dict[str, float | int]:
    return {
        "n_events": s.n_events,
        "n_speakers": s.n_speakers,
        "n_speakers_known_gender": s.n_speakers_known_gender,
        "speech_seconds": round(s.speech_seconds, 3),
        "known_gender_seconds": round(s.known_gender_seconds, 3),
        "unattributed_share": round(s.unattributed_share, 4),
    }


def run_metric(metric_id: str, frame: pd.DataFrame) -> MetricResult:
    """Ejecuta una métrica; si la muestra no llega a sus mínimos, devuelve «no concluyente»."""
    spec = get_metric(metric_id)
    s = sample_of(frame)
    base = {
        "metric_id": spec.metric_id,
        "name": spec.name,
        "is_example": spec.is_example,
        "sample": _sample_dict(s),
    }
    short = []
    if s.n_speakers_known_gender < spec.min_speakers_known_gender:
        short.append(
            f"voces con género conocido {s.n_speakers_known_gender}"
            f" < {spec.min_speakers_known_gender}"
        )
    if s.known_gender_seconds < spec.min_known_gender_seconds:
        short.append(
            f"segundos con género conocido {s.known_gender_seconds:.0f}"
            f" < {spec.min_known_gender_seconds:.0f}"
        )
    if short:
        return MetricResult(
            **base,
            value=None,
            conclusive=False,
            reason="no concluyente: muestra insuficiente (" + "; ".join(short) + ")",
        )
    out = spec.func(frame)
    if out.reason:
        return MetricResult(
            **base,
            value=None,
            margin=out.margin,
            conclusive=False,
            reason=out.reason,
            details=out.details,
        )
    return MetricResult(
        **base, value=out.value, margin=out.margin, conclusive=True, details=out.details
    )


MAX_UNATTRIBUTED_PCT = 20.0  # M13: más del 20 % sin atribuir no permite concluir (20,0 vale)


def gap_is_conclusive(
    gap: float, *, threshold: float, unattributed_share: float, margin: float | None
) -> tuple[bool, str | None]:
    """Regla de conclusiones de docs/metricas.md (apartado 3) para una brecha entre grupos.

    `gap`, `threshold`, `unattributed_share` y `margin` van en puntos de % (2,5 % = 2.5, no
    0.025). Concluye solo si |brecha| >= umbral (15,0 cuenta), el tiempo sin atribuir es como
    mucho del 20 % y menor que la brecha, y la brecha resiste el margen de error. `threshold` es
    obligatorio y sin valor por defecto: lo fija Ivette.
    """
    g = abs(gap)
    if g < threshold:
        return False, "no concluyente: la brecha no llega al umbral"
    if unattributed_share > MAX_UNATTRIBUTED_PCT:
        return False, "no concluyente: más del 20 % del tiempo está sin atribuir"
    if unattributed_share >= g:
        return False, "no concluyente: el tiempo sin atribuir es mayor o igual que la brecha"
    if margin is not None and g <= margin:
        return False, "no concluyente: la brecha cabe en el margen de error"
    return True, None
