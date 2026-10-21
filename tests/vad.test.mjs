// Prueba del detector de voz con audio sintético: node tests/vad.test.mjs
import assert from 'node:assert/strict'
import { createVad, downsample, encodeWav, toBase64 } from '../dashboard/vad.js'

const SR = 48000
const CHUNK = 2048
let phase = 0

function chunk(amp) {
  const c = new Float32Array(CHUNK)
  for (let i = 0; i < CHUNK; i++) c[i] = amp * Math.sin(phase++ * 0.12) + (Math.random() - 0.5) * 0.006
  return c
}

function run(vad, plan) {
  const events = []
  let t = 0
  for (const [seconds, amp] of plan) {
    for (let n = 0; n < (seconds * SR) / CHUNK; n++) {
      for (const e of vad.push(chunk(amp))) events.push({ ...e, at: t })
      t += (CHUNK / SR) * 1000
    }
  }
  return events
}

// 1) ruido, 1,5 s de voz y 4 s de silencio: empieza, y acaba tras ~2 s de silencio
let ev = run(createVad({ sampleRate: SR }), [[1, 0.004], [1.5, 0.3], [4, 0.004]])
assert.deepEqual(ev.map((e) => e.type), ['start', 'end'])
assert.ok(ev[0].at >= 900 && ev[0].at <= 1300, `empieza hacia 1 s (fue ${ev[0].at})`)
assert.ok(ev[1].at >= 4300 && ev[1].at <= 4800, `acaba ~2 s tras la voz (fue ${ev[1].at})`)
const spoken = ev[1].ms
assert.ok(spoken > 1800 && spoken < 3000, `la frase dura ~1,5 s + pre-roll y cola (fue ${spoken})`)

// 2) silencio de 5 s ajustable: no acaba con 2 s, sí con 5 s
let vad5 = createVad({ sampleRate: SR, silenceMs: 5000 })
ev = run(vad5, [[0.5, 0.004], [1, 0.3], [3, 0.004]])
assert.deepEqual(ev.map((e) => e.type), ['start'], 'con 5 s de silencio aún no cierra')
ev = run(vad5, [[3, 0.004]])
assert.deepEqual(ev.map((e) => e.type), ['end'])

// 3) un golpe corto (100 ms) no cuenta
ev = run(createVad({ sampleRate: SR }), [[1, 0.004], [0.1, 0.4], [3, 0.004]])
assert.ok(!ev.some((e) => e.type === 'end'), 'un golpe no produce frase')

// 4) una pausa corta dentro de la frase no la parte
ev = run(createVad({ sampleRate: SR }), [[0.5, 0.004], [1, 0.3], [1, 0.004], [1, 0.3], [3, 0.004]])
assert.deepEqual(ev.map((e) => e.type), ['start', 'end'])

// 5) el umbral se adapta a un ruido de fondo alto y constante
const noisy = createVad({ sampleRate: SR })
run(noisy, [[3, 0.03]])
assert.ok(noisy.threshold > 0.05, `umbral adaptado (fue ${noisy.threshold})`)

// 6) tope de frase: una voz continua se corta a los 30 s
ev = run(createVad({ sampleRate: SR }), [[0.5, 0.004], [40, 0.3]])
assert.ok(ev.some((e) => e.type === 'end'))

// 7) WAV: cabecera correcta, 16 kHz y base64
const wav = encodeWav(downsample(new Float32Array(SR), SR, 16000), 16000)
assert.equal(String.fromCharCode(...wav.slice(0, 4)), 'RIFF')
assert.equal(wav.length, 44 + 16000 * 2)
assert.ok(toBase64(wav).length > 1000)

console.log('vad: ok')

// 8) pulsaciones de teclado (ráfagas de ruido agudo cada 250 ms durante 4 s): no es voz
{
  const vad = createVad({ sampleRate: SR })
  const events = []
  for (let n = 0; n < (4 * SR) / CHUNK; n++) {
    const c = new Float32Array(CHUNK)
    const clicking = n % 6 < 2 // ~85 ms de clic cada ~250 ms
    for (let i = 0; i < CHUNK; i++) c[i] = (clicking ? 0.5 : 0.004) * (Math.random() * 2 - 1)
    events.push(...vad.push(c))
  }
  assert.ok(!events.some((e) => e.type === 'start'), 'las teclas no inician una frase')
}
console.log('vad teclado: ok')

// 9) con un vídeo sonando (modo estricto): el residuo del vídeo no cuenta, tu voz fuerte sí
{
  const vad = createVad({ sampleRate: SR })
  vad.setStrict(true)
  let events = run(vad, [[1, 0.004], [2, 0.03], [3, 0.004]]) // residuo bajo del vídeo
  assert.ok(!events.some((e) => e.type === 'start'), 'el residuo del vídeo no es voz')
  events = run(vad, [[1.2, 0.3], [3, 0.004]]) // hablas cerca del micrófono
  assert.deepEqual(events.map((e) => e.type), ['start', 'end'])
}
console.log('vad estricto: ok')
