# State File Schemas

## Which of these are live (2026-08-09, v3.0.0)

`worker_output.json`, `verifier_report.json`, `session_state.json` and `meta.json` are written on a
two-role run. `prompt_output.json`, `pm_plan.json`, `research_data.json`, `watchdog_verdicts.json`,
`watchdog_pool_verdicts.json`, `adversarial_report.json` and `polisher_report.json` belong to retired
roles and nothing writes them.

They are documented here anyway, deliberately. `state_manager.py` still defines and tests those
schemas, and documentation that lags the code is worse than documentation of code nobody calls. If
those helpers are ever removed, remove these sections in the same commit.

## Overview
<state_schema>
Common fields on every state file: `version` (int, incremented by 1), `timestamp` (ISO-8601), `thinking_trace` (string, agent outputs), `context_architecture_compliance` (object, self-check).
</state_schema>

## session_state.json
<state_schema>
```json
{
  "session_id": "YYYYMMDD_HHMMSS",
  "created_at": "ISO-8601",
  "task_description": "string",
  "status": "initialized | phase_N_name | completed | failed",
  "current_phase": "int",
  "iteration": "int",
  "max_iterations": "int",
  "complexity": "simple|moderate|complex|expert",
  "agents_status": {
    "prompt_architect": "", "pm_orchestrator": "", "researcher": "",
    "watchdog": "", "worker": "", "adversarial_critic": "",
    "polisher": "", "verifier": ""
  },
  "worker_pool_status": {},
  "watchdog_pool_status": {},
  "phase_history": [],
  "checkpoints": [],
  "async_tasks": []
}
```
</state_schema>

## prompt_output.json
<state_schema>
```json
{
  "version": "int", "timestamp": "ISO-8601",
  "thinking_trace": "string",
  "original_request": "string",
  "analysis": {
    "explicit_intent": "", "implicit_intent": "",
    "constraints": [], "ambiguities": [], "domain": "",
    "complexity_level": "simple|moderate|complex|expert",
    "required_knowledge": []
  },
  "strategy": {"primary": "", "secondary": [], "rationale": ""},
  "structured_prompt": {
    "system_context": "", "task_specification": "",
    "reasoning_framework": "", "quality_gates": "", "examples": []
  },
  "external_spec_references": [],
  "token_budget_suggestion": {},
  "quality_check": {"clarity": "bool", "completeness": "bool", "overall_score": "float"},
  "context_architecture_compliance": {"xml_tags_used": "bool", "thinking_block_present": "bool"},
  "feedback_applied": []
}
```
</state_schema>

## pm_plan.json
<state_schema>
```json
{
  "version": "int", "timestamp": "ISO-8601",
  "thinking_trace": "string",
  "task_decomposition": [],
  "dependency_graph": {},
  "skill_mapping": {
    "required_skills": [], "required_tools": [],
    "required_plugins": [], "anthropic_skills_required": []
  },
  "worker_pool": {
    "total_workers": "int",
    "workers": [{
      "worker_id": "W1", "role": "", "persona": "",
      "structured_output_schema": {},
      "natural_output_format": "thinking_answer_xml",
      "handoff_targets": [], "handoff_enabled": "bool",
      "token_budget": "int",
      "reporting_framework": "PREP|MECE|..."
    }],
    "merge_strategy": {
      "method": "assembler|sequential_merge|parallel_merge",
      "conflict_detection_enabled": "bool",
      "handoff_max_hops": "int"
    }
  },
  "watchdog_pool": {"enabled": "bool", "pool_size": "int", "specialization": []},
  "adversarial_critic_enabled": "bool",
  "polisher_enabled": "bool",
  "async_tasks": {"enabled": "bool", "candidates": []},
  "checkpoint_strategy": {"before_phase": [], "retention": "int"},
  "process_map": {},
  "risk_register": [],
  "causal_graph_analysis": {},
  "framework_selection": {"primary": "", "secondary": [], "rationale": ""},
  "external_spec_versions": {
    "mcp": "2025-11-25",
    "anthropic_memory": "managed-agents-2026-04-01",
    "anthropic_skills": "skills-2025-10-02"
  },
  "interactions_planned": [],
  "federation_routing": null
}
```
</state_schema>

## research_data.json
<state_schema>
```json
{
  "version": "int", "thinking_trace": "",
  "search_plan": {"topics": []},
  "research_items": [{
    "id": "R001", "topic": "", "summary": "",
    "data_points": [{
      "claim": "", "source": "URL", "source_tier": "int",
      "confidence": "float", "published_date": "",
      "cross_validated": "bool", "cross_validation_sources": []
    }],
    "confidence_note": "", "gaps": [], "caveats": []
  }],
  "factcheck_package": {"items": []},
  "overall_confidence": "float",
  "coverage_assessment": {"covered": [], "partially_covered": [],
                          "not_covered": [], "coverage_ratio": "float"},
  "source_statistics": {"tier_1_count": "int", "total_sources": "int"},
  "memory_imported": [],
  "tier_calibration_applied": [],
  "async_search_tasks": [],
  "mcp_registry_used": "bool"
}
```
</state_schema>

## watchdog_verdicts.json + watchdog_pool_verdicts.json
<state_schema>

### watchdog_verdicts.json
```json
{
  "version": "int", "verdicts": [{
    "claim_id": "WD001", "claim": "", "verdict": "TRUE|FALSE|UNVERIFIABLE",
    "confidence": "float", "verification_method": "direct|cross|logical",
    "evidence": {"supporting": [], "contradicting": []},
    "reasoning": ""
  }],
  "aggregate": {
    "total_claims": "int", "true_count": "int", "false_count": "int",
    "unverifiable_count": "int", "critical_false": [],
    "overall_integrity": "float"
  },
  "action_required": {
    "researcher_rerun": "bool",
    "false_claims_for_correction": [],
    "unverifiable_claims_for_investigation": []
  },
  "researcher_correction_package": [{
    "claim_id": "WD001", "original_claim": "", "verdict": "FALSE",
    "falsification_evidence": {
      "contradicting_sources": [], "correct_data": "|null",
      "error_type": "factual_error|outdated_data|misattribution|context_distortion|fabricated_source",
      "error_detail": ""
    },
    "research_hints": {
      "suggested_queries": [], "recommended_sources": [],
      "avoid_sources": [], "scope_guidance": ""
    }
  }]
}
```

### watchdog_pool_verdicts.json
```json
{
  "version": "int", "pool_size": "int",
  "rounds": [{"round": "int", "instances": [{
    "instance_id": "W1", "specialization": "tier1_direct",
    "verdicts": []
  }]}],
  "consensus": {
    "claim_id": "", "final_verdict": "",
    "method": "unanimous|majority|round2_consensus|user_arbitrated",
    "majority_count": "int", "dissent": [], "early_exit": "bool"
  }
}
```
</state_schema>

## worker_output.json
<state_schema>
```json
{
  "version": "int", "thinking_trace": "",
  "worker_id": "W1", "worker_role": "",
  "tasks_completed": [{
    "task_id": "T1", "status": "completed|partial|failed",
    "output_summary": "", "output_files": [],
    "information_used": [{"source": "research_data.json#R001", "watchdog_verdict": "TRUE"}],
    "uncertainties": []
  }],
  "final_output": {"type": "", "path": "", "summary": ""},
  "process_learning": {},
  "structured_output_validation": {"schema_used": "", "valid": "bool", "errors": []},
  "handoffs_made": [],
  "handoffs_received": [],
  "async_tasks_created": [],
  "checkpoint_consumed": "",
  "token_budget": {"allocated": "int", "used": "int", "compression_mode_enabled": "bool"},
  "context_architecture_compliance": {"thinking_present": "bool", "answer_present": "bool"}
}
```
</state_schema>

## adversarial_report.json
<state_schema>
```json
{
  "version": "int", "thinking_trace": "",
  "complexity_level": "complex|expert",
  "claim_analyses": [{
    "claim_id": "AC001", "original_claim": "",
    "counter_scenarios": [{"scenario": "", "preconditions": [],
                            "evidence_required": "", "plausibility": "float",
                            "impact_if_true": "low|medium|high|critical"}],
    "coverage_gaps": [],
    "adversarial_inputs": [{"type": "boundary|malicious|conflict|reverse_causality"}],
    "verdict": "ROBUST|CONDITIONALLY_ROBUST|VULNERABLE"
  }],
  "aggregate": {
    "total_claims": "int", "robust_count": "int", "vulnerable_count": "int",
    "critical_vulnerabilities": [], "vulnerability_discovery_rate": "float",
    "overall_verdict": "ROBUST|CONDITIONALLY_ROBUST|VULNERABLE"
  },
  "verifier_input": {"should_block_pass": "bool",
                     "recommended_iteration_scope": "partial|full|none",
                     "specific_concerns": []}
}
```
</state_schema>

## polisher_report.json
<state_schema>
```json
{
  "version": "int", "thinking_trace": "",
  "input_files": [], "polished_files": [],
  "changes": [{
    "change_id": "P001",
    "dimension": "korean_policy|style|terminology|readability|fact_preservation",
    "severity": "critical|major|minor",
    "before": "", "after": "", "rationale": ""
  }],
  "metrics": {
    "korean_policy_violations_fixed": "int",
    "style_inconsistencies_fixed": "int",
    "terminology_unifications": "int",
    "readability_improvements": "int",
    "fact_preservation_score": "float"
  },
  "fact_preservation_violations": []
}
```
</state_schema>

## verifier_report.json
<state_schema>
```json
{
  "version": "int", "thinking_trace": "",
  "task_specific_rubric": {"criteria": [], "pass_threshold": "float", "rubric_rationale": ""},
  "critical_analysis": {"core_claims": [], "refutable_arguments": [], "rebuttal_impact": ""},
  "quality_rubric": {
    "accuracy": {"score": "1-5", "criteria": "", "findings": []},
    "completeness": {"score": "1-5"},
    "consistency": {"score": "1-5"},
    "efficiency": {"score": "1-5", "telemetry_basis": {}},
    "traceability": {"score": "1-5"},
    "robustness": {"score": "1-5", "adversarial_verdict": ""},
    "external_compliance": {"score": "1-5", "schema_violations": "int", "memory_sync_status": ""},
    "linguistic_quality": {"score": "1-5", "polisher_metrics": {}},
    "context_architecture_compliance": {
      "score": "1-5", "avg_compliance": "float", "n_files": "int",
      "failing_files": [], "common_issues": {}
    }
  },
  "overall_score": "float", "verdict": "PASS|CONDITIONAL_PASS|FAIL",
  "external_calibration": {
    "swe_bench_estimated": "float", "osworld_estimated": "float",
    "calibration_disclaimer": ""
  },
  "agent_feedback": {
    "prompt_architect": {"performance_score": "int", "strengths": [], "improvements": []},
    "pm_orchestrator": {}, "researcher": {}, "watchdog": {},
    "worker": {}, "adversarial_critic": {}, "polisher": {},
    "verifier": {}
  },
  "feedback_directive": {
    "requires_iteration": "bool", "iteration_scope": "full|partial",
    "agents_to_rerun": [], "specific_instructions": {},
    "checkpoint_strategy": {"rollback_to": "", "rationale": ""}
  },
  "loop_decision": {"action": "continue|stop", "reason": "",
                    "iteration_number": "int", "score_trend": [], "convergence_detected": "bool"},
  "final_approval": {"approved": "bool", "conditions": [], "blocked_by": []},
  "maturity_assessment": {"current_level": "Initial|Managed|Defined|Quantitatively Managed|Optimizing"}
}
```
</state_schema>

## Additional Schemas
<state_schema>

### async_tasks.json
```json
{"version": "int", "tasks": {"<uuid>": {
  "task_id": "", "agent": "",
  "state": "pending|working|input_required|completed|failed|cancelled",
  "created_at": "", "last_updated": "", "parent_session": "",
  "payload": {}, "result": null, "error": null,
  "timeout_seconds": "int", "mcp_spec_version": "2025-11-25"
}}}
```

### worker_handoffs.json
```json
{"version": "int", "handoffs": [{
  "handoff_id": "HO001", "from": "", "to": "",
  "context": {}, "hop_count": "int", "timestamp": "",
  "accepted": "bool", "result": null
}]}
```

### worker_conflicts.json
```json
{"version": "int", "conflicts": [{
  "conflict_id": "CF001", "entity": "",
  "worker_a": {"id": "W1", "claim": ""},
  "worker_b": {"id": "W2", "claim": ""},
  "stage_recommendation": "auto_reconcile|watchdog_reverify|pm_arbitration",
  "resolution": null, "resolved_at": null, "user_decision": null
}]}
```

### memory_index.json (persistent)
```json
{"version": "int", "memory_api_enabled": "bool",
 "external_memory_id": null, "last_sync": null,
 "sync_status": "ok|failed|disabled",
 "memories": [{"id": "", "type": "procedural|semantic|episodic",
               "content": "JSON-serialized", "metadata": {}}],
 "anthropic_spec": "managed-agents-2026-04-01"}
```

### Additional compact schemas
- `causal_dag.json`: `{nodes, edges, is_acyclic}`
- `multimodal_verdicts.json`: `{url / code verdicts}`
- `sla_compliance.json`: `{compliance_ratio, violations, compliant, verdict}`
- `mcp_registry_cache.json`: `{keywords -> results}`
- `calibration_estimates.json`: `{benchmark, mas_score, estimated, method}`
- `calibration.json` (persistent): `{benchmark -> observations[]}`

### agent_messages.json
```json
{"version": "int", "interactions": {"<id>": {
  "type": "review_round|debate_round|peer_review|interactive_factcheck|iterative_refinement|standup_sync",
  "participants": [], "started_at": "",
  "max_rounds": "int", "max_hops": "int", "current_round": "int",
  "status": "active|ended", "context": {},
  "termination_reason": null, "ended_at": null, "outcome": null
}}, "messages": [{
  "message_id": "msg_NNNN", "interaction_id": "",
  "sender": "", "content": {}, "round": "int", "references": [],
  "type": "message|vote|question|answer|verdict|argument|standup|handoff_request",
  "timestamp": ""
}]}
```

### Federation
- `federation_registry.json`: `{federation_id, pattern, instances{instance_id -> meta}}`
- `federation_messages.json`: `{messages[], read_log{recipient_id -> [message_ids]}}`
- Per-instance: `instances/<id>/instance.json` + `heartbeat.json` + `state/` + `persistent/`
</state_schema>

## meta.json (persistent)
<state_schema>
```json
{
  "session_count": "int", "review_interval": "int",
  "last_review_session": "int", "last_review_date": "",
  "review_history": [], "avg_quality_scores": [],
  "convergence_bayes": {
    "<complexity>": {"alpha": "float", "beta": "float",
                     "sample_count": "int", "threshold": "float", "last_updated": ""}
  },
  "memory_api_enabled": "bool",
  "anthropic_skills_enabled": "bool",
  "external_spec_pinned_versions": {
    "mcp": "2025-11-25", "anthropic_memory": "managed-agents-2026-04-01",
    "anthropic_skills": "skills-2025-10-02"
  },
  "cost_routing_history": {
    "<model>": {"<complexity>": {"total_runs": "int",
                                  "avg_quality": "float", "avg_duration_ms": "float"}}
  },
  "gate_decision_history": {
    "<gate_id>": {"decisions": [], "counts": {}, "default_recommendation": "", "confidence": "float"}
  }
}
```

### source_reliability.json (persistent)
```json
{"version": "int", "sources": {
  "<url>": {"tier_static": "int", "pass_count": "int", "fail_count": "int",
            "confidence_prior": "float", "last_used": "", "tier_calibrated": "int"}
}}
```
</state_schema>
