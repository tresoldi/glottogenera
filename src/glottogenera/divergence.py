"""
The release: genera of Glottolog 5.3 cut by crown divergence from ASJP wordlists.

Each language is one ASJP doculect (the one with most of the 40 core concepts,
loans removed). Two languages are compared with PMI alignment (glottogenera.pmi):
the mean alignment distance between their words for the same concept,
synonyms averaged, divided by the mean distance between words for different
concepts. For every Glottolog node the crown divergence D is the mean of that
distance between in-scope languages on different child branches. A language's
genus is the highest node on its path whose D is at most delta (an unmeasured
node takes the largest value below it). Below a node that exceeds delta, a
clade without measurements, or the language itself, ends the walk; a family
without any measurement forms one genus. Every genus is a complete Glottolog
clade.

delta is calibrated against the WALS genera family by family: it maximizes the
mean, over Glottolog families with at least two WALS genera, of the agreement
(ARI) between the proposed and the WALS genera of the family's languages; among
tied values the median is taken. Averaging over families rather than pooling
keeps the largest WALS genera from dominating. A bootstrap over concepts and
language pairs recalibrates delta and recuts to give each genus a stability
score.

Reads:
  <data-dir>/sources/               (ASJP, WALS caches)
  genus_names.tsv (package data)    curated genus names
Writes:
  <data-dir>/genera.tsv           one row per language
  <data-dir>/genera_summary.tsv   one row per genus
  <data-dir>/nodes.tsv            crown divergence of every measured node
  <data-dir>/report.md
  <data-dir>/params.json          sources, parameters and evaluation
"""

from __future__ import annotations

import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.metrics import adjusted_rand_score

from . import pmi, tree
from .config import (
    ASJP_REF,
    GLOTTOLOG_CLDF_COMMIT,
    GLOTTOLOG_DOI,
    GLOTTOLOG_RELEASE_COMMIT,
    GLOTTOLOG_RELEASE_TAG_OBJECT,
    GLOTTOLOG_VERSION,
    WALS_REF,
    sources_dir,
)
from .glottolog import Glottolog
from .names import genus_namer
from .wals import NON_GENEALOGICAL_WALS_GENUS, load_wals, wals_eval_set

# ASJP modifier and annotation symbols, stripped before comparing forms. The
# digits 3 5 7 8 encode phonemes and are kept.
_ASJP_STRIP = str.maketrans("", "", '~$*"%. ')


def clean_asjp(form: str) -> str:
    """Normalize an ASJP word form: drop modifiers, keep base phoneme symbols."""
    return form.strip().translate(_ASJP_STRIP)


# The 40-concept ASJP core list (ASJP Parameter_IDs, Swadesh numbering).
ASJP_CORE = (
    "1 2 3 11 12 18 19 21 22 23 25 28 30 31 34 39 40 41 43 44 "
    "47 48 51 53 54 57 58 61 66 72 74 75 77 82 85 86 92 95 96 100"
).split()
MIN_CONCEPTS = 20  # per language, and shared per language pair
MAX_PAIRS = tree.MAX_PAIRS  # sampled cross-branch pairs per node
OFF_DIAGONAL = 60  # sampled different-concept word pairs per language pair
BOOTSTRAP_REPLICATES = 200
# The cut value c(u) of a measured node (tree.cut_values): "own", its own crown
# divergence, or "max", the largest value at or below it. "own" gave the more
# stable genera under the bootstrap.
ENVELOPE_RULE = "own"
GRID_STEP = tree.GRID_STEP
DELTA_GRID = tree.DELTA_GRID
# Half-width of the window over which the calibration objective is averaged, so
# that delta does not hinge on the crossing of single nodes.
SMOOTHING = tree.SMOOTHING
# Node values are rounded to this many decimals before the cut, the calibration and the release, so
# that recutting the released nodes.tsv reproduces every released result exactly.
DECIMALS = 6
CURVE_STEP = 1  # the curve in params.json keeps every grid value (the figure draws its steps)
PERMUTATIONS = 20  # crown divergence shuffled across nodes: the null for the calibration
YARDSTICK_FAMILY = "indo1319"  # reported separately: Dryer's reference family
FAMILY_REPLICATES = 1000  # family resampling of the calibration
BASELINE_DEPTHS = (1, 2, 3, 4)  # fixed-depth cuts reported as baselines

CORE_INDEX = {c: i for i, c in enumerate(ASJP_CORE)}
K = len(ASJP_CORE)

# A wordlist: for each core concept (in ASJP_CORE order), the list of its forms.
Wordlist = List[List[str]]


# ----- wordlists and distance -----


def load_wordlists(data_dir: Path, glottolog: Glottolog) -> Dict[str, Wordlist]:
    """
    One ASJP doculect per in-scope language: the doculect with most core
    concepts (ties: the smallest doculect ID). Pooling all doculects of a
    glottocode would let dialect variants stand in for synonyms and pull
    distances towards zero for well-documented languages. Forms flagged as
    loans are dropped. Languages need at least MIN_CONCEPTS core concepts.
    """
    inscope = {r["glottocode"] for r in glottolog.in_scope_languages()}
    sources = sources_dir(data_dir)
    gc_of = {}
    with (sources / "asjp_languages.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("Glottocode") in inscope:
                gc_of[r["ID"]] = r["Glottocode"]
    doculects: Dict[str, Wordlist] = {}
    with (sources / "asjp_forms.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            doc = r["Language_ID"]
            i = CORE_INDEX.get(r["Parameter_ID"])
            if doc not in gc_of or i is None or r.get("Loan") == "true":
                continue
            form = clean_asjp(r.get("Form") or "")
            if form:
                doculects.setdefault(doc, [[] for _ in range(K)])[i].append(form)
    best: Dict[str, Tuple[int, str]] = {}
    for doc, words in doculects.items():
        n = sum(1 for forms in words if forms)
        gc = gc_of[doc]
        if n >= MIN_CONCEPTS and (gc not in best or (-n, doc) < (-best[gc][0], best[gc][1])):
            best[gc] = (n, doc)
    return {gc: doculects[doc] for gc, (_, doc) in best.items()}


def pair_components(a: Wordlist, b: Wordlist, scorer, seed: str):
    """
    (diag, off) for a language pair: ``diag`` holds, per core concept, the mean
    word distance over synonym pairs (NaN unless both lists attest it);
    ``off`` holds (i, j, mean distance) for OFF_DIAGONAL different-concept
    pairs drawn with a pair-seeded generator. None when fewer than
    MIN_CONCEPTS concepts are shared.
    """
    shared = [i for i in range(K) if a[i] and b[i]]
    if len(shared) < MIN_CONCEPTS:
        return None
    diag = np.full(K, np.nan)
    for i in shared:
        diag[i] = np.mean([scorer.distance(x, y) for x in a[i] for y in b[i]])
    cells = [(i, j) for i in range(K) if a[i] for j in range(K) if b[j] and i != j]
    chosen = sorted(random.Random(seed).sample(cells, min(OFF_DIAGONAL, len(cells))))
    off = [(i, j, float(np.mean([scorer.distance(x, y) for x in a[i] for y in b[j]]))) for i, j in chosen]
    return diag, off


class Components:
    """Pair components, from which the normalized distance is recomputed under any weighting."""

    def __init__(self, items):
        n_off = max(len(off) for _, off in items)
        self.diag = np.stack([diag for diag, _ in items]).astype(np.float32)
        self.off_i = np.zeros((len(items), n_off), dtype=np.int16)
        self.off_j = np.zeros((len(items), n_off), dtype=np.int16)
        self.off_d = np.full((len(items), n_off), np.nan, dtype=np.float32)
        for r, (_, off) in enumerate(items):
            for c, (i, j, d) in enumerate(off):
                self.off_i[r, c], self.off_j[r, c], self.off_d[r, c] = i, j, d

    def values(self, weights: Optional[np.ndarray] = None) -> np.ndarray:
        """
        The mean same-concept distance divided by the mean different-concept
        distance, for every pair. ``weights`` (one per core concept) resample
        concepts for the bootstrap. NaN where fewer than MIN_CONCEPTS concepts
        are shared or the different-concept mean is not positive.
        """
        w = np.ones(K) if weights is None else np.asarray(weights, dtype=float)
        shared = np.isfinite(self.diag)
        with np.errstate(invalid="ignore", divide="ignore"):
            same = np.where(shared, self.diag, 0) @ w / (shared @ w)
            ww = np.where(np.isfinite(self.off_d), w[self.off_i] * w[self.off_j], 0.0)
            base = np.nansum(np.nan_to_num(self.off_d) * ww, axis=1) / ww.sum(axis=1)
            result = same / base
        result[(shared.sum(axis=1) < MIN_CONCEPTS) | ~(base > 0)] = np.nan
        return result


def distance(a: Wordlist, b: Wordlist, scorer, seed: str = "") -> Optional[float]:
    """The normalized PMI distance between two languages (None when undefined)."""
    comp = pair_components(a, b, scorer, seed)
    if comp is None:
        return None
    value = Components([comp]).values()[0]
    return None if np.isnan(value) else float(value)


# ----- crown divergence, envelope and the cut -----


def crown_pairs(glottolog: Glottolog, lists: Dict[str, Wordlist]) -> Dict[str, List[Tuple[str, str]]]:
    """
    Cross-branch language pairs of every node (see tree.crown_pairs), on the
    Glottolog tree of the in-scope languages; ``lists`` must be keyed by
    in-scope languages (others raise KeyError).
    """
    return tree.crown_pairs(glottolog.tree(), lists, MAX_PAIRS)


class Crowns:
    """Pair components for every node's cross-branch pairs."""

    def __init__(self, glottolog: Glottolog, lists: Dict[str, Wordlist], scorer):
        pairs = crown_pairs(glottolog, lists)
        unique = sorted({p for ps in pairs.values() for p in ps})
        items, keep = [], []
        for x, y in unique:
            comp = pair_components(lists[x], lists[y], scorer, f"{x}|{y}")
            if comp is not None:
                items.append(comp)
                keep.append((x, y))
        self.components = Components(items)
        row = {p: i for i, p in enumerate(keep)}
        self.nodes = sorted(pairs)
        self.members = [np.array([row[p] for p in pairs[n] if p in row], dtype=int) for n in self.nodes]
        self.n_pairs = len(keep)

    def divergence(self, weights: Optional[np.ndarray] = None, rng=None) -> Dict[str, dict]:
        """
        {node: {D, n_pairs}}: the mean distance over the node's defined pairs.
        With ``rng``, each node's pairs are resampled with replacement.
        """
        values = self.components.values(weights)
        out = {}
        for node, idx in zip(self.nodes, self.members):
            v = values[idx]
            v = v[~np.isnan(v)]
            if len(v):
                n = len(v)
                if rng is not None:
                    v = v[rng.integers(0, n, n)]
                out[node] = {"D": float(v.mean()), "n_pairs": int(n)}
        return out


def envelope(glottolog: Glottolog, crowns: Dict[str, dict], rule: str = "own") -> Dict[str, float]:
    """
    The value c(u) on which the cut is made, on Glottolog (see tree.cut_values).
    "max" guarantees that no measured sub-clade of a genus exceeds delta, but a
    maximum over many noisy descendants inflates the value; see ENVELOPE_RULE.
    """
    return tree.cut_values(glottolog.tree(), crowns, rule)


def divergence_genera(
    glottolog: Glottolog, env: Dict[str, float], delta: float, languages=None
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    ({language: genus}, {language: method}) on Glottolog (see tree.genera).
    ``languages`` restricts the walk to some of the in-scope languages; any
    other glottocode (a dialect, or an excluded category) raises KeyError.
    """
    return tree.genera(glottolog.tree(), env, delta, languages)


def genealogical_wals(wl: Dict[str, str]) -> Dict[str, str]:
    """WALS genera without the non-genealogical "Creoles and Pidgins" label."""
    return {gc: g for gc, g in wl.items() if g != NON_GENEALOGICAL_WALS_GENUS}


def calibration_families(
    glottolog: Glottolog, wl: Dict[str, str], min_genera: int = 2
) -> Dict[str, List[str]]:
    """
    {family: its WALS-labelled languages}, for families with at least
    ``min_genera`` WALS genera (and at least two such languages).
    """
    by_family = defaultdict(list)
    for gc in sorted(wl):
        by_family[glottolog.family_gc(gc)].append(gc)
    return {
        f: langs
        for f, langs in sorted(by_family.items())
        if len(langs) >= 2 and len({wl[x] for x in langs}) >= min_genera
    }


def yardstick_languages(glottolog: Glottolog, wl: Dict[str, str]) -> List[str]:
    """The WALS-labelled Indo-European languages, Dryer's reference family."""
    return sorted(gc for gc in wl if glottolog.family_gc(gc) == YARDSTICK_FAMILY)


def stepwise(glottolog: Glottolog, env: Dict[str, float], languages, score) -> np.ndarray:
    """score(partition of ``languages``) at every value of DELTA_GRID (see tree.stepwise)."""
    return tree.stepwise(glottolog.tree(), env, languages, score, DELTA_GRID)


smooth = tree.smooth


class Calibration(tree.Calibration):
    """
    Agreement with WALS of every calibration family across DELTA_GRID: the
    matrix ``ari`` has one row per family and one column per grid value.
    """

    def __init__(self, glottolog: Glottolog, env: Dict[str, float], wl: Dict[str, str], min_genera: int = 2):
        super().__init__(glottolog.tree(), env, wl, min_genera, glottolog.family_gc, DELTA_GRID)
        self.families = self.groups


def calibrate_delta(glottolog, env, wl) -> Tuple[float, float, List[float]]:
    """
    delta maximizing the mean ARI against WALS over the calibration families,
    averaged over a window of +-SMOOTHING; the median of tied grid values.
    """
    return Calibration(glottolog, env, wl).delta()


def depth_baseline(glottolog: Glottolog, depth: int) -> Dict[str, str]:
    """
    A fixed-depth cut, as a baseline: the node ``depth`` levels below the family
    root, or the language's parent group when the language is shallower; a
    language under a group that is cut further down elsewhere is its own unit.
    """
    cut = {}
    for r in glottolog.in_scope_languages():
        lineage = glottolog.lineage(r["glottocode"])
        if len(lineage) == 1:
            cut[r["glottocode"]] = lineage[0]
        else:
            cut[r["glottocode"]] = lineage[min(depth, len(lineage) - 2)]
    divided = set()
    for gc, node in cut.items():
        lineage = glottolog.lineage(gc)
        divided.update(lineage[: lineage.index(node)])
    return {gc: gc if node in divided else node for gc, node in cut.items()}


def agreement(glottolog: Glottolog, genus: Dict[str, str], wl: Dict[str, str]) -> dict:
    """Pooled ARI, mean per-family ARI and macro agreement of a partition with WALS."""
    langs = sorted(wl)
    families = calibration_families(glottolog, wl)
    return {
        "languages": len(langs),
        "families": len(families),
        "pooled_ari": round(float(adjusted_rand_score([wl[x] for x in langs], [genus[x] for x in langs])), 4),
        "mean_family_ari": round(
            float(np.mean([adjusted_rand_score([wl[x] for x in m], [genus[x] for x in m]) for m in families.values()])),
            4,
        ),
        **wals_genus_metrics(genus, wl),
    }


def wals_genus_metrics(genus: Dict[str, str], wl: Dict[str, str]) -> dict:
    """
    Macro agreement with WALS: completeness averages over WALS genera with at
    least two shared languages; purity over proposed genera with at least two
    WALS-labelled languages.
    """
    by_wals, by_ours = defaultdict(list), defaultdict(list)
    for gc, label in wl.items():
        by_wals[label].append(genus[gc])
        by_ours[genus[gc]].append(label)
    multi = [v for v in by_wals.values() if len(v) >= 2]
    return {
        "completeness": round(
            float(np.mean([Counter(v).most_common(1)[0][1] / len(v) for v in multi])), 4
        ),
        "contained": round(float(np.mean([len(set(v)) == 1 for v in multi])), 4),
        "purity": round(
            float(
                np.mean(
                    [
                        Counter(v).most_common(1)[0][1] / len(v)
                        for v in by_ours.values()
                        if len(v) >= 2
                    ]
                )
            ),
            4,
        ),
        "wals_genera_with_two_or_more": len(multi),
    }


def bootstrap(glottolog, crowns: Crowns, wl, rule, replicates, fixed_delta, seed=20261101):
    """
    Resample the 40 core concepts and each node's language pairs with
    replacement, recompute every crown divergence and recut, once with delta
    recalibrated and once at ``fixed_delta``. Returns the recalibrated deltas
    and both lists of partitions.
    """
    rng = np.random.default_rng(seed)
    deltas, recalibrated, fixed = [], [], []
    for _ in range(replicates):
        weights = rng.multinomial(K, np.full(K, 1 / K)).astype(float)
        env = envelope(glottolog, crowns.divergence(weights, rng), rule)
        delta, _, _ = calibrate_delta(glottolog, env, wl)
        deltas.append(delta)
        recalibrated.append(divergence_genera(glottolog, env, delta)[0])
        fixed.append(divergence_genera(glottolog, env, fixed_delta)[0])
    return deltas, recalibrated, fixed


def genus_stability(genus: Dict[str, str], partitions) -> Dict[str, float]:
    """Share of replicates in which each genus reappears with exactly its members."""
    members = defaultdict(set)
    for gc, g in genus.items():
        members[g].add(gc)
    hits = Counter()
    for partition in partitions:
        classes = defaultdict(set)
        for gc, g in partition.items():
            classes[g].add(gc)
        recovered = {frozenset(m) for m in classes.values()}
        for g, m in members.items():
            hits[g] += frozenset(m) in recovered
    return {g: hits[g] / len(partitions) for g in members}


# ----- stage -----


def spearman(x, y) -> float:
    """Spearman's rank correlation, ties averaged."""
    def ranks(v):
        v = np.asarray(v, dtype=float)
        order = np.argsort(v, kind="mergesort")
        r = np.empty(len(v))
        r[order] = np.arange(len(v))
        for value in np.unique(v):
            tie = v == value
            r[tie] = r[tie].mean()
        return r

    return float(np.corrcoef(ranks(x), ranks(y))[0, 1])


def languages_below_another(glottolog: Glottolog) -> int:
    """
    In-scope languages with another in-scope language among their ancestors.
    Propositions 1 and 2 of the definition (docs/definition.md) assume there are none.
    """
    inscope = {r["glottocode"] for r in glottolog.in_scope_languages()}
    return sum(any(a in inscope for a in glottolog.ancestors(gc)) for gc in inscope)


def run(data_dir: Path) -> int:
    glottolog = Glottolog.load()
    genus_name = genus_namer(glottolog)
    print("Loading ASJP core wordlists (one doculect per language) ...")
    lists = load_wordlists(data_dir, glottolog)
    print(f"{len(lists)} in-scope languages with >= {MIN_CONCEPTS} core concepts")
    print("Learning sound correspondences ...")
    scorer, training = pmi.train(lists, glottolog)
    print(f"  {training}")
    print("Measuring crown divergence ...")
    crowns = Crowns(glottolog, lists, scorer)
    measured = {n: {**v, "D": round(v["D"], DECIMALS)} for n, v in crowns.divergence().items()}
    print(f"crown divergence measured at {len(measured)} nodes from {crowns.n_pairs} pairs")
    env = envelope(glottolog, measured, ENVELOPE_RULE)
    wl = genealogical_wals(wals_eval_set(glottolog, load_wals(sources_dir(data_dir))))
    calibration = Calibration(glottolog, env, wl)
    delta, objective, tied = calibration.delta()
    print(f"delta = {delta} (mean family ARI {objective:.3f}; tied {tied})")
    genus, method = divergence_genera(glottolog, env, delta)
    print(f"bootstrap over concepts and pairs ({BOOTSTRAP_REPLICATES} replicates) ...")
    deltas, partitions, fixed_partitions = bootstrap(
        glottolog, crowns, wl, ENVELOPE_RULE, BOOTSTRAP_REPLICATES, delta
    )
    stability = genus_stability(genus, partitions)
    stability_fixed = genus_stability(genus, fixed_partitions)

    members = defaultdict(list)
    for gc in sorted(genus):
        members[genus[gc]].append(gc)

    def upper(node):
        """The smallest cut value above the node: the genus exists up to there."""
        above = [env[a] for a in glottolog.ancestors(node) if a in env]
        return round(min(above), DECIMALS) if above else ""

    def value(table, node, key=None):
        if node not in table:
            return ""
        return round(table[node][key] if key else table[node], DECIMALS)

    lang_path = data_dir / "genera.tsv"
    with lang_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["glottocode", "name", "family", "genus_id", "genus_name", "genus_glottolog_name", "method"])
        for gc in sorted(genus):
            w.writerow(
                [
                    gc,
                    glottolog.name(gc),
                    glottolog.family_name(glottolog.family_gc(gc)),
                    genus[gc],
                    genus_name(genus[gc]),
                    glottolog.name(genus[gc]),
                    method[gc],
                ]
            )
    sum_path = data_dir / "genera_summary.tsv"
    with sum_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(
            [
                "genus_id",
                "genus_name",
                "genus_glottolog_name",
                "family",
                "n_languages",
                "method",
                "crown_divergence",
                "crown_pairs",
                "cut_value",
                "upper_value",
                "margin_below",
                "margin_above",
                "stability",
                "stability_fixed_delta",
                "unclassified_node",
            ]
        )
        for node, langs in sorted(members.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            cut, top = value(env, node), upper(node)
            w.writerow(
                [
                    node,
                    genus_name(node),
                    glottolog.name(node),
                    glottolog.family_name(glottolog.family_gc(node)),
                    len(langs),
                    method[langs[0]],
                    value(measured, node, "D"),
                    measured[node]["n_pairs"] if node in measured else "",
                    cut,
                    top,
                    round(delta - cut, DECIMALS) if cut != "" else "",
                    round(top - delta, DECIMALS) if top != "" else "",
                    round(stability[node], 3),
                    round(stability_fixed[node], 3),
                    # an "Unclassified" node collects languages not placed in a subgroup: a residual group
                    int(glottolog.name(node).startswith("Unclassified")),
                ]
            )
    node_path = data_dir / "nodes.tsv"
    with node_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["node", "name", "family", "depth", "crown_divergence", "crown_pairs", "cut_value"])
        for node in sorted(measured):
            w.writerow(
                [
                    node,
                    glottolog.name(node),
                    glottolog.family_name(glottolog.family_gc(node)),
                    len(glottolog.ancestors(node)),
                    round(measured[node]["D"], DECIMALS),
                    measured[node]["n_pairs"],
                    value(env, node),
                ]
            )

    # ----- calibration and evaluation -----
    groups = defaultdict(list)
    for gc, g in genus.items():
        groups[g].append(gc)
    crown_values = [measured[g]["D"] for g, m in groups.items() if len(m) > 1 and g in measured]
    q = np.percentile(crown_values, [10, 25, 50, 75, 90])

    def at(d):
        g, _ = divergence_genera(glottolog, env, d)
        return {
            "delta": d,
            "genera": len(set(g.values())),
            "languages_changing_genus": sum(g[x] != genus[x] for x in genus),
        }

    above = {n for n, v in measured.items() if v["D"] > delta}
    divergence_cut = [g for g, m in members.items() if method[m[0]] == "divergence"]
    with_inversion = 0
    for g in divergence_cut:
        outside = set(glottolog.lineage(g))
        inside = {n for gc in members[g] for n in glottolog.lineage(gc)} - outside
        with_inversion += bool(inside & above)

    rows = np.arange(len(calibration.names))
    rng = np.random.default_rng(20261102)
    resampled = [calibration.delta(rng.choice(rows, len(rows)))[0] for _ in range(FAMILY_REPLICATES)]
    resampled_range = [round(float(v), 4) for v in np.percentile(resampled, [5, 50, 95])]
    held_out = calibration.held_out()
    released_k = calibration.at(delta)
    sizes_wl = np.array([len(calibration.families[n]) for n in calibration.names])
    genera_wl = np.array([len({wl[x] for x in calibration.families[n]}) for n in calibration.names])

    def family_row(f, name):
        best = calibration.ari[f].max()
        tied_f = [d for d, v in zip(DELTA_GRID, calibration.ari[f]) if np.isclose(v, best)]
        return {
            "family": glottolog.name(name),
            "languages": int(sizes_wl[f]),
            "wals_genera": int(genera_wl[f]),
            "tied": [min(tied_f), max(tied_f)],
            "ari_best": round(float(best), 4),
            "ari_at_delta": round(float(calibration.ari[f, released_k]), 4),
        }

    family_rows = sorted(
        (family_row(f, name) for f, name in enumerate(calibration.names)),
        key=lambda r: (-r["languages"], r["family"]),
    )
    sizable = [r for r in family_rows if r["languages"] >= 10]

    def with_delta(d, **extra):
        return {"delta": d, **extra, **at(d)}

    yardstick = yardstick_languages(glottolog, wl)
    ie = calibration.names.index(YARDSTICK_FAMILY)
    everyone = sorted(wl)
    pooled_curve = stepwise(
        glottolog, env, everyone,
        lambda h: adjusted_rand_score([wl[x] for x in everyone], [h[x] for x in everyone]),
    )
    single = Calibration(glottolog, env, wl, min_genera=1)
    alternatives = {
        "unsmoothed": with_delta(calibration.delta(half_width=0)[0]),
        "window_0.01": with_delta(calibration.delta(half_width=0.01)[0]),
        "window_0.03": with_delta(calibration.delta(half_width=0.03)[0]),
        "families_with_3_wals_genera": with_delta(calibration.delta(rows[genera_wl >= 3])[0]),
        "families_with_10_wals_languages": with_delta(calibration.delta(rows[sizes_wl >= 10])[0]),
        "weighted_by_languages": with_delta(calibration.delta(weights=sizes_wl)[0]),
        "including_single_genus_families": with_delta(single.delta()[0], families=len(single.names)),
        "pooled_ari": with_delta(Calibration.choose(pooled_curve)[0]),
        "indo_european_only": with_delta(
            Calibration.choose(calibration.ari[ie])[0],
            tied=[min(d for d, v in zip(DELTA_GRID, calibration.ari[ie]) if np.isclose(v, calibration.ari[ie].max())),
                  max(d for d, v in zip(DELTA_GRID, calibration.ari[ie]) if np.isclose(v, calibration.ari[ie].max()))],
        ),
    }

    # Null: crown divergence shuffled across measured nodes, within or across families.
    names = sorted(measured)
    values = np.array([measured[n]["D"] for n in names])
    family_of = np.array([glottolog.family_gc(n) for n in names])
    null = {"across": [], "within": []}
    perm_rng = np.random.default_rng(20261103)
    for _ in range(PERMUTATIONS):
        for kind in null:
            shuffled = values.copy()
            if kind == "across":
                shuffled = perm_rng.permutation(values)
            else:
                for fam in np.unique(family_of):
                    idx = np.where(family_of == fam)[0]
                    shuffled[idx] = perm_rng.permutation(values[idx])
            env_null = envelope(glottolog, {n: {"D": float(v)} for n, v in zip(names, shuffled)}, rule="own")
            cal_null = Calibration(glottolog, env_null, wl)
            null[kind].append((cal_null.delta()[1], float(np.mean([a for _, _, a in cal_null.held_out()]))))

    # Baseline: the depth of a fixed-depth cut chosen by the same criterion, with families held out.
    depths = list(range(1, 7))
    depth_parts = [depth_baseline(glottolog, k) for k in depths]
    depth_ari = np.array(
        [
            [adjusted_rand_score([wl[x] for x in langs], [b[x] for x in langs]) for b in depth_parts]
            for langs in calibration.families.values()
        ]
    )
    depth_held = [
        float(depth_ari[f, int(np.argmax(depth_ari[rows != f].mean(axis=0)))]) for f in rows
    ]

    non_ie = {gc: g for gc, g in wl.items() if glottolog.family_gc(gc) != YARDSTICK_FAMILY}
    margins = [
        (stability[g], min(delta - env[g], top - delta))
        for g, m in members.items()
        if method[m[0]] == "divergence" and len(m) > 1 and (top := upper(g)) != ""
    ]

    def by_size(min_size):
        by_wals = defaultdict(list)
        for gc, label in wl.items():
            by_wals[label].append(genus[gc])
        big = [v for v in by_wals.values() if len(v) >= min_size]
        return {
            "min_languages": min_size,
            "wals_genera": len(big),
            "completeness": round(float(np.mean([Counter(v).most_common(1)[0][1] / len(v) for v in big])), 4),
            "contained": round(float(np.mean([len(set(v)) == 1 for v in big])), 4),
        }

    multi = [g for g, m in members.items() if len(m) > 1]
    sizes = np.array([len(m) for m in members.values()])
    block = {
        "delta": delta,
        "envelope_rule": ENVELOPE_RULE,
        "distance": {
            "word": "PMI alignment (asymcat smoothed PMI, linear gaps)",
            "gap": pmi.GAP,
            "iterations": pmi.ITERATIONS,
            "training_language_pairs": pmi.LANGUAGE_PAIRS,
            "probable_cognate_threshold": pmi.SELECT,
            "smoothing": pmi.SMOOTHING,
            **training,
            "off_diagonal_pairs": OFF_DIAGONAL,
        },
        "calibration": {
            "criterion": (
                "mean ARI against WALS genera over Glottolog families with at least two WALS "
                f"genera, averaged over a window of +-{SMOOTHING} on a {GRID_STEP} grid"
            ),
            "families": len(calibration.names),
            "languages": sum(len(m) for m in calibration.families.values()),
            "excluded_wals_label": NON_GENEALOGICAL_WALS_GENUS,
            "smoothing": SMOOTHING,
            "grid_step": GRID_STEP,
            "objective": round(objective, 4),
            "objective_unsmoothed_at_delta": round(float(calibration.objective()[released_k]), 4),
            "tied_deltas": [min(tied), max(tied)],
            "family_resampling": {
                "replicates": FAMILY_REPLICATES,
                "delta_percentiles_5_50_95": resampled_range,
                "ends": [at(resampled_range[0]), at(resampled_range[2])],
            },
            "leave_one_family_out": {
                "deltas": dict(sorted(Counter(str(d) for _, d, _ in held_out).items())),
                "mean_held_out_ari": round(float(np.mean([a for _, _, a in held_out])), 4),
                "mean_ari_at_delta": round(float(calibration.ari[:, released_k].mean()), 4),
            },
            "alternatives": alternatives,
            "null": {
                "permutations": PERMUTATIONS,
                **{
                    kind: {
                        "mean_objective": round(float(np.mean([o for o, _ in v])), 4),
                        "max_objective": round(float(np.max([o for o, _ in v])), 4),
                        "mean_held_out_ari": round(float(np.mean([h for _, h in v])), 4),
                        "max_held_out_ari": round(float(np.max([h for _, h in v])), 4),
                    }
                    for kind, v in null.items()
                },
            },
            "family_optima": family_rows,
            "family_optima_spread": {
                "families": len(sizable),
                "midpoint_percentiles_25_50_75": [
                    round(float(v), 4)
                    for v in np.percentile([(r["tied"][0] + r["tied"][1]) / 2 for r in sizable], [25, 50, 75])
                ],
            },
            "curve": [
                {
                    "delta": d,
                    "objective": round(float(calibration.objective()[k]), 4),
                    "objective_smoothed": round(float(v), 4) if np.isfinite(v := smooth(calibration.objective())[k]) else None,
                    "indo_european_ari": round(float(calibration.ari[ie, k]), 4),
                    "pooled_ari": round(float(pooled_curve[k]), 4),
                    "genera": len(set(divergence_genera(glottolog, env, d)[0].values())),
                }
                for k, d in enumerate(DELTA_GRID)
                if k % CURVE_STEP == 0
            ],
            "indo_european": {
                "languages": len(yardstick),
                "ari": round(float(calibration.ari[ie, released_k]), 4),
                "proposed_genera": len({genus[gc] for gc in yardstick}),
                "wals_genera": len({wl[gc] for gc in yardstick}),
                "genera": [
                    {
                        "genus": genus_name(g),
                        "languages": len(m),
                        "wals_genera": sorted({wl[gc] for gc in m}),
                    }
                    for g, m in sorted(
                        (
                            (g, [gc for gc in yardstick if genus[gc] == g])
                            for g in {genus[gc] for gc in yardstick}
                        ),
                        key=lambda kv: (-len(kv[1]), genus_name(kv[0])),
                    )
                ],
            },
        },
        "evaluation": {
            "all": agreement(glottolog, genus, wl),
            "outside_indo_european": agreement(glottolog, genus, non_ie),
            "by_wals_genus_size": [by_size(2), by_size(10)],
            "held_out_mean_family_ari": round(float(np.mean([a for _, _, a in held_out])), 4),
            "baselines": [
                {"depth": k, "genera": len(set(b.values())), **agreement(glottolog, b, wl)}
                for k in BASELINE_DEPTHS
                for b in [depth_baseline(glottolog, k)]
            ],
            "tuned_depth": {
                "depths": depths,
                "in_sample_mean_family_ari": round(float(depth_ari.mean(axis=0).max()), 4),
                "best_depth": depths[int(np.argmax(depth_ari.mean(axis=0)))],
                "held_out_mean_family_ari": round(float(np.mean(depth_held)), 4),
            },
        },
        "stability_and_margin": {
            "genera": len(margins),
            "spearman": round(spearman([a for a, _ in margins], [b for _, b in margins]), 4),
            "median_margin_stability_below_0.5": round(float(np.median([b for a, b in margins if a < 0.5])), 4),
            "median_margin_stability_0.9_or_more": round(float(np.median([b for a, b in margins if a >= 0.9])), 4),
        },
        "divergence_genera_cut_on_subclade_values": sum(
            method[m[0]] == "divergence" and g not in measured for g, m in members.items()
        ),
        "core_concepts": K,
        "min_concepts": MIN_CONCEPTS,
        "max_pairs_per_node": MAX_PAIRS,
        "languages": len(genus),
        "languages_with_wordlists": len(lists),
        "pairs": crowns.n_pairs,
        "measured_nodes": len(measured),
        "nodes_measured_from_one_pair": sum(v["n_pairs"] == 1 for v in measured.values()),
        "n_genera": len(members),
        "largest_genus": genus_name(max(members, key=lambda g: (len(members[g]), g))),
        "genus_sizes": {
            "median": float(np.median(sizes)),
            "mean": round(float(sizes.mean()), 4),
            "singletons": int((sizes == 1).sum()),
            "max": int(sizes.max()),
        },
        "divergence_cut_genera": len(divergence_cut),
        "divergence_cut_genera_with_measured_subclade_above_delta": with_inversion,
        "methods": {
            "languages": dict(sorted(Counter(method.values()).items())),
            "genera": dict(sorted(Counter(method[m[0]] for m in members.values()).items())),
        },
        "bootstrap": {
            "replicates": BOOTSTRAP_REPLICATES,
            "delta_percentiles_5_50_95": [
                round(float(v), 4) for v in np.percentile(deltas, [5, 50, 95])
            ],
            "mean_language_stability": round(
                float(np.mean([stability[genus[gc]] for gc in genus])), 4
            ),
            "multi_language_genera": len(multi),
            "multi_language_genera_stable_90": sum(stability[g] >= 0.9 for g in multi),
            "mean_language_stability_fixed_delta": round(
                float(np.mean([stability_fixed[genus[gc]] for gc in genus])), 4
            ),
            "multi_language_genera_stable_90_fixed_delta": sum(
                stability_fixed[g] >= 0.9 for g in multi
            ),
            "resampled": "core concepts and each node's language pairs",
        },
        "divergence_cut_genera_from_one_pair": sum(
            g in measured and measured[g]["n_pairs"] == 1 for g in divergence_cut
        ),
        "unmeasured_genera_with_wordlists": sum(
            any(gc in lists for gc in m)
            for g, m in members.items()
            if method[m[0]] in ("unmeasured-clade", "unmeasured-family")
        ),
        "crown_spread": {
            "genera": len(crown_values),
            "percentiles_10_25_50_75_90": [round(float(v), 4) for v in q],
            "iqr": round(float(q[3] - q[1]), 4),
        },
    }
    params = {
        "sources": {
            "glottolog": {
                "version": GLOTTOLOG_VERSION,
                "release_tag_object": GLOTTOLOG_RELEASE_TAG_OBJECT,
                "release_commit": GLOTTOLOG_RELEASE_COMMIT,
                "cldf_commit": GLOTTOLOG_CLDF_COMMIT,
                "doi": GLOTTOLOG_DOI,
            },
            "asjp": {"repository": "lexibank/asjp", "commit": ASJP_REF},
            "wals": {"repository": "cldf-datasets/wals", "release": WALS_REF},
        },
        "hierarchy": {"languages_below_another_language": languages_below_another(glottolog)},
        "divergence": block,
    }
    (data_dir / "params.json").write_text(json.dumps(params, indent=2))

    cal, boot, ev = block["calibration"], block["bootstrap"], block["evaluation"]
    lines = ["# Glottogenera: the release for Glottolog 5.3\n"]
    lines.append(
        "Genera defined by a divergence threshold: the highest Glottolog clades whose "
        "crown divergence (normalized PMI alignment distance over the 40 ASJP core "
        "concepts, one doculect per language) does not exceed delta. See "
        "`docs/definition.md` and `docs/methods.md`.\n"
    )
    p5, p50, p95 = cal["family_resampling"]["delta_percentiles_5_50_95"]
    lines.append(
        f"- **delta = {delta}**: maximizes the mean ARI against WALS, averaged over a window of +-{SMOOTHING}, over "
        f"{cal['families']} families with at least two WALS genera "
        f"({cal['languages']} languages; mean ARI {cal['objective']:.3f}). Resampling "
        f"families: delta {p5}/{p50}/{p95} (5th/50th/95th percentiles); leaving one "
        f"family out: {cal['leave_one_family_out']['deltas']}."
    )
    for end in cal["family_resampling"]["ends"]:
        lines.append(
            f"  At delta = {end['delta']}: {end['genera']} genera, "
            f"{end['languages_changing_genus']} languages in a different genus."
        )
    alt = cal["alternatives"]
    lines.append(
        f"- Other criteria: pooled ARI over all WALS languages picks delta = "
        f"{alt['pooled_ari']['delta']} ({alt['pooled_ari']['genera']} genera); Indo-European "
        f"alone picks {alt['indo_european_only']['delta']} (tied "
        f"{alt['indo_european_only']['tied'][0]}–{alt['indo_european_only']['tied'][-1]})."
    )
    lines.append(
        f"- {block['n_genera']} genera over {len(genus)} languages; {len(measured)} nodes "
        f"measured from {block['pairs']} language pairs "
        f"({block['nodes_measured_from_one_pair']} from a single pair)."
    )
    lines.append(
        "- Methods (languages): "
        + ", ".join(f"{k} {v}" for k, v in block["methods"]["languages"].items())
        + "."
    )
    b5, b50, b95 = boot["delta_percentiles_5_50_95"]
    lines.append(
        f"- Bootstrap over {boot['resampled']} ({boot['replicates']} replicates): delta "
        f"{b5}/{b50}/{b95}; mean language stability {boot['mean_language_stability']:.3f} "
        f"with delta recalibrated, {boot['mean_language_stability_fixed_delta']:.3f} with "
        f"delta fixed."
    )
    for label, key in (("All WALS languages", "all"), ("Outside Indo-European", "outside_indo_european")):
        m = ev[key]
        lines.append(
            f"- {label} ({m['languages']}): mean family ARI {m['mean_family_ari']:.3f}, pooled "
            f"ARI {m['pooled_ari']:.3f}, completeness {m['completeness']:.3f}, purity "
            f"{m['purity']:.3f}, WALS genera contained {m['contained']:.1%}."
        )
    lines.append(
        f"- Crown divergence of measured multi-language genera: IQR "
        f"{block['crown_spread']['iqr']:.3f}.\n"
    )
    (data_dir / "report.md").write_text("\n".join(lines))
    print(f"Wrote {lang_path}, {sum_path}, {node_path}, report.md; {len(members)} genera")
    return 0
