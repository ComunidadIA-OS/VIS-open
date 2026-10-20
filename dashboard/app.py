"""Panel de VIS Open (Streamlit). Uso: streamlit run dashboard/app.py

Lee `data/processed/*/`; si no hay sesiones, enseña las SINTÉTICAS del repositorio.
No calcula nada con IA, nunca muestra nombres y no analiza caras. Si el vídeo original está en
`data/raw/` (solo en el equipo local), lo reproduce tal cual.
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
    fmt_time,
    gender_time_table,
    interventions_table,
    load_sessions,
    metric_card,
    report_html,
    save_review,
    timeline_strip,
    video_path,
    video_tables,
    voice_blocks,
    voices_to_review,
)
from decision.pseudonymize import speaker_codes

COLORS = alt.Scale(
    domain=["mujer", "hombre", "desconocido", "sin_atribuir", "mano_levantada"],
    range=["#7b3fa0", "#2f7f8f", "#9a9a9a", "#d9d9d9", "#e08a00"],
)

st.set_page_config(page_title="VIS Open", layout="wide")
# Letra al doble del tamaño por defecto (16 px → 32 px) para leerlo en pantalla grande o proyectado.
st.markdown(
    "<style>"
    ".stApp p, .stApp li, .stApp label, [data-testid='stAlertContainer'] p,"
    " [data-testid='stCaptionContainer'], [data-testid='stMetricLabel'] p {font-size: 2rem;}"
    "[data-testid='stMetricValue'] {font-size: 4rem;}"
    "[data-testid='stMetricLabel'] {overflow: visible; white-space: normal;}"
    "</style>",
    unsafe_allow_html=True,
)
DATA_DIR = Path(os.environ.get("DATA_DIR") or "data")
sessions = load_sessions(DATA_DIR)
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

    video_file = video_path(s, DATA_DIR)
    if video_file:
        minute = st.number_input(
            "Ir al minuto",
            min_value=0.0,
            max_value=s.timeline.duration_s / 60,
            value=0.0,
            step=1.0,
        )
        st.video(video_file, start_time=int(minute * 60))
        st.caption("Vídeo original del Congreso, sin alterar. Solo se ve en este equipo.")

        pending = voices_to_review(DATA_DIR / "processed" / s.session_id)
        pending = [r for r in pending if r.speaker_id not in s.confirmed]
        with st.expander(
            f"Human in the loop: confirmar el género de las voces ({len(pending)} sin confirmar)"
        ):
            st.write(
                "Mira y escucha cada tramo. Pon mujer u hombre solo si lo tienes claro; si no, "
                "desconocido. El género cuenta cuando **las dos anotadoras** coinciden."
            )
            who = st.radio(
                "Anotadora", [1, 2], horizontal=True, format_func=lambda n: f"Anotadora {n}"
            )
            codes = speaker_codes(s.timeline)
            for row in pending:
                code = codes.get(row.speaker_id, row.speaker_id)
                st.subheader(code)
                for start, end in voice_blocks(s.timeline, row.speaker_id):
                    st.write(f"{code}: de {fmt_time(start)} a {fmt_time(end)}")
                    st.video(video_file, start_time=int(start), end_time=int(min(end, start + 30)))
                with st.form(f"form_{s.session_id}_{row.speaker_id}_{who}"):
                    gender = st.radio("Género", ["mujer", "hombre", "desconocido"], horizontal=True)
                    confidence = st.radio("Seguridad", ["alta", "media", "baja"], horizontal=True)
                    notes = st.text_input("Notas (opcional, sin nombres)")
                    if st.form_submit_button("Guardar"):
                        save_review(
                            DATA_DIR / "processed" / s.session_id,
                            who,
                            row.speaker_id,
                            gender,
                            confidence,
                            notes,
                        )
                        st.success("Guardado. Recarga la página para ver el efecto en las cifras.")

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
