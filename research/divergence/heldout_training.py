"""
Does the distance screen flatter PMI alignment because its sound
correspondences were learned from the evaluation families themselves? For
every family in the cognate and dated-tree evaluation, retrain the
correspondences (package glottogenera.pmi, as released) without that family
and score its evaluation pairs with that scorer; compare with the scorer
trained on all families, through the same code.

Usage: python research/divergence/heldout_training.py OUT SOURCE_VALUES_PKL
"""
import json
import pickle
import sys
from multiprocessing import Pool, set_start_method
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")
from glottogenera import divergence as dv, pmi  # noqa: E402
from glottogenera.glottolog import Glottolog  # noqa: E402

OUT, SOURCE = Path(sys.argv[1]), Path(sys.argv[2])
g = Glottolog.load()
CODE = dv.load_wordlists(Path("data"), g)
D = pickle.load(open(SOURCE, "rb"))
cogs, clock, old = D["cognates"], D["clock"], D["values"]
pairs = sorted({(a, b) for _, a, b, _ in cogs} | {p for v in clock.values() for p in v["pairs"]})
pairs = [p for p in pairs if p in old and p[0] in CODE and p[1] in CODE]
# Pairs across two families (a handful in the pooled datasets) are left out.
pairs = [(a, b) for a, b in pairs if g.family_gc(a) == g.family_gc(b)]
by_family = {}
for a, b in pairs:
    by_family.setdefault(g.family_gc(a), []).append((a, b))


def distances(scorer, ps):
    out = {}
    for a, b in ps:
        comp = dv.pair_components(CODE[a], CODE[b], scorer, f"{a}|{b}")
        v = np.nan if comp is None else dv.Components([comp]).values()[0]
        out[(a, b)] = float(v)
    return out


def held_out(family):
    scorer, _ = pmi.train({gc: wl for gc, wl in CODE.items() if g.family_gc(gc) != family}, g)
    return family, distances(scorer, by_family[family])


if __name__ == "__main__":
    set_start_method("fork")
    print(f"{len(pairs)} evaluation pairs in {len(by_family)} families", flush=True)
    full, _ = pmi.train(CODE, g)
    inside = distances(full, pairs)
    outside = {}
    with Pool(4) as pool:
        for family, values in pool.imap_unordered(held_out, sorted(by_family)):
            print(family, len(values), flush=True)
            outside.update(values)
    values = {}
    for p in pairs:
        values[p] = {"asjp:ldnd (released)": old[p]["asjp:ldnd (released)"],
                     "asjp:pmi (all families)": (np.nan, inside[p]),
                     "asjp:pmi (family held out)": (np.nan, outside[p])}
    pickle.dump({"values": values, "cognates": cogs, "clock": clock}, open(OUT / "heldout_values.pkl", "wb"))
    sys.argv = [sys.argv[0], str(OUT)]
    sys.path.insert(0, str(Path(__file__).parent))
    import compare_measures as cm  # noqa: E402  (scoring as in the screen)
    results = [r for r in cm.score(values, cogs, clock) if r["variant"] == "normalized"]
    json.dump(results, open(OUT / "heldout_training.json", "w"), indent=1)
    cm.report(results)
