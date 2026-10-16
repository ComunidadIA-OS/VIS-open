# MEMORY.md · Memoria del proyecto

Hechos y decisiones que una sesión nueva no debe volver a preguntar. Una línea por hecho; actualiza en vez de duplicar. Sin secretos.

## Proyecto
- Reto "Mujeres por la IA Abierta" (SEDIA / Comunidad IA de Código Abierto). Bases: https://github.com/ComunidadIA-OS/Reto-de-Mujeres-por-la-IA-abierta
- Entrega oficial 30 oct 2026 08:00; presentación presencial 4 nov; el equipo cierra el 28 oct.
- Contacto del reto: comunidad.ia.os@digital.gob.es; mentores en Discord #reto-mujeres-ia-abierta. Sesión de ética de mentores: 16 oct.
- Términos y condiciones (docs/terminos-y-condiciones.pdf) no visibles en el repo del reto: pedirlos y leerlos.

## Equipo
- Sabrina (dirección, arquitectura, pipeline IA, infra, RGPD/AI Act), Ivette (métricas y validación, 2 h/día), Veru (datos, ética y género, dashboard, landing). Trabajo en remoto.
- Nadie es especialista en ML/audio: solo modelos maduros, sin entrenar.

## Documentos
- Propuesta de arquitectura: https://claude.ai/code/artifact/2db12001-92f4-4151-881f-a5c5c038c74a
- PRD: https://claude.ai/code/artifact/646d3e87-9345-42e2-9636-42beac3209aa
- Presentación del plan: https://claude.ai/artifact/B6QaA9ZNPNFEpiXrmPV1xN

## Decisiones tomadas / propuestas
- MVP: audio de debates en vídeo, sin análisis de imagen. Pendiente de aprobación del equipo.
- Género nunca inferido (declarado > registro público > anotación de 2 personas > desconocido).
- Jev: no usar (API alojada, sin pesos abiertos). Kev: experimental (Apache 2.0, solo inglés). `nimble` sí (Apache 2.0); `nimble-v3` no (CC BY-NC 4.0). Laya (Apache 2.0, multilingüe) como opción.
- Sin LangChain; `DecisionEngine` propio, `RulesEngine` por defecto.
- Licencia del repo propuesta: Apache 2.0.

## Pendiente
- Ivette: definiciones y umbrales de las 13 métricas y libro de códigos.
- Verificar licencias de FFmpeg, faster-whisper, WhisperX, pandas y Streamlit (anotadas de memoria).
- Copiar el archivo de licencia de `nimble` a `THIRD_PARTY_LICENSES.md`.
- Probar la V100S el día 2. Pedir token de Hugging Face (pyannote, modelo restringido).
- Solicitar acceso a la organización GitHub de la Comunidad IA.
- Aprobación de Sabrina para arrancar M1.

## Calendario (oct 2026)
M0 15–16 · M1 16–17 · M2 17–22 · M3 18–22 · M5 18–23 · M4 21–23 · M6 23 (núcleo funcionando) · M7 22–27 · M8 26–28.
