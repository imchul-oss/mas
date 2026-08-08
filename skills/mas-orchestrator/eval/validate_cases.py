#!/usr/bin/env python3
"""Validate eval/cases.jsonl before anyone spends tokens running it.

Why this exists: seven of the twelve cases used to name an artifact that did not exist
("this 300-line auth module", "these 5 conflicting analyst reports", "<text>"). Nothing
checked, so the 2026-06-28 run quietly executed the only three cases that needed no
attachment and the harness read as if it had a 7-case set. A case that cannot be run is
not a gap in coverage, it is a silent cap on the eval.

Checks:
  [E1] required keys present, case_id unique
  [E2] a non-null `fixture` resolves to a file that exists, relative to cases.jsonl
  [E3] a null `fixture` means the task text references no attachment
  [E4] warrant_mas is a bool and both values occur (a set with no negative cases cannot
       catch a Warrant Gate that fires too eagerly)

Exit 0 clean, 1 findings, 2 could not read the case file.
Usage: python eval/validate_cases.py [--cases PATH] | --selftest
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

REQUIRED = {"case_id", "task", "type", "warrant_mas", "fixture", "note"}
ATTACHMENT_MARKERS = ("attached", "this function", "this module", "these ", "<text>")


def validate(cases_path):
    cases_path = Path(cases_path)
    try:
        raw = cases_path.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        return None, [f"[E0] cannot read {cases_path}: {e}"]

    findings, rows, seen = [], [], set()
    for i, line in enumerate(raw, 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError as e:
            findings.append(f"[E1] line {i}: not valid JSON ({e.msg})")
            continue
        rows.append(r)

        missing = REQUIRED - set(r)
        if missing:
            findings.append(f"[E1] {r.get('case_id', f'line {i}')}: missing keys {sorted(missing)}")
            continue
        if r["case_id"] in seen:
            findings.append(f"[E1] duplicate case_id {r['case_id']}")
        seen.add(r["case_id"])

        fixture = r["fixture"]
        if fixture:
            if not (cases_path.parent / fixture).exists():
                findings.append(f"[E2] {r['case_id']}: fixture not found: {fixture}")
        else:
            hit = next((m for m in ATTACHMENT_MARKERS if m in r["task"].lower()), None)
            if hit:
                findings.append(
                    f"[E2] {r['case_id']}: task references an attachment ({hit!r}) but fixture is null")

        if not isinstance(r["warrant_mas"], bool):
            findings.append(f"[E3] {r['case_id']}: warrant_mas is not a bool")

    warrants = {r.get("warrant_mas") for r in rows if isinstance(r.get("warrant_mas"), bool)}
    if rows and warrants != {True, False}:
        findings.append("[E4] the set needs both warrant_mas values; "
                        "with no warrant=false cases nothing catches an over-eager Warrant Gate")
    return rows, findings


def _selftest():
    good = [{"case_id": "a", "task": "A self-contained question?", "type": "factual",
             "warrant_mas": False, "fixture": None, "note": "n"},
            {"case_id": "b", "task": "Audit the attached module.", "type": "audit",
             "warrant_mas": True, "fixture": "f.py", "note": "n"}]
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "f.py").write_text("x = 1\n", encoding="utf-8")
        p = d / "cases.jsonl"

        def write(rows):
            p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

        write(good)
        rows, f = validate(p)
        assert len(rows) == 2 and not f, f

        bad = [dict(good[0]), dict(good[1], fixture="missing.py")]
        write(bad)
        assert any(x.startswith("[E2]") and "fixture not found" in x for x in validate(p)[1])

        bad = [dict(good[0]), dict(good[1], fixture=None)]
        write(bad)
        assert any("references an attachment" in x for x in validate(p)[1])

        write([dict(good[0]), dict(good[1], case_id="a")])
        assert any("duplicate case_id" in x for x in validate(p)[1])

        write([dict(good[1]), dict(good[1], case_id="c")])
        assert any(x.startswith("[E4]") for x in validate(p)[1])

        write([dict(good[0]), {k: v for k, v in good[1].items() if k != "note"}])
        assert any("missing keys" in x for x in validate(p)[1])

        assert validate(d / "nope.jsonl")[1][0].startswith("[E0]")
    print("VALIDATE-CASES SELFTEST PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", default=str(Path(__file__).parent / "cases.jsonl"))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(_selftest())

    rows, findings = validate(args.cases)
    if rows is None:
        print(findings[0], file=sys.stderr)
        sys.exit(2)
    for f in findings:
        print(f)
    runnable = len(rows) - sum(1 for f in findings if f.startswith("[E2]"))
    print(f"VALIDATE-CASES {'FAIL' if findings else 'PASS'}: "
          f"{len(rows)} case(s), {runnable} runnable, {len(findings)} finding(s)")
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
