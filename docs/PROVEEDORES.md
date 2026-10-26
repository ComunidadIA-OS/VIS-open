# Proveedores y servicios que reciben datos

Qué servicios externos usa VIS Open, qué datos les llegan y para qué. Es la tabla de «subencargados» del proyecto: si se añade un servicio que trate datos, se añade una fila aquí **antes** de usarlo.

**Estado de la información:** lo que dice «Verificado» sale del código o de la documentación del repositorio. Lo que dice **Por verificar** son datos que aún no se han comprobado en la fuente oficial del proveedor (condiciones, retención, contrato) y que no se deben dar por ciertos en la presentación.

## Resumen

El análisis de las sesiones (audio, vídeo, separación de voces, gestos, métricas, panel) ocurre **en local o en la máquina del equipo en OVHcloud**. Solo salen de ahí, hacia una API, tres tipos de contenido:

1. El **audio de una orden hablada** al asistente de voz (segundos, solo tu voz diciendo la orden; nunca audio de las sesiones).
2. **Frases de la transcripción seudonimizada** para la métrica M09 (preguntas).
3. **Texto de la transcripción seudonimizada** para el resumen del contenido de una sesión (asistente de voz).

## Tabla

| Proveedor / servicio | Qué datos recibe | Para qué | Dónde y retención | Contrato / DPA | Estado |
|---|---|---|---|---|---|
| **OVHcloud AI Endpoints** (API compatible con OpenAI) | Audio de las órdenes de voz (`whisper-large-v3-turbo`, licencia MIT verificada el 21 oct 2026); texto seudonimizado (Qwen, Apache-2.0: M09 y resumen) | Transcribir las órdenes; clasificar preguntas; resumir | **Por verificar** (ubicación de los datos y si se guardan las peticiones; notas del equipo dicen que no, sin comprobar en la fuente) | **Por verificar** | Usado en pruebas y en el panel |
| **OVHcloud notebooks con GPU** (VM del equipo, 2 × V100S) | Vídeos, audio, transcripciones y resultados de las sesiones (`/workspace/equipo6`) | Ejecutar el análisis y el ajuste de Qwen | Espacio del equipo; **la Organización puede leerlo**: nunca claves ni tokens ahí | Condiciones del reto; **por verificar** | Usado |
| **Hugging Face** | Nada de las sesiones; solo descarga de modelos (con un token para los de acceso restringido, como pyannote) | Obtener modelos | Descarga en tiempo de ejecución | Condiciones de cada modelo | Usado |
| **GitHub** (organización de la Comunidad IA de Código Abierto) | Código, documentación, datos sintéticos y frases de prueba sintetizadas. **Ningún dato real** | Repositorio público el 29 oct; el vídeo explicativo va como adjunto de una Release | Según GitHub | Condiciones de GitHub | Usado |
| **Congreso de los Diputados** | Nada: es la **fuente** de los vídeos | Sesiones públicas, reutilizadas sin alterar y citando la fuente | Aviso legal del Congreso (`docs/FUENTE_CONGRESO.md`) | No aplica | Verificado |
| **Herramienta de desarrollo con IA** (Claude Code, Anthropic) | Código del repositorio y, si se ejecutan pruebas con datos locales, lo que salga por pantalla (puede incluir fragmentos de transcripción **seudonimizada**). No se envían audio ni vídeo | Escribir y probar el código | **Por verificar** según las condiciones de la cuenta del equipo | **Por verificar** | Usado. **Decisión pendiente:** si se acepta que vea texto seudonimizado en las pruebas o se evita (ver `docs/BORRADOR_PRODUCCION_RGPD_AIACT.md`) |

## Servicios que NO se usan

- Reconocimiento facial, ni propio ni de terceros.
- APIs de pago obligatorias: todo funciona con modelos abiertos; Qwen puede servirse desde un servidor propio compatible con OpenAI.
- La voz de síntesis de OVH (NVIDIA Riva) y otras voces en la nube: la voz del asistente es la del navegador, en local.
- Servicios de analítica o de publicidad en el panel: no hay estadísticas de uso ni recursos externos.

## Herramientas usadas fuera del sistema

No forman parte de VIS Open ni reciben datos del sistema; se indican por transparencia.

- **ElevenLabs** (síntesis de voz): solo para la **voz en off del vídeo explicativo** (26 oct 2026). Recibió únicamente el texto del guion y tres frases de ejemplo de la demo del asistente; ningún dato de las sesiones (ni audio, ni vídeo, ni transcripciones). El vídeo lo indica al final: «Voz generada con IA (ElevenLabs)».

## Cómo se actualiza

1. Si añades un servicio que reciba datos, escribe su fila aquí en la misma PR.
2. Si algo pasa de **Por verificar** a verificado, cita la fuente y la fecha.
3. Cualquier incidente con datos de un proveedor se trata como problema de seguridad (`SECURITY.md`).
