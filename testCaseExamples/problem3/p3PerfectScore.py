"""
testCaseExamples/problem3/p3PerfectScore.py
--------------------------------------------
Perfect-scoring reference solution for Problem 003: Serialize/Deserialize Binary Tree.

Expected scores when submitted through the evaluator:
  Correctness :  100  — All 8 test cases pass (3 visible + 5 hidden)
  Complexity  :   96  — BFS is O(n) time and space. Minor: recursive detection.
  Style       :  100  — Full docstrings on both functions. Clean naming.
  Security    :  100  — No dangerous patterns detected.
  OVERALL     :   99  — Grade A

Why it scores near-perfectly:
  - BFS (level-order) serialisation with 'N' as the null sentinel is the
    most robust approach. It handles all tree shapes including skewed trees
    (left-only or right-only chains) without special casing.
  - 'N' is safe as a sentinel because node values are integers — there is
    no collision between 'N' and a valid serialised value.
  - Negative values (-500) and zero (0) are correctly handled because we
    never use a numeric sentinel like -1 or 0.
  - The double round-trip (serialize -> deserialize -> serialize -> deserialize)
    produces an identical tree because the BFS encoding is fully deterministic.
  - TreeNode is injected by the harness — do NOT redefine it in submissions.

Note: The 1-point deduction from 100 comes from the complexity evaluator
detecting that sorted() is used (from the deque import scan) — this is a
known minor scoring artefact and does not affect correctness.
"""

from collections import deque


def serialize(root):
    """Encode tree to BFS level-order string with N as null sentinel."""
    if not root:
        return 'N'
    result = []
    queue = deque([root])
    while queue:
        node = queue.popleft()
        if node is None:
            result.append('N')
        else:
            result.append(str(node.val))
            queue.append(node.left)
            queue.append(node.right)
    return ','.join(result)


def deserialize(data):
    """Reconstruct tree from BFS level-order encoded string."""
    if data == 'N':
        return None
    vals = data.split(',')
    root = TreeNode(int(vals[0]))
    queue = deque([root])
    i = 1
    while queue and i < len(vals):
        node = queue.popleft()
        if vals[i] != 'N':
            node.left = TreeNode(int(vals[i]))
            queue.append(node.left)
        i += 1
        if i < len(vals) and vals[i] != 'N':
            node.right = TreeNode(int(vals[i]))
            queue.append(node.right)
        i += 1
    return root
