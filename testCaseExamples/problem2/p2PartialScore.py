"""
testCaseExamples/problem2/p2PartialScore.py
--------------------------------------------
Partial-scoring solution for Problem 002: LRU Cache.

Expected scores when submitted through the evaluator:
  Correctness :  ~43  — 3/7 test cases pass. Fails recency and update tests.
  Complexity  :   80  — Plain dict + list is O(n) for put() due to list.pop(0).
  Style       :   70  — No class or method docstrings. Inline comments only.
  Security    :  100  — No dangerous patterns detected.
  OVERALL     :  ~60  — Grade D

Why it fails:

  BUG 1 — get() does NOT refresh recency:
    Returning self.cache.get(key, -1) is correct for the value but the
    key is never moved to the "most recently used" position. This breaks
    the hidden test case that calls get(key) then expects that key to
    survive the next eviction.

  BUG 2 — put() on existing key doesn't update order:
    When a key already exists, only the value is updated — the key stays
    in its original position in self.order. This means the order list
    and the cache dict get out of sync after updates.

  PERFORMANCE — list.pop(0) is O(n):
    Removing the front element of a Python list shifts every remaining
    element. A proper LRU needs a deque or OrderedDict for O(1) eviction.

This example is designed to pass basic put/get tests while failing the
hidden edge cases that specifically probe recency and update correctness.
"""


class LRUCache:
    # Buggy: get() does not refresh recency
    # Buggy: updating existing key does not update its position in order list

    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = {}
        self.order = []

    def get(self, key):
        # Bug: should call move_to_end equivalent to refresh recency
        return self.cache.get(key, -1)

    def put(self, key, value):
        if key not in self.cache and len(self.cache) >= self.capacity:
            oldest = self.order.pop(0)  # O(n) — should use deque or OrderedDict
            del self.cache[oldest]
        self.cache[key] = value
        if key not in self.order:
            self.order.append(key)
        # Bug: if key already exists, its position in self.order is not updated
