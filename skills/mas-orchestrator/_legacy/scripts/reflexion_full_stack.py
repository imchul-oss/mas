"""
Reflexion Full Stack (Goal-Driven Mode enhancement)

Reflexion 3-component:
  Actor           -> MAS Worker (produces outputs)
  Evaluator       -> MAS Verifier (scores outputs)
  Self-Reflection -> this module (generates verbal feedback)

Goal-Driven Mode (goal_driven_executor.py) previously had _self_reflect()
that simply passed unmet criteria. This module upgrades it to verbal
reinforcement (LLM-style reasoning trace).

This module avoids direct LLM call dependency -- it is a structured
reflection prompt generator. The actual LLM call is handled by the caller
(Worker or Adversarial Critic).
"""

import json
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# Reflection Trace (episodic memory unit)
# ============================================================

class ReflectionTrace:
    """
    A single reflection history. The verbal feedback buffer.
    Used by the Worker as a prior in the next iteration.
    """

    def __init__(self):
        self.entries = []

    def add(self, iteration, unmet_criteria, what_worked, what_failed,
            root_cause_hypothesis, next_attempt_strategy):
        self.entries.append({
            "iteration": iteration,
            "unmet_criteria": unmet_criteria,
            "what_worked": what_worked,
            "what_failed": what_failed,
            "root_cause_hypothesis": root_cause_hypothesis,
            "next_attempt_strategy": next_attempt_strategy,
            "timestamp": now_iso()
        })

    def to_prompt(self):
        """
        XML structure to inject into the next iteration's Worker prompt.
        """
        if not self.entries:
            return ""
        lines = ["<reflection_trace>"]
        for e in self.entries:
            lines.append(f"  <iteration n=\"{e['iteration']}\">")
            lines.append(f"    <unmet_criteria>{', '.join(c.get('criterion_id','?') for c in e['unmet_criteria'])}</unmet_criteria>")
            if e['what_worked']:
                lines.append(f"    <what_worked>{e['what_worked']}</what_worked>")
            if e['what_failed']:
                lines.append(f"    <what_failed>{e['what_failed']}</what_failed>")
            if e['root_cause_hypothesis']:
                lines.append(f"    <root_cause>{e['root_cause_hypothesis']}</root_cause>")
            if e['next_attempt_strategy']:
                lines.append(f"    <next_strategy>{e['next_attempt_strategy']}</next_strategy>")
            lines.append("  </iteration>")
        lines.append("</reflection_trace>")
        return "\n".join(lines)


# ============================================================
# Reflection Prompt Generator
# ============================================================

REFLECTION_PROMPT_TEMPLATE = """
<reflection_task>
You are reflecting on a previous attempt to meet success criteria.
Analyze what happened and propose a concrete next strategy.

<previous_attempt>
{attempt_summary}
</previous_attempt>

<success_criteria>
{criteria_listing}
</success_criteria>

<verification_results>
{verification_results}
</verification_results>

<prior_reflections>
{prior_reflections}
</prior_reflections>

Respond ONLY in this exact structured format:

<reflection>
<what_worked>[1-2 sentences: which parts succeeded]</what_worked>
<what_failed>[1-2 sentences: which parts failed, specifically]</what_failed>
<root_cause>[1 sentence: root cause hypothesis (wrong assumption, missing info, tool misuse, etc.)]</root_cause>
<next_strategy>[1-2 sentences: concrete change to try in the next iteration. Format: "Change X to Y".]</next_strategy>
</reflection>

Do not generate code. Reflection only.
"""


def build_reflection_prompt(iteration, attempt_output, success_criteria,
                             verification_results, prior_traces=None):
    """
    Build a Reflexion-style reflection prompt.

    Args:
        iteration: current iteration number
        attempt_output: prior attempt output (summary)
        success_criteria: target criteria list
        verification_results: verification result per criterion
        prior_traces: optional previous ReflectionTrace

    Returns: prompt string (used by LLM caller)
    """
    attempt_summary = _summarize(attempt_output)
    criteria_listing = "\n".join(
        f"  - {c.get('criterion_id','?')}: {c.get('description','?')}"
        for c in success_criteria
    )
    verif_lines = []
    for v in verification_results:
        status = "passed" if v.get("passed") else "failed"
        verif_lines.append(f"  - {v.get('criterion_id','?')}: {status} "
                          f"(score: {v.get('score',0)}, feedback: {v.get('feedback','')[:80]})")
    verification_block = "\n".join(verif_lines)

    prior_block = ""
    if prior_traces and prior_traces.entries:
        prior_block = prior_traces.to_prompt()
    else:
        prior_block = "(no prior reflections)"

    return REFLECTION_PROMPT_TEMPLATE.format(
        attempt_summary=attempt_summary,
        criteria_listing=criteria_listing,
        verification_results=verification_block,
        prior_reflections=prior_block
    )


def parse_reflection_response(text):
    """
    Parse the <reflection> block from an LLM response.

    Returns: {"what_worked", "what_failed", "root_cause", "next_strategy"}
    None on parse failure -> caller handles fallback.
    """
    import re
    fields = ["what_worked", "what_failed", "root_cause", "next_strategy"]
    result = {}
    for f in fields:
        m = re.search(rf"<{f}>(.*?)</{f}>", text, re.DOTALL)
        result[f] = m.group(1).strip() if m else ""
    if not any(result.values()):
        return None
    return result


def _summarize(output):
    if isinstance(output, str):
        return output[:400]
    if isinstance(output, dict):
        return json.dumps({k: (v if not isinstance(v, dict) else "<...>")
                           for k, v in list(output.items())[:5]},
                          ensure_ascii=False)[:400]
    return str(output)[:400]


# ============================================================
# Integration with Goal-Driven Executor
# ============================================================

class ReflexionEnhancedSelfReflect:
    """
    Replacement for GoalDrivenExecutor._self_reflect().

    Takes an LLM call callback, performs verbal reflection, accumulates the
    ReflectionTrace, and injects it into the Worker prompt.

    Usage:
        from goal_driven_executor import GoalDrivenExecutor
        from reflexion_full_stack import ReflexionEnhancedSelfReflect

        reflector = ReflexionEnhancedSelfReflect(llm_callback=my_llm_call)
        executor = GoalDrivenExecutor(criteria, max_iterations=3,
                                       worker_runner=my_worker)
        executor._self_reflect = reflector.reflect  # monkey-patch
    """

    def __init__(self, llm_callback=None):
        """
        Args:
            llm_callback: callable(prompt) -> str (LLM response).
                          If None, simple fallback behavior is used.
        """
        self.llm_callback = llm_callback
        self.trace = ReflectionTrace()

    def reflect(self, output, unmet, iteration_num=None,
                success_criteria=None, all_verifications=None):
        """_self_reflect compatible signature + extension."""
        if not self.llm_callback or not success_criteria:
            # Fallback behavior
            return {
                "unmet_criteria_count": len(unmet),
                "feedback_for_next_iteration": [
                    {"criterion_id": v["criterion_id"], "feedback": v.get("feedback", "")}
                    for v in unmet
                ]
            }

        # Reflexion full stack
        prompt = build_reflection_prompt(
            iteration=iteration_num or len(self.trace.entries) + 1,
            attempt_output=output,
            success_criteria=success_criteria,
            verification_results=all_verifications or unmet,
            prior_traces=self.trace
        )
        try:
            response = self.llm_callback(prompt)
            parsed = parse_reflection_response(response)
            if parsed:
                self.trace.add(
                    iteration=iteration_num or len(self.trace.entries) + 1,
                    unmet_criteria=unmet,
                    what_worked=parsed["what_worked"],
                    what_failed=parsed["what_failed"],
                    root_cause_hypothesis=parsed["root_cause"],
                    next_attempt_strategy=parsed["next_strategy"]
                )
                return {
                    "unmet_criteria_count": len(unmet),
                    "verbal_reflection": parsed,
                    "trace_for_next_iteration": self.trace.to_prompt()
                }
        except Exception as e:
            return {
                "unmet_criteria_count": len(unmet),
                "reflection_error": str(e),
                "fallback": "simple_unmet_passing"
            }
        # Parse failure fallback
        return {
            "unmet_criteria_count": len(unmet),
            "parse_failed": True,
            "raw_response": response[:300]
        }


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Reflexion Full Stack")
    print("=" * 60)

    # Trace test
    trace = ReflectionTrace()
    trace.add(
        iteration=1,
        unmet_criteria=[{"criterion_id": "SC1"}],
        what_worked="data collection succeeded",
        what_failed="validation score 0.6 < 0.8 threshold",
        root_cause_hypothesis="missing edge case handling",
        next_attempt_strategy="add null/empty input handling"
    )
    print("\n[Trace XML prompt]:")
    print(trace.to_prompt())

    # Prompt builder test
    print("\n[Reflection prompt]:")
    prompt = build_reflection_prompt(
        iteration=2,
        attempt_output={"result": "partial output", "score": 0.6},
        success_criteria=[{"criterion_id": "SC1", "description": "score >= 0.8"}],
        verification_results=[{"criterion_id": "SC1", "passed": False,
                                "score": 0.6, "feedback": "below threshold"}],
        prior_traces=trace
    )
    print(prompt[:600])

    # Parse test
    sample_response = """
    <reflection>
    <what_worked>core logic works correctly</what_worked>
    <what_failed>score drops on some inputs due to missing exception handling</what_failed>
    <root_cause>edge case assumption was missing</root_cause>
    <next_strategy>add guards that handle null, empty, and boundary inputs</next_strategy>
    </reflection>
    """
    parsed = parse_reflection_response(sample_response)
    print(f"\n[Parsed]: {parsed}")

    print("\n" + "=" * 60)
    print("Demo complete.")
