"""
evaluators/correctnessEvaluator.py
-----------------------------------
Runs submitted Python code against a problem's test cases in an isolated
subprocess sandbox. Each test case is executed independently so one crash
does not block the others.

Evaluation dimensions:
  - correctness:   Does the function return the expected output?
  - edge cases:    Does it handle the problem's designated tricky inputs?
  - robustness:    Does it raise exceptions on invalid input gracefully?

Score: 0-100 (weighted by test case importance flags in the problem spec).
"""

import json
import subprocess
import sys
import textwrap
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SANDBOX_TIMEOUT_SECONDS = 5   # Kill runaway solutions after 5 s
MAX_OUTPUT_CHARS        = 500  # Truncate stdout to avoid flooding


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _buildRunnerScript(submittedCode: str, functionCall: str, preamble: str = "") -> str:
    """
    Wrap the submitted code + a single function call in a minimal Python
    script that prints the result as JSON to stdout.

    Args:
        submittedCode: The full source of the user's solution.
        functionCall:  A Python expression string, e.g. "twoSum([2,7], 9)".
        preamble:      Optional code to inject before the solution (e.g. TreeNode class).

    Returns:
        A self-contained Python script string ready to execute.
    """
    dedentedCode = textwrap.dedent(submittedCode)

    parts = ["import json, sys\n"]
    if preamble:
        parts.append("# ---- Problem preamble ----\n")
        parts.append(textwrap.dedent(preamble))
        parts.append("\n")
    parts.append("# ---- Submitted solution ----\n")
    parts.append(dedentedCode)
    parts.append("\n\n# ---- Test driver ----\n")
    parts.append("try:\n")
    parts.append(f"    result = {functionCall}\n")
    parts.append('    print(json.dumps({"status": "ok", "result": result}))\n')
    parts.append("except Exception as exc:\n")
    parts.append('    print(json.dumps({"status": "error", "error": str(exc)}))\n')

    return "".join(parts)


def _runInSandbox(script: str) -> dict:
    """
    Execute a Python script in a subprocess with a hard timeout.

    Args:
        script: Full Python source to execute.

    Returns:
        Dict with keys: status ("ok" | "error" | "timeout"), result or error.
    """
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=SANDBOX_TIMEOUT_SECONDS,
        )
        rawOutput = proc.stdout.strip()
        if not rawOutput:
            stderrSnippet = proc.stderr[:MAX_OUTPUT_CHARS].strip()
            return {"status": "error", "error": stderrSnippet or "No output produced."}

        # Only parse the last non-empty line (handles print() inside solutions)
        lastLine = [l for l in rawOutput.splitlines() if l.strip()][-1]
        return json.loads(lastLine)

    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": f"Exceeded {SANDBOX_TIMEOUT_SECONDS}s time limit."}
    except json.JSONDecodeError:
        return {"status": "error", "error": f"Could not parse output: {rawOutput[:MAX_OUTPUT_CHARS]}"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _valuesMatch(actual: Any, expected: Any, ordered: bool = True) -> bool:
    """
    Flexible equality check supporting:
      - Unordered list comparison (for problems where order doesn't matter)
      - Nested structures
      - Floating-point tolerance (1e-6)
      - None / null comparison

    Args:
        actual:   The value returned by the submitted code.
        expected: The ground-truth value from the problem spec.
        ordered:  If False, sort lists before comparing.
    """
    if expected is None:
        return actual is None

    if isinstance(expected, float) or isinstance(actual, float):
        try:
            return abs(float(actual) - float(expected)) < 1e-6
        except (TypeError, ValueError):
            return False

    if isinstance(expected, list) and isinstance(actual, list):
        if not ordered:
            try:
                return sorted(actual) == sorted(expected)
            except TypeError:
                return sorted(map(str, actual)) == sorted(map(str, expected))
        return actual == expected

    return actual == expected


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def runCorrectnessEvaluation(submittedCode: str, problem: dict) -> dict:
    """
    Evaluate submitted code against all test cases defined in the problem.

    Problem spec fields used:
        testCases (list):       Visible test cases shown to the user.
        hiddenTestCases (list): Hidden edge cases not shown to the user.
            Each case: { "args": "...", "expected": ..., "label": "...",
                         "ordered": bool, "weight": int }
        preamble (str):         Optional code injected before the solution.

    Args:
        submittedCode: The user's Python solution as a string.
        problem:       The full parsed problem JSON.

    Returns:
        {
            "score": 0-100,
            "passed": int,
            "total": int,
            "testResults": [ { "label", "status", "expected", "actual", "hidden" } ]
        }
    """
    preamble = problem.get("preamble", "")
    allTestCases = []

    for tc in problem.get("testCases", []):
        allTestCases.append({**tc, "hidden": False})

    for tc in problem.get("hiddenTestCases", []):
        allTestCases.append({**tc, "hidden": True})

    testResults  = []
    totalWeight  = 0
    earnedWeight = 0

    for tc in allTestCases:
        label        = tc.get("label", "Unnamed test")
        functionCall = tc.get("args", "")
        expected     = tc.get("expected")
        ordered      = tc.get("ordered", True)
        weight       = tc.get("weight", 1)

        totalWeight += weight

        script  = _buildRunnerScript(submittedCode, functionCall, preamble)
        outcome = _runInSandbox(script)

        if outcome["status"] == "ok":
            actual = outcome["result"]
            passed = _valuesMatch(actual, expected, ordered=ordered)
            status = "pass" if passed else "fail"
            if passed:
                earnedWeight += weight
        else:
            actual = None
            status = outcome["status"]  # "error" or "timeout"

        testResults.append({
            "label":    label,
            "status":   status,
            "expected": expected,
            "actual":   actual,
            "error":    outcome.get("error") if outcome["status"] != "ok" else None,
            "hidden":   tc["hidden"],
            "weight":   weight,
        })

    score  = int((earnedWeight / totalWeight) * 100) if totalWeight > 0 else 0
    passed = sum(1 for r in testResults if r["status"] == "pass")

    return {
        "score":       score,
        "passed":      passed,
        "total":       len(allTestCases),
        "testResults": testResults,
    }
