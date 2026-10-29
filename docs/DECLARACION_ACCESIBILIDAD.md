# Declaración de accesibilidad

Qué hace VIS Open para que el panel lo pueda usar cualquier persona, qué no cumple todavía y cómo se ha comprobado. Complementa `docs/ACCESIBILIDAD.md` (descripción técnica del asistente de voz).

**Fecha de esta declaración:** 21 de octubre de 2026. **Alcance:** el panel de Streamlit (`dashboard/`), incluido el asistente de voz y el modo manos libres.

## Estado de conformidad

**No se ha hecho una auditoría formal de accesibilidad.** El objetivo de diseño es el nivel AA de las pautas WCAG 2.2 y, en un despliegue real, la norma EN 301 549. Hoy el panel se considera **parcialmente conforme**: cumple los puntos de la lista de abajo y tiene las carencias conocidas de la sección siguiente.

## Qué incluye

| Necesidad | Qué hace el panel |
|---|---|
| Sordera o dificultad auditiva | Subtítulos (botón «CC» y descarga `.vtt`) en el vídeo de la sesión y en los cortes de validación; todo lo que dice el asistente se escribe en una ventana. Son automáticos y pueden tener errores. |
| Ceguera o baja visión | Asistente de voz que obedece órdenes habladas y contesta en voz alta; modo manos libres con pitidos de aviso; letra grande (ningún texto baja de 20 px) y alto contraste; página en español para el lector de pantalla. |
| Lector de pantalla | `lang="es"`; encabezados en todas las secciones; cada gráfico tiene una descripción en español con sus cifras; vídeos, ventana del asistente y botones con nombre; lo que dice el asistente se anuncia en una región `aria-live`. |
| No poder usar el ratón | Todo se puede hacer por voz o escribiendo la orden; el botón del asistente y el modo manos libres se activan con el teclado (Enter); foco visible. |
| Sensibilidad al movimiento | Con «reducir movimiento» activado en el sistema, el avatar del asistente no se anima. |
| Cansancio o dificultad para leer | Respuestas del asistente cortas; las explicaciones se piden con voz («explícame los resultados»). |

## Contenido que todavía NO es accesible

- **No se ha probado con un lector de pantalla real** (NVDA, JAWS, VoiceOver): la revisión se hizo con el árbol de accesibilidad del navegador. Puede haber problemas de orden de lectura o de foco en la ventana del asistente.
- **Tablas grandes** (voces, intervenciones): se leen mal con lector de pantalla. Alternativa: la transcripción en CSV.
- **El vídeo original del Congreso** no tiene audiodescripción ni interpretación en lengua de signos: se muestra sin alterar. Los subtítulos son nuestros, automáticos.
- **Contraste y tamaños** no se han medido con una herramienta formal.
- **El asistente de voz** funciona solo en español y necesita un navegador con micrófono, Web Audio y WebGL (Chrome, Edge). Con mucho ruido de fondo se equivoca más. El avatar es solo visual; no sustituye al texto.
- **Palabras muy cortas en manos libres:** un «sí» dicho rápido no llega. El detector de voz solo da por empezada una frase con al menos 0,22 s de voz seguida y descarta lo que dure menos de 0,4 s, para que un golpe de tecla, un clic o un ruido corto no se tomen por una orden. Mejor palabras de dos sílabas o más: «sigue», «para», «stop». Hablar rápido también hace que Whisper confunda palabras («régimen» por «resumen»); se corrigen los errores conocidos, pero conviene hablar a ritmo normal.
- **Con altavoces, el micrófono no oye a la persona mientras el asistente habla** (oye su voz). Por eso las respuestas largas se leen por partes, con una pausa en la que «para» o «stop» lo detienen. Con auriculares, «para» también corta a mitad de frase.
- **El modo manos libres no es para usarlo conduciendo:** las validaciones de género piden atención.

## Cómo se ha comprobado

Pruebas funcionales con el navegador (árbol de accesibilidad, descripciones de gráficos, nombres de elementos) y pruebas del asistente con audio sintetizado y con el micrófono de Sabrina. Sin personas usuarias con discapacidad ni auditoría externa: **pendiente**.

## Cómo informar de un problema

Abre una incidencia en el repositorio o sigue `CONTRIBUTING.md`. Indica el navegador, el lector de pantalla (si usas uno) y qué pasó.

## Qué no hacemos

VIS Open **no detecta ni registra la discapacidad de las personas que intervienen** en las sesiones: sería un dato de salud (categoría especial del RGPD) y no se puede inferir de la voz ni de la imagen. La accesibilidad aquí es del panel, no una métrica sobre las personas.
