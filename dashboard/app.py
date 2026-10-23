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


def big(chart: alt.Chart, description: str = "") -> alt.Chart:
    """Letra legible en pantalla grande y, para lectores de pantalla, una descripción en español
    en lugar de las que Vega genera en inglés para cada eje, leyenda y barra."""
    return (
        chart.properties(description=description)
        .configure_axis(labelFontSize=20, titleFontSize=22, aria=False)
        .configure_legend(labelFontSize=20, titleFontSize=22, aria=False)
        .configure_mark(aria=False)
    )


def chart(c: alt.Chart, text: str) -> None:
    """Gráfico con su alternativa en texto (oculta a la vista, la lee el lector de pantalla)."""
    import html

    st.altair_chart(big(c, text), use_container_width=True)
    st.markdown(f"<p class='sr-only'>{html.escape(text)}</p>", unsafe_allow_html=True)


def say_rows(rows, label: str, value: str, unit: str) -> str:
    """«mujer 2,8 minutos; hombre 0 minutos…» a partir de una tabla."""
    from dashboard.voice import es_num

    return "; ".join(f"{r[label]} {es_num(float(r[value]))} {unit}" for _, r in rows.iterrows())


def page_a11y() -> None:
    """Idioma de la página (español, para que el lector no lea con voz inglesa) y nombres para
    los vídeos y la ventana del asistente, que Streamlit deja sin nombre."""
    import streamlit.components.v1 as components

    components.html(
        "<script>(function(){const d=window.parent.document;d.documentElement.lang='es';"
        "const fix=()=>{d.querySelectorAll('video').forEach((v)=>{if(!v.getAttribute('aria-label'))"
        "v.setAttribute('aria-label',v.closest('[role=dialog]')?'Corte de voz para validar'"
        ":'Vídeo de la sesión')});d.querySelectorAll('[role=dialog] iframe')"
        ".forEach((f)=>{f.title='Asistente de voz'})};fix();"
        "if(!d.__a11y){d.__a11y=new MutationObserver(fix);"
        "d.__a11y.observe(d.body,{childList:true,subtree:true})}})()</script>",
        height=0,
    )


COLORS = alt.Scale(
    domain=["mujer", "hombre", "desconocido", "sin_atribuir"],
    range=["#8e4b8b", "#2a7b8c", "#a7a39b", "#d9d5cc"],
)

SUBTITLE_LABEL = "Español (automático)"
SHORT_TITLES = {
    "M01": "M01 Presencia",
    "M02": "M02 Tiempo de palabra",
    "M02b": "M02b Uso del tiempo",
    "M03": "M03 Turnos",
    "M04": "M04 Brecha de paridad",
    "M06": "M06 Preguntas al Presidente",
    "M09": "M09 Preguntas recibidas",
    "M13": "M13 Sin atribuir",
}
METRIC_UNITS = {
    "M01": "personas",
    "M02": "%",
    "M02b": "%",
    "M03": "turnos por pregunta",
    "M04": "puntos",
    "M06": "%",
    "M13": "%",
}  # M09 es un cociente (1 = igual): sin unidad


def with_unit(key: str, valor: str) -> str:
    """«41.65» → «41,65 %»; «no concluyente» y «no aplica» quedan igual."""
    if not valor[:1].isdigit() and not valor.startswith("-"):
        return valor
    number = valor.replace(".", ",").replace("-", "−")
    return f"{number} {METRIC_UNITS[key]}" if key in METRIC_UNITS else number


# Qué es cada cifra, en una línea, bajo su tarjeta (definiciones de Ivette, docs/metricas.md).
METRIC_EXPLAINED = {
    "M01": "Personas distintas que intervienen, sin contar la Presidencia.",
    "M02": "% del tiempo de palabra de las mujeres, sobre el tiempo con género conocido.",
    "M02b": "% de intervenciones (una persona en una pregunta) que pasan de 160 s: "
    "150 s asignados + 10 s de tolerancia.",
    "M03": "Turnos por pregunta, sin la Presidencia. Lo esperado es de 3 a 6; "
    "fuera de ese rango hay que revisar la separación de voces.",
    "M04": "Puntos: % del tiempo de las mujeres menos % del de los hombres. "
    "Negativo = las mujeres hablan menos.",
    "M06": "% de las preguntas al Presidente del Gobierno que hacen mujeres.",
    "M09": "Preguntas por ministra frente a preguntas por ministro (1 = igual; menos de 1 = "
    "las ministras reciben menos). Solo descriptiva: también influye la actualidad de cada "
    "ministerio.",
    "M13": "% del tiempo de voz sin atribuir o con género desconocido (calidad del dato). "
    "Por encima del 20 % se avisa.",
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
    if act == "summary":
        from pipeline.envfile import load_dotenv

        load_dotenv()
        try:
            return voice.content_summary(sess, cache=ss)
        except Exception as exc:  # noqa: BLE001 - sin red o sin clave: se dice, no se cae
            why = str(exc) if isinstance(exc, ValueError) else f"{type(exc).__name__}: {exc}"[:140]
            return f"No he podido resumir la sesión: {why}."
    if act == "download":
        names = {
            "informe": ("el informe", "Descargar informe"),
            "transcripcion": ("la transcripción", "Descargar transcripción"),
            "subtitulos": ("los subtítulos", "Descargar subtítulos"),
        }
        if cmd.topic not in names:
            return "¿Qué descargo: el informe, la transcripción o los subtítulos?"
        ss["voz_descarga"] = names[cmd.topic][1]
        return f"Descargo {names[cmd.topic][0]}."
    if act == "handsfree_off":
        ss["voz_hf_off"] = ss.get("voz_hf_off", 0) + 1
        if cmd.topic == "bye":
            return "¡Hasta pronto! Apago el modo manos libres."
        return "Modo manos libres desactivado."
    if act in ("play_video", "stop_video"):
        ss["voz_video"] = act == "play_video"
        ss["voz_ancla"] = "sec-video"
        if act == "stop_video":
            ss["voz_vstop"] = ss.get("voz_vstop", 0) + 1  # el modo manos libres no lo reanuda
            return "Detengo el vídeo."
        return (
            f"Vídeo {current} seleccionado. " if cmd.session else ""
        ) + "Pongo el vídeo en marcha."
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
    if act == "set_annotator":
        ss["anotadora"] = cmd.person  # la misma elección que los botones 1 y 2 de la página
        ss["voz_estado"], ss["voz_cortes"] = None, None
        return f"Ahora validas como anotadora {cmd.person}."
    if act == "validate_person":
        redo = cmd.topic == "redo"
        cuts = voice.pending_cuts(sess, folder, who, redo=redo)
        mine = [c for c in cuts if c["code"] == f"Persona {cmd.person}"]
        if not mine:
            from dashboard.data import annotator_answers

            done = annotator_answers(folder, who)
            again = [c for c in voice.pending_cuts(sess, folder, who, redo=True) if c not in cuts]
            old = [c for c in again if c["code"] == f"Persona {cmd.person}"]
            if old:
                return (
                    f"Persona {cmd.person} ya la validaste como {done[str(old[0]['speaker_id'])]} "
                    f"(anotadora {who}). Para corregirla di «otra vez»; para validar como la "
                    "otra anotadora di «anotadora 2» o «anotadora 1»."
                )
            return f"Persona {cmd.person} no tiene voz pendiente de validar en la sesión {current}."
        ss.update(
            voz_cortes=mine + [c for c in cuts if c not in mine],
            voz_i=0,
            voz_estado="gender",
            voz_ancla="sec-hitl",
            voz_conf=cmd.confidence or "media",
            voz_play=mine[0],  # pone en marcha la prueba de sonido
        )
        return f"Reproduzco la prueba de {mine[0]['code']}. ¿Es mujer, hombre o desconocido?"
    if act in ("val_gender", "val_conf", "val_confirm", "val_cancel", "val_skip", "play_cut"):
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
        if act in ("val_gender", "val_conf"):
            if cmd.gender:
                ss["voz_genero"] = cmd.gender
            ss["voz_conf"] = cmd.confidence or ss.get("voz_conf", "media")
            ss["voz_estado"] = "confirm"
            if cmd.topic != "save":  # «es mujer, confirmo» guarda de una vez
                return (
                    f"Has dicho {ss['voz_genero']} para {cut['code']}, con confianza "
                    f"{ss['voz_conf']}. ¿Confirmas? Di «confirmo» o «cancela»."
                )
            act = "val_confirm"
        if act == "val_confirm":
            save_review(
                folder,
                who,
                str(cut["speaker_id"]),
                ss["voz_genero"],
                ss.get("voz_conf", "media"),
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
        ss.update(voz_cortes=rest, voz_i=0, voz_estado="gender", voz_conf="media")
        return done + voice.describe_cut(rest[0], 1, len(rest))
    return voice.answer(cmd, sess)


VIDEO_COMMANDS = ("stop_video", "handsfree_off")  # el resto sería el audio del vídeo
VIDEO_MAX_WORDS = 8  # una orden es corta; el discurso del vídeo, no


def _process_voice(text: str, during_video: bool = False, handsfree: bool = False) -> None:
    """Encaja lo dicho en una orden, la ejecuta y apunta la conversación.

    Con un vídeo sonando solo valen las órdenes de controlarlo: lo demás es, casi seguro, el audio
    del vídeo, y se ignora sin contestar.
    """
    from dashboard import voice

    ss = st.session_state
    ids = [x.session_id for x in sessions]
    if voice.is_echo(text, ss.get("voz_respuesta", "")):
        return  # el micrófono recogió la voz del propio asistente
    cmd = voice.parse_command(text, ids, ss.get("voz_estado"))
    if during_video and (cmd is None or cmd.action not in VIDEO_COMMANDS):
        if voice.stop_intent(text):  # con el vídeo sonando, Whisper oye mal: basta la intención
            cmd = voice.Command("stop_video")
    if during_video and (
        cmd is None
        or cmd.action not in VIDEO_COMMANDS
        or len(voice.normalize(text).split()) > VIDEO_MAX_WORDS
    ):
        # se apunta (sin hablar) para que se vea qué se oyó mientras sonaba el vídeo
        note = "(con el vídeo sonando solo atiendo «para el vídeo»)"
        ss["voz_historial"] = [*ss.get("voz_historial", []), [text, note]][-30:]
        return
    if cmd is None:  # en manos libres puede ser ruido o una charla ajena: sin regañar
        reply = "Si necesitas algo, indícamelo." if handsfree else "No te he entendido. Di «ayuda»."
    else:
        reply = run_voice(cmd, ids)
    ss["voz_respuesta"] = reply
    ss["voz_nueva"] = True  # el avatar habla en el próximo dibujo
    ss["voz_refrescar"] = True  # la página de fondo se vuelve a dibujar con la orden cumplida
    ss["voz_historial"] = [*ss.get("voz_historial", []), [text, reply]][-30:]


def on_voice_audio() -> None:
    """Cuando acaba la grabación del botón: voz -> texto (Whisper de OVH) -> orden."""
    audio = st.session_state.get("voz_audio")
    if audio is not None:
        _hear(audio.getvalue())


def on_voice_handsfree() -> None:
    """Frase que el modo manos libres cortó solo; `voz_seq` avisa de que ya está atendida."""
    from dashboard import handsfree

    ss = st.session_state
    try:
        payload = ss["voz_hf"].audio
        _hear(handsfree.decode_audio(payload), bool(payload.get("video")), handsfree=True)
    except Exception as exc:  # noqa: BLE001 - un audio roto no debe parar el modo
        reply = f"No he podido oír la orden: {exc}."[:160]
        ss["voz_respuesta"] = reply
        ss["voz_historial"] = [*ss.get("voz_historial", []), ["(audio)", reply]][-30:]
    finally:
        ss["voz_seq"] = ss.get("voz_seq", 0) + 1
        # esta orden ya provoca un redibujado completo: no hace falta un segundo (ahorra ~1 s)
        ss.pop("voz_refrescar", None)


def on_handsfree_on() -> None:
    if st.session_state["voz_hf"].on:
        st.session_state["voz_abierto"] = True  # se abre la ventana: se ve lo que se dice


def _hear(audio: bytes, during_video: bool = False, handsfree: bool = False) -> None:
    """Voz -> texto (Whisper de OVH) -> orden."""
    from dashboard import voice
    from pipeline.envfile import load_dotenv

    load_dotenv()  # LLM_BASE_URL y LLM_API_KEY del .env (nunca del repo)
    ss = st.session_state
    try:
        text = voice.transcribe(audio)
    except Exception as exc:  # noqa: BLE001 - sin red o sin clave: se dice, no se cae
        why = str(exc) if isinstance(exc, ValueError) else f"{type(exc).__name__}: {exc}"[:140]
        reply = f"No he podido oír la orden: {why}."
        ss["voz_respuesta"] = reply
        ss["voz_historial"] = [*ss.get("voz_historial", []), ["(audio)", reply]][-30:]
        return
    if text.strip():  # una transcripción vacía (ruido, teclas) no es una orden: se ignora
        _process_voice(text, during_video, handsfree)


def on_voice_text() -> None:
    text = st.session_state.get("voz_texto", "")
    st.session_state["voz_texto"] = ""
    if text.strip():
        _process_voice(text)


def _voice_closed() -> None:
    st.session_state["voz_abierto"] = False


@st.dialog("Asistente de voz", width="medium", on_dismiss=_voice_closed)
def voice_dialog() -> None:
    """Ventana delante de la página: avatar, micrófono y la conversación por escrito."""
    import streamlit.components.v1 as components

    from dashboard.avatar import avatar_html

    ss = st.session_state
    if ss.pop("voz_refrescar", False):
        st.rerun()  # dibuja la página de fondo con la orden cumplida y reabre esta ventana
    cut = ss.pop("voz_play", None)
    video = ss.pop("voz_video", None)  # True: lanzar el vídeo; False: pararlo
    download = ss.pop("voz_descarga", None)  # texto del botón de descarga a pulsar
    then = None
    if cut:
        then = {"op": "play", "sel": "[role=dialog] video", "delay": 400}
    elif download:
        then = {"op": "click", "text": download, "delay": 700}
    elif video is not None:
        then = {"op": "play" if video else "pause", "sel": ".st-key-sec_video video", "delay": 1000}
    components.html(
        avatar_html(
            ss.get("voz_respuesta"),
            ss.get("voz_ancla"),
            ss.pop("voz_nueva", False),
            then=then,  # el vídeo suena (o se para) según la orden, junto a lo que se dice
        ),
        height=220,
    )
    st.audio_input("Pulsa, habla y para", key="voz_audio", on_change=on_voice_audio)
    st.text_input("o escribe la orden", key="voz_texto", on_change=on_voice_text)
    st.caption(
        "Di «ayuda» para oír todo lo que puedo hacer. Soy un asistente de IA: las cifras las "
        "calcula el código y los resúmenes pueden tener errores."
    )
    for said, reply in reversed(ss.get("voz_historial", [])[-6:]):
        st.text(f"Tú: {said}")  # texto plano: nunca se interpreta
        st.text(f"Asistente: {reply}")
    current = ss.get("sesion", sessions[0].session_id)
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
            st.video(mp4)


def voice_button() -> None:
    from dashboard.handsfree import handsfree

    ss = st.session_state
    st.sidebar.button(
        "🎙 Abrir el asistente de voz",
        key="voz_btn",
        on_click=lambda: st.session_state.update(voz_abierto=True),
        help="Habla con el panel: te responde en voz alta y por escrito.",
    )
    with st.sidebar:
        st.slider(
            "Silencio que cierra la frase (s)",
            1.0,
            5.0,
            2.0,
            0.5,
            key="voz_silencio",
            help="Segundos callado para que el modo manos libres dé la frase por terminada.",
        )
        handsfree(
            key="voz_hf",
            silence_s=ss.get("voz_silencio", 2.0),
            seq=ss.get("voz_seq", 0),
            force_off=ss.get("voz_hf_off", 0),
            vstop=ss.get("voz_vstop", 0),
            on_audio=on_voice_handsfree,
            on_on=on_handsfree_on,
        )


if sessions:
    voice_button()
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
        st.markdown(
            "<span id='sec-video' class='anchor'></span>"
            "<h2 class='sr-only'>Vídeo de la sesión</h2>",
            unsafe_allow_html=True,
        )
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
                    with_unit(key, card["valor"]),
                    help=card["titulo"],  # el nombre completo, al pasar el ratón
                )
                if key in METRIC_EXPLAINED:
                    col.caption(METRIC_EXPLAINED[key])
        if why := inconclusive_reason(s):
            st.warning(why)
        for key, label in PENDING_METRICS.items():
            st.caption(f"{key} {label}: no disponible todavía")
        if s.referencia:
            a, b = s.referencia["a"], s.referencia["b"]
            partes = []
            if a["porcentaje"] is not None:
                partes.append(f"A (ese día) {a['porcentaje']:.1f} % · {a['mujeres']}/{a['total']}")
            if b["porcentaje"] is not None:
                partes.append(
                    f"B (legislatura) {b['porcentaje']:.1f} % · {b['mujeres']}/{b['total']}"
                )
            if partes:
                st.caption("Diputadas en la cámara: " + " · ".join(partes))
            if s.referencia["diferencia_puntos"] is not None:
                st.caption(f"Diferencia B − A: {s.referencia['diferencia_puntos']:+.1f} puntos.")
            for aviso in s.referencia["avisos"]:
                st.warning(aviso)
        elif s.camara_aviso:
            st.caption(f"Composición de la cámara: sin datos ({s.camara_aviso}).")

    with st.container(key="sec_audio"):
        st.markdown("<span id='sec-audio' class='anchor'></span>", unsafe_allow_html=True)
        st.header("Análisis de audio (transcripción y voces)")
        st.subheader("Tiempo de palabra por género")
        gt = gender_time_table(s)
        chart(
            alt.Chart(gt)
            .mark_bar()
            .encode(x="gender", y="minutos", color=alt.Color("gender", scale=COLORS)),
            "Gráfico de barras del tiempo de palabra por género: "
            + say_rows(gt, "gender", "minutos", "minutos")
            + ".",
        )
        st.subheader("Línea de tiempo")
        chart(
            alt.Chart(timeline_strip(s))
            .mark_bar(height=80)
            .encode(x="inicio_min", x2="fin_min", color=alt.Color("genero", scale=COLORS))
            .properties(height=130),
            f"Línea de tiempo de los {s.timeline.duration_s / 60:.0f} minutos de la sesión, "
            "coloreada por el género de quien habla. La transcripción de abajo tiene lo mismo en "
            "texto, en orden.",
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
                chart(
                    alt.Chart(video_people_series(s))
                    .mark_area(opacity=0.6, line=True)
                    .encode(x="minuto", y="personas"),
                    "Gráfico de área de las personas que ve la cámara por minuto: máximo "
                    f"{v['personas_visibles_max']} y mediana {v['personas_visibles_mediana']}.",
                )
                st.subheader("Tiempo en pantalla por género")
                st.caption("El género sale del audio, no de la imagen.")
                chart(
                    alt.Chart(vt[0])
                    .mark_bar()
                    .encode(x="genero", y="minutos", color=alt.Color("genero", scale=COLORS)),
                    "Gráfico de barras del tiempo en pantalla por género: "
                    + say_rows(vt[0], "genero", "minutos", "minutos")
                    + ".",
                )
                st.subheader("Pistas con más tiempo en pantalla")
                st.table(show_tracks(video_tracks_with_totals(s)).style.hide(axis="index"))
                st.caption(
                    "Pista: una persona seguida en la imagen (número interno, sin identificarla). "
                    "Tamaño medio: qué parte de la imagen ocupa de media (más grande = plano más "
                    "cercano). Centralidad: 1 si suele estar en el centro horizontal de la imagen, "
                    "0 si en el borde. El género sale del audio, nunca de la imagen."
                )
    with st.container(key="sec_descargas"):
        st.markdown(
            "<span id='sec-descargas' class='anchor'></span><h2 class='sr-only'>Descargas</h2>",
            unsafe_allow_html=True,
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
    from dashboard.voice import explain_evolution

    chart(
        alt.Chart(evolution_gender_table(sessions))
        .mark_bar()
        .encode(
            x=alt.X(
                "sesion",
                title="Sesión",
                sort=None,  # ya viene en orden de fecha
                axis=alt.Axis(labelAngle=0, labelExpr="split(datum.label, ' · ')"),
            ),
            y=alt.Y("porcentaje", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("gender", scale=COLORS),
            tooltip=["sesion", "gender", "porcentaje"],
        ),
        "Gráfico de barras. " + explain_evolution(sessions),
    )
    st.caption("Una sesión con todo «desconocido» aún no tiene género asignado: falta revisión.")
    evo = evolution_table(sessions).astype(object).fillna("no concluyente")
    names = {"sesion": "Sesión", "fecha": "Fecha"} | {
        k: f"{v} ({METRIC_UNITS[k]})" if k in METRIC_UNITS else v for k, v in SHORT_TITLES.items()
    }
    evo = evo.rename(columns={c: names.get(c, c) for c in evo.columns})
    st.table(evo.style.hide(axis="index").format(precision=2, na_rep="-"))
    st.markdown("**Qué es cada columna**")
    for key, text in METRIC_EXPLAINED.items():
        if names[key] in evo.columns:
            st.caption(f"**{SHORT_TITLES[key]}:** {text}")


if sessions and st.session_state.get("voz_abierto"):
    voice_dialog()

page_a11y()
