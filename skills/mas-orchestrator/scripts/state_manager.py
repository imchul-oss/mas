#!/usr/bin/env python3
"""
MAS State Manager
=================

This module provides:

  - State management (init/read/write)
  - Telemetry, Breakpoints
  - Worker/Skill/Agent registries
  - Concurrency safety (file lock + atomic write)
  - Bayesian convergence (cold-start fallback)
  - Watchdog Pool aggregation
  - Worker conflict detection
  - MCP async Tasks primitive
  - Anthropic Memory API adapter
  - LangGraph-style checkpoint + time travel
  - OpenAI SDK-style worker handoff
  - Structured Output Schema validation
"""

import json
import os
import sys
import argparse
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager

# ============================================================
# Globals & Constants
# ============================================================

STATE_DIR = None
PERSISTENT_DIR = None

PERSISTENT_FILES = {
    "process_policy.json", "worker_registry.json", "skill_registry.json",
    "agent_evolution.json", "meta.json", "memory_index.json"
}

DEFAULT_REVIEW_INTERVAL = 5

# Bayesian convergence
HARDCODED_THRESHOLDS = {"simple": 0.15, "moderate": 0.10, "complex": 0.05, "expert": 0.03}
MIN_SAMPLES_FOR_BAYESIAN = 10
PRIOR_ALPHA = 2.0
PRIOR_BETA = 2.0

# Async Tasks state
TASK_STATES = {"pending", "working", "input_required", "completed", "failed", "cancelled"}

# Checkpoint retention
CHECKPOINT_RETENTION = 5  # last 5 + summary

# Handoff hop limit
MAX_HANDOFF_HOPS = 3


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# Concurrency Safety — File Lock + Atomic Write
# ============================================================

if sys.platform == "win32":
    import msvcrt
    @contextmanager
    def _file_lock(file_handle):
        try:
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)
            yield
        finally:
            try:
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
else:
    import fcntl
    @contextmanager
    def _file_lock(file_handle):
        try:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


_REPLACE_RETRIES = 50
_REPLACE_DELAY_S = 0.01


@contextmanager
def _exclusive_write_lock(filepath):
    """Serialize writers to the same destination via a sidecar .lock file.

    The lock is held across the entire read-version -> os.replace window so
    that the version CAS cannot suffer lost updates, and so that two writers
    never race on os.replace (which raises PermissionError on Windows when
    the destination is open in another writer/reader).
    """
    lockpath = filepath.with_name(filepath.name + ".lock")
    lock_handle = open(lockpath, "a+")
    try:
        with _file_lock(lock_handle):
            yield
    finally:
        lock_handle.close()


def _replace_with_retry(src, dst):
    """os.replace with short backoff retry.

    On Windows, os.replace fails with PermissionError when the destination is
    momentarily open by a concurrent reader (no FILE_SHARE_DELETE). Retrying
    briefly is the standard pattern; POSIX never hits this path.
    """
    last_err = None
    for _ in range(_REPLACE_RETRIES):
        try:
            os.replace(src, dst)
            return
        except PermissionError as e:
            last_err = e
            time.sleep(_REPLACE_DELAY_S)
    raise last_err


def _atomic_write(filepath, data):
    """Atomic write with writer serialization (sidecar lock) + fsync + os.replace."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with _exclusive_write_lock(filepath):
        # CAS via version field (race-free: lock held until replace completes)
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                if "version" in existing and "version" in data:
                    if data["version"] <= existing["version"]:
                        data["version"] = existing["version"] + 1
            except (json.JSONDecodeError, OSError):
                pass

        fd, tmppath = tempfile.mkstemp(
            dir=str(filepath.parent), prefix=f".{filepath.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            _replace_with_retry(tmppath, filepath)
            return str(filepath)
        except Exception:
            try:
                os.unlink(tmppath)
            except OSError:
                pass
            raise


# ============================================================
# Path Resolution
# ============================================================

def get_state_dir():
    global STATE_DIR
    if STATE_DIR is None:
        STATE_DIR = Path.cwd() / "state"
    return STATE_DIR


def get_persistent_dir():
    global PERSISTENT_DIR
    if PERSISTENT_DIR is None:
        env_dir = os.environ.get("MAS_PERSISTENT_DIR")
        if env_dir and Path(env_dir).parent.exists():
            PERSISTENT_DIR = Path(env_dir)
        else:
            cowork_path = Path("/sessions") / os.environ.get("SESSION_NAME", "") / "mnt" / "claude" / "mas-state"
            if cowork_path.parent.exists():
                PERSISTENT_DIR = cowork_path
            else:
                claude_dir = Path.home() / ".claude" / "mas-state"
                try:
                    claude_dir.mkdir(parents=True, exist_ok=True)
                    PERSISTENT_DIR = claude_dir
                except OSError:
                    PERSISTENT_DIR = get_state_dir()
    return PERSISTENT_DIR


def set_state_dir(path):
    global STATE_DIR
    STATE_DIR = Path(path)


def set_persistent_dir(path):
    global PERSISTENT_DIR
    PERSISTENT_DIR = Path(path)


def _resolve_path(filename):
    base = get_persistent_dir() if filename in PERSISTENT_FILES else get_state_dir()
    return base / filename


def read_state(filename):
    filepath = _resolve_path(filename)
    if not filepath.exists():
        alt = (get_state_dir() if filename in PERSISTENT_FILES else get_persistent_dir()) / filename
        if alt.exists():
            filepath = alt
        else:
            return None
    with open(filepath, "r", encoding="utf-8") as f:
        with _file_lock(f):
            return json.load(f)


def write_state(filename, data):
    """Atomic write. Preserves the existing write_state interface."""
    return _atomic_write(_resolve_path(filename), data)


# ============================================================
# Bayesian Convergence (Cold-start fallback)
# ============================================================

def _wilson_hilferty_beta_ppf(p, alpha, beta):
    """Beta(alpha, beta) p-percentile via Wilson-Hilferty approximation. +/-0.02 bound (alpha+beta >= 10)."""
    import math
    mean = alpha / (alpha + beta)
    var = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))
    std = math.sqrt(var)
    if p < 0.5:
        t = math.sqrt(-2 * math.log(p))
        z = -(t - (2.30753 + 0.27061 * t) / (1 + 0.99229 * t + 0.04481 * t ** 2))
    else:
        t = math.sqrt(-2 * math.log(1 - p))
        z = t - (2.30753 + 0.27061 * t) / (1 + 0.99229 * t + 0.04481 * t ** 2)
    return max(0.001, min(0.999, mean + z * std))


def get_adaptive_threshold(complexity):
    meta = _read_meta()
    bayes = meta.get("convergence_bayes", {})
    tier = bayes.get(complexity)
    if not tier or tier.get("sample_count", 0) < MIN_SAMPLES_FOR_BAYESIAN:
        return HARDCODED_THRESHOLDS.get(complexity, 0.10), "hardcoded_fallback"
    threshold = _wilson_hilferty_beta_ppf(0.05, tier.get("alpha", PRIOR_ALPHA), tier.get("beta", PRIOR_BETA))
    return threshold, "bayesian"


def update_convergence_bayes(complexity, converged_within_budget):
    meta = _read_meta()
    bayes = meta.setdefault("convergence_bayes", {})
    tier = bayes.setdefault(complexity, {"alpha": PRIOR_ALPHA, "beta": PRIOR_BETA, "sample_count": 0})
    if converged_within_budget:
        tier["alpha"] = tier.get("alpha", PRIOR_ALPHA) + 1
    else:
        tier["beta"] = tier.get("beta", PRIOR_BETA) + 1
    tier["sample_count"] = tier.get("sample_count", 0) + 1
    tier["last_updated"] = now_iso()
    _write_meta(meta)


# ============================================================
# Watchdog Pool Aggregation
# ============================================================

def aggregate_watchdog_verdicts(pool_verdicts):
    """Aggregate verdicts from multiple Watchdog instances. Classify as unanimous, majority, or disputed."""
    if not pool_verdicts:
        return {"consensus": "UNVERIFIABLE", "method": "no_input", "early_exit": False}
    verdicts = [pv["verdict"] for pv in pool_verdicts]
    pool_size = len(verdicts)
    if len(set(verdicts)) == 1:
        return {"consensus": verdicts[0], "method": "unanimous",
                "majority_count": pool_size, "dissent": [], "early_exit": True}
    from collections import Counter
    cnt = Counter(verdicts)
    majority_verdict, majority_count = cnt.most_common(1)[0]
    threshold = (pool_size * 2 + 2) // 3
    if majority_count >= threshold:
        dissent = [pv for pv in pool_verdicts if pv["verdict"] != majority_verdict]
        return {"consensus": majority_verdict, "method": "majority",
                "majority_count": majority_count, "dissent": dissent, "early_exit": False}
    return {"consensus": "DISPUTED", "method": "dispute",
            "majority_count": majority_count, "dissent": pool_verdicts,
            "early_exit": False, "next_action": "round2_or_user_arbitration"}


# ============================================================
# Worker Conflict Detection
# ============================================================

def detect_worker_conflicts(worker_outputs):
    """Detect entity/sub-claim conflicts between multiple worker outputs."""
    conflicts = []
    for i, wo_a in enumerate(worker_outputs):
        for wo_b in worker_outputs[i + 1:]:
            tasks_a = {t.get("task_id"): t for t in wo_a.get("tasks_completed", [])}
            tasks_b = {t.get("task_id"): t for t in wo_b.get("tasks_completed", [])}
            shared = set(tasks_a.keys()) & set(tasks_b.keys())
            for tid in shared:
                summary_a = tasks_a[tid].get("output_summary", "")
                summary_b = tasks_b[tid].get("output_summary", "")
                if not summary_a or not summary_b:
                    continue
                if summary_a != summary_b:
                    conflicts.append({
                        "conflict_id": f"CF{len(conflicts) + 1:03d}",
                        "entity": f"task_{tid}",
                        "worker_a": {"id": wo_a.get("worker_id"), "claim": summary_a[:200]},
                        "worker_b": {"id": wo_b.get("worker_id"), "claim": summary_b[:200]},
                        "stage_recommendation": "watchdog_reverify"
                    })
    return conflicts


# ============================================================
# MCP Async Tasks Primitive
# ============================================================

def create_async_task(agent_name, task_payload, parent_session_id=None):
    """Split long-running work into a task handle.
    Returns: task_id (UUID4)
    """
    task_id = str(uuid.uuid4())
    tasks_file = "async_tasks.json"
    tasks = read_state(tasks_file) or {"version": 1, "tasks": {}}
    tasks["tasks"][task_id] = {
        "task_id": task_id,
        "agent": agent_name,
        "state": "pending",
        "created_at": now_iso(),
        "parent_session": parent_session_id,
        "payload": task_payload,
        "result": None,
        "error": None
    }
    write_state(tasks_file, tasks)
    return task_id


def update_async_task(task_id, new_state, result=None, error=None):
    """Transition a task state. Raises ValueError for unknown states."""
    if new_state not in TASK_STATES:
        raise ValueError(f"Invalid task state: {new_state}. Must be {TASK_STATES}")
    tasks = read_state("async_tasks.json")
    if not tasks or task_id not in tasks.get("tasks", {}):
        raise KeyError(f"Task {task_id} not found")
    task = tasks["tasks"][task_id]
    task["state"] = new_state
    task["last_updated"] = now_iso()
    if result is not None:
        task["result"] = result
    if error is not None:
        task["error"] = error
    write_state("async_tasks.json", tasks)


def get_async_task(task_id):
    tasks = read_state("async_tasks.json")
    if not tasks:
        return None
    return tasks.get("tasks", {}).get(task_id)


def list_async_tasks(state_filter=None):
    tasks = read_state("async_tasks.json")
    if not tasks:
        return []
    result = list(tasks.get("tasks", {}).values())
    if state_filter:
        result = [t for t in result if t["state"] == state_filter]
    return result


# ============================================================
# Anthropic Memory API Adapter
# ============================================================

def memory_export(agent_name=None):
    """Self-rolled state -> Anthropic Memory API format.
    Adapter pattern preserves the internal schema while staying compatible externally.
    """
    process = read_state("process_policy.json") or {}
    workers = read_state("worker_registry.json") or {}
    memory_export_data = {
        "version": 1,
        "exported_at": now_iso(),
        "format": "anthropic_memory_api_v1",
        "memories": []
    }
    # process_policy.json patterns -> memory entries
    for task_type, pattern in process.get("patterns", {}).items():
        memory_export_data["memories"].append({
            "id": f"pattern_{task_type}",
            "type": "procedural",
            "content": json.dumps(pattern, ensure_ascii=False),
            "metadata": {"task_type": task_type, "source": "mas_process_policy"}
        })
    # worker_registry -> memory entries (specialist workers)
    for sp in workers.get("specialists", []):
        if agent_name and agent_name not in sp.get("domain", ""):
            continue
        memory_export_data["memories"].append({
            "id": f"specialist_{sp['specialist_id']}",
            "type": "semantic",
            "content": json.dumps(sp, ensure_ascii=False),
            "metadata": {"domain": sp.get("domain"), "source": "mas_worker_registry"}
        })
    return memory_export_data


def memory_import(memory_data):
    """Anthropic Memory API -> self-rolled state. Bidirectional compatibility."""
    imported_count = 0
    for mem in memory_data.get("memories", []):
        if mem.get("metadata", {}).get("source") == "mas_process_policy":
            process = read_state("process_policy.json") or {"version": 1, "patterns": {}}
            task_type = mem.get("metadata", {}).get("task_type")
            if task_type:
                try:
                    process["patterns"][task_type] = json.loads(mem["content"])
                    imported_count += 1
                except json.JSONDecodeError:
                    pass
            write_state("process_policy.json", process)
    return imported_count


# ============================================================
# LangGraph-style Checkpoint + Time Travel
# ============================================================

def create_checkpoint(checkpoint_name=None):
    """Snapshot the current state directory.
    Retention: last 5 + summary."""
    state_dir = get_state_dir()
    if not state_dir.exists():
        return None
    checkpoint_dir = state_dir / "_checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)
    cp_id = checkpoint_name or f"cp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    cp_path = checkpoint_dir / cp_id
    cp_path.mkdir(exist_ok=True)
    # Copy all state files (excluding checkpoints directory itself)
    for f in state_dir.iterdir():
        if f.is_file() and f.suffix == ".json":
            shutil.copy2(f, cp_path / f.name)
    # Apply retention policy
    _enforce_checkpoint_retention(checkpoint_dir)
    return cp_id


def restore_checkpoint(cp_id):
    """Time travel: restore state from a specific checkpoint."""
    state_dir = get_state_dir()
    cp_path = state_dir / "_checkpoints" / cp_id
    if not cp_path.exists():
        raise FileNotFoundError(f"Checkpoint {cp_id} not found")
    # Back up current state (rollback is possible)
    backup_id = create_checkpoint(f"pre_restore_{cp_id}")
    # Restore checkpoint files into state_dir
    for f in cp_path.iterdir():
        if f.is_file() and f.suffix == ".json":
            shutil.copy2(f, state_dir / f.name)
    return backup_id


def list_checkpoints():
    state_dir = get_state_dir()
    cp_dir = state_dir / "_checkpoints"
    if not cp_dir.exists():
        return []
    return sorted([cp.name for cp in cp_dir.iterdir() if cp.is_dir()])


def _enforce_checkpoint_retention(checkpoint_dir):
    """Retention: keep the last N + 'summary'. Delete everything else."""
    cps = sorted([cp for cp in checkpoint_dir.iterdir() if cp.is_dir()],
                 key=lambda p: p.stat().st_mtime, reverse=True)
    keep = cps[:CHECKPOINT_RETENTION]
    keep_names = {cp.name for cp in keep} | {"summary"}
    for cp in cps:
        if cp.name not in keep_names:
            shutil.rmtree(cp, ignore_errors=True)


# ============================================================
# OpenAI SDK-style Worker Handoff
# ============================================================

def record_worker_handoff(from_worker, to_worker, context, hop_count=0):
    """Direct worker-to-worker transfer. Hop count limit prevents infinite ping-pong."""
    if hop_count >= MAX_HANDOFF_HOPS:
        return {"accepted": False, "reason": f"hop_limit_exceeded ({hop_count})"}
    handoffs = read_state("worker_handoffs.json") or {"version": 1, "handoffs": []}
    handoff_id = f"HO{len(handoffs['handoffs']) + 1:03d}"
    handoffs["handoffs"].append({
        "handoff_id": handoff_id,
        "from": from_worker,
        "to": to_worker,
        "context": context,
        "hop_count": hop_count + 1,
        "timestamp": now_iso(),
        "accepted": True
    })
    write_state("worker_handoffs.json", handoffs)
    return {"accepted": True, "handoff_id": handoff_id, "hop_count": hop_count + 1}


def get_handoff_chain(starting_handoff_id):
    """Trace the handoff chain (for debugging)."""
    handoffs = read_state("worker_handoffs.json")
    if not handoffs:
        return []
    chain = []
    by_id = {h["handoff_id"]: h for h in handoffs["handoffs"]}
    current = by_id.get(starting_handoff_id)
    while current:
        chain.append(current)
        next_handoff = next((h for h in handoffs["handoffs"]
                             if h["from"] == current["to"] and h["timestamp"] > current["timestamp"]), None)
        current = next_handoff
        if len(chain) > MAX_HANDOFF_HOPS + 1:
            break
    return chain


# ============================================================
# Structured Output Schema Validation
# ============================================================

def validate_worker_output_schema(worker_output, schema):
    """Validate a worker's output against a JSON Schema.
    Uses a minimal built-in validator to avoid hard dependencies (jsonschema is optional)."""
    errors = []
    try:
        import jsonschema
        try:
            jsonschema.validate(worker_output, schema)
            return {"valid": True, "errors": []}
        except jsonschema.ValidationError as e:
            return {"valid": False, "errors": [str(e)]}
    except ImportError:
        # Fallback: minimal type/required checks
        if "type" in schema and schema["type"] == "object":
            if not isinstance(worker_output, dict):
                errors.append("Expected object")
        if "required" in schema:
            for req_field in schema["required"]:
                if req_field not in worker_output:
                    errors.append(f"Missing required field: {req_field}")
        return {"valid": len(errors) == 0, "errors": errors}


# ============================================================
# Core features (init_session, telemetry, breakpoints, etc.)
# ============================================================

def _read_meta():
    meta_path = get_persistent_dir() / "meta.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            with _file_lock(f):
                return json.load(f)
    return {
        "session_count": 0,
        "review_interval": DEFAULT_REVIEW_INTERVAL,
        "last_review_session": 0,
        "last_review_date": None,
        "review_history": [],
        "avg_quality_scores": [],
        "convergence_bayes": {},
        "memory_api_enabled": False,
        "created_at": now_iso(),
    }


def _write_meta(meta):
    _atomic_write(get_persistent_dir() / "meta.json", meta)


def _check_learning_review_due(meta):
    sessions_since = meta["session_count"] - meta["last_review_session"]
    interval = meta.get("review_interval", DEFAULT_REVIEW_INTERVAL)
    if sessions_since >= interval:
        return True, f"interval_reached ({sessions_since}/{interval})"
    scores = meta.get("avg_quality_scores", [])
    if len(scores) >= 3:
        last3 = scores[-3:]
        if last3[0] > last3[1] > last3[2]:
            return True, f"quality_declining ({last3})"
    return False, None


def init_session(task_description):
    state_dir = get_state_dir()
    state_dir.mkdir(parents=True, exist_ok=True)
    persistent_dir = get_persistent_dir()
    persistent_dir.mkdir(parents=True, exist_ok=True)

    meta = _read_meta()
    meta["session_count"] += 1
    meta["last_session_date"] = now_iso()
    _write_meta(meta)

    review_due, trigger_reason = _check_learning_review_due(meta)
    if review_due:
        print(f"  LEARNING REVIEW DUE: {trigger_reason}")

    print(f"  Session #{meta['session_count']}")

    session_state = {
        "session_id": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
        "created_at": now_iso(),
        "task_description": task_description,
        "status": "initialized",
        "current_phase": 0,
        "iteration": 1,
        "max_iterations": 3,
        "agents_status": {a: "pending" for a in
                          ["prompt_architect", "pm_orchestrator", "researcher",
                           "watchdog", "worker", "verifier", "adversarial_critic"]},
        "worker_pool_status": {},
        "watchdog_pool_status": {},
        "phase_history": [],
        "checkpoints": [],
        "async_tasks": [],
    }
    write_state("session_state.json", session_state)

    # Empty state files
    empty_files = {
        "prompt_output.json": {"version": 0, "timestamp": now_iso()},
        "pm_plan.json": {"version": 0, "timestamp": now_iso()},
        "research_data.json": {"version": 0, "timestamp": now_iso()},
        "watchdog_verdicts.json": {"version": 0, "timestamp": now_iso()},
        "watchdog_pool_verdicts.json": {"version": 0, "timestamp": now_iso()},
        "worker_output.json": {"version": 0, "timestamp": now_iso()},
        "worker_conflicts.json": {"version": 0, "conflicts": []},
        "worker_handoffs.json": {"version": 0, "handoffs": []},
        "adversarial_report.json": {"version": 0, "timestamp": now_iso()},
        "verifier_report.json": {"version": 0, "timestamp": now_iso()},
        "feedback_loop.json": {"version": 0, "feedbacks": {a: [] for a in
                                ["prompt_architect", "pm_orchestrator", "researcher",
                                 "watchdog", "worker", "verifier", "adversarial_critic"]}},
        "iteration_log.json": {"iterations": [], "current_iteration": 1},
        "process_policy.json": {"version": 1, "last_updated": now_iso(), "patterns": {}, "global_rules": []},
        "error_log.json": {"errors": []},
        "telemetry.json": {"version": 1, "created_at": now_iso(), "agent_metrics": {},
                           "phase_metrics": {}, "cumulative": {"total_agent_runs": 0,
                           "total_tool_calls": 0, "total_retries": 0, "total_duration_ms": 0}},
        "breakpoints.json": {"version": 1, "created_at": now_iso(),
                             "breakpoint_policy": "auto", "gates": [], "decisions": []},
        "async_tasks.json": {"version": 1, "tasks": {}},
    }
    for filename, content in empty_files.items():
        write_state(filename, content)

    print(f"Session initialized: {session_state['session_id']}")
    return session_state


# ============================================================
# Breakpoints (gate policy)
# ============================================================

def set_breakpoint_policy(policy):
    """Set the session breakpoint policy in breakpoints.json (SKILL.md Phase 0)."""
    breakpoints = read_state("breakpoints.json") or {
        "version": 1, "created_at": now_iso(),
        "breakpoint_policy": policy, "gates": [], "decisions": []
    }
    breakpoints["breakpoint_policy"] = policy
    breakpoints["last_updated"] = now_iso()
    write_state("breakpoints.json", breakpoints)
    return breakpoints


def list_breakpoints():
    """Return the current breakpoints.json content (policy, gates, decisions)."""
    return read_state("breakpoints.json") or {}


# ============================================================
# Adaptive convergence detection (should_continue_loop)
# ============================================================

def should_continue_loop():
    """Bayesian convergence + checkpoint awareness."""
    session = read_state("session_state.json")
    iteration_log = read_state("iteration_log.json")
    verifier = read_state("verifier_report.json")
    prompt_output = read_state("prompt_output.json")

    current_iteration = session.get("iteration", 1)
    max_iterations = session.get("max_iterations", 3)
    complexity = (prompt_output.get("analysis", {}).get("complexity_level", "moderate")
                  if prompt_output else "moderate")

    threshold, source = get_adaptive_threshold(complexity)

    # Condition 1: max iterations
    if current_iteration > max_iterations:
        result = {"continue": False, "reason": f"max_iterations({max_iterations}) reached",
                  "algorithm": "max_iteration", "complexity": complexity, "threshold_source": source}
        print(json.dumps(result, ensure_ascii=False))
        return False

    # Condition 2: PASS
    if verifier and verifier.get("verdict") == "PASS":
        update_convergence_bayes(complexity, True)
        result = {"continue": False, "reason": "Verifier PASS",
                  "algorithm": "pass_achieved", "final_score": verifier.get("overall_score", 0)}
        print(json.dumps(result, ensure_ascii=False))
        return False

    # Condition 3: adaptive convergence
    iterations = iteration_log.get("iterations", []) if iteration_log else []
    if len(iterations) >= 2:
        scores = [it.get("overall_score", 0) for it in iterations]
        delta = abs(scores[-1] - scores[-2])
        if delta < threshold:
            update_convergence_bayes(complexity, False)
            result = {"continue": False, "reason": f"adaptive_convergence (delta={delta:.3f}<{threshold:.3f})",
                      "algorithm": "adaptive_convergence", "scores": scores,
                      "threshold_source": source, "complexity": complexity}
            print(json.dumps(result, ensure_ascii=False))
            return False
        # Declining trend
        if len(scores) >= 3:
            gradients = [scores[i] - scores[i - 1] for i in range(1, len(scores))]
            if gradients[-1] < 0 and sum(gradients) / len(gradients) < 0:
                result = {"continue": False, "reason": "negative_gradient",
                          "algorithm": "gradient_decline", "scores": scores}
                print(json.dumps(result, ensure_ascii=False))
                return False

    result = {"continue": True, "iteration": current_iteration, "max": max_iterations,
              "complexity": complexity, "threshold": threshold, "threshold_source": source}
    print(json.dumps(result, ensure_ascii=False))
    return True


# ============================================================
# CLI Entry Point
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="MAS State Manager")
    parser.add_argument("--state-dir", help="Session state directory")
    parser.add_argument("--persistent-dir", help="Persistent learning data directory")
    sub = parser.add_subparsers(dest="command")

    # Core commands
    p_init = sub.add_parser("init"); p_init.add_argument("--task", required=True)
    sub.add_parser("validate")
    sub.add_parser("should-loop")
    sub.add_parser("review-status")
    p_review = sub.add_parser("complete-review"); p_review.add_argument("--quality-score", type=float)

    # Watchdog/conflict commands
    p_pool = sub.add_parser("watchdog-pool-aggregate")
    p_pool.add_argument("--input-file", required=True)
    p_conflict = sub.add_parser("detect-conflicts")
    p_conflict.add_argument("--worker-files", nargs="+")

    # Async/checkpoint/handoff/memory commands
    p_async = sub.add_parser("async-task")
    p_async.add_argument("--action", choices=["create", "update", "get", "list"], required=True)
    p_async.add_argument("--task-id")
    p_async.add_argument("--state")
    p_async.add_argument("--agent")

    p_cp = sub.add_parser("checkpoint")
    p_cp.add_argument("--action", choices=["create", "restore", "list"], required=True)
    p_cp.add_argument("--cp-id")

    p_handoff = sub.add_parser("handoff")
    p_handoff.add_argument("--from-worker", required=True)
    p_handoff.add_argument("--to-worker", required=True)
    p_handoff.add_argument("--hop-count", type=int, default=0)

    p_mem = sub.add_parser("memory")
    p_mem.add_argument("--action", choices=["export", "import"], required=True)
    p_mem.add_argument("--data-file")

    p_bp = sub.add_parser("breakpoint")
    p_bp.add_argument("--action", choices=["set-policy", "list"], required=True)
    p_bp.add_argument("--policy", default="auto")

    args = parser.parse_args()

    if args.state_dir: set_state_dir(args.state_dir)
    if args.persistent_dir: set_persistent_dir(args.persistent_dir)

    if args.command == "init":
        init_session(args.task)
    elif args.command == "should-loop":
        should_continue_loop()
    elif args.command == "watchdog-pool-aggregate":
        with open(args.input_file) as f:
            verdicts = json.load(f)
        result = aggregate_watchdog_verdicts(verdicts)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "async-task":
        if args.action == "create":
            tid = create_async_task(args.agent or "unknown", {})
            print(json.dumps({"task_id": tid}))
        elif args.action == "list":
            print(json.dumps(list_async_tasks(args.state), ensure_ascii=False, indent=2))
    elif args.command == "checkpoint":
        if args.action == "create":
            cp = create_checkpoint()
            print(json.dumps({"checkpoint_id": cp}))
        elif args.action == "list":
            print(json.dumps(list_checkpoints(), ensure_ascii=False))
    elif args.command == "memory":
        if args.action == "export":
            data = memory_export()
            print(json.dumps(data, ensure_ascii=False, indent=2))
    elif args.command == "breakpoint":
        if args.action == "set-policy":
            bp = set_breakpoint_policy(args.policy)
            print(json.dumps({"breakpoint_policy": bp["breakpoint_policy"]}, ensure_ascii=False))
        elif args.action == "list":
            print(json.dumps(list_breakpoints(), ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
