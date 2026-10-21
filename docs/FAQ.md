# Preguntas frecuentes

Respuestas para este proyecto. Lo que depende de las bases del reto y no hemos podido confirmar está marcado como **por confirmar con la Organización** (comunidad.ia.os@digital.gob.es).

## ¿Usamos modelos de IA propietarios dentro de un proyecto open source?

No dependemos de ninguno. Por defecto el sistema funciona con modelos abiertos y reglas deterministas, sin ningún LLM. El motor de decisión opcional habla con cualquier API compatible con OpenAI, de modo que la solución es agnóstica del modelo, como piden las bases. No incluimos claves ni servicios de pago en el repositorio. Si alguien conecta un modelo propietario por su cuenta, es su elección y debe respetar la licencia de ese servicio. Si el reto lo permite como componente del proyecto: **por confirmar**.

## ¿Podemos usar Cursor, Claude Code u otros asistentes de IA?

Sí los usamos: parte del código y de la documentación se ha escrito con Claude Code, y las personas del equipo revisan, prueban y se responsabilizan de lo que se publica. Los commits hechos con ayuda de IA llevan el trailer `Co-Authored-By`. Que las bases lo permitan expresamente: **por confirmar**.

## ¿Se puede comercializar un proyecto open source?

La licencia Apache-2.0 del proyecto permite el uso comercial. Ojo con los componentes de terceros: cada uno mantiene su licencia (`THIRD_PARTY_LICENSES.md`); algunos modelos exigen atribución (CC-BY-4.0) o aceptar condiciones (pyannote), y no usamos nada de licencia no comercial. Además, tratar voces e imágenes reales exige base jurídica y evaluación RGPD y AI Act (ver `docs/RESPONSIBLE_USE.md`).

## ¿Tiene que estar todo el historial de commits del hackathon?

Conservamos el historial completo, sin aplastar ni reescribir commits, con mensajes descriptivos. Según las bases solo cuenta el código desarrollado entre el 14 y el 30 de octubre de 2026 a las 08:00; el nuestro empieza el 16 de octubre. Si la Organización exige algo más concreto sobre el historial: **por confirmar**.

## ¿Qué datos salen del equipo cuando uso el asistente de voz?

Solo tu voz diciendo una orden (a la API de transcripción) y, para el resumen o M09, fragmentos de transcripción **seudonimizada** (al modelo de lenguaje). Nunca audio ni vídeo de las sesiones. Detalle en `docs/PROVEEDORES.md`.

## ¿El asistente puede equivocarse o inventar cosas?

Sí. Las cifras las calcula siempre el código; el resumen del contenido lo hace un modelo, va marcado como IA y puede tener errores. Con ruido, el transcriptor puede inventar frases: se filtran, pero revisa lo que ves escrito en la ventana. Nada se guarda sin tu «confirmo».

## ¿El panel es accesible?

Parcialmente: subtítulos, asistente de voz, modo manos libres y lector de pantalla (página en español, gráficos descritos). No se ha auditado con personas usuarias ni con un lector real. Ver `docs/DECLARACION_ACCESIBILIDAD.md`.

## ¿VIS Open registra si alguien tiene una discapacidad?

No. Sería un dato de salud y no se puede inferir de la voz ni de la imagen. La accesibilidad es del panel, no una métrica sobre las personas.

