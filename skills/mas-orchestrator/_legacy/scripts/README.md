# Retired scripts (2026-08-09, v3.0.0)

Eight modules and their five test files, about 139 KB, left `scripts/` when the skill went from eight
roles to two. Nothing in the live contract invokes any of them, and no surviving script imports one -
both checked before moving, not assumed.

| module | what it did | why it left |
|---|---|---|
| `agent_interaction.py` | The 15 inter-agent channels, peer review rounds, debate | Two roles need one handoff |
| `c_implementations.py` | MCP Registry lookup and the PM's skill-discovery path | PM is retired |
| `multi_mas_federation.py` | Hub-spoke / hierarchical / peer-to-peer / swarm federation | Federating an unproven unit multiplies it |
| `skillopt_adapter.py` | SkillOpt loop over agent evolution | The evolution machinery it drove is gone |
| `goal_driven_executor.py` | The `goal_driven` Worker execution mode PM selected | Its selector was the PM |
| `senior_engineer_metrics.py` | AST-based code-simplicity score, the old rubric's 10th dimension | The live Verifier rubric has nine dimensions and never included it. The README claimed ten; that was the doc drifting from the definition, not a missing implementation |
| `reflexion_full_stack.py` | Reflexion loop, ungrounded self-correction guarded by an external signal | Never wired to either surviving role |
| `gepa_optimizer.py` | Pareto prompt evolution, fitness = `eval/scorer.py` | See below - this one is the interesting removal |

**GEPA deserves its own sentence, because on paper it fits.** It optimises prompts against the eval
and adopts a mutation only if it Pareto-dominates on (quality, cost), which is exactly the discipline
the rest of this skill now runs on. It goes anyway because its precondition does not hold: measured
2026-08-09, judge standard deviation on this rubric is 0.10 to 0.38 and the standard error of an n=1
difference is 0.391, so the fitness signal it would climb is mostly noise at any replicate count this
skill can afford. An optimiser fed an unresolvable objective does not find nothing - it finds
something, confidently, and ships it. Restore it when a case can be scored to a resolution finer than
the improvements being sought.

**What stayed.** `state_manager.py` (state, telemetry, breakpoints - the contract's Phase 0 calls it),
`xml_parser.py` and `run_xml_lint.py` (the tag convention and its CI entry point), and everything in
`eval/`. That is the whole live surface.

**The test count moved and that is not a regression.** The suite was 147 tests across 8 files; five
test files retired with their modules, so what remains covers only live code. A smaller suite over a
smaller surface is the point of the exercise, not a loss - but if a module comes back, its tests come
back with it, and they are here rather than deleted for exactly that reason.
