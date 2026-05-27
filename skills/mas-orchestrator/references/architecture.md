# MAS Architecture Reference

## System Architecture Overview
<protocol_definition>
Integrated 8-agent system with Context Architecture (XML tag convention).
</protocol_definition>

## Design Principles
<integration_note>

### 1. Separation of Concerns
Each agent has a single, clear responsibility.

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
