"""
Sensitivity of the distance screen to the pooling of source varieties: the
deposited judgements (cognates/) give each language an aggregate doculect that
can pool several varieties of the source dataset. Here each language is
represented instead by its single most complete source variety (most core
concepts with a judgement; ties: smallest identifier), the expert cognate
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
MIN_PAIRS = 30
MEASURES = {"asjp:pmi-asymcat-smoothed normalized": "released distance (PMI alignment)",
            "asjp:ldnd (released) normalized": "LDND"}


def varieties():
    """dataset -> Glottocode -> {concept: cognate sets} of its most complete source variety."""
    best = {}
    for path in sorted((HERE / "cognates").glob("*.csv")):
        by_variety, glottocode = defaultdict(lambda: defaultdict(set)), {}
        with path.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                sets = memberships(r["Cognacy"])
                if sets:
                    by_variety[r["source_language_id"]][r["concept"]].update(sets)
                    glottocode[r["source_language_id"]] = r["Glottocode"]
        chosen = {}
        for v in sorted(by_variety, key=lambda v: (-len(by_variety[v]), v)):
            chosen.setdefault(glottocode[v], by_variety[v])
        best[path.stem] = chosen
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
    pooled, single = [], []
    with gzip.open(results / "screen_pairs.csv.gz", "rt", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["evidence"] != "cognates":
                continue
            values = {k: float(r[k]) if r[k] else None for k in MEASURES}
            s, a, b = r["dataset_or_node"], r["language_a"], r["language_b"]
            va, vb = best[s].get(a), best[s].get(b)
            d = distance(va, vb) if va and vb else None
            if d is not None:  # the same pairs on both sides
                pooled.append((s, float(r["cognate_distance"]), values))
                single.append((s, d, values))
    out = {"pairs": len(single), "changed": sum(p[1] != q[1] for p, q in zip(pooled, single)), "measures": []}
    for key, label in MEASURES.items():
        wp, pp, n = correlations(pooled, key)
        ws, ps, _ = correlations(single, key)
        out["measures"].append({"measure": label, "datasets": n, "within_pooled_doculects": round(wp, 4),
                                "within_single_variety": round(ws, 4), "pooled_pooled_doculects": round(pp, 4),
                                "pooled_single_variety": round(ps, 4)})
    (results / "variety_sensitivity.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
