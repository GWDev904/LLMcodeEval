"""
testCaseExamples/problem2/p2PerfectScore.py
--------------------------------------------
Perfect-scoring reference solution for Problem 002: LRU Cache.

Expected scores when submitted through the evaluator:
  Correctness : 100  — All 7 test cases pass (3 visible + 4 hidden)
  Complexity  : 100  — O(1) get() and put() using OrderedDict.
  Style       : 100  — Full docstrings on class and all methods. Clean naming.
  Security    : 100  — No dangerous patterns detected.
  OVERALL     : 100  — Grade A

Why it scores perfectly:
  - OrderedDict maintains insertion order AND provides move_to_end() in O(1),
    making both get() and put() true O(1) operations.
  - get() calls move_to_end(key) to refresh recency — this is what the
    hidden "recency refresh" test case specifically targets.
  - put() checks if the key already exists and moves it to end BEFORE
    assigning the new value, preventing duplicate entries.
  - popitem(last=False) evicts the LRU item (front of OrderedDict) in O(1).
  - Full class and method docstrings pass the style evaluator cleanly.
"""

from collections import OrderedDict


class LRUCache:
    """O(1) LRU Cache backed by an OrderedDict."""

    def __init__(self, capacity):
        """Initialise with fixed capacity."""
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key):
        """Return value and refresh recency, or -1 if absent."""
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        """Insert or update key. Evict LRU entry if over capacity."""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
