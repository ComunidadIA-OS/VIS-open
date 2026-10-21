// Prueba del detector de voz: voz real sintetizada (tests/fixtures/voz) frente a ruidos típicos.
//   node tests/vad.test.mjs
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { createVad, downsample, encodeWav, toBase64 } from '../dashboard/vad.js'

const SR = 16000
const CHUNK = 512
const here = fileURLToPath(new URL('.', import.meta.url))

function loadWav(name) {
  const b = readFileSync(`${here}/fixtures/voz/${name}`)
  const v = new DataView(b.buffer, b.byteOffset, b.byteLength)
  const n = (b.length - 44) / 2
  const out = new Float32Array(n)
  for (let i = 0; i < n; i++) out[i] = v.getInt16(44 + i * 2, true) / 32768
  return out
}

let seed = 7
const rand = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32) * 2 - 1
const floor = (s) => Float32Array.from({ length: Math.floor(s * SR) }, () => 0.004 * rand())
const tone = (s, f, amp) =>
  Float32Array.from({ length: Math.floor(s * SR) }, (_, i) => amp * Math.sin((2 * Math.PI * f * i) / SR))
const join = (...parts) => {
  const out = new Float32Array(parts.reduce((n, p) => n + p.length, 0))
  let at = 0
  for (const p of parts) {
    out.set(p, at)
    at += p.length
  }
  return out
}
const mix = (a, b) => Float32Array.from(a, (x, i) => x + (b[i] ?? 0))
const gain = (a, g) => a.map((x) => x * g)

function run(vad, audio) {
  const events = []
  for (let i = 0; i + CHUNK <= audio.length; i += CHUNK) {
    for (const e of vad.push(audio.subarray(i, i + CHUNK))) events.push(e.type)
  }
  return events
}
const types = (audio, opts = {}) => run(createVad({ sampleRate: SR, ...opts }), audio)

// ---- ruidos --------------------------------------------------------------------------------
const noises = {
  'bocina (dos tonos fijos)': mix(tone(1.5, 420, 0.25), tone(1.5, 510, 0.25)),
  'bocina con pitidos': join(tone(0.35, 440, 0.4), floor(0.25), tone(0.35, 440, 0.4), floor(0.25)),
  'motor (sierra de 90 Hz)': Float32Array.from(
    { length: 3 * SR },
    (_, i) => 0.25 * ((((i * 90) / SR) % 1) - 0.5),
  ),
  'sirena (barrido)': Float32Array.from(
    { length: 3 * SR },
    (_, i) => 0.3 * Math.sin(2 * Math.PI * (700 * (i / SR) + 150 * Math.sin((2 * Math.PI * i) / SR))),
  ),
  'coche que pasa (grave)': (() => {
    let y = 0
    return Float32Array.from({ length: 4 * SR }, (_, i) => {
      y += 0.03 * (rand() - y) // paso bajo ~80 Hz
      return 3 * y * Math.sin((Math.PI * i) / (4 * SR))
    })
  })(),
  teclas: (() => {
    const a = new Float32Array(4 * SR)
    for (let k = 0; k < 16; k++) {
      for (let i = 0; i < 0.06 * SR; i++) a[Math.floor(k * 0.25 * SR) + i] = 0.5 * rand()
    }
    return a
  })(),
  'viento o aire (ruido plano)': Float32Array.from({ length: 3 * SR }, () => 0.06 * rand()),
  portazo: (() => {
    const a = new Float32Array(2 * SR)
    for (let i = 0; i < 0.12 * SR; i++) {
      a[Math.floor(0.5 * SR) + i] = 0.8 * rand() * Math.exp(-i / (0.03 * SR))
    }
    return a
  })(),
}
for (const [name, noise] of Object.entries(noises)) {
  const ev = types(join(floor(1), noise, floor(3)))
  assert.ok(!ev.includes('end'), `${name}: no debe pasar por voz (eventos: ${ev})`)
}
console.log(`ruidos rechazados: ${Object.keys(noises).length}`)

// ---- voz real ------------------------------------------------------------------------------
const speeches = ['dashboard_sesion4.wav', 'para_el_video.wav', 'resumen.wav', 'es_un_hombre.wav']
for (const name of speeches) {
  const ev = types(join(floor(1), loadWav(name), floor(3)))
  assert.deepEqual(ev, ['start', 'end'], `${name}: voz detectada (eventos: ${ev})`)
}
console.log(`voces aceptadas: ${speeches.length}`)

// con ruido de fondo moderado (tráfico grave) también se oye la voz
const traffic = noises['coche que pasa (grave)']
for (const name of speeches) {
  const speech = loadWav(name)
  const ev = types(join(floor(1), mix(speech, gain(traffic.subarray(0, speech.length), 0.5)), floor(3)))
  assert.deepEqual(ev, ['start', 'end'], `${name} con tráfico de fondo (eventos: ${ev})`)
}
console.log('voz con tráfico de fondo: ok')

// ---- ajustes -------------------------------------------------------------------------------
const phrase = loadWav('resumen.wav')
const five = createVad({ sampleRate: SR, silenceMs: 5000 })
assert.deepEqual(run(five, join(floor(0.5), phrase, floor(3))), ['start'], 'con 5 s de silencio aún no cierra')
assert.deepEqual(run(five, floor(3)), ['end'])

const twice = types(join(floor(0.5), loadWav('para_el_video.wav'), floor(1), phrase, floor(3)))
assert.deepEqual(twice, ['start', 'end'], 'una pausa corta dentro de la frase no la parte')

const long = types(join(floor(0.5), ...Array.from({ length: 14 }, () => phrase)))
assert.ok(long.includes('end'), 'tope de frase')

// con un vídeo sonando (modo estricto): el residuo bajo no cuenta, tu voz fuerte sí
const strict = createVad({ sampleRate: SR })
strict.setStrict(true)
assert.ok(!run(strict, join(floor(1), gain(phrase, 0.04), floor(3))).includes('end'), 'residuo del vídeo')
assert.deepEqual(run(strict, join(floor(1), gain(phrase, 2.5), floor(3))), ['start', 'end'])

// ---- WAV -----------------------------------------------------------------------------------
const wav = encodeWav(downsample(new Float32Array(48000), 48000, 16000), 16000)
assert.equal(String.fromCharCode(...wav.slice(0, 4)), 'RIFF')
assert.equal(wav.length, 44 + 16000 * 2)
assert.ok(toBase64(wav).length > 1000)

console.log('vad: ok')

// ---- rapidez: el ruido de la sala no alarga la espera tras la frase --------------------------
{
  const speech = loadWav('resumen.wav')
  const room = Float32Array.from({ length: speech.length + 6 * SR }, () => 0.03 * rand())
  const audio = mix(join(floor(0.01), speech, new Float32Array(6 * SR)), room)
  const vad = createVad({ sampleRate: SR, silenceMs: 2000 })
  let endAt = null
  for (let i = 0; i + CHUNK <= audio.length; i += CHUNK) {
    for (const e of vad.push(audio.subarray(i, i + CHUNK))) {
      if (process.env.VAD_DEBUG) console.log(Math.round((i / SR) * 1000), e)
      if (e.type === 'end') endAt = (i / SR) * 1000
    }
  }
  const speechEnd = (speech.length / SR) * 1000
  assert.ok(endAt !== null, 'con ruido de sala la frase se cierra')
  assert.ok(endAt - speechEnd < 2600, `corta ~2 s después de hablar (tardó ${Math.round(endAt - speechEnd)} ms)`)
  console.log(`corte tras la frase con ruido de sala: ${Math.round(endAt - speechEnd)} ms`)
}
