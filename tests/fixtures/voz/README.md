# Frases de prueba del detector de voz

Cuatro frases cortas **sintetizadas** (voz de síntesis «Microsoft Helena» de Windows, en local) a
16 kHz mono. No hay voz de ninguna persona ni audio de sesiones. Las usa `tests/vad.test.mjs` para
comprobar que el detector acepta voz real y rechaza teclas, tráfico y bocinas.

- `dashboard_sesion4.wav`: «Enséñame el dashboard de la sesión cuatro»
- `para_el_video.wav`: «Para la vídeo»
- `resumen.wav`: «Dame el resumen de la sesión cuatro»
- `es_un_hombre.wav`: «Es un hombre, con confianza media»

Publicación aprobada por Sabrina (21 oct 2026). Si algún día se retiran, la prueba se salta sola.
