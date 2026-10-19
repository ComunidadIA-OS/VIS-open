# Ficha de modelos y uso responsable

VIS Open usa modelos abiertos ya entrenados y reglas deterministas. La única excepción prevista es un **ajuste ligero del modelo de lenguaje** (Qwen) para la métrica M09, que se mide antes y después; si no mejora, se usa el modelo sin ajustar. Esta ficha describe qué modelos intervienen, para qué sirven y dónde fallan. Las licencias exactas están en `THIRD_PARTY_LICENSES.md`.

## Información del sistema

VIS Open es una herramienta de código abierto (Apache-2.0) que combina modelos de terceros ya entrenados con métricas deterministas. Entrada: vídeo o audio de debates. Salida: línea de tiempo en JSON, tabla de revisión en CSV y métricas agregadas en un panel. No es un modelo nuevo: no hay pesos propios que publicar.

## Modelos usados

| Etapa | Modelo | Licencia (verificada el 16 oct 2026) | Notas |
|---|---|---|---|
| Transcripción | faster-whisper `small` (CPU) y `large-v3` (GPU) | MIT | Descarga en tiempo de ejecución |
| Alineado de palabras | WhisperX | BSD-2-Clause | Opcional (`WHISPER_ALIGN`) |
| Diarización (quién habla) | pyannote `speaker-diarization-3.1` | MIT | Acceso restringido en Hugging Face: exige aceptar condiciones y un token |
| Embeddings de voz | pyannote `wespeaker-voxceleb-resnet34-LM` | CC-BY-4.0 | Exige atribución |
| Gestos de levantar la mano | MediaPipe / OpenCV | pendiente de verificar | Sin reconocimiento facial |
| Motor de decisión (opcional) | LLM abierto por API compatible con OpenAI (p. ej. Qwen3) | pendiente de verificar en el repositorio oficial | El sistema es agnóstico del modelo; por defecto funciona sin LLM (motor de reglas) |

Quedan fuera `nimble-v3` (licencia no comercial) y cualquier API de pago.

## Datos de los modelos

Con qué datos se entrenó cada modelo de terceros está en `docs/DATASET_CARD.md` (sección "Modelos usados y datos con los que se entrenaron"). Salvo el ajuste ligero de Qwen descrito arriba, no entrenamos ni ajustamos modelos. Los datos de ese ajuste se describen en `docs/DATASET_CARD.md`.

## Uso previsto

Medir, en debates grabados, la presencia, la participación y el protagonismo de las mujeres: tiempo de palabra, intervenciones, preguntas, interrupciones y turnos concedidos. Los resultados son orientativos y deben revisarse por personas.

## Uso no previsto

- Identificar o seguir a personas concretas, ni reconocimiento facial.
- Inferir el género de nadie a partir de la cara o de la voz.
- Evaluar, puntuar o sancionar a individuos.
- Usar los resultados como única base de una decisión sobre personas.

## Cómo se trata el género

Ningún modelo lo infiere de la cara ni de la voz. Decisión del 16 oct (pendiente de implementar): la IA lo toma del lenguaje de la transcripción («la señora / el señor X» de la Presidencia, concordancias) con la frase y el minuto como evidencia; sin pista o con pistas contradictorias queda `desconocido` y pasa a revisión humana. No se usa el tono de voz: sería categorización biométrica (AI Act, Anexo III 1.b). En la evaluación se mide el acuerdo con dos anotadoras (kappa de Cohen). `desconocido` siempre es visible.

## Limitaciones conocidas

- La transcripción puede fallar con acentos, ruido, solapamientos y terminología específica.
- La diarización puede confundir o fusionar voces, sobre todo con muchas personas y habla simultánea.
- Los modelos abiertos reflejan sesgos de sus datos de entrenamiento; no hemos medido su efecto en este caso de uso y esta ficha no lo afirma.
- Con LLM, la salida puede equivocarse o ser manipulada por texto del vídeo (inyección de instrucciones). Por eso toda salida del LLM se valida contra un esquema y se marca como inferida por IA, y las inferencias poco fiables van a revisión humana.
- Las métricas son deterministas, pero su calidad depende de lo anterior. Si la diferencia entre grupos es menor que el margen de error, el informe dice "no concluyente".

## Implementación y sostenibilidad

Desarrollo y pruebas pequeñas en CPU; transcripción, diarización y LLM en las VM de OVHcloud con V100S (Volta): float16 o int8, no bf16. Aún no hemos medido consumo energético ni emisiones; lo indicaremos cuando lo midamos.

## Distribución

El código se publica en GitHub (Comunidad IA de Código Abierto) con licencia Apache-2.0. Los pesos de los modelos no se distribuyen en el repo: se descargan en tiempo de ejecución desde sus fuentes oficiales y cada uno mantiene su licencia (`THIRD_PARTY_LICENSES.md`). Algunos, como pyannote, exigen aceptar condiciones y un token.

## Evaluación

Pendiente: las métricas de calidad (error de transcripción y de diarización en nuestros vídeos, acuerdo entre anotadoras) las define y valida Ivette. Hasta entonces no afirmamos ninguna cifra propia; las que publican los autores de los modelos están en sus fichas.

## Reproducibilidad

Los tests usan solo datos sintéticos (`make test`).

## Contacto

Dudas o problemas: ver `CONTRIBUTING.md` y `SECURITY.md`.
