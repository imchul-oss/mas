"""
MAS v1.4.0 A — SkillOpt Slow Update + Meta Skill

근거: Microsoft SkillOpt (Yang et al. 2026, arXiv:2605.23904) 의 ablation.
"without meta skill + slow update": SpreadsheetBench 77.5 → 55.0 (대폭 하락)
→ v1.3.0 adapter 에 미구현 → v1.4.0 추가.

본 모듈:
- SlowUpdate: epoch 마다 longitudinal 비교로 rare-but-valuable rule 보존
- MetaSkill: optimizer-side memory (모든 rejected/accepted edits 의 패턴)

v1.3.0 SkillOptAdapter 와 호환. import 하여 plug-in 가능.
"""

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# Slow Update (longitudinal 비교)
# ============================================================

class SlowUpdate:
    """
    SkillOpt slow update: 매 epoch 의 결과를 longitudinal 추적.

    핵심: 단일 epoch 에서 rejected 되었으나 여러 epoch 에 걸쳐 일관성 있게
          개선 신호를 주는 edit 패턴을 발굴 → 정식 채택.

    paper 매핑: "Epoch 3 slow update — Train rollout 80.0% / Selection gate 81.4%"
    """

    def __init__(self, lookback_epochs=3):
        self.lookback_epochs = lookback_epochs
        self.epoch_records = []

    def record_epoch(self, epoch, accepted_edits, rejected_edits, val_score):
        """매 epoch 마다 결과 기록."""
        self.epoch_records.append({
            "epoch": epoch,
            "val_score": val_score,
            "accepted_count": len(accepted_edits),
            "rejected_count": len(rejected_edits),
            "accepted_signatures": [self._sig(e) for e in accepted_edits],
            "rejected_signatures": [self._sig(e) for e in rejected_edits],
            "timestamp": now_iso()
        })

    def _sig(self, edit):
        """edit signature (target_section + op_type)."""
        return f"{edit.get('op_type','?')}::{edit.get('target_section','?')[:80]}"

    def detect_persistent_rejections(self, threshold=2):
        """
        여러 epoch 에 걸쳐 rejected 된 동일 패턴.
        threshold 이상 등장 시 "지속적 거부" → optimizer 가 향후 회피.
        """
        cnt = Counter()
        for rec in self.epoch_records[-self.lookback_epochs:]:
            for sig in rec["rejected_signatures"]:
                cnt[sig] += 1
        return [{"signature": s, "rejection_count": c}
                for s, c in cnt.items() if c >= threshold]

    def detect_slow_improvements(self):
        """
        Val score 가 epoch 간 작지만 consistent 증가 → slow improvement 신호.

        Returns: { "is_slow_improving": bool, "avg_delta": float, "trend": str }
        """
        if len(self.epoch_records) < 2:
            return {"is_slow_improving": False, "reason": "insufficient_data"}
        scores = [r["val_score"] for r in self.epoch_records]
        deltas = [scores[i] - scores[i-1] for i in range(1, len(scores))]
        avg = sum(deltas) / len(deltas)
        positive_count = sum(1 for d in deltas if d > 0)
        return {
            "is_slow_improving": avg > 0 and positive_count >= len(deltas) // 2,
            "avg_delta": round(avg, 4),
            "positive_epochs": positive_count,
            "total_epochs": len(deltas),
            "trend": "improving" if avg > 0.005 else "stable" if abs(avg) <= 0.005 else "declining"
        }

    def to_dict(self):
        return {
            "version": 1,
            "lookback_epochs": self.lookback_epochs,
            "epoch_records": self.epoch_records,
            "persistent_rejections": self.detect_persistent_rejections(),
            "slow_improvements": self.detect_slow_improvements()
        }


# ============================================================
# Meta Skill (optimizer-side memory)
# ============================================================

class MetaSkill:
    """
    SkillOpt meta skill: optimizer 자체의 메모리.

    Reflector(예: Adversarial Critic)가 edit candidate 를 제안할 때
    과거 어떤 edit 이 어떤 상황에서 성공/실패했는지 hint 로 사용.

    핵심 데이터:
    - edit_pattern → success_rate (다른 epoch·다른 skill 에서의 종합)
    - failure_pattern → typical_cause (왜 rejected 되었나)
    """

    def __init__(self):
        self.pattern_stats = defaultdict(lambda: {"accepted": 0, "rejected": 0})
        self.failure_causes = defaultdict(Counter)
        self.session_id = now_iso()

    def update(self, edit, outcome, rejection_reason=None):
        """
        outcome: "accepted" | "rejected"
        rejection_reason: rejected 시 사유 (validation_gate_failed, regression_caused 등)
        """
        sig = f"{edit.get('op_type','?')}::{(edit.get('target_section','') or '')[:80]}"
        self.pattern_stats[sig][outcome] += 1
        if outcome == "rejected" and rejection_reason:
            self.failure_causes[sig][rejection_reason] += 1

    def get_pattern_success_rate(self, edit):
        """Reflector 가 후보 평가 시 사용."""
        sig = f"{edit.get('op_type','?')}::{(edit.get('target_section','') or '')[:80]}"
        stats = self.pattern_stats.get(sig)
        if not stats:
            return None  # 전례 없음
        total = stats["accepted"] + stats["rejected"]
        if total == 0:
            return None
        return {
            "success_rate": stats["accepted"] / total,
            "n_samples": total,
            "typical_failures": dict(self.failure_causes.get(sig, Counter()).most_common(3))
        }

    def top_successful_patterns(self, top_k=10):
        """가장 성공률 높은 패턴 (n_samples ≥ 3)."""
        ranked = []
        for sig, stats in self.pattern_stats.items():
            total = stats["accepted"] + stats["rejected"]
            if total < 3:
                continue
            rate = stats["accepted"] / total
            ranked.append({"signature": sig, "success_rate": rate, "n_samples": total})
        ranked.sort(key=lambda x: x["success_rate"], reverse=True)
        return ranked[:top_k]

    def to_dict(self):
        return {
            "version": 1,
            "session_id": self.session_id,
            "pattern_stats": {sig: dict(s) for sig, s in self.pattern_stats.items()},
            "failure_causes": {sig: dict(c) for sig, c in self.failure_causes.items()},
            "top_successful": self.top_successful_patterns()
        }


# ============================================================
# Integration helper — v1.3.0 SkillOptAdapter 확장
# ============================================================

def extend_skillopt_adapter(adapter):
    """
    v1.3.0 SkillOptAdapter 에 slow_update + meta_skill 주입.

    Usage:
        from skillopt_adapter import SkillOptAdapter
        from skillopt_v1_4_extensions import extend_skillopt_adapter

        adapter = SkillOptAdapter(skill_path, max_epochs=4, edit_budget=4)
        extend_skillopt_adapter(adapter)  # v1.4.0 확장 주입
        result = adapter.train(train_batch, val_batch)
    """
    adapter.slow_update = SlowUpdate(lookback_epochs=3)
    adapter.meta_skill = MetaSkill()

    original_train = adapter.train

    def enhanced_train(train_batch, val_batch):
        # v1.3.0 train 호출 후 epoch 마다 hook 추가는 wrapper 로
        # 본 단순 구현: original 실행 → history 후처리
        result = original_train(train_batch, val_batch)
        # history → slow_update 누적
        for h in result.get("history", []):
            adapter.slow_update.record_epoch(
                epoch=h["epoch"],
                accepted_edits=[],  # 단순화: real impl 은 epoch별 edit list 필요
                rejected_edits=[],
                val_score=h.get("val_score_candidate", 0)
            )
        # meta_skill 통계도 rejected_buffer 에서 추출
        for rej in adapter.rejected_buffer:
            adapter.meta_skill.update(rej, "rejected",
                                       rejection_reason=rej.get("rejected_reason", "unknown"))
        # 결과 확장
        result["slow_update_analysis"] = adapter.slow_update.to_dict()
        result["meta_skill_state"] = adapter.meta_skill.to_dict()
        return result

    adapter.train = enhanced_train
    return adapter


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MAS v1.4.0 A — SkillOpt Slow Update + Meta Skill")
    print("=" * 60)

    # Slow Update test
    print("\n[Slow Update]")
    su = SlowUpdate(lookback_epochs=3)
    fake_edit_1 = {"op_type": "add", "target_section": "section_x"}
    fake_edit_2 = {"op_type": "replace", "target_section": "section_y"}
    su.record_epoch(1, [fake_edit_1], [fake_edit_2], val_score=0.75)
    su.record_epoch(2, [], [fake_edit_2], val_score=0.78)
    su.record_epoch(3, [fake_edit_1], [fake_edit_2], val_score=0.80)
    print(f"  persistent_rejections: {su.detect_persistent_rejections()}")
    print(f"  slow_improvements: {su.detect_slow_improvements()}")

    # Meta Skill test
    print("\n[Meta Skill]")
    ms = MetaSkill()
    for _ in range(5):
        ms.update(fake_edit_1, "accepted")
    for _ in range(2):
        ms.update(fake_edit_2, "rejected", "validation_gate_failed")
    ms.update(fake_edit_1, "rejected", "regression_caused")
    print(f"  fake_edit_1 success_rate: {ms.get_pattern_success_rate(fake_edit_1)}")
    print(f"  top_successful: {ms.top_successful_patterns(top_k=3)}")

    print("\n" + "=" * 60)
    print("Demo complete.")
