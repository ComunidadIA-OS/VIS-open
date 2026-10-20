---
name: revisar-antes-de-publicar
description: Revisión de seguridad de VIS Open antes de subir una rama o de hacer público el repositorio (secretos, datos, ficheros grandes, nombres, licencias, tests). Úsala antes de cualquier push a la organización o de cambiar la visibilidad.
---

# Revisar antes de publicar

No hagas push ni cambies la visibilidad si algún punto falla: informa de qué fichero o commit y espera instrucciones. No reescribas el historial sin permiso.

1. `git status -sb`: sin cambios sin commit; rama correcta.
2. **Secretos** (ficheros e historial): `gitleaks detect --source . --log-opts="--all"` si está instalado; si no, `git grep -nIiE "hf_[A-Za-z0-9]{20,}|gho_|sk-[A-Za-z0-9]{20,}|BEGIN .*PRIVATE" $(git branch -r --format='%(refname:short)')`. `.env` no debe estar versionado; solo `.env.example` con valores vacíos.
3. **Ficheros prohibidos** en árbol e historial: `git log --all --name-only --format="" | sort -u | rg -i "\.(mp4|mkv|webm|wav|mp3|m4a|pdf|docx|zip)$|PENDIENTE_"`. `data/` debe estar en `.gitignore`.
4. **Ficheros grandes:** nada de más de 5 MB (`git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | awk '$3 > 5000000'`).
5. **Nombres reales:** `rg -n -i "señora|señor|diputad"` solo debe encontrar tratamientos genéricos, reglas o casos inventados («Persona N», «Luna Ortega» sintético). Ningún dato real en `evaluation/synthetic/` ni en tests.
6. **Licencias:** existen `LICENSE` (Apache-2.0) y `THIRD_PARTY_LICENSES.md`, y toda dependencia nueva está anotada con su licencia verificada en la fuente.
7. `python -m ruff check .` y `python -m pytest -q` en verde (en Windows no hay `make`).
8. Informa del remoto usado y del resultado de cada punto. El PR lo abre y lo fusiona una persona.

Poner el repositorio en público es un paso aparte, solo el 29 de octubre y solo lo hace Sabrina (Settings → General → Danger Zone → Change visibility).
