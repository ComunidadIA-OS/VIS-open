import pytest

from contracts import AnalysisEvent, AnalysisTimeline, EventType, Provenance, Speaker
from contracts.enums import GenderSource, GenderValue
from decision.questions import QuestionDecision, QuestionRulesEngine
from decision.roles import (
    ROLE_ASK,
    ROLE_CHAIR,
    ROLE_GOV,
    assign_roles,
    find_chair,
    question_blocks,
)
from metrics.m09 import Judgement, compute_m06, compute_m09, is_head_of_government, judge_blocks

CHAIR, A1, A2, A3, MIN_F, MIN_M = (f"SPEAKER_0{i}" for i in range(6))
GRANT = "Tiene la palabra la señora diputada."


def _timeline(blocks):
    """blocks: lista de (texto de la pregunta, quien pregunta, quien responde)."""
    events, t = [], 0.0

    def add(speaker, text, seconds):
        nonlocal t
        events.append(
            AnalysisEvent(
                event_id=f"e{len(events)}",
                type=EventType.SPEECH,
                start_s=t,
                end_s=t + seconds,
                speaker_id=speaker,
                text=text,
                provenance=Provenance.OBSERVED,
            )
        )
        t += seconds + 1.5

    for question, asker, answerer in blocks:
        add(CHAIR, GRANT, 3)
        add(asker, question, 60)
        add(answerer, "Gracias, le respondo con datos.", 90)
        add(asker, "Insisto en la pregunta.", 30)
        add(answerer, "Y yo insisto en mi respuesta.", 40)
    speakers = [
        Speaker(
            speaker_id=sid,
            gender=GenderValue.WOMAN if sid in (MIN_F, A1) else GenderValue.MAN,
            gender_source=GenderSource.LANGUAGE_CUE,
        )
        for sid in (CHAIR, A1, A2, A3, MIN_F, MIN_M)
    ]
    return AnalysisTimeline(video_id="T", duration_s=t + 10, speakers=speakers, events=events)


Q_MIN = "Señora ministra, ¿qué piensa hacer con los alquileres?"
Q_MAN = "Señor ministro, ¿cuándo bajará el precio de la luz?"
Q_PM = "Presidente del Gobierno, ¿va a convocar elecciones?"
GENDERS = {
    CHAIR: "hombre",
    A1: "mujer",
    A2: "hombre",
    A3: "hombre",
    MIN_F: "mujer",
    MIN_M: "hombre",
}


@pytest.fixture
def timeline():
    return _timeline(
        [(Q_MIN, A1, MIN_F), (Q_MIN, A2, MIN_F), (Q_MAN, A3, MIN_M), (Q_PM, A1, MIN_M)]
    )


def test_blocks_and_roles(timeline):
    assert find_chair(timeline) == CHAIR
    blocks = question_blocks(timeline)
    got = [(b.index, b.asker, b.answerer) for b in blocks]
    assert got == [(1, A1, MIN_F), (2, A2, MIN_F), (3, A3, MIN_M), (4, A1, MIN_M)]
    assert len(blocks[0].turns) == 4  # pregunta, respuesta, réplica y dúplica
    assert blocks[0].role_of(CHAIR) == ROLE_CHAIR
    assert (blocks[0].role_of(A1), blocks[0].role_of(MIN_F)) == (ROLE_ASK, ROLE_GOV)
    roles = {s.speaker_id: s.role for s in assign_roles(timeline).speakers}
    assert roles == {
        CHAIR: ROLE_CHAIR,
        A1: ROLE_ASK,
        A2: ROLE_ASK,
        A3: ROLE_ASK,
        MIN_F: ROLE_GOV,
        MIN_M: ROLE_GOV,
    }


def test_no_chair_no_blocks():
    tl = _timeline([(Q_MIN, A1, MIN_F)])  # una sola vez: no basta para decir quién preside
    assert find_chair(tl) is None and question_blocks(tl) == []


def test_ivette_test_case_normalized_rate():
    # 3 preguntas: 2 a «la señora ministra» y 1 a «el señor ministro» -> 2,0 frente a 1,0
    tl = _timeline([(Q_MIN, A1, MIN_F), (Q_MIN, A2, MIN_F), (Q_MAN, A3, MIN_M)])
    blocks = question_blocks(tl)
    engine = QuestionRulesEngine()
    judgements = [Judgement(b.index, engine.ask(b.asker_text).is_question, 0.9) for b in blocks]
    m = compute_m09(blocks, GENDERS, judgements, min_voices=2, min_seconds=0)
    assert m.value == pytest.approx(2.0)
    assert m.details["tasa_por_voz"] == {"mujer": 2.0, "hombre": 1.0}
    assert m.conclusive and "actualidad" in m.details["nota"]


def test_head_of_government_is_separate_and_low_confidence_goes_to_review(timeline):
    blocks = question_blocks(timeline)
    judgements = [
        Judgement(1, True, 0.9, "ministra"),
        Judgement(2, True, 0.5, "ministra"),  # confianza baja: a revisión, no se cuenta
        Judgement(3, True, 0.9, "ministro"),
        Judgement(4, True, 0.9, "Presidente del Gobierno"),
    ]
    m9 = compute_m09(blocks, GENDERS, judgements, min_voices=2, min_seconds=0)
    assert m9.details["pendientes_de_revision"] == [2]
    assert [q["pregunta"] for q in m9.details["presidente_del_gobierno"]] == [4]
    assert m9.details["por_genero"]["mujer"]["preguntas"] == 1  # solo la 1; la 4 va aparte
    m6 = compute_m06(blocks, GENDERS, judgements)
    assert m6.value == pytest.approx(100.0) and m6.sample == {"preguntas_al_presidente": 1}


def test_small_sample_is_inconclusive(timeline):
    blocks = question_blocks(timeline)
    judgements = [Judgement(b.index, True, 0.9) for b in blocks]
    m = compute_m09(blocks, GENDERS, judgements)  # mínimos de Ivette: 4 voces y 600 s
    assert not m.conclusive and "muestra insuficiente" in (m.reason or "")


def test_judge_blocks_uses_the_engine(timeline):
    class Fake:
        def ask(self, text, context=None):
            return QuestionDecision(
                is_question=True, confidence=0.8, cargo_destinatario="Presidente del Gobierno"
            )

    js = judge_blocks(question_blocks(timeline), Fake())
    assert all(j.is_question and is_head_of_government(j.cargo_destinatario) for j in js)
    assert not is_head_of_government(None) and not is_head_of_government("ministra")


def test_named_addressee_that_differs_from_who_answers_is_flagged(timeline):
    blocks = question_blocks(timeline)
    # la pregunta 3 nombra a «el señor ministro» pero la respondió una mujer: se avisa
    swapped = dict(GENDERS, **{MIN_M: "mujer"})
    judgements = [Judgement(3, True, 0.9, "el señor ministro")]
    m = compute_m09(blocks, swapped, judgements, min_voices=1, min_seconds=0)
    flag = m.details["destinatario_distinto_de_quien_responde"]
    assert [f["pregunta"] for f in flag] == [3]
    assert m.details["preguntas_por_persona"][MIN_M]["recibidas"] == 1  # cuenta quien responde
