"""
MAS Test-First Task Transformation

Examples:
| "Add validation"   ->  "Write tests for invalid inputs, then make them pass"
| "Fix the bug"       ->  "Write a test that reproduces it, then make it pass"
| "Refactor X"        ->  "Ensure tests pass before and after"

Automatically converts imperative tasks into verifiable goals during PM
Step 3.7.

This module is Pure Python keyword-based heuristics (no NLP dependencies).
Accuracy can be improved later by upgrading to an LLM-based transformation.
"""

import re
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# Transformation Patterns
# ============================================================

TRANSFORMATION_PATTERNS = [
    # (regex, task_type, transformer function)
    {
        "keywords": ["add", "implement", "create", "build", "introduce"],
        "task_type": "add_feature",
        "template": "Write a test for the new behavior of {entity}, then implement until the test passes",
        "plan": [
            "1. Write a failing test that captures the desired {entity} behavior",
            "2. Implement minimum code to make the test pass",
            "3. Verify all tests still pass (regression)"
        ]
    },
    {
        "keywords": ["fix", "debug", "resolve", "repair", "patch"],
        "task_type": "fix_bug",
        "template": "Write a test that reproduces the bug in {entity}, then fix until the test passes",
        "plan": [
            "1. Write a test that reproduces the failure mode",
            "2. Verify test fails (confirming bug)",
            "3. Fix the underlying cause",
            "4. Verify test passes"
        ]
    },
    {
        "keywords": ["refactor", "improve", "optimize", "clean up", "restructure"],
        "task_type": "refactor",
        "template": "Ensure existing tests pass, refactor {entity}, verify tests still pass",
        "plan": [
            "1. Run existing tests (baseline)",
            "2. Add tests if coverage missing",
            "3. Refactor without changing behavior",
            "4. Verify all tests pass post-refactor"
        ]
    },
    {
        "keywords": ["verify", "validate", "check", "ensure", "confirm"],
        "task_type": "verify",
        "template": "Define explicit verification criteria for {entity}, write the check, ensure satisfied",
        "plan": [
            "1. Define what 'verified' means (pass condition)",
            "2. Write the check (assertion or test)",
            "3. Run the check",
            "4. If fails, identify root cause"
        ]
    },
    {
        "keywords": ["analyze", "investigate", "study", "examine"],
        "task_type": "analyze",
        "template": "Define hypothesis or question about {entity}, gather evidence, conclude with verdict",
        "plan": [
            "1. State the hypothesis or question explicitly",
            "2. Gather evidence (data, metrics, observations)",
            "3. Apply verification (statistical or logical)",
            "4. Conclude with confidence level"
        ]
    },
    {
        "keywords": ["document", "write", "explain", "describe"],
        "task_type": "documentation",
        "template": "Define the audience and questions to answer about {entity}, write content, verify covered",
        "plan": [
            "1. Define target audience and the questions they need answered",
            "2. Write content addressing each question",
            "3. Self-check: are all questions answered? Is anything missing?"
        ]
    }
]


# ============================================================
# Core Transformer
# ============================================================

def transform_task(imperative_text):
    """
    Imperative task description -> goal-driven structure.

    Args:
        imperative_text: original task description (from user or Prompt Architect output)

    Returns: {
        "original": str,
        "task_type": str | "unknown",
        "transformed_goal": str,
        "plan": list of step strings,
        "success_criteria": list of criterion dicts (Goal-Driven Executor input),
        "transformation_confidence": float (0-1),
        "rationale": str
    }
    """
    text_lower = imperative_text.lower()

    # 1. Find the best-matching pattern
    matched = None
    matched_keyword = None
    for pattern in TRANSFORMATION_PATTERNS:
        for kw in pattern["keywords"]:
            if re.search(rf'\b{re.escape(kw)}\b', text_lower):
                matched = pattern
                matched_keyword = kw
                break
        if matched:
            break

    if not matched:
        return {
            "original": imperative_text,
            "task_type": "unknown",
            "transformed_goal": imperative_text,  # no transformation
            "plan": ["1. Execute task as specified"],
            "success_criteria": [{
                "criterion_id": "SC_GENERIC",
                "description": "Task completed as specified",
                "verification_method": "manual_check"
            }],
            "transformation_confidence": 0.2,
            "rationale": "No matching transformation pattern. Defaulting to generic execution."
        }

    # 2. Extract entity (simple: first noun phrase after the keyword)
    entity = _extract_entity(imperative_text, matched_keyword)

    # 3. Fill in the template
    transformed_goal = matched["template"].replace("{entity}", entity)
    plan = [step.replace("{entity}", entity) for step in matched["plan"]]

    # 4. Generate success criteria (per task_type)
    criteria = _generate_criteria(matched["task_type"], entity, plan)

    return {
        "original": imperative_text,
        "task_type": matched["task_type"],
        "transformed_goal": transformed_goal,
        "plan": plan,
        "success_criteria": criteria,
        "transformation_confidence": _confidence(matched_keyword, entity),
        "rationale": f"Matched pattern '{matched['task_type']}' via keyword '{matched_keyword}'. Entity: '{entity}'."
    }


def _extract_entity(text, keyword):
    """Extract the first noun phrase after the keyword (simple heuristic)."""
    pattern = re.compile(rf'\b{re.escape(keyword)}\b\s+([A-Za-z0-9_\-\.\s가-힣]{{1,40}})',
                          re.IGNORECASE)
    m = pattern.search(text)
    if m:
        entity = m.group(1).strip().rstrip(".,!?")
        # If too long, keep only the first 5 words
        words = entity.split()
        return " ".join(words[:5])
    # fallback
    return "the requested change"


def _generate_criteria(task_type, entity, plan):
    """Generate verification criteria per task_type."""
    if task_type == "add_feature":
        return [{
            "criterion_id": "SC_TEST_PASS",
            "description": f"Tests for {entity} all pass",
            "verification_method": "automated_test"
        }, {
            "criterion_id": "SC_NO_REGRESSION",
            "description": "Existing tests still pass",
            "verification_method": "automated_test"
        }]
    if task_type == "fix_bug":
        return [{
            "criterion_id": "SC_BUG_REPRO_TEST",
            "description": f"Test reproducing the bug in {entity} now passes",
            "verification_method": "automated_test"
        }, {
            "criterion_id": "SC_NO_REGRESSION",
            "description": "Existing tests still pass",
            "verification_method": "automated_test"
        }]
    if task_type == "refactor":
        return [{
            "criterion_id": "SC_BEHAVIOR_PRESERVED",
            "description": f"All tests pass before and after refactoring {entity}",
            "verification_method": "automated_test"
        }, {
            "criterion_id": "SC_LINES_REDUCED",
            "description": "Total LOC not increased (preferably reduced)",
            "verification_method": "metric_threshold",
            "metric_path": "loc_delta",
            "threshold": 0  # <= 0 means same or reduced
        }]
    if task_type == "verify":
        return [{
            "criterion_id": "SC_CHECK_DEFINED",
            "description": f"Explicit verification check for {entity} exists",
            "verification_method": "file_exists"
        }, {
            "criterion_id": "SC_CHECK_PASSES",
            "description": "The check passes",
            "verification_method": "automated_test"
        }]
    if task_type == "analyze":
        return [{
            "criterion_id": "SC_HYPOTHESIS_STATED",
            "description": f"Hypothesis or question about {entity} stated",
            "verification_method": "regex_match",
            "pattern": r"(hypothesis|question|claim)"
        }, {
            "criterion_id": "SC_EVIDENCE_GATHERED",
            "description": "Evidence and verdict provided with confidence level",
            "verification_method": "regex_match",
            "pattern": r"(confidence|verdict|conclusion)"
        }]
    if task_type == "documentation":
        return [{
            "criterion_id": "SC_AUDIENCE_DEFINED",
            "description": "Target audience is defined",
            "verification_method": "regex_match",
            "pattern": r"(audience|reader|target)"
        }, {
            "criterion_id": "SC_COMPLETE",
            "description": "All defined questions answered",
            "verification_method": "manual_check"
        }]
    # default
    return [{
        "criterion_id": "SC_GENERIC",
        "description": "Task completed as specified",
        "verification_method": "manual_check"
    }]


def _confidence(keyword, entity):
    """Estimate transformation confidence."""
    base = 0.7  # baseline when keyword matches
    if entity != "the requested change":
        base += 0.15
    if len(entity.split()) >= 2:
        base += 0.05
    return min(1.0, base)


# ============================================================
# Batch transformation (for PM integration)
# ============================================================

def transform_pm_plan_tasks(pm_plan):
    """
    Transform every task in pm_plan.task_decomposition.

    Works in-place or as a copy. This function copies the plan and
    returns the new one.

    Returns: updated pm_plan (with transformed_tasks added).
    """
    if not isinstance(pm_plan, dict):
        return pm_plan
    tasks = pm_plan.get("task_decomposition", [])
    transformed = []
    for task in tasks:
        desc = task.get("description", "")
        if not desc:
            transformed.append({**task, "transformation": None})
            continue
        result = transform_task(desc)
        transformed.append({**task, "transformation": result})
    pm_plan = {**pm_plan, "task_decomposition_with_transformations": transformed}
    pm_plan["transformation_applied_at"] = now_iso()
    return pm_plan


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MAS Test-First Task Transformer Self-Test")
    print("=" * 60)

    test_cases = [
        "Add validation for email inputs",
        "Fix the bug in payment processing",
        "Refactor the authentication module",
        "Verify the calculation is correct",
        "Analyze Q3 financial trends",
        "Document the API endpoints",
        "Make it work somehow"  # unknown
    ]

    for i, tc in enumerate(test_cases, 1):
        print(f"\n[Case {i}] {tc!r}")
        result = transform_task(tc)
        print(f"  type: {result['task_type']}")
        print(f"  goal: {result['transformed_goal']}")
        print(f"  confidence: {result['transformation_confidence']}")
        print(f"  criteria: {len(result['success_criteria'])} criterion(a)")
        for c in result['success_criteria']:
            print(f"    - {c['criterion_id']}: {c['description'][:60]}...")
