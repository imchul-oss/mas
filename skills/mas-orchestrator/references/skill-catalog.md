# Available Skill Catalog

## Overview
<integration_note>
This catalog is a **hint list, not an authority** — the harness's live Skill-tool list is the source of truth for what's actually installed (a hand-maintained catalog goes stale). PM consults it during Phase 2 skill mapping and injects only the 1-2 relevant skills per agent (selective injection — agents do not each search). Worker invokes skills during Phase 3c execution. Anthropic Agent Skills are integrated bidirectionally.
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
PM Step 2.4 queries the Anthropic Skills API.
- Built-in: PowerPoint, Excel, Word, PDF.
- User-defined skills are supported.
</integration_note>

## Skill Selection Guide for PM
<integration_note>

| Task | Primary | Alternative |
|---|---|---|
| Report | docx | pdf, md |
| Presentation | pptx | html (React artifact) |
| Data analysis | data:analyze | data:statistical-analysis |
| Visualization | data:create-viz | data:build-dashboard |
| Risk analysis | operations:risk-assessment | direct analysis |
| Data table | xlsx | data:write-query |
| Brand content | brand-voice:brand-voice-enforcement | direct authoring |

### Search Order (when no skill matches)
1. Check this catalog.
2. `search_plugins` (plugin marketplace).
3. MCP Registry first (`search_plugins_priority`).
4. `search_mcp_registry` fallback.
5. Anthropic Agent Skills.
6. Alternative design (basic tools only).
</integration_note>

## Plugin Discovery Protocol
<protocol_definition>

### Auto-Discovery Tools
| Tool | Purpose | When |
|---|---|---|
| `search_plugins` | Plugin marketplace | PM Step 2.2 |
| `suggest_plugin_install` | Suggest install for matched plugin | On match |
| `search_mcp_registry` | MCP connector | PM Step 2.3 |
| `suggest_connectors` | Suggest matched connector | On match |

### Discovery Keyword Mapping
- External comms: slack / teams / discord / messaging / chat
- Project management: jira / asana / linear / trello
- Design: figma / canva / design / graphic
- Documents: notion / confluence / google drive / sharepoint / box
- Data: snowflake / bigquery / databricks / database / analytics
- CRM: salesforce / hubspot / crm / sales
- Development: github / gitlab / jenkins / ci-cd / deployment
- Monitoring: datadog / pagerduty / opsgenie / monitoring

### Worker Usage
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
