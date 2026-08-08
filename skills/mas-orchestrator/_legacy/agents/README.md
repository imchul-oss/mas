# Retired agent definitions (2026-08-09, v3.0.0)

Six of the original eight roles were removed from the contract. They are kept here rather than
deleted because the reason for removal is a measurement, and a measurement can be overturned.

**Why they went.** The eval programme finished on 2026-08-09. The full ten-agent Complex-tier
configuration was run once against the pair on the case most favourable to it: 14.13x the tokens, a
lower score, and a false claim shipped at Established grade that its own Adversarial Critic had
caught. The pair was then run against a single agent across three cases at n=3-4 judges per
condition: it did not win on the mean in any of them. None of these six roles had ever beaten a
single-agent baseline on `eval/`, which SKILL.md guardrail 11 has required since v2.0.0.

**What was measured to work, and where it went.** Two things earned their keep and were folded into
the two remaining roles rather than lost:

- The Watchdog Pool, given PARTITIONED AXES, returned disjoint real defects over one 45-source
  document - 11 sources written off as unverifiable that were real (6 of them Tier A), a benchmark
  baseline band mis-transcribed in three places, and three source pairs cited as independent that
  were one lab, one author group and one benchmark lineage. That is now an option inside
  `agents/verifier.md`: when an artifact is too large for one re-derivation pass, name the axes and
  run them separately. It is a way of reading, not a second agent.
- The Researcher's discipline - collect before writing, record what each source establishes, declare
  coverage gaps rather than filling them - is now stated in `agents/worker.md`.

**What would bring one back.** Each definition still carries the specific eval result that restores
it, written when the role was demoted to opt-in in v2.3.0. Those conditions stand. The Researcher is
the likeliest: it is the only removed role whose boundary changes what is SEEN rather than what is
asked, and it was never measured directly.

**What was NOT touched.** `scripts/state_manager.py` and its siblings still carry fields and helpers
named for these roles. Removing them would risk a 147-test suite for no measured benefit; unused
state keys are inert. The contract is what binds a session's behaviour, and the contract no longer
names them.
