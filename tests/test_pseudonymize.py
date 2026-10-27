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


def test_strict_mode_redacts_unlisted_capitalised_words_but_keeps_institutions():
    tl = make(
        [
            (
                "SPEAKER_00",
                "Gracias, Andrea. El Gobierno de España y el Grupo Parlamentario Popular.",
            ),
            ("SPEAKER_01", "Lo dijo la banquera Alcaraz. Agustio Itamillasquer presenta."),
        ]
    )
    out, _ = pseudonymize_timeline(tl)
    t0, t1 = out.events[0].text, out.events[1].text
    assert "Andrea" not in t0 and "Gobierno de España" in t0 and "Grupo Parlamentario Popular" in t0
    assert "Alcaraz" not in t1 and "Agustio" not in t1 and "Itamillasquer" not in t1
    assert t1.startswith("Lo dijo la banquera Persona")  # el inicio de frase no se toca


def test_sentence_initial_words_are_not_names():
    tl = make([("SPEAKER_00", "Hoy hablamos. Pues bien. ¿Crees que sí? Vosotros lo sabéis.")])
    out, _ = pseudonymize_timeline(tl)
    assert out.events[0].text == tl.events[0].text


def test_pseudonymizing_twice_is_stable():
    tl = make(
        [
            ("SPEAKER_00", "Tiene la palabra la señora Luna Ortega. Gracias, Andrea."),
            ("SPEAKER_01", "Hola."),
        ]
    )
    once, _ = pseudonymize_timeline(tl)
    twice, _ = pseudonymize_timeline(once)
    assert [e.text for e in once.events] == [e.text for e in twice.events]


def test_standalone_surname_as_a_whole_sentence_is_redacted_but_common_words_are_not():
    tl = make(
        [
            ("SPEAKER_00", "Uriarte."),
            ("SPEAKER_01", "Alcaraz. Gracias, presidenta. Gracias. Presidente."),
        ]
    )
    out, _ = pseudonymize_timeline(tl)
    assert "Uriarte" not in out.events[0].text and out.events[0].text.startswith("Persona")
    t1 = out.events[1].text
    assert "Alcaraz" not in t1 and "Gracias, presidenta. Gracias. Presidente." in t1


def test_strict_mode_keeps_acronyms_but_still_hides_surnames():
    from decision.pseudonymize import find_names

    text = "Habló con Alcaraz sobre el IVA, el PIB y la OPEP."
    assert [n for _, _, n in find_names(text, True)] == ["Alcaraz"]


@pytest.mark.parametrize(
    ("turns", "texts"),
    [
        # Whisper parte el nombre entre dos trozos de la misma voz
        (
            [("SPEAKER_00", "Pregunta de la diputada doña Luna"), ("SPEAKER_00", "Ortega, del PP")],
            ["Pregunta de la diputada doña Persona 2", ", del PP"],
        ),
        (
            [("SPEAKER_01", "Mire, señor"), ("SPEAKER_01", "Sala, yo creo que no.")],
            ["Mire, señor", "Persona 2, yo creo que no."],
        ),
        # ya seudonimizado (reanalizar): el resto del nombre tras el código se quita
        (
            [("SPEAKER_00", "doña Persona 52"), ("SPEAKER_00", "Ortega, del Grupo")],
            ["doña Persona 52", ", del Grupo"],
        ),
        ([("SPEAKER_00", "Persona 94 Cortés, del Grupo Mixto.")], ["Persona 94, del Grupo Mixto."]),
        # «Cortés» es apellido; «Cortes», institución
        (
            [("SPEAKER_00", "Doña Luna Ortega Cortés y las Cortes Generales.")],
            ["Doña Persona 2 y las Cortes Generales."],
        ),
        # apellido en minúscula tras un tratamiento; el cargo sí se queda
        (
            [("SPEAKER_01", "Señor sala, yo no le diré que no, señor presidente.")],
            ["Señor Persona 2, yo no le diré que no, señor presidente."],
        ),
    ],
)
def test_names_split_or_left_by_transcription_are_hidden(turns, texts):
    out, _ = pseudonymize_timeline(make(turns))
    assert [e.text for e in out.events] == texts
