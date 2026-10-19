import importlib.util
import sys
from types import SimpleNamespace

import pytest

from pipeline.transcribe import Segment, TranscribeConfig, transcribe


def test_config_defaults_cpu():
    cfg = TranscribeConfig.from_env({})
    assert (cfg.device, cfg.model, cfg.compute_type) == ("cpu", "small", "int8")
    assert cfg.language == "es" and cfg.align is True


def test_config_defaults_cuda():
    cfg = TranscribeConfig.from_env({"WHISPER_DEVICE": "cuda"})
    assert (cfg.model, cfg.compute_type) == ("large-v3", "float16")


def test_config_overrides():
    cfg = TranscribeConfig.from_env(
        {"WHISPER_MODEL": "tiny", "WHISPER_LANGUAGE": "", "WHISPER_ALIGN": "0"}
    )
    assert cfg.model == "tiny" and cfg.language is None and cfg.align is False


def test_config_rejects_bfloat16():
    with pytest.raises(ValueError, match="bfloat16"):
        TranscribeConfig.from_env({"WHISPER_DEVICE": "cuda", "WHISPER_COMPUTE_TYPE": "bfloat16"})


def test_config_rejects_unknown_device():
    with pytest.raises(ValueError, match="WHISPER_DEVICE"):
        TranscribeConfig.from_env({"WHISPER_DEVICE": "tpu"})


class _FakeWhisperModel:
    calls: dict = {}

    def __init__(self, model, device, compute_type):
        _FakeWhisperModel.calls = {"model": model, "device": device, "compute_type": compute_type}

    def transcribe(self, path, **kwargs):
        _FakeWhisperModel.calls["kwargs"] = kwargs
        words = [SimpleNamespace(probability=0.9), SimpleNamespace(probability=0.5)]
        segs = [
            SimpleNamespace(start=0.0, end=1.5, text=" Hola a todas ", words=words),
            SimpleNamespace(start=1.5, end=2.0, text="sí", words=[]),
        ]
        return iter(segs), SimpleNamespace(language="es")


def test_transcribe_with_fake_faster_whisper(monkeypatch, sine_wav):
    monkeypatch.setitem(
        sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=_FakeWhisperModel)
    )
    cfg = TranscribeConfig(align=False)
    segments = transcribe(sine_wav, cfg)
    assert _FakeWhisperModel.calls["compute_type"] == "int8"
    assert _FakeWhisperModel.calls["kwargs"]["language"] == "es"
    assert segments[0] == Segment(0.0, 1.5, "Hola a todas", 0.7, "faster-whisper:small")
    assert segments[1].confidence is None


def test_transcribe_aligns_with_fake_whisperx(monkeypatch, sine_wav):
    monkeypatch.setitem(
        sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=_FakeWhisperModel)
    )

    def fake_align(segs, model, metadata, audio, device, return_char_alignments):
        assert device == "cpu" and len(segs) == 2
        return {
            "segments": [
                {
                    "start": 0.1,
                    "end": 1.4,
                    "text": "Hola a todas",
                    "words": [{"score": 0.8}, {"word": "x"}],
                },
                {"text": "sin tiempos"},  # WhisperX no pudo alinearlo: se descarta
            ]
        }

    fake_whisperx = SimpleNamespace(
        load_align_model=lambda language_code, device: ("model", {"lang": language_code}),
        load_audio=lambda path: "audio",
        align=fake_align,
    )
    monkeypatch.setitem(sys.modules, "whisperx", fake_whisperx)
    segments = transcribe(sine_wav, TranscribeConfig())
    assert segments == [Segment(0.1, 1.4, "Hola a todas", 0.8, "faster-whisper:small+whisperx")]


def test_transcribe_without_faster_whisper(monkeypatch, sine_wav):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    with pytest.raises(RuntimeError, match="falta faster-whisper"):
        transcribe(sine_wav, TranscribeConfig())


@pytest.mark.skipif(
    importlib.util.find_spec("faster_whisper") is None,
    reason="faster-whisper no instalado (extra [pipeline]); se prueba en la VM",
)
def test_real_faster_whisper_on_synthetic_tone(sine_wav):
    # Descarga el modelo 'tiny' la primera vez. Un tono puro no tiene voz: basta con que no falle.
    segments = transcribe(sine_wav, TranscribeConfig(model="tiny", align=False))
    assert all(s.end_s >= s.start_s for s in segments)
