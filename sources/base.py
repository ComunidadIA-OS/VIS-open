"""Interfaz intercambiable de fuentes de vídeo (RF-19).

Cada fuente (Congreso, Senado, Parlamento Europeo, subida de fichero...) sabe describir un
vídeo (URL o fichero local) como fila del manifiesto y, si se permite, descargarlo.
Una fuente nunca modifica el vídeo: lo guarda tal cual.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class DownloadDisabled(RuntimeError):
    """La descarga automática está desactivada (AUTO_DOWNLOAD=false) o sin implementar."""


class VideoSource(ABC):
    name: str

    @abstractmethod
    def manifest_row(
        self, ref: str | None = None, file: Path | None = None, **fields: str
    ) -> dict[str, str]:
        """Fila del manifiesto con lo que se pueda deducir de `ref` (URL) y/o del `file` local.

        Los campos que solo una persona puede decidir (licencia verificada, quién descargó,
        tramo...) quedan vacíos o en `pendiente`; el validador del manifiesto los exige.
        """

    @abstractmethod
    def download(self, ref: str, dest_dir: Path) -> Path:
        """Descarga el vídeo sin alterarlo. Puede lanzar `DownloadDisabled`."""
