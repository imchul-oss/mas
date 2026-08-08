# Retired references (2026-08-09, v3.0.0)

Four documents left `references/` when the skill went from eight roles to two. Each described a
mechanism the contract no longer offers.

| file | what it specified | why it left |
|---|---|---|
| `protocols.md` | 15 inter-agent message channels over `state/*.json`, peer review rounds, debate | Two roles need one handoff, not a channel registry. Fourteen of the fifteen channels had no sender or no receiver |
| `c-integration-notes.md` | MCP Registry search as the PM's skill-discovery path | PM is retired. The Worker calls skills directly and does not need a discovery protocol between it and itself |
| `federation-architecture.md` | Multi-MAS federation, hub-spoke / hierarchical / peer-to-peer / swarm, cross-MAS audit | Federating an architecture that has not beaten one agent multiplies an unproven unit. It was specified, never measured, never used |
| `skillopt-integration.md` | SkillOpt prompt-optimisation loop wired to agent evolution | The evolution machinery it optimises belonged to the retired roles |

**Their scripts are still in `scripts/`.** `multi_mas_federation.py` (30 KB) and `skillopt_adapter.py`
(15 KB) remain, with their tests inside the 147-test suite. That is the same line drawn when the six
agent definitions were retired: remove from the contract, leave the machinery, because ripping out
tested code buys nothing measurable and risks the suite. The consequence is stated rather than hidden
- those two scripts are now documented only here, which makes them the obvious candidates for a
removal pass if nothing calls them by the next review.

**What did NOT leave, and why.** `architecture.md`, `context-architecture.md` (the tag convention
`xml_parser.py` enforces), `karpathy-guidelines.md` (Worker-facing coding guidance),
`external-spec-status.md` and `upgrade-assessment-2026-08.md` are live. `evolution-policy.md`,
`skill-catalog.md` and `state-schema.md` were pruned in place rather than retired, because each holds
a live section inside a mostly-dead document.
