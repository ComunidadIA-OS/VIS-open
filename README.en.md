# VIS Open

*[Versión en español: README.md](README.md). The detailed documentation in `docs/` is in Spanish.*

**How much space do women take up in parliamentary debate?**

***Holding a seat is not the same as having the floor.***

VIS Open measures whether the presence of women in Parliament also translates into participation and prominence: who speaks, for how long, in what proportion, and who holds the most visible turns.

VIS Open is an open-source tool that measures the presence and participation of women in recorded sessions, from their audio and video, without facial recognition. The first use case is the sessions of the Spanish Congress of Deputies (Congreso de los Diputados).

Project by Team 6 in the «Mujeres por la IA Abierta» (Women for Open AI) challenge (SEDIA, Comunidad IA de Código Abierto).

**Explainer video (about 5 min, in Spanish):** [download `VIS_Open_video_explicativo_26oct.mp4`](https://github.com/ComunidadIA-OS/VIS-open/releases/download/video-explicativo-2026-10-26/VIS_Open_video_explicativo_26oct.mp4) · [Release page](https://github.com/ComunidadIA-OS/VIS-open/releases/tag/video-explicativo-2026-10-26). AI-generated voice (ElevenLabs).

**Full presentation (20 slides, with notes, in Spanish):** [download the PowerPoint](https://github.com/ComunidadIA-OS/VIS-open/releases/download/presentacion-2026-10-30/260128.VIS.Open.Presentacion.del.reto.pptx) · [Release page](https://github.com/ComunidadIA-OS/VIS-open/releases/tag/presentacion-2026-10-30)

**Short presentation with video (final, 04/11/2026, 9 slides, in Spanish):** [download `Video_Presentacion_04112026.pptx`](https://github.com/ComunidadIA-OS/VIS-open/releases/download/presentacion-corta-2026-11-04/Video_Presentacion_04112026.pptx) · [Release page](https://github.com/ComunidadIA-OS/VIS-open/releases/tag/presentacion-corta-2026-11-04)

**Dashboard with the real sessions:** [https://efa4ebc2-44b3-48b1-92d5-ee25fd02e6f1-8501.notebook.gra.ai.cloud.ovh.net](https://efa4ebc2-44b3-48b1-92d5-ee25fd02e6f1-8501.notebook.gra.ai.cloud.ovh.net) (OVHcloud; access with the challenge token). The repository only shows synthetic sessions: real videos and results are not uploaded (GDPR and the Congress legal notice). The real sessions, with video, are in that dashboard. **To see the full dashboard on OVHcloud you need the challenge token** («Login with token» when you open the link).

## What it does

1. It takes a Congress session downloaded without any changes, with its record in the manifest (source, date and digital fingerprint).
2. It extracts the audio, transcribes it and separates each person who speaks.
3. It gives each voice an anonymous code (Persona 1, Persona 2…) and its gender **only from language cues** («la señora…», «el señor…», «tiene la palabra…»: "Madam…", "Sir…", "has the floor…"), with the sentence and the minute as evidence. No names are stored: in the evidence, the name is replaced by the code. If there is no cue, the gender stays `desconocido` (unknown) and goes to human review.
4. It analyses the video (visible people and screen time) from body posture, without recognising faces or inferring gender from the image.
5. It computes the metrics with deterministic code and shows them in a dashboard with a report for each session (PDF, transcript as CSV and subtitles).
6. **It can be used without seeing the screen or using a mouse:** the dashboard has a voice assistant and a hands-free mode (see below).

## Dashboard, voice assistant and accessibility

The dashboard (Streamlit, run locally) is a single page with cards: session video, **Human in the loop** (validating voices without a gender), metrics, audio and video analysis, and downloads. Also:

- **Voice assistant:** a window with an abstract avatar that follows spoken or typed commands from a **closed list** («enséñame la sesión cuatro», «léeme la transcripción del minuto 3:59», «explícame los resultados», «lanza el vídeo», «descarga el informe»…: show session four, read me the transcript at minute 3:59, explain the results, play the video, download the report). The figures it says are computed by the code; the content summary is written by Qwen and labelled as AI.
- **Human in the loop by voice:** «activa el vídeo de la persona 1» plays the clip, you say «es mujer, confianza media» (it is a woman, medium confidence) and «confirmo» (I confirm). The assistant never suggests a gender and **saves nothing without your confirmation**.
- **Hands-free mode (innovation):** one click and the dashboard listens on its own. A **home-made voice detector** (`dashboard/vad.js`, no libraries: spectrum, pitch and syllables) tells your voice apart from keystrokes, traffic, horns and the video's own audio; it pauses while it answers and pauses the video when you speak.
- **Accessibility:** subtitles for deaf people, voice and hands-free mode for blind people or people who cannot use a mouse, a page in Spanish with charts described for screen readers. See [`docs/DECLARACION_ACCESIBILIDAD.md`](docs/DECLARACION_ACCESIBILIDAD.md) and [`docs/ACCESIBILIDAD.md`](docs/ACCESIBILIDAD.md).

The audio of a spoken command is transcribed with `whisper-large-v3-turbo` through an OpenAI-compatible API (OVHcloud AI Endpoints in the challenge). Without that API the dashboard works the same: commands are typed. Which data leave the team, and to whom: [`docs/PROVEEDORES.md`](docs/PROVEEDORES.md).

> **Voice assistant and hands-free mode: beta.** Given the time of the challenge, they have only been tested with a few voices and in a few settings. Making them reliable would take weeks of testing and tuning with more voices, accents, noise and commands. No model is trained: the voice detector, the filters and the command list are tuned. Meanwhile, everything can also be done with mouse and keyboard. **Response time:** it depends on the command (switching session or playing the video answers in a few seconds; a summary goes through Qwen and takes longer), on the server load and on the network, because each spoken command is first transcribed with Whisper through the API.

## Metrics in this release

| ID | What it measures | How it is computed |
|---|---|---|
| M01 | Presence: how many people speak, by gender | Code |
| M02 | Speaking time by gender (with M02b, use of the allotted time) | Code |
| M03a | Interventions per question (quality check) | Code |
| M03b | Voices per question (quality check) | Code |
| M04 | Parity gap: women's % of speaking time minus their % among speakers | Code |
| M06 | Questions to the head of Government, by gender of the person asking | Code, from the Speaker's announcement |
| M09 | Questions received by women and men ministers | Code, from the Speaker's announcement; the language model (Qwen) gives the office each question is addressed to, with the literal quote |
| M13 | Share of time not attributed (data quality) | Code |

Full definitions in `docs/metricas.md`. **Validation** against the official list of interventions of the Congress (3 sessions, 87 people): 86 with the correct gender, 0 errors and 1 sent to human review; M06 matches in all 3 sessions and M09 in 2 of 3. Details in [`docs/EVALUACION.md`](docs/EVALUACION.md), which also includes the approximate WER against the official Diario de Sesiones (10.0 %, an upper bound) and a prompt-injection test with the real model. Discarded for the Congress: M05, M08, M10 and M14–M16 (for example, in the plenary nobody asks for the floor by raising a hand).

The figures are always computed by the code; the language model only classifies sentences (for example, whether an intervention is a question addressed to someone) and returns the sentence that supports it. If the sample is too small, the metric is marked «no concluyente» (inconclusive).

## Installation

Requirements: Python 3.11 or later (below 3.14 for the audio analysis), FFmpeg in the PATH and, for speaker separation, a Hugging Face token with the conditions of `pyannote/speaker-diarization-3.1` accepted.

```bash
pip install -e ".[dev]"        # code, tests and metrics
pip install -e ".[pipeline]"   # audio analysis (on the GPU machine)
cp .env.example .env           # fill in HF_TOKEN; WHISPER_DEVICE=cuda on the GPU
```

There are also Docker images for CPU and GPU in `docker/` (see `docs/PRUEBA_GPU.md`).

## Usage

```bash
make pipeline VIDEO=data/raw/sesion.mp4   # analyse one session
make test                                 # tests with synthetic data
make check                                # code style and tests
python -m sources.diputados                # composition of the chamber (M04 c), open data
python -m streamlit run dashboard/app.py  # the dashboard and the voice assistant
python -m pipeline.sesion --buscar        # detect and download new plenary sessions (row pending validation)
python -m pipeline.sesion --pendientes    # analyse the validated sessions still missing
node tests/vad.test.mjs                   # voice detector test (needs Node)
```

For the spoken voice assistant, in `.env`: `LLM_BASE_URL`, `LLM_API_KEY` and, optionally, `VOICE_ASR_MODEL` (default `whisper-large-v3-turbo`). The content summary uses `LLM_MODEL`. None of this goes into the repository.

A video must have its complete row in the manifest (see `docs/FUENTE_CONGRESO.md`); otherwise it is not analysed. New plenary sessions are detected automatically with `--buscar`; committees and other events are added by link (`--congreso-url` or `--hls-url`). Full flow in [`docs/FLUJO.md`](docs/FLUJO.md). Results are written to `data/processed/<video>/`, which is not uploaded to the repository.

## Structure

- `contracts/`: shared data formats (timeline, voices, human review and gestures).
- `pipeline/`: audio, transcription, speaker separation, timeline, gestures and entry point.
- `sources/`: Congress source and manifest validation.
- `decision/`: gender from language cues and decision engines (rules or language model).
- `metrics/`: registry and computation of the metrics.
- `evaluation/`: synthetic data and evaluation of the engines.
- `dashboard/`: Streamlit dashboard with the report of each session and the evolution across sessions (see `docs/PANEL.md`); `voice.py` (voice commands), `handsfree.py` and `vad.js` (hands-free mode and voice detector), `avatar.py` (assistant avatar).
- `docker/`: images for CPU and GPU.
- `docs/`: documentation in Spanish (work plan, model and dataset cards, responsible use, providers, accessibility, draft GDPR and AI Act plan, FAQ).

## Principles

- The AI never infers gender from the face or the voice. It comes from language cues, from a declared fact or from human review, and the report always says how it was obtained. `desconocido` (unknown) is always visible.
- Congress videos are used unaltered, citing the source and the date. They are never uploaded to the repository.
- No personal names are stored: each voice is identified by an anonymous code (Persona 1, Persona 2…).
- No audio, video, real transcripts or keys are uploaded to the repository.
- The voice assistant only follows a closed list of commands, treats what it hears as data (never as instructions), saves nothing without confirmation and labels anything generated by a model as AI.
- The system is language-model agnostic: it works with any open model through an OpenAI-compatible API, and also without a model (rules engine).

### Limitation: the gender we measure is not gender identity

- VIS Open measures gender **as it is named in the Chamber** («señora ministra», «el diputado»), checked against the official list: it is **attributed, not self-declared**, and it is not each person's gender identity, which only they can declare. That is why it uses three values (woman, man, `desconocido`) and cannot reflect non-binary identities.
- Only the person themselves can say «I am a woman». Assigning someone's gender without their consent, from how they are addressed or how they look, can get their identity wrong (*misgendering*). That is why VIS Open never publishes the gender of an identified person: each voice is an anonymous code, conclusions are aggregated (never about an identified person) and, when available, the gender the person has declared prevails (in our own recordings each participant declares it).
- Any model that assigns gender, whether rules, a language model or a person, can carry role biases and stereotypes («el presidente», «la portavoz»). Here the AI does not decide gender on its own: rules read the explicit form of address and, if there is none, the value stays `desconocido`.
- The risk of misgendering is highest in Human in the loop: the gender the annotators mark is **perceived** and can also be biased. To reduce this, it only counts when two annotators agree, `desconocido` is always a valid and visible answer, and every value carries its provenance.
- The figures describe presence and participation according to how people are named in the plenary; they are not a judgement about any of them.
- Limitation: even though no names are stored, a public office holder («la ministra de Hacienda») can be recognised from the session date. Details in `docs/MODEL_CARD.md`.

## Third-party components and licences

The full list, with versions, sources and verification date (last review: 21 Oct 2026), is in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md). The licence texts are in [`LICENSES/`](LICENSES/) and the attribution required by CC-BY-4.0, in [`NOTICE`](NOTICE). VIS Open does not redistribute any component: they are installed or downloaded from their sources. Main components:

| Component | Use | Licence |
|---|---|---|
| faster-whisper | Transcription | MIT |
| WhisperX | Word alignment | BSD-2-Clause |
| pyannote.audio and `speaker-diarization-3.1` | Speaker separation | MIT (gated model) |
| `wespeaker-voxceleb-resnet34-LM` | Voice embeddings to separate speakers | CC-BY-4.0 |
| FFmpeg | Audio extraction (external binary) | LGPL-2.1+ |
| pandas | Metrics | BSD-3-Clause |
| Pydantic | Data formats | MIT |
| `whisper-large-v3-turbo` (via the OVHcloud API) | Transcribing voice commands | MIT |
| Voice detector, avatar and dashboard components | Hands-free mode and assistant | Own code (Apache-2.0); uses browser features (Web Audio, WebGL, speech synthesis), no third-party libraries |
| OpenCV and MediaPipe | Video analysis (visible people, screen time) | Apache-2.0 |
| Streamlit and Altair | Dashboard and charts | Apache-2.0 and BSD-3-Clause |
| Qwen3.5 (4B and 9B) | Language model (M09 and summary) | Apache-2.0 |

## Roadmap

The detailed plan for this release, with tasks, owners, dates and dependencies, is in [`docs/PLAN_DE_TRABAJO.md`](docs/PLAN_DE_TRABAJO.md).

Production deployment plan: [`docs/PRODUCCION.md`](docs/PRODUCCION.md) (access, shared data, automation and cost per plenary session) and [`docs/BORRADOR_PRODUCCION_RGPD_AIACT.md`](docs/BORRADOR_PRODUCCION_RGPD_AIACT.md) (GDPR and AI Act).

Future work:

- **Automation:** check the automatic detection end to end with the first plenary session published: new video → manifest → human validation → analysis. It has already been tested with plenary session 203 (see [`docs/FLUJO.md`](docs/FLUJO.md)). Plenary sessions are detected automatically; events and committees are added by link.
- **Light fine-tuning of Qwen** with a development session (V008, 21/09/2022), different from the evaluation sessions, if it improves on the base model. The model is already evaluated with `modelo_por_pregunta` against the official list of interventions.
- Go from 3 to 6–10 sessions and, later, to the Congress archive, the Senate, the European Parliament, universities and conference rooms.
- More metrics (`docs/metricas.md`, future work): interruptions and calls to order (M07), topics by gender (M12), cuts by the Speaker (M18) and M09 controlling for the topic (the same ministry held by a woman and by a man).
- Pseudonymisation: codes per person rather than per word of the name (today two people sharing a surname share a code).
- Video analysis on a machine without a GPU, or in parallel with the transcription: it would halve the cost per plenary session (`docs/HERRAMIENTAS_Y_COSTES.md`).
- Voice assistant: test it with a screen reader and with users, more languages (Catalan, French) and a better synthetic voice.
- Measure speaker separation (DER) and the exact WER with a 5-minute stretch annotated by hand: the code exists (`evaluation/asr_diar.py`), the annotation is missing. The approximate WER against the Diario de Sesiones is already measured (10.0 %, an upper bound; `docs/EVALUACION.md`).
- Wider evaluation of speaker separation with the Albayzin metric and the Àgora corpus, if their licence allows it.

## Team

Sabrina (direction, architecture and AI model), Ivette (definition and validation of metrics) and Veru (data, metrics, dashboard and ethics).

## Licence

Apache-2.0. See [`LICENSE`](LICENSE), the notice in [`NOTICE`](NOTICE) and the third-party licence texts in [`LICENSES/`](LICENSES/).
