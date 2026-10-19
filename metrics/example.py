"""MÉTRICA DE EJEMPLO. No es M01 a M13 y no tiene validez: sirve para copiar el patrón.

Para crear una métrica real (Ivette): copia esta función, cambia `metric_id`, `name`, la
docstring (la definición en una frase) y el cálculo, y fija los mínimos de muestra que decida.
Pasos completos en docs/METRICAS_MARCO.md.
"""

from __future__ import annotations

import pandas as pd

from contracts import GenderValue
from metrics.frame import speech_time_by_gender
from metrics.registry import MetricOutput, metric


@metric(
    metric_id="X00_EJEMPLO",
    name="EJEMPLO: porcentaje del tiempo de palabra de mujeres (sobre género conocido)",
    # Mínimos de juguete para los tests; los reales los decide Ivette.
    min_speakers_known_gender=2,
    min_known_gender_seconds=10,
    is_example=True,
)
def example_women_share_of_known_speech(frame: pd.DataFrame) -> MetricOutput:
    """Segundos de palabra de mujeres / (mujeres + hombres), en puntos porcentuales (0 a 100)."""
    by_gender = speech_time_by_gender(frame).set_index("gender")["seconds"]
    women = float(by_gender[GenderValue.WOMAN.value])
    known = women + float(by_gender[GenderValue.MAN.value])
    return MetricOutput(
        value=round(100 * women / known, 2),
        margin=None,  # una métrica real calcula aquí su margen de error
        details={"women_s": women, "men_s": known - women},
    )
