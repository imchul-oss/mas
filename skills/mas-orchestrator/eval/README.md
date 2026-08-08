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

### Fixtures

Seven of the twelve cases hand the agent an artifact, which lives in `fixtures/` and is named by the
case's `fixture` field. Before 2026-08-08 those cases named an artifact that did not exist ("this
300-line auth module", "these 5 conflicting analyst reports", `<text>`), so only the five
self-contained cases could actually be run - which is why the 2026-06-28 run covered three cases and
still read as a full harness. A case that cannot be run is not a coverage gap, it is a silent cap.

The fixtures are built so the right answer is checkable rather than a matter of taste: `audit-1`
carries defects of differing severity so the RANKING can be graded, `synth-1`'s fifth report averages
three of the other four so a correct answer must catch the double-count, `synth-2`'s three sources
measure different scopes so any averaged figure is wrong, `audit-2`'s "local variable" binds a shared
dict, and `code-refactor-1` hides load-bearing behavior (atomic replace, silent default on malformed
config, backoff, loop-survives-failure) that a careless split drops.

```bash
python eval/validate_cases.py            # every case runnable? (also in CI)
python eval/validate_cases.py --selftest
```

## Run 2026-08-08 - the four warrant=false cases

One run per file. `results.jsonl` is the current run; `results-2026-06-28.jsonl` is the earlier one.
They are NOT merged, because the scorer keys on `case_id` alone and would silently combine two cases
of the same name measured under different conditions - which it did once before this split.

| case | single | mas | gain | tokens | verdict |
|---|---|---|---|---|---|
| fact-1 | 4.5 | 4.5 | +0.0 | 2.03x | single_sufficient |
| rewrite-1 | 3.8 | 4.6 | +0.8 | 2.05x | **mas_worth_it** |
| code-small-1 | 4.4 | 4.8 | +0.4 | 2.11x | single_sufficient |
| research-3 | 4.3 | 4.8 | +0.5 | 2.23x | **mas_worth_it** |

**The Warrant Gate's cost premise does not hold on this harness.** SKILL.md justifies single-agent-by-
default with "~15x the tokens". Measured here the compact pipeline costs **2.03x to 2.23x**, because a
sub-agent's base context is roughly 50,000 tokens before it does any work, and that floor dominates
everything else. The same fact-1 case cost 25,313 tokens as a single agent in June and 50,125 in
August with no change to the task. At 2x rather than 15x, a verification pass is cheap and "is this
worth a second agent" has a different answer than the gate assumes.

Read that narrowly. This measured a **2-agent** Worker plus Verifier chain, not the 8-agent pipeline.
Eight agents at a ~50k floor each would land far closer to the original 15x, so the finding supports
cheap verification, not the full pipeline.

**Two warrant=false cases were won by MAS, and the gate is not what was wrong.** The README rule says
a MAS win on a warrant=false case means the gate is mis-sized. Here the Verifier earned it on merit:
in `rewrite-1` the single agent silently strengthened a condition ("stating which fields are missing"
where the source only says fields are missing) and nobody caught it, while the Verifier did; in
`research-3` it caught three real errors in a confident answer - the 1986 collapse was the LBL to UC
Berkeley path and not NSFNET, the RTO doubling is RFC 6298 §5.5 rather than Karn's algorithm, and the
Chiu-Jain result is scoped to linear controls. Settled-knowledge questions are exactly where a
confident single agent misattributes, so "cost of being wrong" may be the warrant signal that matters
rather than task type.

**Judge limitation, stated rather than implied**: scoring was done by the session model knowing which
arm produced which answer. That is a bias in MAS's favour on the two cases where the Verifier's catch
is the whole difference. A blind re-score is the correction, and it has not been done.

**Outstanding**: the eight warrant=true cases have not been run. `code-small-1`'s fixture does not
actually raise on a None name - the `if p` filter is evaluated before `p.strip()` - so the case
accidentally became a second false-premise test rather than the surgical-edit test it was meant to
be, and both arms correctly rejected the premise. It needs either a fixture that really raises or an
honest reclassification. Until the full run exists, SKILL.md guardrail 11 still blocks any new
learning loop or added agent from shipping.

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
