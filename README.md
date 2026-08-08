# MAS Orchestrator Plugin

**v2.7.0** · Production-grade 8-agent Multi-Agent System (MAS) orchestrator for Claude Code / Claude Desktop. One skill, no dependencies, headless-safe (Hermes/cron).

This skill is **on-demand and self-gating**: even when triggered, a **Warrant Gate** (SKILL.md) drops to a single agent for tasks that don't justify the pipeline. As of 2.2.0 that gate is calibrated on measurement rather than on a cited figure — a Worker+Verifier pair costs **1.8x-2.2x** a single agent on this runtime, not the ~15x that describes a deep many-agent research run, because a sub-agent carries ~50,000 tokens of base context before doing any work. What that ~2x buys is **variance reduction, not capability**: across the measured cases the single agent found every planted trap, and the pipeline won only where a Verifier caught the first agent's own error. So the gate asks how expensive an occasional wrong answer is, not what type of task it is. Design is grounded in 2025-2026 research (Anthropic context-engineering / multi-agent, Berkeley MAST, GEPA, ThinkPRM, OTel-GenAI), and complexity is held accountable by the `eval/` harness rather than asserted.

---

## What's new in 2.3.0

**Correction to 2.2.0's headline first.** The "compact pipeline" measured there was a Worker+Verifier pair, a configuration this architecture never defined. Adding up the activation policies as specified — PM and Researcher unconditionally active, Worker and Verifier always running — the real floor was **Simple 4 agents / 200k (4.0x), Moderate 6 / 300k (6.0x), Complex and Expert 10 / 500k (10.0x)**. So the literature's ~15x was a fair description of *this* architecture at Complex, and there was no cheap tier: even Simple billed 4x before any work.

- **Design Principle 0 — an agent boundary must change what is SEEN, not what is ASKED.** A different instruction is a section in a prompt and is free; a different context window is 50,000 tokens. Sorting the eight roles by that test: **Verifier** (fresh context over the Worker's output), **Researcher** (external material), and a **parallel Worker Pool** (a different sub-task each) earn a boundary. **Prompt Architect, PM, Watchdog and Polisher** re-read material the previous agent already had. **Adversarial Critic** does take fresh context — but the same fresh context the Verifier already takes.
- **Guardrail 11 applied to incumbents.** The rule that new complexity must beat a single-agent baseline had never been applied backwards, so six roles held always-on or default-on status unmeasured. All six are now opt-in against a named trigger, the per-tier baseline is the pair, and each role's definition names the eval result that restores its default. New floors: Simple/Moderate/Complex **100k (2.0x)**, Expert **300k (6.0x)**.
- **Not a claim that those roles don't work** — it is the existing guardrail applied to what was already there, reversible one line at a time. The decisive test is still unrun: one Complex case executed twice, full 10-agent spec against the pair, ~600k for the single case. That is what separates "the pipeline raises the ceiling" from "it raises the floor".

## What's new in 2.2.0

Three changes, each from the 8-case measured run, all subtractive or retargeting rather than additive:

- **Warrant Gate re-derived.** Cost premise corrected to the measured 1.8x-2.2x for a verify pair, with the ~15x kept for the shape it actually describes. Decision axis moved from task type and stakes to cost-of-an-occasional-wrong-answer, because both old proxies mis-sorted the measured set — two audits warranted the pipeline and two syntheses did not, and all four were "high stakes" under the old signals. The warranted default is now a **pair**, not the full pipeline; escalating past it needs a named reason.
- **Token efficiency, rule 0: cut agents before payload.** At a ~50,000-token per-agent floor, removing one agent saves more than perfectly optimising the context of four. An 8-agent run costs ~400k in floor alone regardless of task size, which makes proportional response a cost control and not only a quality one.
- **Verifier gained a mandatory Worker-Output Re-Derivation step** — recompute derived numbers, check a remedy is scoped to the object the diagnosis named, look for recoverable information the Worker discarded, check the conclusion against the Worker's own reasoning, name claimed-but-absent items. These are the five error shapes that were actually caught in measurement, not a generic checklist.

Unchanged: the 8-agent architecture. Four `warrant_mas: true` cases remain unrun, and research fan-out is the one shape that could move the ceiling rather than the floor.

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

Two of the eight are the baseline; the rest are opt-in against a named trigger as of 2.3.0. "Boundary" is Design Principle 0: does spawning this agent change what is SEEN, or only what is ASKED.

| # | Agent | Role | Activation | Boundary |
|---|---|---|---|---|
| 5 | **Worker (Pool)** | Task execution with handoff, structured output, token budget | **baseline** | Pool only: a different sub-task each |
| 8 | **Verifier** | 10-dimension rubric QA + Worker-Output Re-Derivation, schema validation | **baseline** | Yes — fresh context over the Worker's output |
| 3 | **Researcher** | Information collection with tiered source reliability | on trigger: material not already in context | Yes — external material |
| 4 | **Watchdog** (Pool of 3 at Expert) | Fact verification via multi-agent debate | on trigger: contested factual base | No — claims already in context; 3 over one document are correlated votes |
| 6 | **Adversarial Critic** | Proactive vulnerability discovery (counter-scenarios, edge cases) | on trigger at Complex, on at Expert | Fresh, but the same fresh context the Verifier takes |
| 7 | **Polisher** | Linguistic polish (Korean style, terminology — fact-preserving) | on trigger: named audience + style contract | No — rewrites the Worker's prose |
| 2 | **PM / Orchestrator** | Process design, Worker Pool, pool activation, federation routing | always, **light mode default**; may not spawn to decide a spawn | Partial |
| 1 | **Prompt Architect** | User request → structured prompt + mandatory `<thinking>` block | on trigger at Expert only | No — same request, restructured for the same model |

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
