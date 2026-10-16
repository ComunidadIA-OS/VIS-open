# VIS Open

Herramienta abierta y local que mide la presencia, participación, protagonismo y representación de las mujeres en debates en vídeo (audio + gestos), sin reconocimiento facial. Reto "Mujeres por la IA Abierta" (SEDIA / Comunidad IA de Código Abierto). Equipo 6.

## Estado

M1 (16 oct 2026): estructura del repo, esquemas Pydantic de la línea de tiempo y de las tablas de revisión humana, CI y tests. Todavía no hay pipeline de audio/vídeo.

## Cómo probarlo

```bash
pip install -e ".[dev]"
make test     # tests
make check    # lint + tests
```

Requiere Python 3.11 o superior. Los tests usan solo datos sintéticos.

## Estructura

- `contracts/`: esquemas Pydantic (`AnalysisEvent`, `AnalysisTimeline`, `Speaker`, tablas de revisión y de gestos) y lectura/escritura de CSV.
- `pipeline/`, `decision/`, `metrics/`, `evaluation/`, `dashboard/`, `docker/`: carpetas reservadas para M2 en adelante.
- `docs/`: documentación.
- `THIRD_PARTY_LICENSES.md`: dependencias y sus licencias.

## Principios

- El género nunca se infiere de la cara ni de la voz: lo anotan dos personas y se informa como género atribuido; `desconocido` siempre es visible.
- Todo en local. No se suben al repo audio, vídeo, transcripciones reales ni secretos.

## Licencia

Apache-2.0 (aprobada por Sabrina el 16 oct 2026; pendiente de avisar a Ivette y Veru). Ver `LICENSE`.
