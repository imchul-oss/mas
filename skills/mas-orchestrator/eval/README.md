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

## Self-check

`python eval/scorer.py` (no args) runs a built-in self-check on the three verdict paths.
