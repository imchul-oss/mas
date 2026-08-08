# Causal / Multi-modal / SLA / Registry / Calibration / Memory Integration Notes

How the six C-series implementations integrate into the 8-agent architecture.

---

## C1: Causal Graph -> PM Risk Register Analysis
<integration_note>

### Integration Point
`agents/pm-orchestrator.md` Step 5 Risk Analysis:
- Existing: FMEA-based RPN.
- New: register risk items as CausalDAG nodes -> separate correlation vs. causation -> compute backdoor_set to prioritize mitigations.

### Call Example
```python
from c_implementations import CausalDAG, analyze_risk_with_causal_graph

dag = CausalDAG()
dag.add_edge("R2", "convergence_failure")
dag.add_edge("R9", "race_condition")
dag.add_edge("convergence_failure", "TARGET_QUALITY")
analysis = analyze_risk_with_causal_graph(pm_plan["risk_register"], dag)
```
</integration_note>

---

## C2: Multi-modal Watchdog -> Watchdog Pool Extension
<integration_note>

### Integration Point
Add a modality dimension to the Watchdog Pool:
- Standard pool: `[W1=tier1_direct, W2=tier2_cross, W3=tier3_logical]` (all text).
- Extended pool: above + `W4=multimodal` (image / code verdicts).

### Pool Activation Policy
| Worker output contains image URL or code block | W4 activation |
|---|---|
| None | W4 skip |
| 1+ image | W4 active (`verify_image_url`) |
| 1+ code block | W4 active (`verify_code_block`) |

### Limitations
- Vision model calls (Claude Vision API) depend on an external service.
- This module verifies format, metadata, and domain reliability.
- Actual image content analysis requires Vision API opt-in (user gate).
</integration_note>

---

## C3: SLA / SLO -> All Phases
<integration_note>

### Integration Point
SKILL.md Phase 0 init + Phase 4 Verifier:

```python
# Phase 0
if pm_plan.sla:
    schedule_sla_monitor(pm_plan.sla)

# Phase 4 (Verifier)
sla_compliance = evaluate_sla_compliance(pm_plan, telemetry)
if sla_compliance.violations:
    trigger_sla_breach_gate(violations)
```

### New Gate
GATE: `sla_breach`
- decision_type: direction
- options: [`accept_breach`, `extend_budget`, `abort_session`, `rollback_to_checkpoint`]
- Activation: 1+ critical violations or `compliance_ratio` < 0.7.
</integration_note>

---

## C4: MCP Registry Primary -> PM Skill Discovery
<integration_note>

### Integration Point
`agents/pm-orchestrator.md` Step 2:

| Step | Current | Registry-Primary |
|---|---|---|
| 2.1 | local skills | local skills |
| 2.2 | `search_plugins` | MCP Registry (`search_plugins_priority`) |
| 2.3 | `search_mcp_registry` | `search_plugins` fallback (automatic) |
| 2.4 | Anthropic Agent Skills | Anthropic Agent Skills |
| 2.5 | alternatives | alternatives |

### Environment
```bash
export MCP_REGISTRY_ENDPOINT="https://registry.modelcontextprotocol.io"
export MCP_REGISTRY_AUTH_TOKEN="..."
```

### Limitation
Actual Registry API calls are delegated by the PM agent to the `search_plugins` MCP tool. This module only provides the abstraction.
</integration_note>

---

## C5: Benchmark Calibration -> Verifier
<integration_note>

### Integration Point
`agents/verifier.md` Step 5 Quality Assessment:
```python
swe_bench_estimate = calibrate_to_benchmark(overall_score, "swe_bench_verified")
osworld_estimate = calibrate_to_benchmark(overall_score, "osworld_verified")
verifier_report["external_calibration"] = {
    "swe_bench_estimated": swe_bench_estimate.estimated,
    "osworld_estimated": osworld_estimate.estimated,
    "method": "linear_interp",
    "calibration_disclaimer": "default mapping; update after 5+ measurements"
}
```

### Limitations
- Real benchmark scores require an external evaluation harness.
- These values are estimates only.
- Cross-domain extrapolation risk applies.
</integration_note>

---

## C6: Long-horizon Memory -> Researcher + Persistent State
<integration_note>

### Integration Point
Memory API integration inside `agents/researcher.md`:
```python
from c_implementations import HierarchicalMemory, compress_memory_acon_style

# Phase 0 entry
if meta.memory_api_enabled:
    raw_memories = anthropic_memory_api.fetch(domain="data_analysis")
    compressed = compress_memory_acon_style(raw_memories, target_size=50)
    mem = HierarchicalMemory(hot_size=10, warm_size=20)
    for m in compressed:
        mem.add(m["id"], m["content"], m["metadata"])
    relevant = mem.search(["customer", "churn"], top_k=5)
```

### Limitations
This implementation approximates the published concept with simple heuristics. Refine after primary-source verification.
</integration_note>

---

## Gate Additions
<protocol_definition>

| gate_id | Phase | Trigger |
|---|---|---|
| `sla_breach` | 4 | Critical SLA violation |
| `multimodal_vision_call` | 3b | Vision API opt-in |
| `calibration_recalibration` | 6 | 5 real observations accumulated; recommend mapping refresh |
</protocol_definition>

---

## New State Files
<state_schema>

```
./state/ additions:
  - causal_dag.json              # PM Risk Register analysis
  - multimodal_verdicts.json     # Image / code verdicts
  - sla_compliance.json          # SLA evaluation
  - mcp_registry_cache.json      # Registry search cache
  - calibration_estimates.json   # Verifier benchmark estimates

~/.claude/mas-state/ additions:
  - calibration.json             # Real observations (persistent)
```
</state_schema>

---

## Risk Register
<integration_note>

| ID | Risk | P | I | RPN | Mitigation |
|---|---|---|---|---|---|
| C-R1 | Causal graph misidentifies causation | 3 | 4 | 12 | State that this is a simple heuristic; require PM user review |
| C-R2 | Multi-modal Vision API cost explosion | 4 | 3 | 12 | Opt-in gate + sample rate limit |
| C-R3 | SLA breach gate fatigue | 3 | 3 | 9 | Severity weighting + auto-extend option |
| C-R4 | MCP Registry endpoint change | 3 | 4 | 12 | Abstraction layer + fallback retained |
| C-R5 | Calibration mapping deviates from reality | 4 | 3 | 12 | Explicit disclaimer + refresh after 5 measurements |
| C-R6 | Memory implementation diverges from primary source | 4 | 2 | 8 | Refine after primary-source verification |
</integration_note>
