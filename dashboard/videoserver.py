"""Sirve al reproductor del panel los vídeos originales de `data/raw` sin cargarlos en memoria.

`st.video` con un fichero lo lee entero en memoria: con una sesión de 3,6 GB da `MemoryError`.
Este servidor solo escucha en 127.0.0.1 (el propio equipo), solo entrega `<id>.mp4` de la carpeta
de vídeos y admite peticiones `Range`, así que el navegador pide solo los trozos que reproduce.
El fichero no se modifica.
"""

from __future__ import annotations

import http.server
import re
import threading
from pathlib import Path

_NAME = re.compile(r"^/([A-Za-z0-9_-]+\.mp4)$")
_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")
CHUNK = 1 << 20
_servers: dict[Path, tuple[str, int]] = {}
_lock = threading.Lock()


def _byte_range(header: str | None, size: int) -> tuple[int, int] | None:
    """(inicio, fin) incluidos de una cabecera Range; None si no hay o no se entiende."""
    m = _RANGE.match(header or "")
    if not m or not (m.group(1) or m.group(2)):
        return None
    if not m.group(1):  # «bytes=-N»: los N últimos
        return max(size - int(m.group(2)), 0), size - 1
    start = int(m.group(1))
    end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
    return start, end


class _Handler(http.server.BaseHTTPRequestHandler):
    root: Path

    def do_GET(self) -> None:  # noqa: N802 - nombre de la API de http.server
        self._serve(body=True)

    def do_HEAD(self) -> None:  # noqa: N802
        self._serve(body=False)

    def _serve(self, body: bool) -> None:
        m = _NAME.match(self.path.split("?")[0])
        path = self.root / m.group(1) if m else None
        if path is None or not path.is_file():
            self.send_error(404)
            return
        size = path.stat().st_size
        rng = _byte_range(self.headers.get("Range"), size)
        if rng is not None and (rng[0] >= size or rng[0] > rng[1]):
            self.send_error(416)
            return
        start, end = rng or (0, size - 1)
        self.send_response(206 if rng else 200)
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        if not body:
            return
        with path.open("rb") as fh:
            fh.seek(start)
            left = end - start + 1
            while left > 0 and (chunk := fh.read(min(CHUNK, left))):
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):  # el navegador saltó a otro punto
                    return
                left -= len(chunk)

    def log_message(self, *args) -> None:  # sin ruido en la consola del panel
        pass


def video_url(path: Path) -> str:
    """URL local para reproducir `path`; arranca el servidor de su carpeta la primera vez."""
    root = Path(path).parent.resolve()
    with _lock:
        if root not in _servers:
            handler = type("VideoHandler", (_Handler,), {"root": root})
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            _servers[root] = server.server_address[:2]
        host, port = _servers[root]
    return f"http://{host}:{port}/{Path(path).name}"
