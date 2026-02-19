"""
app.py
------
Flask API server for the LLM Code Evaluation Harness.

Endpoints:
  POST /api/evaluate   - Submit code + problem ID for full evaluation
  GET  /api/problems   - List all available problems
  GET  /api/problems/<id> - Get a single problem by ID

Run with:
  python app.py
  # or for production:
  gunicorn app:app --bind 0.0.0.0:8000
"""

import json
import os

from flask import Flask, request, jsonify

from evaluators.correctnessEvaluator import runCorrectnessEvaluation
from evaluators.complexityEvaluator import runComplexityEvaluation
from evaluators.styleEvaluator import runStyleEvaluation
from evaluators.securityEvaluator import runSecurityEvaluation
from evaluators.reportGenerator import buildReport

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

# Enable CORS so the React dev server (localhost:3000) can call this API.
# In production, restrict origins to your actual domain.
try:
    from flask_cors import CORS
    CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])
except ImportError:
    # flask-cors not installed — add permissive header manually
    @app.after_request
    def addCorsHeaders(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

PROBLEMS_DIR = os.path.join(os.path.dirname(__file__), "problems")


# ---------------------------------------------------------------------------
# Helper: load problem JSON from disk
# ---------------------------------------------------------------------------

def loadProblem(problemId: str) -> dict | None:
    """
    Load a problem specification from the /problems directory.

    Args:
        problemId: The problem identifier string, e.g. "001".

    Returns:
        Parsed problem dict, or None if not found.
    """
    filePath = os.path.join(PROBLEMS_DIR, f"problem_{problemId}.json")
    if not os.path.isfile(filePath):
        return None
    with open(filePath, "r", encoding="utf-8") as f:
        return json.load(f)


def listAllProblems() -> list[dict]:
    """
    Return a summary list of all problems (id, title, difficulty).
    """
    summaries = []
    if not os.path.isdir(PROBLEMS_DIR):
        return summaries

    for fileName in sorted(os.listdir(PROBLEMS_DIR)):
        if not fileName.endswith(".json"):
            continue
        filePath = os.path.join(PROBLEMS_DIR, fileName)
        with open(filePath, "r", encoding="utf-8") as f:
            data = json.load(f)
        summaries.append({
            "id": data.get("id"),
            "title": data.get("title"),
            "difficulty": data.get("difficulty"),
            "description": data.get("description", "")[:120] + "...",
        })
    return summaries


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/api/problems", methods=["GET"])
def getProblems():
    """Return a list of all available problem summaries."""
    return jsonify(listAllProblems())


@app.route("/api/problems/<problemId>", methods=["GET"])
def getProblem(problemId: str):
    """Return the full spec for a single problem."""
    problem = loadProblem(problemId)
    if problem is None:
        return jsonify({"error": f"Problem '{problemId}' not found."}), 404
    # Exclude hidden test cases from the client view
    publicProblem = {k: v for k, v in problem.items() if k != "hiddenTestCases"}
    return jsonify(publicProblem)


@app.route("/api/evaluate", methods=["POST", "OPTIONS"])
def evaluateCode():
    """
    Evaluate submitted code against a problem.

    Expected JSON body:
        {
            "problemId": "001",
            "code": "def twoSum(nums, target): ..."
        }

    Returns a structured evaluation report.
    """
    if request.method == "OPTIONS":
        # Pre-flight CORS request
        return jsonify({}), 200

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be JSON."}), 400

    problemId = body.get("problemId", "").strip()
    submittedCode = body.get("code", "").strip()

    if not problemId:
        return jsonify({"error": "Field 'problemId' is required."}), 400
    if not submittedCode:
        return jsonify({"error": "Field 'code' is required."}), 400

    problem = loadProblem(problemId)
    if problem is None:
        return jsonify({"error": f"Problem '{problemId}' not found."}), 404

    # ------------------------------------------------------------------
    # Run all evaluators in sequence. Each returns a structured dict.
    # ------------------------------------------------------------------
    correctnessResult = runCorrectnessEvaluation(submittedCode, problem)
    complexityResult  = runComplexityEvaluation(submittedCode)
    styleResult       = runStyleEvaluation(submittedCode)
    securityResult    = runSecurityEvaluation(submittedCode)

    # Build the final unified report
    report = buildReport(
        problem=problem,
        code=submittedCode,
        correctness=correctnessResult,
        complexity=complexityResult,
        style=styleResult,
        security=securityResult,
    )

    return jsonify(report)


# ---------------------------------------------------------------------------
# Dev server entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Starting LLM Code Eval API on http://localhost:8000")
    app.run(host="0.0.0.0", port=8000, debug=True)
