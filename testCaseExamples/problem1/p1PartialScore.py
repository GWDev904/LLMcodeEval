"""
testCaseExamples/problem1/p1PartialScore.py
--------------------------------------------
Partial-scoring solution for Problem 001: Two Sum.

Expected scores when submitted through the evaluator:
  Correctness :   0  — All 8 test cases fail (wrong index order [j, i])
  Complexity  :  60  — O(n²) time due to nested loops. Nesting depth flagged.
  Style       :  85  — No docstring on function. Inline comment not a docstring.
  Security    : 100  — No dangerous patterns detected.
  OVERALL     :  ~47  — Grade F

Why it fails:
  1. WRONG INDEX ORDER — returns [j, i] instead of [i, j].
     Every test case expects the smaller index first (sorted order).
     This single bug causes 0/8 correctness.

  2. O(n²) TIME COMPLEXITY — nested for loops scan every pair.
     The large-array hidden test case (1002 elements) still passes functionally
     but the complexity evaluator penalises the nesting depth.

  3. NO DOCSTRING — the inline `# Works for small inputs...` comment
     is not a docstring. The style evaluator deducts points for missing
     triple-quoted docstrings on functions.

This example demonstrates how the evaluator catches structural bugs
(wrong return value) independently of style issues.
"""


def twoSum(nums, target):
    # Works for small inputs but wrong index order — returns [j, i] not [i, j]
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [j, i]
    return []
