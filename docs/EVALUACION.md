# Evaluación: cómo comprobamos que las cifras son fiables

Principio (charla de visión del reto): **evaluar sobre nuestro propio contenido, con anotación hecha a mano, y contar los errores con honestidad**. Una cifra sin su error no se publica. Cada capa de VIS Open se evalúa con tres preguntas: ¿se encuentra lo que hay?, ¿el atributo es correcto?, ¿la medida final se acerca a la de una persona?

## Resultados (validación de Ivette, 25–26 oct 2026)

Referencia: la **lista oficial de intervenciones** del archivo audiovisual del Congreso, sobre las tres sesiones de evaluación (V005, V006 y V007). Sustituye a la anotación manual de 150 turnos prevista (#52): es más completa e independiente del sistema. Cada voz se empareja con la persona oficial por el orden y la estructura de las preguntas, sin usar el género; el género solo se compara al final. Detalle en las issues #55 y #144.

| Qué | Resultado |
|---|---|
| Personas que intervienen | 87 de 87 (25 / 31 / 31) |
| Género | 86 correctas (98,9 %), **0 errores**, 1 desconocida (un diputado), que es la que el panel manda a Human in the loop. Antes de mejorar la regla del lenguaje (PR #145) eran 83 correctas y 4 desconocidas, 3 de ellas ministras |
| Error por grupo | 0 errores en mujeres y en hombres. Sin género: 0 de 47 mujeres y 1 de 40 hombres (antes de la PR #145: 3 de 47 y 1 de 40) |
| Intervenciones | Oficial 66 / 73 / 76; sistema 64 / 74 / 75. 4 casos de voces mezcladas, siempre entre personas del mismo género |
| Bloques de pregunta | 17 / 18 / 20 frente a 17 / 19 / 20. En V006 falta la pregunta 13 (sin anuncio en la transcripción, #124) |
| M03a / M03b | La pausa de 1 s partía las intervenciones con los aplausos (6,7 / 8,9 / 7,1). Con la nueva definición M03a (5 s): 3,82 / 3,89 / 3,65 frente a 3,88 / 3,84 / 3,80 oficiales (PR #142, con los ficheros regenerados el 26/10). M03b avisa de los bloques con 3 o más voces |
| M06 | 40 % de 5 / 67 % de 3 / 0 % de 3: **igual que la referencia** en las tres |
| M09 | 0,75 / 0,86 / 0,81 frente a 0,75 / 0,73 / 0,81: igual en V005 y V007; en V006 falta la pregunta 13 |
| Modelo (Qwen) | Se evalúa aparte con `modelo_por_pregunta` (si detecta la pregunta y si acierta el cargo). Pendiente: los m09.json de OVH del 26/10 se generaron sin llamadas al modelo; se medirá cuando se vuelva a lanzar M09 con Qwen |

Queda opcional el tiempo de palabra (M02), que la lista oficial no da: cronometrar a mano una pregunta o declararlo como límite.

## Qué se evalúa, con qué y quién

| Capa | Pregunta | Medida | Herramienta | Quién |
|---|---|---|---|---|
| Transcripción | ¿Se entiende lo que se dice? | WER (palabras mal transcritas) en un tramo anotado | pendiente de programar | Ivette anota; Sabrina mide |
| Separación de voces | ¿Quién habla cuándo? | DER (error de diarización) en un tramo anotado | pendiente de programar | Ivette anota; Sabrina mide |
| Género por lenguaje | ¿El género asignado es correcto? | Aciertos, errores y % a revisión, también por grupo | Lista oficial de intervenciones (ver «Resultados»); los 150 turnos anotados con `evaluation/benchmark.py` quedan como opcional (#52) | Ivette (hecho) |
| Métricas | ¿Coinciden con la referencia oficial? | Diferencia en número y orden de intervenciones, género, M03a/M03b, M06 y M09 | lista oficial de intervenciones del archivo audiovisual | Ivette (hecho, ver «Resultados») |
| Vídeo: personas visibles | ¿Se cuentan bien? | Error medio (MAE), sesgo a contar de menos, recall y precisión | `evaluation/video_eval.py` | Ivette anota `personas.csv` |
| Transcripción | ¿Se transcribe bien lo que se dice? | WER (sustituciones, borrados, inserciones) | `evaluation/asr_diar.py wer` | Un tramo de 5 min transcrito a mano, comprobado con el Diario de Sesiones |
| Diarización | ¿Se separa bien quién habla? | DER (voz perdida, falsa alarma, confusión), sin margen de tolerancia | `evaluation/asr_diar.py der` | Turnos `speaker_id,start_s,end_s` del mismo tramo |
| Vídeo: género de las pistas (por audio) | ¿El audio asigna bien el género a quien sale en pantalla? | % etiquetadas, acierto sobre las etiquetadas y **cuántas mujeres y hombres quedan sin etiquetar** | `evaluation/video_eval.py` | Ivette anota `pistas.csv` |

## Línea base con la que comparamos

Una medida solo vale si mejora algo simple:

- **Género:** «todo desconocido». Nuestra regla debe etiquetar bien una parte y dejar en «desconocido» (a revisión) el resto.
- **Personas visibles:** «siempre una persona en pantalla». El conteo con pose debe tener menos error.

## Límites conocidos del vídeo

El modelo de pose (`pose_landmarker_full`, Apache-2.0) está pensado para una sola persona a menos de ~4 m (ficha del modelo). Con `num_poses` alto sirve, pero en planos amplios del hemiciclo **cuenta de menos**. Lo declaramos como límite y lo medimos contra `personas.csv`; no se presenta como conteo exacto de la sala.

## Resultado del género por lenguaje (20 oct 2026)

Benchmark sintético (`SINTETICO_turnos.csv`) con Qwen3.5-9B por OVH AI Endpoints y el prompt simétrico: F1 macro 0,90 (mujer 0,99, hombre 0,97, desconocido 0,74), 10 % a revisión. Antes del prompt simétrico, hasta 22 de 69 hombres caían en «desconocido». Es un dato sintético: no sustituye la evaluación con turnos anotados por Ivette.

## Anotar los 150 turnos de género (Ivette y Veru)

```
python -m evaluation.prepare_annotation      # lee data/processed/*/, escribe data/anotacion/
```

- `turnos_para_anotar.csv` (`turn_id,context_before,text,label`): lo único que ven quienes anotan. No lleva el género que asignó el sistema. Cada una rellena `label` por su cuenta (`mujer`, `hombre` o `desconocido`) mirando solo `context_before` y `text`, y solo si el texto da una pista explícita («tiene la palabra la señora…», «estoy agradecida»). Nunca por el nombre, la voz ni la imagen.
- `clave_interna.csv`: qué turno es de qué sesión y qué género le dio el sistema. No se enseña a quien anota; se usa después para calcular el F1 con `evaluation.benchmark`.
- Reparto por defecto: 60 mujer, 60 hombre y 30 desconocido **según el sistema**, solo para equilibrar la muestra; si una clase no llega, se completa con turnos de otras clases. Los turnos se parten en trozos de hasta ~60 palabras.
- Ninguno de los dos ficheros se sube al repo (`data/` está ignorado): contienen transcripciones reales seudonimizadas.

## Informe de análisis

`python -m evaluation.informe` escribe `data/informe_analisis.md` con audio (voces, género, confianza), vídeo (personas, tiempo en pantalla, manos) y consumo del modelo de lenguaje (tokens, latencia, precio con los `LLM_PRICE_*` del `.env`). El consumo se mide con el benchmark sintético, no con sesiones reales.

## Cómo anotar el vídeo (Ivette)

Se anotan 2 a 5 minutos de una sesión, sin nombres. Tres CSV en UTF-8 (no abrirlos con doble clic en Excel; usar «Importar» o un editor de texto):

```
personas.csv   t_s,n_personas        # cuántas personas se ven en ese segundo
pistas.csv     pista,genero          # mujer | hombre | desconocido, para cada pista de video.json
```

Después: `python -m evaluation.video_eval data/processed/V001/video.json --personas personas.csv --pistas pistas.csv`.

## Por qué no usamos el género por la cara (decisión de diseño)

La baseline de la charla etiqueta el género con un modelo de caras. No la seguimos en ese paso:

- **Sesgo:** la propia charla muestra que los clasificadores de género por cara se equivocan más con mujeres (Gender Shades: 34,7 % de error con mujeres de piel oscura frente a 0,8 % con hombres de piel clara) y que, en su ejemplo, la medida **subestima a las mujeres** (2 de 4 acaban «desconocido»). Un modelo sesgado sesga directamente las conclusiones sobre la presencia de mujeres.
- **Naturaleza del dato:** el género no se ve en una cara; el modelo predice cómo la percibieron quienes anotaron sus datos de entrenamiento.
- **Normativa:** clasificar por rasgos biométricos nos llevaría a un sistema de alto riesgo (Reglamento de IA, Anexo III.1.b).
- **Licencias:** las herramientas de la baseline (Ultralytics YOLO, AGPL-3.0; modelos de InsightFace, no comercial) no encajan con Apache-2.0.

En su lugar, el género sale de las pistas del lenguaje de la sesión y, en el vídeo, solo se asigna por el audio (cuando en el plano hay una sola persona y la voz que habla tiene género por lenguaje). Si no hay base suficiente: «desconocido», siempre visible.

## Límites que se declaran

- Las personas visibles son lo que ve la cámara, no quién hay en la sala; con planos amplios se cuenta de menos.
- El voto por audio supone que el primer plano muestra a quien habla.
- La seudonimización es por reglas y puede dejar pasar un nombre suelto; se revisa antes de publicar.
- Con 3 sesiones no se pueden sacar tendencias.
- Las métricas siguen la definición de Ivette (`docs/metricas.md`) y están validadas frente a la lista oficial (ver «Resultados»).

## Para la presentación (texto propuesto para una diapositiva «Evaluación y límites»)

> **Cómo sabemos que las cifras son fiables**
> - Evaluamos sobre nuestras propias sesiones frente a la lista oficial de intervenciones del Congreso.
> - Género: 86 de 87 personas correctas, 0 errores, 1 a revisión humana. M06 coincide en las 3 sesiones; M09 en 2 de 3.
> - «Desconocido» siempre visible: lo que no sabemos, no lo inventamos.
> - Decisión de diseño: sin género por la cara (sesgo medido en la literatura, alto riesgo normativo, licencias incompatibles).
> - Límites: cuenta lo que ve la cámara; el género depende de las pistas del lenguaje; 3 sesiones no dan tendencias.
>
> *Cifras: apartado «Resultados» de este documento (validación del 25–26 oct).*
