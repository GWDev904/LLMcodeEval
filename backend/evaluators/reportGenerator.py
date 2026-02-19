"""
evaluators/reportGenerator.py
------------------------------
Assembles the outputs of all individual evaluators into a single, unified
evaluation report. Computes a weighted overall score and generates a
human-readable summary with actionable recommendations.

Score weights (must sum to 1.0):
  Correctness : 0.50  — Does the code produce correct results?
  Complexity  : 0.20  — Is the algorithm efficient?
  Style       : 0.15  — Is the code readable and idiomatic?
  Security    : 0.15  — Is the code free of security anti-patterns?
"""

from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCORE_WEIGHTS = {
    "correctness": 0.50,
    "complexity":  0.20,
    "style":       0.15,
    "security":    0.15,
}

GRADE_THRESHOLDS = [
    (90, "A",  "Excellent — production-ready quality."),
    (80, "B",  "Good — minor improvements suggested."),
    (70, "C",  "Acceptable — several areas need attention."),
    (60, "D",  "Below average — significant issues present."),
    (0,  "F",  "Failing — fundamental problems detected."),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _computeOverallScore(
    correctnessScore: int,
    complexityScore:  int,
    styleScore:       int,
    securityScore:    int,
) -> int:
    """
    Compute the weighted overall score from the four dimension scores.

    Returns an integer 0–100.
    """
    weighted = (
        correctnessScore * SCORE_WEIGHTS["correctness"]
        + complexityScore  * SCORE_WEIGHTS["complexity"]
        + styleScore       * SCORE_WEIGHTS["style"]
        + securityScore    * SCORE_WEIGHTS["security"]
    )
    return int(round(weighted))


def _assignGrade(overallScore: int) -> tuple[str, str]:
    """
    Map a numeric score to a letter grade and label.

    Returns: (grade, label) e.g. ("B", "Good — minor improvements suggested.")
    """
    for threshold, grade, label in GRADE_THRESHOLDS:
        if overallScore >= threshold:
            return grade, label
    return "F", "Failing"


def _buildRecommendations(
    correctness: dict,
    complexity:  dict,
    style:       dict,
    security:    dict,
) -> list[str]:
    """
    Derive a prioritised list of actionable recommendations from all evaluators.
    Recommendations are ordered: correctness → security → complexity → style.
    """
    recommendations = []

    # Correctness failures
    failedTests = [
        t for t in correctness.get("testResults", [])
        if t["status"] in ("fail", "error", "timeout")
    ]
    if failedTests:
        failCount = len(failedTests)
        recommendations.append(
            f"Fix {failCount} failing test case(s). Start with visible failures before tackling hidden edge cases."
        )

    # Security issues (highest priority after correctness)
    criticalFindings = [
        f for f in security.get("findings", [])
        if f["severity"] in ("critical", "high")
    ]
    for finding in criticalFindings[:3]:  # Cap at 3 to avoid noise
        recommendations.append(f"[Security] {finding['description']}")

    # Complexity warnings
    for warning in complexity.get("warnings", [])[:2]:
        recommendations.append(f"[Complexity] {warning}")

    # Style violations — top 3 most impactful categories
    styleViolations = style.get("violations", {})
    highImpactCategories = ["emptyExcept", "mutableDefault", "bareExcept", "missingDocstring"]
    for category in highImpactCategories:
        if category in styleViolations:
            firstViolation = styleViolations[category][0]
            recommendations.append(f"[Style] {firstViolation}")

    return recommendations[:8]  # Return at most 8 recommendations


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def buildReport(
    problem:     dict,
    code:        str,
    correctness: dict,
    complexity:  dict,
    style:       dict,
    security:    dict,
) -> dict:
    """
    Build the final unified evaluation report.

    Args:
        problem:     The full problem specification dict.
        code:        The submitted source code string.
        correctness: Output from correctnessEvaluator.runCorrectnessEvaluation()
        complexity:  Output from complexityEvaluator.runComplexityEvaluation()
        style:       Output from styleEvaluator.runStyleEvaluation()
        security:    Output from securityEvaluator.runSecurityEvaluation()

    Returns:
        A fully structured report dict suitable for JSON serialisation.
    """
    overallScore = _computeOverallScore(
        correctnessScore = correctness.get("score", 0),
        complexityScore  = complexity.get("score", 0),
        styleScore       = style.get("score", 0),
        securityScore    = security.get("score", 0),
    )

    grade, gradeLabel = _assignGrade(overallScore)
    recommendations   = _buildRecommendations(correctness, complexity, style, security)

    return {
        # ---- Metadata ----
        "evaluatedAt":    datetime.now(timezone.utc).isoformat(),
        "problemId":      problem.get("id"),
        "problemTitle":   problem.get("title"),
        "difficulty":     problem.get("difficulty"),
        "codeLength":     len(code.splitlines()),

        # ---- Overall score ----
        "overallScore":   overallScore,
        "grade":          grade,
        "gradeLabel":     gradeLabel,
        "scoreWeights":   SCORE_WEIGHTS,

        # ---- Dimension scores ----
        "dimensions": {
            "correctness": {
                "score":       correctness.get("score", 0),
                "weight":      SCORE_WEIGHTS["correctness"],
                "passed":      correctness.get("passed", 0),
                "total":       correctness.get("total", 0),
                "testResults": correctness.get("testResults", []),
            },
            "complexity": {
                "score":        complexity.get("score", 0),
                "weight":       SCORE_WEIGHTS["complexity"],
                "summary":      complexity.get("summary", ""),
                "functions":    complexity.get("functions", []),
                "builtinHints": complexity.get("builtinHints", []),
                "warnings":     complexity.get("warnings", []),
            },
            "style": {
                "score":           style.get("score", 0),
                "weight":          SCORE_WEIGHTS["style"],
                "summary":         style.get("summary", ""),
                "totalViolations": style.get("totalViolations", 0),
                "violations":      style.get("violations", {}),
            },
            "security": {
                "score":    security.get("score", 0),
                "weight":   SCORE_WEIGHTS["security"],
                "summary":  security.get("summary", ""),
                "findings": security.get("findings", []),
            },
        },

        # ---- Actionable output ----
        "recommendations": recommendations,
    }
