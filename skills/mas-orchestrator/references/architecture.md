# MAS Architecture Reference

## System Architecture Overview
<protocol_definition>
Integrated 8-agent system with Context Architecture (XML tag convention).
</protocol_definition>

## Cost Structure (measured 2026-08-08)
<integration_note>

A sub-agent costs about **50,000 tokens of base context before it does any work**. Multiply that by
the activation policies below and the architecture has a floor per tier, independent of task size:

| tier | agents by spec | floor | vs one agent |
|---|---|---|---|
| Simple | 4 (PM, Researcher, Worker, Verifier - all always-active) | 200,000 | 4.0x |
| Moderate | 6 (+ Watchdog 1, Polisher) | 300,000 | 6.0x |
| Complex / Expert | 10 (+ Prompt Architect, Watchdog 3, Adversarial Critic) | 500,000 | 10.0x |
| Worker + Verifier pair | 2 | 100,000 | 2.0x |

Two things follow. The ~15x figure in the literature is a fair description of THIS architecture at
Complex, not an overstatement - the 1.83x-2.23x measured in `eval/` is the cost of the **pair**, which
is a configuration this document did not previously define. And there is no cheap tier: even Simple
costs 4x before any work, because PM and Researcher are unconditionally active.

### Design Principle 0: an agent boundary must change what is SEEN, not what is ASKED

This is the rule the cost floor forces. A different instruction is a section in a prompt and costs
nothing. A different context window costs 50,000 tokens. So a role earns a boundary only when it
sees material the previous agent did not.

| Role | What its boundary buys | Verdict |
|---|---|---|
| Verifier | The Worker's output read in fresh context | Earns it. Every measured MAS win came from here |
| Researcher | External material nobody else has read | Earns it in principle; unmeasured |
| Worker Pool (parallel) | A different sub-task each | Earns it when the sub-tasks are genuinely independent |
| Adversarial Critic | Fresh context, but over the same artifact the Verifier reads | Duplicates a role that is measured. Fold into the Verifier |
| Prompt Architect | The same request, restructured for the same model | Does not earn it |
| PM | The same request, plus a decision about activation | Does not earn a full boundary |
| Watchdog | Claims already present in the Researcher's output | Does not earn it, and a Pool of 3 reading identical material gives correlated votes |
| Polisher | The Worker's prose, to rewrite | Does not earn it; measured single-agent output needed no polish pass |

### Burden of proof (guardrail 11, applied to what already exists)

SKILL.md requires new complexity to beat a single-agent baseline on `eval/` before it ships. That
rule was never applied backwards, so six roles hold always-on or default-on status having never been
measured. Default-on for an unmeasured role inverts the burden the guardrail sets. The activation
policies were therefore moved to opt-in with a named trigger. **This is not a claim that those roles
do not work** - it is the same rule the guardrail already states, applied to incumbents. Each role's
definition now names the measurement that restores its default.

The decisive experiment, unrun: one Complex case executed twice, full 10-agent spec versus the pair,
same task and same rubric. That is the only test that separates "the pipeline raises the ceiling"
from "the pipeline raises the floor", and it costs about 600,000 tokens for one case.

### 1. Separation of Concerns
Each agent has a single, clear responsibility. Note the tension with Principle 0: separation of
concerns is free inside one context and costs 50,000 tokens across contexts, so it is a reason to
write separate SECTIONS, and only sometimes a reason to spawn separate AGENTS.

| Agent | Single Responsibility | Never Does |
|---|---|---|
| Prompt Architect | Prompt optimization + XML tag wrapping | Direct task execution |
| PM | Process and Worker Pool design + activation decisions | Information collection / task execution |
| Researcher | Information collection + Memory API + dynamic Tier | Fact verification / task execution |
| Watchdog (Pool) | Fact verdicts (TRUE / FALSE) | Information collection / quality scoring |
| Worker (Pool) | Task execution + skill delegation + handoff | Process design / verification |
| Adversarial Critic | Proactive adversarial verification (counter-scenarios) | Direct edits |
| Polisher | Linguistic polish (fact-preserving) | Altering facts or conclusions |
| Verifier | QA + 9-dim rubric | Direct edits |

### 2. State-based Communication
Agents do not communicate directly. They exchange asynchronous messages via `state/*.json`. Inter-agent review/debate/peer-review rounds live in `agent_messages.json`.

### 3. Verification-First Principle
```
Fact accuracy > Task completion > Process efficiency
```
Watchdog-FALSE information is unusable anywhere in the system (non-negotiable).

### 4. Continuous Learning
Worker -> `process_policy.json` accumulation. Additional persistent stores: `source_reliability`, `calibration`, `cost_routing_history`.

### 5. Bounded Feedback Loop
Maximum 3 iterations. Verifier decides convergence (Bayesian).

### 6. Context Architecture
All `agents/*.md`, `references/*.md`, `SKILL.md`, and Worker natural-language outputs use XML tags. `xml_parser.py` runs mechanical validation.
</integration_note>

## Execution Flow
<protocol_definition>

### Normal Flow
```
Phase 0: Init -> Phase 0.5: Complexity -> Phase 1: Prompt Architect (Complex/Expert)
  -> Phase 2: PM (Worker Pool + Watchdog Pool + Adversarial + Polisher decisions)
  -> Phase 3a: Researcher (Memory import, async)
  -> Phase 3b: Watchdog Pool (debate)
  -> Phase 3c: Worker Pool (handoff, schema, budget)
  -> Phase 3c.5: Adversarial Critic (Complex/Expert)
  -> Phase 3c.7: Polisher (Moderate+, fact-preserving)
  -> Phase 4: Verifier (9-dim rubric + xml_parser)
  -> Phase 5: Feedback loop (optional, with checkpoint rollback)
  -> Phase 6: Final + Memory export
```

### Federation Flow
```
FederationCoordinator (hub-spoke recommended)
  -> spawn instances (finance, legal, marketing, ...)
  -> route task by domain
  -> cross-MAS audit (one instance audits another)
  -> learning share (audited patterns broadcast)
```
</protocol_definition>

## Scalability
<integration_note>

### Horizontal (Worker Pool)
PM dynamically allocates 1 to 5 Workers. Independent tasks spawn in parallel.

### Watchdog Pool
For Complex/Expert, 3 parallel instances with majority consensus.

### Vertical (Skill Delegation)
Worker calls docx / pptx / xlsx / data:* skills directly.

### Cross-Session
`process_policy` / `worker_registry` / `skill_registry` / `agent_evolution` + `memory_index` + `source_reliability` + `calibration`.

### Federation
Multi-MAS instances (Hub-Spoke / Hierarchical / Peer-to-Peer / Swarm).
</integration_note>

## Security & Integrity
<integration_note>
- Watchdog verdicts are immutable (no other agent can change them).
- Every state mutation records a timestamp (audit trail).
- All factual claims require external verification.
- File lock + atomic write prevents races.
- Memory API usage is opt-in with PII filtering.
- Code outputs are scanned for dangerous patterns.
- XML tag orphans trigger self-correction.
</integration_note>
