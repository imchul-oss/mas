"""
Senior Engineer Test Objective Metric

Senior Engineer Test was qualitative; this module adds quantitative metrics.

Objective metrics (Python `ast` standard module, zero external dependencies):
1. LOC delta - line count before/after change
2. Cyclomatic complexity - branching complexity (self-implemented)
3. Unused symbols - unused import / function / variable
4. Speculative features - unused abstractions
5. Dead code - unreachable code

Feeds directly into the 10th dimension (senior_engineer_test) of the Verifier score.
"""

import ast
import re
from collections import defaultdict
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# Metric 1: LOC Delta
# ============================================================

def loc_delta(before_code, after_code):
    """LOC difference before/after change."""
    before = _count_loc(before_code)
    after = _count_loc(after_code)
    return {
        "before_loc": before,
        "after_loc": after,
        "delta": after - before,
        "delta_ratio": (after - before) / before if before > 0 else 0
    }


def _count_loc(code):
    """LOC excluding comments and blank lines."""
    if not code:
        return 0
    lines = code.split("\n")
    return sum(1 for ln in lines
               if ln.strip() and not ln.strip().startswith("#"))


# ============================================================
# Metric 2: Cyclomatic Complexity (ast-based)
# ============================================================

class CyclomaticVisitor(ast.NodeVisitor):
    """
    Cyclomatic complexity.
    +1 per branch: if, elif, for, while, try, except, with, and, or, ternary.
    """

    def __init__(self):
        self.complexity = 1  # base

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        # and / or
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_IfExp(self, node):
        # ternary
        self.complexity += 1
        self.generic_visit(node)


def cyclomatic_complexity(code):
    """Per-function cyclomatic complexity analysis."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"error": f"syntax_error: {str(e)[:100]}"}

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visitor = CyclomaticVisitor()
            visitor.visit(node)
            functions.append({
                "name": node.name,
                "lineno": node.lineno,
                "complexity": visitor.complexity,
                "rating": _rate_complexity(visitor.complexity)
            })

    return {
        "functions": functions,
        "total_functions": len(functions),
        "avg_complexity": (sum(f["complexity"] for f in functions) / len(functions)
                           if functions else 0),
        "max_complexity": max((f["complexity"] for f in functions), default=0),
        "high_complexity_count": sum(1 for f in functions if f["complexity"] > 10)
    }


def _rate_complexity(c):
    """Complexity rating."""
    if c <= 5: return "A (simple)"
    if c <= 10: return "B (low)"
    if c <= 20: return "C (moderate)"
    if c <= 30: return "D (more than moderate)"
    if c <= 40: return "E (high)"
    return "F (very high)"


# ============================================================
# Metric 3: Unused Symbols
# ============================================================

def detect_unused_imports(code):
    """Imported but unused symbols."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported.add(alias.asname or alias.name)

    # Collect all Name nodes
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            # For x.y.z, extract only the root x
            n = node
            while isinstance(n, ast.Attribute):
                n = n.value
            if isinstance(n, ast.Name):
                used.add(n.id)

    return sorted(imported - used)


def detect_unused_functions(code):
    """Functions defined but never called (single-file scope)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    defined = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):  # exclude private
                defined[node.name] = node.lineno

    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)

    unused = [name for name in defined if name not in called]
    return [{"name": n, "lineno": defined[n]} for n in unused]


# ============================================================
# Metric 4 + 5: Speculative Features & Dead Code
# ============================================================

def detect_speculative_features(code):
    """
    Speculative feature candidates:
    - TODO / FIXME / XXX comments
    - Unused abstract base class or single-use class
    - Functions with empty 'kwargs' (over-flexibility candidate)
    """
    findings = []

    # TODO / FIXME
    for m in re.finditer(r"#\s*(TODO|FIXME|XXX|HACK)[:\s](.{0,80})", code):
        findings.append({
            "type": "todo_marker",
            "marker": m.group(1),
            "context": m.group(2).strip(),
            "lineno": code[:m.start()].count("\n") + 1
        })

    # Single-use class
    try:
        tree = ast.parse(code)
        class_defs = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_defs[node.name] = node.lineno

        class_uses = defaultdict(int)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in class_defs:
                class_uses[node.id] += 1

        for cname, lineno in class_defs.items():
            if class_uses[cname] <= 1:  # only definition itself counted
                findings.append({
                    "type": "single_use_class",
                    "name": cname,
                    "lineno": lineno,
                    "uses": class_uses[cname]
                })
    except SyntaxError:
        pass

    return findings


def detect_dead_code(code):
    """Simple dead code detection: code after return, unreachable branches."""
    findings = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return findings

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            for i, stmt in enumerate(body[:-1]):
                if isinstance(stmt, ast.Return):
                    findings.append({
                        "type": "after_return",
                        "function": node.name,
                        "lineno": body[i+1].lineno
                    })
                    break
                if isinstance(stmt, ast.Raise):
                    findings.append({
                        "type": "after_raise",
                        "function": node.name,
                        "lineno": body[i+1].lineno
                    })
                    break

    return findings


# ============================================================
# Aggregate: Senior Engineer Test Score
# ============================================================

def senior_engineer_test_score(code, original_code=None):
    """
    Quantitative version of the "200->50" simplification test.

    Returns: {
        "score": 1-5,
        "criteria": "...",
        "metrics": {...},
        "estimated_simplification_potential": "0-50%",
        "concrete_findings": [...]
    }
    """
    # 1. Basic stats
    loc = _count_loc(code)

    # 2. Complexity
    complexity = cyclomatic_complexity(code)

    # 3. Unused
    unused_imports = detect_unused_imports(code)
    unused_funcs = detect_unused_functions(code)

    # 4. Speculative
    speculative = detect_speculative_features(code)

    # 5. Dead code
    dead = detect_dead_code(code)

    # 6. Optional LOC delta
    delta = loc_delta(original_code, code) if original_code else None

    # Score calculation
    score = 5
    issues = []

    # Complexity penalty
    if isinstance(complexity, dict) and "max_complexity" in complexity:
        if complexity["max_complexity"] > 30:
            score -= 2
            issues.append(f"max complexity {complexity['max_complexity']} (severe)")
        elif complexity["max_complexity"] > 20:
            score -= 1
            issues.append(f"max complexity {complexity['max_complexity']} (high)")
        if complexity["high_complexity_count"] > 0:
            score -= 0.5
            issues.append(f"{complexity['high_complexity_count']} functions with complexity > 10")

    # Unused penalty
    n_unused = len(unused_imports) + len(unused_funcs)
    if n_unused > 5:
        score -= 1
        issues.append(f"{n_unused} unused symbols")
    elif n_unused > 2:
        score -= 0.5
        issues.append(f"{n_unused} unused symbols")

    # Speculative penalty
    if len(speculative) > 3:
        score -= 0.5
        issues.append(f"{len(speculative)} speculative features")

    # Dead code penalty
    if dead:
        score -= 0.5
        issues.append(f"{len(dead)} dead code blocks")

    score = max(1, min(5, round(score)))

    # Simplification estimate
    base_potential = 0
    if isinstance(complexity, dict) and complexity.get("max_complexity", 0) > 10:
        base_potential += min(0.3, (complexity["max_complexity"] - 10) * 0.02)
    if n_unused > 0:
        base_potential += min(0.2, n_unused * 0.03)
    if dead:
        base_potential += min(0.1, len(dead) * 0.02)
    if speculative:
        base_potential += min(0.15, len(speculative) * 0.02)
    simp_estimate = round(min(0.5, base_potential), 2)

    return {
        "score": score,
        "criteria": "'200->50' simplification test (objective metric)",
        "metrics": {
            "loc": loc,
            "cyclomatic": complexity,
            "unused_imports": unused_imports,
            "unused_functions": unused_funcs,
            "speculative_features": speculative,
            "dead_code": dead,
            "loc_delta": delta
        },
        "estimated_simplification_potential": f"{simp_estimate*100:.0f}%",
        "concrete_findings": issues
    }


# ============================================================
# Self-test
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Senior Engineer Test Metric")
    print("=" * 60)

    sample = '''
import json
import os  # unused
import re

def calculate(x, y):
    if x > 0:
        if y > 0:
            return x + y
        else:
            return x - y
    elif x < 0:
        return -x
    return 0
    print("never reached")  # dead code

def unused_function():
    pass

class SingleUseClass:
    def __init__(self):
        self.x = 1

# TODO: refactor this later
def complex_func(a, b, c, d, e):
    if a > 0 and b > 0 and c > 0:
        if d > 0 or e > 0:
            return a + b + c + d + e
        elif d == 0:
            for i in range(10):
                if i % 2 == 0:
                    print(i)
    return 0
'''

    result = senior_engineer_test_score(sample)
    print(f"\nScore: {result['score']}/5")
    print(f"Criteria: {result['criteria']}")
    print(f"Simplification potential: {result['estimated_simplification_potential']}")
    print(f"\nFindings:")
    for f in result['concrete_findings']:
        print(f"  - {f}")
    print(f"\nUnused imports: {result['metrics']['unused_imports']}")
    print(f"Unused functions: {[f['name'] for f in result['metrics']['unused_functions']]}")
    print(f"Speculative features: {len(result['metrics']['speculative_features'])}")
    print(f"Dead code blocks: {len(result['metrics']['dead_code'])}")
    print(f"\nCyclomatic:")
    for f in result['metrics']['cyclomatic'].get('functions', []):
        print(f"  {f['name']} (line {f['lineno']}): {f['complexity']} ({f['rating']})")
