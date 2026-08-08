# Upgrade Assessment 2026-08

<upgrade_assessment>

Assessment of upgrade candidates for v2.1.0, made 2026-08-08 against the external agent-orchestration
landscape. Verdicts use four rings: **adopt** (do it), **trial** (do it behind a measurement),
**assess** (keep watching, do not build), **hold** (decided against for a stated reason).

The controlling fact for all of it: `eval/results.jsonl` holds 3 executed cases, and they show MAS at
+0.0 / +0.3 / +0.7 rubric points for 2.0x / 2.89x / 2.85x the tokens. Guardrail 11 makes every added
loop or agent conditional on beating a single-agent baseline, so nothing below ships ahead of the
12-case run.

## Portability is the axis that decides the two biggest candidates

This skill's durable value is that `SKILL.md` and `agents/*.md` are runtime-portable prose. Only the
frontmatter block is runtime-specific, so moving to another agent runtime is a frontmatter swap. Two
otherwise-attractive candidates would spend exactly that.

### Structured output enforced by the host runtime - **hold**

`SKILL.md` Cost & Context Strategy 5 states the sub-agent boundary has no output-format control and
prescribes post-hoc validation plus one self-correction retry. On the Claude Code harness as of
2026-08-08 that is no longer true: its Workflow tool takes a JSON Schema per agent call, forces a
structured-output tool call, and validates at the tool-call layer with model-side retries.

Adopting it would delete our validation code and improve reliability at the agent boundary. It is
held anyway, because the enforcement lives in one host's orchestration tool, and a skill that depends
on it stops being portable prose. The current design already degrades correctly: schema stated in the
prompt, enforced in code afterwards, which works on any runtime.

What would change the verdict: the same enforcement appearing as a runtime-neutral capability rather
than one vendor's tool, or a measured error rate at the agent boundary high enough that portability
is the more expensive side of the trade. Neither is measured today.

### PM emits an executable orchestration graph instead of prose - **assess**

Graph-based execution is the convergence axis across LangGraph, Google ADK 2.0 and CrewAI Flows;
prose orchestration inside one session is the outlier. A PM that emitted a deterministic script
(fan-out, barriers, budget, resume) would get real parallel execution and a replayable run.

It is not built, for two reasons. It has the same portability cost as the candidate above, larger,
since orchestration becomes host-specific rather than one field. And the eval says the pipeline has
not yet earned its current cost, so buying more orchestration machinery is buying scale for something
whose value per unit is unmeasured. Sequence matters here: the eval first, then this.

## Remaining candidates

| candidate | ring | reasoning |
|---|---|---|
| 12-case eval run | **adopt** | Cases expanded 7 -> 12 on 2026-08-08. Execution is outstanding and everything else waits on it |
| MCP spec reassessment | **adopt** | Done, see `references/external-spec-status.md`. Outcome was WAIT, not a version bump |
| GEPA one offline run | **trial** | The engine exists and its fitness function is the eval scorer, so it is blocked on the eval, not on the optimizer |
| DSPy MIPROv2 as the optimizer | **assess** | Would be a second optimizer with the same blocker. Judge only if GEPA runs and disappoints |
| MAST-style failure attribution | **assess** | The best published methods identify the responsible agent 53.5% of the time and the failing step 14.2%. Wiring a signal that wrong into a gate would produce confident misattribution |
| Overlap with external adversarial-review skills | **assess** | Third-party skill catalogs now ship fresh-context adversarial review, which is the Adversarial Critic's job. If an external skill does it as well, our version should shrink to what is specific to this pipeline rather than duplicate a maintained one |

## Deliberately unchanged

The 2026-06-28 YAGNI list (A2A wire, graph/vector memory, Darwin-Godel, AFlow, MARL) stands. Nothing
in the 2026 H1 landscape moved any of them from "specified somewhere" to "measured to help".

</upgrade_assessment>
