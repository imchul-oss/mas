# Inter-Agent Communication Protocols

## Protocol Overview
<protocol_definition>
All agent-to-agent communication is asynchronous via `state/*.json`. Every state file shares these common fields:
```json
{"version": "int", "timestamp": "ISO-8601", "agent_specific": "..."}
```
- `version`: incremented by 1 on each write
- `timestamp`: last update time
</protocol_definition>

## Channels
<protocol_definition>

### Base Channels (1 to 12)
| # | File | Direction | Trigger | Content |
|---|---|---|---|---|
| 1 | prompt_output.json | Prompt Architect -> PM | Phase 1 complete | Structured prompt + thinking_trace |
| 2 | pm_plan.json | PM -> All | Phase 2 complete | Process map, Worker Pool, skill mapping, activation policies |
| 3 | research_data.json | Researcher -> Watchdog | Research complete | factcheck_package + tier_calibration_applied |
| 3.5 | watchdog_verdicts.json (correction_package) | Watchdog -> Researcher | On FALSE | Refuting evidence + research_hints |
| 4 | watchdog_verdicts.json | Watchdog -> Worker, Verifier | Verification done | Verdicts + aggregate |
| 5 | worker_output.json | Worker -> Watchdog | Task complete | thinking + answer + sources |
| 6 | feedback_loop.json | Verifier -> All | FAIL / CONDITIONAL | Per-agent feedback |
| 7 | telemetry.json | All -> Telemetry | Start / end / retry | Execution metrics |
| 8 | breakpoints.json | Orchestrator <-> User | Gate trigger | Decision options |
| 9 | worker_registry.json | PM <-> Registry <-> Worker | Phase 3, 6 | Specialist worker profile |
| 10 | pm_plan.json (required_plugins) | PM -> Plugin Registry -> Worker | Phase 2 | Plugin discovery |
| 11 | skill_registry.json | PM -> Skill Registry -> skill-creator | Phase 6 | Skill proposals |
| 12 | agent_evolution.json | Verifier / User -> PM -> agents/*.md | Phase 6 | Agent evolution |
</protocol_definition>

### Adversarial + Conflict
<protocol_definition>

#### Channel 13: Adversarial Critic <-> Verifier
- File: `state/adversarial_report.json`
- Trigger: Phase 3c complete (Complex/Expert)
- Content: counter_scenarios, coverage_gaps, adversarial_inputs, vulnerability verdict
- Verdict mapping: ROBUST -> PASS bonus / CONDITIONALLY_ROBUST -> CONDITIONAL_PASS / VULNERABLE -> FAIL

#### Channel 14: Worker Conflict Resolution
- File: `state/worker_conflicts.json`
- Trigger: Conflict detected across multiple Worker outputs
- 4-Stage: Detection -> Auto-Reconcile -> Watchdog Re-verify -> PM Arbitration Gate
</protocol_definition>

### Async + Memory + Skills + Handoff
<protocol_definition>

#### Channel 15: Async Task Lifecycle
- File: `state/async_tasks.json`
- Trigger: PM detaches a long-running task
- States: pending -> working -> completed | failed | cancelled | input_required

#### Channel 16: Memory API Sync
- File: `~/.claude/mas-state/memory_index.json` + Memory API
- Trigger: session start (import) / end (export)
- Adapter pattern

#### Channel 17: Anthropic Skills Bidirectional
- File: `state/skill_registry.json` (extended)
- Trigger: PM Phase 2 skill mapping

#### Channel 18: Worker Handoff
- File: `state/worker_handoffs.json`
- Trigger: Worker recognizes out-of-domain task -> transfer to handoff_targets
- Hop count <= 3 enforced
</protocol_definition>

### Causal, Multi-modal, SLA, Registry, Calibration, Memory
<protocol_definition>
- Causal Graph: `state/causal_dag.json` (PM Risk Register analysis)
- Multi-modal: `state/multimodal_verdicts.json` (Watchdog Pool extension)
- SLA/SLO: `state/sla_compliance.json` + new `sla_breach` gate
- MCP Registry: `state/mcp_registry_cache.json`
- Calibration: `state/calibration_estimates.json` + persistent `calibration.json`
- Long-horizon Memory: hot / warm / cold tier organization
</protocol_definition>

### Inter-Agent Harness
<protocol_definition>
- File: `state/agent_messages.json` (event bus)
- 6 protocols: review_round, debate_round, peer_review, interactive_factcheck, iterative_refinement, standup_sync
- Token control: round <= 2, hop <= 3, participants <= 5
- New gates: `review_round_continue`, `peer_review_hop_limit`, `interaction_token_budget_breach`
</protocol_definition>

### Federation
<protocol_definition>
- Files: `federation_messages.json` + `federation_registry.json` + per-instance state
- 9 message types: task_request, audit_request / audit_response, learning_share, status_query / status_response, result_return, heartbeat, termination_signal
- 4 patterns: hub_spoke (recommended), hierarchical, peer_to_peer, swarm
- ManagedAgentsAdapter (production path)
</protocol_definition>

### Context Architecture
<protocol_definition>
- All natural-language outputs are wrapped with `<thinking>` + `<answer>` + source/uncertainty XML tags.
- `xml_parser.py` performs mechanical validation -> Verifier `context_architecture_compliance` dimension.
- Worker handoffs preserve XML tags so the chain remains parseable.
</protocol_definition>

## Feedback Loop Termination
<protocol_definition>

```python
def should_continue_loop():
    if iteration >= max_iterations: return False
    if verdict == "PASS": return False
    threshold, source = get_adaptive_threshold(complexity)
    if abs(scores[-1] - scores[-2]) < threshold: return False  # convergence
    if has_negative_gradient_3plus(): return False  # decline
    if recommend_checkpoint_rollback(): return False  # rollback path
    return True
```
</protocol_definition>

## Sequence Diagram
<protocol_definition>

```
User -> Orchestrator: task + breakpoint policy
Orchestrator -> StateManager: init + telemetry
Orchestrator -> PromptArchitect: Phase 1 (with <thinking>)
PromptArchitect -> State: prompt_output.json (with thinking_trace)
Orchestrator -> PM: Phase 2
PM -> State: pm_plan.json (Pool/Adversarial/Polisher decisions)
GATE: phase_2_plan_review
Orchestrator -> Researcher: Phase 3a
Researcher -> State: research_data.json (with Memory import, tier_calibration)
Orchestrator -> Watchdog Pool x3: Phase 3b
Watchdog Pool -> State: watchdog_pool_verdicts.json (consensus)
GATE: phase_3b_false_detected | watchdog_disagreement_arbitration
Orchestrator -> Worker Pool: Phase 3c (handoff, schema, budget)
Worker Pool -> State: worker_output_W*.json (thinking + answer XML)
Conflict Detection -> GATE: worker_conflict_resolution
Orchestrator -> Adversarial Critic: Phase 3c.5 (Complex/Expert)
Adversarial Critic -> State: adversarial_report.json
Orchestrator -> Polisher: Phase 3c.7 (Moderate+, fact-preserving)
Polisher -> State: polisher_report.json + worker_output_polished.json
Orchestrator -> Verifier: Phase 4 (9-dim rubric + xml_parser)
Verifier -> State: verifier_report.json (with context_architecture_compliance)
GATE: phase_4_verification_result
alt [PASS] -> Final + Memory export
alt [FAIL] -> Phase 5 feedback loop (with checkpoint rollback option)
```
</protocol_definition>
