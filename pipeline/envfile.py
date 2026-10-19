"""Lectura mínima del fichero `.env` (sin dependencias). Nunca pisa variables ya definidas."""

from __future__ import annotations

import os
import re
from pathlib import Path


def parse_env(text: str) -> dict[str, str]:
    """`CLAVE=valor`; ignora líneas vacías y comentarios (`#`, también tras el valor)."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = re.split(r"(?:^|\s)#", value.strip(), maxsplit=1)[0].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key.strip()] = value
    return out


def load_dotenv(path: Path | str = ".env") -> list[str]:
    """Carga `path` en `os.environ` (lo ya definido manda). Devuelve las claves nuevas."""
    path = Path(path)
    if not path.is_file():
        return []
    loaded = []
    for key, value in parse_env(path.read_text(encoding="utf-8")).items():
        if key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded
