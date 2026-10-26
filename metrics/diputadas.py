"""Composición de la cámara para M04 c) (§4 bis de `docs/metricas.md`).

- Medida A: quién tenía escaño el día de la sesión (`FECHAALTA <= fecha < FECHABAJA`).
- Medida B: todas las personas que ocuparon escaño durante la legislatura.

El sexo se toma de una columna SEXO/GENERO o del tratamiento (Sra./Sr.) si existe. Los CSV del
Congreso no traen ninguna de las dos, así que se cruzan las listas oficiales `Diputadas`
(mujeres) y `Diput__` (todas las personas) por nombre normalizado. Quien no aparece en ninguna
lista queda como «desconocido» y se informa aparte: no se reparte entre mujeres y hombres.

Uso (tabla para la presentación): python -m metrics.diputadas [--data data]
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path

from contracts import GenderValue

W, M, UNKNOWN = GenderValue.WOMAN.value, GenderValue.MAN.value, GenderValue.UNKNOWN.value
EXPECTED_SEATS = 350  # §4 bis: control de calidad de la medida A
TOTALES_B = {15: 412, 14: 407, 12: 393}  # buscador oficial, consultado el 22/10/2026
FORMATOS_FECHA = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")
ROMANOS = (
    "", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
    "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX",
)  # fmt: skip
SEXOS = {
    "m": W, "mujer": W, "f": W, "femenino": W, "female": W, "sra": W,
    "h": M, "hombre": M, "masculino": M, "male": M, "sr": M, "varon": M, "v": M,
}  # fmt: skip
_COLUMNAS = {
    "nombre": ("nombre",),
    "apellidos": ("apellidos",),
    "alta": ("fechaalta", "fechainiciolegislatura"),
    "baja": ("fechabaja", "fechafinlegislatura"),
    "sexo": ("sexo", "genero"),
    "tratamiento": ("tratamiento",),
    "legislatura": ("legislatura",),
    "actual": ("legislaturaactual",),
}


class DatosCamara(RuntimeError):
    """Faltan los datos de la cámara o no se pueden interpretar."""


@dataclass(frozen=True)
class Conteo:
    total: int
    mujeres: int
    hombres: int
    desconocido: int
    porcentaje: float | None

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "mujeres": self.mujeres,
            "hombres": self.hombres,
            "desconocido": self.desconocido,
            "porcentaje": self.porcentaje,
        }


@dataclass(frozen=True)
class ReferenciaCamara:
    fecha: str
    legislatura: str
    fuente_a: str
    a: Conteo
    b: Conteo
    avisos: tuple[str, ...] = ()

    @property
    def diferencia_puntos(self) -> float | None:
        """% B − % A, en puntos (error de usar la legislatura completa)."""
        if self.a.porcentaje is None or self.b.porcentaje is None:
            return None
        return round(self.b.porcentaje - self.a.porcentaje, 2)

    def attrs(self) -> dict[str, float]:
        """Lo que M04 espera en `frame.attrs`; solo lo que superó los controles."""
        out = {}
        if self.a.porcentaje is not None:
            out["porcentaje_diputadas"] = self.a.porcentaje
        if self.b.porcentaje is not None:
            out["porcentaje_diputadas_b"] = self.b.porcentaje
        return out

    def resumen(self) -> dict:
        return {
            "fecha": self.fecha,
            "legislatura": self.legislatura,
            "fuente_a": self.fuente_a,
            "a": self.a.as_dict(),
            "b": self.b.as_dict(),
            "diferencia_puntos": self.diferencia_puntos,
            "avisos": list(self.avisos),
        }


def normalizar(texto: str) -> str:
    """Nombre comparable: sin acentos, minúsculas y sin puntuación."""
    sin = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^0-9a-z]+", " ", sin.lower()).split())


def clave_persona(nombre: str, apellidos: str = "") -> str:
    """«Apellidos, Nombre» y «Apellidos + Nombre» dan la misma clave."""
    if apellidos:
        return normalizar(f"{apellidos} {nombre}")
    cabeza, coma, cola = (nombre or "").partition(",")
    return normalizar(f"{cabeza} {cola}" if coma else nombre)


def numero_legislatura(valor: int | str) -> int:
    """«15», «XV», «Leg. XV» → 15."""
    if isinstance(valor, int):
        num = valor
    else:
        texto = str(valor).strip().upper().removeprefix("LEG.").strip().strip(".")
        if texto.isdigit():
            num = int(texto)
        elif texto in ROMANOS:
            num = ROMANOS.index(texto)
        else:
            num = 0
    if not 1 <= num <= 20:
        raise DatosCamara(f"legislatura no reconocida: {valor!r}")
    return num


def _romano(num: int) -> str:
    return ROMANOS[num]


def _fecha(texto: str | None) -> date | None:
    for fmt in FORMATOS_FECHA:
        try:
            return datetime.strptime((texto or "").strip(), fmt).date()
        except ValueError:
            continue
    return None


def _sexo(texto: str | None) -> str:
    sin = normalizar(texto or "")
    return SEXOS.get(sin, UNKNOWN)


def _leer_tabla(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    data = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            texto = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        texto = data.decode("utf-8", errors="replace")
    cabecera = texto.splitlines()[0] if texto else ""
    delim = ";" if cabecera.count(";") >= cabecera.count(",") else ","
    reader = csv.DictReader(io.StringIO(texto), delimiter=delim)
    return list(reader.fieldnames or []), list(reader)


def _columnas(cabecera: list[str]) -> dict[str, str | None]:
    mapa = {_limpia(c): c for c in cabecera if c}
    return {
        campo: next((mapa[a] for a in alias if a in mapa), None)
        for campo, alias in _COLUMNAS.items()
    }


def _limpia(texto: str) -> str:
    sin = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "".join(c for c in sin.lower() if c.isalnum())


def leer_personas(path: Path) -> list[dict]:
    """Filas con nombre, sexo (si el CSV lo trae) y fechas de alta y baja."""
    cabecera, filas = _leer_tabla(path)
    cols = _columnas(cabecera)
    if cols["nombre"] is None:
        raise DatosCamara(f"{Path(path).name} no tiene columna NOMBRE")
    out = []
    for fila in filas:
        nombre = fila.get(cols["nombre"]) or ""
        apellidos = fila.get(cols["apellidos"]) if cols["apellidos"] else ""
        clave = clave_persona(nombre, apellidos or "")
        if not clave:
            continue
        sexo = _sexo(fila.get(cols["sexo"])) if cols["sexo"] else UNKNOWN
        if sexo == UNKNOWN and cols["tratamiento"]:
            sexo = _sexo(fila.get(cols["tratamiento"]))
        out.append(
            {
                "clave": clave,
                "sexo": sexo,
                "alta": _fecha(fila.get(cols["alta"])) if cols["alta"] else None,
                "baja": _fecha(fila.get(cols["baja"])) if cols["baja"] else None,
            }
        )
    return out


def leer_lista(path: Path) -> tuple[dict[str, set[str]], int | None]:
    """Listas oficiales (`Diputadas`, `Diput__`): legislatura → claves, y la actual."""
    cabecera, filas = _leer_tabla(path)
    cols = _columnas(cabecera)
    if cols["nombre"] is None or cols["legislatura"] is None:
        raise DatosCamara(f"{Path(path).name} no tiene NOMBRE y LEGISLATURA")
    por_leg: dict[str, set[str]] = {}
    actual = None
    for fila in filas:
        roman = (
            str(fila.get(cols["legislatura"]) or "").strip().upper().removeprefix("LEG.").strip()
        )
        clave = clave_persona(fila.get(cols["nombre"]) or "", fila.get(cols["apellidos"]) or "")
        if not roman or not clave:
            continue
        por_leg.setdefault(roman, set()).add(clave)
        if cols["actual"] and str(fila.get(cols["actual"]) or "").strip().upper() in {
            "S", "SI", "SÍ", "YES", "Y",
        }:
            actual = numero_legislatura(roman)
    return por_leg, actual


def _cuenta(filas: list[dict], dia: date | None, sexo_por_clave: dict[str, str]) -> Conteo:
    personas: dict[str, dict] = {}
    for fila in filas:
        if dia is not None:
            if fila["alta"] and fila["alta"] > dia:
                continue
            if fila["baja"] and fila["baja"] <= dia:
                continue
        personas.setdefault(fila["clave"], fila)
    total = len(personas)
    mujeres = 0
    hombres = 0
    for clave, fila in personas.items():
        sexo = fila["sexo"] if fila["sexo"] != UNKNOWN else sexo_por_clave.get(clave, UNKNOWN)
        mujeres += sexo == W
        hombres += sexo == M
    return Conteo(total, mujeres, hombres, total - mujeres - hombres,
                  round(100 * mujeres / total, 2) if total else None)  # fmt: skip


def _cuenta_lista(mujeres: set[str], todas: set[str]) -> Conteo:
    total = len(todas)
    n_mujeres = len(mujeres & todas)
    return Conteo(total, n_mujeres, total - n_mujeres, 0,
                  round(100 * n_mujeres / total, 2) if total else None)  # fmt: skip


VACANTES_MIN = 340  # §4 bis: de 340 a 349 escaños ocupados vale, con aviso (vacantes ese día)


def _control(conteo: Conteo, esperado: int | None, etiqueta: str, avisos: list[str]) -> Conteo:
    if esperado is None or conteo.total == esperado:
        return conteo
    if esperado == EXPECTED_SEATS and VACANTES_MIN <= conteo.total < esperado:
        avisos.append(f"{conteo.total} escaños ocupados: hay vacantes ese día")
        return conteo  # el denominador es N: un escaño vacío no es una persona que pueda preguntar
    avisos.append(
        f"la medida {etiqueta} suma {conteo.total} (se esperaban {esperado}): no se usa "
        "hasta revisarlo"
    )
    return replace(conteo, porcentaje=None)


def _busca(carpeta: Path, patron: str) -> Path | None:
    encontrados = sorted(Path(carpeta).glob(patron))
    return encontrados[-1] if encontrados else None


def cargar(
    carpeta: Path,
    fecha: date | str,
    legislatura: int | str,
    *,
    esperado_a: int | None = EXPECTED_SEATS,
    esperado_b: int | None = None,
) -> ReferenciaCamara:
    """Medidas A y B de una sesión a partir de los CSV de `sources.diputados`."""
    carpeta = Path(carpeta)
    num = numero_legislatura(legislatura)
    roman = _romano(num)
    dia = fecha if isinstance(fecha, date) else date.fromisoformat(str(fecha))
    f_mujeres = _busca(carpeta, "Diputadas__*.csv")
    f_todos = _busca(carpeta, "Diput__*.csv")
    if f_mujeres is None or f_todos is None:
        raise DatosCamara(
            f"faltan las listas de diputadas/diputados en {carpeta}: "
            "ejecuta `python -m sources.diputados`"
        )
    mujeres_leg, actual = leer_lista(f_mujeres)
    todos_leg, _ = leer_lista(f_todos)
    mujeres = mujeres_leg.get(roman, set())
    todas = todos_leg.get(roman, set())
    if not todas:
        raise DatosCamara(f"la lista completa no tiene la legislatura {roman}")

    if num == actual:
        activos = _busca(carpeta, "DiputadosActivos__*.csv")
        baja = _busca(carpeta, "DiputadosDeBaja__*.csv")
        if activos is None or baja is None:
            raise DatosCamara(f"faltan Activos y DeBaja para la legislatura actual en {carpeta}")
        filas = leer_personas(activos) + leer_personas(baja)
        fuente = f"{activos.name} + {baja.name}"
    else:
        f_leg = _busca(carpeta, f"odsDiputados{num:02d}__*.csv")
        if f_leg is None:
            raise DatosCamara(f"falta odsDiputados{num:02d} en {carpeta}")
        filas, fuente = leer_personas(f_leg), f_leg.name

    sexo = {k: W for k in mujeres} | {k: M for k in todas - mujeres}
    avisos: list[str] = []
    a = _control(_cuenta(filas, dia, sexo), esperado_a, "A", avisos)
    b = _control(
        _cuenta_lista(mujeres, todas),
        esperado_b if esperado_b is not None else TOTALES_B.get(num),
        "B",
        avisos,
    )
    if a.desconocido:
        avisos.append(
            f"{a.desconocido} personas con escaño ese día no aparecen en las listas oficiales: "
            "su sexo queda como desconocido"
        )
    if sueltas := mujeres - todas:
        avisos.append(
            f"{len(sueltas)} diputadas no aparecen en la lista completa (revisar nombres)"
        )
    return ReferenciaCamara(dia.isoformat(), roman, fuente, a, b, tuple(avisos))


def _fila(sesion: str, ref: ReferenciaCamara, preguntas: dict | None) -> list[str]:
    p = preguntas or {}
    return [
        sesion,
        ref.fecha,
        ref.legislatura,
        str(ref.a.total),
        str(ref.a.mujeres),
        _pct(ref.a.porcentaje),
        str(ref.b.total),
        str(ref.b.mujeres),
        _pct(ref.b.porcentaje),
        _pct(ref.diferencia_puntos),
        _pct(p.get("brecha_puntos")),
        _pct(p.get("brecha_b_puntos")),
        "" if p.get("cambia_conclusion") is None else ("si" if p["cambia_conclusion"] else "no"),
        " | ".join(ref.avisos),
    ]


def _pct(valor: float | None) -> str:
    return "" if valor is None else f"{valor:.2f}".replace(".", ",")


def main(argv: list[str] | None = None) -> None:
    from contracts import AnalysisTimeline
    from metrics import enriquecer_frame, run_metric, timeline_to_frame
    from sources.manifest import read_manifest

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--carpeta", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args(argv)
    carpeta = args.carpeta or args.data / "externos" / "congreso"
    manifest = args.manifest or args.data / "manifiesto.csv"
    filas_manifiesto = read_manifest(manifest)

    cabecera = [
        "sesion", "fecha", "leg", "A_total", "A_mujeres", "A_%",
        "B_total", "B_mujeres", "B_%", "dif", "M04_brecha_A", "M04_brecha_B",
        "cambia", "avisos",
    ]  # fmt: skip
    print(";".join(cabecera))
    for video_id, fila in sorted(filas_manifiesto.items()):
        try:
            leg = re.search(r"[?&]idLegislaturaElegida=(\d+)", fila.get("url_origen") or "")
            ref = cargar(carpeta, fila["fecha_evento"], leg.group(1) if leg else "")
        except (DatosCamara, ValueError, KeyError) as exc:
            print(f"{video_id};sin dato;;{exc}".replace("\n", " "))
            continue
        preguntas = None
        timeline = args.data / "processed" / video_id / "timeline.json"
        if timeline.is_file():
            tl = AnalysisTimeline.model_validate_json(timeline.read_text("utf-8"))
            frame = enriquecer_frame(tl, timeline_to_frame(tl))
            frame.attrs.update(ref.attrs())
            preguntas = (run_metric("M04", frame).details or {}).get("preguntas")
        print(";".join(_fila(video_id, ref, preguntas)))


if __name__ == "__main__":
    main()
