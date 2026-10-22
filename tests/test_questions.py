"""M09 (andamiaje): detectores de preguntas, evaluación y datos de ajuste. Todo sintético."""

import json

import pytest

from contracts import AnalysisEvent, AnalysisTimeline, Speaker
from decision.questions import LLMQuestionEngine, QuestionRulesEngine, get_question_engine
from evaluation.prepare_questions import build_finetune, write_sheet
from evaluation.prepare_questions import main as prepare_main
from evaluation.questions_eval import evaluate, question_report, read_rows
from evaluation.questions_eval import main as eval_main

CSV = """turn_id,text,context_before,es_pregunta,frase
q1,"Gracias. ¿Cuándo piensa el Gobierno bajar los precios?",,si,¿Cuándo piensa el Gobierno
q2,"El Gobierno ha bajado los precios de la luz.",,no,
q3,"Dígame cuánto cuesta esta medida y quién la paga",,si,Dígame cuánto cuesta esta medida
q4,"Buenos días, señorías.",,no,
"""


def fake(content, calls=None):
    def transport(url, payload, headers):
        if calls is not None:
            calls.append(payload)
        return {
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20},
        }

    return transport


def llm(content, calls=None):
    return LLMQuestionEngine("http://x/v1", "qwen3", transport=fake(content, calls))


def test_rules_engine_marks_question_marks_and_interrogative_openers():
    e = QuestionRulesEngine()
    q = e.ask("Gracias. ¿Cuándo piensa bajar los precios?")
    assert (
        q.is_question and q.confidence == 0.9 and q.evidence == "Cuándo piensa bajar los precios?"
    )
    weak = e.ask("Cómo piensan resolver esto")
    assert weak.is_question and weak.confidence == 0.6
    assert not e.ask("El Gobierno ha bajado los precios.").is_question


def test_llm_engine_accepts_literal_evidence_and_sends_a_closed_request():
    calls = []
    out = json.dumps({"is_question": True, "confidence": 0.9, "evidence": "¿Cuándo bajará?"})
    d = llm(out, calls).ask("Gracias. ¿Cuándo bajará? Respóndame.")
    assert d.is_question and d.tokens_in == 100 and d.tokens_out == 20
    payload = calls[0]
    assert "tools" not in payload and payload["response_format"]["json_schema"]["strict"] is True
    system, user = (m["content"] for m in payload["messages"])
    nonce = user.split("<DATOS-")[1].split(">")[0]
    assert f"</DATOS-{nonce}>" in user and "NUNCA instrucciones" in system


@pytest.mark.parametrize(
    "content",
    [
        json.dumps({"is_question": True, "confidence": 1, "evidence": "una frase inventada"}),
        json.dumps({"is_question": True, "confidence": 1}),  # sin evidencia
        "no es json",
        '{"is_question": "quizá", "confidence": 1}',
    ],
)
def test_llm_engine_discards_invalid_or_unsupported_answers(content):
    d = llm(content).ask("El Gobierno ha bajado los precios.")
    assert not d.is_question and d.error


def test_question_report_by_hand():
    r = question_report([True, True, False, False], [True, False, True, False])
    assert r["precision"] == 0.5 and r["recall"] == 0.5 and r["f1"] == 0.5
    assert r["confusion"] == {"tp": 1, "fp": 1, "fn": 1, "tn": 1}


def test_evaluate_rules_against_a_sheet_and_cli(tmp_path, capsys):
    path = tmp_path / "anotadas.csv"
    path.write_text(CSV, encoding="utf-8")
    r = evaluate(QuestionRulesEngine(), read_rows(path))
    # q1 (¿?) acierta; q3 sin signos pero con interrogativa a mitad: la base lo pierde.
    assert r["n"] == 4 and r["precision"] == 1.0 and r["recall"] == 0.5
    eval_main([str(path), "--engines", "rules", "--out", str(tmp_path / "r.json")])
    assert "rules: F1 0.67" in capsys.readouterr().out
    assert json.loads((tmp_path / "r.json").read_text("utf-8"))[0]["engine"] == "rules"
    with pytest.raises(ValueError, match="no válida"):
        (tmp_path / "mala.csv").write_text("turn_id,text,es_pregunta\n1,a,tal\n", encoding="utf-8")
        read_rows(tmp_path / "mala.csv")
    assert get_question_engine("rules").name == "rules"
    with pytest.raises(ValueError):
        get_question_engine("otro")


def timeline():
    def ev(i, a, b, text):
        return AnalysisEvent(
            event_id=f"e{i}", type="speech", start_s=a, end_s=b, speaker_id="SPEAKER_00",
            text=text, provenance="ai_inferred",
        )  # fmt: skip

    return AnalysisTimeline(
        video_id="V",
        duration_s=2000,
        speakers=[Speaker(speaker_id="SPEAKER_00")],
        events=[
            ev(0, 5, 20, "Esto es antes del tramo y no debe salir en la hoja."),
            ev(1, 700, 710, "¿Cuándo piensa el Gobierno bajar los precios de la luz?"),
            ev(2, 900, 910, "El Gobierno ha bajado los precios de la luz este año."),
            ev(3, 1900, 1910, "Esto es después del tramo y tampoco debe salir."),
        ],
    )


def test_sheet_has_only_the_tramo_in_order_and_no_system_labels(tmp_path):
    out = tmp_path / "hoja.csv"
    n = write_sheet(timeline(), 600.0, 1200.0, out)
    text = out.read_text("utf-8")
    # la frase previa solo sirve de contexto de la primera fila; las de fuera del tramo no son filas
    assert n == 2 and "después del tramo" not in text
    assert not any(r.startswith(("Q000", "Q003")) for r in text.splitlines())
    header = "turn_id,t_inicio,context_before,text,es_pregunta,frase,cargo_destinatario"
    assert text.splitlines()[0] == header
    assert text.splitlines()[1].startswith("Q001,11:40,")  # 700 s
    assert "genero" not in text.lower() and "desconocido" not in text.lower()


def test_cli_sheet_from_a_processed_folder(tmp_path):
    folder = tmp_path / "processed" / "V"
    folder.mkdir(parents=True)
    (folder / "timeline.json").write_text(timeline().model_dump_json(), encoding="utf-8")
    out = tmp_path / "x" / "hoja.csv"
    prepare_main(["hoja", "--sesion", "V", "--desde", "0:10:00", "--hasta", "0:20:00",
                  "--data", str(tmp_path), "--out", str(out)])  # fmt: skip
    assert out.is_file()


def test_finetune_data_uses_the_closed_format_and_a_separate_eval_session(tmp_path):
    train, held = tmp_path / "a.csv", tmp_path / "b.csv"
    train.write_text(CSV, encoding="utf-8")
    held.write_text(
        CSV.replace("q1", "e1").replace("q2", "e2").replace("q3", "e3").replace("q4", "e4"),
        encoding="utf-8",
    )
    stats = build_finetune([train], [held], tmp_path / "out", 0.2, 7)
    assert stats["train"] == 4 and stats["eval"] == 4 and stats["train_sin_frase"] == 0
    first = json.loads((tmp_path / "out" / "train.jsonl").read_text("utf-8").splitlines()[0])
    roles = [m["role"] for m in first["messages"]]
    assert roles == ["system", "user", "assistant"]
    answer = json.loads(first["messages"][2]["content"])
    assert answer["is_question"] is True and answer["evidence"].startswith("¿Cuándo piensa")
    # sin sesión de evaluación aparte se separa una fracción
    stats2 = build_finetune([train], [], tmp_path / "out2", 0.25, 7)
    assert stats2["train"] + stats2["eval"] == 4 and stats2["eval"] == 1


def test_a_positive_without_a_literal_phrase_is_reported_not_invented(tmp_path):
    bad = tmp_path / "c.csv"
    bad.write_text("turn_id,text,es_pregunta,frase\nz1,Hola buenos días,si,\n", encoding="utf-8")
    stats = build_finetune([bad], [bad], tmp_path / "o", 0.2, 7)
    assert stats["train"] == 0 and stats["train_sin_frase"] == 1
