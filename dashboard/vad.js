// Detector de voz propio (sin librerías): decide qué es voz humana y qué es ruido.
// Lo usa el modo manos libres (dashboard/handsfree.py, que incrusta este fichero) y se prueba con
// Node (tests/vad.test.mjs). Recibe trozos de audio y avisa cuándo empieza y cuándo acaba una frase.
//
// Cada trozo se mira por su volumen y por su espectro (FFT): la voz tiene casi toda la energía
// entre 100 y 4000 Hz y es tonal; una tecla es un golpe ancho y agudo; el tráfico es un ruido
// grave; una bocina es un tono fijo. Al cerrar la frase se comprueba además que el volumen y el
// timbre cambian como lo hacen las sílabas: una bocina o un motor constante se descartan.

export function rms(chunk) {
  let s = 0
  for (let i = 0; i < chunk.length; i++) s += chunk[i] * chunk[i]
  return Math.sqrt(s / Math.max(1, chunk.length))
}

function fft(re, im) {
  const n = re.length
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1
    for (; j & bit; bit >>= 1) j ^= bit
    j ^= bit
    if (i < j) {
      ;[re[i], re[j]] = [re[j], re[i]]
      ;[im[i], im[j]] = [im[j], im[i]]
    }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (-2 * Math.PI) / len
    const wr = Math.cos(ang)
    const wi = Math.sin(ang)
    for (let i = 0; i < n; i += len) {
      let cr = 1
      let ci = 0
      for (let k = 0; k < len / 2; k++) {
        const a = i + k
        const b = a + len / 2
        const tr = re[b] * cr - im[b] * ci
        const ti = re[b] * ci + im[b] * cr
        re[b] = re[a] - tr
        im[b] = im[a] - ti
        re[a] += tr
        im[a] += ti
        const ncr = cr * wr - ci * wi
        ci = cr * wi + ci * wr
        cr = ncr
      }
    }
  }
}

// Rasgos de un trozo: parte de la energía en la banda de la voz (100-4000 Hz), tonalidad y
// centroide. Por debajo de 100 Hz solo hay rumor de tráfico y motores.
export function spectralShape(chunk, sr) {
  let n = 1
  while (n * 2 <= chunk.length) n *= 2
  const re = new Float64Array(n)
  const im = new Float64Array(n)
  let peak = 0
  let energy = 0
  for (let i = 0; i < n; i++) {
    const w = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (n - 1))
    re[i] = chunk[i] * w
    peak = Math.max(peak, Math.abs(chunk[i]))
    energy += chunk[i] * chunk[i]
  }
  fft(re, im)
  let total = 0
  let speech = 0
  let logSum = 0
  let bins = 0
  let centroidNum = 0
  for (let k = 1; k < n / 2; k++) {
    const f = (k * sr) / n
    const p = re[k] * re[k] + im[k] * im[k]
    total += p
    if (f >= 100 && f <= 4000) {
      speech += p
      logSum += Math.log(p + 1e-12)
      bins++
      centroidNum += f * p
    }
  }
  const mean = speech / Math.max(1, bins)
  const r = Math.sqrt(energy / n)
  return {
    speechRatio: total > 0 ? speech / total : 0,
    flatness: bins && mean > 0 ? Math.exp(logSum / bins) / mean : 1,
    centroid: speech > 0 ? centroidNum / speech : 0,
    crest: r > 0 ? peak / r : 0,
    periodicity: periodicity(chunk, sr),
  }
}

// Periodicidad de la voz: parecido de la señal consigo misma a un desfase de 3 a 12 ms (tono de
// 80 a 300 Hz). Las vocales valen 0,6-0,95; el ruido, el tráfico y las teclas, menos de 0,35.
function periodicity(chunk, sr) {
  const x = new Float32Array(chunk.length - 1)
  for (let i = 1; i < chunk.length; i++) x[i - 1] = chunk[i] - 0.97 * chunk[i - 1]
  const lo = Math.floor(sr / 300)
  const hi = Math.min(Math.floor(sr / 80), x.length - 2)
  let best = 0
  for (let lag = lo; lag <= hi; lag++) {
    let ab = 0
    let aa = 0
    let bb = 0
    for (let i = 0; i + lag < x.length; i++) {
      ab += x[i] * x[i + lag]
      aa += x[i] * x[i]
      bb += x[i + lag] * x[i + lag]
    }
    const r = aa > 0 && bb > 0 ? ab / Math.sqrt(aa * bb) : 0
    if (r > best) best = r
  }
  return best
}

const mean = (a) => a.reduce((x, y) => x + y, 0) / Math.max(1, a.length)
const variation = (a) => {
  const m = mean(a)
  return m > 0 ? Math.sqrt(mean(a.map((x) => (x - m) ** 2))) / m : 0
}

export function createVad(options) {
  const sr = options.sampleRate
  const cfg = {
    silenceMs: 2000, // silencio que cierra la frase
    minSpeechMs: 400, // menos voz que esto es un golpe o un clic: se descarta
    maxUtteranceMs: 30000, // tope de una frase
    preRollMs: 400, // se guarda lo anterior al inicio para no perder la primera sílaba
    startMs: 220, // voz sostenida necesaria para dar por empezada la frase (una tecla no llega)
    gapMs: 130, // huecos entre sílabas que no cortan el comienzo
    minThreshold: 0.015,
    noiseFactor: 3.5,
    minSpeechRatio: 0.55, // parte de la energía entre 100 y 4000 Hz
    minPeriodicity: 0.45, // la voz es periódica (tono de 80 a 300 Hz); el ruido no
    minEnergyVariation: 0.25, // la voz sube y baja; una bocina o un motor no
    minTimbreVariation: 0.04, // el timbre cambia de sílaba en sílaba
    ...options,
  }
  const base = { noiseFactor: cfg.noiseFactor, minThreshold: cfg.minThreshold }
  let state = 'wait'
  let noise = 0.008
  let candidate = []
  let candMs = 0
  let gapMs = 0
  let preroll = []
  let preMs = 0
  let buf = []
  let bufMs = 0
  let voicedMs = 0
  let sinceVoiceMs = 0
  let energies = []
  let centroids = []

  const ms = (c) => (c.length / sr) * 1000
  const threshold = () => Math.max(cfg.minThreshold, noise * cfg.noiseFactor)

  function reset() {
    state = 'wait'
    candidate = []
    candMs = 0
    gapMs = 0
    preroll = []
    preMs = 0
    buf = []
    bufMs = 0
    voicedMs = 0
    sinceVoiceMs = 0
    energies = []
    centroids = []
  }

  function looksLikeSpeech() {
    if (voicedMs < cfg.minSpeechMs) return false
    return (
      variation(energies) >= cfg.minEnergyVariation && variation(centroids) >= cfg.minTimbreVariation
    )
  }

  function finish(events) {
    if (looksLikeSpeech()) {
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
      events.push({
        type: 'discard',
        voicedMs,
        energyVariation: variation(energies),
        timbreVariation: variation(centroids),
      })
    }
    reset()
  }

  function push(chunk) {
    const events = []
    const level = rms(chunk)
    const d = ms(chunk)
    const shape = spectralShape(chunk, sr)
    const voiced =
      level > threshold() &&
      shape.speechRatio > cfg.minSpeechRatio &&
      shape.periodicity > cfg.minPeriodicity &&
      shape.crest < 7
    if (state === 'wait') {
      if (voiced) {
        candidate.push(chunk)
        candMs += d
        gapMs = 0
        if (candMs >= cfg.startMs) {
          state = 'speech'
          buf = [...preroll, ...candidate]
          bufMs = preMs + candMs
          voicedMs = candMs
          sinceVoiceMs = 0
          energies = [level]
          centroids = [shape.centroid]
          preroll = []
          preMs = 0
          candidate = []
          candMs = 0
          events.push({ type: 'start' })
        }
      } else if (candidate.length && gapMs + d <= cfg.gapMs) {
        candidate.push(chunk) // hueco corto entre sílabas: no corta el comienzo
        gapMs += d
      } else {
        candidate = []
        candMs = 0
        gapMs = 0
        if (level <= threshold()) noise = Math.min(0.05, noise * 0.97 + level * 0.03)
        preroll.push(chunk)
        preMs += d
        while (preroll.length > 1 && preMs - ms(preroll[0]) >= cfg.preRollMs) {
          preMs -= ms(preroll.shift())
        }
      }
    } else {
      buf.push(chunk)
      bufMs += d
      if (level > threshold() * 0.7 && (shape.periodicity > 0.3 || shape.speechRatio > 0.5)) {
        sinceVoiceMs = 0
        voicedMs += d
        energies.push(level)
        if (shape.centroid > 0) centroids.push(shape.centroid)
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
