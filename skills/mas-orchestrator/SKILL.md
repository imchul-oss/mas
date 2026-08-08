---
name: mas-orchestrator
description: "8-agent collaborative MAS — Context Architecture with mandatory XML tags, Multi-Watchdog Debate, Bayesian convergence, Adversarial Critic, Polisher, MCP async tasks, Memory API, checkpointing, handoff, federation. Triggers: MAS, multi-agent, systematic analysis, evidence-based verification, fact-check, thorough audit, self-check, system audit, polish, causal analysis, SLA."
---

## Output Language Policy
<output_language_policy>
- **Internal processing**: English (all definition and reference files).
- **User-facing output**: Korean by default. Switch to another language only when the user explicitly instructs otherwise.
- **Breakpoint / gate messages**: Korean.
</output_language_policy>

# MAS Orchestrator — 8-Agent + Context Architecture

## System Overview
<system_overview>
Eight specialized agents collaborate inside an XML-tag based document ecosystem (Context Architecture). Each agent has independent responsibility, applies proportional response to task complexity, and produces machine-parseable outputs with measurable simplicity guarantees.

**Core Principle**: Independent agent responsibility + Proportional Response + machine-parseable docs + measurable simplicity.

**8 Agents**: Prompt Architect, PM, Researcher, Watchdog Pool, Worker, Adversarial Critic, Polisher, Verifier.
</system_overview>

## Token Efficiency Protocol
<token_efficiency_protocol>
**Rule 0 dominates the rest: cut AGENTS before you cut payload.** Measured 2026-08-08 over 20
sub-agent runs, a sub-agent costs about **50,000 tokens of base context before it does any work**;
across cases the whole spread ran 50,125 to 70,445. Every rule below trims the payload *on top of*
that floor, so removing one agent saves more than perfectly optimising the context of four. The
rules stay because they are close to free, but a plan that adds a phase to save context has the
arithmetic backwards.

Two consequences worth stating: an 8-agent pipeline costs ~400k in floor alone regardless of task
size, so proportional response is a COST control and not only a quality one; and on small tasks the
floor is nearly the entire bill, which is why the measured Worker+Verifier ratio sits near 2.0x
rather than scaling with task difficulty.

1. **Fewest agents that can do the job** - the only lever that moves the dominant term.
2. **Lazy Loading**: `agents/*.md` is loaded only when that phase is entered.
3. **Reference-Pointer Communication**: pass state file paths, not contents.
4. **Selective Context Injection**: each sub-agent receives only the files it needs.
5. **Compressed Handoff**: summarized `feedback_directive` only.
6. **References Lazy Loading**: PM determines necessity before loading.
7. **Async Tasks Offloading**: long-running tasks are detached via task handles.
8. **Checkpoint Summary**: only the most recent checkpoint summary is retained.
9. **Selective XML Tagging**: section-level wrapping only, never paragraph-level.
</token_efficiency_protocol>

## Quality Guardrails
<quality_guardrails>
1. **Absolute no-hallucination**: "unverifiable" is preferred over unsourced claims.
2. **Fact-based enforcement**: Researcher prioritizes Tier 1-2 sources.
3. **Automatic framework selection**: PM picks the framework per task.
4. **Conciseness**: Worker output is clear without losing substance.
5. **Critical analysis first**: Verifier integrates its own rubric with Adversarial input.
6. **Proportional Response**: simple tasks do not require all 8 agents.
7. **Concurrency Safety**: file lock + atomic write.
8. **External Spec Compliance**: MCP / Memory / Skills versions are pinned.
9. **Context Architecture Compliance**: XML tag convention is enforced.
10. **`<thinking>` mandatory**: Complex / Expert agents must externalize reasoning before answering.
11. **Eval-justified complexity**: any new learning loop or added agent must beat a single-agent baseline on `eval/` before it ships. Complexity is earned against a measurable eval, not assumed.
</quality_guardrails>

## Sub-Agent Optimization
<sub_agent_optimization>

| Phase | Agent | Model | Rationale |
|---|---|---|---|
| 1 | Prompt Architect (Complex/Expert) | sonnet | Structuring XML-tagged prompts |
| 2 | PM / Orchestrator | opus | Multi-decision accuracy |
| 3a | Researcher | sonnet | Search throughput |
| 3b | Watchdog (single) | opus | Factual accuracy |
| 3b | Watchdog Pool x3 (Complex/Expert) | opus x3 | Multi-agent debate |
| 3c | Worker (simple) | sonnet | Single skill |
| 3c | Worker (complex) | opus | Multi-skill |
| 3c.5 | Adversarial Critic (Complex/Expert) | opus | Adversarial verification |
| 3c.7 | Polisher (Moderate+) | sonnet | Polish throughput |
| 4 | Verifier | opus | QA accuracy |

Model routing is **static** (the table above). Dynamic telemetry-based routing is intentionally deferred until the eval harness (`eval/`) can prove it beats the static table — see Cost & Context Strategy.
</sub_agent_optimization>

## MAS Warrant Gate
<mas_warrant_gate>
**Two cost figures, and using the wrong one mis-sizes this gate.** The ~15x in Anthropic's *Building a multi-agent research system* (2025) describes a deep many-agent research run. **Measured on this runtime (`eval/`, 8 cases, 2026-08-08), a Worker+Verifier pair costs 1.83x to 2.23x**, because a sub-agent carries roughly 50,000 tokens of base context before it does any work and that floor dominates everything else. Read the number that matches the shape you are about to run: a verify pair is ~2x, and eight agents at that floor approach the original figure.

**The decision axis is not task type, and not stakes.** Measured across the same 8 cases: the single agent found every planted trap - it rejected a false thread-safety premise and measured the race to prove it, caught a double-counted forecast and solved for the hidden source, called out a category error across mismatched statistics, and found every planted auth defect. MAS never won by seeing more of the problem. It won, twice, by a Verifier catching the **first agent's own** error: a lock scoped to the wrong object, a mis-multiplied revision range, a discarded datum, a floor contradicting its own argument. It lost the other two because the single agent had simply made no such error.

So the pipeline raises the FLOOR, not the ceiling. What ~2x buys is variance reduction. Ask accordingly:

1. **Single-agent default.** One-shot lookup, short rewrite, known-answer question, small surgical edit → answer with one agent and say in one line that MAS was skipped.
2. **The warrant question: how expensive is an occasional wrong answer here?** Warranted when the output is load-bearing and ships without a second reader - a fix that gets applied, a number that gets quoted, a severity ranking that sets work order, an irreversible action. Not warranted when the reader checks it anyway, when the task is self-verifying, or when being wrong costs a re-ask. Task type is a poor proxy: two audits warranted it and two syntheses did not, and all four were "high stakes" by the old signals.
3. **The warranted default is a PAIR, not the pipeline.** Worker + Verifier is what earned its keep in measurement. Going beyond it needs a stated reason - genuinely independent sub-questions that parallelize (Researcher fan-out), a contested factual base (Watchdog Pool), an adversarial requirement the Verifier cannot self-serve (Critic). Absent one of those, more agents buy base context, not quality.
4. **Right-size to complexity** (Phase 0.5) once past the gate.

**Tested 2026-08-08 on the case most favourable to the pipeline.** `research-2` - the one case the June run scored `mas_worth_it`, needing external material, parallel decomposition and evidence grading - was run three ways: single 4.4 at 88,735 tokens, pair **4.8** at 184,175 (2.08x), full 10-agent Complex spec **4.1** at 1,253,663 (14.13x). The full spec cost 6.81x the pair, scored lower, and did not converge - its own Verifier returned CONDITIONAL_PASS 3.22/5 with a blocking defect, so a shippable artifact needs a Phase 5 pass on top of the 1.25M.

**And the reason is an ordering defect, not weak agents.** The Watchdog Pool's corrections landed, because the Worker reads them and is the author. The Critic's did not: it caught a false claim, and nothing downstream can act on one, since the Verifier makes no direct edits and the Polisher never alters facts. The deliverable shipped that claim at Established grade while self-reporting zero propagated false verdicts. **A phase that produces findings after the last agent able to edit the artifact is speculative work.** Before escalating past the pair, check that every phase you add still has an author downstream of it.
</mas_warrant_gate>

## Cost & Context Strategy
<cost_context_strategy>
1. **Prompt caching (biggest cost lever).** Put the stable shared prefix (this SKILL.md, role definitions, tool defs, shared context) at the *front* of every sub-agent call so it is cache-hit (cached reads ≈ 0.1x input cost). Order content stable-prefix-first; never interleave volatile content into the cached region.
2. **`effort` over model-swap.** Use a low/medium reasoning-effort setting for routine coordination and reserve high effort for genuinely hard reasoning (Critic, Verifier, conflict arbitration). Cheaper than swapping to a bigger model.
3. **Context isolation, not context dumping.** Each sub-agent explores in its own window and returns a **distilled 1,000–2,000 token summary**, not its raw transcript (Anthropic, *Effective context engineering*, 2025). "Context rot" is measured: recall degrades as input grows, well before the window limit.
4. **Just-in-time context.** Pass reference pointers (state file paths, queries, IDs), not payloads. Load full content only when a specific agent needs it.
5. **Structured Outputs for machine handoffs.** Constrained-decoding JSON-schema enforcement (`response_format`) lives only at the Anthropic Messages API layer; the Claude Code Agent/Task tool that spawns sub-agents does **not** expose it (sub-agent frontmatter is `context`/`agent`/`allowed-tools`/`model`/`effort`/`hooks` — no output-format control), so a skill cannot force schema-valid output at the agent boundary. Instead, for agent→agent machine-parsed payloads (PM plans, verdicts, schemas): **(a)** state the target JSON schema explicitly in the sub-agent prompt, and **(b)** enforce it post-hoc in code with `state_manager.validate_worker_output_schema()` plus a single self-correction retry on violation. Keep **XML tags** for reasoning-rich outputs that interleave `<thinking>` + `<answer>` — forcing complex reasoning into rigid JSON degrades it.
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
[Phase 0: Init] -- session_state, async_tasks, breakpoints
   |
[Phase 0.5: Complexity Classification]
   | (Simple / Moderate / Complex / Expert)
   |
[Phase 1: Prompt Architect] (Complex/Expert) -- mandatory <thinking>
   |
[Phase 2: PM Orchestrator]
   |- Skill mapping (local + Anthropic Skills)
   |- Worker Pool design + structured_output_schema
   |- Watchdog Pool activation
   |- Adversarial Critic activation
   |- Async task candidates
   |- Checkpoint strategy
   |- Polisher activation
   | -> GATE: phase_2_plan_review
   |
[Phase 3a: Researcher] (+ Memory API import)
   |
[Phase 3b: Watchdog Pool x3] (Complex/Expert)
   | -> GATE: phase_3b_false_detected | watchdog_disagreement_arbitration
   |
[Phase 3c: Worker Pool] (+ Handoff, Structured Output, Token Budget)
   | conflict detection
   | -> GATE: worker_conflict_resolution
   |
[Phase 3c.5: Adversarial Critic] (Complex/Expert)
   |
[Phase 3c.7: Polisher] (Moderate+) -- fact-preserving polish
   |
[Phase 4: Verifier]
   |- Watchdog Pool synthesis
   |- Adversarial input integration
   |- Schema compliance
   |- Polisher metrics
   |- context_architecture_compliance
   | -> GATE: phase_4_verification_result
   |
[Phase 5: Feedback Loop] (if needed) + checkpoint rollback
   |
[Phase 6: Final + Memory API export]
```
</agent_architecture>

## Execution Protocol
<execution_protocol>

### Phase 0: Initialization
```bash
python scripts/state_manager.py --state-dir ./state init --task "<summary>"
python scripts/state_manager.py --state-dir ./state breakpoint --action set-policy --policy auto
```
Atomic writes + file lock. Async tasks and handoffs are initialized here. XML lint runs before agent phases.

### Phase 0.5: Complexity Classification

Baseline for every tier is the **pair**: Worker + Verifier. Everything else is opt-in against a named
trigger, because at ~50,000 tokens per agent a default-on role bills whether or not it was needed,
and none of the opt-in roles has ever been measured against a single-agent baseline (guardrail 11,
applied to incumbents - see `references/architecture.md`).

| Complexity | Researcher | Watchdog | Adversarial | Polisher | Prompt Architect | Async | Checkpoint | Handoff | `<thinking>` |
|---|---|---|---|---|---|---|---|---|---|
| Simple | on trigger | off | off | off | off | off | off | off | optional |
| Moderate | on trigger | on trigger | off | on trigger | off | optional | off | off | on |
| Complex | on trigger | on trigger | on trigger | on trigger | off | on | on | optional | on |
| Expert | on trigger | 3 (Pool) | on | on trigger | on trigger | on | on | on | on |

**Triggers.** Researcher: the task needs material not already in context (a lookup, a source, a file
nobody has read). Watchdog: the factual base is contested or a wrong fact is unrecoverable; Pool of 3
only when the three would read DIFFERENT material, since three agents over one document give
correlated votes. Adversarial Critic: an adversarial requirement the Verifier's re-derivation step
cannot self-serve - it reads the same artifact the Verifier does, so it is redundancy until that is
shown false. Polisher: the output has a named audience and a style contract; measured single-agent
output needed no polish pass. Prompt Architect: the request is genuinely ambiguous AND will be
consumed by several agents.

PM runs in light mode by default and is the one role that may not spawn to decide a spawn - at 50,000
tokens, an orchestrator deciding between cheap options costs more than the decision saves.

### Phases 1 to 6
Each phase consults the relevant `agents/*.md` definition. All agent definitions use the XML-tag convention defined in `references/context-architecture.md`.

Gate IDs are listed in the Gate Definitions section below.
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
| phase_2_plan_review | 2 | PM plan finalized |
| phase_3b_false_detected | 3 | Watchdog FALSE |
| watchdog_disagreement_arbitration | 3 | Pool split after Round 2 |
| phase_3c_worker_start | 3 | Before Worker start |
| worker_conflict_resolution | 3 | Worker conflict unresolved |
| phase_4_verification_result | 4 | Verifier completed |
| feedback_loop_iteration | 5 | Feedback loop iteration begins |
| async_task_timeout | 3 | Async task timeout |
| memory_api_sync_failure | 0 | Memory import failure |
| sla_breach | 4 | Critical SLA breach |
| multimodal_vision_call | 3b | Vision API opt-in |
| calibration_recalibration | 6 | 5 real observations accumulated; recommend mapping refresh |
| review_round_continue | 3 | Review consensus dispersion |
| peer_review_hop_limit | 3 | Hop >= 3 |
| interaction_token_budget_breach | 3 | Interaction cost overrun |
| specialist_worker_promotion | 6 | PM promotion recommendation |
| skill_creation_review | 6 | Skill creation proposal |
| agent_evolution_review | 6 | Agent evolution proposal |
| skillopt_deploy_best | 6 | best_score > current_baseline |
| goal_driven_max_iter | 3 | Goal-driven loop reaches max_iterations without meeting all criteria |
</gate_definitions>

## Error Handling
<error_handling>
- Agent failure: up to 2 retries.
- Watchdog Pool split: Round 2 -> user gate.
- Worker conflict: 4-stage auto resolution -> user gate.
- Async task timeout: user gate.
- Memory API failure: local fallback.
- Infinite feedback loop: max 3 iterations.
- XML tag orphan detected: single self-correction; failure deducts the Verifier dimension.
- All errors are logged to `state/error_log.json`.
</error_handling>

## Agent Detail References
<agent_references>

| Agent | File |
|---|---|
| Prompt Architect | `agents/prompt-architect.md` |
| PM / Orchestrator | `agents/pm-orchestrator.md` |
| Researcher | `agents/researcher.md` |
| Watchdog | `agents/watchdog.md` |
| Worker | `agents/worker.md` |
| Adversarial Critic | `agents/adversarial-critic.md` |
| Polisher | `agents/polisher.md` |
| Verifier | `agents/verifier.md` |

References: `references/architecture.md`, `protocols.md`, `state-schema.md`, `evolution-policy.md`, `context-architecture.md`, `skill-catalog.md`, `c-integration-notes.md`, `federation-architecture.md`, `karpathy-guidelines.md`, `skillopt-integration.md`, `external-spec-status.md`, `upgrade-assessment-2026-08.md`.
</agent_references>
