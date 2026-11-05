"""Paired bootstrap of differences between measures (cognate tracking, clock)."""
import pickle, sys
from collections import defaultdict
import numpy as np
from scipy.stats import spearmanr

D = pickle.load(open(sys.argv[1], "rb"))
values, cogs, clock = D["values"], D["cognates"], D["clock"]
# The baseline, then the candidates, as measure names (normalized variants).
if len(sys.argv) < 4:
    sys.exit("usage: measure_tests.py VALUES_PKL BASELINE CANDIDATE [CANDIDATE ...]")
BASE = (sys.argv[2], 1)
CANDIDATES = [(m, 1) for m in sys.argv[3:]]
rng = np.random.default_rng(7)
B = 1000

def v(m, a, b):
    row = values.get((a, b)); return np.nan if not row else row[m[0]][m[1]]

by_ds = defaultdict(list)
for s, a, b, cd in cogs: by_ds[s].append((a, b, cd))
nodes = list(clock.items())

def cognate_within(m, idx):
    out = []
    for s, rows in by_ds.items():
        r = [rows[i] for i in idx[s]]
        x = np.array([c for _, _, c in r]); y = np.array([v(m, a, b) for a, b, _ in r])
        ok = np.isfinite(y)
        if ok.sum() >= 30: out.append(spearmanr(x[ok], y[ok]).statistic)
    return np.mean(out)

def clock_rho(m, idx, old=False):
    age, dist = [], []
    for i in idx:
        node, info = nodes[i]
        d = [v(m, a, b) for a, b in info["pairs"]]; d = [x for x in d if np.isfinite(x)]
        if d and (not old or info["age"] >= 2000): age.append(info["age"]); dist.append(np.mean(d))
    return spearmanr(age, dist).statistic

full_cog = {s: np.arange(len(r)) for s, r in by_ds.items()}
full_nodes = np.arange(len(nodes))
# Blocked resampling: whole cognate datasets and whole dated phylogenies, since
# pairs within a dataset share languages and nodes within a tree are nested.
datasets = sorted(by_ds)
trees = defaultdict(list)
for i, (_, info) in enumerate(nodes): trees[info["family"]].append(i)
tree_names = sorted(trees)
print(f"# blocks: {len(datasets)} cognate datasets, {len(tree_names)} language families of dated nodes")

def cognate_within_one(m, s):
    rows = by_ds[s]; x = np.array([c for _, _, c in rows]); y = np.array([v(m, a, b) for a, b, _ in rows])
    ok = np.isfinite(y)
    return spearmanr(x[ok], y[ok]).statistic if ok.sum() >= 30 else np.nan

for cand in CANDIDATES:
    diffs = {"cognate within": [], "age": [], "age old": [],
             "cognate within, blocked": [], "age, blocked": [], "age old, blocked": []}
    for _ in range(B):
        ci = {s: rng.integers(0, len(r), len(r)) for s, r in by_ds.items()}
        ni = rng.integers(0, len(nodes), len(nodes))
        diffs["cognate within"].append(cognate_within(cand, ci) - cognate_within(BASE, ci))
        diffs["age"].append(clock_rho(cand, ni) - clock_rho(BASE, ni))
        diffs["age old"].append(clock_rho(cand, ni, True) - clock_rho(BASE, ni, True))
        ds = [datasets[i] for i in rng.integers(0, len(datasets), len(datasets))]
        diffs["cognate within, blocked"].append(np.nanmean([cognate_within_one(cand, s) - cognate_within_one(BASE, s) for s in ds]))
        ti = [i for t in rng.integers(0, len(tree_names), len(tree_names)) for i in trees[tree_names[t]]]
        diffs["age, blocked"].append(clock_rho(cand, ti) - clock_rho(BASE, ti))
        diffs["age old, blocked"].append(clock_rho(cand, ti, True) - clock_rho(BASE, ti, True))
    point = {"cognate within": cognate_within(cand, full_cog) - cognate_within(BASE, full_cog),
             "age": clock_rho(cand, full_nodes) - clock_rho(BASE, full_nodes),
             "age old": clock_rho(cand, full_nodes, True) - clock_rho(BASE, full_nodes, True),
             "cognate within, blocked": cognate_within(cand, full_cog) - cognate_within(BASE, full_cog),
             "age, blocked": clock_rho(cand, full_nodes) - clock_rho(BASE, full_nodes),
             "age old, blocked": clock_rho(cand, full_nodes, True) - clock_rho(BASE, full_nodes, True)}
    print(cand[0], "minus", BASE[0] + ":")
    for k, d in diffs.items():
        lo, hi = np.percentile(d, [2.5, 97.5])
        print(f"   {k:24s} {point[k]:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]  P(diff<=0)={np.mean(np.array(d) <= 0):.3f}")
