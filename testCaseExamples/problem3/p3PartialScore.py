"""
testCaseExamples/problem3/p3PartialScore.py
--------------------------------------------
Partial-scoring solution for Problem 003: Serialize/Deserialize Binary Tree.

Expected scores when submitted through the evaluator:
  Correctness :  ~12  — 1-2/8 test cases pass (empty tree only)
  Complexity  :   90  — O(n) traversal but broken logic limits real use.
  Style       :   70  — No docstrings. Inline comments are not docstrings.
  Security    :  100  — No dangerous patterns detected.
  OVERALL     :  ~37  — Grade F

Why it fails:

  BUG 1 — serialize() loses structural information:
    Pre-order traversal WITHOUT null markers cannot distinguish between
    different tree shapes that share the same values. For example:
      Tree A:  1          Tree B:  1
              /                      \\
             2                        2
    Both serialize to "1,2" — there is no way to know which is which.

  BUG 2 — deserialize() can only reconstruct a single node:
    The function splits the string and creates a root node from vals[0]
    but discards the rest of the list entirely. For any tree with more
    than one node, all children are lost.

  BUG 3 — no null sentinel means no way to encode missing children:
    Without 'N' or a similar marker, skipping empty children destroys
    the positional information needed to rebuild the tree.

WHICH TEST CASES PASS:
  - Empty tree: serialize(None) returns '' and deserialize('') returns None ✓
  - Single node: serialize(root) returns '5' and deserialize('5')
    correctly creates a TreeNode(5) with no children ✓
  - All multi-node tests fail: structure is lost during serialization ✗

This example is designed to show what a plausible-looking but structurally
incorrect approach produces — passing the simplest cases while failing
all tests that require preserving tree shape.
"""


def serialize(root):
    # Bug: pre-order without null markers destroys structural information
    # Different tree shapes with the same values produce identical strings
    if not root:
        return ''
    result = str(root.val)
    if root.left:
        result += ',' + serialize(root.left)
    if root.right:
        result += ',' + serialize(root.right)
    return result


def deserialize(data):
    # Bug: only constructs the root node — all children are discarded
    # vals[1:] is never processed, so any multi-node tree is lost
    if not data:
        return None
    vals = data.split(',')
    return TreeNode(int(vals[0]))
