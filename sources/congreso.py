"""Adaptador del Congreso de los Diputados.

Acepta la URL de una sesión del archivo audiovisual
(`app.congreso.es/AudiovisualCongreso/audiovisualdetalledisponible?codOrgano=..&codSesion=..
&idLegislaturaElegida=..&fechaSesion=..`) y/o un fichero ya descargado, y rellena la fila del
manifiesto. No toca la red: la descarga automática está desactivada (AUTO_DOWNLOAD=false)
hasta comprobar el robots.txt de app.congreso.es.

Uso: python -m sources.congreso --url URL [--file video.mp4] [--manifest data/manifiesto.csv]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sources.base import DownloadDisabled, VideoSource
from sources.manifest import append_row, check_row, sha256_file

ALLOWED_HOSTS = {"app.congreso.es"}
LICENSE_URL = "https://www.congreso.es/es/cem/aviso-legal"
DATE_FORMATS = ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d")


@dataclass(frozen=True)
class SessionRef:
    cod_organo: str
    cod_sesion: str
    legislatura: str
    fecha_sesion: str  # tal como viene en la URL

    @property
    def event_date(self) -> str:
        """Fecha ISO (AAAA-MM-DD) o '' si el formato de la URL no se reconoce."""
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(self.fecha_sesion, fmt).date().isoformat()
            except ValueError:
                continue
        return ""


def parse_session_url(url: str) -> SessionRef:
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or parts.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"URL no válida: se espera una URL de {sorted(ALLOWED_HOSTS)}")
    q = {k.lower(): v[0] for k, v in parse_qs(parts.query).items() if v}
    wanted = {
        "codorgano": "codOrgano",
        "codsesion": "codSesion",
        "idlegislaturaelegida": "idLegislaturaElegida",
        "fechasesion": "fechaSesion",
    }
    missing = [name for key, name in wanted.items() if not q.get(key)]
    if missing:
        raise ValueError(f"a la URL le faltan parámetros: {missing}")
    return SessionRef(
        cod_organo=q["codorgano"],
        cod_sesion=q["codsesion"],
        legislatura=q["idlegislaturaelegida"],
        fecha_sesion=q["fechasesion"],
    )


def probe_duration_s(video: Path) -> float | None:
    """Duración con ffprobe; None si ffprobe no está disponible."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        return None
    out = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(video)],
        capture_output=True, text=True,
    )  # fmt: skip
    try:
        return round(float(out.stdout.strip()), 3)
    except ValueError:
        return None


class CongresoSource(VideoSource):
    name = "congreso"

    def manifest_row(
        self, ref: str | None = None, file: Path | None = None, **fields: str
    ) -> dict[str, str]:
        if ref is None and file is None:
            raise ValueError("indica una URL de sesión, un fichero local o ambos")
        row = {
            "fuente": "congreso",
            "licencia": "Aviso legal Congreso",
            "url_licencia": LICENSE_URL,
            "atribucion": "Fuente: Congreso de los Diputados",
            "condiciones": (
                "No alterar el contenido; citar fuente y fecha de última actualización; "
                "no usar grabaciones de interpretación simultánea"
            ),
            "licencia_verificada": "pendiente",
            "formato": "debate",
            "idioma": "es",
            "personas_publicas": "si",
            "base_legal": "interes_legitimo",
            "categorias_especiales": "opiniones políticas, manifiestamente públicas",
            "uso": "evaluacion",
            "uso_entrenamiento": "no",
        }
        if ref is not None:
            session = parse_session_url(ref)
            row.update(
                # 400 = Pleno (si es la sesión de control, una persona pone «control»)
                tipo_sesion={"400": "pleno", "500": "diputacion_permanente"}.get(
                    session.cod_organo, "comision"
                ),
                url_origen=ref,
                fecha_evento=session.event_date,
                titulo=(
                    f"Congreso, sesión {session.cod_sesion} "
                    f"(órgano {session.cod_organo}, legislatura {session.legislatura})"
                ),
            )
        if file is not None:
            file = Path(file)
            if not file.is_file():
                raise FileNotFoundError(file)
            row["video_id"] = file.stem
            row["sha256"] = sha256_file(file)
            duration = probe_duration_s(file)
            if duration is not None:
                row["duracion_s"] = str(duration)
        row.update(fields)  # lo que decide una persona (quién descargó, tramo, licencia...)
        return row

    def download(self, ref: str, dest_dir: Path) -> Path:
        parse_session_url(ref)  # valida la URL aunque no se descargue
        if os.environ.get("AUTO_DOWNLOAD", "false").strip().lower() != "true":
            raise DownloadDisabled(
                "descarga automática desactivada (AUTO_DOWNLOAD=false): pendiente de comprobar "
                "el robots.txt de app.congreso.es. Descarga el vídeo a mano y pásalo con --file."
            )
        raise DownloadDisabled(
            "descarga automática sin implementar: tras confirmar que el Congreso la permite, "
            "este es el punto de entrada (guardar el fichero tal cual, sin recodificar)."
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--set", action="append", default=[], metavar="CAMPO=VALOR")
    args = parser.parse_args(argv)

    overrides = dict(item.split("=", 1) for item in args.set)
    row = CongresoSource().manifest_row(args.url, args.file, **overrides)
    manifest = args.manifest or Path(os.environ.get("DATA_DIR") or "data") / "manifiesto.csv"
    append_row(row, manifest)
    print(f"fila añadida a {manifest}")
    for problem in check_row(row):
        print(f"  pendiente: {problem}")


if __name__ == "__main__":
    main()
