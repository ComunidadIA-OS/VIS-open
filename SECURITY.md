# Política de seguridad

VIS Open analiza debates en vídeo y trabaja con datos sensibles. Tomamos en serio cualquier fallo que pueda exponer datos personales, credenciales o resultados manipulados.

## Cómo comunicar una vulnerabilidad

No abras una issue pública con los detalles. Usa una de estas vías:

1. **Preferida:** el aviso privado de seguridad de GitHub (pestaña *Security* del repositorio, "Report a vulnerability"), cuando el repo esté publicado.
2. Un correo a **ivetoak@gmail.com** con el asunto "Seguridad VIS Open".

Incluye qué has encontrado, cómo reproducirlo (con datos sintéticos) y qué impacto crees que tiene. Intentaremos acusar recibo en 7 días y te avisaremos cuando esté corregido. Es un proyecto de hackathon: no hay garantía de plazos.

## Qué nos interesa especialmente

- Credenciales o tokens publicados por error (OVHcloud, Hugging Face u otros), en el código, el historial de git, issues o PRs.
- Audio, vídeo, transcripciones reales o datos personales dentro del repositorio.
- Entradas que manipulen al motor de decisión basado en LLM (inyección de prompts) o que alteren las métricas.
- Dependencias con vulnerabilidades conocidas o con licencia incompatible.
- Cualquier camino por el que el sistema infiera el género a partir de la cara o la voz, o use reconocimiento facial: va contra las reglas del proyecto.

## Si encuentras un secreto o un dato real en el repo

1. Avisa por las vías de arriba, sin reproducirlo en un comentario público.
2. El equipo revocará y rotará la credencial de inmediato y retirará el dato, incluido el historial de git si hace falta.

## Versiones con soporte

Solo la rama `main`. El proyecto no tiene versiones publicadas todavía.

## Buenas prácticas del proyecto

- Los secretos viven en `.env`, que está ignorado por git. `.env.example` no lleva valores reales.
- Los PDF, DOCX y datos del reto no se suben (ver `.gitignore`).
- Los tests usan solo datos sintéticos.
- Cada dependencia queda registrada en `THIRD_PARTY_LICENSES.md`.
