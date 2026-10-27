"""Informe descargable de una sesión en PDF (ReportLab, BSD).

Resumen con lectura prudente de la brecha, métricas, análisis de audio (tiempo de palabra,
línea de tiempo, voces), análisis de vídeo (MediaPipe, sin caras) y método y límites. La
transcripción completa no va en el PDF: se enlaza a un CSV (`transcripcion_<id>.csv`).
"""

from __future__ import annotations

import io
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.graphics.shapes import Drawing, Line, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from dashboard.data import (
    METHOD_NOTICE,
    PENDING_METRICS,
    SOURCE_NOTICE,
    Session,
    fmt_pct,
    fmt_time,
    gender_time_table,
    inconclusive_reason,
    metric_card,
    session_summary,
    timeline_strip,
    turn_use_text,
    video_people_series,
    video_tables,
    video_tracks_with_totals,
    voices_table,
    with_unit,
)

WIDTH = A4[0] - 4 * cm  # ancho útil
GENDER_COLORS = {
    "mujer": colors.HexColor("#8e4b8b"),
    "hombre": colors.HexColor("#2a7b8c"),
    "desconocido": colors.HexColor("#a7a39b"),
    "sin_atribuir": colors.HexColor("#d9d5cc"),
}
INK, MUTED, LINE = (
    colors.HexColor("#222222"),
    colors.HexColor("#666666"),
    colors.HexColor("#e5e5ea"),
)


def _t(text: object) -> str:
    """Texto seguro para la fuente estándar del PDF (cp1252) y para XML."""
    plain = str(text).replace("−", "-").replace("≥", ">=").replace("▶", ">")
    return escape(plain.encode("cp1252", "replace").decode("cp1252"))


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=base["Title"], fontSize=22, alignment=0, spaceAfter=2),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontSize=15, spaceBefore=16, spaceAfter=6, textColor=INK
        ),
        "h3": ParagraphStyle(
            "h3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "p": ParagraphStyle("p", parent=base["BodyText"], fontSize=10, leading=14),
        "mut": ParagraphStyle("mut", parent=base["BodyText"], fontSize=8.5, textColor=MUTED),
        "cell": ParagraphStyle("cell", parent=base["BodyText"], fontSize=8.5, leading=10.5),
        "card": ParagraphStyle(
            "card", parent=base["BodyText"], fontSize=8, leading=10, alignment=1, textColor=MUTED
        ),
        "val": ParagraphStyle(
            "val", parent=base["BodyText"], fontSize=16, leading=19, alignment=1, textColor=INK
        ),
    }


def _box(text: str, style: ParagraphStyle, bg: str, bar: str) -> Table:
    box = Table([[Paragraph(_t(text), style)]], colWidths=[WIDTH])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
                ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor(bar)),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return box


def _grid(rows: list[list], widths: list[float] | None = None, header: bool = True) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fafafa")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    table.setStyle(TableStyle(style))
    return table


def _stacked_bar(table: pd.DataFrame) -> Drawing:
    """Barra apilada por género con su porcentaje y leyenda."""
    d = Drawing(WIDTH, 52)
    x = 0.0
    for r in table.itertuples():
        w = WIDTH * float(r.porcentaje) / 100
        if w <= 0:
            continue
        d.add(Rect(x, 22, w, 22, fillColor=GENDER_COLORS.get(r.gender), strokeColor=None))
        if w > 28:
            d.add(
                String(
                    x + w / 2,
                    29,
                    f"{r.porcentaje:.0f}%",
                    fontName="Helvetica",
                    fontSize=8,
                    fillColor=colors.white,
                    textAnchor="middle",
                )  # fmt: skip
            )
        x += w
    lx = 0.0
    for name, color in GENDER_COLORS.items():
        d.add(Rect(lx, 4, 8, 8, fillColor=color, strokeColor=None))
        d.add(
            String(
                lx + 12,
                5,
                name.replace("_", " "),
                fontName="Helvetica",
                fontSize=8,
                fillColor=MUTED,
            )
        )
        lx += 92
    return d


def _timeline(session: Session) -> Drawing:
    """Una franja por género a lo largo de la sesión, con eje en minutos."""
    strip = timeline_strip(session).sort_values("inicio_min")
    end = max(session.timeline.duration_s / 60, 0.01)
    d = Drawing(WIDTH, 52)
    spans: list[list] = []
    for r in strip.itertuples():
        if spans and spans[-1][2] == r.genero and r.inicio_min - spans[-1][1] < 0.05:
            spans[-1][1] = max(spans[-1][1], r.fin_min)
        else:
            spans.append([r.inicio_min, r.fin_min, r.genero])
    for start, stop, genero in spans:
        color = GENDER_COLORS.get(genero, colors.HexColor("#e08a00"))
        d.add(
            Rect(
                WIDTH * start / end,
                16,
                max(WIDTH * (stop - start) / end, 0.6),
                30,
                fillColor=color,
                strokeColor=None,
            )  # fmt: skip
        )
    step = max(1, int(end // 8))
    for m in range(0, int(end) + 1, step):
        x = WIDTH * m / end
        d.add(Line(x, 12, x, 16, strokeColor=MUTED, strokeWidth=0.5))
        d.add(
            String(
                x,
                3,
                f"{m} min",
                fontName="Helvetica",
                fontSize=7,
                fillColor=MUTED,
                textAnchor="middle",
            )
        )
    return d


def _people_line(session: Session) -> Drawing:
    series = video_people_series(session)
    d = Drawing(WIDTH, 90)
    if series.empty:
        return d
    xmax, ymax = max(series["minuto"].max(), 0.01), max(series["personas"].max(), 1.0)
    pts: list[float] = []
    for r in series.itertuples():
        pts += [WIDTH * r.minuto / xmax, 14 + 70 * r.personas / ymax]
    d.add(Line(0, 14, WIDTH, 14, strokeColor=MUTED, strokeWidth=0.5))
    d.add(PolyLine(pts, strokeColor=GENDER_COLORS["hombre"], strokeWidth=1.2))
    d.add(String(0, 2, "0 min", fontName="Helvetica", fontSize=7, fillColor=MUTED))
    d.add(
        String(
            WIDTH,
            2,
            f"{xmax:.0f} min",
            fontName="Helvetica",
            fontSize=7,
            fillColor=MUTED,
            textAnchor="end",
        )
    )
    d.add(
        String(
            0, 82, f"máx. {ymax:.1f} personas", fontName="Helvetica", fontSize=7, fillColor=MUTED
        )
    )
    return d


def _footer(canvas, doc) -> None:  # noqa: ANN001 - firma de ReportLab
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(
        2 * cm, 1.2 * cm, "VIS Open - cifras calculadas por código; sin nombres, sin caras"
    )
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    canvas.restoreState()


def report_pdf(
    session: Session, transcript_link: str | None = None, compress: bool = True
) -> bytes:
    """PDF del informe de una sesión."""
    st = _styles()
    gt = gender_time_table(session)
    voices = voices_table(session)
    src = session.source or {}
    ficha = (
        "SINTÉTICO: datos de ejemplo, no son una sesión real."
        if session.synthetic
        else src.get("cita") or SOURCE_NOTICE
    )
    link = transcript_link or f"transcripcion_{session.session_id}.csv"
    summary = session_summary(session)

    story: list = [
        Paragraph(_t(f"Informe de la sesión {session.session_id}"), st["h1"]),
        Paragraph(_t(ficha), st["mut"]),
        Paragraph("Resumen", st["h2"]),
        _box(summary, st["p"], "#f4f1f8", "#7b3fa0"),
        Paragraph("Métricas", st["h2"]),
    ]
    cards = []
    for key, r in session.metrics.items():
        c = metric_card(r)
        valor = " ".join(filter(None, [with_unit(key, c["valor"]), c.get("base")]))
        if c.get("aviso"):  # M04 con cifra pero sin conclusión (regla 5)
            valor += "<br/><font size='8'>no concluyente</font>"
        cards.append({**c, "valor": valor})
    per_row = 4  # con 6-8 métricas, una sola fila quedaría ilegible
    chunks = [cards[i : i + per_row] for i in range(0, len(cards), per_row)]
    empty = {"titulo": "", "valor": ""}
    chunks = [c + [empty] * (per_row - len(c)) for c in chunks]
    body = []
    for chunk in chunks:
        body.append([Paragraph(_t(c["titulo"].split(" (")[0]), st["card"]) for c in chunk])
        body.append(
            [
                Paragraph(
                    _t(c["valor"])
                    .replace("&lt;br/&gt;", "<br/>")
                    .replace("&lt;font size='8'&gt;", "<font size='8'>")
                    .replace("&lt;/font&gt;", "</font>"),
                    st["val"],
                )
                for c in chunk
            ]
        )
    metrics = Table(body, colWidths=[WIDTH / per_row] * per_row)
    metrics.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(metrics)
    if "M02b" in session.metrics and (use := turn_use_text(session.metrics["M02b"])):
        story += [Spacer(1, 4), Paragraph(_t(use), st["mut"])]
    if why := inconclusive_reason(session):
        story += [Spacer(1, 6), _box(why, st["p"], "#fff8e1", "#e0a100")]
    for c in cards:
        if c.get("aviso"):
            text = c["aviso"].removeprefix("no concluyente: ")
            story += [
                Spacer(1, 6),
                _box(f"{c['titulo']}: no concluyente, {text}.", st["p"], "#fff8e1", "#e0a100"),
            ]
    if PENDING_METRICS:
        story.append(
            Paragraph(
                _t(
                    "; ".join(f"{k} {v}: no disponible todavía" for k, v in PENDING_METRICS.items())
                ),
                st["mut"],
            )
        )

    story += [
        Paragraph("Análisis de audio (transcripción y voces)", st["h2"]),
        Paragraph("Tiempo de palabra por género", st["h3"]),
        _stacked_bar(gt),
        _grid(
            [["Género", "Tiempo de palabra", "%"]]
            + [
                [r.gender, fmt_time(r.minutos * 60), fmt_pct(r.porcentaje)] for r in gt.itertuples()
            ],
            [WIDTH * 0.5, WIDTH * 0.25, WIDTH * 0.25],
        ),
        Paragraph("Línea de tiempo", st["h3"]),
        Paragraph(
            "Cada franja es una intervención; el color es el género de quien habla.", st["mut"]
        ),
        _timeline(session),
        Paragraph("Voces", st["h3"]),
        _grid(
            [["Persona", "Género", "Origen", "Tiempo de palabra", "Intervenciones"]]
            + [
                [r.persona, r.genero, r.origen, fmt_time(r.minutos * 60), str(r.intervenciones)]
                for r in voices.itertuples()
            ]
        ),
        Spacer(1, 6),
        Paragraph(
            _t("La transcripción seudonimizada completa está en un CSV: ")
            + f"<a href='{escape(link)}' color='#2f7f8f'>{_t(link)}</a>.",
            st["p"],
        ),
    ]

    if video_tables(session):
        v = session.video
        pct = v["tiempo_en_pantalla_por_genero_%"]
        screen = pd.DataFrame({"gender": list(pct), "porcentaje": list(pct.values())})
        tracks = video_tracks_with_totals(session)
        story += [
            Paragraph("Análisis de vídeo (MediaPipe, sin caras)", st["h2"]),
            Paragraph(
                _t(
                    "MediaPipe devuelve puntos del cuerpo; de ahí salen las personas visibles, el "
                    "tiempo en pantalla. No lee caras ni género."
                ),
                st["p"],
            ),
            Spacer(1, 4),
            _box(v["aviso"], st["p"], "#fff8e1", "#e0a100"),
            Spacer(1, 6),
            Paragraph(
                _t(
                    f"Personas visibles a la vez: máximo {v['personas_visibles_max']}, mediana "
                    f"{v['personas_visibles_mediana']}; fotogramas sin nadie: "
                    f"{v['fotogramas_sin_personas_%']} %."
                ),
                st["p"],
            ),
            Paragraph("Personas que ve la cámara a lo largo del vídeo", st["h3"]),
            _people_line(session),
            Paragraph("Tiempo en pantalla por género (el género sale del audio)", st["h3"]),
            _stacked_bar(screen),
            KeepTogether(
                [
                    Paragraph("Pistas con más tiempo en pantalla", st["h3"]),
                    _grid(
                        [
                            [
                                "Pista",
                                "Min. en pantalla",
                                "%",
                                "Tamaño",
                                "Centralidad",
                                "Género (audio)",
                            ]
                        ]
                        + [
                            [
                                str(r.pista),
                                fmt_time(r.minutos_en_pantalla * 60),
                                fmt_pct(r.porcentaje),
                                "" if pd.isna(r.tamano_medio) else f"{r.tamano_medio:.2f}",
                                "" if pd.isna(r.centralidad) else f"{r.centralidad:.2f}",
                                r.genero_por_audio,
                            ]
                            for r in tracks.itertuples()
                        ]
                    ),
                ]
            ),
        ]

    story += [
        Paragraph("Método y límites", st["h2"]),
        Paragraph(_t(METHOD_NOTICE), st["p"]),
        Paragraph(
            _t(
                "Las voces sin pista clara figuran como «desconocido» hasta que las confirman dos "
                "anotadoras. La Presidencia queda fuera de M02 y M04. Métricas validadas con "
                "anotación humana (género: 86 de 87 personas correctas; docs/EVALUACION.md)."
            ),
            st["p"],
        ),
    ]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=2 * cm,
        title=f"Informe {session.session_id}",
        author="VIS Open",
        pageCompression=1 if compress else 0,
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
