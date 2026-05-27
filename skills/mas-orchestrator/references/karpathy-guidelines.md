# Karpathy Guidelines for MAS

## 0. Position of This Document
<integration_note>
Augments the 8-agent architecture with Goal-Driven Execution and simplicity enforcement on top of the Context Architecture.
</integration_note>

---

## 1. Three Common LLM Pitfalls
<knowledge_base>

### Pitfall 1: Wrong Assumptions + No Pushback
Models make wrong assumptions on the user's behalf and run with them without checking. They do not manage confusion, seek clarification, surface inconsistencies, present trade-offs, or push back when they should.

### Pitfall 2: Overcomplication
Models tend to overcomplicate code and APIs, bloat abstractions, leave dead code around, and build 1000-line scaffolds where 100 lines would do.

### Pitfall 3: Side-effect Changes
Models sometimes change or remove comments and code they do not fully understand as side effects, even when those are orthogonal to the task.
</knowledge_base>

---

## 2. Four Principles Mapped to MAS
<integration_note>

| Principle | MAS Mapping | Enforcement |
|---|---|---|
| **1. Think Before Coding** | Mandatory `<thinking>` + Watchdog Pool + Adversarial Critic | retained |
| **2. Simplicity First** | Token Budget + Polisher + Proportional Response | Senior Engineer Test dimension |
| **3. Surgical Changes** | Worker schema + Polisher fact preservation | Touch-Only-Requested check |
| **4. Goal-Driven Execution** | Verifier rubric + Bayesian convergence | Goal-Driven Worker Mode + Test-First Transformation |
</integration_note>

---

## 3. Goal-Driven Execution Mode
<execution_protocol>

### Core Insight
LLMs excel at looping until they meet specific goals. Provide success criteria, not step-by-step instructions, and let the model iterate.

### Mode Definitions

| Mode | Description | Default |
|---|---|---|
| `prescriptive` | PM specifies role / persona / assigned_tasks / steps | default |
| `goal_driven` | PM specifies success_criteria only; Worker loops | optional |

### Activation Conditions

PM sets `pm_plan.worker_pool.workers[i].execution_mode = "goal_driven"` when:
- The task is verifiable (testable, measurable output).
- Complexity is Moderate or Complex (Simple is one-shot; Expert prefers prescriptive).

### Goal-Driven Worker Loop
```
1. Worker reads success_criteria.
2. <thinking>: plan how to loop.
3. Loop:
   a. Current attempt.
   b. Self-Verifier mini-check (criteria met?).
   c. If met -> break.
   d. If not -> self-reflect on what is missing.
   e. Next iteration (max 3).
4. After exit, write worker_output.json.
```

### Schema Extension
```json
{
  "worker_pool": {
    "workers": [{
      "execution_mode": "prescriptive | goal_driven",
      "success_criteria": [{
        "criterion_id": "SC001",
        "description": "validation tests for invalid inputs all pass",
        "verification_method": "automated_test | manual_check | metric_threshold",
        "verification_command": "pytest tests/test_validation.py"
      }],
      "max_self_iterations": 3
    }]
  }
}
```
</execution_protocol>

---

## 4. Test-First Task Transformation
<execution_protocol>

### Conversion Examples

| Imperative | Goal-Driven Conversion |
|---|---|
| "Add validation" | "Write tests for invalid inputs, then make them pass" |
| "Fix the bug" | "Write a test that reproduces it, then make it pass" |
| "Refactor X" | "Ensure tests pass before and after" |

### PM Step 3.7
```
During PM Phase 2:
  for each task in task_decomposition:
    if task.type in {"add_feature", "fix_bug", "refactor"}:
      transform to goal_driven:
        original: "Add X"
        goal: "Tests for X behavior pass"
        plan: ["1. Write failing test", "2. Implement", "3. Verify"]
      mark worker.execution_mode = "goal_driven"
```

### Auto-conversion Matrix
| Keyword | Conversion |
|---|---|
| "add", "implement", "create" | "Write a test for the new behavior, then make it pass" |
| "fix", "debug", "resolve" | "Write a test that reproduces the issue, then make it pass" |
| "refactor", "improve", "optimize" | "Ensure existing tests pass before and after; add tests if missing" |
| "verify", "validate", "check" | "Define verification criteria + write the check, then ensure satisfied" |
</execution_protocol>

---

## 5. Surgical Changes Enforcement
<execution_protocol>

### Rules
- Do not "improve" adjacent code, comments, or formatting.
- Do not refactor things that are not broken.
- Match the existing style.
- If you notice unrelated dead code, mention it; do not delete it.

### Worker Step 3.5
```python
def surgical_change_check(diff, task_request):
    """Are all changed lines directly traceable to the task?"""
    untraced = []
    for line in diff:
        if not traces_to(line, task_request):
            untraced.append(line)
    if untraced:
        return {"violation": True, "untraced_lines": untraced,
                "recommendation": "If unrelated to the task, remove this change"}
    return {"violation": False}
```

### Verifier Integration
The consistency dimension of the 9-dim rubric gains a sub-criterion:
- **surgical_change_compliance**: are all changed lines traced to the task?
</execution_protocol>

---

## 6. Senior Engineer Test (Verifier Dimension)
<execution_protocol>

### Test
"Would a senior engineer say this is overcomplicated? If yes, simplify."

### 10-Dim Rubric
9 dimensions plus:
```json
{
  "senior_engineer_test": {
    "score": "1-5",
    "criteria": "Would a senior engineer judge this overcomplicated?",
    "checks": {
      "is_minimum_viable": "bool",
      "has_speculative_features": "bool",
      "has_premature_abstractions": "bool",
      "lines_could_be_reduced": "float",
      "dead_code_present": "bool"
    },
    "estimated_simplification_potential": "0-50% reduction possible"
  }
}
```

### Score Mapping
- 5: minimum viable, no speculation, near-optimal length.
- 4: minor simplification potential (<= 10%).
- 3: moderate simplification (10 to 30%).
- 2: significant simplification (30 to 50%).
- 1: severe overcomplication (>= 50% reduction possible).

### Activation
- Triggered when Worker output includes code or structured design.
- N/A for natural-language-only outputs.
</execution_protocol>

---

## 7. Activation Policy
<agent_activation_policy>

| Complexity | Goal-Driven | Test-First Transform | Surgical Check | Senior Eng Test |
|---|---|---|---|---|
| Simple | optional | off | off | optional |
| Moderate | default for testable tasks | on (default) | on (default) | on (default) |
| Complex | optional | on | on | on |
| Expert | optional (prescriptive preferred) | on | on | on |

Trivial tasks do not apply full rigor.
</agent_activation_policy>

---

## 8. Lightweight Onramp
<integration_note>

### Single-file Lightweight Philosophy
A single lightweight `SKILL.md` captures the principles.

### MAS Integration
`skills/karpathy-guidelines/SKILL.md`:
- Single lightweight file (<= 200 lines).
- Compressed 4-principle guide.
- Orthogonal to the 8 agents (opt-in).
- Bidirectional Anthropic Skills integration.

Activation:
- Direct user invocation.
- PM auto-recommendation after task analysis for coding tasks.
- Inject into Worker prompt (about 5KB).

### Token Cost
- About 5KB per call (200 lines).
- Lazy load policy: not loaded unless the task is coding.
</integration_note>

---

## 9. Migration Phases
<integration_note>

### Phase A (immediate): Core
- This document.
- `goal_driven_executor.py`.
- `test_first_transformer.py`.
- `karpathy-guidelines/SKILL.md`.

### Phase B (after 5 sessions): Agent Integration
- `worker.md` (Goal-Driven Mode).
- `pm-orchestrator.md` (Test-First Transformation).
- `verifier.md` (Senior Engineer Test).

### Phase C (after 10 sessions): Refinement
- Accumulate `process_policy` for which task types fit goal-driven.
- Feed senior_engineer_test score into cost-aware routing.
</integration_note>

---

## 10. Honest Limitations
<failure_modes>
- The Senior Engineer Test is qualitative; objectivity is limited.
- Goal-Driven Mode suits verifiable tasks; natural-language outputs stay prescriptive.
- Auto Test-First Transformation uses keyword heuristics, not deep NLP.
</failure_modes>
