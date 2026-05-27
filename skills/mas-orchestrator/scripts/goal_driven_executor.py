"""
MAS Goal-Driven Worker Execution Mode

Core idea:
    Given only success_criteria from the PM, a Worker loops execution
    until the criteria are met, then terminates.

The existing prescriptive mode remains the default. This module is opt-in.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# Success Criterion verification methods
# ============================================================

VERIFICATION_METHODS = {
    "automated_test",      # pytest, unittest, etc.
    "metric_threshold",     # e.g. quality score >= 4.0
    "manual_check",         # user confirmation required
    "regex_match",          # output matches a pattern
    "schema_compliance",    # JSON schema validation
    "file_exists",          # file creation check
    "watchdog_verdict",     # MAS Watchdog's TRUE verdict
    "verifier_dim_score"    # MAS Verifier dimension score >= N
}


# ============================================================
# Goal-Driven Executor
# ============================================================

class GoalDrivenExecutor:
    """
    Wrapper that loops Worker execution until success_criteria are met.

    The Worker itself (Agent tool spawn or in-process) is supplied by the
    caller as the worker_runner callback. This class handles only the
    loop and verification.
    """

    def __init__(self, success_criteria, max_iterations=3,
                 worker_runner=None, verifier=None,
                 state_path=None):
        """
        Args:
            success_criteria: list of dict [{
                "criterion_id": "SC001",
                "description": "...",
                "verification_method": str,
                "verification_command": str (optional),
                "threshold": float (optional)
            }]
            max_iterations: maximum number of iterations (default 3)
            worker_runner: callable(iteration_num, prior_attempts) -> output
            verifier: callable(output, criterion) -> {"passed": bool, "score": float, "feedback": str}
            state_path: optional path for persisting progress state
        """
        self.success_criteria = success_criteria
        self.max_iterations = max_iterations
        self.worker_runner = worker_runner
        self.verifier = verifier or default_verifier
        self.state_path = Path(state_path) if state_path else None
        self.attempts = []

    def execute(self):
        """
        Loop until all criteria met or max_iterations reached.

        Returns: {
            "status": "passed | failed | max_iter",
            "iterations": int,
            "attempts": [{iteration, output, verifications}],
            "final_output": ... | None,
            "unmet_criteria": [...]
        }
        """
        for it in range(1, self.max_iterations + 1):
            output = self._run_iteration(it)
            verifications = self._verify_all(output)

            self.attempts.append({
                "iteration": it,
                "output_summary": _summarize(output),
                "verifications": verifications,
                "timestamp": now_iso()
            })
            self._persist_state()

            # All passed?
            if all(v["passed"] for v in verifications):
                return {
                    "status": "passed",
                    "iterations": it,
                    "attempts": self.attempts,
                    "final_output": output,
                    "unmet_criteria": []
                }

            # Loop with self-reflection
            unmet = [v for v in verifications if not v["passed"]]
            if it < self.max_iterations:
                self._self_reflect(output, unmet)

        # Max iterations reached without all passing
        last = self.attempts[-1]
        unmet = [v for v in last["verifications"] if not v["passed"]]
        return {
            "status": "max_iter",
            "iterations": self.max_iterations,
            "attempts": self.attempts,
            "final_output": _last_output(self.attempts),
            "unmet_criteria": [v["criterion_id"] for v in unmet]
        }

    def _run_iteration(self, iteration_num):
        if not self.worker_runner:
            return {
                "noop": True,
                "iteration": iteration_num,
                "note": "no worker_runner provided"
            }
        return self.worker_runner(iteration_num, self.attempts)

    def _verify_all(self, output):
        results = []
        for criterion in self.success_criteria:
            try:
                v = self.verifier(output, criterion)
                if "criterion_id" not in v:
                    v["criterion_id"] = criterion.get("criterion_id", "?")
            except Exception as e:
                v = {
                    "criterion_id": criterion.get("criterion_id", "?"),
                    "passed": False,
                    "score": 0,
                    "feedback": f"verification error: {e}"
                }
            results.append(v)
        return results

    def _self_reflect(self, output, unmet):
        """
        Self-Reflection component.

        This simple implementation forwards the unmet criteria to the
        worker_runner. Any actual self-reflection LLM call is handled
        by the worker_runner itself.
        """
        return {
            "unmet_criteria_count": len(unmet),
            "feedback_for_next_iteration": [
                {"criterion_id": v["criterion_id"], "feedback": v.get("feedback", "")}
                for v in unmet
            ]
        }

    def _persist_state(self):
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump({
                "version": 1,
                "last_updated": now_iso(),
                "max_iterations": self.max_iterations,
                "criteria": self.success_criteria,
                "attempts": self.attempts
            }, f, ensure_ascii=False, indent=2)


# ============================================================
# Default verifier - common verification methods
# ============================================================

def default_verifier(output, criterion):
    """
    Handle common verification methods. The actual verification varies
    by method.

    output: Worker output (dict | str | object)
    criterion: success criterion dict
    Returns: {"criterion_id", "passed", "score", "feedback"}
    """
    method = criterion.get("verification_method", "manual_check")
    cid = criterion.get("criterion_id", "?")

    if method == "metric_threshold":
        threshold = criterion.get("threshold", 0)
        actual = _extract_metric(output, criterion.get("metric_path"))
        if actual is None:
            return {"criterion_id": cid, "passed": False, "score": 0,
                    "feedback": f"metric not found at {criterion.get('metric_path')}"}
        passed = actual >= threshold
        return {"criterion_id": cid, "passed": passed, "score": float(actual),
                "feedback": f"actual={actual} vs threshold={threshold}"}

    elif method == "regex_match":
        import re
        pattern = criterion.get("pattern", "")
        text = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
        match = re.search(pattern, text)
        return {"criterion_id": cid, "passed": bool(match),
                "score": 1.0 if match else 0,
                "feedback": "matched" if match else "no match"}

    elif method == "schema_compliance":
        schema = criterion.get("schema", {})
        try:
            import jsonschema
            jsonschema.validate(output, schema)
            return {"criterion_id": cid, "passed": True, "score": 1.0,
                    "feedback": "schema valid"}
        except ImportError:
            # Fallback minimal check
            required = schema.get("required", [])
            missing = [k for k in required if not (isinstance(output, dict) and k in output)]
            passed = len(missing) == 0
            return {"criterion_id": cid, "passed": passed,
                    "score": 1.0 if passed else 0,
                    "feedback": f"missing: {missing}"}
        except Exception as e:
            return {"criterion_id": cid, "passed": False, "score": 0,
                    "feedback": f"schema invalid: {e}"}

    elif method == "file_exists":
        p = Path(criterion.get("path", ""))
        passed = p.exists()
        return {"criterion_id": cid, "passed": passed,
                "score": 1.0 if passed else 0,
                "feedback": f"{p} {'exists' if passed else 'missing'}"}

    elif method == "manual_check":
        return {"criterion_id": cid, "passed": False, "score": 0,
                "feedback": "manual_check requires user - defaulted to fail"}

    elif method == "automated_test":
        # The caller must include results from an external test runner (e.g. pytest) in the output.
        test_result = output.get("test_result") if isinstance(output, dict) else None
        if test_result is None:
            return {"criterion_id": cid, "passed": False, "score": 0,
                    "feedback": "test_result not provided in output"}
        passed = bool(test_result.get("passed"))
        return {"criterion_id": cid, "passed": passed,
                "score": 1.0 if passed else 0,
                "feedback": test_result.get("summary", "")}

    elif method == "watchdog_verdict":
        # for MAS integration
        verdict = output.get("watchdog_verdict") if isinstance(output, dict) else None
        passed = verdict == "TRUE"
        return {"criterion_id": cid, "passed": passed,
                "score": 1.0 if passed else 0,
                "feedback": f"Watchdog verdict: {verdict}"}

    elif method == "verifier_dim_score":
        dim = criterion.get("dimension", "")
        threshold = criterion.get("threshold", 4.0)
        score = output.get(f"verifier_{dim}_score", 0) if isinstance(output, dict) else 0
        passed = score >= threshold
        return {"criterion_id": cid, "passed": passed, "score": score,
                "feedback": f"{dim} score={score} vs threshold={threshold}"}

    else:
        return {"criterion_id": cid, "passed": False, "score": 0,
                "feedback": f"unknown method: {method}"}


# ============================================================
# Helpers
# ============================================================

def _extract_metric(output, path):
    """Extract a metric using dot-notation path (e.g. 'metrics.quality.score')."""
    if not path:
        return None
    cur = output
    for seg in path.split("."):
        if isinstance(cur, dict) and seg in cur:
            cur = cur[seg]
        else:
            return None
    return cur


def _summarize(output):
    if isinstance(output, str):
        return output[:200]
    if isinstance(output, dict):
        return {k: (v[:200] if isinstance(v, str) else "<...>" if isinstance(v, dict) else v)
                for k, v in list(output.items())[:5]}
    return str(output)[:200]


def _last_output(attempts):
    if not attempts:
        return None
    return attempts[-1].get("output_summary")


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MAS Goal-Driven Executor Self-Test")
    print("=" * 60)

    # Demo: increment until score >= 0.9
    state = {"score": 0.5}

    def fake_worker(iteration, prior):
        # Each iteration increases score by 0.2 (>=0.9 after 3 calls, 1.1 after 4)
        state["score"] += 0.2
        return {"score": state["score"], "iteration": iteration}

    criteria = [{
        "criterion_id": "SC001",
        "description": "score >= 0.9",
        "verification_method": "metric_threshold",
        "metric_path": "score",
        "threshold": 0.9
    }]

    executor = GoalDrivenExecutor(
        success_criteria=criteria,
        max_iterations=5,
        worker_runner=fake_worker
    )
    result = executor.execute()
    print(f"\nstatus: {result['status']}")
    print(f"iterations: {result['iterations']}")
    print(f"final_output: {result['final_output']}")
    print(f"unmet: {result['unmet_criteria']}")

    print("\n" + "=" * 60)
    print(f"Demo complete. Looped {result['iterations']} times until criteria met.")
