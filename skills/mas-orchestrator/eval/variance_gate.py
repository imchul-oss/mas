#!/usr/bin/env python3
"""Is a recorded single-vs-MAS delta bigger than the judge noise that produced it?

Why this exists: the 2026-06-28 through 2026-08-09 runs all recorded ONE judge score per
arm and drew verdicts from the difference. Measured on 2026-08-09 with 4 independent
judges over the same two documents, the judge standard deviation is 0.10 to 0.38 on a
1-5 rubric, which puts the standard error of an n=1 difference at about 0.39. Eleven of
the twelve deltas the programme recorded are smaller than that. A verdict at n=1 is not
a measurement, it is one draw.

The same run found the thing worth measuring instead. The two arms' MEANS were 4.475 and
4.450, a difference of 0.025, while their spreads were 0.377 and 0.100. The verification
pass did not move the average, it collapsed the variance - which is what "raises the
floor, not the ceiling" means when it is measured rather than asserted.

So this gate reports two things per case: whether the delta of means clears the noise
floor, and what happened to the spread. It refuses a verdict rather than issuing a weak
one - `UNRESOLVED` is the correct output for n=1, not a quiet pass.

Exit 0 when every case with a claimed verdict is resolvable, 1 when a claimed verdict
rests on an unresolvable delta, 2 when the file cannot be read.
Usage: python eval/variance_gate.py --results eval/results.jsonl [--min-n 3] | --selftest
"""
import argparse
import json
import statistics as st
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

# Measured 2026-08-09, research-1, 4 independent judges per arm, identical prompts.
MEASURED_POOLED_SD = 0.276

# Zero observed spread at n=3 does not mean zero true spread. Measured 2026-08-09:
# code-refactor-1 returned 4.8 three times in BOTH arms, which drove the threshold to
# 0.00 and would have let any nonzero delta through on a spuriously certain variance.
# Scores are recorded on a 0.1 grid, so one grid step is the smallest spread that can
# be claimed honestly.
SD_FLOOR = 0.1


def _se_of_delta(a, b):
    """Welch standard error from the OBSERVED spreads when replicates exist.

    The fallback constant is only for an arm with no replicates. Using it everywhere was
    a real defect, found 2026-08-09 the first time this gate met a genuine effect: the
    constant comes from a document whose score varied 0.377 because it contained an error
    some judges found and some missed, and applying that spread to two tightly-clustered
    arms (sd 0.100 and 0.096) refused a +0.275 difference that is roughly 4 standard
    errors out. A gate calibrated on the noisiest case rejects real results everywhere
    else; measure the arms you actually have.
    """
    var_a = max(st.variance(a), SD_FLOOR ** 2) if len(a) > 1 else MEASURED_POOLED_SD ** 2
    var_b = max(st.variance(b), SD_FLOOR ** 2) if len(b) > 1 else MEASURED_POOLED_SD ** 2
    return (var_a / max(len(a), 1) + var_b / max(len(b), 1)) ** 0.5


def analyse(path, min_n=3):
    try:
        rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, json.JSONDecodeError) as e:
        return None, [f"[V0] cannot read {path}: {e}"]

    by = defaultdict(list)
    for r in rows:
        if "case_id" in r and "mode" in r and "overall_score" in r:
            by[(r["case_id"], r["mode"])].append(float(r["overall_score"]))

    cases = sorted({c for c, _ in by})
    out, findings = [], []
    for case in cases:
        a, b = by.get((case, "single"), []), by.get((case, "mas"), [])
        if not a or not b:
            continue
        delta = st.mean(a) - st.mean(b)
        se = _se_of_delta(a, b)
        threshold = 1.96 * se
        resolvable = abs(delta) > threshold
        row = {
            "case": case, "n_single": len(a), "n_mas": len(b),
            "mean_single": round(st.mean(a), 3), "mean_mas": round(st.mean(b), 3),
            "delta": round(delta, 3), "threshold": round(threshold, 3),
            "verdict": "RESOLVED" if resolvable else "UNRESOLVED",
            "sd_single": round(st.stdev(a), 3) if len(a) > 1 else None,
            "sd_mas": round(st.stdev(b), 3) if len(b) > 1 else None,
        }
        out.append(row)
        if not resolvable:
            findings.append(f"[V1] {case}: delta {delta:+.2f} is inside the noise floor "
                            f"(+/-{threshold:.2f} at n={len(a)}/{len(b)}); no verdict is supported")
        if len(a) < min_n or len(b) < min_n:
            findings.append(f"[V2] {case}: {len(a)}/{len(b)} judge score(s) per arm, "
                            f"below the {min_n} replicates a delta needs")
    return out, findings


def _selftest():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "r.jsonl"

        def write(rows):
            p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

        # n=1 per arm with a big-looking gap: must refuse
        write([{"case_id": "x", "mode": "single", "overall_score": 4.8},
               {"case_id": "x", "mode": "mas", "overall_score": 4.4}])
        rows, f = analyse(p)
        assert rows[0]["verdict"] == "UNRESOLVED", rows
        assert any(x.startswith("[V1]") for x in f) and any(x.startswith("[V2]") for x in f)

        # replicated and genuinely separated: must resolve
        write([{"case_id": "y", "mode": "single", "overall_score": v} for v in (4.9, 4.8, 4.9, 5.0)] +
              [{"case_id": "y", "mode": "mas", "overall_score": v} for v in (3.9, 4.0, 3.8, 4.0)])
        rows, f = analyse(p)
        assert rows[0]["verdict"] == "RESOLVED", rows
        assert not any(x.startswith("[V1]") for x in f)
        assert rows[0]["sd_single"] is not None and rows[0]["sd_mas"] is not None

        # replicated, wide spread, small gap: refuse despite the replicates
        write([{"case_id": "z", "mode": "single", "overall_score": v} for v in (4.9, 4.2, 4.5)] +
              [{"case_id": "z", "mode": "mas", "overall_score": v} for v in (4.8, 4.1, 4.6)])
        assert analyse(p)[0][0]["verdict"] == "UNRESOLVED"

        # tight spreads make a small gap resolvable - the case the fixed-constant
        # version wrongly refused
        write([{"case_id": "t", "mode": "single", "overall_score": v} for v in (4.4, 4.4, 4.4, 4.6)] +
              [{"case_id": "t", "mode": "mas", "overall_score": v} for v in (4.6, 4.8, 4.8, 4.7)])
        assert analyse(p)[0][0]["verdict"] == "RESOLVED", analyse(p)[0]

        # identical scores in both arms must NOT drive the threshold to zero
        write([{"case_id": "f", "mode": "single", "overall_score": 4.8} for _ in range(3)] +
              [{"case_id": "f", "mode": "mas", "overall_score": 4.9} for _ in range(3)])
        row = analyse(p)[0][0]
        assert row["threshold"] > 0.1, row
        assert row["verdict"] == "UNRESOLVED", row

        # an arm missing entirely is skipped, not crashed
        write([{"case_id": "w", "mode": "single", "overall_score": 4.0}])
        assert analyse(p)[0] == []

        assert analyse(Path(d) / "nope.jsonl")[1][0].startswith("[V0]")
    print("VARIANCE-GATE SELFTEST PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default=str(Path(__file__).parent / "results.jsonl"))
    ap.add_argument("--min-n", type=int, default=3)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(_selftest())

    rows, findings = analyse(args.results, args.min_n)
    if rows is None:
        print(findings[0], file=sys.stderr)
        sys.exit(2)
    for r in rows:
        sd = f" sd {r['sd_single']}/{r['sd_mas']}" if r["sd_single"] is not None else ""
        print(f"{r['case']:<18} n={r['n_single']}/{r['n_mas']} "
              f"means {r['mean_single']}/{r['mean_mas']} delta {r['delta']:+.2f} "
              f"(needs >{r['threshold']:.2f}){sd}  {r['verdict']}")
    for f in findings:
        print(f)
    unresolved = sum(1 for r in rows if r["verdict"] == "UNRESOLVED")
    print(f"VARIANCE-GATE: {len(rows)} case(s), {unresolved} unresolved")
    sys.exit(1 if unresolved else 0)


if __name__ == "__main__":
    main()
