"""Eval harness. Run: python -m eval.run_eval [--no-llm]

Suites:
  1. retrieval_cases  — hybrid search returns expected products/knowledge (no LLM)
  2. engine_cases     — deterministic engines give correct decisions (no LLM)
  3. answer_cases     — full agent answers, scored by DeepSeek as judge (needs key)

Exit code 1 if any non-LLM suite fails -> usable as a CI gate.
"""
from __future__ import annotations
import sys, json, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.retrieval.hybrid import get_corpus           # noqa: E402
from app.reasoning import chemistry, pricing, compatibility  # noqa: E402
from app.data_store import get_store                   # noqa: E402

GOLDEN = json.loads((ROOT / "eval" / "golden_set.json").read_text(encoding="utf-8"))


def _ok(cond: bool) -> str:
    return "PASS" if cond else "FAIL"


def run_retrieval() -> tuple[int, int]:
    corpus = get_corpus()
    passed = total = 0
    print("\n== retrieval_cases ==")
    for c in GOLDEN["retrieval_cases"]:
        total += 1
        prod_hits = {h["payload"]["id"] for h in corpus.search(c["query"], kind="product", k=5)}
        hit_prod = bool(set(c["expect_product_ids_any"]) & prod_hits)
        hit_kn = True
        if c.get("expect_knowledge_contains"):
            kn = " ".join(h["payload"]["text"] for h in corpus.search(c["query"], kind="knowledge", k=3)).lower()
            hit_kn = c["expect_knowledge_contains"].lower() in kn
        good = hit_prod and hit_kn
        passed += good
        print(f"  [{_ok(good)}] {c['query'][:50]:50}  got={sorted(prod_hits)}")
    return passed, total


def run_engines() -> tuple[int, int]:
    passed = total = 0
    print("\n== engine_cases ==")
    for c in GOLDEN["engine_cases"]:
        total += 1
        good = False
        try:
            if c["name"].startswith("lime"):
                r = chemistry.dosage_lime_ph(c["value"], c["target_ph"]).dict()
                good = r["total_unit"] == c["expect_total_unit"] and r["unit"] == c["expect_dose_unit"] and r["total_low"] > 0
            elif "margin floor" in c["name"]:
                d = pricing.quote_line(c["product_id"], c["qty"], c["discount_pct"]).dict()
                good = d["below_floor"] == c["expect_below_floor"] and (d["approval_required"] is not None) == c["expect_approval_not_null"]
            elif "within margin" in c["name"]:
                d = pricing.quote_line(c["product_id"], c["qty"], c["discount_pct"]).dict()
                good = d["below_floor"] == c["expect_below_floor"]
            elif "stoichiometry" in c["name"]:
                r = chemistry.stoichiometry_neutralization(c["acid_kg"], c["acid"], c["base"])
                good = r["base_kg_required"] > 0
            elif "incompatible" in c["name"]:
                store = get_store()
                prods = [store.product_by_id[i] for i in c["product_ids"]]
                good = (not compatibility.check_pairwise(prods)["safe"]) == c["expect_unsafe"]
        except Exception as e:
            print(f"  [ERR ] {c['name']}: {e}")
        passed += good
        print(f"  [{_ok(good)}] {c['name']}")
    return passed, total


def run_answers() -> tuple[float, int]:
    from app.agent.graph import run
    from app.llm import json_complete
    print("\n== answer_cases (LLM judge) ==")
    score = 0.0
    cases = GOLDEN["answer_cases"]
    for c in cases:
        ans = run(c["input"])["answer"]
        verdict = json_complete(
            "You are a strict grader. Given an answer and a rubric, score 0-5 and "
            "return JSON {\"score\": int, \"reason\": str}. 5 = fully meets rubric.",
            f"RUBRIC:\n{c['rubric']}\n\nANSWER:\n{ans}")
        s = float(verdict.get("score", 0))
        score += s
        print(f"  [{c['id']}] score={s}/5  {verdict.get('reason','')[:90]}")
    return score, len(cases) * 5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true", help="skip LLM-judged answer cases")
    args = ap.parse_args()

    rp, rt = run_retrieval()
    ep, et = run_engines()
    det_ok = (rp == rt) and (ep == et)
    print(f"\nretrieval {rp}/{rt} | engines {ep}/{et}")

    if not args.no_llm:
        try:
            asc, asm = run_answers()
            print(f"answers {asc}/{asm} ({asc/asm:.0%})")
        except Exception as e:
            print(f"answer suite skipped: {e}")

    print("\nDETERMINISTIC GATE:", "PASS" if det_ok else "FAIL")
    sys.exit(0 if det_ok else 1)


if __name__ == "__main__":
    main()
