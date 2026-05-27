# Agent v1.2.0 Deltas (Worker + PM + Verifier)

본 문서는 v1.1.0 의 3 agent 정의에 v1.2.0 G1/G2/B1/B2 추가분을 명시. 적용 시 v1.1.0 파일 끝에 append 또는 해당 절 교체.

---

## A. agents/worker.md — v1.2.0 Delta

### Identity (확장)
<agent_identity>
- KPI 추가: **Goal Achievement Rate (G1, goal_driven mode)**, **Surgical Change Compliance (B1)**
</agent_identity>

### Multi-Instance Architecture (확장)
<multi_instance>
v1.2.0 추가:
- `pm_plan.worker_pool.workers[i].execution_mode = "prescriptive" | "goal_driven"`
- goal_driven 시 `success_criteria` + `max_self_iterations` 명시
- v1.2.0: `karpathy_guidelines_enabled` 옵트인 (코딩 task)
</multi_instance>

### Step 2.95 (신설, B1): Surgical Change Check
<surgical_change_check>
v1.1.0 Step 2.9 (Token Budget) 다음, Step 3 (Output Generation) 전:

```
Worker 가 변경 결과 (diff 또는 변경 영역) 를 자체 점검:

1. for line in diff:
   if not traces_to_request(line):
     mark untraced

2. untraced lines 가 발견되면:
   - 옵션 A: 제거 (요청 외 변경 자체 정정)
   - 옵션 B: 보고 ("이 변경이 요청과 직접 관련 없음. 사용자 확인 권고")

3. 변경 결과 worker_output.json.surgical_change_check 에 기록:
   {
     "checked": true,
     "untraced_lines": [...],
     "action": "removed | reported"
   }

근거: Karpathy "Surgical Changes" principle (forrestchang repo Tier 2).
```
</surgical_change_check>

### Step 4 (신설, G1): Goal-Driven Loop
<goal_driven_loop>
`execution_mode == "goal_driven"` 시 Step 1~3 대신:

```python
from goal_driven_executor import GoalDrivenExecutor

executor = GoalDrivenExecutor(
    success_criteria=pm_plan.worker_pool.workers[self.id].success_criteria,
    max_iterations=pm_plan.worker_pool.workers[self.id].max_self_iterations or 3,
    worker_runner=self.attempt_step,
    state_path=f"state/worker_loops/{self.id}.json"
)
result = executor.execute()
worker_output["goal_driven_result"] = result
```

`attempt_step(iteration, prior_attempts)`:
- iteration 1: 초기 시도
- iteration 2+: 이전 verifications.feedback 참고하여 self-reflect 후 재시도

근거:
- Karpathy "Goal-Driven Execution" principle (Tier 2)
- Reflexion (Shinn et al. 2023, NeurIPS) Self-Reflection 컴포넌트 (이미 v0.5.0 Adversarial Critic 매핑)
</goal_driven_loop>

### Output Format (확장)
<output_format>
worker_output.json 에 v1.2.0 추가 필드:
```json
{
  "execution_mode": "prescriptive | goal_driven",
  "goal_driven_result": null | {
    "status": "passed | failed | max_iter",
    "iterations": int,
    "attempts": [...],
    "unmet_criteria": [...]
  },
  "surgical_change_check": null | {
    "checked": bool,
    "untraced_lines": [],
    "action": "removed | reported | none"
  },
  "karpathy_guidelines_applied": bool
}
```
</output_format>

### Non-Negotiable Rules (확장)
<non_negotiable_rules>
v1.1.0 5개 + v1.2.0 추가:
6. **execution_mode = "goal_driven" 시 max_self_iterations 초과 금지** (R2 cold-start mitigation 와 동일 정신)
7. **Surgical Change Check 통과 또는 보고 의무** (B1)
8. **Karpathy 인용 시 forrestchang Tier 2 출처 명시** (환각 방지)
</non_negotiable_rules>

---

## B. agents/pm-orchestrator.md — v1.2.0 Delta

### Step 3.7 (신설, G2): Test-First Task Transformation
<test_first_transformation>
Step 3 (Worker Pool Design) 다음, Step 4 (Process Map) 전:

```python
from test_first_transformer import transform_pm_plan_tasks

# task_decomposition 의 각 task 를 verifiable goal 로 변환
pm_plan = transform_pm_plan_tasks(pm_plan)

# 변환 신뢰도 ≥ 0.7 인 task 는 worker.execution_mode = "goal_driven" 으로 자동 설정
for task_with_trans in pm_plan["task_decomposition_with_transformations"]:
    trans = task_with_trans.get("transformation")
    if trans and trans["transformation_confidence"] >= 0.7:
        # 해당 task 를 처리하는 Worker 를 goal_driven 으로
        worker_id = task_with_trans["assigned_worker_id"]
        for worker in pm_plan["worker_pool"]["workers"]:
            if worker["worker_id"] == worker_id:
                worker["execution_mode"] = "goal_driven"
                worker["success_criteria"] = trans["success_criteria"]
                worker["max_self_iterations"] = 3
                break
```

활성화 조건:
- complexity ∈ {Moderate, Complex}
- task_type ∈ {add_feature, fix_bug, refactor, verify, analyze, documentation}
- 변환 confidence ≥ 0.7

근거: Karpathy Examples (Tier 2 forrestchang repo) — "Add validation" → "Write tests..."
</test_first_transformation>

### Step 3.8 (신설, G3): Karpathy Guidelines Skill Activation
<karpathy_guidelines_activation>
코딩 task (task_type 에 "code", "refactor", "debug", "test" 포함) 시:
```python
for worker in pm_plan["worker_pool"]["workers"]:
    if any(kw in worker["role"].lower()
           for kw in ["code", "refactor", "debug", "test", "implement"]):
        worker["karpathy_guidelines_enabled"] = True
        # PM 이 Worker spawn 시 prompt 의 system_context 에
        # karpathy-guidelines/SKILL.md 의 4 principles 를 inject
```

비활성화: 자연어 보고서·분석·문서 작성 task.
</karpathy_guidelines_activation>

---

## C. agents/verifier.md — v1.2.0 Delta

### 10-Dimension Rubric (B2)
<verification_framework>
v1.1.0 9 dimension + 1 신설:

| 차원 | 검증 대상 | v |
|---|---|---|
| 1-9 (v1.1.0 유지) | accuracy/completeness/consistency/efficiency/traceability/robustness/external_compliance/linguistic_quality/context_architecture_compliance | v1.1.0 |
| **10. senior_engineer_test (신설, B2)** | Karpathy "200→50" test — overcomplicated 여부 | v1.2.0 |

### Step 4.5 (신설, B2): Senior Engineer Test
<senior_engineer_test>
Worker 산출물에 코드 또는 구조화된 design 포함 시:

```python
def senior_engineer_test(output):
    checks = {
        "is_minimum_viable": detect_speculative_features(output) is None,
        "has_speculative_features": bool(detect_speculative_features(output)),
        "has_premature_abstractions": detect_unused_abstractions(output) > 0,
        "lines_could_be_reduced": estimate_simplification_potential(output),
        "dead_code_present": detect_dead_code(output) > 0
    }

    # 점수 매핑 (Karpathy "200 lines could be 50 → rewrite" 기준)
    reduction = checks["lines_could_be_reduced"]
    if reduction == 0 and not checks["has_speculative_features"]:
        score = 5  # minimum viable
    elif reduction <= 0.10:
        score = 4  # minor
    elif reduction <= 0.30:
        score = 3  # moderate
    elif reduction <= 0.50:
        score = 2  # significant
    else:
        score = 1  # severe overcomplication

    return {
        "score": score,
        "criteria": "Karpathy '200→50' test",
        "checks": checks,
        "estimated_simplification_potential": f"{reduction*100:.0f}%"
    }
```

자연어만 산출물인 경우 N/A 처리 (점수 5 default).

근거: Karpathy "Simplicity First" principle (Tier 2 forrestchang repo).
</senior_engineer_test>

### Step 5 (확장): 10-Dim Quality Assessment
<verification_framework>
```json
{
  "quality_rubric": {
    /* v1.1.0 9 dimension 유지 */
    "senior_engineer_test": {
      "score": 1-5,
      "criteria": "...",
      "checks": {...},
      "estimated_simplification_potential": "..."
    }
  },
  "overall_score": float,  // 10 dimension 평균
  "verdict": "PASS|CONDITIONAL_PASS|FAIL"
}
```

PASS threshold 유지 (≥ 4.0).
</verification_framework>

---

## D. SKILL.md — v1.2.0 Delta

### Sub-Agent Optimization (확장)
<sub_agent_optimization>
v1.2.0 추가 행:

| Phase | Agent | model | Rationale |
|---|---|---|---|
| 3c (goal_driven) | Worker (loop) | sonnet | Loop 반복은 속도 우선 |
</sub_agent_optimization>

### Activation Policy (Proportional Response, v1.2.0 갱신)
<execution_protocol>

| Complexity | G1 Goal-Driven | G2 Test-First | B1 Surgical | B2 Senior Eng | G3 karpathy-skill |
|---|---|---|---|---|---|
| Simple | optional | ❌ | ❌ | optional | optional |
| Moderate | **default for testable** | ✅ default | ✅ default | ✅ default | optional |
| Complex | optional | ✅ | ✅ | ✅ | ✅ for code task |
| Expert | optional (prescriptive 권장) | ✅ | ✅ | ✅ | ✅ for code task |

**Karpathy Trade-off note 정합**: trivial 에는 full rigor 미적용.
</execution_protocol>

### Gate Definitions (확장)
<gate_definitions>

v1.2.0 신규 게이트 1종:

| gate_id | Phase | Trigger |
|---|---|---|
| **goal_driven_max_iter (v1.2.0)** | 3c | Worker goal_driven loop max_iter 도달 unmet criteria | direction: {accept_partial, switch_to_prescriptive, abort} |
</gate_definitions>
