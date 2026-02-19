"""
testCaseExamples/problem1/p1PerfectScore.py
--------------------------------------------
Perfect-scoring reference solution for Problem 001: Two Sum.

Expected scores when submitted through the evaluator:
  Correctness : 100  — All 8 test cases pass (3 visible + 5 hidden)
  Complexity  :  100  — O(n) time, O(n) space via hash map. Single pass.
  Style       :   97  — Clean, docstring present, snake_case throughout.
                        Minor: sorted() builtin flagged by complexity hints.
  Security    :  100  — No dangerous patterns detected.
  OVERALL     :  100  — Grade A

Why it scores perfectly:
  - Hash map (dict) eliminates the O(n²) nested-loop approach.
  - sorted([a, b]) ensures the returned indices are always [smaller, larger],
    which is what all 8 test cases expect.
  - Handles negative numbers and duplicates correctly because we look up
    the complement BEFORE inserting the current element.
  - Single docstring, no magic numbers, no security issues.
"""


def twoSum(nums, target):
    """Return indices of two numbers that add to target using a hash map."""
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return sorted([seen[complement], i])
        seen[num] = i
    return []
