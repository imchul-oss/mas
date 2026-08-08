# Available Skill Catalog

## Overview
<integration_note>
This catalog is a **hint list, not an authority** - the harness's live Skill-tool list is the source of truth for what is actually installed, because a hand-maintained catalogue goes stale. The Worker consults it before delegating and pulls in only the one or two skills the task needs. Anthropic Agent Skills are integrated bidirectionally.
</integration_note>

## Document Creation Skills
<protocol_definition>

### docx
- Trigger: Word documents, reports, memos, letters.
- Worker usage: reports, proposals, policy docs.

### pptx
- Trigger: presentations, slide decks, pitch decks.
- Worker usage: strategy talks, business plans, training material.

### xlsx
- Trigger: spreadsheets, data tables, budgets, financial models.
- Worker usage: data wrangling, financial analysis, KPI dashboards.

### pdf
- Trigger: PDF read / generate / merge / split, form filling.
- Worker usage: PDF reports, form filling, document merging.
</protocol_definition>

## Data & Analysis Skills
<protocol_definition>

### data:analyze / data:explore-data / data:create-viz / data:build-dashboard / data:statistical-analysis / data:write-query / data:sql-queries / data:validate-data
- Researcher: augment information collection (`data:analyze`, `data:statistical-analysis`).
- Worker: analysis, visualization, dashboards.
- Verifier: `data:validate-data`.
</protocol_definition>

## Operations Skills
<protocol_definition>
operations:status-report / risk-assessment / process-doc / process-optimization / compliance-tracking / vendor-review / capacity-plan / change-request / runbook.
</protocol_definition>

## Brand & Content Skills
<protocol_definition>
- `brand-voice:brand-voice-enforcement` (integrates with Polisher).
- `brand-voice:guideline-generation` / `discover-brand`.
</protocol_definition>

## Anthropic Agent Skills
<integration_note>
Query the Anthropic Skills API when the local catalogue has no match.
- Built-in: PowerPoint, Excel, Word, PDF.
- User-defined skills are supported.
</integration_note>

## Worker Usage

**Pruned 2026-08-09 (v3.0.0).** The removed half was a skill-DISCOVERY protocol for the PM: search
order, MCP registry fallback, keyword mapping. There is no PM, and a Worker searching for a skill on
behalf of itself is a lookup, not a protocol. What stays is the catalogue itself, which the Worker
reads to know what it can delegate to.

- `mcp__<prefix>__<tool>`: read is automatic.
- `mcp__<prefix>__<tool>`: write requires a user gate.
</protocol_definition>

## Context Architecture for Skill Calls
<integration_note>
Worker wraps natural-language output from skill calls as follows:
```xml
<thinking>
- Why this skill is appropriate
- Why it beats the alternatives
</thinking>

<answer>
[Integrated skill output]
</answer>

<source_citations>
- skill: <skill_name>
- input: <pm_plan reference>
</source_citations>
```
</integration_note>
