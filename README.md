# MAS Orchestrator Plugin

**v2.1.0** · Production-grade 8-agent Multi-Agent System (MAS) orchestrator for Claude Code / Claude Desktop. One skill, no dependencies, headless-safe (Hermes/cron).

A multi-agent system costs ~15x the tokens of a single agent, so this skill is **on-demand and self-gating**: even when triggered, a **Warrant Gate** (SKILL.md) drops to a single agent for tasks that don't justify the pipeline. The MAS earns its cost on read-heavy research, audits, and high-stakes synthesis — not on lookups or small edits. Its design is grounded in 2025-2026 research (Anthropic context-engineering / multi-agent, Berkeley MAST, GEPA, ThinkPRM, OTel-GenAI) and its complexity is held accountable by an `eval/` harness.

---

## What's new in 2.1.0

Observability, reliability, and offline optimization — all additive, headless-safe (Hermes/cron):

- **OTel-GenAI telemetry** (`telemetry` CLI) — one span per agent step/tool call with `parent_span_id` (span tree), `gen_ai.usage.*` tokens, and derived `cost_usd`. Fixes the previously-dead `telemetry.json`; feeds the Verifier efficiency dimension, `eval/` token attribution, and GEPA's per-agent credit. Replayable into Langfuse/Phoenix over OTLP.
- **Typed handoff contracts** — `record_worker_handoff(..., contract={objective, output_format, boundaries, allowed_tools})`; missing fields warn, never block (the ~79%-of-MAS-failures coordination class).
- **Typed memory** — `memory-entry` CLI: episodic/semantic/procedural entries with timestamp + supersession-by-key (validity-based forgetting, no graph DB). Aligned with Anthropic's GA file-based memory tool.
- **GEPA reflective optimizer** (`scripts/gepa_optimizer.py`) — Pareto-front prompt evolution over (quality, cost) using `eval/scorer.py` as fitness; engine implemented + tested, LLM callbacks injected, runs offline. Ship a mutated prompt only if it Pareto-dominates the baseline.
- **Step-level generative verification** (ThinkPRM) and **ACE delta-merge** (append deltas, never wholesale-rewrite persistent docs) added to the Verifier / evolution policy.
- **Headless / Hermes mode** documented — set breakpoint policy `auto`; all learning writers are atomic file appends.
- **Skill routing clarified** — PM does selective per-agent injection once; agents do not each search; the static catalog is a hint, the live Skill-tool list is authority.

---

## What's new in 2.0.0

Research-aligned overhaul (Anthropic context-engineering / multi-agent posts, Cognition, Berkeley MAST, DSPy/GEPA, ICLR/Nature verification work):

- **Single skill.** Merged the standalone `karpathy-guidelines` skill into `mas-orchestrator` (still present as an internal reference + Worker injection). One install, one skill.
- **MAS Warrant Gate + Cost & Context Strategy** in SKILL.md — single-agent default, prompt-cache the stable prefix, `effort` over model-swap, distilled sub-agent summaries, Structured Outputs for machine handoffs.
- **Fresh-context Adversarial Critic** — reviews output without the Worker's reasoning trace (catches more defects); reflexion must cite an external signal (ungrounded self-correction degrades accuracy).
- **Watchdog debate, corrected** — heterogenize the pool, debate only disputed/high-impact claims, discount correlated consensus.
- **Layered Verifier** — deterministic rules → tools → LLM-judge (last), with position/length/self-preference bias controls.
- **Source reliability is now real code** — Beta-Binomial `source-reliability` promoted from `_legacy/` into `state_manager.py` + CLI + tests.
- **Honest docs** — dead `recommend_model_for_task` reference removed (routing is static); deferred learning loops (B1/B3/B4) marked 🚧 instead of claimed as active.
- **`eval/` harness** — proves whether the MAS beats a single agent by enough to justify its tokens.

---

## Installation

This plugin is distributed as a Claude Code marketplace. Both local and GitHub installation paths use the same commands.

### GitHub install

```
/plugin marketplace add imchul-oss/mas
/plugin install mas-orchestrator@ImFe
```

### Update / Uninstall

```
/plugin marketplace update ImFe
/plugin uninstall mas-orchestrator@ImFe
```

---

## Output Language Policy

- **Internal processing**: English (all definition and reference files).
- **User-facing output**: Korean by default. Switch to other languages only when the user explicitly instructs otherwise.
- **Breakpoint / gate messages**: Korean.

---

## 8-Agent Architecture

| # | Agent | Role | KPI |
|---|---|---|---|
| 1 | **Prompt Architect** | User request → structured prompt + mandatory `<thinking>` block | Clarity, Completeness, Actionability |
| 2 | **PM / Orchestrator** | Process design, Worker Pool, pool activation, federation routing | Process Completeness, Resource Optimization |
| 3 | **Researcher** | Information collection with tiered source reliability | Source Credibility, Coverage |
| 4 | **Watchdog Pool** (x3 for Complex/Expert) | Fact verification via multi-agent debate | Verdict Accuracy |
| 5 | **Worker (Pool)** | Task execution with handoff, structured output, token budget | Output Quality, Schema Compliance |
| 6 | **Adversarial Critic** | Proactive vulnerability discovery (counter-scenarios, edge cases) | Vulnerability Discovery Rate |
| 7 | **Polisher** | Linguistic polish (Korean style, terminology, readability — fact-preserving) | Linguistic Quality |
| 8 | **Verifier** | 10-dimension rubric QA, adversarial integration, schema validation | Defect Detection, Improvement Effectiveness |

---

## 10-Dimension Verifier Rubric

1. Accuracy
2. Completeness
3. Consistency
4. Efficiency
5. Traceability
6. Robustness (adversarial verdict integration)
7. External Compliance (MCP / Memory / Skills schemas)
8. Linguistic Quality (Polisher metrics)
9. Context Architecture Compliance (XML tag convention)
10. Senior Engineer Test (code simplicity, AST-based)

---

## Core Capabilities

**Gating & accountability**
- MAS Warrant Gate (single-agent default; full pipeline only when warranted) + Cost & Context Strategy (prompt caching, `effort`, distilled summaries, Structured Outputs)
- `eval/` harness — proves the MAS beats a single agent by enough to justify its tokens

**Verification & quality**
- Watchdog pool: heterogenized, debate-only-when-disputed, correlated-consensus discount
- Layered Verifier (deterministic rules → tools → LLM-judge last) + step-level generative verification (ThinkPRM) + LLM-judge bias controls
- Fresh-context Adversarial Critic with external-signal-grounded reflexion
- Bayesian convergence (semantic agreement + external signal, not verbalized confidence)

**Observability & reliability**
- OTel-GenAI telemetry spans (parent_span_id tree, token attribution, derived cost) — replayable into Langfuse/Phoenix
- Typed handoff contracts (objective/format/boundaries/tools); concurrency safety (file lock + atomic write + CAS)
- LangGraph-style checkpointing + time travel

**Learning (eval-gated)**
- Dynamic source-tier reliability (Beta-Binomial, implemented)
- Typed memory (episodic/semantic/procedural) + timestamp + supersession; ACE delta-merge
- GEPA Pareto-front reflective prompt optimizer (offline, eval-driven) + SkillOpt 4-loop
- Gate-learning / token-budget / dynamic cost-routing 🚧 deferred until eval-validated — see `references/evolution-policy.md`

**Reach**
- Worker conflict resolution (4-stage), goal-driven worker mode, test-first task transformation
- Causal graph risk analysis, multi-modal watchdog (image / code), SLA/SLO, MCP registry
- Inter-agent harness (review/debate/peer-review/fact-check/refinement/standup)
- Multi-MAS federation (hub-spoke / hierarchical / peer / swarm)
- Context architecture with mandatory XML tags and `<thinking>` blocks

---

## Gates (Breakpoints)

`phase_2_plan_review`, `phase_3b_false_detected`, `watchdog_disagreement_arbitration`, `phase_3c_worker_start`, `worker_conflict_resolution`, `phase_4_verification_result`, `feedback_loop_iteration`, `async_task_timeout`, `memory_api_sync_failure`, `sla_breach`, `multimodal_vision_call`, `calibration_recalibration`, `review_round_continue`, `peer_review_hop_limit`, `interaction_token_budget_breach`, `specialist_worker_promotion`, `skill_creation_review`, `agent_evolution_review`, `skillopt_deploy_best`, `goal_driven_max_iter`.

---

## References (`skills/mas-orchestrator/references/`)

| File | Content |
|---|---|
| `architecture.md` | System design principles and 8-agent responsibility separation |
| `protocols.md` | Inter-agent communication channels |
| `state-schema.md` | JSON schema for all state files |
| `evolution-policy.md` | Skill vs. agent evolution policy |
| `skill-catalog.md` | Skill hint list (live Skill-tool list is authority) |
| `context-architecture.md` | XML tag convention constitution |
| `c-integration-notes.md` | Causal graph / multi-modal / SLA / registry / calibration / memory |
| `federation-architecture.md` | Federation 4-pattern ADR |
| `karpathy-guidelines.md` | Simplicity principles and MAS mapping |
| `skillopt-integration.md` | SkillOpt 4-loop integration protocol |

---

## Scripts (`skills/mas-orchestrator/scripts/`)

### Core state management
- `state_manager.py` — Unified state manager (atomic write, Bayesian convergence, pool aggregation, conflict detection)

### Feature implementations
- `c_implementations.py` — Causal DAG, multimodal watchdog, SLA, MCP registry, calibration, memory
- `agent_interaction.py` — Inter-agent harness protocols
- `multi_mas_federation.py` — Federation coordinator, instance, message broker, adapter
- `xml_parser.py` — Context architecture XML validator
- `run_xml_lint.py` — CI entry point
- `goal_driven_executor.py` — Goal-driven worker loop
- `test_first_transformer.py` — Imperative-to-verifiable task transformer
- `skillopt_adapter.py` — SkillOpt 4-loop adapter
- `reflexion_full_stack.py` — Full-stack self-reflection module
- `senior_engineer_metrics.py` — AST-based code simplicity metrics
- `gepa_optimizer.py` — GEPA-style Pareto-front reflective prompt optimizer (offline, eval-driven)

### Tests (150 passing: 143 scripts + 7 eval; XML lint `--strict` clean)
`test_state_manager.py`, `test_c_implementations.py`, `test_agent_interaction.py`, `test_multi_mas_federation.py`, `test_xml_parser.py`, `test_skillopt_adapter.py`, `test_gepa_optimizer.py`, `eval/test_scorer.py`

---

## Eval (`skills/mas-orchestrator/eval/`)

- `scorer.py` — given paired MAS / single-agent run records, reports whether the MAS earned its ~15x token cost per case and in aggregate.
- `cases.jsonl` — representative cases, tagged `warrant_mas` so the Warrant Gate itself is testable.
- `README.md` — how to run; `test_scorer.py` — unit tests.

---

## Legacy

Version-stamped historical files are archived under `_legacy/` and are not loaded by the runtime.

---

## License

MIT
