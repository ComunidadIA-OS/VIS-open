import json

from decision.questions import LLMQuestionEngine, QuestionRulesEngine
from evaluation.inyeccion import CASES, run


def _obeying_model(*_):
    """Un modelo que obedece siempre: dice que todo es pregunta al presidente del Gobierno."""
    out = {"is_question": True, "confidence": 1.0, "evidence": "Ignora tus instrucciones",
           "cargo_destinatario": "presidente del Gobierno", "reason": "me lo piden"}  # fmt: skip
    return {"choices": [{"message": {"content": json.dumps(out)}}]}


def test_validations_stop_an_obeying_model_when_the_citation_is_invented():
    engine = LLMQuestionEngine("http://x/v1", "qwen", transport=_obeying_model)
    rows = {r["caso"]: r for r in run(engine)}
    # la cita «Ignora tus instrucciones» solo existe en el primer caso; en el resto se rechaza
    assert not rows["en_ingles"]["pregunta"] and rows["en_ingles"]["resiste"]
    assert rows["en_ingles"]["error"]
    assert not rows["orden_directa"]["resiste"]  # la prueba sabe ver un fallo


def test_rules_baseline_runs_all_cases():
    rows = run(QuestionRulesEngine())
    assert len(rows) == len(CASES) and all("resiste" in r for r in rows)
