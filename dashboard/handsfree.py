"""Modo manos libres del asistente de voz: el panel escucha solo, sin pulsar nada.

Un componente de Streamlit (v2, inline) que en el navegador:
- pide el micrófono una sola vez (con cancelación de eco y de ruido del navegador);
- detecta cuándo empiezas a hablar y cuándo paras (detector propio, `dashboard/vad.js`; el
  silencio que cierra la frase es ajustable de 1 a 5 s);
- manda esa frase como WAV a Python, que la transcribe como cualquier otra orden;
- se pausa mientras el asistente contesta y vuelve a escuchar cuando termina, con un pitido
  corto al cortar y otro al volver a escuchar (para quien no ve la pantalla).

Solo viaja tu voz diciendo una orden, igual que con el botón del micrófono. La orden «desactiva el
modo manos libres» lo apaga. La frase llega como dato no fiable: se valida el tamaño y la cabecera
WAV y luego pasa por el mismo camino cerrado de órdenes que el resto.
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

MAX_B64_CHARS = 6_000_000  # una frase de 30 s a 16 kHz son ~1,3 MB en base64

_VAD = (Path(__file__).parent / "vad.js").read_text("utf-8").replace("export ", "")

_HTML = """
<div class="hf">
  <button id="tg" type="button" aria-pressed="false">🎧 Modo manos libres</button>
  <div id="st" role="status" aria-live="polite">Apagado</div>
  <div id="lv" aria-hidden="true"><i></i></div>
</div>
"""

_CSS = """
.hf { display: flex; flex-direction: column; gap: 6px; font-family: inherit; }
button { width: 100%; padding: 0.6rem 1rem; border: 0; border-radius: 999px; cursor: pointer;
  font: inherit; font-weight: 600; color: #fff;
  background: linear-gradient(135deg, #1f4fd8, #1f8fb0);
  box-shadow: 0 6px 18px rgba(31, 79, 216, 0.3); }
button[aria-pressed="true"] { background: linear-gradient(135deg, #0b7a4b, #1f8fb0); }
button:focus-visible { outline: 3px solid #1f4fd8; outline-offset: 3px; }
#st { font-size: 1rem; color: var(--st-text-color, inherit); min-height: 1.4em; }
#lv { height: 6px; border-radius: 3px; background: rgba(31, 79, 216, 0.15); overflow: hidden; }
#lv i { display: block; height: 100%; width: 0; background: #1f8fb0; transition: width 80ms; }
"""

_JS = """
/*VAD*/
const TEXT = {
  off: 'Apagado',
  listen: 'Escuchando… habla cuando quieras',
  hear: 'Te oigo…',
  processing: 'Procesando…',
  speaking: 'El asistente contesta…',
}

function beep(ctx, hz, ms) {
  try {
    const o = ctx.createOscillator()
    const g = ctx.createGain()
    o.frequency.value = hz
    g.gain.value = 0.06
    o.connect(g)
    g.connect(ctx.destination)
    o.start()
    o.stop(ctx.currentTime + ms / 1000)
  } catch (e) {}
}

export default function (component) {
  const { data, parentElement, setStateValue, setTriggerValue } = component
  // Un único estado en la página: si Streamlit vuelve a montar el componente, el micrófono sigue.
  const s = (window.__vozHf = window.__vozHf || {
    phase: 'off', ctx: null, stream: null, vad: null, timer: null, sentSeq: 0,
  })
  s.btn = parentElement.querySelector('#tg')
  s.status = parentElement.querySelector('#st')
  s.level = parentElement.querySelector('#lv i')
  s.data = data
  s.setStateValue = setStateValue
  s.setTriggerValue = setTriggerValue

  const say = (key) => { s.status.textContent = TEXT[key] }
  const speaking = () =>
    window.speechSynthesis && (speechSynthesis.speaking || speechSynthesis.pending)

  function resume() {
    if (s.vad) s.vad.reset()
    s.phase = 'listen'
    say('listen')
    if (s.ctx) beep(s.ctx, 600, 70)
  }

  function stop() {
    if (s.timer) clearInterval(s.timer)
    s.timer = null
    if (s.stream) s.stream.getTracks().forEach((t) => t.stop())
    if (s.ctx) s.ctx.close().catch(() => {})
    s.stream = s.ctx = s.vad = null
    s.phase = 'off'
    s.btn.setAttribute('aria-pressed', 'false')
    s.btn.textContent = '🎧 Modo manos libres'
    say('off')
    s.level.style.width = '0'
    s.setStateValue('on', false)
  }

  function send(samples) {
    const wav = encodeWav(downsample(samples, s.ctx.sampleRate, 16000), 16000)
    s.sentSeq = s.data.seq
    s.t0 = Date.now()
    s.phase = 'processing'
    say('processing')
    beep(s.ctx, 880, 80)
    s.setTriggerValue('audio', { b64: toBase64(wav), id: Date.now() })
  }

  async function start() {
    try {
      s.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1,
        },
      })
    } catch (e) {
      s.status.textContent = 'No tengo permiso para usar el micrófono'
      return
    }
    s.ctx = new (window.AudioContext || window.webkitAudioContext)()
    await s.ctx.resume()
    s.vad = createVad({ sampleRate: s.ctx.sampleRate, silenceMs: (s.data.silence_s || 2) * 1000 })
    const src = s.ctx.createMediaStreamSource(s.stream)
    const proc = s.ctx.createScriptProcessor(2048, 1, 1)
    const mute = s.ctx.createGain()
    mute.gain.value = 0
    src.connect(proc)
    proc.connect(mute)
    mute.connect(s.ctx.destination)
    proc.onaudioprocess = (e) => {
      const input = new Float32Array(e.inputBuffer.getChannelData(0))
      s.level.style.width = Math.min(100, rms(input) * 400) + '%'
      if (s.phase !== 'listen' || speaking()) {
        if (s.vad) s.vad.reset()
        return
      }
      for (const ev of s.vad.push(input)) {
        if (ev.type === 'start') { say('hear') }
        else if (ev.type === 'discard') { say('listen') }
        else if (ev.type === 'end') { send(ev.samples) }
      }
    }
    s.btn.setAttribute('aria-pressed', 'true')
    s.btn.textContent = '⏹ Detener el modo manos libres'
    s.setStateValue('on', true)
    resume()
    s.timer = setInterval(() => {
      const now = Date.now()
      if (s.phase === 'processing') {
        if (s.data.seq > s.sentSeq) { s.phase = 'await'; s.t1 = now }
        else if (now - s.t0 > 25000) resume()
      } else if (s.phase === 'await') {
        if (speaking()) { s.phase = 'speaking'; say('speaking') }
        else if (now - s.t1 > 1800) resume() // no hay respuesta hablada
      } else if (s.phase === 'speaking') {
        if (!speaking()) { s.phase = 'cooldown'; s.t2 = now } // cola de eco
      } else if (s.phase === 'cooldown') {
        if (now - s.t2 > 700) resume()
      }
    }, 150)
  }

  const on = s.phase !== 'off'
  s.btn.setAttribute('aria-pressed', String(on))
  s.btn.textContent = on ? '⏹ Detener el modo manos libres' : '🎧 Modo manos libres'
  const shown = { listen: 'listen', speaking: 'speaking', cooldown: 'speaking' }
  say(on ? shown[s.phase] || 'processing' : 'off')
  s.btn.onclick = () => (s.phase === 'off' ? start() : stop())
  if (s.vad) s.vad.setSilence((data.silence_s || 2) * 1000)
  if (s.forceOff !== undefined && data.force_off !== s.forceOff && s.phase !== 'off') stop()
  s.forceOff = data.force_off
  window.addEventListener('pagehide', () => { if (s.phase !== 'off') stop() }, { once: true })
}
""".replace("/*VAD*/", _VAD)

_COMPONENT = st.components.v2.component("voz_manos_libres", html=_HTML, css=_CSS, js=_JS)


def handsfree(*, key: str, silence_s: float, seq: int, force_off: int, on_audio, on_on):
    """Monta el componente. `seq` sube con cada frase atendida; `force_off`, al apagarlo por voz."""
    return _COMPONENT(
        key=key,
        data={"silence_s": float(silence_s), "seq": int(seq), "force_off": int(force_off)},
        on_audio_change=on_audio,
        on_on_change=on_on,
    )


def decode_audio(payload) -> bytes:
    """WAV de la frase, validado: dato no fiable que llega del navegador."""
    if not isinstance(payload, dict) or not isinstance(payload.get("b64"), str):
        raise ValueError("audio no válido")
    b64 = payload["b64"]
    if not b64 or len(b64) > MAX_B64_CHARS:
        raise ValueError("audio vacío o demasiado largo")
    wav = base64.b64decode(b64, validate=True)
    if wav[:4] != b"RIFF" or wav[8:12] != b"WAVE":
        raise ValueError("el audio no es un WAV")
    return wav
