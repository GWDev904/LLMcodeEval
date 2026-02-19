"""
evaluators/complexityEvaluator.py
----------------------------------
Performs static analysis on submitted Python code to assess:

  1. Cyclomatic complexity  — number of independent paths through the code.
     High cyclomatic complexity (>10) signals hard-to-maintain code.

  2. Nested loop depth      — deeply nested loops often indicate O(n^k) algorithms.

  3. Recursive call detection — flags recursion so the reviewer knows to
     consider stack depth / memoization.

  4. Built-in complexity hints — detects usage of sorted(), set(), dict()
     which carry their own complexity implications.

Uses only Python stdlib (ast module) — no external dependencies required.

Score: 0–100. Penalised for high cyclomatic complexity and deep nesting.
"""

import ast
import textwrap
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class FunctionMetrics(NamedTuple):
    name:              str
    cyclomaticScore:   int   # Raw cyclomatic complexity count
    maxNestDepth:      int   # Deepest loop/conditional nesting
    isRecursive:       bool
    lineCount:         int


# ---------------------------------------------------------------------------
# AST visitors
# ---------------------------------------------------------------------------

class _CyclomaticVisitor(ast.NodeVisitor):
    """
    Count decision points to compute McCabe cyclomatic complexity.
    Each of the following adds 1: if, elif, for, while, except, with,
    assert, comprehension (if clause), boolean operators (and/or).
    """

    DECISION_NODE_TYPES = (
        ast.If, ast.For, ast.While, ast.ExceptHandler,
        ast.With, ast.Assert, ast.comprehension,
    )

    def __init__(self):
        self.count = 1  # Base complexity is always 1

    def visit_If(self, node):
        self.count += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.count += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.count += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.count += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        # Each extra operand in `and`/`or` chain adds a branch
        self.count += len(node.values) - 1
        self.generic_visit(node)

    def visit_comprehension(self, node):
        # Each `if` inside a comprehension
        self.count += len(node.ifs)
        self.generic_visit(node)


class _NestingDepthVisitor(ast.NodeVisitor):
    """
    Track the maximum nesting depth of loops and conditionals.
    """

    NESTING_NODES = (ast.For, ast.While, ast.If)

    def __init__(self):
        self.maxDepth    = 0
        self._currentDepth = 0

    def _visitNested(self, node):
        self._currentDepth += 1
        self.maxDepth = max(self.maxDepth, self._currentDepth)
        self.generic_visit(node)
        self._currentDepth -= 1

    def visit_For(self, node):   self._visitNested(node)
    def visit_While(self, node): self._visitNested(node)
    def visit_If(self, node):    self._visitNested(node)


def _detectRecursion(funcNode: ast.FunctionDef) -> bool:
    """
    Return True if the function contains a call to itself by name.
    Handles direct recursion only (not mutual recursion).
    """
    funcName = funcNode.name
    for node in ast.walk(funcNode):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == funcName:
                return True
    return False


def _detectBuiltinHints(tree: ast.AST) -> list[str]:
    """
    Scan for calls to Python builtins that imply specific complexity:
      sorted()    → O(n log n)
      set()/dict()→ O(n) construction but O(1) lookup
      reversed()  → O(n)
      enumerate() → neutral but good practice note
    """
    HINTS = {
        "sorted":   "Uses sorted() — O(n log n) time.",
        "sort":     "Uses list.sort() — O(n log n) in-place.",
        "set":      "Uses set() — O(n) construction, O(1) average lookup.",
        "dict":     "Uses dict() — O(n) construction, O(1) average lookup.",
        "reversed": "Uses reversed() — O(n) traversal.",
    }
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            funcName = None
            if isinstance(node.func, ast.Name):
                funcName = node.func.id
            elif isinstance(node.func, ast.Attribute):
                funcName = node.func.attr
            if funcName and funcName in HINTS and HINTS[funcName] not in found:
                found.append(HINTS[funcName])
    return found


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _scoreFromMetrics(metrics: list[FunctionMetrics]) -> int:
    """
    Convert raw metrics into a 0–100 quality score.

    Deductions:
      - Cyclomatic complexity > 5:  -5 per point above 5 (max -30)
      - Cyclomatic complexity > 10: additional -5 per point above 10 (max -20)
      - Nesting depth > 2:          -10 per extra level (max -30)
      - Recursive without obvious memoisation: -5 (informational)

    Score starts at 100 and deductions are applied per-function, then averaged.
    """
    if not metrics:
        return 50  # No functions found — neutral score

    functionScores = []
    for m in metrics:
        score = 100

        # Cyclomatic complexity penalty
        if m.cyclomaticScore > 10:
            score -= min(30, (m.cyclomaticScore - 10) * 5)
            score -= min(20, (m.cyclomaticScore - 5) * 3)
        elif m.cyclomaticScore > 5:
            score -= min(20, (m.cyclomaticScore - 5) * 4)

        # Nesting depth penalty
        if m.maxNestDepth > 2:
            score -= min(30, (m.maxNestDepth - 2) * 10)

        functionScores.append(max(0, score))

    return int(sum(functionScores) / len(functionScores))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def runComplexityEvaluation(submittedCode: str) -> dict:
    """
    Analyse the cyclomatic complexity and nesting depth of submitted Python code.

    Args:
        submittedCode: Raw Python source string.

    Returns:
        {
            "score": 0–100,
            "functions": [ { name, cyclomaticScore, maxNestDepth, isRecursive, lineCount } ],
            "builtinHints": [ "Uses sorted() — O(n log n) time.", ... ],
            "summary": "Human-readable summary string",
            "warnings": [ "..." ]
        }
    """
    result = {
        "score":        0,
        "functions":    [],
        "builtinHints": [],
        "summary":      "",
        "warnings":     [],
    }

    try:
        tree = ast.parse(submittedCode)
    except SyntaxError as exc:
        result["summary"]  = f"Syntax error — could not parse: {exc}"
        result["warnings"] = [str(exc)]
        return result

    functionMetrics = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Cyclomatic complexity
        cyclomaticVisitor = _CyclomaticVisitor()
        cyclomaticVisitor.visit(node)

        # Nesting depth
        nestingVisitor = _NestingDepthVisitor()
        nestingVisitor.visit(node)

        lineCount = (node.end_lineno - node.lineno + 1) if hasattr(node, "end_lineno") else 0

        metrics = FunctionMetrics(
            name            = node.name,
            cyclomaticScore = cyclomaticVisitor.count,
            maxNestDepth    = nestingVisitor.maxDepth,
            isRecursive     = _detectRecursion(node),
            lineCount       = lineCount,
        )
        functionMetrics.append(metrics)

    builtinHints = _detectBuiltinHints(tree)
    score        = _scoreFromMetrics(functionMetrics)

    # Build warnings list
    warnings = []
    for m in functionMetrics:
        if m.cyclomaticScore > 10:
            warnings.append(
                f"'{m.name}' has high cyclomatic complexity ({m.cyclomaticScore}). "
                f"Consider breaking it into smaller functions."
            )
        if m.maxNestDepth > 3:
            warnings.append(
                f"'{m.name}' has deep nesting (depth={m.maxNestDepth}). "
                f"This often indicates O(n^k) time complexity."
            )
        if m.isRecursive:
            warnings.append(
                f"'{m.name}' is recursive. Ensure base cases are correct "
                f"and consider memoisation for overlapping subproblems."
            )

    # Human-readable summary
    if not functionMetrics:
        summary = "No top-level functions detected."
    else:
        avgCyclomatic = sum(m.cyclomaticScore for m in functionMetrics) / len(functionMetrics)
        summary = (
            f"Analysed {len(functionMetrics)} function(s). "
            f"Average cyclomatic complexity: {avgCyclomatic:.1f}. "
            f"{'No major complexity issues detected.' if score >= 80 else 'Complexity issues found — see warnings.'}"
        )

    result.update({
        "score":        score,
        "functions":    [m._asdict() for m in functionMetrics],
        "builtinHints": builtinHints,
        "summary":      summary,
        "warnings":     warnings,
    })
    return result
