"""Los datos sintéticos son deterministas, válidos y están marcados como SINTETICO."""

import csv
import json
from pathlib import Path

from contracts import AnalysisTimeline, EventType, GenderValue, ReviewRow, read_rows
from evaluation.synthetic import SCENARIOS, generate_timeline, write_dataset

SAMPLES = Path(__file__).parent.parent / "evaluation" / "synthetic" / "muestras"


def test_same_seed_same_bytes_and_other_seed_differs(tmp_path):
    a = write_dataset(tmp_path / "a", seed=1)
    b = write_dataset(tmp_path / "b", seed=1)
    c = write_dataset(tmp_path / "c", seed=2)
    assert [p.read_bytes() for p in a] == [p.read_bytes() for p in b]
    assert [p.read_bytes() for p in a] != [p.read_bytes() for p in c]


def test_committed_samples_match_the_generator(tmp_path):
    fresh = write_dataset(tmp_path)
    for path in fresh:
        committed = SAMPLES / path.name
        assert committed.read_text(encoding="utf-8") == path.read_text(encoding="utf-8"), (
            f"{path.name} desactualizado: ejecuta make synthetic"
        )


def test_timelines_are_valid_and_marked():
    for name, scenario in SCENARIOS.items():
        tl = generate_timeline(scenario)
        AnalysisTimeline.model_validate_json(tl.model_dump_json())
        assert tl.video_id == f"SINTETICO_{name}"
        assert all(e.source.startswith("SINTETICO") for e in tl.events)


def test_every_file_name_and_table_says_sintetico(tmp_path):
    for path in write_dataset(tmp_path):
        assert path.name.startswith("SINTETICO")
        if path.suffix == ".csv" and "revision" not in path.name:
            rows = list(csv.DictReader(path.open(encoding="utf-8")))
            assert rows and {r["origen"] for r in rows} == {"SINTETICO"}
        if path.name.endswith("_revision.csv"):
            assert all(r.video_id.startswith("SINTETICO") for r in read_rows(ReviewRow, path))
        if path.suffix == ".json":
            assert json.loads(path.read_text(encoding="utf-8"))["video_id"].startswith("SINTETICO")


def test_dataset_has_the_hard_cases():
    tls = {n: generate_timeline(s) for n, s in SCENARIOS.items()}
    genders = {s.gender for tl in tls.values() for s in tl.speakers}
    assert GenderValue.UNKNOWN in genders and GenderValue.WOMAN in genders
    unattributed = [
        e for e in tls["con_desconocidos"].events
        if e.type == EventType.SPEECH and e.speaker_id is None
    ]  # fmt: skip
    assert unattributed
    assert any(e.type == EventType.HAND_RAISE and e.granted is not None
               for e in tls["con_manos"].events)  # fmt: skip
    assert any(e.needs_review for e in tls["equilibrado"].events)  # confianza < 0,7


def test_summary_marks_insufficient_sample(tmp_path):
    write_dataset(tmp_path)
    rows = {r["video_id"]: r for r in csv.DictReader(
        (tmp_path / "SINTETICO_resumen_genero.csv").open(encoding="utf-8"))}  # fmt: skip
    assert rows["SINTETICO_muestra_insuficiente"]["conclusivo_ejemplo"] == "no"
    assert rows["SINTETICO_equilibrado"]["conclusivo_ejemplo"] == "si"
    assert float(rows["SINTETICO_pocas_mujeres"]["share_mujer_sobre_conocido"]) < 20
    assert float(rows["SINTETICO_con_desconocidos"]["unattributed_share"]) > 0.2
