"""
MAS C-track implementations (C1~C6)
===================================

Pure-Python implementation of the C-track features. Optional dependencies:
- networkx (optional, enhances C1; falls back to pure Python)
- jsonschema (optional, for schema validation)
"""

import json
import math
import os
import re
import time
import hashlib
import ast
from collections import defaultdict, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# C1: Causal Graph
# ============================================================
#
# A causal DAG plus basic do-calculus operations. Used by the PM to
# separate correlation from causation in the risk_register analysis.
#
# Limitations: not all do-calculus rules (do(X)=do(X), backdoor,
# frontdoor) are implemented. Only d-separation + backdoor adjustment
# are supported.

class CausalDAG:
    """A simple causal DAG. Each node is a variable; edges represent causal direction."""

    def __init__(self):
        self.nodes = set()
        self.edges = []  # [(parent, child)]
        self._parents_cache = None
        self._children_cache = None

    def add_node(self, name):
        self.nodes.add(name)
        self._invalidate_cache()

    def add_edge(self, parent, child):
        self.add_node(parent)
        self.add_node(child)
        if (parent, child) not in self.edges:
            self.edges.append((parent, child))
        self._invalidate_cache()

    def _invalidate_cache(self):
        self._parents_cache = None
        self._children_cache = None

    def parents(self, node):
        if self._parents_cache is None:
            self._parents_cache = defaultdict(set)
            for p, c in self.edges:
                self._parents_cache[c].add(p)
        return self._parents_cache.get(node, set())

    def children(self, node):
        if self._children_cache is None:
            self._children_cache = defaultdict(set)
            for p, c in self.edges:
                self._children_cache[p].add(c)
        return self._children_cache.get(node, set())

    def ancestors(self, node):
        result = set()
        stack = list(self.parents(node))
        while stack:
            n = stack.pop()
            if n not in result:
                result.add(n)
                stack.extend(self.parents(n))
        return result

    def descendants(self, node):
        result = set()
        stack = list(self.children(node))
        while stack:
            n = stack.pop()
            if n not in result:
                result.add(n)
                stack.extend(self.children(n))
        return result

    def is_acyclic(self):
        """Detect cycles via Kahn's algorithm."""
        in_degree = {n: 0 for n in self.nodes}
        for p, c in self.edges:
            in_degree[c] = in_degree.get(c, 0) + 1
        queue = [n for n in self.nodes if in_degree[n] == 0]
        visited = 0
        while queue:
            n = queue.pop(0)
            visited += 1
            for child in self.children(n):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        return visited == len(self.nodes)

    def d_separation(self, x, y, conditioning_set=None):
        """
        d-separation: test whether x is independent of y given conditioning_set.

        Returns True if x and y are conditionally independent, False if they
        may be dependent.
        """
        if conditioning_set is None:
            conditioning_set = set()
        # Enumerate all paths (simple-graph assumption)
        paths = self._all_undirected_paths(x, y)
        for path in paths:
            if not self._is_blocked(path, conditioning_set):
                return False
        return True

    def _all_undirected_paths(self, x, y, max_paths=50):
        """All undirected paths from x to y (simple graph, depth-limited)."""
        adj = defaultdict(set)
        for p, c in self.edges:
            adj[p].add(c)
            adj[c].add(p)
        paths = []
        def dfs(node, target, visited, path):
            if len(paths) >= max_paths:
                return
            if node == target:
                paths.append(list(path))
                return
            for next_node in adj[node]:
                if next_node not in visited:
                    visited.add(next_node)
                    path.append(next_node)
                    dfs(next_node, target, visited, path)
                    path.pop()
                    visited.remove(next_node)
        dfs(x, y, {x}, [x])
        return paths

    def _is_blocked(self, path, conditioning):
        """Return True if the path is blocked by the conditioning set (collider rule applied)."""
        if len(path) < 3:
            return False
        for i in range(1, len(path) - 1):
            prev_n, mid, next_n = path[i-1], path[i], path[i+1]
            is_collider = (prev_n in self.parents(mid)) and (next_n in self.parents(mid))
            if is_collider:
                # collider: blocked unless mid or descendant in conditioning
                if mid in conditioning or self.descendants(mid) & conditioning:
                    continue  # not blocked
                return True
            else:
                # chain or fork: blocked iff mid in conditioning
                if mid in conditioning:
                    return True
        return False

    def backdoor_set(self, treatment, outcome):
        """
        Backdoor adjustment set: the set of variables to condition on
        to estimate the causal effect of treatment on outcome.

        Simple heuristic: all parents of treatment. (The full backdoor
        criterion additionally requires excluding descendants, etc.)
        """
        return self.parents(treatment) - self.descendants(treatment)

    def to_dict(self):
        return {"nodes": sorted(self.nodes),
                "edges": self.edges,
                "is_acyclic": self.is_acyclic()}


def analyze_risk_with_causal_graph(risk_register, dag):
    """
    Analyze items in pm_plan.risk_register through a causal DAG.

    Returns: for each risk, a causal-vs-correlational classification
    plus the backdoor adjustment set.
    """
    analysis = []
    for risk in risk_register:
        risk_node = risk.get("id", "R?")
        if risk_node not in dag.nodes:
            analysis.append({"risk_id": risk_node, "status": "not_in_graph",
                            "recommendation": "needs to be added to the DAG"})
            continue
        downstream = dag.descendants(risk_node)
        upstream = dag.ancestors(risk_node)
        bd = dag.backdoor_set(risk_node, "TARGET_QUALITY") if "TARGET_QUALITY" in dag.nodes else set()
        analysis.append({
            "risk_id": risk_node,
            "downstream_impacts": sorted(downstream),
            "upstream_causes": sorted(upstream),
            "backdoor_adjustment_set": sorted(bd),
            "is_root_cause": len(upstream) == 0
        })
    return analysis


# ============================================================
# C2: Multi-modal Watchdog
# ============================================================
#
# Extends the text-only Watchdog to also verify image URLs and code.
# Actual Vision-model calls are abstracted behind a Claude Vision API
# interface.

def verify_image_url(url, expected_metadata=None):
    """
    Verify an image URL's existence and basic metadata.

    Limitation: real image-content analysis requires calling the Claude
    Vision API. Here we self-verify only URL format, domain, and
    accessibility.
    """
    result = {"url": url, "verdict": "UNVERIFIABLE", "checks": {}}

    # Format check
    url_pattern = re.compile(
        r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE
    )
    if not url_pattern.match(url):
        result["checks"]["format"] = "invalid_url_format"
        result["verdict"] = "FALSE"
        return result
    result["checks"]["format"] = "valid"

    # Extension check
    ext_match = re.search(r'\.(jpg|jpeg|png|gif|webp|svg)(\?|$)', url, re.IGNORECASE)
    result["checks"]["has_image_extension"] = bool(ext_match)

    # Domain trust (Tier mapping)
    domain_match = re.search(r'https?://([^/]+)', url)
    if domain_match:
        domain = domain_match.group(1).lower()
        trusted_domains = {"upload.wikimedia.org", "commons.wikimedia.org",
                           "github.com", "githubusercontent.com",
                           "cdn.britannica.com"}
        result["checks"]["trusted_domain"] = any(td in domain for td in trusted_domains)

    # Metadata match check
    if expected_metadata:
        result["checks"]["expected_metadata"] = expected_metadata
        result["verdict"] = "REQUIRES_VISION_API"  # claude vision call needed
    else:
        result["verdict"] = "PARTIAL_VERIFY"

    result["next_step"] = "Call Claude Vision API (on user opt-in)"
    return result


def verify_code_block(code, language="python"):
    """
    Verify a code block.

    Python: AST parsing for syntax checks + dangerous-pattern detection.
    Other languages: heuristic checks.
    """
    result = {"language": language, "verdict": "UNVERIFIABLE", "checks": {}}

    if language.lower() == "python":
        try:
            tree = ast.parse(code)
            result["checks"]["syntax"] = "valid"
            # AST analysis
            dangerous = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr
                    if func_name in {"eval", "exec", "compile", "__import__"}:
                        dangerous.append(f"dangerous_call:{func_name}")
                if isinstance(node, ast.ImportFrom):
                    if node.module in {"os", "subprocess", "shutil"}:
                        dangerous.append(f"sensitive_import:{node.module}")
            result["checks"]["dangerous_patterns"] = dangerous
            result["verdict"] = "TRUE" if not dangerous else "REQUIRES_REVIEW"
            result["complexity"] = {
                "lines": len(code.split("\n")),
                "ast_nodes": sum(1 for _ in ast.walk(tree))
            }
        except SyntaxError as e:
            result["checks"]["syntax"] = f"invalid: {str(e)[:100]}"
            result["verdict"] = "FALSE"
    else:
        # Other languages: simple heuristics
        result["checks"]["non_empty"] = bool(code.strip())
        result["checks"]["balanced_braces"] = code.count("{") == code.count("}")
        result["checks"]["balanced_brackets"] = code.count("[") == code.count("]")
        result["checks"]["balanced_parens"] = code.count("(") == code.count(")")
        all_balanced = all(v for k, v in result["checks"].items() if k.startswith("balanced"))
        result["verdict"] = "TRUE" if all_balanced else "REQUIRES_REVIEW"

    return result


def multimodal_watchdog_verdict(claim, modality):
    """
    Unified entry point for the multi-modal Watchdog.
    modality: "text" | "image" | "code" | "mixed"
    """
    if modality == "image":
        return verify_image_url(claim.get("url"), claim.get("expected_metadata"))
    elif modality == "code":
        return verify_code_block(claim.get("code"), claim.get("language", "python"))
    elif modality == "mixed":
        results = []
        for sub_claim in claim.get("components", []):
            results.append(multimodal_watchdog_verdict(sub_claim, sub_claim.get("modality", "text")))
        # Adopt the most conservative verdict
        if any(r.get("verdict") == "FALSE" for r in results):
            overall = "FALSE"
        elif any(r.get("verdict") == "REQUIRES_REVIEW" for r in results):
            overall = "REQUIRES_REVIEW"
        else:
            overall = "TRUE"
        return {"overall_verdict": overall, "components": results}
    else:
        return {"verdict": "TEXT_DEFAULT", "note": "Delegated to the existing text-only Watchdog"}


# ============================================================
# C3: SLA/SLO Formalization
# ============================================================

DEFAULT_SLA = {
    "phase_1_prompt_architect_ms": 30000,
    "phase_2_pm_orchestrator_ms": 60000,
    "phase_3a_researcher_ms": 180000,
    "phase_3b_watchdog_ms": 120000,
    "phase_3c_worker_ms": 300000,
    "phase_3c5_adversarial_ms": 90000,
    "phase_3c7_polisher_ms": 60000,
    "phase_4_verifier_ms": 90000,
    "session_total_ms": 1200000  # 20 min
}


def evaluate_sla_compliance(pm_plan, telemetry, default_sla=None):
    """
    Evaluate telemetry against pm_plan.sla or DEFAULT_SLA.

    Returns: {compliance_ratio, violations, summary}
    """
    sla = pm_plan.get("sla") or default_sla or DEFAULT_SLA
    violations = []
    compliant = []

    phase_metrics = telemetry.get("phase_metrics", {})
    for sla_key, target_ms in sla.items():
        actual_ms = 0
        if sla_key == "session_total_ms":
            actual_ms = telemetry.get("cumulative", {}).get("total_duration_ms", 0)
        else:
            # phase_1_prompt_architect_ms -> phase_metrics.prompt_architect.duration
            phase_name = sla_key.replace("_ms", "")
            for pname, pdata in phase_metrics.items():
                if pname in phase_name or phase_name.endswith(pname):
                    actual_ms = pdata.get("duration_ms", 0)
                    break

        if actual_ms == 0:
            continue  # Skip phases that were not run

        if actual_ms > target_ms:
            violations.append({
                "sla_key": sla_key,
                "target_ms": target_ms,
                "actual_ms": actual_ms,
                "breach_ratio": actual_ms / target_ms,
                "severity": "critical" if actual_ms > 2 * target_ms else "major"
            })
        else:
            compliant.append({"sla_key": sla_key, "target_ms": target_ms, "actual_ms": actual_ms})

    total = len(violations) + len(compliant)
    compliance_ratio = len(compliant) / total if total > 0 else 1.0
    return {
        "compliance_ratio": compliance_ratio,
        "violations": violations,
        "compliant": compliant,
        "summary": f"{len(compliant)}/{total} phases meet SLA",
        "verdict": "PASS" if compliance_ratio >= 0.9 else
                   "CONDITIONAL_PASS" if compliance_ratio >= 0.7 else "FAIL"
    }


def trigger_sla_breach_gate(violations):
    """Build user-gate data when SLA violations occur."""
    critical = [v for v in violations if v["severity"] == "critical"]
    if critical:
        return {
            "gate_id": "sla_breach",
            "decision_type": "direction",
            "options": ["accept_breach", "extend_budget", "abort_session", "rollback_to_checkpoint"],
            "data_to_present": {"critical_violations": critical, "total": len(violations)}
        }
    return None


# ============================================================
# C4: MCP Registry alignment (primary path)
# ============================================================
#
# Earlier revisions used search_plugins as primary and the Registry as a
# fallback; this implementation makes the Registry the primary path,
# abstracted to absorb external spec changes.

class MCPRegistryClient:
    """MCP Registry abstraction."""

    def __init__(self, endpoint=None, auth_token=None):
        self.endpoint = endpoint or os.environ.get("MCP_REGISTRY_ENDPOINT")
        self.auth_token = auth_token or os.environ.get("MCP_REGISTRY_AUTH_TOKEN")
        self.cache = {}

    def search(self, keywords, max_results=10):
        """
        Search the Registry by keyword.

        Only called when an endpoint is configured. Without one, an
        abstraction is returned so the caller can decide on a fallback.
        """
        if not self.endpoint:
            return {"status": "no_endpoint", "results": [], "fallback_to_search_plugins": True}

        cache_key = ":".join(sorted(keywords))
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Actual call depends on the environment (HTTP request abstraction).
        # This implementation is a placeholder; use `requests` etc. when
        # a real endpoint is wired in.
        result = {
            "status": "endpoint_set_but_http_not_implemented_in_this_module",
            "results": [],
            "note": "External calls are delegated to the caller (PM agent) via the search_plugins MCP tool"
        }
        self.cache[cache_key] = result
        return result

    def get_server_metadata(self, server_name):
        """Fetch metadata for a specific server (for security checks)."""
        return {"server": server_name, "metadata": "abstraction_only", "verified": False}


def search_plugins_priority(keywords, registry_client=None, fallback_search_func=None):
    """
    Registry primary, search_plugins fallback.

    Args:
        keywords: search keywords
        registry_client: MCPRegistryClient instance
        fallback_search_func: search_plugins MCP tool callable
    """
    # Step 1: try the Registry
    if registry_client:
        registry_result = registry_client.search(keywords)
        if registry_result.get("results"):
            return {"source": "mcp_registry_primary", "results": registry_result["results"]}

    # Step 2: search_plugins fallback
    if fallback_search_func:
        try:
            fallback_result = fallback_search_func(keywords)
            return {"source": "search_plugins_fallback", "results": fallback_result}
        except Exception as e:
            return {"source": "fallback_failed", "error": str(e), "results": []}

    return {"source": "no_search_available", "results": []}


# ============================================================
# C5: Benchmark Calibration
# ============================================================
#
# Calibrate the Verifier's internal quality_score against standard
# benchmark scores.
#
# Limitation: fetching real benchmark scores requires an external
# evaluation harness. This module only provides the calibration
# mapping function.

# Calibration mapping (internal 5-point scale -> estimated benchmark percentage)
# This mapping is a synthetic baseline; it needs to be refreshed after
# observing several real sessions.
DEFAULT_CALIBRATION = {
    "swe_bench_verified": {
        # mas_score -> swe_bench_estimate (%)
        1.0: 5,
        2.0: 15,
        3.0: 35,
        3.5: 50,
        4.0: 65,
        4.5: 75,
        5.0: 85
    },
    "osworld_verified": {
        1.0: 3,
        2.0: 8,
        3.0: 20,
        3.5: 30,
        4.0: 42,
        4.5: 52,
        5.0: 60
    }
}


def calibrate_to_benchmark(mas_score, benchmark="swe_bench_verified", calibration=None):
    """
    Map an internal MAS score onto an estimated benchmark score.

    Uses linear interpolation. Could be upgraded to isotonic regression
    once enough measured data accumulates.
    """
    cal = calibration or DEFAULT_CALIBRATION.get(benchmark)
    if not cal:
        return {"error": f"Unknown benchmark: {benchmark}"}

    sorted_pts = sorted(cal.items())
    if mas_score <= sorted_pts[0][0]:
        return {"benchmark": benchmark, "mas_score": mas_score,
                "estimated": sorted_pts[0][1], "method": "extrapolation_low"}
    if mas_score >= sorted_pts[-1][0]:
        return {"benchmark": benchmark, "mas_score": mas_score,
                "estimated": sorted_pts[-1][1], "method": "extrapolation_high"}
    # Linear interpolation
    for i in range(len(sorted_pts) - 1):
        x1, y1 = sorted_pts[i]
        x2, y2 = sorted_pts[i + 1]
        if x1 <= mas_score <= x2:
            ratio = (mas_score - x1) / (x2 - x1) if x2 != x1 else 0
            estimated = y1 + ratio * (y2 - y1)
            return {"benchmark": benchmark, "mas_score": mas_score,
                    "estimated": round(estimated, 1), "method": "linear_interp"}
    return {"error": "calibration_failed"}


def update_calibration_from_actual(mas_score, actual_benchmark_score, benchmark, persistent_dir):
    """
    Update the calibration mapping when real external benchmark scores arrive.

    With >= 5 samples, a simple-average update is suggested. With >= 30
    samples, consider isotonic regression or similar.
    """
    cal_path = Path(persistent_dir) / "calibration.json"
    if cal_path.exists():
        with open(cal_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"version": 1, "calibrations": {}}

    bench_data = data["calibrations"].setdefault(benchmark, {"observations": []})
    bench_data["observations"].append({
        "mas_score": mas_score,
        "actual_score": actual_benchmark_score,
        "timestamp": now_iso()
    })

    cal_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Recommend recalibration once >= 5 samples are collected
    return {"observations_count": len(bench_data["observations"]),
            "ready_for_recalibration": len(bench_data["observations"]) >= 5}


# ============================================================
# C6: Long-horizon Memory
# ============================================================
#
# Core ideas:
#   1) Compression (importance sampling + dedup)
#   2) Tiering (hot/warm/cold)
#   3) Adaptive retrieval (relevance scoring)


def compress_memory_acon_style(memories, target_size=None):
    """
    Memory compression in the ACON style.
    - Deduplicate (content hash)
    - Importance score (usage frequency + recency)
    - Keep the top N

    Limitation: a reasonable approximation rather than a faithful
    reproduction of the original algorithm.
    """
    if not memories:
        return []

    # Step 1: Dedup by content hash
    seen_hashes = {}
    deduped = []
    for mem in memories:
        content = mem.get("content", "")
        h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        if h not in seen_hashes:
            seen_hashes[h] = mem
            deduped.append(mem)
        else:
            # Duplicate: bump usage_count
            existing = seen_hashes[h]
            existing["usage_count"] = existing.get("usage_count", 1) + 1

    # Step 2: Importance score = usage_count * recency_factor
    now_ts = time.time()
    for mem in deduped:
        usage = mem.get("usage_count", 1)
        last_used_str = mem.get("metadata", {}).get("last_used", mem.get("timestamp", now_iso()))
        try:
            last_ts = datetime.fromisoformat(last_used_str.replace("Z", "+00:00")).timestamp()
            age_days = (now_ts - last_ts) / 86400
            recency_factor = math.exp(-age_days / 30)  # 30-day half-life
        except (ValueError, TypeError):
            recency_factor = 1.0
        mem["_importance_score"] = usage * recency_factor

    # Step 3: Keep the top N
    deduped.sort(key=lambda m: m.get("_importance_score", 0), reverse=True)
    if target_size and len(deduped) > target_size:
        deduped = deduped[:target_size]

    # cleanup
    for mem in deduped:
        mem.pop("_importance_score", None)

    return deduped


class HierarchicalMemory:
    """
    Self-organizing memory.

    Tiers:
      - hot: recently used (top N by LRU)
      - warm: medium frequency
      - cold: inactive

    Limitation: an LRU + frequency heuristic rather than a full
    self-organizing implementation.
    """

    def __init__(self, hot_size=10, warm_size=50):
        self.hot_size = hot_size
        self.warm_size = warm_size
        self.hot = OrderedDict()   # LRU
        self.warm = OrderedDict()
        self.cold = {}
        self.access_count = defaultdict(int)

    def add(self, memory_id, content, metadata=None):
        memory = {"id": memory_id, "content": content,
                  "metadata": metadata or {}, "added_at": now_iso()}
        self.hot[memory_id] = memory
        self.access_count[memory_id] = 1
        self._reorganize()
        return memory

    def get(self, memory_id):
        """Promote to the hot tier on access."""
        for tier_name, tier in [("hot", self.hot), ("warm", self.warm), ("cold", self.cold)]:
            if memory_id in tier:
                memory = tier.pop(memory_id) if tier_name != "cold" else tier[memory_id]
                if tier_name == "cold":
                    del self.cold[memory_id]
                self.hot[memory_id] = memory
                self.access_count[memory_id] += 1
                self._reorganize()
                return {"memory": memory, "promoted_from": tier_name}
        return None

    def _reorganize(self):
        """Demote hot overflow to warm, and warm overflow to cold."""
        while len(self.hot) > self.hot_size:
            oldest_id, memory = self.hot.popitem(last=False)
            self.warm[oldest_id] = memory
        while len(self.warm) > self.warm_size:
            oldest_id, memory = self.warm.popitem(last=False)
            self.cold[oldest_id] = memory

    def search(self, query_keywords, top_k=5):
        """Simple keyword-based search. Relevance = keyword matches + tier weight."""
        results = []
        tier_weight = {"hot": 1.5, "warm": 1.0, "cold": 0.5}
        for tier_name, tier in [("hot", self.hot), ("warm", self.warm), ("cold", self.cold)]:
            for mem_id, memory in tier.items():
                content = memory.get("content", "").lower()
                matches = sum(1 for kw in query_keywords if kw.lower() in content)
                if matches > 0:
                    score = matches * tier_weight[tier_name] * (1 + math.log1p(self.access_count[mem_id]))
                    results.append({"memory": memory, "tier": tier_name, "score": score})
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    def stats(self):
        return {
            "hot_count": len(self.hot),
            "warm_count": len(self.warm),
            "cold_count": len(self.cold),
            "total_accesses": sum(self.access_count.values())
        }


# ============================================================
# Self-test entry point
# ============================================================

if __name__ == "__main__":
    print("[C1] Causal Graph self-test")
    dag = CausalDAG()
    dag.add_edge("watchdog_pool_size", "verdict_accuracy")
    dag.add_edge("verdict_accuracy", "TARGET_QUALITY")
    dag.add_edge("token_budget", "TARGET_QUALITY")
    print(f"  acyclic: {dag.is_acyclic()}")
    print(f"  d-sep(watchdog_pool_size, token_budget | TARGET_QUALITY): "
          f"{dag.d_separation('watchdog_pool_size', 'token_budget', {'TARGET_QUALITY'})}")
    print(f"  backdoor for verdict_accuracy -> TARGET_QUALITY: "
          f"{dag.backdoor_set('verdict_accuracy', 'TARGET_QUALITY')}")

    print("\n[C2] Multi-modal Watchdog self-test")
    img_result = verify_image_url("https://upload.wikimedia.org/test.png")
    print(f"  image: {img_result['verdict']} - {img_result['checks']}")
    code_result = verify_code_block("def hello(): return 42")
    print(f"  code: {code_result['verdict']} - {code_result['checks']}")

    print("\n[C3] SLA self-test")
    sla_result = evaluate_sla_compliance(
        {}, {"phase_metrics": {"prompt_architect": {"duration_ms": 25000}}}
    )
    print(f"  compliance_ratio: {sla_result['compliance_ratio']}, verdict: {sla_result['verdict']}")

    print("\n[C4] MCP Registry self-test")
    client = MCPRegistryClient()
    print(f"  search no-endpoint: {client.search(['slack'])}")

    print("\n[C5] Calibration self-test")
    cal = calibrate_to_benchmark(3.5, "swe_bench_verified")
    print(f"  mas_score 3.5 -> swe_bench: {cal}")

    print("\n[C6] Long-horizon memory self-test")
    mem = HierarchicalMemory(hot_size=2, warm_size=3)
    for i in range(5):
        mem.add(f"m{i}", f"memory content {i}", {"tag": f"t{i}"})
    print(f"  stats after 5 adds: {mem.stats()}")
    search = mem.search(["content", "1"])
    print(f"  search 'content 1': {len(search)} results")

    print("\n[C6] ACON compression self-test")
    test_mems = [
        {"id": "m1", "content": "duplicate", "metadata": {"last_used": now_iso()}},
        {"id": "m2", "content": "duplicate", "metadata": {"last_used": now_iso()}},
        {"id": "m3", "content": "unique", "metadata": {"last_used": now_iso()}}
    ]
    compressed = compress_memory_acon_style(test_mems, target_size=5)
    print(f"  3 inputs (2 dup) -> {len(compressed)} compressed")
