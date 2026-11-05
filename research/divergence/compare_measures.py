"""
The evidence for screening word distances, used by compare_sources.py and
heldout_training.py: expert cognate distances between pairs of languages from
the aggregated forms of twelve cognate datasets (COGNATE_FORMS, a CSV with the
columns cognate_source, av_id, Glottocode, concept_id, Cognacy and
Cognate_Detection_Method), crown ages
of the dated Phlorest trees (OUT/ages.json, from ages.py), and the scores
(Spearman correlations, share of the residual variance of log age between
families) of a distance against both.

Imported with the output directory as sys.argv[1].
"""

import csv
import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "src")
sys.path.insert(0, str(Path(__file__).parent))
from glottogenera import divergence as dv  # noqa: E402
from glottogenera.glottolog import Glottolog  # noqa: E402
import measures as ms  # noqa: E402

OUT = Path(sys.argv[1])
COGNATE_FORMS = os.environ.get("COGNATE_FORMS", "cognates/forms.csv")
CORE_CONCEPTS = ["kin-i", "kin-you", "kin-we", "qua-one", "qua-two", "kin-person", "ani-fish", "ani-dog",
             "ani-louse", "agr-tree", "agr-leaf", "bod-skin", "bod-blood", "bod-bone", "bod-horn", "bod-ear",
             "bod-eye", "bod-nose", "bod-tooth", "bod-tongue", "bod-knee", "bod-hand", "bod-breast",
             "bod-liver", "foo-drink", "sns-see", "sns-hear", "bod-die", "mot-come", "phy-sun", "phy-star",
             "phy-water", "phy-stone", "phy-fire", "mot-path", "phy-mountain", "tim-night", "qua-full",
             "tim-new", "lng-name"]
SOURCES = ["iecor", "abvd2026", "grollemundbantu", "bowernpny", "tuled", "uralex", "sagartst",
           "kogansemitic", "hruschkaturkic", "dravlex", "peirosaustroasiatic", "acd"]
PER_DATASET = 1500
PER_NODE = 50

g = Glottolog.load()
SEG = ms.load_segmented(Path("data"), g)
CODE = dv.load_wordlists(Path("data"), g)
COVERED = set(SEG) & set(CODE)


def cognate_pairs():
    csv.field_size_limit(10**8)
    core = set(CORE_CONCEPTS)
    cog = {s: defaultdict(lambda: defaultdict(set)) for s in SOURCES}
    gc_of = {}
    with open(COGNATE_FORMS, newline="") as fh:
        for r in csv.DictReader(fh):
            s = r["cognate_source"]
            if s in cog and r["Cognate_Detection_Method"] == "expert" and r["concept_id"] in core and r["Cognacy"]:
                cog[s][r["av_id"]][r["concept_id"]].add(r["Cognacy"])
                gc_of[r["av_id"]] = r["Glottocode"]
    out = []
    for s, langs in cog.items():
        best = {}
        for av in langs:
            gc = gc_of[av]
            if gc in COVERED and len(langs[av]) >= 20 and (gc not in best or len(langs[av]) > len(langs[best[gc]])):
                best[gc] = av
        avs = sorted(best.values())
        pairs = [(x, y) for i, x in enumerate(avs) for y in avs[i + 1:]]
        random.Random(s).shuffle(pairs)
        n = 0
        for x, y in pairs:
            shared = set(langs[x]) & set(langs[y])
            if len(shared) < 15:
                continue
            cd = 1 - sum(bool(langs[x][c] & langs[y][c]) for c in shared) / len(shared)
            a, b = sorted((gc_of[x], gc_of[y]))
            out.append((s, a, b, cd))
            n += 1
            if n >= PER_DATASET:
                break
    return out


def clock_nodes():
    ages = json.load(open(OUT / "ages.json"))
    roots = defaultdict(float)
    for r in ages:
        roots[r["repo"]] = max(roots[r["repo"]], r["age_years"])
    best = {}
    for r in ages:
        if not r["monophyletic"] or r["leaves"] < 4 or abs(r["age_years"] - roots[r["repo"]]) < 1 or r["age_years"] < 500:
            continue
        if r["node"] not in best or r["leaves"] > best[r["node"]]["leaves"]:
            best[r["node"]] = r
    pairs = dv.crown_pairs(g, {gc: CODE[gc] for gc in COVERED})
    out = {}
    for node, r in best.items():
        if node in pairs:
            ps = sorted(pairs[node])
            random.Random(node).shuffle(ps)
            out[node] = {"age": r["age_years"], "family": r["family"], "pairs": [tuple(sorted(p)) for p in ps[:PER_NODE]]}
    return out


def score(values, cogs, clock):
    """Cognate tracking and clock metrics for every measure and variant."""
    names = sorted({k for v in values.values() if v for k in v})
    results = []
    for name in names:
        for variant, idx in (("raw", 0), ("normalized", 1)):
            def val(a, b):
                v = values.get((a, b))
                return np.nan if not v or name not in v else v[name][idx]
            # cognate tracking within and across datasets
            within, xs, ys = [], [], []
            for s in SOURCES:
                rows = [(cd, val(a, b)) for src, a, b, cd in cogs if src == s]
                rows = [(c, v) for c, v in rows if np.isfinite(v)]
                if len(rows) >= 30:
                    within.append(spearmanr(*zip(*rows)).statistic)
                    xs += [c for c, _ in rows]; ys += [v for _, v in rows]
            if not within:
                continue
            pooled = spearmanr(xs, ys).statistic
            # clock
            nodes = []
            for node, v in clock.items():
                d = [val(a, b) for a, b in v["pairs"]]
                d = [x for x in d if np.isfinite(x)]
                if d:
                    nodes.append((v["age"], np.mean(d), v["family"]))
            age = np.array([n[0] for n in nodes]); dist = np.array([n[1] for n in nodes]); fam = np.array([n[2] for n in nodes])
            rho_age = spearmanr(age, dist).statistic
            old = age >= 2000
            rho_old = spearmanr(age[old], dist[old]).statistic
            y = np.log(age); slope, icept = np.polyfit(dist, y, 1); res = y - (icept + slope * dist)
            fm = {f: res[fam == f].mean() for f in set(fam)}
            between = np.var([fm[f] for f in fam]) / res.var()
            results.append({"measure": name, "variant": variant, "cognate_rho_within": float(np.mean(within)),
                            "cognate_rho_pooled": float(pooled), "comparability": float(pooled / np.mean(within)),
                            "age_rho": float(rho_age), "age_rho_old": float(rho_old), "clock_between_family": float(between),
                            "clock_resid_factor": float(np.exp(res.std())), "dated_nodes": len(nodes)})
    results.sort(key=lambda r: -(r["cognate_rho_within"] + r["cognate_rho_pooled"] + r["age_rho"] + r["age_rho_old"]))
    return results


def report(results):
    print(f"{'measure':40s} {'variant':10s} cog-within cog-pooled ratio  age-rho age-old between factor")
    for r in results:
        print(f"{r['measure']:40s} {r['variant']:10s} {r['cognate_rho_within']:10.3f} {r['cognate_rho_pooled']:10.3f} "
              f"{r['comparability']:5.2f} {r['age_rho']:8.3f} {r['age_rho_old']:7.3f} {r['clock_between_family']:7.0%} {r['clock_resid_factor']:6.2f}")

