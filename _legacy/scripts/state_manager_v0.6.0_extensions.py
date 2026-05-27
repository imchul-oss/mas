"""
MAS State Manager v0.6.0 Extensions — B1/B3/B4 + 윤문 + C 항목 scaffolding
==========================================================================

state_manager.py에 추가할 함수들. v0.6.0 Phase B 통합 빌드의 잔여 항목.

포함:
- B1: RLHF-style gate decision learning
- B2: Dynamic source reliability tracking (Researcher 보조)
- B3: Token budget tracking (Worker 보조)
- B4: Cost-aware model routing (PM 보조)
- 윤문: Polisher report aggregation
- C 항목 scaffolding (실제 구현은 v0.7.0)

기존 state_manager.py 끝에 append 또는 별도 import.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

# Assumes state_manager.py 본체가 동일 디렉토리에 있다
# from state_manager import (
#     read_state, write_state, get_persistent_dir, _file_lock, _atomic_write,
#     now_iso, _read_meta, _write_meta
# )


# ============================================================
# B1: RLHF-style Gate Decision Learning
# ============================================================

def update_gate_decision_pattern(gate_id, decision, session_id):
    """
    breakpoints.json의 사용자 결정을 누적 분석하여 PM 추천 갱신.

    근거: Christiano et al. 2017 RLHF, Ouyang et al. 2022.
    실제 RL 아닌 통계적 환류.
    """
    meta_path = Path("agent_evolution.json")
    # persistent로 가야 하는 항목 — 실제 구현 시 persistent_dir 사용
    evolution = {} if not meta_path.exists() else json.loads(meta_path.read_text(encoding="utf-8"))

    gate_history = evolution.setdefault("gate_decision_history", {})
    gate_data = gate_history.setdefault(gate_id, {"decisions": [], "counts": {}})

    gate_data["decisions"].append({
        "session_id": session_id,
        "decision": decision,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    # 마지막 20개만 유지
    gate_data["decisions"] = gate_data["decisions"][-20:]
    gate_data["counts"][decision] = gate_data["counts"].get(decision, 0) + 1

    # 표본 ≥ 10 시 default_recommendation 갱신
    total = sum(gate_data["counts"].values())
    if total >= 10:
        most_common = max(gate_data["counts"], key=gate_data["counts"].get)
        confidence = gate_data["counts"][most_common] / total
        if confidence >= 0.7:
            gate_data["default_recommendation"] = most_common
            gate_data["confidence"] = confidence

    return gate_data


def get_gate_default_recommendation(gate_id):
    """PM이 게이트 옵션 제시 시 default 추천 조회."""
    # 실제 구현 시 agent_evolution.json에서 read
    # 여기서는 schema 명시
    return None  # 또는 {"default": "approve", "confidence": 0.85, "based_on": 18}


# ============================================================
# B2: Dynamic Source Reliability (Researcher 보조)
# ============================================================

def update_source_reliability(source, watchdog_verdict, persistent_dir):
    """
    Watchdog verdict 결과를 source_reliability.json에 누적.

    Beta-Binomial conjugate update와 동일 구조.
    """
    rel_path = Path(persistent_dir) / "source_reliability.json"
    if rel_path.exists():
        with open(rel_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"version": 1, "sources": {}}

    src = data["sources"].setdefault(source, {
        "tier_static": None, "pass_count": 0, "fail_count": 0,
        "confidence_prior": None, "last_used": None, "tier_calibrated": None
    })

    if watchdog_verdict == "TRUE":
        src["pass_count"] += 1
    elif watchdog_verdict == "FALSE":
        src["fail_count"] += 1
    # UNVERIFIABLE은 미반영

    total = src["pass_count"] + src["fail_count"]
    if total >= 10:  # cold-start 방지
        src["confidence_prior"] = src["pass_count"] / total
    src["last_used"] = datetime.now(timezone.utc).isoformat()

    rel_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return src


def get_source_confidence_prior(source, persistent_dir):
    """Researcher가 출처 사용 전 historical confidence 조회."""
    rel_path = Path(persistent_dir) / "source_reliability.json"
    if not rel_path.exists():
        return None
    with open(rel_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("sources", {}).get(source, {}).get("confidence_prior")


# ============================================================
# B3: Token Budget Tracking (Worker 보조)
# ============================================================

class TokenBudgetTracker:
    """
    Worker별 token 예산 측정·강제. self.token_budget 기반 compression mode 제어.

    근거: Anthropic Context Engineering Guide (2025).
    """

    def __init__(self, worker_id, allocated_budget):
        self.worker_id = worker_id
        self.allocated = allocated_budget
        self.used = 0
        self.compression_mode = False
        self.events = []

    def track(self, tokens_used):
        self.used += tokens_used
        ratio = self.used / self.allocated if self.allocated > 0 else 0
        if ratio >= 0.8 and not self.compression_mode:
            self.compression_mode = True
            self.events.append({"event": "compression_enabled", "at_ratio": ratio,
                                "timestamp": datetime.now(timezone.utc).isoformat()})
        if ratio >= 1.0:
            self.events.append({"event": "budget_exceeded", "at_ratio": ratio,
                                "timestamp": datetime.now(timezone.utc).isoformat()})
        return {"used": self.used, "allocated": self.allocated, "ratio": ratio,
                "compression_mode": self.compression_mode}

    def report(self):
        return {
            "worker_id": self.worker_id,
            "allocated": self.allocated,
            "used": self.used,
            "ratio": self.used / self.allocated if self.allocated > 0 else 0,
            "compression_mode_enabled": self.compression_mode,
            "budget_exceeded": self.used > self.allocated,
            "events": self.events
        }


# ============================================================
# B4: Cost-aware Model Routing (PM 보조)
# ============================================================

def update_cost_routing_history(model, task_complexity, quality_score, duration_ms, persistent_dir):
    """
    telemetry → 모델별 평균 quality·cost 누적.
    PM이 model 선택 시 historical data 활용.
    """
    meta_path = Path(persistent_dir) / "meta.json"
    meta = {} if not meta_path.exists() else json.loads(meta_path.read_text(encoding="utf-8"))

    routing = meta.setdefault("cost_routing_history", {})
    by_model = routing.setdefault(model, {})
    by_complexity = by_model.setdefault(task_complexity, {
        "total_runs": 0, "avg_quality": 0, "avg_duration_ms": 0
    })

    n = by_complexity["total_runs"]
    by_complexity["avg_quality"] = (by_complexity["avg_quality"] * n + quality_score) / (n + 1)
    by_complexity["avg_duration_ms"] = (by_complexity["avg_duration_ms"] * n + duration_ms) / (n + 1)
    by_complexity["total_runs"] = n + 1

    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def recommend_model_for_task(task_complexity, quality_threshold=4.0, persistent_dir=None):
    """
    PM이 task에 적합한 모델 추천.

    Returns: {"recommended": "sonnet|opus", "rationale": "..."}
    """
    if persistent_dir is None:
        return {"recommended": "opus", "rationale": "no_routing_history (default conservative)"}

    meta_path = Path(persistent_dir) / "meta.json"
    if not meta_path.exists():
        return {"recommended": "opus", "rationale": "no_meta"}

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    routing = meta.get("cost_routing_history", {})

    # sonnet quality at this complexity
    sonnet = routing.get("sonnet", {}).get(task_complexity, {})
    sonnet_quality = sonnet.get("avg_quality", 0)
    sonnet_runs = sonnet.get("total_runs", 0)

    if sonnet_runs >= 5 and sonnet_quality >= quality_threshold:
        return {"recommended": "sonnet",
                "rationale": f"sonnet historical quality {sonnet_quality:.2f} >= {quality_threshold} ({sonnet_runs} runs)"}
    return {"recommended": "opus",
            "rationale": f"sonnet quality {sonnet_quality:.2f} insufficient (runs={sonnet_runs}) → opus"}


# ============================================================
# 윤문: Polisher Report Aggregation
# ============================================================

def aggregate_polisher_metrics(polisher_report):
    """Polisher 산출 통계를 Verifier linguistic_quality 차원에 입력."""
    metrics = polisher_report.get("metrics", {})
    score = 5
    if metrics.get("fact_preservation_score", 1.0) < 1.0:
        score -= 2  # critical
    if metrics.get("korean_policy_violations_fixed", 0) > 5:
        score -= 1
    if metrics.get("style_inconsistencies_fixed", 0) > 5:
        score -= 1
    if len(polisher_report.get("fact_preservation_violations", [])) > 0:
        score = 1  # critical failure
    return max(1, min(5, score))


# ============================================================
# C 항목 Scaffolding (v0.7.0 후보)
# ============================================================

def causal_graph_scaffolding_placeholder():
    """C1: Pearl 2009 인과 그래프. v0.7.0에서 구현."""
    raise NotImplementedError("C1 Causal Graph: v0.7.0 후보. Pearl 2009.")


def multimodal_watchdog_scaffolding_placeholder():
    """C2: Multi-modal Watchdog (이미지/코드). v0.7.0 후보."""
    raise NotImplementedError("C2 Multi-modal Watchdog: v0.7.0 후보.")


def sla_slo_check(pm_plan, telemetry):
    """C3: SLA/SLO scaffolding. 현 v0.6.0은 측정만, 강제는 v0.7.0."""
    sla = pm_plan.get("sla", {})
    if not sla:
        return {"status": "no_sla_defined", "v0.7.0_candidate": True}

    violations = []
    for phase_name, target_ms in sla.items():
        actual = telemetry.get("phase_metrics", {}).get(phase_name, {}).get("duration_ms", 0)
        if actual > target_ms:
            violations.append({"phase": phase_name, "target": target_ms, "actual": actual})
    return {"status": "checked", "violations": violations}


def mcp_registry_search_priority():
    """C4: MCP Registry 우선 검색. 현 v0.6.0은 보조, v0.7.0에서 primary."""
    return {"current": "search_plugins primary, mcp_registry secondary",
            "v0.7.0_target": "mcp_registry primary after AAIF GA"}


def swe_bench_calibration_scaffolding():
    """C5: SWE-bench / OSWorld calibration. v0.7.0 후보."""
    return {"status": "scaffolding", "v0.7.0_candidate": True,
            "calibration_targets": ["SWE-bench Verified", "OSWorld-Verified"]}


def long_horizon_memory_scaffolding():
    """C6: ACON, EverMemOS 등. v0.7.0 후보 (paper 본문 검증 후)."""
    return {"status": "scaffolding (Anthropic Memory API adapter는 v0.6.0 도입됨)",
            "v0.7.0_candidate": True,
            "prerequisites": ["arXiv 2512.13564 본문 검증", "arXiv 2602.22769 본문 검증",
                              "본 MAS 도메인 적합성 확인"]}
