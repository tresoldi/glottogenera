"""
Sensitivity of the distance screen to the pooling of source varieties: the
deposited judgements (cognates/) give each language an aggregate doculect that
can pool several varieties of the source dataset. Here each language is
represented instead by its single most complete source variety (most core
concepts with a judgement, at least 20 as in the screen; ties: smallest identifier), the expert cognate
distance of every evaluation pair of the screen is recomputed from those
varieties (pairs with fewer than 15 shared concepts are dropped, as in the
screen), and the correlations of the screen's table are compared with those
on the pooled doculects, over the same pairs.

Usage: variety_sensitivity.py RESULTS_DIR   (reads screen_pairs.csv.gz, writes variety_sensitivity.json)
"""

import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).parent))
from cognacy import memberships  # noqa: E402

HERE = Path(__file__).parent
MIN_SHARED = 15
MIN_CONCEPTS = 20  # judged concepts of a doculect or variety, as in the screen
MIN_PAIRS = 30
MEASURES = {"asjp:pmi-asymcat-smoothed normalized": "released distance (PMI alignment)",
            "asjp:ldnd (released) normalized": "LDND"}


def varieties():
    """
    dataset -> Glottocode -> (pooled, single): the {concept: cognate sets} of the doculect the screen uses
    (the aggregate doculect with most judged concepts, at least MIN_CONCEPTS, chosen as compare_measures
    does) and of the language's most complete source variety (also at least MIN_CONCEPTS).
    """
    best = {}
    for path in sorted((HERE / "cognates").glob("*.csv")):
        by_doculect, by_variety = defaultdict(lambda: defaultdict(set)), defaultdict(lambda: defaultdict(set))
        gc_of_doculect, gc_of_variety = {}, {}
        with path.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                sets = memberships(r["Cognacy"])
                if sets:
                    by_doculect[r["doculect"]][r["concept"]].update(sets)
                    gc_of_doculect[r["doculect"]] = r["Glottocode"]
                    by_variety[r["source_language_id"]][r["concept"]].update(sets)
                    gc_of_variety[r["source_language_id"]] = r["Glottocode"]
        pooled = {}
        for doc in by_doculect:  # file order, as in compare_measures.cognate_pairs
            gc = gc_of_doculect[doc]
            if len(by_doculect[doc]) >= MIN_CONCEPTS and (gc not in pooled or len(by_doculect[doc]) > len(pooled[gc])):
                pooled[gc] = by_doculect[doc]
        single = {}
        for v in sorted(by_variety, key=lambda v: (-len(by_variety[v]), v)):
            if len(by_variety[v]) >= MIN_CONCEPTS:
                single.setdefault(gc_of_variety[v], by_variety[v])
        best[path.stem] = {gc: (pooled.get(gc), single.get(gc)) for gc in set(pooled) | set(single)}
    return best


def distance(x, y):
    shared = set(x) & set(y)
    if len(shared) < MIN_SHARED:
        return None
    return 1 - sum(bool(x[c] & y[c]) for c in shared) / len(shared)


def correlations(rows, key):
    """Mean within-dataset Spearman correlation (datasets with >= MIN_PAIRS pairs) and pooled one."""
    within, xs, ys = [], [], []
    for s in sorted({r[0] for r in rows}):
        pts = [(cd, v[key]) for d, cd, v in rows if d == s and v.get(key) is not None]
        if len(pts) >= MIN_PAIRS:
            within.append(spearmanr(*zip(*pts)).statistic)
            xs += [c for c, _ in pts]
            ys += [v for _, v in pts]
    return float(np.mean(within)), float(spearmanr(xs, ys).statistic), len(within)


def main(results):
    best = varieties()
    pooled, single, dropped = [], [], 0
    with gzip.open(results / "screen_pairs.csv.gz", "rt", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["evidence"] != "cognates":
                continue
            values = {k: float(r[k]) if r[k] else None for k in MEASURES}
            s, a, b = r["dataset_or_node"], r["language_a"], r["language_b"]
            (pa, sa), (pb, sb) = best[s].get(a, (None, None)), best[s].get(b, (None, None))
            dp = distance(pa, pb) if pa and pb else None
            ds = distance(sa, sb) if sa and sb else None
            if dp is None or ds is None:
                dropped += 1
                continue
            if abs(dp - float(r["cognate_distance"])) > 1e-5:  # the pooled distance is the screen's
                sys.exit(f"pooled distance differs from the screen for {s} {a} {b}")
            pooled.append((s, dp, values))
            single.append((s, ds, values))
    changed = {}
    for (s, dp, _), (_, ds, _) in zip(pooled, single):
        changed[s] = changed.get(s, 0) + (dp != ds)
    out = {"pairs": len(single), "dropped": dropped, "changed": sum(changed.values()),
           "changed_by_dataset": dict(sorted(changed.items())), "measures": []}
    for key, label in MEASURES.items():
        wp, pp, n = correlations(pooled, key)
        ws, ps, _ = correlations(single, key)
        per = {}
        for s in sorted({x[0] for x in pooled}):
            a = [(cd, v[key]) for d, cd, v in pooled if d == s and v.get(key) is not None]
            b = [(cd, v[key]) for d, cd, v in single if d == s and v.get(key) is not None]
            if len(a) >= MIN_PAIRS:
                per[s] = [round(float(spearmanr(*zip(*a)).statistic), 4), round(float(spearmanr(*zip(*b)).statistic), 4)]
        out["measures"].append({"measure": label, "datasets": n, "within_pooled_doculects": round(wp, 4),
                                "within_single_variety": round(ws, 4), "pooled_pooled_doculects": round(pp, 4),
                                "pooled_single_variety": round(ps, 4), "by_dataset": per})
    (results / "variety_sensitivity.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "measures"}, indent=1))
    for m in out["measures"]:
        print(m["measure"], m["within_pooled_doculects"], m["within_single_variety"])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
