"""Panel de VIS Open (Streamlit). Uso: streamlit run dashboard/app.py

Lee `data/processed/*/`; si no hay sesiones, enseña las SINTÉTICAS del repositorio.
No calcula nada con IA y nunca muestra nombres, caras ni fotogramas.
"""

from __future__ import annotations

import os
from pathlib import Path

import altair as alt
import streamlit as st

from dashboard.data import (
    METHOD_NOTICE,
    PENDING_METRICS,
    SOURCE_NOTICE,
    evolution_table,
    gender_time_table,
    interventions_table,
    load_sessions,
    metric_card,
    report_html,
    timeline_strip,
    video_tables,
)

COLORS = alt.Scale(
    domain=["mujer", "hombre", "desconocido", "sin_atribuir", "mano_levantada"],
    range=["#7b3fa0", "#2f7f8f", "#9a9a9a", "#d9d9d9", "#e08a00"],
)

st.set_page_config(page_title="VIS Open", layout="wide")
sessions = load_sessions(Path(os.environ.get("DATA_DIR") or "data"))
screen = st.sidebar.radio("Pantalla", ["Sesión", "Evolución"])
st.sidebar.info(METHOD_NOTICE)

if not sessions:
    st.warning("No hay sesiones procesadas.")
    st.stop()

if screen == "Sesión":
    chosen = st.sidebar.selectbox("Sesión", [s.session_id for s in sessions])
    s = next(x for x in sessions if x.session_id == chosen)
    st.title(f"Sesión {s.session_id}")
    if s.synthetic:
        st.warning("SINTÉTICO: datos de ejemplo, no es una sesión real.")
    else:
        src = s.source or {}
        st.caption(src.get("cita") or SOURCE_NOTICE)
        if src.get("url_origen"):
            st.markdown(f"[Fuente]({src['url_origen']})")
    st.info(METHOD_NOTICE)

    cards = [metric_card(r) for r in s.metrics.values()]
    for col, card in zip(st.columns(len(cards)), cards, strict=True):
        col.metric(card["titulo"].split(" (")[0], card["valor"])
    for key, label in PENDING_METRICS.items():
        st.caption(f"{key} {label}: no disponible todavía")

    st.subheader("Tiempo de palabra por género")
    gt = gender_time_table(s)
    st.altair_chart(
        alt.Chart(gt)
        .mark_bar()
        .encode(x="gender", y="minutos", color=alt.Color("gender", scale=COLORS)),
        use_container_width=True,
    )
    st.subheader("Línea de tiempo")
    st.altair_chart(
        alt.Chart(timeline_strip(s))
        .mark_bar(height=30)
        .encode(x="inicio_min", x2="fin_min", color=alt.Color("genero", scale=COLORS)),
        use_container_width=True,
    )
    vt = video_tables(s)
    if vt:
        st.subheader("Vídeo (sin caras)")
        st.warning(s.video["aviso"])
        left, right = st.columns(2)
        left.caption("Tiempo en pantalla por género (el género sale del audio)")
        left.altair_chart(
            alt.Chart(vt[0])
            .mark_bar()
            .encode(x="genero", y="minutos", color=alt.Color("genero", scale=COLORS)),
            use_container_width=True,
        )
        right.caption("Manos levantadas por zona de la imagen")
        right.dataframe(vt[1], use_container_width=True)
    st.subheader("Intervenciones")
    st.dataframe(interventions_table(s), use_container_width=True)
    st.download_button(
        "Descargar informe",
        report_html(s),
        file_name=f"informe_{s.session_id}.html",
        mime="text/html",
    )
else:
    st.title("Evolución entre sesiones")
    st.info(
        "Con 3 sesiones no se pueden sacar tendencias; "
        "el gráfico muestra cómo funcionará con más sesiones."
    )
    evo = evolution_table(sessions)
    st.altair_chart(
        alt.Chart(evo)
        .mark_line(point=True)
        .encode(x="sesion", y="M02", tooltip=["sesion", "M02", "M04"]),
        use_container_width=True,
    )
    st.dataframe(evo, use_container_width=True)
