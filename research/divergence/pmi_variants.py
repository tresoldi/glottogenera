"""
PMI sound-correspondence scores and alignment over ASJP symbols, after Jäger
(2013): align probable cognates, estimate pointwise mutual information between
aligned symbols, realign with it, and iterate. Simplified: linear gaps.
"""

import math
import random
from collections import Counter

GAP = -2.5
ITERATIONS = 3
LANGUAGE_PAIRS = 30000
SELECT = 0.5  # word distance at or below which a pair counts as probably cognate


def align(a, b, score, gap=GAP):
    """Needleman-Wunsch with linear gaps: (score, aligned symbol pairs)."""
    n, m = len(a), len(b)
    f = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        f[i][0] = i * gap
    for j in range(1, m + 1):
        f[0][j] = j * gap
    for i in range(1, n + 1):
        ai, row, prev = a[i - 1], f[i], f[i - 1]
        for j in range(1, m + 1):
            row[j] = max(prev[j - 1] + score(ai, b[j - 1]), prev[j] + gap, row[j - 1] + gap)
    pairs, i, j = [], n, m
    while i > 0 and j > 0:
        if f[i][j] == f[i - 1][j - 1] + score(a[i - 1], b[j - 1]):
            pairs.append((a[i - 1], b[j - 1])); i -= 1; j -= 1
        elif f[i][j] == f[i - 1][j] + gap:
            i -= 1
        else:
            j -= 1
    return f[n][m], pairs


class Scorer:
    def __init__(self, table=None, default=None):
        self.table = table or {}
        self.default = min(self.table.values()) if default is None and self.table else (default or -1.0)
        self.self_cache = {}

    def __call__(self, x, y):
        if not self.table:
            return 1.0 if x == y else -1.0
        return self.table.get((x, y), self.default)

    def similarity(self, a, b):
        return align(a, b, self)[0]

    def distance(self, a, b):
        """1 - 2 s(a,b) / (s(a,a) + s(b,b))."""
        a, b = tuple(a), tuple(b)
        for w in (a, b):
            if w not in self.self_cache:
                self.self_cache[w] = self.similarity(w, w)
        denom = self.self_cache[a] + self.self_cache[b]
        if denom <= 0:
            return 1.0
        return 1.0 - 2.0 * self.similarity(a, b) / denom


def _asymcat_table(counts, measure):
    """Symmetric substitution scores from an asymcat measure over aligned pairs."""
    import asymcat

    cooccs = [pair for pair, n in counts.items() for _ in range(n)]
    scorer = asymcat.CatScorer(cooccs, smoothing_method="laplace")  # add-one
    scores = getattr(scorer, measure)()
    return {pair: (xy + yx) / 2 for pair, (xy, yx) in scores.items()}


def train(code_lists, glottolog, seed=1, estimator="own"):
    """
    Estimate correspondence scores between symbols from same-family language
    pairs. ``estimator`` is "own" (the PMI below) or "asymcat:<measure>"
    (pmi, pmi_smoothed or tresoldi, averaged over both directions).
    """
    rng = random.Random(seed)
    by_family = {}
    for gc in sorted(code_lists):
        by_family.setdefault(glottolog.family_gc(gc), []).append(gc)
    families = [langs for langs in by_family.values() if len(langs) >= 2]
    weights = [len(f) for f in families]
    candidates = []
    for _ in range(LANGUAGE_PAIRS):
        fam = rng.choices(families, weights)[0]
        a, b = rng.sample(fam, 2)
        for i, (fa, fb) in enumerate(zip(code_lists[a], code_lists[b])):
            if fa and fb:
                candidates.append((fa[0], fb[0]))
    freq = Counter(ch for gc in code_lists for forms in code_lists[gc] for f in forms for ch in f)
    candidates = [(tuple(a), tuple(b)) for a, b in candidates]
    total = sum(freq.values())
    q = {c: v / total for c, v in freq.items()}
    scorer = Scorer()
    for _ in range(ITERATIONS):
        counts = Counter()
        kept = 0
        for a, b in candidates:
            if scorer.table:
                if scorer.distance(a, b) > SELECT:
                    continue
            else:
                ldn = 1 - sum(x == y for x, y in align(a, b, scorer)[1]) / max(len(a), len(b))
                if ldn > SELECT:
                    continue
            kept += 1
            for x, y in align(a, b, scorer)[1]:
                counts[(x, y)] += 1
                counts[(y, x)] += 1
        if estimator == "own":
            n = sum(counts.values())
            table = {}
            for x in q:
                for y in q:
                    p = (counts.get((x, y), 0) + 0.5) / (n + 0.5 * len(q) ** 2)
                    table[(x, y)] = math.log(p / (q[x] * q[y]))
        else:
            table = _asymcat_table(counts, estimator.split(":", 1)[1])
        scorer = Scorer(table)
    return scorer, {"candidates": len(candidates), "kept_last_iteration": kept, "symbols": len(q)}
