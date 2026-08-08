---
name: mas-orchestrator
description: "Worker plus Verifier: a second pass in fresh context that re-derives the first agent's output and authors the corrected final. Warrant-gated - it runs only where an occasional wrong answer is expensive, and answers directly otherwise. Triggers: verification pass, fact-check, evidence-based verification, thorough audit, self-check, system audit, second opinion, check my work."
---

## Output Language Policy
<output_language_policy>
- **Internal processing**: English (all definition and reference files).
- **User-facing output**: Korean by default. Switch to another language only when the user explicitly instructs otherwise.
- **Breakpoint / gate messages**: Korean.
</output_language_policy>

# MAS Orchestrator - Worker + Verifier

## System Overview
<system_overview>
**Two roles: Worker, then Verifier.** The Worker produces the deliverable; the Verifier reads it in fresh context, re-derives what it can, applies the corrections and authors the final artifact. That is the whole architecture.

It used to be eight. The other six were removed on 2026-08-09 because the eval said so, not because they were badly written - none had ever beaten a single-agent baseline, which guardrail 11 has required since v2.0.0, and the ten-agent configuration measured 14.13x the tokens for a lower score while shipping a false claim its own Critic had caught. What each of them was measured to contribute was folded into these two: partitioned-axis reading into the Verifier, evidence discipline into the Worker. Definitions and restoration conditions are kept in `_legacy/agents/`.

**Core principle**: an agent boundary must change what is SEEN, not what is ASKED. A different instruction is a section in a prompt and costs nothing; a different context window costs about 50,000 tokens.
</system_overview>

## Token Efficiency Protocol
<token_efficiency_protocol>
**Rule 0: cut AGENTS before you cut payload - in NOMINAL tokens, which is the only unit measured
here.** A sub-agent costs about **50,000 tokens of base context before it does any work** (measured
2026-08-08 over 20 runs; the spread ran 50,125 to 70,445). Every rule below trims payload *on top of*
that floor, so removing one agent saves more than perfectly optimising four - and a plan that adds a
phase to save context has the arithmetic backwards.

**The caveat is load-bearing and was missed for two days.** Every figure in this file is a nominal
token count, not a billed cost. Prompt caching bills a cached read at roughly a tenth of fresh input,
and the ~50k base - shared system prompt and tool definitions, identical across sibling sub-agents -
is precisely the most cacheable part of the bill. If the host shares that prefix across siblings,
the marginal BILLED cost of one more agent is far below its nominal 50k and rule 0 weakens
accordingly. Measured 2026-08-09: the orchestrating session runs at a **98.6% cache hit rate**, so
caching is demonstrably active there; sub-agent billed cost could not be measured at all, because no
sidechain record reaches the session transcript and the per-call token figure is nominal - four
byte-identical judge prompts varied 3.5%, where a cache discount would show an order of magnitude.
So: rule 0 is established in nominal tokens and UNVERIFIED in billed cost. What would settle it is a
per-sub-agent usage record carrying `cache_read_input_tokens`.

**What is actionable regardless: order a sub-agent prompt stable-prefix-first.** Put the rubric,
role, and shared instructions ahead of the task-specific part, so sibling agents share the longest
possible identical prefix. This is Cost & Context Strategy rule 1, and the 2026-08-09 eval harness
violated it - the judge prompts opened with the task and the document path, which caps the shared
prefix at a few dozen tokens for no reason.

Two consequences worth stating: a ten-agent pipeline cost ~500k in floor alone regardless of task
size, so proportional response is a COST control and not only a quality one; and on small tasks the
floor is nearly the entire bill, which is why the measured Worker+Verifier ratio sits near 2.0x
rather than scaling with task difficulty.

1. **Fewest agents that can do the job** - the only lever that moves the dominant term.
2. **Lazy Loading**: `agents/*.md` is loaded only when that phase is entered.
3. **Reference-Pointer Communication**: pass state file paths, not contents.
4. **Selective Context Injection**: each sub-agent receives only the files it needs.
5. **Compressed Handoff**: summarized `feedback_directive` only.
6. **References Lazy Loading**: load a reference only when the phase needs it.
7. **Async Tasks Offloading**: long-running tasks are detached via task handles.
8. **Checkpoint Summary**: only the most recent checkpoint summary is retained.
9. **Selective XML Tagging**: section-level wrapping only, never paragraph-level.
</token_efficiency_protocol>

## Quality Guardrails
<quality_guardrails>
1. **Absolute no-hallucination**: "unverifiable" is preferred over unsourced claims.
2. **Fact-based enforcement**: the Worker prioritises Tier 1-2 sources and says which it opened.
3. **Conciseness**: Worker output is clear without losing substance.
4. **The Verifier authors**: it applies its corrections rather than describing them, and its correction log stays out of the deliverable.
5. **Proportional Response**: the Warrant Gate answers directly with one agent unless a wrong answer is expensive.
6. **Concurrency Safety**: file lock + atomic write.
7. **External Spec Compliance**: MCP / Memory / Skills versions are pinned.
8. **Context Architecture Compliance**: XML tag convention is enforced.
9. **`<thinking>` mandatory**: both roles externalise reasoning before answering.
10. **Eval-justified complexity**: any added agent or learning loop must beat a single-agent baseline on `eval/` before it ships. This rule retired six of the original eight roles on 2026-08-09 when it was finally applied to incumbents; it applies to anything you want to add back.
</quality_guardrails>

## Sub-Agent Optimization
<sub_agent_optimization>

| Phase | Agent | Model | Rationale |
|---|---|---|---|
| 1 | Worker | session model | Produces the deliverable |
| 1 | Worker Pool 2-5 | session model | Only when sub-tasks are independent AND each reads different material |
| 2 | Verifier | session model | Re-derives, corrects, authors the final |

**Never run the Verifier below the Worker's model.** A judge that is weaker than the author does not
verify less, it reports confidently on what was fine while missing what was not, and the whole value
of this pair is the second read. Save on generation if you must; never on the check.

Model routing is static. Dynamic telemetry-based routing stays deferred until `eval/` can show it
beats the static table, and the same rule that retired six roles applies to it.
</sub_agent_optimization>

## MAS Warrant Gate
<mas_warrant_gate>
**Two cost figures, and using the wrong one mis-sizes this gate.** The ~15x in Anthropic's *Building a multi-agent research system* (2025) describes a deep many-agent research run. **Measured on this runtime (`eval/`, 8 cases, 2026-08-08), a Worker+Verifier pair costs 1.83x to 2.23x**, because a sub-agent carries roughly 50,000 tokens of base context before it does any work and that floor dominates everything else. Read the number that matches the shape you are about to run: a verify pair is ~2x, and eight agents at that floor approach the original figure.

**The decision axis is not task type, and not stakes.** Measured across the same 8 cases: the single agent found every planted trap - it rejected a false thread-safety premise and measured the race to prove it, caught a double-counted forecast and solved for the hidden source, called out a category error across mismatched statistics, and found every planted auth defect. MAS never won by seeing more of the problem. It won, twice, by a Verifier catching the **first agent's own** error: a lock scoped to the wrong object, a mis-multiplied revision range, a discarded datum, a floor contradicting its own argument. It lost the other two because the single agent had simply made no such error.

So the pipeline raises the FLOOR, not the ceiling. What ~2x buys is variance reduction. Ask accordingly:

1. **Single-agent default.** One-shot lookup, short rewrite, known-answer question, small surgical edit → answer with one agent and say in one line that MAS was skipped.
2. **The warrant question: how expensive is an occasional wrong answer here?** Warranted when the output is load-bearing and ships without a second reader - a fix that gets applied, a number that gets quoted, a severity ranking that sets work order, an irreversible action. Not warranted when the reader checks it anyway, when the task is self-verifying, or when being wrong costs a re-ask. Task type is a poor proxy: two audits warranted it and two syntheses did not, and all four were "high stakes" by the old signals.
3. **The pair is the whole architecture.** Worker + Verifier is what survived measurement; the only sanctioned expansion is a Worker Pool where sub-tasks are independent and each instance reads different material. Anything else buys base context, not quality, and guardrail 10 governs adding it back.
4. **Right-size to complexity** (Phase 0.5) once past the gate.

**What is actually measured, after judge variance was quantified (2026-08-09).** Four independent judges over the same two documents gave the single-agent artifact 4.8/4.1/4.8/4.2 (mean 4.475, **sd 0.377**) and the pair's 4.4/4.4/4.4/4.6 (mean 4.450, **sd 0.100**). The averages are indistinguishable - delta +0.025 - and the spread collapses 3.8x. Pooled sd 0.276 puts the standard error of an n=1 difference at 0.391, so **eleven of the twelve deltas this eval recorded are inside the noise floor** and the verdicts drawn from them are withdrawn (`eval/README.md`, retraction; `eval/variance_gate.py` now refuses a verdict at n=1).

So the one claim that survives its own noise is the one this gate rests on: **a verification pass buys predictability, not a better average.** The mechanism is visible - the single artifact carried a real error graded `확실` (that Signal offers no cloud backup, untrue since 2025-09-08); two of four judges caught it and two did not, so its score depended on judge luck, while the pair had corrected it and all four judges converged. Route on the cost of an occasional bad answer, because that is the only thing the pair reliably changes.

**Blind-scored 2026-08-09, and the pair stopped winning (superseded above - these were n=1 readings).** Nine artifacts were graded by independent judges, one document each, on an absolute rubric, with no knowledge that a sibling arm existed - the correction to the judge bias flagged in every earlier run. Across three cases not previously run, the pair never beat the single agent: research-1 4.8 vs **4.4**, fact-2 4.8 vs **4.6**, code-refactor-1 4.8 vs 4.8. On research-2 the pair still won, 4.7 vs 4.2. So the pair is worth its 2x on a minority of tasks, and on the rest it is 2x for nothing or worse.

The two ways it went NEGATIVE are both fixed in this version and are worth knowing as failure modes. A verification pass can **introduce** an error and certify it: one Verifier corrected an attribution, substituted a wrong reporting period, graded it `확실`, and logged that it had re-verified the number. And a correction log inside the deliverable reads as padding: three judges independently docked "a verification log outside the question", "a third of the document is correction narrative", and citations to a worker report the reader does not have.

Calibration note on my own earlier scores: on research-2, the only case scored both ways, self-scored against blind was single 4.4 -> 4.2, pair 4.8 -> 4.7, full 4.1 -> 4.2. The ranking held; the margins were mine.

**Tested 2026-08-08 on the case most favourable to the pipeline.** `research-2` - the one case the June run scored `mas_worth_it`, needing external material, parallel decomposition and evidence grading - was run three ways: single 4.4 at 88,735 tokens, pair **4.8** at 184,175 (2.08x), full 10-agent Complex spec **4.1** at 1,253,663 (14.13x). The full spec cost 6.81x the pair, scored lower, and did not converge - its own Verifier returned CONDITIONAL_PASS 3.22/5 with a blocking defect, so a shippable artifact needs a Phase 5 pass on top of the 1.25M.

**And the reason is an ordering defect, not weak agents.** The Watchdog Pool's corrections landed, because the Worker reads them and is the author. The Critic's did not: it caught a false claim, and nothing downstream can act on one, because at the time the Verifier was forbidden to edit and the only role after it could not alter facts. The deliverable shipped that claim at Established grade while self-reporting zero propagated false verdicts. **A phase that produces findings after the last agent able to edit the artifact is speculative work.** That is fixed as of this version - the Verifier authors the corrected artifact - and the rule generalises: before adding any phase, check it still has an author downstream of it.
</mas_warrant_gate>

## Cost & Context Strategy
<cost_context_strategy>
1. **Prompt caching (biggest cost lever).** Put the stable shared prefix (this SKILL.md, role definitions, tool defs, shared context) at the *front* of every sub-agent call so it is cache-hit (cached reads ≈ 0.1x input cost). Order content stable-prefix-first; never interleave volatile content into the cached region.
2. **`effort` over model-swap.** Use a low/medium reasoning-effort setting for routine coordination and reserve high effort for genuinely hard reasoning (Critic, Verifier, conflict arbitration). Cheaper than swapping to a bigger model.
3. **Context isolation, not context dumping.** Each sub-agent explores in its own window and returns a **distilled 1,000–2,000 token summary**, not its raw transcript (Anthropic, *Effective context engineering*, 2025). "Context rot" is measured: recall degrades as input grows, well before the window limit.
4. **Just-in-time context.** Pass reference pointers (state file paths, queries, IDs), not payloads. Load full content only when a specific agent needs it.
5. **Structured Outputs for machine handoffs.** Constrained-decoding JSON-schema enforcement (`response_format`) lives only at the Anthropic Messages API layer; the Claude Code Agent/Task tool that spawns sub-agents does **not** expose it (sub-agent frontmatter is `context`/`agent`/`allowed-tools`/`model`/`effort`/`hooks` — no output-format control), so a skill cannot force schema-valid output at the agent boundary. Instead, for agent→agent machine-parsed payloads (plans, verdicts, schemas): **(a)** state the target JSON schema explicitly in the sub-agent prompt, and **(b)** enforce it post-hoc in code with `state_manager.validate_worker_output_schema()` plus a single self-correction retry on violation. Keep **XML tags** for reasoning-rich outputs that interleave `<thinking>` + `<answer>` — forcing complex reasoning into rigid JSON degrades it.
</cost_context_strategy>

## Observability & Headless Operation
<observability_headless>
**Observability (mandatory for multi-agent).** Handoff drops, runaway token spend, and looping sub-agents are only diagnosable with a span tree + per-agent token attribution. Every agent step and tool call emits one OpenTelemetry-GenAI-shaped span:
```bash
python scripts/state_manager.py telemetry --action record --agent researcher \
  --operation invoke_agent --model claude-sonnet --input-tokens N --output-tokens N --parent <span_id>
python scripts/state_manager.py telemetry --action summary   # tokens + derived cost per agent
```
Field names follow the OTel GenAI convention (`gen_ai.usage.*`, `gen_ai.agent.name`, `parent_span_id`), so `telemetry.json` can be replayed into Langfuse/Phoenix over OTLP later with no rework. This is also the data the **Verifier efficiency dimension** and `eval/` token attribution consume, and the per-agent credit signal GEPA needs. `cost_usd` is a local derived field (OTel does not standardize cost).

**Headless / Hermes mode.** The skill runs unattended (Hermes NAS agent, cron). Set the breakpoint policy to `auto` at init so gates log + auto-resolve instead of blocking on a human:
```bash
python scripts/state_manager.py breakpoint --action set-policy --policy auto
```
All learning writers (`source-reliability`, `telemetry`, `memory-entry`) are plain file appends — safe in headless and concurrent runs (atomic write + lock).
</observability_headless>

## Agent Architecture
<agent_architecture>

```
USER REQUEST
   |
[Warrant Gate] -- is an occasional wrong answer expensive here?
   | no  -> one agent, say in a line that the pair was skipped, stop
   | yes
   |
[Phase 0: Init] -- session_state (optional; a single-pass run needs no state dir)
   |
[Phase 1: Worker] -- <thinking> then <answer>; evidence discipline; declares its gaps
   | Pool of 2-5 ONLY when sub-tasks are independent and each reads different material
   |
[Phase 2: Verifier] -- fresh context, AUTHORS the corrected final artifact
   |- Worker-Output Re-Derivation (5 checks, mandatory)
   |- partitioned axes when the artifact is too large for one sweep
   |- applies its corrections rather than describing them
   |- grades its own additions at the standard it applied to the Worker
   |- correction log goes to a SEPARATE report, never into the deliverable
   | -> GATE: phase_4_verification_result
   |
[Phase 3: Feedback Loop] (only if the Verifier withheld a pass) -- max 3 iterations
   |
[Final]
```

**Authorship rule (2026-08-08, from the `research-2` full-spec run).** Every phase that produces
findings must have an author downstream of it, or be one itself. This is why the Verifier authors
instead of judging, and it is the rule that decided which roles could survive at all: in the measured
ten-agent run the Critic correctly identified a false claim and the deliverable shipped it at
Established grade, because everything between the finding and delivery was forbidden to touch facts.
Any phase you add back must satisfy this rule before anything else.
</agent_architecture>

## Execution Protocol
<execution_protocol>

### Phase 0: Initialization
```bash
python scripts/state_manager.py --state-dir ./state init --task "<summary>"
python scripts/state_manager.py --state-dir ./state breakpoint --action set-policy --policy auto
```
Atomic writes + file lock. Async tasks and handoffs are initialized here. XML lint runs before agent phases.

### Phase 0.5: Right-sizing

There is no complexity table any more, because there are no optional roles to switch on. The Warrant
Gate decides one agent or two; past that the only remaining question is whether the Worker is one
instance or a pool, and a pool is warranted only when the sub-tasks are independent and each instance
reads different material.

`<thinking>` is on for both roles at all times. It costs nothing and the Verifier's re-derivation is
unreadable without the Worker's reasoning to check against.

### Phases 1 to 3
Each phase consults its `agents/*.md` definition. Both use the XML-tag convention in
`references/context-architecture.md`. Gate IDs are below.
</execution_protocol>

## State Management
<state_management>

```
./state/ (session-local)
|- session_state.json
|- prompt_output.json (+ thinking_trace)
|- pm_plan.json
|- research_data.json
|- watchdog_verdicts.json
|- watchdog_pool_verdicts.json
|- worker_output.json (+ thinking + answer XML)
|- worker_conflicts.json
|- worker_handoffs.json
|- adversarial_report.json
|- polisher_report.json
|- verifier_report.json (+ context_architecture_compliance)
|- feedback_loop.json
|- iteration_log.json
|- async_tasks.json
|- telemetry.json
|- breakpoints.json
|- _checkpoints/

~/.claude/mas-state/ (persistent)
|- meta.json (+ convergence_bayes, memory_api)
|- process_policy.json
|- worker_registry.json
|- skill_registry.json
|- agent_evolution.json
|- memory_index.json
|- source_reliability.json
|- calibration.json
```
</state_management>

## Gate Definitions
<gate_definitions>

| gate_id | Phase | Trigger |
|---|---|---|
| phase_4_verification_result | 2 | Verifier completed |
| feedback_loop_iteration | 3 | Feedback loop iteration begins |
| worker_conflict_resolution | 1 | Worker Pool conflict unresolved |
| async_task_timeout | 1 | Async task timeout |
| sla_breach | 2 | Critical SLA breach |

Gate ids kept their historical names so existing state files and `state_manager.py` still parse.
Fourteen gates belonging to retired roles were removed with them; they are listed in
`_legacy/agents/README.md` if a role is ever restored.

</gate_definitions>

## Error Handling
<error_handling>
- Agent failure: up to 2 retries.
- Worker conflict: 4-stage auto resolution -> user gate.
- Async task timeout: user gate.
- Infinite feedback loop: max 3 iterations.
- XML tag orphan detected: single self-correction; failure deducts the Verifier dimension.
- All errors are logged to `state/error_log.json`.
</error_handling>

## Agent Detail References
<agent_references>

| Agent | File |
|---|---|
| Worker | `agents/worker.md` |
| Verifier | `agents/verifier.md` |

Retired 2026-08-09 and kept with their restoration conditions: `_legacy/agents/`.

References: `references/architecture.md`, `protocols.md`, `state-schema.md`, `evolution-policy.md`, `context-architecture.md`, `skill-catalog.md`, `c-integration-notes.md`, `federation-architecture.md`, `karpathy-guidelines.md`, `skillopt-integration.md`, `external-spec-status.md`, `upgrade-assessment-2026-08.md`.
</agent_references>
