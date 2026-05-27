---
name: karpathy-guidelines
description: "Lightweight coding skill — Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution. Inject into Worker prompts for coding tasks. Triggers: coding, refactor, debug, validation, test-first."
---

## Output Language Policy
<output_language_policy>
- Internal processing: English.
- User-facing output: Korean by default. Code identifiers stay in English. Switch to another language only on explicit user instruction.
</output_language_policy>

# Karpathy Guidelines — Lightweight Coding Skill

## Position
<system_overview>
Companion skill to `mas-orchestrator`. Injects 4 coding principles into the Worker prompt as a lightweight augmentation. Single-file, opt-in, not loaded for non-coding tasks.
</system_overview>

## 4 Principles
<core_principles>

### Principle 1: Think Before Coding
**Do not assume. Do not hide confusion. Surface trade-offs.**

Checklist:
- [ ] State assumptions explicitly.
- [ ] Offer multiple interpretations when ambiguous.
- [ ] Push back when a simpler approach exists.
- [ ] Stop and ask when confused.

MAS integration: mandatory `<thinking>` + Adversarial Critic.

### Principle 2: Simplicity First
**Minimum code that solves the problem. Nothing speculative.**

Checklist:
- [ ] No features beyond the request.
- [ ] No abstractions on single-use code.
- [ ] No flexibility or configuration that was not requested.
- [ ] No error handling for impossible scenarios.
- [ ] If a 50-line solution exists for a 200-line draft, rewrite.

**Senior Engineer Test**: "Would a senior engineer call this overcomplicated?" If yes, simplify.

MAS integration: Token Budget + Polisher conciseness + Verifier `senior_engineer_test` dimension.

### Principle 3: Surgical Changes
**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- [ ] Do not "improve" adjacent code, comments, or formatting.
- [ ] Do not refactor things that are not broken.
- [ ] Match the existing style, even if you would do it differently.
- [ ] On unrelated dead code, mention only; do not delete.

If your change creates orphans:
- [ ] Remove only the unused imports / variables / functions you created.
- [ ] Existing dead code is removed only when explicitly requested.

**Test**: Is every changed line directly traceable to the user request?

MAS integration: Worker `surgical_change_check` + Verifier consistency dimension.

### Principle 4: Goal-Driven Execution
**Define success criteria. Loop until verified.**

Core insight: LLMs are good at looping until they meet specific goals. Provide success criteria, not step-by-step instructions.

Imperative -> Verifiable transformation:

| Instead of... | Transform to... |
|---|---|
| "Add validation" | "Write tests for invalid inputs, then make them pass" |
| "Fix the bug" | "Write a test that reproduces it, then make it pass" |
| "Refactor X" | "Ensure tests pass before and after" |

For multi-step tasks, write a brief plan:
```
1. [Step] -> verify: [check]
2. [Step] -> verify: [check]
3. [Step] -> verify: [check]
```

MAS integration:
- `scripts/test_first_transformer.py`: PM Step 3.7 auto-conversion.
- `scripts/goal_driven_executor.py`: Worker loop execution.
- `pm_plan.worker_pool.workers[i].execution_mode = "goal_driven"` opt-in.
</core_principles>

## Activation
<agent_activation_policy>

PM invokes this skill when:
- task type is in {coding, refactor, debugging, test-writing, code-review}.
- complexity is in {Moderate, Complex, Expert} (optional on Simple).
- The user explicitly invokes `/karpathy-guidelines`.

Skip:
- Natural-language reports, analysis, or documentation tasks without code output.
- Trivial typo fixes.
</agent_activation_policy>

## Worker Prompt Injection
<execution_protocol>

When PM spawns a Worker, inject the 4 principles into `system_context`:

```xml
<karpathy_guidelines>
1. Think Before Coding - state assumptions, push back, stop when confused.
2. Simplicity First - minimum code, no speculation, senior engineer test.
3. Surgical Changes - touch only what is traceable to the request.
4. Goal-Driven Execution - define success criteria, loop until verified.
</karpathy_guidelines>
```

Token cost: roughly 200 tokens (selective, coding tasks only).
</execution_protocol>

## Observability
<observability>
- Diffs contain only requested changes.
- Fewer rewrites caused by overcomplication.
- Clarifying questions appear before implementation, not after.
- Clean, minimal PRs without drive-by refactoring.
</observability>

## Token Efficiency
<token_efficiency_rules>
- Lazy load: coding tasks only.
- Selective injection: only the 4 principles (checklist body lives in the reference).
- Worker prompt addition: roughly 200 tokens.
- Cost control: opt-in via `pm_plan.worker_pool.workers[i].karpathy_guidelines_enabled`.
</token_efficiency_rules>

## Failure Modes
<failure_modes>
- Forcing Goal-Driven Mode on non-verifiable tasks is wrong; fall back to `execution_mode = "prescriptive"`.
- Test-First Transformation keyword matching can fail; skip conversion when confidence < 0.5.
- Senior Engineer Test is qualitative; Verifier also uses objective metrics (LOC, abstraction count).
</failure_modes>

## Trade-off Note
<trade_off_note>
These guidelines bias toward caution over speed. For trivial tasks (simple typo fixes, obvious one-liners), use judgment. Not every change needs the full rigor.
</trade_off_note>

## License
<attribution>
MIT.
</attribution>
