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

### The decisive experiment, RUN 2026-08-08

`research-2` executed three ways, same task and rubric. It was chosen as the case most favourable to
the pipeline: it is the one case the 2026-06-28 run scored `mas_worth_it`, and it needs external
material, parallel decomposition and evidence grading, so Researcher, Watchdog Pool and Critic all
have their best case.

| arm | agents | tokens | vs single | score |
|---|---|---|---|---|
| single | 1 | 88,735 | 1.00x | 4.4 |
| pair (Worker + Verifier) | 2 | 184,175 | 2.08x | **4.8** |
| full Complex spec | 10 | 1,253,663 | **14.13x** | 4.1 |

**The full spec cost 6.81x the pair and scored lower.** It also did not converge: its own Verifier
returned CONDITIONAL_PASS 3.22/5 with a blocking defect, so reaching a shippable artifact needs a
Phase 5 iteration on top of the 1.25M already spent. The ~15x from the literature is confirmed for
this architecture, and the 2.0x floor arithmetic above understates a working pipeline by about 2.4x,
because agents doing real work exceed their base context.

### Two corrections this experiment forced

**1. Design Principle 0 was too strong, and the Watchdog Pool disproved it.** The claim was that three
agents over one document give correlated votes. Given PARTITIONED AXES - citation existence, numeric
provenance, source independence - the three produced disjoint and real defect sets: 11 sources the
Researcher had written off as unverifiable were real and 6 were Tier A; a benchmark's baseline band
was mis-transcribed in three places; three pairs of sources cited as independent were one lab, one
author group, and one benchmark lineage. So the principle is about ATTENTION, not only material: a
boundary earns its cost when the agent's attention covers ground the previous agent's attention could
not, and an artifact can be too large for one agent to hold three axes over at once. Same material
plus a genuinely different axis is a boundary; same material plus a different tone is not.

**2. The pipeline's defect is not its agents, it is that findings have no path to the artifact.**
The Watchdog Pool's corrections did land, because Phase 3c reads them and the Worker is the author.
The Critic's did not. It correctly identified a false claim - the deliverable states SAFE's twelve
authors are all Google DeepMind, graded Established - and nothing downstream can act on it: the
Verifier "makes no direct edits" and the Polisher "never alters facts". So the artifact shipped the
false claim at Established grade while its own `self_report` recorded
`watchdog_false_verdicts_propagated: 0`. Depth was purchased and then discarded between 3c.5 and
delivery. **Any phase that produces findings after the last agent able to edit the artifact is
speculative work**, and that ordering defect is worth more than any activation-policy change in this
document.

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
| Adversarial Critic | Proactive adversarial verification (counter-scenarios) | Direct edits - its findings route to the Verifier, which applies them |
| Polisher | Linguistic polish (fact-preserving), Phase 4.5 after corrections land | Altering facts or conclusions |
| Verifier | QA + 9-dim rubric, **and authorship of the corrected final artifact** | Inventing content the evidence base does not carry |

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
Phase 0: Init -> Phase 0.5: Complexity -> Phase 1: Prompt Architect (Expert, on trigger)
  -> Phase 2: PM (light by default)
  -> Phase 3a: Researcher (on trigger; Memory import, async)
  -> Phase 3b: Watchdog Pool (on trigger; one named AXIS per instance)
  -> Phase 3c: Worker Pool (handoff, schema, budget)
  -> Phase 3c.5: Adversarial Critic (on trigger)
  -> Phase 4: Verifier - re-derivation, applies Critic and Watchdog findings,
              AUTHORS the corrected final artifact
  -> Phase 4.5: Polisher (on trigger, fact-preserving, after corrections land)
  -> Phase 5: Feedback loop (optional, with checkpoint rollback)
  -> Phase 6: Final + Memory export
```

**Authorship rule.** Every findings-producing phase must have an author downstream of it, or be one
itself. Polisher moved 3c.7 -> 4.5 under the same rule: polishing before corrections land polishes
the uncorrected artifact. This is the fix for the ordering defect measured on 2026-08-08, and it adds
no agent - it withdraws a constraint, which is why guardrail 11 does not require a fresh eval for it.
The pair arm, whose Verifier already authored its corrected output, is the configuration that scored
highest of the three.

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
