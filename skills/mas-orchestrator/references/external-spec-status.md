# External Spec Status

<external_spec_status>

Current assessment of every externally-owned spec this skill pins. The pin in
`meta.external_spec_pinned_versions` records what we RUN ON. This file records what upstream has
PUBLISHED and what we decided about the gap, so a reader does not have to re-derive the assessment
from a changelog.

Reviewed: 2026-08-08. Next review due: 2026-11-08 (quarterly, or on any `evolution_review` trigger).

## MCP

| field | value |
|---|---|
| pinned (what we run on) | `2025-11-25` |
| latest published | `2026-07-28` (confirmed revision, not a release candidate) |
| classification | **MAJOR / breaking** |
| decision | **WAIT** |
| adopt not before | 2027-01-28 |

Decision basis is this skill's own rule, not a preference: External Spec Lifecycle Policy classifies
a breaking change as `GATE: external_spec_breaking_change -> rollback / migrate / wait` and sets a
6-month stability window before adopting a new spec. 2026-07-28 plus six months is 2027-01-28.
Upstream's own deprecation window for the removed features is a minimum of 12 months, so waiting
costs no compatibility.

What changes when we do adopt:
- **Stateless core.** Protocol-level sessions and the `Mcp-Session-Id` header are gone (SEP-2567), as
  is the `initialize` / `notifications/initialized` handshake (SEP-2575). Every request carries
  `protocolVersion` and client capabilities in `_meta`. Cross-call state moves to server-issued
  handles passed as ordinary tool arguments.
- **Tasks left the core** for the `io.modelcontextprotocol/tasks` extension (SEP-2663). Blocking
  `tasks/result` is replaced by `tasks/get` polling, `tasks/update` is added, `tasks/list` is removed.
  This is the one that touches us: `state/async_tasks.json` models a task lifecycle with a
  `mcp_spec_version` field. Our `input_required` state already matches the direction upstream took
  with MRTR (SEP-2322), so the async model migrates rather than gets rebuilt.
- **`server/discover`** becomes a MUST-implement RPC for capability advertisement.
- **Caching becomes part of the contract**: `ttlMs` and `cacheScope` are required on list/read
  results (SEP-2549), and `tools/list` SHOULD be deterministically ordered.

Do not adopt now, in either direction:
- **Roots, Sampling, Logging are deprecated** (SEP-2577). New code must not take a dependency on
  them. Replacements: Roots becomes a tool parameter or resource URI, Sampling becomes a direct LLM
  provider call, Logging becomes stderr (stdio) or OpenTelemetry.
- **HTTP+SSE transport** is reclassified as deprecated.

Not affected by this revision: the MCP Registry search path (`search_plugins` /
`search_mcp_registry`) the Worker uses to find a skill. That is a registry API, not the transport spec.

## Anthropic Memory

Pinned `managed-agents-2026-04-01`. Not reassessed this round; carried forward unchanged.

## Anthropic Skills

Pinned `skills-2025-10-02`. Not reassessed this round; carried forward unchanged.

</external_spec_status>
