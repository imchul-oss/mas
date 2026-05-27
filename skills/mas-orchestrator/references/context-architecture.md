# MAS Context Architecture Convention

**Doc Type**: Architecture Convention (Normative)

---

## 0. Position of This Document

This document is the constitution for the XML tag convention applied across the MAS document ecosystem: `agents/*.md`, `references/*.md`, `SKILL.md`, and `state/*.json` artifacts.

---

## 1. Two Integration Dimensions (MECE)

### Dimension A: Mandatory `<thinking>` in Agent Output (Prompt-level)
Every agent externalizes reasoning before answering:

```xml
<thinking>
   - Analysis step 1
   - Analysis step 2
   - Rationale for the conclusion
</thinking>

<answer>
   ... final deliverable ...
</answer>
```

**Activation Policy (Proportional Response)**:
- Simple: optional (the `<thinking>` block may be omitted).
- Moderate and above: mandatory.

### Dimension B: XML Tag Augmentation in the Document Ecosystem (Document-level)
Preserve markdown headers (human-readable) and add XML tags (machine-parseable). Hybrid approach.

```markdown
## Identity
<agent_identity>
- Role: ...
- KPI: ...
</agent_identity>

## Execution Protocol
<execution_protocol>
... protocol content ...
</execution_protocol>
```

**Principle**: XML tags follow the markdown header on the next line, wrap the entire section, and both are preserved.

---

## 2. Standard XML Tag Dictionary (Authoritative)

### 2.1 Agent Definition Files (`agents/*.md`)

| Tag | Meaning | Required |
|---|---|---|
| `<agent_identity>` | Role / KPI / Character | required |
| `<agent_activation_policy>` | Complexity activation | required (Complex/Expert) |
| `<knowledge_base>` | Knowledge and references | required |
| `<execution_protocol>` | Step-by-step protocol | required |
| `<output_format>` | Output schema | required |
| `<token_efficiency_rules>` | Token-efficiency rules | required |
| `<failure_modes>` | Failure handling | required |
| `<feedback_integration>` | Feedback handling | required |
| `<non_negotiable_rules>` | Absolute rules | required (Watchdog / Adversarial) |
| `<evolution_notes>` | Evolution / version notes | optional |

### 2.2 SKILL.md

| Tag | Meaning |
|---|---|
| `<output_language_policy>` | Output language policy |
| `<system_overview>` | 8-agent overview |
| `<token_efficiency_protocol>` | Token efficiency principles |
| `<quality_guardrails>` | Quality guardrails |
| `<sub_agent_optimization>` | Model routing table |
| `<agent_architecture>` | Diagram and phase flow |
| `<execution_protocol>` | Phase 0 to 6 protocol |
| `<state_management>` | State / persistent directories |
| `<gate_definitions>` | Defined gate list |
| `<error_handling>` | Error handling |

### 2.3 References (`references/*.md`)

| Tag | Meaning |
|---|---|
| `<protocol_definition>` | Channel definitions |
| `<state_schema>` | JSON schemas |
| `<evolution_policy_section>` | Evolution policy section |
| `<integration_note>` | Integration guide |

### 2.4 Worker Output (Natural-language)

```xml
<thinking>
[Worker reasoning steps before producing the answer]
</thinking>

<answer>
[Final output - alongside JSON when a schema applies, otherwise standalone markdown]
</answer>

<source_citations>
- [Source 1] ...
- [Source 2] ...
</source_citations>

<uncertainty>
- [unverified] ...
- [estimated] ...
</uncertainty>
```

---

## 3. Verifier Dimension: `context_architecture_compliance`

Verifier adds a 9th dimension to its quality_rubric:

```json
{
  "context_architecture_compliance": {
    "score": "1-5",
    "criteria": "XML tag convention compliance across agents/*.md and outputs",
    "checks": {
      "required_tags_present": true,
      "thinking_tag_used": true,
      "tag_pairing_balanced": true,
      "no_orphan_tags": true,
      "machine_parseable": true
    },
    "findings": []
  }
}
```

Evaluation method:
- Call `xml_parser.parse_agent_definition(file_path)`.
- Check that every required tag listed in 2.1 is present.
- Check that every opening tag has a matching closing tag.
- Check that Worker output separates `<thinking>` and `<answer>`.

---

## 4. Migration Strategy (Incremental)

```
Phase 1 (immediate): SKILL.md + canonical agent (prompt-architect.md)
   -> 5-session validation
Phase 2: core agents (pm-orchestrator, watchdog, verifier)
   -> 5-session validation
Phase 3: remaining agents (researcher, worker, adversarial-critic, polisher)
   -> 5-session validation
Phase 4: all references/*.md
```

Each phase requires a self-audit verdict of CONDITIONAL_PASS or higher before proceeding.

---

## 5. Token Cost Mitigation

1. Lazy load: `agents/*.md` is loaded only when its phase is entered.
2. Selective tagging: section-level wrapping only, never paragraph-level.
3. Cost-aware routing: dynamic sonnet / opus selection offsets cost.
4. Token Budget Enforcement: per-Worker budget cap.

With lazy load + selective tagging + cost routing, net XML tag overhead trends to zero or negative.

---

## 6. Honest Trade-offs

| Trade-off | Mitigation |
|---|---|
| Reduced readability for non-developers | Markdown headers preserved (hybrid) |
| Token cost overhead | See section 5 |
| Maintenance burden (headers + tags) | Automated with `xml_parser` lint |
| Mixed adoption (tagged vs. untagged files) | Incremental migration per section 4 |

---

## Conclusion

`<thinking>` enforcement (Dimension A) + document-ecosystem XML tags (Dimension B) jointly improve MAS machine-parseability and agent reasoning quality. Incremental migration controls the risk.
