"""
evaluators/
-----------
Evaluation pipeline for the LLM Code Evaluation Harness.

Modules:
    correctnessEvaluator  — Sandboxed subprocess test execution
    complexityEvaluator   — AST-based cyclomatic complexity analysis
    styleEvaluator        — PEP 8 and anti-pattern detection
    securityEvaluator     — Static security vulnerability scanning
    reportGenerator       — Unified weighted report assembly
"""
