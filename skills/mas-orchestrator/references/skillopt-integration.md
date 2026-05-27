# SkillOpt Integration Reference

**Doc Type**: Architecture Integration Note

---

## 0. Position of This Document
<integration_note>
Adapter integration that maps the SkillOpt 4-loop pattern (rollout -> reflect -> bounded edit -> validation gate) onto existing MAS assets. The full SkillOpt training infrastructure (cloud training environment, benchmark datasets, multiple epochs x batches) is not adopted - simplicity first.
</integration_note>

---

## 1. SkillOpt 4-loop Mapped to MAS Assets
<knowledge_base>

| SkillOpt Stage | MAS Adapter |
|---|---|
| **Rollout** | Worker execution + telemetry -> score |
| **Reflect** | Adversarial Critic counter_scenarios -> SkillEdit candidate |
| **Bounded Edit** | SkillEdit (add / delete / replace) + edit_budget = 4 |
| **Validation Gate** | Verifier 10-dim rubric overall_score (held-out improvement) |
| **Memory (rejected buffer)** | `process_policy` + `skillopt_state.json rejected_buffer` |
| **Memory (slow update)** | Patterned after `meta.json convergence_bayes` (optional use) |
| **best_skill.md export** | `<skill>.best_skill.md` output |
</knowledge_base>

---

## 2. Target Skills (Optimizable)
<protocol_definition>

| Skill Kind | Path | Priority |
|---|---|---|
| Karpathy Guidelines | `references/karpathy-guidelines.md` | high (lightweight, clear criteria) |
| Context Architecture | `references/context-architecture.md` | medium (`xml_parser` provides objective metric) |
| Registered skills | persistent `skill_registry.json` -> `created_skills[]` | medium |
| User-specified `.md` | `--skill_path` argument | user-decided |

**Not in scope**:
- `agents/*.md` (agent definitions evolve via `agent_evolution.json`).
- `SKILL.md` (orchestrator file).
- Quantitative schema definitions (e.g., `state-schema.md`).
</protocol_definition>

---

## 3. Activation Policy
<agent_activation_policy>

| Condition | Activation |
|---|---|
| Explicit user invocation | on |
| PM recommendation during Phase 6 learning review (after 5 sessions) | optional |
| Complexity in {Complex, Expert} + same skill used 3+ times | optional |
| Simple / Moderate | off (avoid overbuild) |

**Prerequisites**:
- The target skill has a validation-capable task set.
- Adversarial Critic or Verifier callback works.
</agent_activation_policy>

---

## 4. Integration Protocol
<execution_protocol>

### Step 1: Prepare target skill + validation set

```python
from skillopt_adapter import SkillOptAdapter, integrate_with_mas_verifier

adapter = SkillOptAdapter(
    skill_path="references/karpathy-guidelines.md",
    edit_budget=4,
    max_epochs=4,
    persistent_dir="~/.claude/mas-state/skillopt"
)
```

### Step 2: Register MAS callbacks

```python
def mas_rollout(skill_text, batch):
    # Inject skill_text into Worker prompt; run batch tasks.
    # Results combine telemetry + Verifier score.
    return [{"task_id": t["id"],
             "score": run_mas_task(t, skill_text)["score"],
             "trajectory": "..."} for t in batch]

def mas_reflector(skill_text, successes, failures):
    # Adversarial Critic analysis -> SkillEdit.
    adv_report = run_adversarial_critic_on_failures(failures, skill_text)
    return integrate_with_adversarial_critic(adv_report_path)

def mas_validator(skill_text, val_batch):
    # Verifier 10-dim rubric call.
    verifier_report = run_verifier_with_skill(skill_text, val_batch)
    return integrate_with_mas_verifier(verifier_report)

adapter.rollout_fn = mas_rollout
adapter.reflector_fn = mas_reflector
adapter.validator_fn = mas_validator
```

### Step 3: Train

```python
result = adapter.train(train_batch, val_batch)
# -> best_skill.md output
# -> history + rejected_buffer persisted
```

### Step 4: Deploy best skill (optional)

```python
import shutil
if result["best_score"] > current_baseline:
    shutil.copy(result["best_skill_path"], "references/karpathy-guidelines.md")
    # Bump version in skill_registry.json
```
</execution_protocol>

---

## 5. New Gates
<protocol_definition>

| gate_id | Phase | Trigger | Options |
|---|---|---|---|
| `skillopt_deploy_best` | 6 | best_score > current_baseline | accept_replace / accept_as_alternative / reject |
| `skillopt_max_epochs` | training | max_epochs reached + best_score < threshold | continue_training / accept_current / abort |
</protocol_definition>

---

## 6. State Files
<state_schema>

### `skillopt_state.json` (persistent)
```json
{
  "version": 1,
  "last_updated": "ISO-8601",
  "skill_path": "",
  "edit_budget": 4,
  "max_epochs": 4,
  "best_score": 0.0,
  "history": [{
    "epoch": "int",
    "train_score": "float",
    "val_score_candidate": "float",
    "val_score_current": "float",
    "edits_proposed": "int",
    "edits_accepted_in_budget": "int",
    "edits_deferred": "int",
    "edit_accepted": "bool",
    "edit_rejected_reason": "null | string"
  }],
  "rejected_buffer": [{
    "edit_id": "string", "op_type": "add|delete|replace",
    "target_section": "string", "content_before": "string",
    "content_after": "string", "rationale": "string", "cost": "int",
    "rejected_at_epoch": "int", "rejected_reason": "string"
  }]
}
```

### `best_skill.md` (output)
Saved next to the original skill as `<name>.best_skill.md`.
</state_schema>

---

## 7. Risk Register
<integration_note>

| ID | Risk | P | I | RPN | Mitigation |
|---|---|---|---|---|---|
| S-R1 | Skill damage from over-editing during training | 3 | 4 | 12 | Enforce edit_budget = 4 + validation gate + rejected_buffer |
| S-R2 | Domain extrapolation risk for Korean business domain | 4 | 3 | 12 | Train only on Korean task batches + explicit disclaimer |
| S-R3 | Validator score is sycophantic | 3 | 4 | 12 | Watchdog Pool + Adversarial Critic restrain Verifier |
| S-R4 | Adapter result diverges from full SkillOpt | 3 | 2 | 6 | State the adapter limitation explicitly (no full training infra) |
| S-R5 | Regression after auto-deploying best skill | 2 | 4 | 8 | `skillopt_deploy_best` gate for user confirmation |
| S-R6 | This adapter itself contradicts "Simplicity First" | 3 | 3 | 9 | Activation matrix + explicit-invocation default |
</integration_note>

---

## 8. Success Metrics
<integration_note>

| KPI | Baseline | Target |
|---|---|---|
| Share of training runs with best_score > current_baseline | N/A | >= 60% |
| Average epochs to reach best | N/A | <= 3 |
| Rejected buffer reuse rate (referenced by reflector) | N/A | >= 30% |
| Cross-task transfer (qualitative) | N/A | Verified qualitatively |
| Tokens / training session | N/A | <= 5x single-task cost |
</integration_note>

---

## 9. Known Limitations
<failure_modes>

### Adapter Scope
- Score estimation during rollout depends on Verifier; Verifier accuracy caps the ceiling.
- Reflection quality is bounded by `reflector_fn` quality.
- No benchmark calibration is included.
</failure_modes>

---

## 10. Next Steps
<integration_note>
1. Run the SkillOpt adapter unit tests.
2. Run `python scripts/skillopt_adapter.py` self-test.
3. Stabilize for 5 sessions.
4. Track `best_score` trend over time.
</integration_note>
