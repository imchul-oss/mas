# Upgrade Assessment 2026-08 (CLOSED)

<upgrade_assessment>

Opened 2026-08-08 against the external agent-orchestration landscape, closed 2026-08-09 when the eval
programme finished. Every candidate is resolved. Kept because the reasoning outlives the decisions -
the next proposal will resemble one of these.

## Resolved

| candidate | outcome |
|---|---|
| Run the 12-case eval | **done.** Cases 7 -> 12 with fixtures, all executed, then re-run blind with replicates. It is what retired six roles |
| MCP spec reassessment | **done, WAIT not bump.** 2026-07-28 is a breaking revision; this skill's own 6-month stability window puts adoption no earlier than 2027-01-28. See `external-spec-status.md` |
| Host-enforced structured output | **HOLD, and the reasoning still binds.** The enforcement lives in one host's orchestration tool, and a skill that depends on it stops being portable prose - which is this skill's durable value, since only the frontmatter is runtime-specific. The current design degrades correctly: schema stated in the prompt, enforced in code afterwards, on any runtime. Reverse it if the same enforcement appears runtime-neutral, or if a measured boundary error rate makes portability the more expensive side |
| An executable orchestration graph instead of prose | **moot.** Graph execution is the convergence axis across LangGraph, ADK 2.0 and CrewAI Flows, and prose orchestration was the outlier - but with two phases there is nothing to orchestrate, and the role that would have emitted the script is retired. The portability objection above still applies to anything that reintroduces host-specific orchestration |
| GEPA offline run | **retired with the optimiser.** Its fitness function was the eval scorer, and judge sd 0.10-0.38 makes that signal unresolvable at any replicate count this skill can afford. An optimiser fed an unresolvable objective ships something confidently. `_legacy/scripts/README.md` |
| DSPy MIPROv2 as a second optimiser | **closed.** Same blocker, one level removed |
| MAST-style failure attribution | **closed.** Best published methods identify the responsible agent 53.5% of the time and the failing step 14.2%. Wiring a signal that wrong into a gate produces confident misattribution, and with two roles there is little to attribute |
| Overlap with external adversarial-review skills | **resolved by subtraction.** Third-party catalogues ship fresh-context adversarial review; rather than compete, the Critic was retired and its job folded into the Verifier's own adversarial pass |

## What replaced this document

Ring assessments were the right instrument while the question was "what should we add". After the
measurements the question changed to "what has earned its place", and that is answered by
`eval/` plus guardrail 10 rather than by a landscape scan. A future candidate needs a case in
`eval/cases.jsonl` and a resolvable result from `variance_gate.py`, not a ring.

## Deliberately unchanged

The 2026-06-28 YAGNI list - A2A wire, graph/vector memory, Darwin-Godel, AFlow, MARL - stands.
Nothing in the 2026 H1 landscape moved any of them from "specified somewhere" to "measured to help",
and the bar is now higher than it was when they were skipped.

</upgrade_assessment>
