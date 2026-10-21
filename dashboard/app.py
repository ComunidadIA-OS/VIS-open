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
    annotator_answers,
    evolution_gender_table,
    evolution_table,
    fmt_time,
    gender_time_table,
    inconclusive_reason,
    interventions_table,
    load_sessions,
    make_clip,
    metric_card,
    review_cuts,
    save_review,
    show_interventions,
    show_tracks,
    show_voices,
    timeline_strip,
    transcript_csv,
    transcript_turns,
    video_path,
    video_people_series,
    video_tables,
    video_tracks_with_totals,
    voice_transcripts,
    voices_table,
    voices_to_review,
)
from dashboard.pdf_report import report_pdf
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

SHORT_TITLES = {
    "M01": "M01 Presencia",
    "M02": "M02 Tiempo de palabra",
    "M03": "M03 Turnos",
    "M04": "M04 Brecha de paridad",
    "M13": "M13 Sin atribuir",
}

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
    "[data-testid='stMetricLabel'], [data-testid='stMetricLabel'] *"
    " {overflow: visible !important; white-space: normal !important;"
    " text-overflow: clip !important;}"
    "[data-testid='stMetric'] {padding: 0.5rem 0 1.4rem;}"
    "[data-testid='stMetricLabel'] {min-height: 2.6em;}"
    "[data-testid='stSelectbox'] input, [data-testid='stSelectbox'] [role='group'],"
    " [role='listbox'] [role='option'], [role='listbox'] [role='option'] *"
    " {font-size: clamp(1.2rem, 2.2vw, 1.8rem);}"
    "[data-testid='stSelectbox'] [role='group'] {min-height: 3.2rem;}"
    ".st-key-genero_filtro, .st-key-genero_filtro > div"
    " {flex-direction: row !important; flex-wrap: wrap;"
    " gap: 0.4rem 2rem;}"
    ".stApp h1 {font-size: clamp(2.2rem, 5vw, 4rem);"
    " background: linear-gradient(90deg, #7b3fa0, #2f7f8f); -webkit-background-clip: text;"
    " background-clip: text; -webkit-text-fill-color: transparent;}"
    ".stApp h2 {font-size: clamp(1.8rem, 4vw, 3rem); color: #7b3fa0;"
    " border-left: 6px solid #2f7f8f; padding-left: 0.6rem; margin-top: 3.4rem;"
    " border-bottom: 1px solid #e5e5ea;}"
    ".stApp h3 {font-size: clamp(1.4rem, 3vw, 2.4rem); color: #2f7f8f; margin-top: 2.2rem;}"
    "[data-testid='stMainBlockContainer'] [data-testid='stVerticalBlock'] {gap: 1.4rem;}"
    "[data-testid='stDownloadButton'] {margin-top: 1.2rem;}"
    ".st-key-transcript_box p, .st-key-voices_box [data-testid='stExpanderDetails'] p"
    " {font-size: clamp(0.85rem, 1.2vw, 1.15rem);}"
    ".st-key-video_box p, .st-key-video_box li,"
    " .st-key-video_box [data-testid='stCaptionContainer'],"
    " .st-key-video_box [data-testid='stAlertContainer'] p"
    " {font-size: clamp(0.85rem, 2vw, 1.7rem);}"
    "[data-testid='stTable'] td, [data-testid='stTable'] th"
    " {font-size: clamp(1.1rem, 2vw, 1.7rem);}"
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
            "Escucha la muestra: valida **la voz que oyes**, no a las demás personas que salgan "
            "en la imagen. Pon mujer u hombre solo si lo tienes claro; si dudas, desconocido. "
            "El género cuenta cuando **las dos anotadoras** coinciden."
        )
    who = st.radio("Anotadora", [1, 2], horizontal=True, format_func=lambda n: f"Anotadora {n}")

    codes = speaker_codes(s.timeline)
    folder = DATA_DIR / "processed" / s.session_id
    answers = annotator_answers(folder, who)  # lo que ya has validado tú, por voz
    cuts = review_cuts(s, [r.speaker_id for r in pending])
    if cuts:
        st.caption(
            f"{len(cuts)} cortes, uno a continuación de otro. Cuando validas una voz en un corte, "
            "vale para todos los cortes de esa voz."
        )
    for i, cut in enumerate(cuts, 1):
        sid = str(cut["speaker_id"])
        code = codes.get(sid, sid)
        if sid in answers:
            st.markdown(
                f"**Corte {i} de {len(cuts)} · {code}:** ya validada por ti como "
                f"**{answers[sid]}** (vale para todos sus cortes)."
            )
            continue
        start, stop = float(cut["start"]), float(cut["stop"])
        st.subheader(f"Corte {i} de {len(cuts)} · {code}")
        clip, text = st.columns([3, 2])
        clip.write(f"De {fmt_time(start)} a {fmt_time(stop)}")
        if video_file:
            mp4 = make_clip(video_file, start, stop, DATA_DIR / "clips", f"{s.session_id}_{sid}")
            if mp4:
                clip.video(mp4)  # solo esos segundos
            else:
                clip.video(video_file, start_time=int(start), end_time=int(stop))
        text.caption("Lo que dice en este corte")
        text.write(str(cut["texto"])[:400])
        with st.form(f"form_{s.session_id}_{sid}_{i}_{who}"):
            gender = st.radio("Género", ["mujer", "hombre", "desconocido"], horizontal=True)
            confidence = st.radio("Seguridad", ["alta", "media", "baja"], horizontal=True)
            notes = st.text_input("Notas (opcional, sin nombres)")
            if st.form_submit_button("Guardar"):
                save_review(
                    folder, who, sid, gender, confidence, notes, current_user or f"anotadora_{who}"
                )
                st.rerun()  # los demás cortes de esa voz pasan a «ya validada»

    # 3. El análisis de la sesión completa.
    st.header("Análisis de la sesión")
    cards = [(key, metric_card(r)) for key, r in s.metrics.items()]
    per_row = 3
    for first in range(0, len(cards), per_row):
        for col, (key, card) in zip(
            st.columns(per_row), cards[first : first + per_row], strict=False
        ):
            col.metric(
                SHORT_TITLES.get(key, card["titulo"].split(" (")[0]),
                card["valor"],
                help=card["titulo"],  # el nombre completo, al pasar el ratón
            )
    if why := inconclusive_reason(s):
        st.warning(why)
    for key, label in PENDING_METRICS.items():
        st.caption(f"{key} {label}: no disponible todavía")

    st.header("Análisis de audio (transcripción y voces)")
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
            .mark_bar(height=80)
            .encode(x="inicio_min", x2="fin_min", color=alt.Color("genero", scale=COLORS))
            .properties(height=130)
        ),
        use_container_width=True,
    )

    st.subheader("Transcripción")
    with st.container(height=600, key="transcript_box"):
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
    voices = voices_table(s)
    st.table(show_voices(voices).style.hide(axis="index"))
    st.caption("Pulsa en una voz para ver su transcripción.")
    by_voice = voice_transcripts(s)
    with st.container(key="voices_box"):
        for r in voices.itertuples():
            with st.expander(f"{r.persona} · {r.genero} · {fmt_time(r.minutos * 60)}"):
                for t in by_voice.get(r.persona, []):
                    st.write(f"**{fmt_time(t['inicio_s'])}** {t['texto']}")
    st.subheader("Intervenciones")
    inter = interventions_table(s)
    genders = ["mujer", "hombre", "desconocido", "sin_atribuir"]
    st.write("Género a mostrar")
    controls, _ = st.columns([7, 3])  # los controles ocupan el 70 % de la izquierda
    with controls.container(key="genero_filtro"):  # casillas en horizontal (ver CSS)
        shown = [
            g
            for g in genders
            if st.checkbox(g.replace("_", " "), value=True, key=f"genero_{s.session_id}_{g}")
        ]
    rows = inter[inter["genero"].isin(shown)].drop(columns=["evidencia"])
    per_page = 25
    pages = max(1, -(-len(rows) // per_page))
    page = controls.number_input(
        f"Página (de {pages})", min_value=1, max_value=pages, value=1, step=1
    )
    st.table(
        show_interventions(rows.iloc[(page - 1) * per_page : page * per_page]).style.hide(
            axis="index"
        )
    )
    with st.container(key="video_box"):
        st.header("Análisis de vídeo (MediaPipe, sin caras)")
        st.write(
            "MediaPipe devuelve puntos del cuerpo; de ahí salen las personas visibles, el "
            "tiempo en pantalla y las manos levantadas. No lee caras ni género."
        )
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
            st.subheader("Personas que ve la cámara a lo largo del vídeo")
            st.altair_chart(
                big(
                    alt.Chart(video_people_series(s))
                    .mark_area(opacity=0.6, line=True)
                    .encode(x="minuto", y="personas")
                ),
                use_container_width=True,
            )
            st.subheader("Tiempo en pantalla por género")
            st.caption("El género sale del audio, no de la imagen.")
            st.altair_chart(
                big(
                    alt.Chart(vt[0])
                    .mark_bar()
                    .encode(x="genero", y="minutos", color=alt.Color("genero", scale=COLORS))
                ),
                use_container_width=True,
            )
            st.subheader("Pistas con más tiempo en pantalla")
            st.table(show_tracks(video_tracks_with_totals(s)).style.hide(axis="index"))
            hands = v.get("manos_levantadas", [])
            st.subheader("Manos levantadas")
            st.caption("Zona de la imagen y momento; ▶ mueve el vídeo de arriba.")
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
    st.download_button(
        "Descargar transcripción (CSV)",
        transcript_csv(s),
        file_name=f"transcripcion_{s.session_id}.csv",
        mime="text/csv",
    )
    st.download_button(
        "Descargar informe (PDF)",
        report_pdf(s),
        file_name=f"informe_{s.session_id}.pdf",
        mime="application/pdf",
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
    st.table(evo.style.hide(axis="index").format(precision=2, na_rep="-"))
