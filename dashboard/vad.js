// Detector de voz propio (sin librerías): energía con umbral que se adapta al ruido de fondo.
// Lo usa el modo manos libres (dashboard/handsfree.py, que incrusta este fichero) y se prueba con
// Node (tests/vad.test.mjs). Recibe trozos de audio y avisa cuándo empieza y cuándo acaba una frase.

export function rms(chunk) {
  let s = 0
  for (let i = 0; i < chunk.length; i++) s += chunk[i] * chunk[i]
  return Math.sqrt(s / Math.max(1, chunk.length))
}

// Fracción de la energía por debajo de ~3 kHz y cresta (pico/energía): la voz tiene casi todo su
// cuerpo en graves y es sostenida; un golpe de tecla o un clic es agudo e impulsivo.
function voiceShape(chunk, state, sr) {
  const a = 1 - Math.exp((-2 * Math.PI * 3000) / sr)
  let low = 0
  let total = 0
  let peak = 0
  for (let i = 0; i < chunk.length; i++) {
    const x = chunk[i]
    state.y1 += a * (x - state.y1)
    state.y2 += a * (state.y1 - state.y2)
    low += state.y2 * state.y2
    total += x * x
    peak = Math.max(peak, Math.abs(x))
  }
  const n = Math.max(1, chunk.length)
  const r = Math.sqrt(total / n)
  return { lowRatio: total > 0 ? Math.sqrt(low / total) : 0, crest: r > 0 ? peak / r : 0 }
}

export function createVad(options) {
  const sr = options.sampleRate
  const cfg = {
    silenceMs: 2000, // silencio que cierra la frase
    minSpeechMs: 400, // menos voz que esto es un golpe o un clic: se descarta
    maxUtteranceMs: 30000, // tope de una frase
    preRollMs: 400, // se guarda lo anterior al inicio para no perder la primera sílaba
    startMs: 250, // voz sostenida necesaria para dar por empezada la frase (una tecla no llega)
    minThreshold: 0.015,
    noiseFactor: 3.5,
    ...options,
  }
  const base = { noiseFactor: cfg.noiseFactor, minThreshold: cfg.minThreshold }
  const filt = { y1: 0, y2: 0 }
  let state = 'wait'
  let noise = 0.008
  let candidate = []
  let candMs = 0
  let preroll = []
  let preMs = 0
  let buf = []
  let bufMs = 0
  let voicedMs = 0
  let sinceVoiceMs = 0

  const ms = (c) => (c.length / sr) * 1000
  const threshold = () => Math.max(cfg.minThreshold, noise * cfg.noiseFactor)

  function reset() {
    state = 'wait'
    candidate = []
    candMs = 0
    preroll = []
    preMs = 0
    buf = []
    bufMs = 0
    voicedMs = 0
    sinceVoiceMs = 0
  }

  function finish(events) {
    if (voicedMs >= cfg.minSpeechMs) {
      const trim = Math.max(0, Math.floor(((sinceVoiceMs - 300) / 1000) * sr)) // deja 300 ms de cola
      const total = buf.reduce((n, c) => n + c.length, 0)
      const samples = new Float32Array(Math.max(0, total - trim))
      let at = 0
      for (const c of buf) {
        const take = Math.min(c.length, samples.length - at)
        if (take <= 0) break
        samples.set(c.subarray(0, take), at)
        at += take
      }
      events.push({ type: 'end', samples, ms: (samples.length / sr) * 1000 })
    } else {
      events.push({ type: 'discard' })
    }
    reset()
  }

  function push(chunk) {
    const events = []
    const level = rms(chunk)
    const d = ms(chunk)
    const shape = voiceShape(chunk, filt, sr)
    const voiced = level > threshold() && shape.lowRatio > 0.55 && shape.crest < 7
    if (state === 'wait') {
      if (voiced) {
        candidate.push(chunk)
        candMs += d
        if (candMs >= cfg.startMs) {
          state = 'speech'
          buf = [...preroll, ...candidate]
          bufMs = preMs + candMs
          voicedMs = candMs
          sinceVoiceMs = 0
          preroll = []
          preMs = 0
          candidate = []
          candMs = 0
          events.push({ type: 'start' })
        }
      } else {
        candidate = []
        candMs = 0
        if (level <= threshold()) noise = Math.min(0.05, noise * 0.97 + level * 0.03)
        preroll.push(chunk)
        preMs += d
        while (preroll.length > 1 && preMs - ms(preroll[0]) >= cfg.preRollMs) preMs -= ms(preroll.shift())
      }
    } else {
      buf.push(chunk)
      bufMs += d
      if (level > threshold() * 0.7 && shape.lowRatio > 0.4) {
        sinceVoiceMs = 0
        voicedMs += d
      } else {
        sinceVoiceMs += d
      }
      if (sinceVoiceMs >= cfg.silenceMs || bufMs >= cfg.maxUtteranceMs) finish(events)
    }
    return events
  }

  return {
    push,
    reset,
    setSilence(value) {
      cfg.silenceMs = value
    },
    // Con un vídeo sonando: la voz tiene que destacar mucho más sobre el ruido.
    setStrict(on) {
      cfg.noiseFactor = on ? 7 : base.noiseFactor
      cfg.minThreshold = on ? 0.04 : base.minThreshold
    },
    get state() {
      return state
    },
    get threshold() {
      return threshold()
    },
  }
}

export function downsample(samples, from, to) {
  if (from === to) return samples
  const ratio = from / to
  const out = new Float32Array(Math.floor(samples.length / ratio))
  for (let i = 0; i < out.length; i++) {
    const x = i * ratio
    const j = Math.floor(x)
    const f = x - j
    out[i] = samples[j] * (1 - f) + (samples[Math.min(j + 1, samples.length - 1)] ?? 0) * f
  }
  return out
}

export function encodeWav(samples, sampleRate) {
  const out = new DataView(new ArrayBuffer(44 + samples.length * 2))
  const text = (o, s) => {
    for (let i = 0; i < s.length; i++) out.setUint8(o + i, s.charCodeAt(i))
  }
  text(0, 'RIFF')
  out.setUint32(4, 36 + samples.length * 2, true)
  text(8, 'WAVEfmt ')
  out.setUint32(16, 16, true)
  out.setUint16(20, 1, true) // PCM
  out.setUint16(22, 1, true) // mono
  out.setUint32(24, sampleRate, true)
  out.setUint32(28, sampleRate * 2, true)
  out.setUint16(32, 2, true)
  out.setUint16(34, 16, true)
  text(36, 'data')
  out.setUint32(40, samples.length * 2, true)
  for (let i = 0; i < samples.length; i++) {
    const v = Math.max(-1, Math.min(1, samples[i]))
    out.setInt16(44 + i * 2, v < 0 ? v * 0x8000 : v * 0x7fff, true)
  }
  return new Uint8Array(out.buffer)
}

export function toBase64(bytes) {
  let s = ''
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000))
  return btoa(s)
}
