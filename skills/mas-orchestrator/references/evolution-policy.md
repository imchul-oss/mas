# Evolution Policy

## Skill vs. Agent Path Decision Matrix
<evolution_policy_section>

| Change Area | Path |
|---|---|
| Add domain knowledge | Skill Factory |
| Support new task type | Skill Factory |
| Integrate new tool | Skill Factory |
| Modify agent behavior pattern | Agent Evolution |
| Adjust agent decision criteria | Agent Evolution |
| Change inter-agent interaction | Agent Evolution |

### Boundary Rules
- Domain knowledge -> Skill.
- Behavior pattern -> Agent.
- Both -> Skill first, Agent later.
- Ambiguous -> Skill (lower risk).
</evolution_policy_section>

## MAS Self-Audit Protocol
<evolution_policy_section>

### Triggers
- User: "self-audit", "system audit", "agent diagnosis".
- Auto: 3 consecutive verifier_score < 3.5, same agent retried 3 times, abort rate > 30%.

### Procedure
1. Prompt Architect redefines as "Full audit of MAS agent definitions and protocols".
2. PM decomposes audit items: (a) protocol consistency, (b) state schema alignment, (c) gate completeness, (d) role boundaries, (e) missing error handling.
3. Researcher collects external best practices.
4. Watchdog checks source credibility and identifies gaps.
5. Worker (audit) analyzes per item and labels critical / major / minor / suggestion.
6. Verifier validates the audit result and issues a final report.

### Result Routing
- CRITICAL -> Agent Evolution or Skill Factory per the matrix.
- MAJOR -> Skill Factory (domain) or Agent Evolution (behavior).
- MINOR -> Agent Evolution.
- SUGGESTION -> Backlog.
</evolution_policy_section>

## External Source Usage Policy
<evolution_policy_section>

### Tier Priority
- Tier 1: official documentation from major model providers, top-conference papers, peer-reviewed work.
- Tier 2: official repos, major tech blogs, vendor documentation.
- Tier 3: community forums, personal tech blogs (cross-validation required).
- Tier 4: social media (trend signal only), video content (verify against primary source).

### Recency Windows
- Agent architecture: 2 months (Tier 1-2).
- Prompt engineering: 3 months (Tier 1).
- Core principles: 6 months.
</evolution_policy_section>

## Per-Agent Evolution Sources
<evolution_policy_section>

### Prompt Architect
- Official prompt-engineering guides from major model providers.
- XML tag best practices.
- Prompt template frameworks.

### Researcher
- Tool-use guides.
- RAG literature.
- Academic search techniques and fact-checking principles.

### Watchdog
- Fact-checking standards.
- Academic verification methodology (peer review, replication).
- Logical fallacy taxonomy.

### Worker
- Domain-specific industry standards.
- Claude Skill docs (docx / pptx / xlsx / pdf).
- Domain expert communities.

### PM / Orchestrator
- Multi-agent system design patterns.
- Project management methodologies.
- Resource optimization algorithms.

### Verifier
- Quality management standards.
- LLM evaluation frameworks.
- Rubric-based evaluation.

### Adversarial Critic
- Self-criticism + correction loops.
- Verbal reinforcement and reflection.
- Adversarial probing methodology.
- Multi-perspective debate.

### Polisher
- Korean orthography and style guides.
- English style references (e.g., Chicago Manual of Style).
- Document consistency standards.
- Domain glossaries.
</evolution_policy_section>

## PM Integration Rules
<evolution_policy_section>

### Phase 6 (Skill / Agent Evolution)
- Detect improvement opportunity -> route by the matrix.
- Agent Evolution follows the external-source policy.

### Self-Audit Mode
- Trigger -> follow the audit procedure.
- Result -> route by the matrix.

### New External Source
- Request Watchdog verification using the tier priority.
- On verification pass, propose addition to the relevant agent's source list.
</evolution_policy_section>

## Bayesian Threshold Update
<evolution_policy_section>
- On session close, `update_convergence_bayes(complexity, converged_within_budget)`.
- Cold-start protection: sample_count < 10 -> hardcoded fallback.
- Prior: Beta(2, 2) weakly informative.
- Drift detection: last-10-session average deviates by +/-50% -> shorten review_interval from 5 to 3.
</evolution_policy_section>

## Concurrency Safety Invariants
<evolution_policy_section>
- I1: Atomic state write (`tempfile` + `os.replace`).
- I2: Exclusive file lock (POSIX `fcntl` / Windows `msvcrt`).
- I3: Optimistic concurrency (`version` CAS).
- I4: Worker Pool synchronization (Phase 4 starts only after all Worker writes complete).
</evolution_policy_section>

## Evolution Gates (Skill vs. Agent)
<evolution_policy_section>

| Change Area | Path |
|---|---|
| Pool size adjustment | Agent Evolution (`watchdog.md`) |
| Bayesian prior adjustment | Agent Evolution (state_manager policy) |
| Adversarial threshold | Agent Evolution (`adversarial-critic.md`) |
| File lock strategy | Skill Factory (infrastructure) |
</evolution_policy_section>

## Self-Audit Auto Triggers
<evolution_policy_section>
- Watchdog Pool split rate > 30% (3 consecutive sessions).
- Adversarial VULNERABLE > 50% (3 consecutive sessions).
- Worker Conflict Stage 4 > 2 / session (3-session average).
- Bayesian threshold deviates by +/-50% from baseline.
</evolution_policy_section>

## External Spec Lifecycle Policy
<evolution_policy_section>

### Spec Pinning
Explicit in `meta.external_spec_pinned_versions`.

### Spec Change Detection
On Phase 0 init, compare fetched spec version with the pinned one. Mismatch triggers `evolution_review`.

### Breaking Change Response
- Patch (compatible): auto-apply and update pin.
- Minor (compatible): PM review + user gate.
- Major (breaking): GATE: `external_spec_breaking_change` -> rollback / migrate / wait.

### Stability Window
Adopt a new spec only after a 6-month stability window. Beta specs require a fallback path.
</evolution_policy_section>

## Self-Rolled Improvements
<evolution_policy_section>

**Status legend:** ✅ implemented in `scripts/` · 🚧 deferred (specified here, not yet in active code — gated behind the `eval/` harness so any learning loop can be proven to help before it ships). History-based "learning" optimizers are explicitly deferred: without an eval set they cannot be validated and may degrade behavior.

### B1: Gate Decision Learning 🚧 deferred
- During Phase 6 learning review, gate decision history updates `default_recommendation`.
- sample >= 20 + confidence >= 0.7 -> auto-update with user gate confirmation.

### B2: Dynamic Tier Reliability ✅ implemented
- On session close, `state_manager.update_source_reliability(source, watchdog_verdict)` (CLI: `source-reliability --action update`).
- Beta-Binomial conjugate update; `get_source_confidence_prior(source)` for read.
- Keep static tier until sample >= 10 (cold-start guard).

### B3: Token Budget Enforcement 🚧 deferred
- PM assigns per-Worker `token_budget`.
- Worker self-measures and enforces (compression mode).
- Verifier validates (`efficiency.token_compliance`).

### B4: Cost-aware Model Routing 🚧 deferred
- Routing is currently **static** (SKILL.md Sub-Agent Optimization table).
- Dynamic telemetry-based routing (`cost_routing_history` -> per-task model choice) is deferred until the `eval/` harness can show it beats the static table. No `recommend_model_for_task()` is called in the active pipeline.
</evolution_policy_section>

## Future Roadmap
<evolution_policy_section>

### Causal Graph
- DAG, d-separation, backdoor adjustment.
- Future: integrate causal inference libraries; full SCM.

### Multi-modal Watchdog
- `verify_image_url`, `verify_code_block` (Python AST).
- Future: vision API integration + code execution sandbox.

### SLA / SLO
- `evaluate_sla_compliance`, `sla_breach` gate.

### MCP Registry Primary
- `search_plugins_priority` abstraction.

### Benchmark Calibration
- `calibrate_to_benchmark` (linear interpolation).
- Future: isotonic regression after sample >= 30.

### Long-horizon Memory
- Compression + hierarchical memory (hot/warm/cold).
- ✅ Typed entries (episodic/semantic/procedural) + timestamp + supersession-by-key (`add_memory_entry`/`get_memory_entries`) — validity-based forgetting, the cheap fix for memory staleness without a graph DB. Aligns with Anthropic's GA file-based memory tool conventions.
- Future: refinement after primary-source verification.

### GEPA Reflective Prompt Optimization ✅ engine / 🚧 callbacks
- `scripts/gepa_optimizer.py`: Pareto-front evolution over (quality, cost) driven by `eval/scorer.py` as fitness — keeps trade-off candidates instead of greedy single-metric (GEPA, arXiv:2507.19457).
- Engine (Pareto maintenance, evolve loop) is implemented + tested; the `reflect_mutate` (LLM rewrites a prompt from eval traces) and `evaluate` (run the eval set) callbacks are caller-injected. Run **offline** against `eval/`; ship a mutated prompt only if it Pareto-dominates the baseline.
- This replaces dynamic in-loop "learning" optimizers (B1/B3/B4) as the eval-grounded way to improve prompts — it is the one optimizer with a measurable gate.

### ACE delta-merge (anti context-collapse)
- For any persistent doc that evolves across runs (checkpoints, memory, handoff logs, agent_evolution): **append small deltas, never wholesale-rewrite** (ACE, arXiv:2510.04618 — iterative full-rewrites erode accumulated knowledge / "context collapse"). Critic = Reflector, Polisher/Verifier = Curator of deltas.
</evolution_policy_section>

## Self-Audit Learning Persistence
<evolution_policy_section>
Hallucination incidents detected by self-audit are persisted into `agent_evolution.json`:
```json
{"agents": {"researcher": {
  "performance_baseline": {"common_issues": ["estimating quantitative figures from abstracts"]},
  "evolution_history": [{
    "version": "x.y.z",
    "evolution_type": "feedback_integration",
    "trigger": {"source": "self_audit"},
    "changes": [{
      "section": "Step 5.5 Source Quality Self-Check",
      "before": "abstract-only quantitative quotation permitted",
      "after": "quantitative figures outside an abstract require verification against the paper body or official docs"
    }]
  }]
}}}
```
Applied on every Researcher initialization to prevent recurrence.
</evolution_policy_section>

## Context Architecture Policy
<evolution_policy_section>

### XML Tag Evolution Gate
Every change to `agents/*.md` must preserve:
- The standard tag dictionary (`context-architecture.md`).
- Markdown headers (hybrid).
- `xml_parser` lint passing.

### Auto-trigger
- `xml_parser compliance_score` average < 0.85 -> `agent_evolution_review` gate.
- Frequent orphan tags -> persist self-correction learning for the offending agent.

### Migration Phases
- Phase 1: SKILL.md + Prompt Architect.
- Phase 2: PM, Watchdog, Verifier.
- Phase 3: Researcher, Worker, Adversarial Critic, Polisher.
- Phase 4: All `references/*.md`.

Each phase requires a self-audit verdict >= CONDITIONAL_PASS before proceeding.
</evolution_policy_section>
