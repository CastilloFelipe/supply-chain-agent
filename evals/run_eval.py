"""Evalua el traductor contra respuestas esperadas.

Dos fuentes de predicciones:
    python evals/run_eval.py --set v2 --predicciones evals/predicciones/<corrida>   # archivos <id>.json
    python evals/run_eval.py --set v2 --api                                         # traductor con API

Cada set vive en evals/<set>/ (preguntas.json + respuestas_esperadas.json). Una
pregunta puede indicar "datos" (red sobre la que se hace); por defecto, Chile.

Criterio por caso: ACIERTO si el conjunto de operaciones coincide con alguna
respuesta aceptable (sin importar el orden; factores con tolerancia 0.005) y,
cuando el caso lo exige, se declara la parte no modelable en `unsupported`.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from network_opt import load_network  # noqa: E402

EVALS = ROOT / "evals"
TOL = 0.005


def _key(op: dict) -> tuple:
    return tuple(sorted((k, v) for k, v in op.items() if k not in ("factor", "n")))


def same_operations(pred: list[dict], expected: list[dict]) -> bool:
    if len(pred) != len(expected):
        return False
    remaining = list(expected)
    for p in pred:
        match = next(
            (e for e in remaining
             if _key(e) == _key(p)
             and abs(e.get("factor", 0) - p.get("factor", 0)) <= TOL
             and e.get("n") == p.get("n")),
            None,
        )
        if match is None:
            return False
        remaining.remove(match)
    return True


def score_case(pred_ops: list[dict] | None, unsupported: str, expected: dict, error: str = "") -> dict:
    if error:
        return {"acierto": False, "motivo": f"error: {error}"}
    ops_ok = any(same_operations(pred_ops, alt) for alt in expected["aceptables"])
    needs_unsupported = expected.get("unsupported", False)
    declared = bool(unsupported.strip())
    if not ops_ok:
        return {"acierto": False, "motivo": "operaciones distintas a las esperadas"}
    if needs_unsupported and not declared:
        return {"acierto": False, "motivo": "no declaro la parte no modelable"}
    return {"acierto": True, "motivo": "ok" if not (declared and not needs_unsupported)
            else "ok (declaro algo no modelable sin necesidad)"}


_NETWORKS: dict = {}


def network_for(q: dict):
    path = str(ROOT / q.get("datos", "data/base_network.json"))
    if path not in _NETWORKS:
        _NETWORKS[path] = load_network(path)
    return _NETWORKS[path]


def predict_from_files(folder: Path, questions: list[dict]) -> dict:
    from whatif_agent.offline import load_scenario

    out = {}
    for q in questions:
        data = network_for(q)
        f = folder / f"{q['id']}.json"
        if not f.exists():
            out[q["id"]] = (None, "", "falta archivo de prediccion")
            continue
        try:
            s = load_scenario(f, data)
            out[q["id"]] = (s.operations, s.unsupported, "")
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            out[q["id"]] = (None, "", str(e))
    return out


def predict_with_api(questions: list[dict]) -> dict:
    from whatif_agent import TranslationError, translate

    out = {}
    for q in questions:
        try:
            s = translate(q["pregunta"], network_for(q))
            out[q["id"]] = (s.operations, s.unsupported, "")
        except (TranslationError, ValueError) as e:
            out[q["id"]] = (None, "", str(e))
        print(f"  {q['id']}: listo", file=sys.stderr)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--predicciones", help="Carpeta con <id>.json por pregunta")
    g.add_argument("--api", action="store_true", help="Traducir con la API de Anthropic")
    ap.add_argument("--set", default="v1", help="Set de evaluacion (carpeta en evals/)")
    args = ap.parse_args()

    questions = json.loads((EVALS / args.set / "preguntas.json").read_text(encoding="utf-8"))
    expected = json.loads((EVALS / args.set / "respuestas_esperadas.json").read_text(encoding="utf-8"))
    preds = (predict_from_files(Path(args.predicciones), questions) if args.predicciones
             else predict_with_api(questions))

    rows = []
    for q in questions:
        ops, unsupported, err = preds[q["id"]]
        r = score_case(ops, unsupported, expected[q["id"]], err)
        rows.append({"id": q["id"], "pregunta": q["pregunta"], **r, "prediccion": ops,
                     "unsupported": unsupported})

    hits = sum(r["acierto"] for r in rows)
    source = args.predicciones or "api"
    lines = [f"# Evaluación del traductor", "",
             f"Set: `{args.set}` · Fuente: `{source}` · {datetime.now():%Y-%m-%d %H:%M}", "",
             f"**Aciertos: {hits} de {len(rows)} ({hits / len(rows):.0%})**", "",
             "| Caso | Resultado | Detalle |", "|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {'✅' if r['acierto'] else '❌'} | {r['motivo']} |")
    fails = [r for r in rows if not r["acierto"]]
    if fails:
        lines += ["", "## Fallos", ""]
        for r in fails:
            exp = expected[r["id"]]
            lines += [f"**{r['id']}** — {r['pregunta']}", "",
                      f"- Predicción: `{json.dumps(r['prediccion'], ensure_ascii=False)}`"
                      + (f" · unsupported: _{r['unsupported']}_" if r["unsupported"] else ""),
                      f"- Esperado: `{json.dumps(exp['aceptables'][0], ensure_ascii=False)}`"
                      + (" + declarar no modelable" if exp.get("unsupported") else "")
                      + (f" ({exp['nota']})" if exp.get("nota") else ""), ""]
    report = "\n".join(lines) + "\n"
    print(report)

    out = EVALS / "resultados"
    out.mkdir(exist_ok=True)
    stem = f"{args.set}-{datetime.now():%Y%m%d-%H%M%S}"
    (out / f"{stem}.md").write_text(report, encoding="utf-8")
    (out / f"{stem}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardado en evals/resultados/{stem}.md")


if __name__ == "__main__":
    main()
