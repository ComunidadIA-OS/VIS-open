"""Seudonimización. Nombres INVENTADOS (Luna Ortega, Mateo Ruiz...); nada real."""

import pytest

from contracts import AnalysisEvent, AnalysisTimeline, EventType, Provenance, Speaker
from decision.pseudonymize import find_names, pseudonymize_timeline
from pipeline.analyze import analyze_timeline


def make(turns):
    events, t = [], 0.0
    for i, (sp, text) in enumerate(turns):
        events.append(
            AnalysisEvent(
                event_id=f"e{i}",
                type=EventType.SPEECH,
                start_s=t,
                end_s=t + 4,
                speaker_id=sp,
                text=text,
                confidence=0.9,
                provenance=Provenance.AI_INFERRED,
            )  # fmt: skip
        )
        t += 5
    ids = sorted({sp for sp, _ in turns if sp})
    return AnalysisTimeline(
        video_id="SINTETICO", duration_s=t + 1,
        speakers=[Speaker(speaker_id=s, name="Nombre Real") for s in ids], events=events,
    )  # fmt: skip


@pytest.mark.parametrize(
    ("text", "names"),
    [
        ("Tiene la palabra la señora Luna Ortega, cuando quiera.", ["Luna Ortega"]),
        ("El señor ministro Mateo Ruiz de la Vega ha dicho.", ["Mateo Ruiz de la Vega"]),
        ("Me llamo Ana Pardo y soy abogada.", ["Ana Pardo"]),
        ("Gracias, señor Presidente.", []),
        ("Señora Presidenta, buenos días.", []),
        ("Habla el ministro de Hacienda.", []),
        ("Tiene la palabra la señora.", []),
    ],
)
def test_find_names(text, names):
    assert [n for _, _, n in find_names(text)] == names


def test_floor_grant_name_becomes_next_voice_code():
    tl = make(
        [
            ("SPEAKER_00", "Tiene la palabra la señora Luna Ortega."),
            ("SPEAKER_01", "Gracias. Señora Ortega, gracias a usted."),
        ]
    )
    out, codes = pseudonymize_timeline(tl)
    assert codes == {"SPEAKER_00": "Persona 1", "SPEAKER_01": "Persona 2"}
    assert out.events[0].text == "Tiene la palabra la señora Persona 2."
    assert out.events[1].text == "Gracias. Señora Persona 2, gracias a usted."  # mismo apellido


def test_third_party_gets_a_stable_new_code():
    tl = make(
        [
            ("SPEAKER_00", "Tiene la palabra el señor Hugo Sala."),
            ("SPEAKER_01", "Como dijo la señora ministra Olga Reyes. Y repito, señora Reyes."),
        ]
    )
    out, _ = pseudonymize_timeline(tl)
    assert (
        out.events[1].text == "Como dijo la señora ministra Persona 3. Y repito, señora Persona 3."
    )


def test_no_name_survives_anywhere_and_speaker_name_cleared():
    tl = make(
        [
            ("SPEAKER_00", "Tiene la palabra la señora Luna Ortega."),
            ("SPEAKER_01", "Me llamo Luna Ortega. Estoy muy agradecida."),
        ]
    )
    out, _ = analyze_timeline(tl)[0], None
    dump = out.model_dump_json()
    for secret in ("Luna", "Ortega", "Nombre Real"):
        assert secret not in dump
    assert all(s.name is None for s in out.speakers)


def test_gender_cue_still_works_after_pseudonymizing():
    tl = make(
        [
            ("SPEAKER_00", "Tiene la palabra la señora Luna Ortega."),
            ("SPEAKER_01", "Gracias."),
        ]
    )
    out, review, summary = analyze_timeline(tl)
    assert {s.speaker_id: s.gender.value for s in out.speakers}["SPEAKER_01"] == "mujer"
    assert summary["voces"] == {"SPEAKER_00": "Persona 1", "SPEAKER_01": "Persona 2"}
    assert "Ortega" not in str(summary) and all("Ortega" not in (r.notes or "") for r in review)
    assert "Persona 2" in out.speakers[1].gender_evidence[0].phrase


def test_input_not_mutated_and_no_text_is_fine():
    tl = make([("SPEAKER_00", "Tiene la palabra la señora Luna Ortega."), ("SPEAKER_01", "Hola.")])
    pseudonymize_timeline(tl)
    assert "Luna" in tl.events[0].text and tl.speakers[0].name == "Nombre Real"
