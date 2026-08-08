# MAS eval harness

The point of an eval: **prove the 8-agent MAS beats a single agent by enough to justify ~15x the tokens.** Without this, "more agents = better" is an unverified assumption (and the research record says it often isn't true).

## How to run an eval

For each case in `cases.jsonl`, run the task **twice** — once with the full MAS pipeline, once with a single well-prompted agent (same model, same tools) — and append both as records to `results.jsonl`:

```json
{"case_id": "research-1", "mode": "single", "passed": true,  "overall_score": 3.6, "tokens": 4200}
{"case_id": "research-1", "mode": "mas",    "passed": true,  "overall_score": 4.4, "tokens": 58000}
```

Score with the same rubric for both runs (rules-based checks first, then a length-normalized, position-randomized LLM judge — see `agents/verifier.md` Verification Layering). Then:

```bash
python eval/scorer.py eval/results.jsonl
```

The scorer reports, per case and in aggregate, whether MAS earned its token cost (`mas_worth_it`) or the single agent was sufficient (`single_sufficient`).

## Reading the result

- **`warrant_mas: false` cases** should come back `single_sufficient`. If MAS "wins" a trivial lookup, the Warrant Gate is mis-sized — fix the gate, don't celebrate.
- **`warrant_mas: true` cases** are where MAS must earn its keep (research, audit, synthesis). If it doesn't win these, the pipeline isn't pulling its weight.

~20 representative cases are enough to see large effect sizes; add human spot-checks for edge cases an LLM judge misses. Keep `cases.jsonl` small and representative, not exhaustive.

## Case set (12 cases as of 2026-08-08)

Expanded from 7. A case earns its place by being able to FALSIFY something, so each new one names
what it discriminates rather than what it covers:

| case | warrant | what it can falsify |
|---|---|---|
| fact-2 | true | the no-hallucination guardrail. Recency trap where the correct answer may be "cannot verify" |
| research-3 | false | Warrant Gate OVER-firing. Settled textbook knowledge wearing a research shape; if MAS fires, the gate is reading task type instead of task difficulty |
| audit-2 | true | sycophancy. The task asserts a false premise and asks for confirmation; the correct answer rejects it |
| code-refactor-1 | true | Verifier substance on code. Multi-skill refactor where "behavior unchanged" has to be argued, not asserted |
| synth-2 | true | conflict detection vs conflict smoothing. An averaged number is a failure even when it reads well |

The set is deliberately 8 warrant-true / 4 warrant-false: the false cases exist to catch a gate that
fires too eagerly, which is the failure mode that costs money silently.

**Run status: not yet executed.** `results.jsonl` holds the 3-case run from 2026-06-28. The 12-case
run is the outstanding work; until it exists, SKILL.md guardrail 11 blocks any new learning loop or
added agent from shipping.

## Sample run (`results.jsonl`)

A committed 3-case run (each task executed twice — single agent vs. a compact MAS pipeline of real subagents, scored on one rubric with bias controls):

| case | warrant | single | mas | verdict | tokens |
|---|---|---|---|---|---|
| fact-1 (Apollo year) | false | 4.5 pass | 4.5 pass | single_sufficient | 2.0x |
| research-1 (messaging privacy) | true | 4.2 pass | 4.5 pass | single_sufficient | 2.9x |
| research-2 (hallucination detection) | true | 4.0 pass | 4.7 pass | **mas_worth_it** | 2.85x |

**MAS earned its cost on 1/3 cases.** It won research-2 because the Verifier layer caught two citation errors the single agent missed (a wrong FacTool source ID and an unverified arXiv ID). It did *not* win the trivial fact (correctly — overkill) or research-1 (a single agent already answered well).

Two honest caveats: (1) the token ratio here is ~2-3x, not the ~15x of deep many-agent research — this pipeline used only 2-3 subagents, where the per-agent base context cost dominates. (2) Scores are this judge's; a real eval pairs them with human spot-checks. The takeaway holds: MAS pays off specifically where independent verification catches errors, not as a blanket default.

## Self-check

`python eval/scorer.py` (no args) runs a built-in self-check on the three verdict paths.
