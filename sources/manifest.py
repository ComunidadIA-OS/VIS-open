"""Manifiesto de vídeos (docs/BANCO_VIDEOS.md §5): una fila por vídeo.

Un vídeo no se analiza hasta que su fila esté completa, con la licencia verificada y sin uso
para entrenamiento. El vídeo nunca se modifica: la huella sha256 permite comprobarlo.
"""

from __future__ import annotations

import csv
import hashlib
import re
from collections.abc import Mapping
from pathlib import Path

COLUMNS = [
    "video_id", "titulo", "fuente", "url_origen", "fecha_evento", "fecha_descarga",
    "descargado_por", "licencia", "url_licencia", "atribucion", "condiciones",
    "licencia_verificada", "formato", "idioma", "tramo_inicio", "tramo_fin", "duracion_s",
    "personas_publicas", "base_legal", "ref_consentimiento", "categorias_especiales", "uso",
    "uso_entrenamiento", "sha256", "ruta_drive", "fecha_borrado", "anotadoras", "notas",
    "tipo_sesion",
]  # fmt: skip
# Solo se exigen cuando aplican.
OPTIONAL = {"ref_consentimiento", "anotadoras", "notas", "tipo_sesion"}
# Columnas añadidas después: un manifiesto anterior sin ellas se sigue leyendo.
NEWER = {"tipo_sesion"}
REQUIRED = [c for c in COLUMNS if c not in OPTIONAL]

FUENTES = {
    "congreso", "parlamento_europeo", "wikimedia_commons", "organizacion", "propia", "sintetico",
}  # fmt: skip
FORMATOS = {"debate", "entrevista", "mesa_redonda", "comparecencia", "sintetico"}
BASES_LEGALES = {"interes_legitimo", "consentimiento", "no_aplica"}
USOS = {"evaluacion", "demo", "test"}
# Solo «control» (sesión de control al Gobierno) tiene las métricas de preguntas.
TIPOS_SESION = {"control", "pleno", "comision", "diputacion_permanente"}

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME = re.compile(r"^\d{2}:[0-5]\d:[0-5]\d$")
_SHA = re.compile(r"^[0-9a-f]{64}$")


class ManifestError(RuntimeError):
    """El vídeo no puede analizarse: falta o está mal su fila del manifiesto."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def check_row(row: Mapping[str, str | None]) -> list[str]:
    """Lista de problemas de una fila (vacía = fila válida)."""
    get = lambda k: (row.get(k) or "").strip()  # noqa: E731
    problems = [f"falta el campo obligatorio '{c}'" for c in REQUIRED if not get(c)]

    vid = get("video_id")
    if vid.upper().startswith("EJEMPLO"):
        problems.append("es la fila de ejemplo de la plantilla: bórrala y rellena la tuya")
    if get("licencia_verificada") and get("licencia_verificada") != "si":
        problems.append("licencia_verificada debe ser 'si' (alguien tiene que verificarla)")
    if get("uso_entrenamiento") and get("uso_entrenamiento") != "no":
        problems.append("uso_entrenamiento debe ser siempre 'no'")
    for col, valid in (
        ("fuente", FUENTES),
        ("formato", FORMATOS),
        ("base_legal", BASES_LEGALES),
        ("tipo_sesion", TIPOS_SESION),
    ):
        if get(col) and get(col) not in valid:
            problems.append(f"{col}='{get(col)}' no es válido; admitidos: {sorted(valid)}")
    if get("uso") and not set(get("uso").split(";")) <= USOS:
        problems.append(f"uso='{get('uso')}' no es válido; admitidos: {sorted(USOS)} (con ';')")
    for col in ("fecha_evento", "fecha_descarga", "fecha_borrado"):
        if get(col) and not _DATE.match(get(col)):
            problems.append(f"{col}='{get(col)}' debe tener formato AAAA-MM-DD")
    for col in ("tramo_inicio", "tramo_fin"):
        if get(col) and not _TIME.match(get(col)):
            problems.append(f"{col}='{get(col)}' debe tener formato hh:mm:ss")
    if get("sha256") and not _SHA.match(get("sha256")):
        problems.append("sha256 debe ser una huella de 64 caracteres hexadecimales")
    if get("duracion_s"):
        try:
            if float(get("duracion_s")) <= 0:
                raise ValueError
        except ValueError:
            problems.append("duracion_s debe ser un número de segundos mayor que 0")
    if get("base_legal") == "consentimiento" and not get("ref_consentimiento"):
        problems.append("base_legal=consentimiento exige ref_consentimiento")
    return problems


def read_manifest(path: Path) -> dict[str, dict[str, str]]:
    path = Path(path)
    if not path.is_file():
        raise ManifestError(f"no existe el manifiesto {path}; créalo a partir de la plantilla")
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or []) and c not in NEWER]
        if missing:
            raise ManifestError(f"al manifiesto le faltan columnas: {missing}")
        return {r["video_id"]: r for r in reader if r.get("video_id")}


def parse_hms(value: str) -> float:
    """«hh:mm:ss» (o «hh:mm:ss.s») a segundos."""
    h, m, s = value.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def tramo_s(row: Mapping[str, str]) -> tuple[float, float | None]:
    """(inicio, fin) en segundos del tramo que se analiza; (0, None) = el vídeo entero."""
    start = parse_hms(row["tramo_inicio"]) if row.get("tramo_inicio") else 0.0
    end = parse_hms(row["tramo_fin"]) if row.get("tramo_fin") else None
    if end is not None and end <= start:
        raise ManifestError("tramo_fin debe ser posterior a tramo_inicio")
    return start, end


def require_ready(video: Path, manifest: Path) -> dict[str, str]:
    """Devuelve la fila del vídeo o lanza ManifestError explicando qué falta.

    El `video_id` es el nombre del fichero sin extensión. Comprueba también que el fichero
    sigue siendo el original (sha256), porque el vídeo no se puede haber alterado.
    """
    video = Path(video)
    rows = read_manifest(manifest)
    row = rows.get(video.stem)
    if row is None:
        raise ManifestError(
            f"el vídeo '{video.stem}' no tiene fila en {manifest}: añádela antes de analizarlo"
        )
    problems = check_row(row)
    if not problems and video.is_file() and sha256_file(video) != row["sha256"]:
        problems.append(
            "el sha256 del fichero no coincide con el del manifiesto (¿se ha alterado?)"
        )
    if problems:
        detail = "\n  - ".join(problems)
        raise ManifestError(
            f"no se analiza '{video.stem}': fila incompleta o inválida:\n  - {detail}"
        )
    return row


def append_row(row: Mapping[str, str], path: Path) -> None:
    """Añade una fila al manifiesto; crea el fichero con cabecera si no existe."""
    path = Path(path)
    new = not path.is_file()
    columns = COLUMNS
    if not new:  # se respeta la cabecera que ya tiene (puede no tener las columnas nuevas)
        with path.open(newline="", encoding="utf-8") as fh:
            columns = next(csv.reader(fh), None) or COLUMNS
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        if new:
            writer.writeheader()
        writer.writerow({c: row.get(c, "") for c in columns})
