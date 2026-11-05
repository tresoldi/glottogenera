"""
Genera on trees estimated from the ASJP distances, against those on Glottolog.

For every Glottolog family with at least two languages with ASJP wordlists,
the distances between all its languages (the released PMI distance) form a
matrix, from which UPGMA and neighbour-joining trees are estimated. Families
are taken from Glottolog, since distances between families are near their
ceiling. On each forest the genera are cut by crown divergence and delta is
calibrated against WALS exactly as for the release; Glottolog's tree,
restricted to the same languages and with the released crown divergences, is
calibrated the same way for comparison.

Undefined distances (pairs with fewer than 20 shared concepts) are imputed
only to estimate the trees, by the family median (or, as a check, the family
maximum); the crown divergences that the cut uses leave them out, as in the
release. Crown divergences use at most 200 sampled pairs per node, as in the
release; a check recomputes them from all pairs.

Usage: python research/divergence/estimated_trees.py OUT
Writes OUT/estimated_distances.pkl (cache), OUT/estimated_trees.nwk and
OUT/estimated_trees.json (copied to results/).
"""

import json
import pickle
import sys
from collections import defaultdict
from multiprocessing import Pool, set_start_method
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import glottogenera  # noqa: E402
from glottogenera import divergence as dv, pmi  # noqa: E402
from glottogenera.glottolog import Glottolog  # noqa: E402
from glottogenera.tree import (  # noqa: E402
    Calibration, Tree, adjusted_rand, crown_divergence, cut_values, genera, neighbor_joining, upgma,
)
from glottogenera.wals import load_wals, wals_eval_set  # noqa: E402

OUT = Path(sys.argv[1])
DATA = Path("data")
g = Glottolog.load()
LISTS = dv.load_wordlists(DATA, g)
SCORER = None


def work(pairs):
    return [(a, b, dv.distance(LISTS[a], LISTS[b], SCORER, f"{a}|{b}")) for a, b in pairs]


def distances(families):
    cache = OUT / "estimated_distances.pkl"
    if cache.exists():
        return pickle.load(open(cache, "rb"))
    pairs = [(a, b) for langs in families.values() for i, a in enumerate(langs) for b in langs[i + 1:]]
    chunks = [pairs[i:i + 2000] for i in range(0, len(pairs), 2000)]
    print(f"{len(pairs)} language pairs in {len(families)} families", flush=True)
    out = {}
    with Pool(4) as pool:
        for k, part in enumerate(pool.imap_unordered(work, chunks)):
            out.update({(a, b): v for a, b, v in part})
            if k % 100 == 0:
                print(f"  {len(out)} pairs", flush=True)
    pickle.dump(out, open(cache, "wb"))
    return out


def matrix(langs, dist, fill="median"):
    """
    The distance matrix of a family, for estimating its tree; undefined pairs
    take the family median (or maximum). None when no pair is defined.
    """
    n = len(langs)
    m = np.full((n, n), np.nan)
    np.fill_diagonal(m, 0.0)
    for i, a in enumerate(langs):
        for j in range(i + 1, n):
            v = dist[(a, langs[j])]
            m[i, j] = m[j, i] = np.nan if v is None else v
    missing = int(np.isnan(m).sum() // 2)
    upper = m[np.triu_indices(n, 1)]
    if np.isnan(upper).all():
        return None, missing
    if missing:
        m[np.isnan(m)] = (np.nanmedian if fill == "median" else np.nanmax)(upper)
    return m, missing


def matching(genus, reference):
    """
    (share of the genera of ``genus`` whose members are exactly those of a
    genus of ``reference``; share of languages outside the genus of ``genus``
    that holds most of their ``reference`` genus).
    """
    def classes(part):
        out = defaultdict(set)
        for x, g in part.items():
            out[g].add(x)
        return out

    ours, theirs = classes(genus), classes(reference)
    identical = {frozenset(s) for s in theirs.values()}
    same = sum(frozenset(s) in identical for s in ours.values()) / len(ours)
    outside = 0
    for members in theirs.values():
        best = max(sum(genus[x] == g for x in members) for g in {genus[x] for x in members})
        outside += len(members) - best
    return round(same, 4), round(outside / len(genus), 4)


def summary(name, tree, c, wl, released):
    cal = Calibration(tree, c, wl, group=g.family_gc)
    delta, smoothed, tied = cal.delta()
    genus = genera(tree, c, delta)[0]
    langs = sorted(genus)
    held = cal.held_out()
    at_released = genera(tree, c, released["delta"])[0]
    out = {
        "delta": delta,
        "tied": [min(tied), max(tied)],
        "genera": len(set(genus.values())),
        "mean_family_ari_smoothed": round(smoothed, 4),
        "mean_family_ari": round(float(cal.ari[:, cal.at(delta)].mean()), 4),
        "held_out_mean_family_ari": round(float(np.mean([a for _, _, a in held])), 4),
        "pooled_ari": round(adjusted_rand([wl[x] for x in sorted(wl)], [genus[x] for x in sorted(wl)]), 4),
        "ari_with_glottolog_genera": round(adjusted_rand([released["genus"][x] for x in langs], [genus[x] for x in langs]), 4),
        "genera_identical_to_glottolog": matching(genus, released["genus"])[0],
        "languages_outside_matching_genus": matching(genus, released["genus"])[1],
        "at_released_delta": {
            "genera": len(set(at_released.values())),
            "ari_with_glottolog_genera": round(adjusted_rand([released["genus"][x] for x in langs], [at_released[x] for x in langs]), 4),
        },
        "families": len(cal.names),
    }
    print(name, json.dumps(out), flush=True)
    return out, genus


def main():
    global SCORER
    OUT.mkdir(parents=True, exist_ok=True)
    SCORER, _ = pmi.train(LISTS, g)
    by_family = defaultdict(list)
    for gc in sorted(LISTS):
        by_family[g.family_gc(gc)].append(gc)
    families = {f: langs for f, langs in by_family.items() if len(langs) >= 2}
    set_start_method("fork")
    dist = distances(families)
    lookup = lambda a, b: dist.get((a, b) if a < b else (b, a))  # noqa: E731

    wl = dv.genealogical_wals(wals_eval_set(g, load_wals(DATA / "sources")))
    wl = {gc: v for gc, v in wl.items() if gc in LISTS}

    # Glottolog, restricted to the languages with wordlists, with the released D
    parent = {}
    for gc in LISTS:
        lin = g.lineage(gc)
        parent.setdefault(lin[0], None)
        for up, down in zip(lin, lin[1:]):
            parent[down] = up
    glottolog_tree = Tree(parent, sorted(LISTS))
    measured = {r["node"]: {"D": float(r["crown_divergence"])} for r in glottogenera.load_nodes()}
    c_glottolog = cut_values(glottolog_tree, measured)
    params = json.loads((DATA / "params.json").read_text())
    delta0 = params["divergence"]["delta"]
    released = {"delta": delta0, "genus": genera(glottolog_tree, c_glottolog, delta0)[0]}

    results = {"languages": len(LISTS), "families_estimated": len(families),
               "pairs": len(dist), "undefined_pairs": sum(v is None for v in dist.values()),
               "wals_languages": len(wl), "trees": {}}
    results["trees"]["glottolog"], _ = summary("glottolog", glottolog_tree, c_glottolog, wl, released)

    def forest_for(method, build, fill):
        parent, leaves, negative, unresolved = {}, [], 0, 0
        for f, langs in sorted(families.items()):
            m, _ = matrix(langs, dist, fill)
            if m is None:  # no defined distance: the family is left unresolved
                unresolved += 1
                for gc in langs:
                    parent[gc] = f"{f}.{method}.star"
                parent[f"{f}.{method}.star"] = None
            else:
                t, _ = build(langs, m, prefix=f"{f}.{method}.")
                parent.update(t.parent)
                negative += t.info.get("negative_lengths", 0)
            leaves += langs
        for gc in LISTS:  # languages alone in their family stand alone
            if gc not in parent:
                parent[gc] = None
                leaves.append(gc)
        return Tree(parent, leaves), negative, unresolved

    newick = []
    for method, build in (("upgma", upgma), ("nj", neighbor_joining)):
        forest, negative, unresolved = forest_for(method, build, "median")
        crowns = crown_divergence(forest, lookup)
        c = cut_values(forest, crowns)
        results["trees"][method], genus = summary(method, forest, c, wl, released)
        results["trees"][method]["measured_nodes"] = len(crowns)
        results["trees"][method]["unresolved_families"] = unresolved
        if method == "nj":
            results["trees"][method]["negative_lengths_set_to_zero"] = negative
        newick.append(f"[{method}]\n" + forest.to_newick())
        # checks: all pairs instead of a sample of 200; the family maximum for imputation
        all_pairs = cut_values(forest, crown_divergence(forest, lookup, max_pairs=10**9))
        check, genus_all = summary(f"{method} all pairs", forest, all_pairs, wl, released)
        results["trees"][method]["all_pairs"] = {k: check[k] for k in ("delta", "genera", "mean_family_ari", "ari_with_glottolog_genera")}
        results["trees"][method]["all_pairs"]["ari_with_sampled"] = round(adjusted_rand(
            [genus[x] for x in sorted(genus)], [genus_all[x] for x in sorted(genus)]), 4)
        forest_max, _, _ = forest_for(method, build, "max")
        c_max = cut_values(forest_max, crown_divergence(forest_max, lookup))
        check, _ = summary(f"{method} max imputation", forest_max, c_max, wl, released)
        results["trees"][method]["max_imputation"] = {k: check[k] for k in ("delta", "genera", "mean_family_ari", "ari_with_glottolog_genera")}
    (OUT / "estimated_trees.nwk").write_text("\n".join(newick) + "\n")
    json.dump(results, open(OUT / "estimated_trees.json", "w"), indent=1)


if __name__ == "__main__":
    main()
