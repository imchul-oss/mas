#!/usr/bin/env python3
"""
GEPA-style reflective prompt optimizer (Genetic-Pareto)
=======================================================

Evolves an agent prompt by reflecting on its eval traces and keeping a
**Pareto front** of candidates over multiple objectives (e.g. quality up,
cost down) instead of greedily chasing one metric — which avoids the local
optima a single-objective optimizer falls into.

Ref: Agrawal et al., "GEPA: Reflective Prompt Evolution" (arXiv:2507.19457,
ICLR 2026 Oral) — beats RL (GRPO) with ~35x fewer rollouts.

This module is the deterministic ENGINE (Pareto maintenance, candidate
selection, the evolve loop). The two expensive, model-driven steps are
injected callbacks, exactly like skillopt_adapter / reflexion_full_stack:

    evaluate(prompt) -> {"quality": float (higher better),
                         "cost": float  (lower better)}
        Run the prompt against the eval set (see eval/scorer.py) and return
        its aggregate metrics.

    reflect_mutate(prompt, eval_result) -> new_prompt:str
        An LLM reflects in natural language on the eval_result and proposes
        an improved prompt. (Default is a placeholder — wire a Claude call.)

Defaults are deliberate placeholders so the engine is testable without an
LLM. The optimizer is meant to run OFFLINE against eval/ — never in the hot
path — and only ships a change if a candidate dominates the baseline.

Usage:
    python gepa_optimizer.py          # built-in self-check demo
"""

import json
import sys

OBJECTIVES = ("quality", "cost")  # quality: maximize, cost: minimize


def _as_vector(scores):
    """Map scores to a vector where bigger is always better (negate cost)."""
    return (scores.get("quality", 0.0), -scores.get("cost", 0.0))


def dominates(a_scores, b_scores):
    """True if a Pareto-dominates b: >= on all objectives, > on at least one."""
    av, bv = _as_vector(a_scores), _as_vector(b_scores)
    return all(x >= y for x, y in zip(av, bv)) and any(x > y for x, y in zip(av, bv))


def pareto_front(candidates):
    """Return the non-dominated subset of candidates (each: {scores, ...})."""
    front = []
    for c in candidates:
        if any(dominates(o["scores"], c["scores"]) for o in candidates if o is not c):
            continue
        front.append(c)
    return front


def _default_reflect_mutate(prompt, eval_result):
    """Placeholder: a real impl asks an LLM to rewrite `prompt` given eval_result."""
    return prompt + "\n# (reflect: no mutation — wire an LLM callback)"


def optimize(seed_prompt, evaluate, reflect_mutate=None, iterations=6):
    """Evolve seed_prompt. Returns {best, front, history}.

    best = the front candidate with the highest quality (ties broken by lower
    cost). Only adopt it downstream if it dominates the seed (caller's call).
    """
    reflect_mutate = reflect_mutate or _default_reflect_mutate
    seed = {"prompt": seed_prompt, "scores": evaluate(seed_prompt),
            "parent": None, "gen": 0}
    population = [seed]
    history = [{"gen": 0, "scores": seed["scores"]}]

    for i in range(1, iterations + 1):
        front = pareto_front(population)
        # Round-robin over the Pareto front so exploration spreads across it.
        parent = front[(i - 1) % len(front)]
        child_prompt = reflect_mutate(parent["prompt"], parent["scores"])
        child = {"prompt": child_prompt, "scores": evaluate(child_prompt),
                 "parent": parent.get("gen"), "gen": i}
        population.append(child)
        history.append({"gen": i, "scores": child["scores"]})

    front = pareto_front(population)
    best = max(front, key=lambda c: (c["scores"].get("quality", 0.0),
                                     -c["scores"].get("cost", 0.0)))
    return {
        "best": best,
        "best_dominates_seed": dominates(best["scores"], seed["scores"]),
        "front_size": len(front),
        "front": [{"gen": c["gen"], "scores": c["scores"]} for c in front],
        "history": history,
    }


def _demo():
    """Self-check: a toy fitness landscape the engine should climb."""
    # Fitness: quality = count of 'WIN'; cost = prompt length (kept flat).
    # reflect_mutate flips one 'BAD' -> 'WIN' (same length), so a better
    # prompt genuinely DOMINATES the seed (higher quality, no extra cost).
    def evaluate(p):
        return {"quality": float(p.count("WIN")), "cost": float(len(p))}

    def reflect_mutate(p, _):
        return p.replace("BAD", "WIN", 1)

    result = optimize("BAD BAD BAD", evaluate, reflect_mutate, iterations=5)
    assert result["best"]["scores"]["quality"] >= 1.0, result
    assert result["best_dominates_seed"] is True, result

    # Pareto sanity: a high-quality/high-cost point and a low/low point should
    # both survive (neither dominates the other).
    cands = [
        {"scores": {"quality": 5, "cost": 9}},   # great but pricey
        {"scores": {"quality": 1, "cost": 1}},   # cheap but weak
        {"scores": {"quality": 3, "cost": 9}},   # dominated by the first
    ]
    front = pareto_front(cands)
    assert len(front) == 2, front
    print(json.dumps({"best": result["best"]["scores"],
                      "dominates_seed": result["best_dominates_seed"],
                      "front_size": result["front_size"]}, indent=2))
    print("\n[demo] self-check passed")


if __name__ == "__main__":
    _demo() if len(sys.argv) < 2 else print("Provide a driver; this module is a library + demo.")
