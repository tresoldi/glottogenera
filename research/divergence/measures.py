"""
Alternative word distances for the screen: the seqsim measures and the GLED
reader, with the per-pair components from which a language distance is made.

Each measure maps two segmented forms (lists of sounds) to a distance. For a
language pair we keep, per measure, the mean distance for each shared concept
(synonyms averaged) and for a fixed sample of different-concept pairs, so both
the raw mean and the LDND-style normalized value (raw divided by the
different-concept mean) can be computed, under any concept weighting.
"""

import csv
import os
import random
from pathlib import Path

import numpy as np
import seqsim

from glottogenera.config import sources_dir
from glottogenera.divergence import ASJP_CORE, CORE_INDEX, K, MIN_CONCEPTS

OFF_DIAGONAL = 60  # sampled different-concept pairs per language pair

def _seqsim(method):
    """A seqsim method as a word distance (normal=True: 0 for identical sequences)."""
    def distance(a, b):
        return seqsim.distance([a, b], method=method, normal=True)
    return distance


def load_segmented(data_dir: Path, glottolog):
    """
    Segmented core wordlists, one doculect per in-scope language, chosen as in
    glottogenera.divergence.load_wordlists (most core concepts, ties: smallest
    doculect ID; loans dropped).
    """
    inscope = {r["glottocode"] for r in glottolog.in_scope_languages()}
    sources = sources_dir(data_dir)
    gc_of = {}
    with (sources / "asjp_languages.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("Glottocode") in inscope:
                gc_of[r["ID"]] = r["Glottocode"]
    docs = {}
    with (sources / "asjp_forms.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            doc, i = r["Language_ID"], CORE_INDEX.get(r["Parameter_ID"])
            if doc not in gc_of or i is None or r.get("Loan") == "true":
                continue
            seg = (r.get("Segments") or "").split()
            if seg:
                docs.setdefault(doc, [[] for _ in range(K)])[i].append(seg)
    best = {}
    for doc, words in docs.items():
        n = sum(1 for f in words if f)
        gc = gc_of[doc]
        if n >= MIN_CONCEPTS and (gc not in best or (-n, doc) < (-best[gc][0], best[gc][1])):
            best[gc] = (n, doc)
    return {gc: docs[doc] for gc, (_, doc) in best.items()}


# The cldf/ directory of the GLED CLDF dataset (release v1.0, r20221127.1).
GLED = Path(os.environ.get("GLED_CLDF", "gled/cldf"))


class GledForm(tuple):
    """A GLED form: its segments, carrying its cognate set as ``cognate``."""

    def __new__(cls, segments, cognate):
        obj = super().__new__(cls, segments)
        obj.cognate = cognate
        return obj


def load_gled(glottolog, gled_dir: Path = GLED):
    """
    GLED wordlists over its 40 concepts, one doculect per in-scope language
    (most concepts; ties: smallest ID). Forms are GledForm tuples of segments
    with their (automatic, family-scoped) cognate set.
    """
    inscope = {r["glottocode"] for r in glottolog.in_scope_languages()}
    with (gled_dir / "parameters.csv").open(encoding="utf-8") as fh:
        concepts = sorted(r["ID"] for r in csv.DictReader(fh))
    index = {c: i for i, c in enumerate(concepts)}
    gc_of = {}
    with (gled_dir / "languages.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("Glottocode") in inscope:
                gc_of[r["ID"]] = r["Glottocode"]
    docs = {}
    with (gled_dir / "forms.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            doc = r["Language_ID"]
            seg = (r.get("Segments") or "").split()
            if doc in gc_of and seg and r["Parameter_ID"] in index:
                docs.setdefault(doc, [[] for _ in range(len(concepts))])[index[r["Parameter_ID"]]].append(
                    GledForm(seg, r.get("Cognacy") or None)
                )
    best = {}
    for doc, words in docs.items():
        n = sum(1 for f in words if f)
        gc = gc_of[doc]
        if n >= MIN_CONCEPTS and (gc not in best or (-n, doc) < (-best[gc][0], best[gc][1])):
            best[gc] = (n, doc)
    return {gc: docs[doc] for gc, (_, doc) in best.items()}


def cognate_distance(a, b):
    """0 if two GLED forms share a cognate set, else 1."""
    return 0.0 if a.cognate is not None and a.cognate == b.cognate else 1.0


def pair_components(a, b, measures, seed):
    """
    For every measure: (diag, off) where diag is a length-K array of mean
    same-concept distances (NaN if not shared) and off a list of
    (i, j, mean distance) over a fixed sample of different-concept pairs.
    """
    shared = [i for i in range(K) if a[i] and b[i]]
    if len(shared) < MIN_CONCEPTS:
        return None
    ca = [i for i in range(K) if a[i]]
    cb = [j for j in range(K) if b[j]]
    rng = random.Random(seed)
    cells = [(i, j) for i in ca for j in cb if i != j]
    off_cells = sorted(rng.sample(cells, min(OFF_DIAGONAL, len(cells))))
    out = {}
    for name, f in measures.items():
        diag = np.full(K, np.nan)
        for i in shared:
            diag[i] = np.mean([f(x, y) for x in a[i] for y in b[i]])
        off = [(i, j, float(np.mean([f(x, y) for x in a[i] for y in b[j]]))) for i, j in off_cells]
        out[name] = (diag, off)
    return out


def distance_from(components, weights=None, normalized=True):
    """Raw mean same-concept distance, or that divided by the different-concept mean."""
    diag, off = components
    w = np.ones(K) if weights is None else weights
    ok = ~np.isnan(diag)
    den = w[ok].sum()
    if den == 0:
        return np.nan
    same = float(np.nansum(np.where(ok, diag, 0) * w) / den)
    if not normalized:
        return same
    ww = np.array([w[i] * w[j] for i, j, _ in off])
    if ww.sum() == 0:
        return np.nan
    baseline = float(np.sum(ww * np.array([d for _, _, d in off])) / ww.sum())
    return same / baseline if baseline > 0 else np.nan


__all__ = ["ASJP_CORE", "load_segmented", "load_gled", "pair_components", "distance_from"]
