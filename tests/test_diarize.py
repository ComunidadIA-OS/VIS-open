import importlib.util
import os
import sys
from types import ModuleType, SimpleNamespace

import pytest

from pipeline.diarize import DEFAULT_MODEL, DiarizeConfig, SpeakerTurn, diarize, normalize_labels


def test_config_requires_token():
    with pytest.raises(RuntimeError, match="HF_TOKEN"):
        DiarizeConfig.from_env({"HF_TOKEN": "  "})


def test_config_from_env_and_hidden_token():
    cfg = DiarizeConfig.from_env({"HF_TOKEN": "fake-token-for-tests", "WHISPER_DEVICE": "cuda"})
    assert cfg.model == DEFAULT_MODEL and cfg.device == "cuda"
    assert "fake-token-for-tests" not in repr(cfg)


def test_normalize_labels_by_first_appearance():
    turns = normalize_labels([(5.0, 6.0, "B"), (0.0, 2.0, "speaker_7"), (2.5, 4.0, "B")])
    assert turns == [
        SpeakerTurn(0.0, 2.0, "SPEAKER_00"),
        SpeakerTurn(2.5, 4.0, "SPEAKER_01"),
        SpeakerTurn(5.0, 6.0, "SPEAKER_01"),
    ]


def test_normalize_labels_limit():
    with pytest.raises(ValueError, match="100 voces"):
        normalize_labels([(float(i), i + 0.5, f"s{i}") for i in range(101)])


class _FakeAnnotation:
    def itertracks(self, yield_label):
        assert yield_label
        yield SimpleNamespace(start=1.0, end=3.0), "t1", "SPEAKER_05"
        yield SimpleNamespace(start=0.0, end=1.0), "t0", "SPEAKER_02"


def test_diarize_with_fake_pyannote(monkeypatch, sine_wav):
    seen = {}

    class FakePipeline:
        @staticmethod
        def from_pretrained(model, token):
            seen.update(model=model, token=token)
            return FakePipeline()

        def to(self, device):
            seen["device"] = device

        def __call__(self, path):
            return SimpleNamespace(speaker_diarization=_FakeAnnotation())  # formato pyannote 4

    pyannote_audio = ModuleType("pyannote.audio")
    pyannote_audio.Pipeline = FakePipeline
    monkeypatch.setitem(sys.modules, "pyannote", ModuleType("pyannote"))
    monkeypatch.setitem(sys.modules, "pyannote.audio", pyannote_audio)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(device=lambda d: f"device:{d}"))
    monkeypatch.delenv("PYANNOTE_METRICS_ENABLED", raising=False)
    monkeypatch.setattr("pipeline.diarize.load_waveform", lambda p: {"waveform": None})

    turns = diarize(sine_wav, DiarizeConfig(token="fake"))
    assert seen == {"model": DEFAULT_MODEL, "token": "fake", "device": "device:cpu"}
    assert os.environ["PYANNOTE_METRICS_ENABLED"] == "0"
    assert turns == [SpeakerTurn(0.0, 1.0, "SPEAKER_00"), SpeakerTurn(1.0, 3.0, "SPEAKER_01")]


@pytest.mark.skipif(
    importlib.util.find_spec("pyannote") is None or not os.environ.get("HF_TOKEN"),
    reason="pyannote.audio no instalado o falta HF_TOKEN; se prueba en la VM",
)
def test_real_pyannote_on_synthetic_tone(sine_wav):
    turns = diarize(sine_wav, DiarizeConfig.from_env())
    assert all(t.end_s >= t.start_s for t in turns)


def test_load_waveform_shape_and_range(sine_wav):
    torch = pytest.importorskip("torch")
    from pipeline.diarize import load_waveform

    out = load_waveform(sine_wav)
    assert out["sample_rate"] == 16_000
    assert out["waveform"].shape == (1, 32_000) and out["waveform"].dtype == torch.float32
    assert float(out["waveform"].abs().max()) <= 1.0
