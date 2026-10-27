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
| Análisis de vídeo: personas visibles y tiempo en pantalla (M14, manos levantadas, descartada para el Congreso) | MediaPipe y OpenCV | Apache-2.0 (verificada el 20 y el 21 oct 2026) | Sin reconocimiento facial; el modelo de pose es para una persona a menos de ~4 m: no apto para reconocer identidad |
| Órdenes de voz (asistente) | `whisper-large-v3-turbo` por API (OVHcloud AI Endpoints) | MIT (etiqueta de Hugging Face, 21 oct 2026) | Solo transcribe la orden hablada; el audio no se guarda en el equipo |
| Resumen del contenido y M09 | Qwen3.5 (4B o 9B) por API compatible con OpenAI | Apache-2.0 (etiqueta de Hugging Face, 21 oct 2026) | Salida cerrada con esquema; el resumen se marca como IA |
| Detector de voz (manos libres) | **No es un modelo entrenado**: reglas de señal (volumen, espectro, periodicidad del tono, variación de sílabas) | Código propio, Apache-2.0 | `dashboard/vad.js`; probado con 8 ruidos sintéticos y 4 frases sintetizadas |
| Voz del asistente y avatar | Síntesis de voz del navegador (es-ES) y un shader WebGL propio | Función del navegador / código propio | Sin servicios en la nube |
| Motor de decisión (opcional) | LLM abierto por API compatible con OpenAI (Qwen3.5 4B y 9B) | Apache-2.0 (etiqueta de Hugging Face, 21 oct 2026) | El sistema es agnóstico del modelo; por defecto funciona sin LLM (motor de reglas) |

Quedan fuera `nimble-v3` (licencia no comercial) y cualquier API de pago.

Los textos de las licencias están en `LICENSES/` y la atribución que exige CC-BY-4.0 (modelo `wespeaker`), en `NOTICE`. Versión y fecha de verificación de cada componente: `THIRD_PARTY_LICENSES.md`.

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

Ningún modelo lo infiere de la cara ni de la voz. Decisión del 16 oct, implementada con reglas (`decision/gender_cues.py`, ver `docs/GENERO_LENGUAJE.md`) y validada frente a la lista oficial del Congreso (86 de 87 personas correctas, 0 errores, 1 a revisión; `docs/EVALUACION.md`): el género se toma del lenguaje de la transcripción («la señora / el señor X» de la Presidencia, concordancias) con la frase y el minuto como evidencia; sin pista o con pistas contradictorias queda `desconocido` y pasa a revisión humana. No se usa el tono de voz: sería categorización biométrica (AI Act, Anexo III 1.b). En la evaluación se mide el acuerdo con dos anotadoras (kappa de Cohen). `desconocido` siempre es visible.

**Atribuido, no autodeclarado, y binario.** En el Congreso, el género sale del tratamiento que da la Cámara («la señora diputada»): es un género atribuido, no la identidad de género, que solo cada persona puede declarar. Tiene dos valores más `desconocido` y no refleja identidades no binarias. Cuando hay un género declarado (grabaciones propias), manda ese dato.

**Riesgo de malgenerizar (*misgendering*).** Asignar el género sin el consentimiento de la persona puede equivocarse con su identidad. El riesgo es mayor en la revisión humana, donde el género es **percibido** (`anotacion_percibida`) y puede arrastrar estereotipos. Lo reducimos así: solo cuenta si coinciden dos anotadoras, `desconocido` siempre es válido y visible, cada dato lleva su procedencia, no se guardan nombres (cada voz es «Persona N») y las conclusiones son agregadas, nunca sobre una persona identificada. Límite: un cargo público («la ministra de Hacienda») puede reconocerse por la fecha de la sesión aunque no se guarde su nombre.

## Asistente de voz

**Uso previsto:** manejar el panel sin ver la pantalla ni usar el ratón: cambiar de sesión, escuchar un corte, explicar resultados, validar voces con confirmación y descargar informes.
**Uso no previsto:** decidir el género de nadie, dar cifras que no calcule el código, usarlo conduciendo o como único control de acceso.
**Transparencia (AI Act, art. 50):** el asistente se presenta como IA; lo que genera un modelo va marcado.
**Limitaciones medidas en pruebas:** con ruido, vídeo o teclado, Whisper puede inventar frases («Gracias por ver el vídeo», «¿Qué es lo que se hace?»); se filtran con la probabilidad de «no es voz» de cada segmento, la confianza, las repeticiones y una lista de muletillas, y con un detector de voz previo. Con un vídeo sonando, solo se atienden órdenes cortas de pararlo. No está probado con muchas voces distintas ni con acentos variados.

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
