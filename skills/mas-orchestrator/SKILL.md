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
1. **Lazy Loading**: `agents/*.md` is loaded only when that phase is entered.
2. **Reference-Pointer Communication**: pass state file paths, not contents.
3. **Selective Context Injection**: each sub-agent receives only the files it needs.
4. **Compressed Handoff**: summarized `feedback_directive` only.
5. **References Lazy Loading**: PM determines necessity before loading.
6. **Async Tasks Offloading**: long-running tasks are detached via task handles.
7. **Checkpoint Summary**: only the most recent checkpoint summary is retained.
8. **Selective XML Tagging**: section-level wrapping only, never paragraph-level.
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

PM may apply cost-aware routing based on telemetry (`state_manager.recommend_model_for_task`).
</sub_agent_optimization>

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

| Complexity | Watchdog Pool | Adversarial | Polisher | Async | Checkpoint | Handoff | `<thinking>` |
|---|---|---|---|---|---|---|---|
| Simple | off | off | optional | off | off | off | optional |
| Moderate | 1 | off | on | optional | off | off | on |
| Complex | 3 (Pool) | on | on | on | on | optional | on |
| Expert | 3 (Pool) | on | on | on | on | on | on |

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
| review_round_continue | 3 | Review consensus dispersion |
| peer_review_hop_limit | 3 | Hop >= 3 |
| interaction_token_budget_breach | 3 | Interaction cost overrun |
| specialist_worker_promotion | 6 | PM promotion recommendation |
| skill_creation_review | 6 | Skill creation proposal |
| agent_evolution_review | 6 | Agent evolution proposal |
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

References: `references/architecture.md`, `protocols.md`, `state-schema.md`, `evolution-policy.md`, `context-architecture.md`, `skill-catalog.md`, `c-integration-notes.md`, `federation-architecture.md`, `karpathy-guidelines.md`, `skillopt-integration.md`.
</agent_references>
