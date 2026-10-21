# Ficha de datos

## Resumen

El repositorio **no contiene datos reales**: ni audio, ni vídeo, ni transcripciones, ni etiquetas de personas. Los tests usan solo datos sintéticos creados para este proyecto.

## Datos que procesa la herramienta

| Dato | Origen | Dónde vive | ¿Se publica? |
|---|---|---|---|
| Vídeos de sesiones del Congreso | Archivo audiovisual del Congreso de los Diputados, reutilizado según su aviso legal (sin alterar, citando fuente y fecha, sin la interpretación simultánea). La Organización no ofrece vídeos | Fuera del repo (`data/`, ignorado por git) y en una unidad compartida solo del equipo, con un manifiesto por vídeo | No |
| Línea de tiempo (JSON) | Generada por el pipeline | Fuera del repo | No |
| Tabla de revisión de voces y de gestos (CSV) | Generada por el pipeline; la rellenan personas en los casos dudosos y, en la evaluación, dos anotadoras | Fuera del repo | No; solo se publican resultados agregados |
| Datos sintéticos de prueba | Creados a mano en `tests/` | En el repo | Sí |
| Frases de prueba del detector de voz | Cuatro frases **sintetizadas** con una voz de síntesis de Windows (no hay voz de ninguna persona), 16 kHz mono | `tests/fixtures/voz/` | Sí (publicación aprobada por Sabrina el 21 oct 2026) |
| Audio de una orden hablada | Tu voz diciendo una orden al asistente (segundos) | Memoria del navegador y del panel; no se guarda | Sale a la API de transcripción (OVHcloud AI Endpoints) |
| Respuestas de las anotadoras | Género, confianza e ID de conexión por voz | `data/processed/<sesión>/` (no se sube) | No |

## Tipos de datos que no usamos

| Tipo | ¿Usado? | Detalle |
|---|---|---|
| Correos electrónicos | No | Ni en el repo ni en el pipeline. |
| Mensajes de texto (chats, SMS, redes) | No | |
| Noticias o textos web | No | No se raspan ni se usan como datos. |
| Datos personales reales de terceros | No | Solo con base jurídica y autorización de la Organización. |
| Audio y vídeo de sesiones del Congreso | Sí, fuera del repo | Cargos públicos en un acto público; resultados solo agregados. |
| Transcripciones | Sí, derivadas | Generadas a partir del audio; no se publican. |
| Etiquetas de género atribuido, rol y gestos (pistas del lenguaje y revisión humana) | Sí, derivadas | Se publican solo agregadas. |
| Datos sintéticos de prueba | Sí | Creados por el equipo, en `tests/`. |

El único texto que lee un LLM opcional es la transcripción seudonimizada de un debate (para M09 y para el resumen del contenido del asistente de voz); por eso se valida su salida (ver `MODEL_CARD.md`, limitaciones). Qué servicios reciben qué datos: `docs/PROVEEDORES.md`.

## Separación de los datos (entrenamiento, validación, prueba)

- **Seudonimización (decisión del 19 oct):** no se guardan nombres. Cada voz se identifica con un código anónimo (Persona 1, Persona 2…) y, en la evidencia del género y en las transcripciones, el nombre se sustituye por ese código.
- **Ajuste ligero del modelo de lenguaje (decisión del 19 oct):** se usa solo el **texto** seudonimizado de nuestra transcripción de una sesión, con las preguntas anotadas a mano por Ivette. Nunca se usan audio, vídeo ni huellas de voz. Se comprueba con el Diario de Sesiones (texto oficial del Congreso) y se evalúa con una sesión distinta de la del ajuste. El modelo ajustado no se publica; en el repositorio solo va el código para reproducir el ajuste.
- **Pruebas de código:** datos sintéticos en `tests/`, separados de todo dato real.
- **Evaluación de calidad:** 3 sesiones del Congreso en esta entrega (6 a 10 como evolución futura), solo para medir. Referencia: el Diario de Sesiones (quién habla y en qué orden) y anotación manual de inicio y fin en 2 o 3 vídeos. Tamaño final: pendiente de Ivette.
- **Anotación de evaluación:** dos personas etiquetan de forma independiente 2 o 3 vídeos y una tercera resuelve desacuerdos.

## Modelos usados y datos con los que se entrenaron

Usamos modelos preentrenados de terceros tal cual, salvo el ajuste ligero de Qwen para M09. Esta tabla recoge, para cada uno, con qué datos lo entrenó su autor, según su ficha oficial (consultada el 2026-10-16). Los datos de entrenamiento son de terceros y no se redistribuyen en este repositorio.

| Modelo | Uso | Licencia | Datos con los que se entrenó (según su ficha) |
|---|---|---|---|
| `Systran/faster-whisper-large-v3` | Transcripción | MIT | Conversión a CTranslate2 (float16) de `openai/whisper-large-v3`, entrenado con 1 millón de horas de audio con etiquetado débil y 4 millones de horas de audio con pseudoetiquetas generadas con large-v2. La ficha avisa de rendimiento desigual según idioma, acento y dialecto, y de posible mayor tasa de error según género, raza y edad. |
| `Systran/faster-whisper-small` | Transcripción en pruebas en CPU | MIT | Pendiente de verificar. |
| `pyannote/segmentation-3.0` | Segmentación de voces | MIT (acceso restringido) | AISHELL, AliMeeting, AMI, AVA-AVD, DIHARD, Ego4D, MSDWild, REPERE y VoxConverse (conjuntos de entrenamiento). |
| `pyannote/speaker-diarization-3.1` | Diarización | MIT (acceso restringido) | Mismo pipeline que la versión 3.0, en PyTorch puro; se evalúa (no se entrena aquí) en AISHELL-4, AliMeeting, AMI, AVA-AVD, DIHARD 3, MSDWild, REPERE y VoxConverse. |
| `pyannote/wespeaker-voxceleb-resnet34-LM` | Embeddings de voz | CC-BY-4.0 | Pendiente de verificar. |
| MediaPipe / OpenCV (gestos) | Detección de manos | Pendiente de verificar | Pendiente de verificar. |
| Qwen3 (motor LLM opcional) | Decisión de roles | Pendiente de verificar | Pendiente de verificar. |

Implicaciones: los modelos de voz se entrenaron con corpus mayoritariamente de reuniones y debates y pueden rendir peor con ciertos acentos, idiomas o perfiles de voz. Por eso medimos el error por grupo y mantenemos la revisión humana.

## Anotación

Decisión del 16 oct: la IA asigna el género por pistas del lenguaje y una persona revisa solo los casos dudosos (sin pista, pistas contradictorias, gestos sin turno). Para la evaluación, dos personas etiquetan de forma independiente todas las voces de 2 o 3 vídeos (mujer / hombre / desconocido, rol, confianza) y los gestos de levantar la mano; una tercera decide los desacuerdos. Se publica el protocolo y el acuerdo entre anotadoras, nunca las etiquetas asociadas a personas identificables.

## Consideraciones éticas y legales

- Las voces y las imágenes son datos personales. No se tratan datos personales reales sin base jurídica y autorización expresa de la Organización.
- No se publican grabaciones, fragmentos ni transcripciones reales.
- El plan de puesta en producción exige consentimiento o base legal, información a las personas grabadas y evaluación RGPD y AI Act (informe pendiente, hito M7).
- Los resultados se presentan agregados y con sus márgenes de error.

## Limitaciones

- Con pocos vídeos, las conclusiones no se pueden generalizar.
- El género se toma de cómo nombra la institución a cada persona o de la revisión humana, y puede no coincidir con su identidad.
- La calidad del audio condiciona la transcripción y la diarización.

## Cómo reproducir sin datos reales

Ejecuta `make test`. Para probar el pipeline, usa un clip corto de una sesión del Congreso, guárdalo en `data/` (ignorado por git) y sigue el `README.md`.
