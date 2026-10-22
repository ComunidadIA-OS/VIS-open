"""Datos abiertos de composición de la cámara (§4 bis de `docs/metricas.md`).

Descarga y cachea los CSV de https://www.congreso.es/es/opendata/diputados en
`data/externos/congreso/` (fuera del repositorio, como los vídeos). Los nombres llevan marca de
tiempo, así que se localizan en la página y, si el fichero ya está descargado, no se vuelve a
bajar. Cada descarga queda registrada con su fecha y su sha256 en `descargas.csv`.

Uso: python -m sources.diputados [--destino DIR] [--legislaturas 12 14] [--manifest CSV]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

PAGINA = "https://www.congreso.es/es/opendata/diputados"
BASE = "https://www.congreso.es/webpublica/opendata/diputados/"
ALLOWED_HOST = "www.congreso.es"
USER_AGENT = "VIS-open/1.0 (docencia; datos abiertos del Congreso)"

LISTAS = {
    "diputadas": "Diputadas__*.csv",
    "diputados": "Diput__*.csv",
    "activos": "DiputadosActivos__*.csv",
    "baja": "DiputadosDeBaja__*.csv",
}
LEGISLATURA = re.compile(r"^odsDiputados(\d{2})__(\d+)\.csv$")
FIJOS = {
    "Diputadas": "diputadas",
    "Diput": "diputados",
    "DiputadosActivos": "activos",
    "DiputadosDeBaja": "baja",
}
_REGISTRO = "descargas.csv"
_REGISTRO_COLUMNAS = ["fichero", "pagina", "url", "fecha_descarga", "sha256"]


class DiputadosError(RuntimeError):
    """No se pueden obtener los datos: se avisa con qué falta y cómo arreglarlo."""


def _nombre(href: str) -> str:
    return unquote(href).rstrip("/").rsplit("/", 1)[-1]


def candidatos(html: str) -> dict[str, list[tuple[str, str]]]:
    """clave → [(marca de tiempo, URL)] de los CSV enlazados en la página."""
    out: dict[str, list[tuple[str, str]]] = {}
    for href in re.findall(r'href="([^"]+?\.csv)"', html):
        nombre = _nombre(href)
        leg = LEGISLATURA.match(nombre)
        if leg:
            clave, marca = f"leg{leg.group(1)}", leg.group(2)
        else:
            partes = nombre.split("__")
            if len(partes) != 2 or partes[0] not in FIJOS:
                continue
            clave, marca = FIJOS[partes[0]], partes[1].removesuffix(".csv")
        out.setdefault(clave, []).append((marca, urljoin(BASE, nombre)))
    return out


def enlaces(html: str) -> dict[str, str]:
    """clave → URL del fichero más reciente de cada tipo (la marca de tiempo cambia)."""
    return {clave: max(v)[1] for clave, v in candidatos(html).items()}


def _valida(url: str) -> None:
    parts = urlparse(url)
    if parts.scheme != "https" or parts.hostname != ALLOWED_HOST:
        raise DiputadosError(f"URL fuera del Congreso: {url}")
    if not parts.path.startswith("/webpublica/opendata/diputados/"):
        raise DiputadosError(f"URL fuera de la carpeta de datos abiertos: {url}")


def _abrir(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as fh:  # noqa: S310 (URL validada)
        return fh.read()


def _texto(data: bytes) -> str:
    return data.decode("utf-8-sig", errors="replace")


def _cache(destino: Path, clave: str) -> Path | None:
    """Fichero ya descargado de ese tipo, el más reciente si hay varios."""
    patron = LISTAS.get(clave) or f"odsDiputados{clave.removeprefix('leg')}__*.csv"
    encontrados = sorted(destino.glob(patron))
    return encontrados[-1] if encontrados else None


def _registra(destino: Path, fichero: Path, url: str, ahora: date) -> None:
    ruta = destino / _REGISTRO
    nuevo = not ruta.is_file()
    with ruta.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_REGISTRO_COLUMNAS)
        if nuevo:
            writer.writeheader()
        writer.writerow(
            {
                "fichero": fichero.name,
                "pagina": PAGINA,
                "url": url,
                "fecha_descarga": ahora.isoformat(),
                "sha256": hashlib.sha256(fichero.read_bytes()).hexdigest(),
            }
        )


def _registradas(destino: Path) -> set[str]:
    ruta = destino / _REGISTRO
    if not ruta.is_file():
        return set()
    with ruta.open(newline="", encoding="utf-8") as fh:
        return {r["fichero"] for r in csv.DictReader(fh)}


def _registra_faltantes(destino: Path, rutas: dict[str, Path], ahora: date) -> None:
    """Deja constancia también de los ficheros que ya estaban (descargados a mano)."""
    vistas = _registradas(destino)
    for fichero in rutas.values():
        if fichero.name not in vistas:
            _registra(destino, fichero, BASE + fichero.name, ahora)


def descargar(
    destino: Path,
    legislaturas: list[int],
    *,
    abrir=_abrir,
    ahora: date | None = None,
) -> dict[str, Path]:
    """Asegura los CSV en `destino` y devuelve clave → ruta; avisa si falta alguna lista.

    Las legislaturas sin `odsDiputadosNN` (la actual) se omiten: se usan Activos + DeBaja.
    Si la página cambia de formato se avisa con lo que falta y se usan los ficheros ya
    descargados; esos ficheros también se pueden dejar a mano en `destino`.
    """
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    claves = list(LISTAS) + [f"leg{n:02d}" for n in legislaturas]
    ahora = ahora or date.today()
    rutas = {k: p for k in claves if (p := _cache(destino, k))}
    if all(k in rutas for k in claves):
        _registra_faltantes(destino, rutas, ahora)
        return rutas

    try:
        links = enlaces(_texto(abrir(PAGINA)))
    except (OSError, DiputadosError) as exc:
        faltan = [k for k in LISTAS if k not in rutas]
        if faltan:
            raise DiputadosError(
                f"no se pudo leer {PAGINA} ({exc}) y faltan {faltan}; coloca los CSV a mano "
                f"en {destino}"
            ) from exc
        _registra_faltantes(destino, rutas, ahora)
        return rutas

    for clave in claves:
        if clave in rutas:
            continue
        url = links.get(clave)
        if url is None:
            if clave in LISTAS:
                raise DiputadosError(
                    f"la página {PAGINA} no enlaza ningún CSV de {clave}; deja el fichero a "
                    f"mano en {destino} o revisa la página"
                )
            continue  # la legislatura actual no tiene fichero propio
        _valida(url)
        fichero = destino / _nombre(url)
        fichero.write_bytes(abrir(url))
        _registra(destino, fichero, url, ahora)
        rutas[clave] = fichero
    _registra_faltantes(destino, rutas, ahora)
    return rutas


def legislaturas_del_manifiesto(path: Path) -> list[int]:
    """Números de legislatura de las sesiones del manifiesto (de `url_origen`)."""
    if not Path(path).is_file():
        return []
    with Path(path).open(newline="", encoding="utf-8") as fh:
        urls = [r.get("url_origen") or "" for r in csv.DictReader(fh)]
    nums = {
        int(m.group(1))
        for url in urls
        if (m := re.search(r"[?&]idLegislaturaElegida=(\d+)", url))
    }
    return sorted(nums)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destino", type=Path, default=Path("data/externos/congreso"))
    parser.add_argument("--legislaturas", type=int, nargs="*", default=None)
    parser.add_argument("--manifest", type=Path, default=Path("data/manifiesto.csv"))
    args = parser.parse_args(argv)

    legislaturas = args.legislaturas
    if legislaturas is None:
        legislaturas = legislaturas_del_manifiesto(args.manifest)
        if not legislaturas:
            raise SystemExit(
                f"no hay legislaturas en {args.manifest}; pásalas con --legislaturas 15 14 12"
            )
    rutas = descargar(args.destino, legislaturas)
    for clave, ruta in sorted(rutas.items()):
        print(f"{clave:10} {ruta} ({ruta.stat().st_size} bytes)")
    if not any(k.startswith("leg") for k in rutas):
        print("aviso: sin ficheros odsDiputadosNN; se usan Activos + DeBaja para la actual")


if __name__ == "__main__":
    main()
