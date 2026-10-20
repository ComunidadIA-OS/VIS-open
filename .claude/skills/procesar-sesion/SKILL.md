---
name: procesar-sesion
description: Procesar una sesión del Congreso en VIS Open de principio a fin (manifiesto, pipeline, seudonimización, género por lenguaje, revisión). Úsala cuando se pida analizar un vídeo nuevo o repetir el análisis.
---

# Procesar una sesión

Reglas que no se rompen: el vídeo no se modifica ni sale de `data/` (ignorado por git); nunca se sube audio, vídeo ni transcripciones; no se guardan nombres (cada voz es «Persona N»); el género sale solo de pistas del lenguaje.

## Pasos

1. **Vídeo.** Debe estar en `data/raw/<video_id>.mp4` (el nombre sin extensión es el `video_id`, p. ej. `V004`). Calcula su duración con `ffprobe`.
2. **Manifiesto.** Si no tiene fila en `data/manifiesto.csv`:
   `python -m sources.congreso --url "<URL de la sesión>" --file data/raw/<id>.mp4 --set descargado_por=<nombre> --set fecha_descarga=AAAA-MM-DD --set tramo_inicio=00:00:00 --set tramo_fin=<hh:mm:ss> --set duracion_s=<s> --set ruta_drive=02_originales/<id>.mp4 --set fecha_borrado=2026-12-04 --set licencia_verificada=si`
   Pon `licencia_verificada=si` solo si una persona ha leído el aviso legal del Congreso. Si falta la URL, pídesela a la persona; no la inventes.
3. **Comprobar la fila:** `python -c "from sources import require_ready; print(require_ready('data/raw/<id>.mp4','data/manifiesto.csv')['video_id'])"`
4. **Analizar:** `python -m pipeline.run data/raw/<id>.mp4` (lee `.env`; necesita `HF_TOKEN`). Salida en `data/processed/<id>/`: `timeline.json`, `resumen.json`, `review_genero.csv`, `review_anotadora_*.csv`, `source.json`.
5. **Revisar:** lee `resumen.json` (tiempo por género, muestra, `voces`, `voces_a_revision`). Si hay una sola voz o casi todo `desconocido`, dilo: suele ser diarización floja en clips cortos o sin la Presidencia dando la palabra.
6. **Nunca** abras los CSV en Excel con doble clic (rompe tildes y columnas): léelos con Python.

## Comprobar que no hay nombres

`rg -n "<apellido conocido>" data/processed/<id>/` no debe dar resultados en `timeline.json`, `resumen.json` ni `review_*.csv`.
