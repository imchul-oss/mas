"""
SkillOpt Adapter

4-loop pattern:
  Rollout -> Reflect -> Bounded Edit -> Validation Gate -> Memory

MAS mapping (adapter pattern, avoids full training infra):
  Rollout         -> MAS task execution + telemetry collection
  Reflect         -> Adversarial Critic reuse
  Bounded Edit    -> this module (add/delete/replace, edit_budget=4 default)
  Validation Gate -> MAS Verifier 10-dim rubric (held-out improvement)
  Memory          -> process_policy.json + rejected_edits field

Supported skill targets:
- references/karpathy-guidelines.md
- references/context-architecture.md
- all registered skills in skill_registry.json
- user-specified .md files
"""

import json
import os
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# Edit Operations (Bounded Edit primitive)
# ============================================================

EDIT_TYPES = {"add", "delete", "replace"}


class SkillEdit:
    """
    A single bounded edit operation.

    Isomorphic to add/delete/replace operations.
    'cost' is the unit of textual learning rate.
    """

    def __init__(self, op_type, target_section, content_before=None,
                 content_after=None, rationale=""):
        if op_type not in EDIT_TYPES:
            raise ValueError(f"Invalid op_type: {op_type}")
        self.op_type = op_type
        self.target_section = target_section  # e.g. "## Identity" or XML tag
        self.content_before = content_before
        self.content_after = content_after
        self.rationale = rationale
        self.created_at = now_iso()
        self.edit_id = self._hash()

    def _hash(self):
        h = hashlib.sha256()
        h.update(f"{self.op_type}:{self.target_section}:{self.content_after}".encode("utf-8"))
        return h.hexdigest()[:12]

    def cost(self):
        """Unit for edit_budget deduction."""
        if self.op_type == "delete":
            return 1
        if self.op_type == "add":
            return 1 + (len((self.content_after or "")) // 500)  # +1 per 500 chars
        if self.op_type == "replace":
            return 2  # most risky
        return 1

    def apply_to(self, skill_text):
        """Apply SkillEdit to text."""
        if self.op_type == "delete":
            if self.target_section in skill_text:
                return skill_text.replace(self.target_section, "")
            return skill_text
        if self.op_type == "add":
            # Append to the end (simple implementation)
            return skill_text + "\n\n" + (self.content_after or "")
        if self.op_type == "replace":
            if self.content_before and self.content_before in skill_text:
                return skill_text.replace(self.content_before,
                                           self.content_after or "", 1)
            return skill_text
        return skill_text

    def to_dict(self):
        return {
            "edit_id": self.edit_id,
            "op_type": self.op_type,
            "target_section": self.target_section[:200],
            "content_before": (self.content_before or "")[:200],
            "content_after": (self.content_after or "")[:200],
            "rationale": self.rationale,
            "cost": self.cost(),
            "created_at": self.created_at
        }


# ============================================================
# SkillOpt Adapter - 4-loop pattern
# ============================================================

class SkillOptAdapter:
    """
    Adapter that maps MAS assets to the SkillOpt 4-loop.

    Args:
        skill_path: target .md file to optimize (e.g. karpathy-guidelines.md)
        rollout_fn: callable(skill_text, batch) -> [{"task_id", "score", "trajectory"}]
                    Wraps MAS Worker execution result. Provided by caller.
        reflector_fn: callable(skill_text, success_batch, failure_batch) -> [SkillEdit, ...]
                      Can reuse Adversarial Critic. Provided by caller.
        validator_fn: callable(skill_text, validation_set) -> {"score": float, "details": ...}
                      Wraps Verifier rubric call. Provided by caller.
        edit_budget: textual learning rate (default 4)
        max_epochs: training epochs (default 4)
        persistent_dir: optional storage for rejected_edits and history
    """

    def __init__(self, skill_path, rollout_fn=None, reflector_fn=None,
                 validator_fn=None, edit_budget=4, max_epochs=4,
                 persistent_dir=None):
        self.skill_path = Path(skill_path)
        self.rollout_fn = rollout_fn or _default_rollout
        self.reflector_fn = reflector_fn or _default_reflector
        self.validator_fn = validator_fn or _default_validator
        self.edit_budget = edit_budget
        self.max_epochs = max_epochs
        self.persistent_dir = Path(persistent_dir) if persistent_dir else None

        # Initial state
        self.current_skill = self._load_skill()
        self.best_skill = self.current_skill
        self.best_score = -float("inf")
        self.history = []
        self.rejected_buffer = []  # rejected_edits memory

    def _load_skill(self):
        if not self.skill_path.exists():
            raise FileNotFoundError(f"Skill file not found: {self.skill_path}")
        return self.skill_path.read_text(encoding="utf-8")

    def train(self, train_batch, val_batch):
        """
        Run the 4-loop training.

        Args:
            train_batch: task set for rollout (list of dict)
            val_batch:   task set for validation gate

        Returns: {
            "best_skill_path": str,
            "best_score": float,
            "history": [{epoch, train_score, val_score, edit_accepted, edit_rejected}],
            "rejected_count": int
        }
        """
        for epoch in range(1, self.max_epochs + 1):
            # 1. Rollout
            train_results = self.rollout_fn(self.current_skill, train_batch)
            successes = [r for r in train_results if r["score"] >= 0.8]
            failures = [r for r in train_results if r["score"] < 0.5]

            # 2. Reflect (generate bounded edit candidates)
            proposed_edits = self.reflector_fn(self.current_skill, successes, failures)

            # 3. Bounded Edit (sum of cost <= edit_budget)
            accepted_edits, deferred = self._bound_edits(proposed_edits)

            # 4. Build candidate skill
            candidate = self.current_skill
            for edit in accepted_edits:
                candidate = edit.apply_to(candidate)

            # 5. Validation Gate
            val_result = self.validator_fn(candidate, val_batch)
            val_score = val_result.get("score", 0)
            current_val = self.validator_fn(self.current_skill, val_batch).get("score", 0)

            epoch_entry = {
                "epoch": epoch,
                "train_score": _avg_score(train_results),
                "val_score_candidate": val_score,
                "val_score_current": current_val,
                "edits_proposed": len(proposed_edits),
                "edits_accepted_in_budget": len(accepted_edits),
                "edits_deferred": len(deferred),
                "edit_accepted": False,
                "edit_rejected_reason": None
            }

            # 6. Memory: update on gate pass, otherwise push to rejected_buffer
            if val_score > current_val:
                self.current_skill = candidate
                epoch_entry["edit_accepted"] = True
                if val_score > self.best_score:
                    self.best_skill = candidate
                    self.best_score = val_score
            else:
                epoch_entry["edit_rejected_reason"] = (
                    f"val_score {val_score:.3f} <= current {current_val:.3f}"
                )
                # rejected edits -> buffer (negative feedback for next reflector)
                for edit in accepted_edits:
                    self.rejected_buffer.append({
                        **edit.to_dict(),
                        "rejected_at_epoch": epoch,
                        "rejected_reason": epoch_entry["edit_rejected_reason"]
                    })

            self.history.append(epoch_entry)
            self._persist_state()

        # Export best_skill.md
        best_path = self._export_best()
        return {
            "best_skill_path": str(best_path),
            "best_score": self.best_score,
            "history": self.history,
            "rejected_count": len(self.rejected_buffer)
        }

    def _bound_edits(self, proposed_edits):
        """Sum costs within edit_budget. Priority based on rationale."""
        accepted = []
        deferred = []
        used = 0
        # Simple greedy: lowest cost first
        sorted_edits = sorted(proposed_edits, key=lambda e: e.cost())
        for edit in sorted_edits:
            if used + edit.cost() <= self.edit_budget:
                accepted.append(edit)
                used += edit.cost()
            else:
                deferred.append(edit)
        return accepted, deferred

    def _persist_state(self):
        if not self.persistent_dir:
            return
        self.persistent_dir.mkdir(parents=True, exist_ok=True)
        state_path = self.persistent_dir / "skillopt_state.json"
        data = {
            "version": 1,
            "last_updated": now_iso(),
            "skill_path": str(self.skill_path),
            "edit_budget": self.edit_budget,
            "max_epochs": self.max_epochs,
            "best_score": self.best_score,
            "history": self.history,
            "rejected_buffer": self.rejected_buffer
        }
        state_path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                encoding="utf-8")

    def _export_best(self):
        """Export best_skill.md (key deploy asset)."""
        out_path = self.skill_path.parent / f"{self.skill_path.stem}.best_skill.md"
        out_path.write_text(self.best_skill, encoding="utf-8")
        return out_path


# ============================================================
# Default callbacks (for testing and examples)
# ============================================================

def _default_rollout(skill_text, batch):
    """Simple echo (real implementation calls MAS Worker via caller)."""
    return [{"task_id": t.get("task_id", f"t{i}"),
             "score": 0.5 + (i % 3) * 0.2,
             "trajectory": "default_noop"}
            for i, t in enumerate(batch)]


def _default_reflector(skill_text, successes, failures):
    """Simple placeholder. Real implementation calls Adversarial Critic agent."""
    edits = []
    if len(failures) > len(successes):
        edits.append(SkillEdit(
            op_type="add",
            target_section="(end)",
            content_after="### Auto-added rule\n- Address recurring failure pattern",
            rationale=f"{len(failures)} failures vs {len(successes)} successes"
        ))
    return edits


def _default_validator(skill_text, val_batch):
    """Simple length-based score (placeholder). Real implementation calls MAS Verifier 10-dim."""
    # Shorter, clearer skills score higher
    length_penalty = max(0, 1 - len(skill_text) / 10000)
    return {"score": length_penalty, "details": "default_validator"}


def _avg_score(results):
    if not results:
        return 0
    return sum(r.get("score", 0) for r in results) / len(results)


# ============================================================
# MAS Integration helpers
# ============================================================

def integrate_with_mas_verifier(verifier_report_path):
    """
    Convert MAS Verifier 10-dim rubric report into a validator score.

    Usage:
        adapter.validator_fn = lambda skill, val: integrate_with_mas_verifier(
            run_verifier_with_skill(skill, val)
        )
    """
    if not Path(verifier_report_path).exists():
        return {"score": 0, "details": "verifier_report_missing"}
    with open(verifier_report_path, "r", encoding="utf-8") as f:
        report = json.load(f)
    return {
        "score": report.get("overall_score", 0),
        "details": {
            "verdict": report.get("verdict", "?"),
            "rubric": report.get("quality_rubric", {})
        }
    }


def integrate_with_adversarial_critic(adversarial_report_path):
    """
    Convert MAS Adversarial Critic vulnerability analysis into SkillEdit candidates.

    counter_scenarios -> SkillEdit (add or replace).
    """
    edits = []
    if not Path(adversarial_report_path).exists():
        return edits
    with open(adversarial_report_path, "r", encoding="utf-8") as f:
        report = json.load(f)
    for analysis in report.get("claim_analyses", []):
        for gap in analysis.get("coverage_gaps", []):
            edits.append(SkillEdit(
                op_type="add",
                target_section="(end)",
                content_after=f"### Address gap: {gap}\n- Mitigation rule TBD",
                rationale=f"Adversarial coverage_gap: {gap[:100]}"
            ))
    return edits


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    import tempfile

    print("=" * 60)
    print("SkillOpt Adapter Self-Test")
    print("=" * 60)

    tmpdir = tempfile.mkdtemp()
    skill_file = Path(tmpdir) / "test_skill.md"
    skill_file.write_text("""# Test Skill

## Identity
- Role: test agent
- KPI: accuracy

## Rules
1. Always cite sources
2. State assumptions
""", encoding="utf-8")

    adapter = SkillOptAdapter(
        skill_path=skill_file,
        edit_budget=4,
        max_epochs=3,
        persistent_dir=Path(tmpdir) / "skillopt_state"
    )

    train_batch = [{"task_id": f"train_{i}"} for i in range(5)]
    val_batch = [{"task_id": f"val_{i}"} for i in range(3)]

    result = adapter.train(train_batch, val_batch)

    print(f"\nbest_skill_path: {result['best_skill_path']}")
    print(f"best_score: {result['best_score']:.3f}")
    print(f"epochs: {len(result['history'])}")
    print(f"rejected: {result['rejected_count']}")
    for h in result["history"]:
        print(f"  epoch {h['epoch']}: train={h['train_score']:.2f}, "
              f"val_cand={h['val_score_candidate']:.2f}, "
              f"accepted={h['edit_accepted']}")

    print("\n" + "=" * 60)
    print(f"Demo complete. State: {tmpdir}")
