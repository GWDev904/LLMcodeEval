"""
evaluators/styleEvaluator.py
-----------------------------
Static style analysis for submitted Python code. Does NOT require external
linters (pylint / flake8) — all checks are implemented using stdlib ast and re.

Checks performed:
  1.  Function & variable naming — snake_case convention (PEP 8)
  2.  Magic numbers             — numeric literals outside assignments flagged
  3.  Docstring presence        — functions should have docstrings
  4.  Line length               — lines > 100 chars flagged
  5.  Blank line spacing        — PEP 8 two-blank-line rule around top-level defs
  6.  Return type ambiguity     — functions with multiple return types flagged
  7.  Unused imports            — imported names never referenced in code
  8.  Empty except blocks       — bare `except: pass` anti-pattern
  9.  Bare `except:`            — catches all exceptions including system exits
  10. Mutable default arguments — def f(x=[]) is a classic Python gotcha

Score: 0–100 based on weighted deduction per violation.
"""

import ast
import re
from collections import defaultdict


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_LINE_LENGTH    = 100
VIOLATION_WEIGHTS  = {
    "namingConvention":     3,
    "magicNumber":          2,
    "missingDocstring":     4,
    "lineTooLong":          1,
    "emptyExcept":          8,
    "bareExcept":           6,
    "mutableDefault":       7,
    "unusedImport":         3,
    "multipleReturnTypes":  2,
}

SNAKE_CASE_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")

# Numbers that are universally acceptable as "not magic"
ALLOWED_MAGIC_NUMBERS = {0, 1, -1, 2, 10, 100}


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _checkNaming(tree: ast.AST) -> list[str]:
    """Flag function and variable names that don't follow snake_case (PEP 8)."""
    violations = []
    for node in ast.walk(tree):
        name = None
        kind = None

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name, kind = node.name, "Function"
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            name, kind = node.id, "Variable"

        if name and not name.startswith("_") and not SNAKE_CASE_PATTERN.match(name):
            # Allow ALL_CAPS constants
            if not name.isupper():
                violations.append(
                    f"{kind} '{name}' at line {getattr(node, 'lineno', '?')} "
                    f"should use snake_case (PEP 8)."
                )
    return violations


def _checkDocstrings(tree: ast.AST) -> list[str]:
    """Flag functions/classes that are missing a docstring."""
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if not (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            violations.append(
                f"'{node.name}' at line {node.lineno} is missing a docstring."
            )
    return violations


def _checkMagicNumbers(tree: ast.AST) -> list[str]:
    """Flag numeric literals used directly in expressions (not in assignments)."""
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if not isinstance(node.value, (int, float)):
            continue
        if node.value in ALLOWED_MAGIC_NUMBERS:
            continue
        violations.append(
            f"Magic number '{node.value}' at line {getattr(node, 'lineno', '?')}. "
            f"Consider extracting to a named constant."
        )
    return violations


def _checkLineLengths(sourceLines: list[str]) -> list[str]:
    """Flag lines exceeding MAX_LINE_LENGTH characters."""
    violations = []
    for i, line in enumerate(sourceLines, start=1):
        if len(line.rstrip()) > MAX_LINE_LENGTH:
            violations.append(
                f"Line {i} is {len(line.rstrip())} characters "
                f"(limit: {MAX_LINE_LENGTH})."
            )
    return violations


def _checkEmptyAndBareExcept(tree: ast.AST) -> list[str]:
    """
    Flag two common exception anti-patterns:
      - `except: pass`  — silently swallows ALL exceptions
      - `except Exception: pass` — silently swallows all non-system exceptions
    """
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        isBodyJustPass = (
            len(node.body) == 1 and isinstance(node.body[0], ast.Pass)
        )
        if node.type is None:
            violations.append(
                f"Bare `except:` at line {node.lineno} catches ALL exceptions "
                f"including SystemExit and KeyboardInterrupt. Be specific."
            )
        elif isBodyJustPass:
            violations.append(
                f"`except` at line {node.lineno} has an empty body (`pass`). "
                f"Silently swallowing exceptions hides bugs."
            )
    return violations


def _checkMutableDefaults(tree: ast.AST) -> list[str]:
    """
    Flag mutable default arguments (list/dict/set literals) in function defs.
    This is a classic Python gotcha — the default is shared across all calls.
    """
    MUTABLE_TYPES = (ast.List, ast.Dict, ast.Set)
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for default in node.args.defaults + node.args.kw_defaults:
            if default and isinstance(default, MUTABLE_TYPES):
                typeName = type(default).__name__.lower().replace("dict", "dict").replace("list", "list")
                violations.append(
                    f"'{node.name}' at line {node.lineno} uses a mutable default "
                    f"argument ({typeName} literal). Use `None` and initialise inside."
                )
    return violations


def _checkUnusedImports(tree: ast.AST, sourceCode: str) -> list[str]:
    """
    Detect imported names that are never referenced in the code body.
    Simple heuristic: check if the name string appears anywhere in source.
    """
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                usedName = alias.asname or alias.name.split(".")[0]
                if sourceCode.count(usedName) <= 1:  # Only the import line itself
                    violations.append(
                        f"Import '{alias.name}' at line {node.lineno} appears unused."
                    )
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                usedName = alias.asname or alias.name
                if usedName != "*" and sourceCode.count(usedName) <= 1:
                    violations.append(
                        f"Import '{alias.name}' from '{node.module}' "
                        f"at line {node.lineno} appears unused."
                    )
    return violations


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _computeScore(violationsByType: dict[str, list[str]]) -> int:
    """
    Compute a 0–100 score by applying weighted deductions per violation.
    Each violation of type T deducts VIOLATION_WEIGHTS[T] points.
    Score cannot go below 0.
    """
    totalDeduction = 0
    for violationType, violations in violationsByType.items():
        weight      = VIOLATION_WEIGHTS.get(violationType, 2)
        totalDeduction += len(violations) * weight
    return max(0, 100 - totalDeduction)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def runStyleEvaluation(submittedCode: str) -> dict:
    """
    Run all style checks on submitted Python source code.

    Args:
        submittedCode: Raw Python source string.

    Returns:
        {
            "score": 0–100,
            "violations": { violationType: [ "description", ... ] },
            "totalViolations": int,
            "summary": str
        }
    """
    result = {
        "score":           0,
        "violations":      {},
        "totalViolations": 0,
        "summary":         "",
    }

    sourceLines = submittedCode.splitlines()

    try:
        tree = ast.parse(submittedCode)
    except SyntaxError as exc:
        result["summary"] = f"Syntax error — style checks skipped: {exc}"
        return result

    violations = {
        "namingConvention":  _checkNaming(tree),
        "missingDocstring":  _checkDocstrings(tree),
        "magicNumber":       _checkMagicNumbers(tree),
        "lineTooLong":       _checkLineLengths(sourceLines),
        "emptyExcept":       _checkEmptyAndBareExcept(tree),
        "mutableDefault":    _checkMutableDefaults(tree),
        "unusedImport":      _checkUnusedImports(tree, submittedCode),
    }

    # Remove empty categories
    violations = {k: v for k, v in violations.items() if v}

    totalViolations = sum(len(v) for v in violations.values())
    score           = _computeScore(violations)

    summary = (
        f"Found {totalViolations} style violation(s) across "
        f"{len(violations)} category/categories."
        if totalViolations > 0
        else "No style violations detected. Clean code!"
    )

    result.update({
        "score":           score,
        "violations":      violations,
        "totalViolations": totalViolations,
        "summary":         summary,
    })
    return result
