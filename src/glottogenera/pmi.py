"""
Sound-correspondence scores and PMI alignment over ASJP symbols.

After Jäger (2013): probable cognates (same-concept words of related languages
that align closely) are aligned, the association between aligned symbols is
estimated, the words are realigned with those scores, and the procedure is
iterated. The association is asymcat's smoothed pointwise mutual information,
averaged over its two directions. Alignment is global (Needleman-Wunsch) with
a linear gap penalty, a simplification of Jäger's affine gaps.

The word distance is 1 - 2 s(a, b) / (s(a, a) + s(b, b)), with s the alignment
score: 0 for identical words, growing as the words diverge, and above 1 when
they align worse than chance.
"""

from __future__ import annotations

import random
from collections import Counter
from typing import Dict, List, Sequence, Tuple

GAP = -2.5
ITERATIONS = 3
LANGUAGE_PAIRS = 30000
SELECT = 0.5  # word distance at or below which a pair counts as a probable cognate
SEED = 1
SMOOTHING = "laplace"  # add-one, from freqprob through asymcat


def align(a: Sequence, b: Sequence, score, gap: float = GAP) -> Tuple[float, List[tuple]]:
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
            pairs.append((a[i - 1], b[j - 1]))
            i, j = i - 1, j - 1
        elif f[i][j] == f[i - 1][j] + gap:
            i -= 1
        else:
            j -= 1
    return f[n][m], pairs


class Scorer:
    """Substitution scores; without a table, +1 for identity and -1 otherwise."""

    def __init__(self, table: Dict[tuple, float] = None):
        self.table = table or {}
        self.default = min(self.table.values()) if self.table else -1.0
        self._self: Dict[tuple, float] = {}

    def __call__(self, x, y) -> float:
        if not self.table:
            return 1.0 if x == y else -1.0
        return self.table.get((x, y), self.default)

    def distance(self, a: Sequence, b: Sequence) -> float:
        """1 - 2 s(a,b) / (s(a,a) + s(b,b))."""
        a, b = tuple(a), tuple(b)
        for w in (a, b):
            if w not in self._self:
                self._self[w] = align(w, w, self)[0]
        denom = self._self[a] + self._self[b]
        if denom <= 0:
            return 1.0
        return 1.0 - 2.0 * align(a, b, self)[0] / denom


def _association(counts: Counter) -> Dict[tuple, float]:
    """asymcat's smoothed PMI over aligned symbol pairs, averaged over directions."""
    import asymcat

    cooccs = [pair for pair, n in sorted(counts.items()) for _ in range(n)]
    scorer = asymcat.CatScorer(cooccs, smoothing_method=SMOOTHING)
    return {pair: (xy + yx) / 2 for pair, (xy, yx) in scorer.pmi_smoothed().items()}


def train(wordlists: Dict[str, List[List[str]]], glottolog) -> Tuple[Scorer, dict]:
    """
    Learn correspondence scores from same-family language pairs drawn with a
    fixed seed (families weighted by size), using the first form of every
    concept both languages attest.
    """
    rng = random.Random(SEED)
    by_family: Dict[str, List[str]] = {}
    for gc in sorted(wordlists):
        by_family.setdefault(glottolog.family_gc(gc), []).append(gc)
    families = [langs for _, langs in sorted(by_family.items()) if len(langs) >= 2]
    weights = [len(f) for f in families]
    candidates = []
    for _ in range(LANGUAGE_PAIRS):
        fam = rng.choices(families, weights)[0]
        a, b = rng.sample(fam, 2)
        for fa, fb in zip(wordlists[a], wordlists[b]):
            if fa and fb:
                candidates.append((tuple(fa[0]), tuple(fb[0])))
    scorer = Scorer()
    kept = 0
    for _ in range(ITERATIONS):
        counts: Counter = Counter()
        kept = 0
        for a, b in candidates:
            if scorer.table:
                if scorer.distance(a, b) > SELECT:
                    continue
            else:
                matches = sum(x == y for x, y in align(a, b, scorer)[1])
                if 1 - matches / max(len(a), len(b)) > SELECT:
                    continue
            kept += 1
            for x, y in align(a, b, scorer)[1]:
                counts[(x, y)] += 1
                counts[(y, x)] += 1
        scorer = Scorer(_association(counts))
    return scorer, {"candidate_pairs": len(candidates), "probable_cognates": kept, "symbols": len({x for x, _ in scorer.table})}
