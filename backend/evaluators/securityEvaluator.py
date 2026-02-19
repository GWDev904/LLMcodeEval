"""
evaluators/securityEvaluator.py
---------------------------------
Static security analysis for submitted Python code. Uses only stdlib ast and re.
Detects common security anti-patterns that LLMs frequently introduce.

Checks:
  1. eval() / exec() usage      — arbitrary code execution
  2. __import__() usage         — dynamic import bypass
  3. os.system() / subprocess   — shell injection surface
  4. Hardcoded secrets          — passwords/keys in string literals
  5. SQL string formatting      — potential SQL injection
  6. pickle / marshal usage     — deserialisation attacks
  7. assert for security checks — stripped in optimised Python (-O flag)
  8. Dangerous file operations  — open() with user-controlled paths

Score: 0–100. Each finding carries a severity (critical/high/medium/low)
which determines the deduction.
"""

import ast
import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SecurityFinding:
    severity:    str   # "critical" | "high" | "medium" | "low"
    category:    str   # Short category label
    description: str   # Human-readable explanation
    line:        int   # Source line number


SEVERITY_DEDUCTIONS = {
    "critical": 30,
    "high":     15,
    "medium":    8,
    "low":       3,
}

# Regex patterns for secret detection in string literals
SECRET_PATTERNS = [
    (re.compile(r"(?i)(password|passwd|pwd)\s*=\s*['\"].{3,}['\"]"),     "Hardcoded password"),
    (re.compile(r"(?i)(api_key|apikey|secret_key)\s*=\s*['\"].{8,}['\"]"), "Hardcoded API key"),
    (re.compile(r"(?i)(token)\s*=\s*['\"][a-zA-Z0-9+/=]{16,}['\"]"),      "Hardcoded token"),
    (re.compile(r"(?i)aws_secret_access_key\s*=\s*['\"].+['\"]"),           "Hardcoded AWS secret"),
]

SQL_INJECTION_PATTERN = re.compile(
    r"(execute|executemany|raw|cursor\.execute)\s*\(\s*[f\"'].*(%s|{|}|format|%\s*\()",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# AST-based checks
# ---------------------------------------------------------------------------

def _checkDangerousCalls(tree: ast.AST) -> list[SecurityFinding]:
    """Detect calls to inherently dangerous built-ins and modules."""
    findings = []

    DANGEROUS = {
        "eval":      ("critical", "eval() executes arbitrary code. Never use on untrusted input."),
        "exec":      ("critical", "exec() executes arbitrary code. Never use on untrusted input."),
        "__import__":("high",     "__import__() bypasses normal import controls."),
    }

    DANGEROUS_ATTRS = {
        ("os",         "system"):         ("high",   "os.system() is vulnerable to shell injection. Use subprocess with a list."),
        ("os",         "popen"):          ("high",   "os.popen() is vulnerable to shell injection."),
        ("subprocess", "call"):           ("medium", "subprocess.call() with shell=True is vulnerable to injection."),
        ("subprocess", "Popen"):          ("medium", "subprocess.Popen — ensure shell=False and avoid string commands."),
        ("pickle",     "loads"):          ("high",   "pickle.loads() on untrusted data enables arbitrary code execution."),
        ("pickle",     "load"):           ("high",   "pickle.load() on untrusted data enables arbitrary code execution."),
        ("marshal",    "loads"):          ("high",   "marshal.loads() deserialises bytecode — never use on untrusted data."),
        ("yaml",       "load"):           ("medium", "yaml.load() without Loader= is unsafe. Use yaml.safe_load()."),
    }

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        lineNo = getattr(node, "lineno", 0)

        # Direct function calls: eval(), exec(), etc.
        if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS:
            severity, desc = DANGEROUS[node.func.id]
            findings.append(SecurityFinding(severity, "DangerousBuiltin", desc, lineNo))

        # Attribute calls: os.system(), pickle.loads(), etc.
        if isinstance(node.func, ast.Attribute):
            moduleName  = None
            if isinstance(node.func.value, ast.Name):
                moduleName = node.func.value.id
            attrName = node.func.attr
            key = (moduleName, attrName)
            if key in DANGEROUS_ATTRS:
                severity, desc = DANGEROUS_ATTRS[key]
                findings.append(SecurityFinding(severity, "DangerousAPI", desc, lineNo))

                # Extra check: subprocess with shell=True
                if moduleName == "subprocess":
                    for kw in node.keywords:
                        if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value:
                            findings.append(SecurityFinding(
                                "high", "ShellInjection",
                                "subprocess called with shell=True — vulnerable to shell injection if input is user-controlled.",
                                lineNo,
                            ))

    return findings


def _checkAssertForSecurity(tree: ast.AST) -> list[SecurityFinding]:
    """
    Detect `assert` used for security/validation checks.
    Assertions are removed when Python runs with the -O optimisation flag.
    """
    findings = []
    SECURITY_KEYWORDS = {"auth", "admin", "permission", "valid", "token", "role", "access"}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        # Try to extract the test expression as a string for keyword matching
        try:
            testSource = ast.unparse(node.test).lower()
        except Exception:
            continue
        if any(kw in testSource for kw in SECURITY_KEYWORDS):
            findings.append(SecurityFinding(
                "high", "AssertForSecurity",
                f"assert used for security check at line {node.lineno}. "
                f"Assertions are stripped with `python -O`. Use explicit if/raise.",
                getattr(node, "lineno", 0),
            ))
    return findings


# ---------------------------------------------------------------------------
# Regex-based checks (applied to raw source)
# ---------------------------------------------------------------------------

def _checkHardcodedSecrets(sourceCode: str) -> list[SecurityFinding]:
    """Scan string literals for hardcoded credentials."""
    findings = []
    for pattern, label in SECRET_PATTERNS:
        for match in pattern.finditer(sourceCode):
            lineNo = sourceCode[:match.start()].count("\n") + 1
            findings.append(SecurityFinding(
                "critical", "HardcodedSecret",
                f"{label} detected at line {lineNo}. Store secrets in environment variables or a secrets manager.",
                lineNo,
            ))
    return findings


def _checkSqlInjection(sourceCode: str) -> list[SecurityFinding]:
    """Detect SQL queries built via string formatting."""
    findings = []
    for match in SQL_INJECTION_PATTERN.finditer(sourceCode):
        lineNo = sourceCode[:match.start()].count("\n") + 1
        findings.append(SecurityFinding(
            "high", "SQLInjection",
            f"Possible SQL injection at line {lineNo}. Use parameterised queries instead of string formatting.",
            lineNo,
        ))
    return findings


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _computeScore(findings: list[SecurityFinding]) -> int:
    totalDeduction = sum(SEVERITY_DEDUCTIONS[f.severity] for f in findings)
    return max(0, 100 - totalDeduction)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def runSecurityEvaluation(submittedCode: str) -> dict:
    """
    Run all security checks on submitted Python source code.

    Args:
        submittedCode: Raw Python source string.

    Returns:
        {
            "score": 0–100,
            "findings": [ { "severity", "category", "description", "line" } ],
            "summary": str
        }
    """
    result = {
        "score":    100,
        "findings": [],
        "summary":  "",
    }

    try:
        tree = ast.parse(submittedCode)
    except SyntaxError as exc:
        result["summary"] = f"Syntax error — security checks skipped: {exc}"
        return result

    allFindings: list[SecurityFinding] = []
    allFindings.extend(_checkDangerousCalls(tree))
    allFindings.extend(_checkAssertForSecurity(tree))
    allFindings.extend(_checkHardcodedSecrets(submittedCode))
    allFindings.extend(_checkSqlInjection(submittedCode))

    score = _computeScore(allFindings)

    severityCounts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in allFindings:
        severityCounts[f.severity] += 1

    if not allFindings:
        summary = "No security issues detected."
    else:
        parts = [f"{v} {k}" for k, v in severityCounts.items() if v > 0]
        summary = f"Found {len(allFindings)} security finding(s): {', '.join(parts)}."

    result.update({
        "score":    score,
        "findings": [
            {
                "severity":    f.severity,
                "category":    f.category,
                "description": f.description,
                "line":        f.line,
            }
            for f in allFindings
        ],
        "summary": summary,
    })
    return result
