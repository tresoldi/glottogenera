"""
Standard LDND (Wichmann et al. 2010) on the ASJP wordlists, the baseline
against which the screen compares the released PMI distance. In the results it
appears as "asjp:ldnd (released)", the name it had when an earlier version of
glottogenera used it; the key is kept so that the results stay comparable.
"""

from typing import Dict, Optional

import numpy as np
from rapidfuzz.distance import Levenshtein
from rapidfuzz.process import cdist

from glottogenera.divergence import K, MIN_CONCEPTS, Wordlist, crown_pairs
from glottogenera.glottolog import Glottolog


def pair_block(a: Wordlist, b: Wordlist) -> np.ndarray:
    """
    The K x K matrix of mean normalized Levenshtein distances between the forms
    of concept i in ``a`` and concept j in ``b``, averaging over synonyms as the
    ASJP software does; NaN where either concept is unattested.
    """
    fa = [(f, i) for i, forms in enumerate(a) for f in forms]
    fb = [(f, j) for j, forms in enumerate(b) for f in forms]
    dist = cdist(
        [f for f, _ in fa],
        [f for f, _ in fb],
        scorer=Levenshtein.normalized_distance,
        workers=1,
    )
    ia = np.array([i for _, i in fa])
    ib = np.array([j for _, j in fb])
    sums = np.zeros((K, K))
    counts = np.zeros((K, K))
    np.add.at(sums, (ia[:, None], ib[None, :]), dist)
    np.add.at(counts, (ia[:, None], ib[None, :]), 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (sums / counts).astype(np.float32)


class PairStats:
    """
    Precomputed pieces of a stack of pair blocks, so that LDND can be
    recomputed under any concept weighting without copying the blocks.
    """

    def __init__(self, blocks: np.ndarray):
        self.attested_a = ~np.all(np.isnan(blocks), axis=2)  # rows: concepts of a
        self.attested_b = ~np.all(np.isnan(blocks), axis=1)  # columns: concepts of b
        self.shared = self.attested_a & self.attested_b
        np.nan_to_num(blocks, copy=False)  # in place: unattested cells count 0
        self.blocks = blocks
        self.diag = np.einsum("pii->pi", blocks).copy()

    def ldnd(self, weights: Optional[np.ndarray] = None) -> np.ndarray:
        """
        LDND for every pair: the mean same-concept distance divided by the
        mean different-concept distance, over the concepts attested in each
        list. ``weights`` (one per core concept) resample concepts for the
        bootstrap; unit weights give the standard LDND. NaN where fewer than
        MIN_CONCEPTS concepts are shared or the different-concept mean is zero.
        """
        w = np.ones(K, dtype=np.float32) if weights is None else np.asarray(weights, np.float32)
        same_den = self.shared @ w
        diff_num = (self.blocks @ w) @ w - self.diag @ (w * w)
        diff_den = (self.attested_a @ w) * (self.attested_b @ w) - self.shared @ (w * w)
        with np.errstate(invalid="ignore", divide="ignore"):
            same = (self.diag @ w) / same_den
            diff = diff_num / diff_den
            result = (same / diff).astype(float)
        result[(self.shared.sum(axis=1) < MIN_CONCEPTS) | ~(diff > 1e-9)] = np.nan
        return result


def ldnd(a: Wordlist, b: Wordlist) -> Optional[float]:
    """Standard LDND between two wordlists (None when undefined)."""
    value = PairStats(pair_block(a, b)[None]).ldnd()[0]
    return None if np.isnan(value) else float(value)


class LdndCrowns:
    """
    Pair blocks for every node's cross-branch pairs, from which crown
    divergence can be recomputed under any concept weighting.
    """

    def __init__(self, glottolog: Glottolog, lists: Dict[str, Wordlist]):
        pairs = crown_pairs(glottolog, lists)
        unique = sorted({p for ps in pairs.values() for p in ps})
        index = {p: i for i, p in enumerate(unique)}
        blocks = np.empty((len(unique), K, K), dtype=np.float32)
        for i, (x, y) in enumerate(unique):
            blocks[i] = pair_block(lists[x], lists[y])
        self.pairs = PairStats(blocks)
        self.nodes = sorted(pairs)
        self.members = [np.array([index[p] for p in pairs[n]]) for n in self.nodes]

    def divergence(self, weights: Optional[np.ndarray] = None) -> Dict[str, dict]:
        """{node: {D, n_pairs}}: the mean LDND over the node's defined pairs."""
        values = self.pairs.ldnd(weights)
        out = {}
        for node, idx in zip(self.nodes, self.members):
            v = values[idx]
            v = v[~np.isnan(v)]
            if len(v):
                out[node] = {"D": float(v.mean()), "n_pairs": int(len(v))}
        return out


