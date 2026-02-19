# LLM Code Eval

**An automated evaluation harness for LLM-generated Python code.**

Evaluates submitted solutions across four dimensions — correctness, algorithmic complexity, style, and security — using static analysis and sandboxed execution. Includes a React frontend for live evaluation in the browser.

Built as a portfolio project demonstrating the skills required for AI data quality / software engineering evaluator roles.

---

## Architecture

```
LLMcodeEval/
├── backend/
│   ├── app.py                          # Flask API server
│   ├── requirements.txt
│   ├── evaluators/
│   │   ├── correctnessEvaluator.py     # Sandboxed test execution
│   │   ├── complexityEvaluator.py      # AST-based cyclomatic complexity
│   │   ├── styleEvaluator.py           # PEP 8 / anti-pattern detection
│   │   ├── securityEvaluator.py        # Security vulnerability scanner
│   │   └── reportGenerator.py          # Unified weighted report builder
│   └── problems/
│       ├── problem_001.json            # Easy:   Two Sum
│       ├── problem_002.json            # Medium: LRU Cache
│       └── problem_003.json            # Hard:   Serialize/Deserialize Binary Tree
├── frontend/
│   └── index.html                      # Self-contained React SPA
└── testCaseExamples/                   # Annotated reference solutions
    ├── problem1/
    │   ├── p1PerfectScore.py           # Hash-map O(n) — scores 100/100
    │   └── p1PartialScore.py           # O(n²) + wrong index order — scores ~47/100
    ├── problem2/
    │   ├── p2PerfectScore.py           # OrderedDict O(1) — scores 100/100
    │   └── p2PartialScore.py           # dict+list, broken recency — scores ~60/100
    └── problem3/
        ├── p3PerfectScore.py           # BFS with null sentinel — scores 99/100
        └── p3PartialScore.py           # Pre-order, no nulls — scores ~37/100
```

---

## Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
# API now running at http://localhost:8000
```

### 2. Frontend

Serve the frontend via Python's built-in HTTP server (opening `index.html`
directly as a `file://` URL will fail with CORS errors):

```bash
cd frontend
python -m http.server 3000
# Frontend now running at http://localhost:3000
```

Then open **http://localhost:3000** in your browser.

> **Windows users:** If `venv\Scripts\activate` throws a script-execution error,
> run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
> in PowerShell first, or use `venv\Scripts\activate.bat` from Command Prompt.

---

## API Reference

### `GET /api/problems`

Returns a summary list of all available problems.

```json
[
  { "id": "001", "title": "Two Sum", "difficulty": "easy", "description": "..." }
]
```

### `GET /api/problems/<id>`

Returns the full problem specification (hidden test cases excluded).

### `POST /api/evaluate`

Evaluates submitted code against a problem.

**Request body:**
```json
{
  "problemId": "001",
  "code": "def twoSum(nums, target):\n    ..."
}
```

**Response:** A structured evaluation report (see below).

---

## Evaluation Report Schema

```json
{
  "evaluatedAt":   "2025-02-19T10:00:00+00:00",
  "problemId":     "001",
  "problemTitle":  "Two Sum",
  "difficulty":    "easy",
  "overallScore":  87,
  "grade":         "B",
  "gradeLabel":    "Good — minor improvements suggested.",
  "scoreWeights":  { "correctness": 0.5, "complexity": 0.2, "style": 0.15, "security": 0.15 },

  "dimensions": {
    "correctness": {
      "score": 100, "passed": 8, "total": 8,
      "testResults": [
        { "label": "Basic case", "status": "pass", "expected": [0,1], "actual": [0,1], "hidden": false }
      ]
    },
    "complexity": {
      "score": 85,
      "functions": [{ "name": "twoSum", "cyclomaticScore": 3, "maxNestDepth": 2, "isRecursive": false }],
      "builtinHints": ["Uses sorted() — O(n log n) time."],
      "warnings": []
    },
    "style": {
      "score": 72, "totalViolations": 3,
      "violations": { "missingDocstring": ["'twoSum' at line 1 is missing a docstring."] }
    },
    "security": {
      "score": 100, "findings": []
    }
  },

  "recommendations": [
    "Add a docstring to 'twoSum'."
  ]
}
```

---

## Score Weights

| Dimension    | Weight | Rationale |
|--------------|--------|-----------|
| Correctness  | 50%    | A solution that fails tests provides no value |
| Complexity   | 20%    | Production code must be efficient at scale |
| Style        | 15%    | Readable code reduces maintenance cost |
| Security     | 15%    | Insecure patterns fail in production environments |

---

## Problems

### Problem 001 — Two Sum (Easy)

Classic hash-map problem. The tricky hidden cases include:
- Both negative numbers summing to zero
- Very large arrays (answer at the end — exposes O(n²) solutions)
- Duplicate values where only one pair is valid

### Problem 002 — LRU Cache (Medium)

`get()` and `put()` must both run in O(1). Hidden cases expose:
- Capacity-1 caches (every put should evict)
- `get()` refreshing recency (protecting accessed keys from eviction)
- Updating an existing key's value must not re-insert it at wrong position
- Idempotent updates (put → put same key → eviction should target correct LRU)

### Problem 003 — Serialize/Deserialize Binary Tree (Hard)

Round-trip lossless encoding. Hidden cases expose:
- Left-skewed trees (linked-list shape — breaks BFS-only solutions)
- Negative and zero values (break solutions using `0` as a null sentinel)
- All-duplicate-value trees (structure must be preserved, not just values)
- Right-only chains
- Idempotency: `deserialize(deserialize(serialize(serialize(root))))`

---

## Evaluator Details

### Correctness Evaluator
- Runs each test case in an **isolated subprocess** with a 5-second timeout
- Parses JSON output from the subprocess — isolates crashes from the server
- Supports **weighted test cases** (edge cases carry more weight than basic cases)
- Flexible value matching: float tolerance (1e-6), ordered/unordered list comparison

### Complexity Evaluator
- **Cyclomatic complexity** via AST decision-point counting (if/for/while/except/BoolOp)
- **Maximum nesting depth** of loops and conditionals
- **Recursive function detection**
- **Built-in complexity hints** (sorted → O(n log n), set → O(n) build / O(1) lookup)

### Style Evaluator
- **Naming convention** — snake_case enforcement (PEP 8)
- **Docstring presence** — all functions and classes
- **Magic numbers** — numeric literals flagged (0, 1, -1, 2, 10, 100 excluded)
- **Line length** — >100 characters flagged
- **Empty except blocks** — `except: pass` anti-pattern
- **Mutable default arguments** — `def f(x=[])` gotcha
- **Unused imports** — heuristic import reference counting

### Security Evaluator
- **Dangerous builtins**: `eval()`, `exec()`, `__import__()`
- **Shell injection surface**: `os.system()`, `subprocess` with `shell=True`
- **Deserialisation attacks**: `pickle.loads()`, `marshal.loads()`, unsafe `yaml.load()`
- **Hardcoded secrets**: password/API key/token regex patterns
- **SQL injection**: string-formatted SQL queries
- **Assert for security**: assert stripped by `-O` flag

---

## Adding a New Problem

Create `backend/problems/problem_XXX.json`:

```json
{
  "id": "004",
  "title": "Your Problem Title",
  "difficulty": "medium",
  "description": "Problem description shown to users.",
  "functionSignature": "def solve(input): ...",
  "constraints": ["1 <= n <= 10^5"],
  "examples": [
    { "input": "solve([1,2,3])", "output": "6", "explanation": "Sum of elements." }
  ],
  "testCases": [
    { "label": "Basic case", "args": "solve([1,2,3])", "expected": 6, "ordered": true, "weight": 1 }
  ],
  "hiddenTestCases": [
    { "label": "HIDDEN: Edge case", "args": "solve([])", "expected": 0, "ordered": true, "weight": 2 }
  ],
  "preamble": "# Optional code injected before the solution (e.g. helper classes)"
}
```

The problem appears in the sidebar automatically — no server restart required.

---

## Code Style Note

This codebase uses **camelCase** for all variable and function names throughout, consistent with the author's preference. Python stdlib identifiers (e.g. `ast.walk`, `subprocess.run`) retain their original naming.

---

## License

MIT
