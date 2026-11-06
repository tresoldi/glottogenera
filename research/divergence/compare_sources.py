"""
Screen word distances on two lexical sources, ASJP and GLED, against expert
cognates and dated trees, on the languages both sources cover.

Measures: standard LDND on ASJP code (the baseline); PMI alignment with correspondence
scores from our own estimate or from asymcat (pmi_smoothed, tresoldi), on ASJP
code and on GLED segments; every seqsim 0.4 distance on ASJP segments; edit
distance and GLED's automatic cognate sets on GLED.

Usage: python research/divergence/compare_sources.py OUT
"""

import json
import pickle
import sys
from collections import defaultdict
from multiprocessing import Pool, set_start_method
from pathlib import Path

import numpy as np
import seqsim

sys.path.insert(0, "src")
sys.path.insert(0, str(Path(__file__).parent))
import compare_measures as cm  # noqa: E402  (cognate and clock evaluation sets)
import measures as ms  # noqa: E402
import pmi_variants as pmi  # noqa: E402
from glottogenera import pmi as released_pmi  # noqa: E402
import ldnd_reference as lr  # noqa: E402

OUT = Path(sys.argv[1])
g = cm.g
SOURCES = {"asjp": cm.CODE, "asjp-seg": cm.SEG, "gled": ms.load_gled(g)}
COMMON = set.intersection(*(set(s) for s in SOURCES.values()))
ESTIMATORS = {"pmi": "own", "pmi-asymcat-smoothed": "asymcat:pmi_smoothed", "pmi-asymcat-tresoldi": "asymcat:tresoldi"}
MEASURES = defaultdict(dict)  # source -> {name: distance}
for source in ("asjp", "gled"):
    for name, estimator in ESTIMATORS.items():
        MEASURES[source][name] = pmi.train(SOURCES[source], g, estimator=estimator)[0].distance
# the released distance as the package trains it (its sampling of training pairs differs from pmi_variants')
MEASURES["asjp"]["pmi-asymcat-smoothed"] = released_pmi.train(SOURCES["asjp"], g)[0].distance
MEASURES["gled"]["levenshtein"] = ms._seqsim("levenshtein")
MEASURES["gled"]["cognates"] = ms.cognate_distance
for m in sorted(seqsim.METHODS):
    if m != "lzma_ncd":  # degenerate and very slow on short words
        MEASURES["asjp-seg"][f"seqsim:{m}"] = ms._seqsim(m)


def meta(cogs, clock, unique):
    """Sample sizes behind the screen."""
    return {"common_languages": len(COMMON), "cognate_pairs": len(cogs),
            "cognate_datasets": len({s for s, *_ in cogs}), "dated_nodes": len(clock),
            "language_pairs": len(unique),
            "seqsim_distances": sum(1 for m in MEASURES["asjp-seg"] if m.startswith("seqsim:"))}


def work(pair):
    a, b = pair
    row = {}
    for source, measures in MEASURES.items():
        comp = ms.pair_components(SOURCES[source][a], SOURCES[source][b], measures, f"{a}|{b}")
        for name, c in (comp or {}).items():
            row[f"{source}:{name}"] = (ms.distance_from(c, normalized=False), ms.distance_from(c))
    base = lr.ldnd(cm.CODE[a], cm.CODE[b])
    row["asjp:ldnd (released)"] = (np.nan, np.nan if base is None else base)
    return pair, row


if __name__ == "__main__":
    set_start_method("fork")  # workers inherit the trained scorers (3.14 defaults to forkserver)
    cm.COVERED = COMMON
    cogs = cm.cognate_pairs()
    clock = cm.clock_nodes()
    unique = sorted({(a, b) for _, a, b, _ in cogs} | {p for v in clock.values() for p in v["pairs"]})
    unique = [p for p in unique if p[0] in COMMON and p[1] in COMMON]
    print(f"{len(COMMON)} common languages; {len(cogs)} cognate pairs, {len(clock)} dated nodes, "
          f"{len(unique)} language pairs", flush=True)
    with Pool(4) as pool:
        values = dict(pool.map(work, unique, chunksize=50))
    pickle.dump({"values": values, "cognates": cogs, "clock": clock}, open(OUT / "source_values.pkl", "wb"))
    results = cm.score(values, cogs, clock)
    json.dump(results, open(OUT / "sources.json", "w"), indent=1)
    json.dump(meta(cogs, clock, unique), open(OUT / "sources_meta.json", "w"), indent=1)
    cm.report(results)
