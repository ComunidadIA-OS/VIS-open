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

from dashboard.auth import auth_enabled, check_login
from dashboard.data import (
    METHOD_NOTICE,
    PENDING_METRICS,
    SOURCE_NOTICE,
    evolution_gender_table,
    evolution_table,
    fmt_time,
    gender_time_table,
    interventions_table,
    load_sessions,
    metric_card,
    report_html,
    save_review,
    timeline_strip,
    transcript_turns,
    video_path,
    video_tables,
    voice_blocks,
    voices_table,
    voices_to_review,
)
from decision.pseudonymize import speaker_codes


def big(chart: alt.Chart) -> alt.Chart:
    """Letra de ejes y leyendas legible en pantalla grande."""
    return chart.configure_axis(labelFontSize=16, titleFontSize=18).configure_legend(
        labelFontSize=16, titleFontSize=18
    )


COLORS = alt.Scale(
    domain=["mujer", "hombre", "desconocido", "sin_atribuir", "mano_levantada"],
    range=["#7b3fa0", "#2f7f8f", "#9a9a9a", "#d9d9d9", "#e08a00"],
)

st.set_page_config(page_title="VIS Open", layout="wide")
# Letra al doble (32 px) en pantalla grande o proyectada; baja sola en tablet y móvil (clamp).
st.markdown(
    "<style>"
    ".stApp p, .stApp li, .stApp label, [data-testid='stAlertContainer'] p,"
    " [data-testid='stCaptionContainer'], [data-testid='stMetricLabel'] p"
    " {font-size: clamp(1rem, 2.4vw, 2rem);}"
    "[data-testid='stSidebar'] p, [data-testid='stSidebar'] label"
    " {font-size: clamp(0.9rem, 1.4vw, 1.3rem);}"
    "[data-testid='stTab'] p, .stButton p {font-size: clamp(0.9rem, 1.5vw, 1.4rem);}"
    "[data-testid='stMetricValue'] {font-size: clamp(2rem, 4.5vw, 4rem);}"
    "[data-testid='stMetricLabel'] {overflow: visible; white-space: normal;}"
    "</style>",
    unsafe_allow_html=True,
)
DATA_DIR = Path(os.environ.get("DATA_DIR") or "data")


def login_gate() -> str | None:
    """Pide usuario, contraseña y código del autenticador si hay usuarios dados de alta."""
    if not auth_enabled(DATA_DIR):
        return None
    if "user" not in st.session_state:
        st.title("VIS Open")
        with st.form("login"):
            user_id = st.text_input("ID de usuario")
            password = st.text_input("Contraseña", type="password")
            code = st.text_input("Código de 6 cifras del autenticador")
            if st.form_submit_button("Entrar"):
                ok, why = check_login(DATA_DIR, user_id.strip(), password, code)
                if ok:
                    st.session_state["user"] = user_id.strip()
                    st.rerun()
                st.error(why)
        st.stop()
    return st.session_state["user"]


current_user = login_gate()
sessions = load_sessions(DATA_DIR)
screen = st.sidebar.radio("Pantalla", ["Sesión", "Evolución"])
st.sidebar.info(METHOD_NOTICE)
if current_user:
    st.sidebar.write(f"Conectada: {current_user}")
    if st.sidebar.button("Salir"):
        del st.session_state["user"]
        st.rerun()

if not sessions:
    st.warning("No hay sesiones procesadas.")
    st.stop()

if screen == "Sesión":
    title_col, pick_col = st.columns([3, 1])
    chosen = pick_col.selectbox("Cambiar de vídeo", [s.session_id for s in sessions])
    s = next(x for x in sessions if x.session_id == chosen)
    title_col.title(f"Sesión {s.session_id}")
    if s.synthetic:
        st.warning("SINTÉTICO: datos de ejemplo, no es una sesión real.")
    else:
        src = s.source or {}
        st.caption(src.get("cita") or SOURCE_NOTICE)
        if src.get("url_origen"):
            st.markdown(f"[Fuente]({src['url_origen']})")
    st.info(METHOD_NOTICE)

    video_file = video_path(s, DATA_DIR)
    minute_key = f"minuto_{s.session_id}"
    max_minute = s.timeline.duration_s / 60

    def go_to(seconds: float) -> None:
        st.session_state[minute_key] = min(seconds / 60, max_minute)

    # 1. El vídeo completo.
    if video_file:
        minute = st.number_input(
            "Ir al minuto", min_value=0.0, max_value=max_minute, step=1.0, key=minute_key
        )
        st.video(video_file, start_time=int(minute * 60))
        st.caption("Vídeo original del Congreso, sin alterar. Solo se ve en este equipo.")
    else:
        st.info("El vídeo original no está en este equipo (`data/raw/`): solo se ve el texto.")

    # 2. Human in the loop: los tramos de las voces que quedaron «desconocido».
    pending = [
        r
        for r in voices_to_review(DATA_DIR / "processed" / s.session_id)
        if r.speaker_id not in s.confirmed
    ]
    st.header(f"Human in the loop ({len(pending)} voces sin confirmar)")
    if not pending:
        st.success("Todas las voces de esta sesión ya tienen género.")
    else:
        st.write(
            "Mira y escucha cada tramo. Pon mujer u hombre solo si lo tienes claro; si no, "
            "desconocido. El género cuenta cuando **las dos anotadoras** coinciden."
        )
    who = st.radio("Anotadora", [1, 2], horizontal=True, format_func=lambda n: f"Anotadora {n}")
    codes = speaker_codes(s.timeline)
    for row in pending:
        code = codes.get(row.speaker_id, row.speaker_id)
        st.subheader(code)
        blocks = voice_blocks(s.timeline, row.speaker_id)
        for col, (start, end) in zip(st.columns(len(blocks) or 1), blocks, strict=False):
            col.write(f"{code}: de {fmt_time(start)} a {fmt_time(end)}")
            if video_file:
                col.video(video_file, start_time=int(start), end_time=int(min(end, start + 30)))
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
                    current_user or f"anotadora_{who}",
                )
                st.success("Guardado. Recarga la página para ver el efecto en las cifras.")

    # 3. El análisis de la sesión completa.
    st.header("Análisis de la sesión")
    cards = [metric_card(r) for r in s.metrics.values()]
    for col, card in zip(st.columns(len(cards)), cards, strict=True):
        col.metric(card["titulo"].split(" (")[0], card["valor"])
    for key, label in PENDING_METRICS.items():
        st.caption(f"{key} {label}: no disponible todavía")

    st.subheader("Tiempo de palabra por género")
    gt = gender_time_table(s)
    st.altair_chart(
        big(
            alt.Chart(gt)
            .mark_bar()
            .encode(x="gender", y="minutos", color=alt.Color("gender", scale=COLORS))
        ),
        use_container_width=True,
    )
    st.subheader("Línea de tiempo")
    st.altair_chart(
        big(
            alt.Chart(timeline_strip(s))
            .mark_bar(height=30)
            .encode(x="inicio_min", x2="fin_min", color=alt.Color("genero", scale=COLORS))
        ),
        use_container_width=True,
    )

    st.subheader("Análisis de vídeo (sin caras)")
    vt = video_tables(s)
    if not vt:
        st.info(
            "Esta sesión no tiene análisis de vídeo. Se genera en el equipo con "
            f"`python -m pipeline.video data/raw/{s.session_id}.mp4 "
            "--model models/pose_landmarker_full.task`."
        )
    else:
        v = s.video
        st.warning(v["aviso"])
        st.write(
            f"Personas visibles a la vez: máximo {v['personas_visibles_max']}, "
            f"mediana {v['personas_visibles_mediana']}. "
            f"Fotogramas sin nadie: {v['fotogramas_sin_personas_%']} %."
        )
        st.caption("Tiempo en pantalla por género (el género sale del audio, no de la imagen)")
        st.altair_chart(
            big(
                alt.Chart(vt[0])
                .mark_bar()
                .encode(x="genero", y="minutos", color=alt.Color("genero", scale=COLORS))
            ),
            use_container_width=True,
        )
        hands = v.get("manos_levantadas", [])
        st.caption("Manos levantadas (zona de la imagen y momento; ▶ mueve el vídeo de arriba)")
        if not hands:
            st.write("No se han detectado manos levantadas.")
        hand_cols = st.columns(4)
        for i, h in enumerate(hands):
            hand_cols[i % 4].button(
                f"▶ {fmt_time(h['inicio_s'])} · zona {h['zona']}",
                key=f"hand_{s.session_id}_{i}",
                on_click=go_to,
                args=(h["inicio_s"],),
                disabled=not video_file,
            )

    st.subheader("Transcripción")
    with st.container(height=600):
        for i, t in enumerate(transcript_turns(s)):
            st.button(
                f"▶ {fmt_time(t['inicio_s'])} · {t['persona']} · {t['genero']}",
                key=f"go_{s.session_id}_{i}",
                on_click=go_to,
                args=(t["inicio_s"],),
                disabled=not video_file,
            )
            st.write(t["texto"])
    st.subheader("Voces y género")
    st.dataframe(voices_table(s), use_container_width=True)
    st.subheader("Intervenciones")
    inter = interventions_table(s)
    shown = st.multiselect(
        "Género a mostrar",
        ["mujer", "hombre", "desconocido", "sin_atribuir"],
        default=["mujer", "hombre", "desconocido", "sin_atribuir"],
    )
    st.dataframe(inter[inter["genero"].isin(shown)], use_container_width=True)
    st.download_button(
        "Descargar informe",
        report_html(s),
        file_name=f"informe_{s.session_id}.html",
        mime="text/html",
    )
else:
    st.title("Evolución entre sesiones")
    st.info(
        "Con pocas sesiones no se pueden sacar tendencias; "
        "el gráfico muestra cómo funcionará con más sesiones."
    )
    st.subheader("Tiempo de palabra por género en cada sesión (%)")
    st.altair_chart(
        big(
            alt.Chart(evolution_gender_table(sessions))
            .mark_bar()
            .encode(
                x="sesion",
                y=alt.Y("porcentaje", scale=alt.Scale(domain=[0, 100])),
                color=alt.Color("gender", scale=COLORS),
                tooltip=["sesion", "gender", "porcentaje"],
            )
        ),
        use_container_width=True,
    )
    st.caption("Una sesión con todo «desconocido» aún no tiene género asignado: falta revisión.")
    evo = evolution_table(sessions).astype(object).fillna("no concluyente")
    st.dataframe(evo, use_container_width=True)
