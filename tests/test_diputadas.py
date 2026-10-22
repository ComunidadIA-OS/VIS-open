"""Composición de la cámara (M04 c) y descarga de los datos abiertos del Congreso."""

from pathlib import Path

import pytest

from metrics.diputadas import DatosCamara, cargar, clave_persona, numero_legislatura
from sources.diputados import PAGINA, DiputadosError, descargar, enlaces

REAL = Path(__file__).parent.parent / "data" / "externos" / "congreso"


def _csv(path: Path, cabecera: list[str], filas: list[tuple[str, ...]]) -> None:
    lineas = [";".join(cabecera), *(";".join(f) for f in filas)]
    path.write_text("\n".join(lineas) + "\n", encoding="utf-8")


@pytest.fixture
def camara(tmp_path: Path) -> Path:
    """Congreso de juguete de §4 bis: la Persona 3 sustituye a la 2."""
    d = tmp_path / "congreso"
    d.mkdir()
    _csv(
        d / "odsDiputados15__20260101000000.csv",
        ["NOMBRE", "SEXO", "FECHAALTA", "FECHABAJA"],
        [
            ("Persona 1", "mujer", "17/08/2023", ""),
            ("Persona 2", "hombre", "17/08/2023", "10/01/2025"),
            ("Persona 3", "hombre", "10/01/2025", ""),
        ],
    )
    lista = ["NOMBRE", "APELLIDOS", "LEGISLATURA", "LEGISLATURAACTUAL"]
    _csv(d / "Diputadas__20260101000000.csv", lista, [("Persona 1", "", "Leg. XV", "N")])
    _csv(
        d / "Diput__20260101000000.csv",
        lista,
        [("Persona 1", "", "Leg. XV", "N"), ("Persona 2", "", "Leg. XV", "N"),
         ("Persona 3", "", "Leg. XV", "N")],
    )  # fmt: skip
    return d


def test_numero_legislatura():
    for valor in (15, "15", "XV", "Leg. XV", "leg. xv"):
        assert numero_legislatura(valor) == 15
    with pytest.raises(DatosCamara):
        numero_legislatura("la que sea")


def test_clave_persona_junta_apellidos_y_nombre():
    a = clave_persona("Pita Cárdenes, María del Carmen")
    b = clave_persona("María del Carmen", "Pita Cárdenes")
    assert a == b == "pita cardenes maria del carmen"


def test_ejemplo_de_juguete_de_la_especificacion(camara: Path):
    ref = cargar(camara, "2026-09-30", 15, esperado_a=2, esperado_b=3)
    assert (ref.a.total, ref.a.mujeres, ref.a.porcentaje) == (2, 1, 50.0)
    assert (ref.b.total, ref.b.mujeres, ref.b.porcentaje) == (3, 1, 33.33)
    assert ref.diferencia_puntos == -16.67
    assert ref.avisos == ()


def test_sin_columna_de_sexo_se_usa_el_tratamiento(tmp_path: Path):
    d = tmp_path / "c"
    d.mkdir()
    _csv(
        d / "odsDiputados15__1.csv",
        ["NOMBRE", "TRATAMIENTO", "FECHAALTA", "FECHABAJA"],
        [("Persona 1", "Sra.", "01/01/2023", ""), ("Persona 2", "Sr.", "01/01/2023", "")],
    )
    lista = ["NOMBRE", "APELLIDOS", "LEGISLATURA", "LEGISLATURAACTUAL"]
    # Las listas no conocen a nadie del día: el sexo solo puede salir del tratamiento.
    _csv(d / "Diputadas__1.csv", lista, [("Otra persona", "", "Leg. XV", "N")])
    _csv(d / "Diput__1.csv", lista, [("Otra persona", "", "Leg. XV", "N")])
    ref = cargar(d, "2026-09-30", 15, esperado_a=2, esperado_b=1)
    assert (ref.a.mujeres, ref.a.hombres, ref.a.desconocido) == (1, 1, 0)
    assert ref.a.porcentaje == 50.0


def test_sin_sexo_ni_tratamiento_queda_desconocido(camara: Path):
    (camara / "odsDiputados15__20260101000000.csv").write_text(
        "NOMBRE;FECHAALTA;FECHABAJA\nPersona 1;17/08/2023;\nPersona 9;17/08/2023;\n",
        encoding="utf-8",
    )
    ref = cargar(camara, "2026-09-30", 15, esperado_a=2, esperado_b=3)
    assert (ref.a.mujeres, ref.a.hombres, ref.a.desconocido) == (1, 0, 1)
    assert any("desconocido" in a for a in ref.avisos)


def test_control_a_distinto_de_350_no_se_usa(camara: Path):
    ref = cargar(camara, "2026-09-30", 15, esperado_a=350, esperado_b=3)
    assert ref.a.total == 2 and ref.a.porcentaje is None
    assert any("medida A suma 2" in a and "350" in a for a in ref.avisos)
    assert ref.attrs() == {"porcentaje_diputadas_b": 33.33}


def test_control_b_que_no_cuadra_no_se_usa(camara: Path):
    ref = cargar(camara, "2026-09-30", 15, esperado_a=2, esperado_b=400)
    assert ref.b.porcentaje is None
    assert any("medida B suma 3" in a for a in ref.avisos)
    assert "porcentaje_diputadas_b" not in ref.attrs()


def test_la_legislatura_actual_usa_activos_y_de_baja(tmp_path: Path):
    d = tmp_path / "c"
    d.mkdir()
    lista = ["NOMBRE", "APELLIDOS", "LEGISLATURA", "LEGISLATURAACTUAL"]
    _csv(d / "Diputadas__1.csv", lista, [("Persona 1", "", "Leg. XV", "S")])
    _csv(
        d / "Diput__1.csv",
        lista,
        [("Persona 1", "", "Leg. XV", "S"), ("Persona 3", "", "Leg. XV", "S")],
    )  # fmt: skip
    _csv(d / "DiputadosActivos__1.csv", ["NOMBRE", "FECHAALTA"],
         [("Persona 1", "17/08/2023")])  # fmt: skip
    _csv(d / "DiputadosDeBaja__1.csv", ["NOMBRE", "FECHAALTA", "FECHABAJA"],
         [("Persona 3", "10/01/2025", "")])  # fmt: skip
    ref = cargar(d, "2026-09-30", 15, esperado_a=2, esperado_b=2)
    assert ref.a.total == 2 and ref.a.mujeres == 1 and ref.a.porcentaje == 50.0
    assert "DiputadosActivos" in ref.fuente_a


def test_sin_datos_avisa_como_conseguirlos(tmp_path: Path):
    with pytest.raises(DatosCamara, match="sources.diputados"):
        cargar(tmp_path, "2026-09-30", 15)


HTML = """
<a href="/webpublica/opendata/diputados/Diputadas__20260101000000.csv">a</a>
<a href="/webpublica/opendata/diputados/Diputadas__20260202000000.csv">b</a>
<a href="/webpublica/opendata/diputados/Diput__20260202000000.csv">c</a>
<a href="/webpublica/opendata/diputados/DiputadosActivos__20260202000000.csv">d</a>
<a href="/webpublica/opendata/diputados/DiputadosDeBaja__20260202000000.csv">e</a>
<a href="/webpublica/opendata/diputados/odsDiputados14__20260101000000.csv">f</a>
<a href="/webpublica/opendata/diputados/odsDiputados14__20260202000000.csv">g</a>
<a href="/webpublica/opendata/diputados/Diputadas__20260202000000.xml">h</a>
"""


def test_enlaces_elige_el_csv_mas_reciente():
    links = enlaces(HTML)
    assert links["diputadas"].endswith("Diputadas__20260202000000.csv")
    assert links["leg14"].endswith("odsDiputados14__20260202000000.csv")
    assert "leg15" not in links


def test_descargar_una_vez_y_registrar(tmp_path: Path):
    pedidas: list[str] = []

    def abrir(url: str) -> bytes:
        pedidas.append(url)
        return HTML.encode() if url == PAGINA else b"NOMBRE\nX\n"

    rutas = descargar(tmp_path, [14], abrir=abrir)
    assert set(rutas) == {"diputadas", "diputados", "activos", "baja", "leg14"}
    assert rutas["diputadas"].name == "Diputadas__20260202000000.csv"
    assert len(pedidas) == 6  # la página y los cinco CSV
    registro = (tmp_path / "descargas.csv").read_text("utf-8").splitlines()
    assert len(registro) == 6 and len(registro[1].split(",")[-1]) == 64

    def no_red(url: str) -> bytes:
        raise AssertionError(f"no debería descargar {url}")

    assert descargar(tmp_path, [14], abrir=no_red) == rutas


def test_pagina_sin_csv_avisa(tmp_path: Path):
    with pytest.raises(DiputadosError, match="no enlaza"):
        descargar(tmp_path, [14], abrir=lambda url: b"<html>cambiada</html>")


def test_pagina_caida_sin_cache_avisa(tmp_path: Path):
    def caida(url: str) -> bytes:
        raise OSError("sin red")

    with pytest.raises(DiputadosError, match="a mano"):
        descargar(tmp_path, [14], abrir=caida)


@pytest.mark.skipif(not any(REAL.glob("Diputadas__*.csv")), reason="sin datos descargados")
def test_datos_reales_coinciden_con_el_buscador():
    casos = {
        15: ("2026-09-29", 412, 189),
        14: ("2022-10-05", 407, 174),
        12: ("2018-09-19", 393, 161),
    }
    for leg, (fecha, total, mujeres) in casos.items():
        ref = cargar(REAL, fecha, leg)
        assert (ref.b.total, ref.b.mujeres) == (total, mujeres)
    assert cargar(REAL, "2026-09-29", 15).a.total == 350
    assert cargar(REAL, "2018-09-19", 12).a.total == 350


@pytest.mark.skipif(not any(REAL.glob("Diputadas__*.csv")), reason="sin datos descargados")
def test_el_panel_pasa_la_composicion_a_m04(tmp_path: Path):
    import json
    import shutil

    from dashboard.data import SYNTHETIC_DIR, load_sessions

    carpeta = tmp_path / "processed" / "V005"
    carpeta.mkdir(parents=True)
    shutil.copy(SYNTHETIC_DIR / "SINTETICO_equilibrado.timeline.json", carpeta / "timeline.json")
    url = (
        "https://app.congreso.es/AudiovisualCongreso/audiovisualdetalledisponible"
        "?codOrgano=400&codSesion=201&fechaSesion=29/09/2026&idLegislaturaElegida=15"
    )
    (carpeta / "source.json").write_text(
        json.dumps({"fecha_evento": "2026-09-29", "url_origen": url}), "utf-8"
    )
    externos = tmp_path / "externos" / "congreso"
    externos.mkdir(parents=True)
    for fichero in REAL.glob("*.csv"):
        shutil.copy(fichero, externos / fichero.name)

    sesion = load_sessions(tmp_path)[0]
    preguntas = sesion.metrics["M04"].details["preguntas"]
    assert preguntas["diputadas_%"] == 44.86
    assert preguntas["diputadas_b_%"] == 45.87
    assert preguntas["cambia_conclusion"] is False
    assert sesion.referencia["diferencia_puntos"] == 1.01
