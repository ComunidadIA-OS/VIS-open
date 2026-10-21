"""Ajuste ligero (LoRA) de Qwen para detectar preguntas (M09), pensado para las V100S de OVH.

Un solo fichero, sin depender del resto del repo, para subirlo tal cual al notebook:
    CUDA_VISIBLE_DEVICES=1 python train_lora.py --smoke                      # prueba de humo
    CUDA_VISIBLE_DEVICES=1 python train_lora.py --train train.jsonl --eval eval.jsonl

- `--smoke`: 16 ejemplos sintéticos y 10 pasos. Solo comprueba que el modelo carga, entrena sin
  NaN y cabe en memoria en una V100S. No usa datos reales.
- Con datos: entrena el adaptador LoRA con `train.jsonl` y mide el ANTES (adaptador apagado) y el
  DESPUÉS (adaptador encendido) sobre `eval.jsonl` con el mismo método y en la misma ejecución.
  Salida: `<out>/adapter` (el adaptador) y `<out>/resultado.json`. Los pesos no se publican ni se
  suben al repo.
- V100S (Volta): sin bf16. El modelo base va en float16 y los parámetros LoRA en float32, con
  autocast y GradScaler. Si aparece un NaN, se para con un mensaje claro.
- Los datos son JSONL de `evaluation/prepare_questions.py ajuste`: cada línea trae `messages`
  (sistema, usuario y asistente con la respuesta JSON cerrada de la anotadora).
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

DEFAULT_MODEL = "Qwen/Qwen3.5-4B"  # probar primero el pequeño; luego Qwen/Qwen3.5-9B
SMOKE_QUESTIONS = [
    "¿Cuándo piensa el Gobierno bajar el precio de la luz?",
    "¿Qué medidas van a tomar con los alquileres?",
    "Dígame cuántos funcionarios se han contratado este año, y quién lo ha decidido.",
    "¿Por qué no han cumplido lo que prometieron en la anterior sesión?",
]
SMOKE_STATEMENTS = [
    "El Gobierno ha bajado el precio de la luz este año.",
    "Buenos días, señorías, comenzamos la sesión de hoy.",
    "Quiero agradecer el trabajo de todos los equipos.",
    "Las cifras de empleo son las mejores de la serie histórica.",
]
SYSTEM = (
    "Eres un clasificador lingüístico. Decide si el turno formula alguna pregunta y responde solo "
    "con un JSON: is_question, confidence, evidence (cita literal o null) y reason."
)


def smoke_examples() -> list[dict]:
    out = []
    for text in SMOKE_QUESTIONS + SMOKE_STATEMENTS:
        asked = text in SMOKE_QUESTIONS
        answer = {
            "is_question": asked,
            "confidence": 1.0,
            "evidence": text if asked else None,
            "reason": "ejemplo sintético",
        }
        out.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": f"[TURNO]\n{text}"},
                    {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)},
                ]
            }
        )
    return out * 2  # 16 ejemplos


def read_jsonl(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in Path(path).read_text("utf-8").splitlines() if line.strip()]
    for r in rows:
        roles = [m["role"] for m in r["messages"]]
        if roles != ["system", "user", "assistant"]:
            raise ValueError(f"un ejemplo no tiene system, user y assistant: {roles}")
    return rows


def prf1(gold: list[bool], pred: list[bool]) -> dict:
    tp = sum(g and p for g, p in zip(gold, pred, strict=True))
    fp = sum((not g) and p for g, p in zip(gold, pred, strict=True))
    fn = sum(g and (not p) for g, p in zip(gold, pred, strict=True))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def parse_answer(text: str) -> bool | None:
    """True/False si la respuesta es un JSON válido con `is_question`; None si no lo es."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        value = json.loads(text[start : end + 1]).get("is_question")
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, bool) else None


def _prompt_and_answer(tok, messages: list[dict]) -> tuple[list[int], list[int]]:
    """Tokens del prompt (sin respuesta) y de la respuesta; la pérdida solo cuenta la respuesta."""
    prompt = tok.apply_chat_template(
        messages[:2], tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    answer = messages[2]["content"] + tok.eos_token
    p = tok(prompt, add_special_tokens=False)["input_ids"]
    a = tok(answer, add_special_tokens=False)["input_ids"]
    return p, a


def load_model(name: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(name)
    try:
        model = AutoModelForCausalLM.from_pretrained(name, dtype=torch.float16, device_map={"": 0})
    except (ValueError, KeyError):  # arquitectura multimodal: cargar con la clase de imagen+texto
        from transformers import AutoModelForImageTextToText

        model = AutoModelForImageTextToText.from_pretrained(
            name, dtype=torch.float16, device_map={"": 0}
        )
    return tok, model


def add_lora(model, rank: int):
    from peft import LoraConfig, get_peft_model

    cfg = LoraConfig(
        r=rank, lora_alpha=2 * rank, lora_dropout=0.05, task_type="CAUSAL_LM",
        target_modules="all-linear", exclude_modules=r".*(visual|vision).*",
    )  # fmt: skip
    peft_model = get_peft_model(model, cfg)
    for p in peft_model.parameters():
        if p.requires_grad:
            p.data = p.data.float()  # LoRA en float32: más estable que fp16 en Volta
    return peft_model


def train(model, tok, rows: list[dict], steps: int, lr: float, accum: int, max_len: int) -> dict:
    import torch

    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model.train()
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.0)
    scaler = torch.amp.GradScaler("cuda")
    data = [_prompt_and_answer(tok, r["messages"]) for r in rows]
    rng, losses = random.Random(7), []
    start = time.time()
    for step in range(1, steps + 1):
        total = 0.0
        for _ in range(accum):
            p, a = rng.choice(data)
            ids = (p + a)[:max_len]
            labels = ([-100] * len(p) + a)[:max_len]
            x = torch.tensor([ids], device="cuda")
            y = torch.tensor([labels], device="cuda")
            with torch.autocast("cuda", dtype=torch.float16):
                loss = model(input_ids=x, labels=y).loss / accum
            if not math.isfinite(loss.item()):
                raise SystemExit(
                    "NaN en la pérdida: float16 no es estable con este modelo. "
                    "Prueba un modelo más pequeño o menos pasos con tasa de aprendizaje menor."
                )
            scaler.scale(loss).backward()
            total += loss.item()
        scaler.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        scaler.step(opt)
        scaler.update()
        opt.zero_grad(set_to_none=True)
        losses.append(total)
        print(f"paso {step}/{steps}  pérdida {total:.4f}", flush=True)
    return {
        "pasos": steps,
        "perdida_inicial": round(losses[0], 4),
        "perdida_final": round(losses[-1], 4),
        "segundos": round(time.time() - start, 1),
        "memoria_gpu_pico_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
    }


def evaluate(model, tok, rows: list[dict]) -> dict:
    import torch

    model.eval()
    gold, pred, invalid = [], [], 0
    for r in rows:
        gold.append(json.loads(r["messages"][2]["content"])["is_question"])
        prompt = tok.apply_chat_template(
            r["messages"][:2], tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
        x = tok(prompt, return_tensors="pt", add_special_tokens=False).to("cuda")
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.float16):
            out = model.generate(**x, max_new_tokens=96, do_sample=False)
        answer = parse_answer(
            tok.decode(out[0][x["input_ids"].shape[1] :], skip_special_tokens=True)
        )
        invalid += answer is None
        pred.append(bool(answer))
    return {**prf1(gold, pred), "n": len(rows), "respuestas_invalidas": invalid}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--train", type=Path)
    ap.add_argument("--eval", type=Path)
    ap.add_argument("--out", type=Path, default=Path("ajuste_qwen"))
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--accum", type=int, default=4)
    ap.add_argument("--max-len", type=int, default=768)
    args = ap.parse_args()
    if not args.smoke and not args.train:
        ap.error("falta --train (o usa --smoke)")

    rows = smoke_examples() if args.smoke else read_jsonl(args.train)
    eval_rows = smoke_examples()[:8] if args.smoke else (read_jsonl(args.eval) if args.eval else [])
    steps = 10 if args.smoke else args.steps

    tok, model = load_model(args.model)
    model = add_lora(model, args.rank)
    result: dict = {"modelo": args.model, "ejemplos_entrenamiento": len(rows)}
    if eval_rows:
        with model.disable_adapter():  # el «antes»: el mismo modelo sin ajustar
            result["antes"] = evaluate(model, tok, eval_rows)
    result["entrenamiento"] = train(model, tok, rows, steps, args.lr, args.accum, args.max_len)
    if eval_rows:
        result["despues"] = evaluate(model, tok, eval_rows)
    args.out.mkdir(parents=True, exist_ok=True)
    if not args.smoke:
        model.save_pretrained(args.out / "adapter")
    (args.out / "resultado.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
