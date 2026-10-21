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
    subtitles_vtt,
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
    return chart.configure_axis(labelFontSize=20, titleFontSize=22).configure_legend(
        labelFontSize=20, titleFontSize=22
    )


COLORS = alt.Scale(
    domain=["mujer", "hombre", "desconocido", "sin_atribuir", "mano_levantada"],
    range=["#8e4b8b", "#2a7b8c", "#a7a39b", "#d9d5cc", "#d98e04"],
)

SUBTITLE_LABEL = "Español (automático)"
SHORT_TITLES = {
    "M01": "M01 Presencia",
    "M02": "M02 Tiempo de palabra",
    "M03": "M03 Turnos",
    "M04": "M04 Brecha de paridad",
    "M13": "M13 Sin atribuir",
}

st.set_page_config(page_title="VIS Open", layout="wide")
# Estilo del panel: dashboard/style.css (papel cálido, tinta y un acento; sin recursos externos).
st.markdown(
    f"<style>{(Path(__file__).parent / 'style.css').read_text(encoding='utf-8')}</style>",
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


def run_voice(cmd, ids: list[str]) -> str:
    """Ejecuta una orden ya validada por la lista cerrada y devuelve lo que se dice en voz alta."""
    from dashboard import voice

    ss = st.session_state
    current = cmd.session or ss.get("sesion", ids[0])
    sess = next(x for x in sessions if x.session_id == current)
    folder = DATA_DIR / "processed" / current
    who = ss.get("anotadora", 1)
    ss["sesion"] = current
    ss["pantalla"] = "Evolución" if cmd.topic == "evolution" else "Sesión"
    ss["voz_ancla"] = cmd.section
    act = cmd.action

    if act == "explain":
        if cmd.topic == "evolution":
            return voice.explain_evolution(sessions)
        return voice.METHOD if cmd.topic == "method" else voice.explain_results(sess)
    if act == "read_transcript":
        ss[f"minuto_{current}"] = min(cmd.minute, sess.timeline.duration_s / 60)
        ss["voz_ancla"] = "sec-video"
        return voice.read_transcript(sess, cmd.minute)
    if act == "go_minute" and cmd.minute is not None and cmd.minute >= 0:
        ss[f"minuto_{current}"] = min(cmd.minute, sess.timeline.duration_s / 60)
        ss["voz_ancla"] = "sec-video"
    if act == "repeat":
        return ss.get("voz_respuesta") or voice.HELP

    if act == "validate_start":
        cuts = voice.pending_cuts(sess, folder, who)
        if not cuts:
            return f"No quedan voces por validar en la sesión {current}."
        ss.update(voz_cortes=cuts, voz_i=0, voz_estado="gender", voz_ancla="sec-hitl")
        return f"Validación de la sesión {current} como anotadora {who}. " + voice.describe_cut(
            cuts[0], 1, len(cuts)
        )
    if act in ("val_gender", "val_confirm", "val_cancel", "val_skip", "play_cut"):
        cuts = ss.get("voz_cortes")
        if not cuts:
            return "No hay una validación en curso. Di «empieza la validación de voces»."
        cut = cuts[ss.get("voz_i", 0)]
        ss["voz_ancla"] = "sec-hitl"
        if act == "val_cancel":
            ss.update(voz_estado=None, voz_cortes=None)
            return "Validación cancelada. No se ha guardado nada."
        if act == "play_cut":
            ss["voz_play"] = cut
            return "Reproduzco el corte."
        if act == "val_gender":
            ss.update(voz_genero=cmd.gender, voz_estado="confirm")
            return (
                f"Has dicho {cmd.gender} para {cut['code']}. ¿Confirmas? Di «confirmo» o «cancela»."
            )
        if act == "val_confirm":
            save_review(
                folder,
                who,
                str(cut["speaker_id"]),
                ss["voz_genero"],
                "media",
                "",
                current_user or f"anotadora_{who}",
            )
            done = f"Guardado: {cut['code']} es {ss['voz_genero']}. "
        else:  # val_skip
            done = "Salto este corte. "
        ss["voz_i"] = ss.get("voz_i", 0) + (1 if act == "val_skip" else 0)
        rest = voice.pending_cuts(sess, folder, who)
        if act == "val_skip":
            rest = cuts[ss["voz_i"] :]
        if not rest:
            ss.update(voz_estado=None, voz_cortes=None)
            return done + "No quedan más cortes. La voz cuenta cuando dos anotadoras coinciden."
        ss.update(voz_cortes=rest, voz_i=0, voz_estado="gender")
        return done + voice.describe_cut(rest[0], 1, len(rest))
    return voice.answer(cmd, sess)


def voice_assistant() -> None:
    """Órdenes habladas (o escritas) -> acción en el panel + respuesta en voz alta."""
    from dashboard import voice

    ss = st.session_state
    ids = [x.session_id for x in sessions]
    box = st.sidebar.expander("Asistente de voz", expanded=bool(ss.get("voz_respuesta")))
    with box:
        st.caption(
            "Pulsa, di una orden y para. Ejemplos: «enséñame la sesión cuatro», «cuántas mujeres "
            "hablaron», «léeme la transcripción del minuto 3:59», «explícame los resultados», "
            "«empieza la validación de voces». Di «ayuda» para oír todas."
        )
        audio = st.audio_input("Dí una orden", key="voz_audio")
        typed = st.text_input("o escríbela", key="voz_texto")
    text = ""
    if audio is not None and ss.get("voz_hecha") != audio.file_id:
        ss["voz_hecha"] = audio.file_id
        try:
            text = voice.transcribe(audio.getvalue())
        except Exception as exc:  # noqa: BLE001 - sin red o sin clave: se dice, no se cae
            ss["voz_respuesta"] = f"No he podido oír la orden ({type(exc).__name__})."
    elif typed and ss.get("voz_escrita") != typed:
        ss["voz_escrita"] = typed
        text = typed
    if text:
        cmd = voice.parse_command(text, ids, ss.get("voz_estado"))
        ss["voz_texto_oido"] = text
        ss["voz_respuesta"] = (
            "No te he entendido. " + voice.HELP if cmd is None else run_voice(cmd, ids)
        )
        ss["voz_nueva"] = True
    if ss.get("voz_respuesta"):
        with box:
            st.text(f"Has dicho: {ss.get('voz_texto_oido', '')}")  # texto plano
            st.text(f"Respuesta: {ss['voz_respuesta']}")
            cut = ss.pop("voz_play", None)
            current = ss.get("sesion", ids[0])
            clip_src = video_path(next(x for x in sessions if x.session_id == current), DATA_DIR)
            if cut and clip_src:
                mp4 = make_clip(
                    clip_src,
                    float(cut["start"]),
                    float(cut["stop"]),
                    DATA_DIR / "clips",
                    f"{current}_{cut['speaker_id']}",
                )
                if mp4:
                    st.video(mp4, autoplay=True)


if sessions:
    voice_assistant()

screen = st.sidebar.radio("Pantalla", ["Sesión", "Evolución"], key="pantalla")
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
    with st.container(key="hero"):
        st.markdown(
            "<div class='eyebrow'>VIS Open · Presencia y participación de las mujeres</div>",
            unsafe_allow_html=True,
        )
        title_col, pick_col = st.columns([3, 1])
        chosen = pick_col.selectbox(
            "Cambiar de vídeo", [s.session_id for s in sessions], key="sesion"
        )
        s = next(x for x in sessions if x.session_id == chosen)
        title_col.title(f"Sesión {s.session_id}")
        if s.synthetic:
            st.warning("SINTÉTICO: datos de ejemplo, no es una sesión real.")
        else:
            src = s.source or {}
            chips = ["Congreso de los Diputados", "Vídeo sin alterar"]
            st.markdown(
                "<div class='chips'>" + "".join(f"<span>{c}</span>" for c in chips if c) + "</div>",
                unsafe_allow_html=True,
            )
            st.caption(src.get("cita") or SOURCE_NOTICE)
            if src.get("url_origen"):
                st.markdown(f"[Fuente]({src['url_origen']})")
        st.info(METHOD_NOTICE)
    with st.container(key="nav"):
        st.markdown(
            "<nav class='secnav'>"
            "<a href='#sec-video'>Vídeo</a><a href='#sec-hitl'>Human in the loop</a>"
            "<a href='#sec-metricas'>Métricas</a><a href='#sec-audio'>Audio</a>"
            "<a href='#sec-vanalisis'>Análisis de vídeo</a><a href='#sec-descargas'>Descargas</a>"
            "</nav>",
            unsafe_allow_html=True,
        )

    video_file = video_path(s, DATA_DIR)
    minute_key = f"minuto_{s.session_id}"
    max_minute = s.timeline.duration_s / 60

    def go_to(seconds: float) -> None:
        st.session_state[minute_key] = min(seconds / 60, max_minute)

    with st.container(key="sec_video"):
        st.markdown("<span id='sec-video' class='anchor'></span>", unsafe_allow_html=True)
        # 1. El vídeo completo.
        if video_file:
            minute = st.number_input(
                "Ir al minuto", min_value=0.0, max_value=max_minute, step=1.0, key=minute_key
            )
            st.video(
                video_file,
                start_time=int(minute * 60),
                subtitles={SUBTITLE_LABEL: subtitles_vtt(s).encode("utf-8")},
            )
            st.caption(
                "Vídeo original del Congreso, sin alterar. Solo se ve en este equipo. "
                "Subtítulos para personas sordas: botón «CC» del reproductor (son automáticos, con "
                "nombres en clave, y pueden tener errores)."
            )
            st.download_button(
                "Descargar subtítulos (.vtt)",
                subtitles_vtt(s),
                file_name=f"subtitulos_{s.session_id}.vtt",
                mime="text/vtt",
            )
        else:
            st.info("El vídeo original no está en este equipo (`data/raw/`): solo se ve el texto.")

    with st.container(key="sec_hitl"):
        st.markdown("<span id='sec-hitl' class='anchor'></span>", unsafe_allow_html=True)
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
                "Escucha la muestra: valida **la voz que oyes**, no a las demás personas que "
                "salgan en la imagen. Pon mujer u hombre solo si lo tienes claro; si dudas, "
                "desconocido. "
                "El género cuenta cuando **las dos anotadoras** coinciden."
            )
        who = st.radio(
            "Anotadora",
            [1, 2],
            horizontal=True,
            format_func=lambda n: f"Anotadora {n}",
            key="anotadora",
        )

        codes = speaker_codes(s.timeline)
        folder = DATA_DIR / "processed" / s.session_id
        answers = annotator_answers(folder, who)  # lo que ya has validado tú, por voz
        cuts = review_cuts(s, [r.speaker_id for r in pending])
        all_voices = voices_to_review(folder)
        decided = sum(
            1 for r in all_voices if r.speaker_id in answers or r.speaker_id in s.confirmed
        )
        if all_voices:
            st.progress(
                decided / len(all_voices),
                text=f"Has validado {decided} de {len(all_voices)} voces",
            )
        if cuts:
            st.caption(
                f"{len(cuts)} cortes, uno a continuación de otro. Cuando validas una voz en un "
                "corte, vale para todos los cortes de esa voz."
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
                mp4 = make_clip(
                    video_file, start, stop, DATA_DIR / "clips", f"{s.session_id}_{sid}"
                )
                if mp4:
                    clip.video(
                        mp4,  # solo esos segundos
                        subtitles={SUBTITLE_LABEL: subtitles_vtt(s, start, stop).encode("utf-8")},
                    )
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
                        folder,
                        who,
                        sid,
                        gender,
                        confidence,
                        notes,
                        current_user or f"anotadora_{who}",
                    )
                    st.rerun()  # los demás cortes de esa voz pasan a «ya validada»

    with st.container(key="sec_metricas"):
        st.markdown("<span id='sec-metricas' class='anchor'></span>", unsafe_allow_html=True)
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

    with st.container(key="sec_audio"):
        st.markdown("<span id='sec-audio' class='anchor'></span>", unsafe_allow_html=True)
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
    with st.container(key="sec_vanalisis"):
        st.markdown("<span id='sec-vanalisis' class='anchor'></span>", unsafe_allow_html=True)
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
    with st.container(key="sec_descargas"):
        st.markdown("<span id='sec-descargas' class='anchor'></span>", unsafe_allow_html=True)
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


def speak_and_scroll() -> None:
    """Dice la respuesta en voz alta (voz del navegador, es-ES) y lleva la vista a la sección."""
    import json as _json

    import streamlit.components.v1 as components

    def _safe(value) -> str:  # JSON sin «<»: nada puede cerrar el <script>
        return _json.dumps(value).replace("<", "\\u003c")

    reply = st.session_state.get("voz_respuesta")
    if not reply:
        return
    if not st.session_state.pop("voz_nueva", False):
        return
    anchor = st.session_state.get("voz_ancla")
    components.html(
        "<script>"
        f"const t={_safe(reply)},a={_safe(anchor)};"
        "const d=window.parent.document;"
        "if(a){setTimeout(()=>{const e=d.getElementById(a);"
        "if(e)e.scrollIntoView({behavior:'smooth'})},400)}"
        "const u=new SpeechSynthesisUtterance(t);u.lang='es-ES';"
        "window.parent.speechSynthesis.cancel();window.parent.speechSynthesis.speak(u);"
        "</script>",
        height=0,
    )


speak_and_scroll()
