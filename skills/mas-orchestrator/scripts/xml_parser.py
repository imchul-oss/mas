"""
MAS XML Tag Parser for Context Architecture

Mechanically parses XML tags in agents/*.md, references/*.md, SKILL.md,
and Worker outputs, feeding them into the Verifier's
context_architecture_compliance dimension.

This module is Pure Python (no external dependencies). Optional dependencies
like lxml are possible, but the standard `re` module is sufficient.
"""

import re
from pathlib import Path


# ============================================================
# Required Tags by Document Type (context-architecture.md, Section 2)
# ============================================================

REQUIRED_TAGS_BY_DOC_TYPE = {
    "agent_definition": [
        "agent_identity",
        "knowledge_base",
        "execution_protocol",
        "output_format",
        "token_efficiency_rules",
        "failure_modes",
        "feedback_integration"
    ],
    "skill_md": [
        "system_overview",
        "token_efficiency_protocol",
        "quality_guardrails",
        "execution_protocol",
        "state_management"
    ],
    "worker_output_natural": [
        "thinking",
        "answer"
    ],
    "researcher_output": [
        "thinking",
        "research_items",
        "source_citations"
    ]
}

OPTIONAL_TAGS = [
    "agent_activation_policy",
    "non_negotiable_rules",
    "evolution_notes",
    "uncertainty",
    "source_citations"
]


# ============================================================
# Core Parser
# ============================================================

def extract_xml_sections(text):
    """
    Extract all XML tag sections from the given text.

    Returns: dict {tag_name: [content_strings]}
    If a tag appears multiple times, its contents are accumulated in a list.
    """
    # Non-greedy matching, multiline + dotall
    pattern = re.compile(r'<(\w+)>(.*?)</\1>', re.DOTALL)
    sections = {}
    for match in pattern.finditer(text):
        tag, content = match.group(1), match.group(2).strip()
        sections.setdefault(tag, []).append(content)
    return sections


def find_orphan_tags(text):
    """
    Detect opening tags without matching closing tags or vice versa.

    Returns: list of orphan tag descriptions.
    """
    opening_pattern = re.compile(r'<(\w+)>')
    closing_pattern = re.compile(r'</(\w+)>')
    openings = [(m.group(1), m.start()) for m in opening_pattern.finditer(text)]
    closings = [(m.group(1), m.start()) for m in closing_pattern.finditer(text)]

    orphans = []
    open_count = {}
    for tag, _ in openings:
        open_count[tag] = open_count.get(tag, 0) + 1
    close_count = {}
    for tag, _ in closings:
        close_count[tag] = close_count.get(tag, 0) + 1

    all_tags = set(open_count.keys()) | set(close_count.keys())
    for tag in all_tags:
        oc = open_count.get(tag, 0)
        cc = close_count.get(tag, 0)
        if oc != cc:
            orphans.append({"tag": tag, "open_count": oc, "close_count": cc,
                            "balanced": False})
    return orphans


def parse_agent_definition(file_path):
    """
    Validate an agents/*.md file against the Context Architecture convention.

    Returns: {
        "file": str,
        "doc_type": "agent_definition",
        "required_tags_present": dict {tag: bool},
        "missing_required": list,
        "extra_tags_found": list,
        "orphan_tags": list,
        "machine_parseable": bool,
        "compliance_score": float (0-1)
    }
    """
    return _parse_doc(file_path, "agent_definition")


def parse_skill_md(file_path):
    return _parse_doc(file_path, "skill_md")


def parse_worker_output(text_or_path, expected_doc_type="worker_output_natural"):
    """Validate Worker natural-language output (thinking + answer separation)."""
    if isinstance(text_or_path, (str, Path)) and Path(text_or_path).exists():
        text = Path(text_or_path).read_text(encoding="utf-8")
    else:
        text = str(text_or_path)
    return _parse_text(text, expected_doc_type, source_label="worker_output")


def _parse_doc(file_path, doc_type):
    fp = Path(file_path)
    if not fp.exists():
        return {"file": str(fp), "error": "file_not_found"}
    text = fp.read_text(encoding="utf-8")
    return _parse_text(text, doc_type, source_label=str(fp))


def _parse_text(text, doc_type, source_label=""):
    sections = extract_xml_sections(text)
    orphans = find_orphan_tags(text)
    found_tags = set(sections.keys())

    required = REQUIRED_TAGS_BY_DOC_TYPE.get(doc_type, [])
    required_set = set(required)
    required_present = {t: t in found_tags for t in required}
    missing_required = [t for t, p in required_present.items() if not p]

    extra_tags = [t for t in found_tags
                  if t not in required_set and t not in OPTIONAL_TAGS]

    machine_parseable = len(orphans) == 0 and len(missing_required) == 0
    compliance_score = (len(required) - len(missing_required)) / len(required) if required else 1.0
    if orphans:
        compliance_score = max(0, compliance_score - 0.2)

    return {
        "file": source_label,
        "doc_type": doc_type,
        "required_tags_present": required_present,
        "missing_required": missing_required,
        "extra_tags_found": extra_tags,
        "orphan_tags": orphans,
        "machine_parseable": machine_parseable,
        "compliance_score": round(compliance_score, 2)
    }


def lint_directory(dir_path, doc_type_resolver=None):
    """
    Lint an entire directory. agents/*.md -> agent_definition,
    SKILL.md -> skill_md, references/*.md -> optional.

    Returns: list of compliance reports.
    """
    dir_path = Path(dir_path)
    if not dir_path.exists():
        return [{"error": f"directory_not_found: {dir_path}"}]

    if doc_type_resolver is None:
        def doc_type_resolver(p):
            if "agents" in p.parts and p.suffix == ".md":
                return "agent_definition"
            if p.name == "SKILL.md":
                return "skill_md"
            return None  # skip

    reports = []
    for f in dir_path.rglob("*.md"):
        doc_type = doc_type_resolver(f)
        if doc_type:
            reports.append(_parse_doc(f, doc_type))
    return reports


# ============================================================
# Verifier integration (computes context_architecture_compliance dimension)
# ============================================================

def compute_verifier_dimension_score(reports):
    """
    Lint reports -> Verifier rubric's context_architecture_compliance score (1-5).

    Mapping:
        avg compliance_score >= 0.95 -> 5
        avg compliance_score >= 0.85 -> 4
        avg compliance_score >= 0.70 -> 3
        avg compliance_score >= 0.50 -> 2
        otherwise -> 1
    """
    if not reports:
        return {"score": 1, "reason": "no_reports"}
    scores = [r.get("compliance_score", 0) for r in reports if "compliance_score" in r]
    if not scores:
        return {"score": 1, "reason": "no_valid_reports"}
    avg = sum(scores) / len(scores)
    if avg >= 0.95: dim_score = 5
    elif avg >= 0.85: dim_score = 4
    elif avg >= 0.70: dim_score = 3
    elif avg >= 0.50: dim_score = 2
    else: dim_score = 1

    failing = [r for r in reports if r.get("compliance_score", 0) < 0.7]
    return {
        "score": dim_score,
        "criteria": "Compliance with context-architecture.md Section 2 XML tag convention",
        "avg_compliance": round(avg, 2),
        "n_files": len(scores),
        "failing_files": [r["file"] for r in failing],
        "common_issues": _aggregate_issues(reports)
    }


def _aggregate_issues(reports):
    """Aggregate common issues."""
    missing_tag_freq = {}
    orphan_freq = {}
    for r in reports:
        for t in r.get("missing_required", []):
            missing_tag_freq[t] = missing_tag_freq.get(t, 0) + 1
        for o in r.get("orphan_tags", []):
            orphan_freq[o["tag"]] = orphan_freq.get(o["tag"], 0) + 1
    return {
        "frequently_missing_tags": sorted(missing_tag_freq.items(),
                                            key=lambda x: -x[1])[:5],
        "frequently_orphan_tags": sorted(orphan_freq.items(),
                                           key=lambda x: -x[1])[:5]
    }


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MAS XML Parser Self-Test")
    print("=" * 60)

    # Test 1: basic parsing
    sample = """
    <agent_identity>
    Role: Test Agent
    KPI: Quality
    </agent_identity>

    <execution_protocol>
    Step 1: ...
    </execution_protocol>
    """
    print("\n[Test 1] extract_xml_sections")
    sections = extract_xml_sections(sample)
    print(f"  found tags: {list(sections.keys())}")

    # Test 2: orphan detection
    bad_sample = "<thinking>incomplete"
    print("\n[Test 2] find_orphan_tags")
    orphans = find_orphan_tags(bad_sample)
    print(f"  orphans: {orphans}")

    # Test 3: worker output validation
    worker_out = """
    <thinking>
    Step 1: analysis
    Step 2: conclusion
    </thinking>

    <answer>
    Final answer
    </answer>
    """
    print("\n[Test 3] parse_worker_output")
    result = _parse_text(worker_out, "worker_output_natural", source_label="<inline>")
    print(f"  compliance: {result['compliance_score']}")
    print(f"  missing: {result['missing_required']}")

    # Test 4: Verifier dimension
    print("\n[Test 4] compute_verifier_dimension_score")
    fake_reports = [
        {"compliance_score": 0.95, "missing_required": [], "orphan_tags": [], "file": "a.md"},
        {"compliance_score": 0.80, "missing_required": ["failure_modes"], "orphan_tags": [], "file": "b.md"},
    ]
    dim = compute_verifier_dimension_score(fake_reports)
    print(f"  dimension score: {dim['score']}, avg: {dim['avg_compliance']}")
    print(f"  common issues: {dim['common_issues']}")

    print("\n" + "=" * 60)
    print("Self-test complete.")
