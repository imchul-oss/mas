# Canonical judge prompt

Use this verbatim for every eval judgement. Two properties are deliberate and both were learned the
hard way.

**Stable prefix first, variable part last.** Everything down to the `---` marker is identical across
every judge call, so sibling calls share the longest possible cached prefix. The 2026-08-09 run put
the task statement and document path at the TOP, which capped the shared prefix at a few dozen tokens
for no reason. This costs nothing to get right and cannot be recovered afterwards.

Caveat worth carrying: the per-call token figure this harness reports is NOMINAL, so the saving from
this ordering is not observable here - a cached read still counts its tokens. The ordering is correct
on the billing side regardless, and the reason it cannot be verified is recorded in `README.md`.

**One document per judge, absolute scoring.** A judge that never sees a sibling cannot be biased by
comparison. Scores from judges who saw both arms are not comparable with these and must not be pooled.

---

## Template

```
You are grading ONE document on an absolute rubric. You are not comparing it to anything; no other
document exists for you.

Score 1-5 on each, then give the mean as `overall`:
- accuracy: are its factual claims correct, and scoped to what the cited source actually supports
- evidence_discipline: is every load-bearing claim sourced and graded, are uncertainties declared
  rather than smoothed
- completeness: does it answer what was asked, and does it name its own gaps
- internal_consistency: does the conclusion follow from what the document itself says
- usability: could a reader act on it without another verification pass

Spot-check the riskiest 3-5 factual claims with web search before scoring accuracy. Note any claim you
find to be wrong or stale.

Reply with a compact block: the five scores, the overall to one decimal, pass (overall >= 4.0) or
fail, and up to 5 lines naming the specific defects you found.

---
TASK THE DOCUMENT ANSWERS: <task>
DOCUMENT: <absolute path>
```

## Replicates

Minimum 3 per condition, 4 preferred; `variance_gate.py` refuses a verdict below that. Judge sd
measured 2026-08-09 ran 0.096 to 0.377 on this rubric, the high end belonging to a document that
contained an error some judges found and some missed - so a document's spread is itself a signal, not
only noise.

## Secondary metric, and it is the sensitive one

Count how many judges NAME a given defect. For a targeted fix this resolves when a mean cannot: the
v2.6.0 Verifier change moved two defect-citation counts from 4-of-4 to 0-of-4 while the mean moved
0.275. Record the counts alongside the scores.
