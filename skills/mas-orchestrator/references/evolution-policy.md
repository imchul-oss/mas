# Evolution Policy

<evolution_policy_section>
**Pruned 2026-08-09 (v3.0.0).** This document specified how eight roles evolved: per-agent evolution
sources, PM integration rules, Bayesian threshold updates, skill-versus-agent promotion gates, a
self-audit protocol and a roadmap. All of it governed roles that no longer exist, and none of it had
ever run. What remains below is the part that governs THIS skill's relationship to specs and state it
does not own. The removed sections are in `_legacy/references/README.md` only as a list; they were
not worth preserving in full, because unlike the agent definitions they described a process rather
than a measurement.
</evolution_policy_section>

## External Spec Lifecycle Policy
<evolution_policy_section>

### Spec Pinning
Explicit in `meta.external_spec_pinned_versions`. The pin records what we RUN ON, never what upstream
has most recently published; the gap between the two is assessed in `references/external-spec-status.md`
and carries a dated decision.

### Spec Change Detection
Detection is a **dated human review**, not an automatic check. Nothing in `scripts/` fetches an
upstream spec version, so a sentence here claiming a Phase 0 comparison would describe a step that
never runs - and the review it was meant to trigger went unheld from 2026-06-28 to 2026-08-08 while
MCP published a breaking revision. The review is quarterly, its outcome and next due date live in
`references/external-spec-status.md`, and any session that notices a version move may hold it early
and record the result there. A mismatch found by that review triggers `evolution_review`. Wiring an
automatic fetch is deferred on purpose: a network call inside a portable skill is a runtime
dependency this skill does not otherwise carry.

### Breaking Change Response
- Patch (compatible): auto-apply and update pin.
- Minor (compatible): review the change, then a user gate before adopting.
- Major (breaking): GATE: `external_spec_breaking_change` -> rollback / migrate / wait.

### Stability Window
Adopt a new spec only after a 6-month stability window. Beta specs require a fallback path.
</evolution_policy_section>

## Concurrency Safety Invariants
<evolution_policy_section>
- I1: Atomic state write (`tempfile` + `os.replace`).
- I2: Exclusive file lock (POSIX `fcntl` / Windows `msvcrt`).
- I3: Optimistic concurrency (`version` CAS).
- I4: Worker Pool synchronization (Phase 4 starts only after all Worker writes complete).
</evolution_policy_section>

## Context Architecture Policy
<evolution_policy_section>

### XML Tag Evolution Gate
Every change to `agents/*.md` must preserve:
- The standard tag dictionary (`context-architecture.md`).
- Markdown headers (hybrid).
- `xml_parser` lint passing.

### Auto-trigger
- `xml_parser compliance_score` average < 0.85 -> stop and fix before shipping the change.
- Frequent orphan tags -> fix the definition rather than the output.

### Scope
`SKILL.md`, `agents/worker.md`, `agents/verifier.md` and every live `references/*.md`. The staged
migration this section used to describe finished long ago and named roles that no longer exist.
</evolution_policy_section>
