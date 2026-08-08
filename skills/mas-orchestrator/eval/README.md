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

## Run 2026-08-08 part 2 - the four cases with planted ground truth

These four were run second because they are the ones whose right answer is fixed in the fixture
rather than decided by a judge's taste, which is the correction to the bias noted below.

| case | single | mas | gain | tokens | verdict |
|---|---|---|---|---|---|
| audit-1 | 4.2 | 4.8 | +0.6 | 2.15x | **mas_worth_it** |
| audit-2 | 4.3 | 4.9 | +0.6 | 1.83x | **mas_worth_it** |
| synth-1 | 4.6 | 4.7 | +0.1 | 2.05x | single_sufficient |
| synth-2 | 4.7 | 4.7 | +0.0 | 1.99x | single_sufficient |

**Both arms found every planted trap.** The single agent rejected audit-2's false premise (and went
as far as installing a free-threading interpreter to measure the race), picked synth-2's 186 GW and
identified source C as a category error, caught synth-1's double-count and even solved for the hidden
fourth forecast, and found every planted defect in audit-1. Nothing in this batch was won by MAS
noticing something the single agent missed in the fixture.

**MAS won where a SECOND look at the first agent's own output was needed.** In audit-2 the Worker
proposed a per-instance `threading.Lock` for state held on a class attribute, and the Verifier
measured that fix failing (10,738 of 40,000 when each thread holds its own instance) before replacing
it. In audit-1 the Verifier added three findings the Worker missed, including that a 32-bit reset
token is brute-forceable even after the seeding bug is fixed, and it found a second independent
trigger for the fail-open path. In synth-2 the Worker got `186 x 1.04` wrong as a 186-195 range and
overstated an arithmetic tension as an internal contradiction; the Verifier corrected both. In
synth-1 the Worker discarded the recoverable fourth forecast and set a floor that contradicted its
own bias argument.

**So the pipeline raises the floor, it does not raise the ceiling.** The two cases MAS did not win
are the two where the single agent simply did not make a mistake for a Verifier to catch - and note
that in synth-2 the single agent got the arithmetic right that the MAS Worker got wrong. What is
being bought at roughly 2x is variance reduction, not capability. That points the Warrant Gate at a
different question than the one it asks: not "is this task type hard" and not even "are the stakes
high", but "how expensive is an occasional wrong answer here". Both audits are load-bearing outputs
where one bad fix ships; both syntheses are analyses a reader would sanity-check anyway.

## RETRACTION 2026-08-09 - every mean-comparison verdict below is withdrawn

Judge variance was measured last, and it should have been measured first. Four independent judges,
identical prompts, over the same two documents:

| document | judge scores | mean | sd |
|---|---|---|---|
| research-1 single | 4.8, 4.1, 4.8, 4.2 | 4.475 | **0.377** |
| research-1 pair | 4.4, 4.4, 4.4, 4.6 | 4.450 | **0.100** |

The delta of means is **+0.025**. The single-replicate reading of the same pair, taken hours earlier,
was 4.8 against 4.4 and reported as a 0.4-point deficit for the pair. That 0.4 was one draw of the
judge. Pooled sd is 0.276, so the standard error of an n=1 difference is 0.391 and nothing under about
0.77 is resolvable at n=1. **Eleven of the twelve deltas this programme recorded are inside that
floor**, and the twelfth (rewrite-1, +0.8) was self-scored rather than blind. `mas_worth_it` counts
computed from those deltas do not mean what they appear to mean.

### What the same measurement DID establish

The two arms' averages are indistinguishable and their spreads are not: **0.377 against 0.100, a
3.8x collapse in variance.** The verification pass does not raise the average answer, it removes the
bad tail - which is what "raises the floor, not the ceiling" means once it is measured instead of
asserted, and it is the first claim in this programme that survives its own noise.

The mechanism is visible in the judges' own comments. The single-agent document contains a real error:
it states in three places, graded `확실`, that Signal offers no cloud backup, which stopped being true
when Signal Secure Backups shipped 2025-09-08. Two of four judges found it and marked accuracy down to
3.5-4; two missed it and gave 5. Its score therefore depends on judge luck. The pair's Verifier had
already caught and corrected that claim, so all four judges converged on the same residual defects.
**Buying a verification pass buys predictability, not a better average.**

### Harness fix

`variance_gate.py` refuses a verdict rather than issuing a weak one - `UNRESOLVED` is the correct
output at n=1, and a quiet pass is how this went unnoticed for six weeks.

```bash
python eval/variance_gate.py --results eval/results.jsonl   # exit 1 if any verdict is unsupported
python eval/variance_gate.py --selftest
```

A future run needs at least 3 judge replicates per arm. Everything below is retained as data, not as
findings.

---

## Run 2026-08-09 - blind scoring, and the three remaining warrant-true cases

The judge bias flagged in every earlier run is corrected here. Each artifact was graded by its own
judge, **one document per judge, absolute rubric, no knowledge that a sibling arm existed** -
comparison bias cannot operate on a judge with nothing to compare. Role markers were stripped from
the artifacts first (`blind_key.json` holds the mapping). Rubric: accuracy, evidence discipline,
completeness, internal consistency, usability, each 1-5, mean reported.

| case | single | pair | delta | pair cost |
|---|---|---|---|---|
| research-1 | **4.8** | 4.4 | -0.4 | 1.86x |
| fact-2 | **4.8** | 4.6 | -0.2 | 2.15x |
| code-refactor-1 | 4.8 | 4.8 | +0.0 | 1.92x |
| research-2 | 4.2 | **4.7** | +0.5 | 2.08x |

**On three of four the pair did not beat the single agent, and on two it scored lower.** The pair is
worth its 2x on a minority of tasks; elsewhere it is 2x for nothing or for a deficit.

Two failure modes made the deficits, and both are fixed in v2.6.0:

1. **A verification pass can introduce an error and certify it.** In research-1 the Verifier
   corrected a figure's attribution, put a wrong reporting period in its place (a full-year total
   labelled as Q4), graded it `확실`, and recorded in its own log that it had re-verified the number
   directly. The grading system that should have caught the error blessed it instead.
2. **A correction log inside the deliverable reads as padding.** Three judges independently docked
   it: "the twenty-line verification log is outside the question", "about a third of the document is
   correction narrative", "F1-F6 and R1-R5 cite a worker report the reader does not have". The
   instruction that produced this was added in v2.5.0 the day before, which is how fast an
   improvement can become a defect without a blind reader.

**Calibration of my own scores.** research-2 is the one case scored both ways: self-scored 4.4 / 4.8
/ 4.1 (single / pair / full) against blind 4.2 / 4.7 / 4.2. The ranking survived; the margins were
mine, and the full arm was the one I under-scored.

**Judge limitation of the EARLIER runs, stated rather than implied**: scoring was done by the session model knowing which
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
