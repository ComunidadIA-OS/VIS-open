"""Género por lenguaje. Frases sintéticas; reglas PENDIENTES DE VALIDAR POR IVETTE."""

import pytest

from contracts import (
    AnalysisEvent,
    AnalysisTimeline,
    EventType,
    GenderSource,
    GenderValue,
    Provenance,
    ReviewRow,
    Speaker,
    read_rows,
    write_rows,
)
from decision import (
    apply_assignments,
    assign_genders,
    build_gender_review_rows,
    extract_cues,
    load_rules,
)

W, M, U = GenderValue.WOMAN, GenderValue.MAN, GenderValue.UNKNOWN


def make(turns: list[tuple[str | None, str]], gap: float = 1.0) -> AnalysisTimeline:
    """turns = [(speaker_id, texto)]; cada turno dura 4 s con `gap` segundos entre ellos."""
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
        t += 4 + gap
    ids = sorted({sp for sp, _ in turns if sp})
    return AnalysisTimeline(
        video_id="SINTETICO", duration_s=t + 1,
        speakers=[Speaker(speaker_id=s) for s in ids], events=events,
    )  # fmt: skip


def gender_of(timeline: AnalysisTimeline, speaker_id: str):
    a = {x.speaker_id: x for x in assign_genders(timeline)}[speaker_id]
    return a.gender, a


@pytest.mark.parametrize(
    ("grant", "expected"),
    [
        ("Tiene la palabra la señora Pérez.", W),
        ("Tiene la palabra el señor Pérez, por tiempo de tres minutos.", M),
        ("Tiene la palabra la diputada Soto.", W),
        ("Tiene la palabra el ministro de Hacienda.", M),
        ("Tiene la palabra la portavoz del grupo.", W),
        ("Tiene la palabra el ponente.", M),
        ("TIENE LA PALABRA LA SEÑORA ministra", W),  # mayúsculas y tildes no importan
        ("Tiene la palabra doña Lucía.", W),
    ],
)
def test_floor_grant_assigns_next_voice(grant, expected):
    tl = make([("SPEAKER_00", grant), ("SPEAKER_01", "Gracias. Voy a hablar de presupuestos.")])
    gender, a = gender_of(tl, "SPEAKER_01")
    assert gender == expected
    ev = a.evidence[0]
    assert ev.method == "floor_grant" and ev.confidence >= 0.7
    assert ev.event_id == "e0" and ev.start_s == 0 and "palabra" in ev.phrase.lower()
    assert gender_of(tl, "SPEAKER_00")[0] == U  # quien da la palabra no recibe nada


def test_floor_grant_ignores_same_voice_and_picks_next_other_voice():
    tl = make(
        [
            ("SPEAKER_00", "Tiene la palabra la señora Pérez."),
            ("SPEAKER_00", "Un momento, por favor."),
            ("SPEAKER_01", "Muchas gracias."),
        ]
    )
    assert gender_of(tl, "SPEAKER_01")[0] == W


def test_floor_grant_too_far_is_ignored():
    tl = make(
        [("SPEAKER_00", "Tiene la palabra la señora Pérez."), ("SPEAKER_01", "Hola.")], gap=60
    )
    assert gender_of(tl, "SPEAKER_01")[0] == U


def test_floor_grant_with_mixed_signals_is_ambiguous():
    tl = make(
        [("SPEAKER_00", "Tiene la palabra el señor o la señora ponente."), ("SPEAKER_01", "Hola.")]
    )
    gender, a = gender_of(tl, "SPEAKER_01")
    assert gender == U and a.needs_review and "sin pistas" in a.reason


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Soy la diputada por Girona y quiero hablar.", W),
        ("Soy el portavoz de mi grupo.", M),
        ("Soy la portavoz de mi grupo.", W),
        ("Estoy muy agradecida por esta invitación.", W),
        ("Estoy agradecido por esta invitación.", M),
        ("Me siento realmente orgullosa de este trabajo.", W),
        ("Me siento orgulloso de este trabajo.", M),
    ],
)
def test_self_cues(text, expected):
    tl = make([("SPEAKER_00", text)])
    gender, a = gender_of(tl, "SPEAKER_00")
    assert gender == expected and a.confidence >= 0.7


def test_reference_to_third_party_is_not_a_cue():
    tl = make([("SPEAKER_00", "La señora ministra dijo que el diputado Ruiz estaba equivocado.")])
    gender, a = gender_of(tl, "SPEAKER_00")
    assert gender == U and a.evidence == [] and a.reason == "sin pistas en el lenguaje"


def test_no_cues_is_unknown_and_goes_to_review():
    tl = make([("SPEAKER_00", "Hoy hablaremos de la ley de presupuestos.")])
    gender, a = gender_of(tl, "SPEAKER_00")
    assert gender == U and a.needs_review and a.source == GenderSource.UNKNOWN


def test_contradictory_cues_are_unknown_and_go_to_review():
    tl = make(
        [
            ("SPEAKER_00", "Tiene la palabra la señora Pérez."),
            ("SPEAKER_01", "Estoy muy agradecido por la palabra."),
        ]
    )
    gender, a = gender_of(tl, "SPEAKER_01")
    assert gender == U and a.needs_review and a.reason == "pistas que se contradicen"
    assert {e.gender for e in a.evidence} == {W, M}  # la evidencia se conserva para la revisión


def test_weak_cue_is_not_assigned_but_is_suggested_for_review():
    tl = make([("SPEAKER_00", "Como diputada, creo que hay que votar.")])
    gender, a = gender_of(tl, "SPEAKER_00")
    assert gender == U and a.needs_review and a.suggestion == W
    assert a.evidence[0].method == "as_role" and a.evidence[0].confidence < 0.7


def test_apply_assignments_sets_source_and_evidence_and_validates():
    tl = make([("SPEAKER_00", "Tiene la palabra el señor Pérez."), ("SPEAKER_01", "Gracias.")])
    out = apply_assignments(tl, assign_genders(tl))
    sp = {s.speaker_id: s for s in out.speakers}
    assert sp["SPEAKER_01"].gender == M
    assert sp["SPEAKER_01"].gender_source == GenderSource.LANGUAGE_CUE
    assert sp["SPEAKER_01"].gender_evidence[0].minute == 0.0
    assert sp["SPEAKER_00"].gender == U and sp["SPEAKER_00"].gender_source == GenderSource.UNKNOWN
    assert tl.speakers[1].gender == U  # no muta la entrada
    AnalysisTimeline.model_validate_json(out.model_dump_json())  # ida y vuelta


def test_apply_does_not_overwrite_known_gender():
    tl = make([("SPEAKER_00", "Tiene la palabra el señor Pérez."), ("SPEAKER_01", "Gracias.")])
    tl.speakers[1] = Speaker(speaker_id="SPEAKER_01", gender=W, gender_source=GenderSource.DECLARED)
    out = apply_assignments(tl, assign_genders(tl))
    assert out.speakers[1].gender == W and out.speakers[1].gender_source == GenderSource.DECLARED


def test_review_csv_has_only_doubtful_voices_and_leaves_decision_blank(tmp_path):
    tl = make(
        [
            ("SPEAKER_00", "Tiene la palabra la señora Pérez."),
            ("SPEAKER_01", "Gracias. Soy la diputada por Lleida."),
            ("SPEAKER_02", "Como ministro, creo que sí."),
        ]
    )
    rows = build_gender_review_rows(tl, assign_genders(tl), "anotadora_1")
    assert {r.speaker_id for r in rows} == {
        "SPEAKER_00",
        "SPEAKER_02",
    }  # la 01 no necesita revisión
    row = next(r for r in rows if r.speaker_id == "SPEAKER_02")
    assert row.gender is None and "Motivo" in row.notes and "ministro" in row.notes
    path = tmp_path / "r.csv"
    write_rows(rows, ReviewRow, path)
    assert len(read_rows(ReviewRow, path)) == 2


def test_rules_come_from_config_and_have_no_proper_names():
    rules = load_rules("es")
    assert ["tiene", "la", "palabra"] in rules.floor_phrases
    assert rules.adjectives["agradecida"] == W and rules.adjectives["agradecido"] == M
    assert len(extract_cues(make([("SPEAKER_00", "Hola.")]), rules)) == 0


def test_unknown_language_has_no_rules():
    with pytest.raises(FileNotFoundError):
        load_rules("xx")


def test_floor_grant_when_diarization_merged_chair_and_speaker_is_only_a_suggestion():
    tl = make([("SPEAKER_00", "Tiene la palabra la señora Pérez."), ("SPEAKER_00", "Gracias.")])
    gender, a = gender_of(tl, "SPEAKER_00")
    assert gender == U and a.needs_review and a.suggestion == W
    assert a.evidence[0].method == "floor_grant_same_voice" and a.evidence[0].confidence < 0.7


def test_floor_grant_splits_a_merged_voice_and_assigns_the_gender_after_it(monkeypatch):
    from decision import split_on_floor_grant

    monkeypatch.setattr("decision.gender_cues.MIN_SPLIT_S", 5.0)  # turnos de prueba de 4 s

    tl = make(
        [
            ("SPEAKER_00", "Tiene la palabra la señora Persona 2."),
            ("SPEAKER_00", "Muchas gracias, presidente. Buenos días."),
            ("SPEAKER_00", "Hoy hablamos de vivienda."),
            ("SPEAKER_00", "Tiene la palabra el señor Persona 3."),
            ("SPEAKER_00", "Gracias. Voy a hablar de energía."),
            ("SPEAKER_00", "Y también de empleo."),
        ]
    )
    out = split_on_floor_grant(tl, load_rules())
    assert [e.speaker_id for e in out.events] == [
        "SPEAKER_00", "SPEAKER_01", "SPEAKER_01", "SPEAKER_00", "SPEAKER_02", "SPEAKER_02",
    ]  # fmt: skip
    assert [s.speaker_id for s in out.speakers] == ["SPEAKER_00", "SPEAKER_01", "SPEAKER_02"]
    assert next(s for s in out.speakers if s.speaker_id == "SPEAKER_01").total_speech_s == 8
    gender = {a.speaker_id: a.gender for a in assign_genders(out, load_rules())}
    assert gender == {"SPEAKER_00": U, "SPEAKER_01": W, "SPEAKER_02": M}


def test_split_leaves_alone_a_timeline_whose_voices_are_already_separate():
    from decision import split_on_floor_grant

    tl = make(
        [
            ("SPEAKER_00", "Tiene la palabra la señora Persona 2."),
            ("SPEAKER_01", "Gracias presidente."),
        ]
    )
    assert split_on_floor_grant(tl, load_rules()) is tl


def test_a_short_stretch_after_a_floor_phrase_is_not_split_off():
    from decision import split_on_floor_grant

    tl = make(
        [
            ("SPEAKER_00", "Tiene la palabra el señor Persona 2."),
            ("SPEAKER_00", "Gracias."),
        ]
    )  # 4 s tras la frase: menos que MIN_SPLIT_S, es ruido
    assert split_on_floor_grant(tl, load_rules()) is tl


def test_control_session_announcement_gives_gender_to_the_next_voice():
    announcement = "La siguiente pregunta la formula la diputada doña Persona 3, del Grupo Popular."
    tl = make([("SPEAKER_00", announcement), ("SPEAKER_01", "Gracias. Mi pregunta es clara.")])
    gender, a = gender_of(tl, "SPEAKER_01")
    assert gender == W and a.confidence >= 0.7


def test_chair_cues_in_a_control_session():
    """Presidencia: anuncio de 2018 y tratamiento a solas para dar paso; «gracias» no cuenta."""
    tl = make(
        [
            ("SPEAKER_00", "Pregunta del diputado don Persona 2, del Grupo Mixto."),
            ("SPEAKER_01", "Señora ministra, ¿qué va a hacer con los alquileres?"),
            ("SPEAKER_00", "Muchas gracias. Señora ministra, cuando quiera."),
            ("SPEAKER_02", "Gracias. Le respondo con datos."),
            (
                "SPEAKER_00",
                "Pregunta también dirigida al señor presidente del diputado don Persona 3.",
            ),
            ("SPEAKER_03", "Presidente, ¿va a convocar elecciones?"),
            ("SPEAKER_00", "Muchas gracias, señor Persona 3."),
            ("SPEAKER_04", "Le contesto enseguida."),
        ]
    )
    got = {
        sid: gender_of(tl, sid)[0]
        for sid in ("SPEAKER_01", "SPEAKER_02", "SPEAKER_03", "SPEAKER_04")
    }
    assert got == {"SPEAKER_01": M, "SPEAKER_02": W, "SPEAKER_03": M, "SPEAKER_04": U}


def test_parliamentary_group_does_not_cancel_the_gender_of_the_announcement():
    announcement = (
        "La primera la formula la diputada doña Persona 2, del Grupo Parlamentario Popular, "
        "que tiene la palabra."
    )
    tl = make([("SPEAKER_00", announcement), ("SPEAKER_01", "Gracias. Mi pregunta es clara.")])
    gender, a = gender_of(tl, "SPEAKER_01")
    assert gender == W and a.confidence >= 0.7
