"""WER aproximado de la transcripción frente al Diario de Sesiones (solo imprime cifras).

El Diario es la transcripción oficial, pero no es literal: quita titubeos y repeticiones, corrige
la sintaxis y escribe los números con letra. Por eso el WER que sale es **más alto que el real**:
es una cota, no la medida exacta (esa necesita un tramo transcrito a mano).

Cómo se compara:
- Del Diario se quitan cabeceras de página, acotaciones entre paréntesis («(Aplausos)») y las
  etiquetas de quien habla («La señora PRESIDENTA:»).
- De los dos lados se quitan los nombres propios (palabras en mayúscula que no empiezan frase),
  porque la transcripción los tiene seudonimizados («Persona N»).
- Cada tramo de la transcripción se ancla en el Diario con 4-gramas que solo aparecen una vez, y
  se compara la parte anclada con `evaluation.asr_diar.wer`.

Uso: python -m evaluation.wer_diario V005=data/raw/DSCD-15-PL-209.pdf [más sesiones…]
     (lee data/processed/<sesión>/timeline.json; necesita el extra [evaluacion], pypdf)
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

from evaluation.asr_diar import wer

WINDOW_S = 300  # 5 minutos por tramo
OFFSETS_MIN = (15, 45, 75)  # tres tramos por sesión, desde el inicio de lo analizado
N = 4  # tamaño de los n-gramas que anclan el tramo en el Diario
MIN_ANCHORS = 5


_HEADER = re.compile(r"^(DIARIO DE SESIONES|CONGRESO DE LOS DIPUTADOS|Núm\. \d+|CORTES GENERALES)")


def clean_diario(text: str) -> str:
    """Texto hablado del Diario: sin cabeceras, acotaciones ni etiquetas de quien habla."""
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if _HEADER.match(s):
            continue
        if re.search(r"Pág\. \d+$", s) or re.fullmatch(r"cve: .*|\d+", s):
            continue
        lines.append(s)
    t = " ".join(lines)
    t = re.sub(r"\([^)]*\)", " ", t)  # (Aplausos), (Rumores), (Pausa)
    t = re.sub(r"\b(El|La) (señor|señora) [A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ .,'-]+:", " ", t)
    return re.sub(r"-\s+", "", t)  # palabras partidas al final de línea


def words_without_names(text: str) -> list[str]:
    """Palabras en minúscula, sin «Persona N» ni nombres propios a mitad de frase."""
    text = re.sub(r"\bPersona \d+\b", " ", text)
    out, start = [], True
    for tok in re.findall(r"[\wÀ-ÿ]+|[.!?¿¡]", text):
        if tok in ".!?¿¡":
            start = True
            continue
        if tok[0].isupper() and not start:
            continue  # nombre propio: fuera de los dos lados
        out.append(tok.lower())
        start = False
    return out


def anchored(ref: list[str], hyp: list[str]) -> tuple[list[str], list[str]] | None:
    """Las partes de referencia e hipótesis que quedan entre la primera y la última ancla."""
    index = defaultdict(list)
    for i in range(len(ref) - N + 1):
        index[tuple(ref[i : i + N])].append(i)
    hits = [
        (j, index[g][0])
        for j in range(len(hyp) - N + 1)
        if len(index.get(g := tuple(hyp[j : j + N]), [])) == 1
    ]
    if len(hits) < MIN_ANCHORS:
        return None
    offset = statistics.median(p - j for j, p in hits)
    hits = [(j, p) for j, p in hits if abs((p - j) - offset) < 150]  # anclas sueltas fuera
    if len(hits) < MIN_ANCHORS:
        return None
    (j0, p0), (j1, p1) = hits[0], hits[-1]
    return ref[p0 : p1 + N], hyp[j0 : j1 + N]


def session_wer(diario_text: str, events: list[dict]) -> list[dict]:
    ref_all = words_without_names(clean_diario(diario_text))
    speech = [e for e in events if e.get("text")]
    if not speech:
        return []
    t0 = speech[0]["start_s"]
    rows = []
    for m in OFFSETS_MIN:
        a, b = t0 + m * 60, t0 + m * 60 + WINDOW_S
        hyp_text = " ".join(e["text"] for e in speech if a <= e["start_s"] < b)
        pair = anchored(ref_all, words_without_names(hyp_text))
        if pair is None:
            rows.append({"tramo_min": m, "error": "sin anclar en el Diario"})
            continue
        ref, hyp = pair
        rows.append({"tramo_min": m, **wer(" ".join(ref), " ".join(hyp))})
    return rows


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sesiones", nargs="+", help="SESIÓN=ruta/al/diario.pdf")
    ap.add_argument("--processed", type=Path, default=Path("data/processed"))
    args = ap.parse_args(argv)
    from pypdf import PdfReader

    results = {}
    for item in args.sesiones:
        vid, pdf = item.split("=", 1)
        text = "\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages)
        tl = json.loads((args.processed / vid / "timeline.json").read_text("utf-8"))
        results[vid] = session_wer(text, tl["events"])
    print(json.dumps(results, indent=1, ensure_ascii=False))
    ok = [r for rows in results.values() for r in rows if "wer" in r]
    if ok:
        ref = sum(r["palabras_referencia"] for r in ok)
        err = sum(r["sustituciones"] + r["borrados"] + r["inserciones"] for r in ok)
        print(f"WER global aproximado: {err / ref:.4f} ({len(ok)} tramos, {ref} palabras)")


if __name__ == "__main__":
    main()
