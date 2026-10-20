# Evaluación: cómo comprobamos que las cifras son fiables

Principio (charla de visión del reto): **evaluar sobre nuestro propio contenido, con anotación hecha a mano, y contar los errores con honestidad**. Una cifra sin su error no se publica. Cada capa de VIS Open se evalúa con tres preguntas: ¿se encuentra lo que hay?, ¿el atributo es correcto?, ¿la medida final se acerca a la de una persona?

## Qué se evalúa, con qué y quién

| Capa | Pregunta | Medida | Herramienta | Quién |
|---|---|---|---|---|
| Transcripción | ¿Se entiende lo que se dice? | WER (palabras mal transcritas) en un tramo anotado | pendiente de programar | Ivette anota; Sabrina mide |
| Separación de voces | ¿Quién habla cuándo? | DER (error de diarización) en un tramo anotado | pendiente de programar | Ivette anota; Sabrina mide |
| Género por lenguaje | ¿El género asignado es correcto? | F1 por clase (mujer, hombre, desconocido), matriz de confusión y % a revisión | `evaluation/benchmark.py` (`docs/MOTORES_DECISION.md`) | Ivette y Veru anotan 150 turnos (30 ambiguos) |
| Métricas | ¿Coinciden con el Diario de Sesiones? | Diferencia en número y orden de intervenciones y en género | a mano, con hoja de cálculo | Ivette |
| Vídeo: personas visibles | ¿Se cuentan bien? | Error medio (MAE), sesgo a contar de menos, recall y precisión | `evaluation/video_eval.py` | Ivette anota `personas.csv` |
| Vídeo: manos levantadas | ¿Se detectan las manos? | Precisión, recall y F1 por solape en el tiempo y la zona | `evaluation/video_eval.py` | Ivette anota `manos.csv` |
| Vídeo: género de las pistas (por audio) | ¿El audio asigna bien el género a quien sale en pantalla? | % etiquetadas, acierto sobre las etiquetadas y **cuántas mujeres y hombres quedan sin etiquetar** | `evaluation/video_eval.py` | Ivette anota `pistas.csv` |

## Línea base con la que comparamos

Una medida solo vale si mejora algo simple:

- **Género:** «todo desconocido». Nuestra regla debe etiquetar bien una parte y dejar en «desconocido» (a revisión) el resto.
- **Personas visibles:** «siempre una persona en pantalla». El conteo con pose debe tener menos error.
- **Manos:** «ninguna mano». El detector debe encontrar manos reales sin inventar otras.

## Cómo anotar el vídeo (Ivette)

Se anotan 2 a 5 minutos de una sesión, sin nombres. Tres CSV en UTF-8 (no abrirlos con doble clic en Excel; usar «Importar» o un editor de texto):

```
personas.csv   t_s,n_personas        # cuántas personas se ven en ese segundo
manos.csv      zona,inicio_s,fin_s   # cada mano levantada; zona Z1..Z4 (cuarto de la imagen, de izquierda a derecha)
pistas.csv     pista,genero          # mujer | hombre | desconocido, para cada pista de video.json
```

Después: `python -m evaluation.video_eval data/processed/V001/video.json --personas personas.csv --manos manos.csv --pistas pistas.csv`.

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
- Las métricas M01–M04 y M13 están en borrador hasta que Ivette las valide.

## Para la presentación (texto propuesto para una diapositiva «Evaluación y límites»)

> **Cómo sabemos que las cifras son fiables**
> - Evaluamos sobre nuestras propias sesiones, con anotación manual de 150 turnos (género) y de un tramo de vídeo (personas y manos).
> - Medimos: F1 por clase del género, error de conteo y F1 de manos levantadas, y comparamos con el Diario de Sesiones.
> - «Desconocido» siempre visible: lo que no sabemos, no lo inventamos.
> - Decisión de diseño: sin género por la cara (sesgo medido en la literatura, alto riesgo normativo, licencias incompatibles).
> - Límites: cuenta lo que ve la cámara; el género depende de las pistas del lenguaje; 3 sesiones no dan tendencias.
>
> *Resultados: se rellenan con las cifras reales de `evaluation/` tras la anotación (27–28 oct).*
