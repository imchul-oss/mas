#!/usr/bin/env python3
"""
MAS XML Lint CI automation

CI integration entry point. Invokes xml_parser.py to lint agents/,
references/, and SKILL.md, then computes the Verifier dimension score.

Exit codes:
  0: PASS (avg compliance >= 0.95, dimension 5/5)
  1: CONDITIONAL_PASS (0.85 <= avg < 0.95, dimension 4/5)
  2: FAIL (avg < 0.85)
  3: execution error (e.g. file not found)

Usage (CI):
    python scripts/run_xml_lint.py [--plugin-root PATH] [--strict] [--json]

Examples:
    # Default run (current directory)
    python scripts/run_xml_lint.py

    # Specific plugin directory
    python scripts/run_xml_lint.py --plugin-root ~/.claude/plugins/mas-orchestrator/skills/mas-orchestrator

    # JSON output (for CI integration)
    python scripts/run_xml_lint.py --json

    # Strict mode (treat CONDITIONAL_PASS as failure)
    python scripts/run_xml_lint.py --strict
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import xml_parser as xp


def doc_type_resolver(p):
    """Determine document type based on path."""
    if "_legacy" in p.parts:
        # Retired material is not the live contract, so it is not held to the contract's
        # tag convention. Added 2026-08-09 when six agent definitions moved to _legacy and
        # the retirement note itself was failed as a malformed agent definition.
        return None
    if "agents" in p.parts and p.suffix == ".md":
        return "agent_definition"
    if p.name == "SKILL.md":
        return "skill_md"
    if "references" in p.parts and p.suffix == ".md":
        # references are not strictly required to have specific tags (loose validation)
        return None
    return None


def lint_plugin_root(plugin_root):
    """Process all lint targets under the plugin root."""
    root = Path(plugin_root)
    if not root.exists():
        return None, f"plugin_root not found: {plugin_root}"

    reports = xp.lint_directory(root, doc_type_resolver=doc_type_resolver)
    if not reports:
        return None, "no lint targets found (agents/*.md or SKILL.md missing)"

    return reports, None


def determine_exit_code(dim_score, strict=False):
    """Verifier dimension score -> exit code."""
    score = dim_score.get("score", 0)
    if score == 5:
        return 0  # PASS
    if score == 4:
        return 1 if strict else 0  # CONDITIONAL -> 1 only in strict mode
    return 2  # FAIL


def format_human_report(reports, dim_score):
    """Human-friendly report."""
    lines = []
    lines.append("=" * 70)
    lines.append("MAS XML Tag Compliance Lint Report")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"Files checked: {dim_score['n_files']}")
    lines.append(f"Average compliance: {dim_score['avg_compliance']:.2f}")
    lines.append(f"Dimension score: {dim_score['score']}/5")
    lines.append("")

    # PASS / CONDITIONAL / FAIL
    score = dim_score['score']
    if score == 5:
        lines.append("[PASS] All files fully compliant")
    elif score == 4:
        lines.append("[CONDITIONAL_PASS] Minor compliance issues")
    else:
        lines.append("[FAIL] Significant compliance issues")
    lines.append("")

    # Per-file details
    lines.append("Per-File Reports:")
    lines.append("-" * 70)
    for r in reports:
        status_icon = "[OK]" if r.get("compliance_score", 0) >= 0.95 else \
                       "[WARN]" if r.get("compliance_score", 0) >= 0.85 else "[FAIL]"
        lines.append(f"  {status_icon} {r['file']}")
        lines.append(f"      compliance: {r.get('compliance_score', 0):.2f}")
        if r.get("missing_required"):
            lines.append(f"      missing: {r['missing_required']}")
        if r.get("orphan_tags"):
            lines.append(f"      orphans: {[o['tag'] for o in r['orphan_tags']]}")

    # Common issues
    common = dim_score.get("common_issues", {})
    if common.get("frequently_missing_tags"):
        lines.append("")
        lines.append("Frequently Missing Tags:")
        for tag, count in common["frequently_missing_tags"][:5]:
            lines.append(f"  - {tag} ({count} occurrences)")

    if common.get("frequently_orphan_tags"):
        lines.append("")
        lines.append("Frequently Orphan Tags:")
        for tag, count in common["frequently_orphan_tags"][:5]:
            lines.append(f"  - {tag} ({count} occurrences)")

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plugin-root", default=".",
                        help="Plugin root directory (default: current)")
    parser.add_argument("--strict", action="store_true",
                        help="Treat CONDITIONAL_PASS as failure (exit 1)")
    parser.add_argument("--json", action="store_true",
                        help="JSON output (for CI integration)")
    args = parser.parse_args()

    reports, err = lint_plugin_root(args.plugin_root)
    if err:
        if args.json:
            print(json.dumps({"error": err}))
        else:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(3)

    dim_score = xp.compute_verifier_dimension_score(reports)

    if args.json:
        print(json.dumps({
            "dimension_score": dim_score,
            "n_files": len(reports),
            "reports": reports
        }, ensure_ascii=False, indent=2))
    else:
        print(format_human_report(reports, dim_score))

    sys.exit(determine_exit_code(dim_score, strict=args.strict))


if __name__ == "__main__":
    main()
