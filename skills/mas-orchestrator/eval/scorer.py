#!/usr/bin/env python3
"""
MAS eval scorer
===============

Answers the only question that justifies a multi-agent system:
*does the 8-agent MAS beat a single agent by enough to be worth ~15x the tokens?*

This does NOT run the MAS (that is a Claude skill executed per-case by the
orchestrator). It ingests run records — one MAS run and one single-agent
baseline run per case — and produces a per-case and aggregate verdict.

Record schema (results.jsonl, one JSON object per line):
    {
      "case_id": "q1",
      "mode": "mas" | "single",
      "passed": true,                # met the case's acceptance bar
      "overall_score": 4.2,          # 1-5 rubric (LLM-judge or human)
      "tokens": 51000,               # total tokens for the run
      "agents_fired": ["pm","researcher","worker","verifier"],  # mas only
      "tool_calls": 12,
      "wall_ms": 38000
    }

A case is "MAS worth it" when MAS passed, the single agent did not OR MAS
scored materially higher, AND the quality gain clears the token-cost bar.

Usage:
    python eval/scorer.py eval/results.jsonl
    python eval/scorer.py            # runs the built-in self-check demo
"""

import json
import sys
from pathlib import Path

# A quality gain must clear this to justify the token multiple it cost.
# 0.3 rubric points per 1x token multiple (e.g. 15x tokens needs +4.5? no —
# we cap: any pass-flip is worth it; for score-only gains require >= MIN_SCORE_GAIN).
MIN_SCORE_GAIN = 0.5          # rubric points; below this, MAS quality gain is noise
MAX_JUSTIFIED_TOKEN_RATIO = 20.0  # above this, even a pass-flip is questioned


def load_results(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def pair_by_case(records):
    """Group records into {case_id: {"mas": rec, "single": rec}}."""
    cases = {}
    for r in records:
        cases.setdefault(r["case_id"], {})[r["mode"]] = r
    return cases


def score_case(pair):
    """Return a verdict dict for one case's mas/single pair."""
    mas = pair.get("mas")
    single = pair.get("single")
    if not mas or not single:
        return {"verdict": "incomplete", "reason": "missing mas or single run"}

    token_ratio = mas["tokens"] / max(single["tokens"], 1)
    score_gain = mas["overall_score"] - single["overall_score"]
    pass_flip = mas["passed"] and not single["passed"]

    if pass_flip:
        worth = token_ratio <= MAX_JUSTIFIED_TOKEN_RATIO
        reason = ("MAS passed where single failed"
                  + ("" if worth else f" but cost {token_ratio:.1f}x (> {MAX_JUSTIFIED_TOKEN_RATIO}x)"))
    elif single["passed"] and not mas["passed"]:
        worth = False
        reason = "regression: MAS failed where single passed"
    else:
        # both passed (or both failed) -> judge on score gain vs cost
        worth = score_gain >= MIN_SCORE_GAIN and token_ratio <= MAX_JUSTIFIED_TOKEN_RATIO
        reason = f"score gain {score_gain:+.2f} at {token_ratio:.1f}x tokens"

    return {
        "verdict": "mas_worth_it" if worth else "single_sufficient",
        "token_ratio": round(token_ratio, 2),
        "score_gain": round(score_gain, 2),
        "pass_flip": pass_flip,
        "reason": reason,
    }


def aggregate(records):
    cases = pair_by_case(records)
    per_case = {cid: score_case(pair) for cid, pair in cases.items()}
    complete = {c: v for c, v in per_case.items() if v["verdict"] != "incomplete"}
    worth = [c for c, v in complete.items() if v["verdict"] == "mas_worth_it"]
    ratios = [v["token_ratio"] for v in complete.values() if "token_ratio" in v]
    return {
        "n_cases": len(cases),
        "n_complete": len(complete),
        "mas_worth_it": len(worth),
        "single_sufficient": len(complete) - len(worth),
        "mas_worth_pct": round(100 * len(worth) / len(complete), 1) if complete else 0.0,
        "median_token_ratio": round(sorted(ratios)[len(ratios) // 2], 2) if ratios else None,
        "per_case": per_case,
    }


def _demo():
    """Self-check: three synthetic cases exercising the three verdict paths."""
    records = [
        # case q1: MAS flips a fail->pass at acceptable cost -> worth it
        {"case_id": "q1", "mode": "single", "passed": False, "overall_score": 2.8, "tokens": 4000},
        {"case_id": "q1", "mode": "mas", "passed": True, "overall_score": 4.3, "tokens": 52000},
        # case q2: both pass, trivial gain at high cost -> single sufficient
        {"case_id": "q2", "mode": "single", "passed": True, "overall_score": 4.1, "tokens": 3500},
        {"case_id": "q2", "mode": "mas", "passed": True, "overall_score": 4.2, "tokens": 49000},
        # case q3: MAS regresses -> single sufficient
        {"case_id": "q3", "mode": "single", "passed": True, "overall_score": 4.0, "tokens": 3000},
        {"case_id": "q3", "mode": "mas", "passed": False, "overall_score": 3.1, "tokens": 60000},
    ]
    agg = aggregate(records)
    assert agg["per_case"]["q1"]["verdict"] == "mas_worth_it", agg["per_case"]["q1"]
    assert agg["per_case"]["q2"]["verdict"] == "single_sufficient", agg["per_case"]["q2"]
    assert agg["per_case"]["q3"]["verdict"] == "single_sufficient", agg["per_case"]["q3"]
    assert agg["mas_worth_it"] == 1 and agg["single_sufficient"] == 2, agg
    print(json.dumps(agg, ensure_ascii=False, indent=2))
    print("\n[demo] self-check passed")


def main():
    if len(sys.argv) < 2:
        _demo()
        return
    path = Path(sys.argv[1])
    agg = aggregate(load_results(path))
    print(json.dumps(agg, ensure_ascii=False, indent=2))
    print(f"\nMAS earned its cost on {agg['mas_worth_it']}/{agg['n_complete']} "
          f"cases ({agg['mas_worth_pct']}%), median {agg['median_token_ratio']}x tokens.")


if __name__ == "__main__":
    main()
