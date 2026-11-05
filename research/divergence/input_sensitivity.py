"""
Sensitivity of the released partition to the inputs the bootstrap holds fixed:
the learned sound correspondences (retrained from a different random sample of
training pairs) and the choice of ASJP doculect (a doculect drawn at random
among those with enough core concepts, for every language that has several).
Each replicate recomputes crown divergence, recalibrates delta with the
released criterion and recuts.

Usage: python research/divergence/input_sensitivity.py OUT [REPLICATES]
"""
import csv
import json
import random
import sys
from collections import defaultdict
from multiprocessing import Pool, set_start_method
from pathlib import Path

import numpy as np

sys.path.insert(0, "src")
import glottogenera  # noqa: E402
from glottogenera import divergence as dv, pmi  # noqa: E402
from glottogenera.config import sources_dir  # noqa: E402
from glottogenera.glottolog import Glottolog  # noqa: E402
from glottogenera.wals import load_wals, wals_eval_set  # noqa: E402

OUT = Path(sys.argv[1])
REPLICATES = int(sys.argv[2]) if len(sys.argv) > 2 else 8
g = Glottolog.load()
CODE = dv.load_wordlists(Path("data"), g)
WL = dv.genealogical_wals(wals_eval_set(g, load_wals(sources_dir(Path("data")))))
RELEASED = {r["glottocode"]: r["genus_id"] for r in glottogenera.load_genera()}
STABILITY = {r["genus_id"]: float(r["stability"]) for r in glottogenera.load_genera_summary()}
DELTA = json.loads(Path("data/params.json").read_text())["divergence"]["delta"]


def all_doculects():
    """{glottocode: [wordlist, ...]}: every doculect with at least MIN_CONCEPTS core concepts."""
    inscope = {r["glottocode"] for r in g.in_scope_languages()}
    sources = sources_dir(Path("data"))
    gc_of = {}
    with (sources / "asjp_languages.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("Glottocode") in inscope:
                gc_of[r["ID"]] = r["Glottocode"]
    docs = {}
    with (sources / "asjp_forms.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            i = dv.CORE_INDEX.get(r["Parameter_ID"])
            if r["Language_ID"] not in gc_of or i is None or r.get("Loan") == "true":
                continue
            form = dv.clean_asjp(r.get("Form") or "")
            if form:
                docs.setdefault(r["Language_ID"], [[] for _ in range(dv.K)])[i].append(form)
    out = defaultdict(list)
    for doc in sorted(docs):
        if sum(1 for f in docs[doc] if f) >= dv.MIN_CONCEPTS:
            out[gc_of[doc]].append(docs[doc])
    return out


DOCULECTS = all_doculects()


def replicate(task):
    kind, r = task
    if kind == "correspondences":
        lists = CODE
        pmi.SEED = 1 + r  # the released scorer uses SEED = 1
    else:
        pmi.SEED = 1  # workers are reused: reset the released seed
        rng = random.Random(r)
        lists = {gc: rng.choice(DOCULECTS[gc]) for gc in sorted(CODE)}
    scorer, _ = pmi.train(lists, g)
    env = dv.envelope(g, dv.Crowns(g, lists, scorer).divergence(), dv.ENVELOPE_RULE)
    delta, _, _ = dv.calibrate_delta(g, env, WL)
    genus, _ = dv.divergence_genera(g, env, delta)
    fixed, _ = dv.divergence_genera(g, env, DELTA)
    return kind, r, delta, genus, fixed


def classes(partition):
    out = defaultdict(set)
    for gc, x in partition.items():
        out[x].add(gc)
    return {frozenset(m) for m in out.values()}


if __name__ == "__main__":
    set_start_method("fork")
    several = sum(len(v) > 1 for gc, v in DOCULECTS.items() if gc in CODE)
    print(f"{several} languages have more than one usable doculect", flush=True)
    released_members = defaultdict(set)
    for gc, x in RELEASED.items():
        released_members[x].add(gc)
    multi = {x: frozenset(m) for x, m in released_members.items() if len(m) > 1}
    tasks = [(k, r) for k in ("correspondences", "doculects") for r in range(1, REPLICATES + 1)]
    rows, hits = [], defaultdict(lambda: defaultdict(int))
    with Pool(4) as pool:
        for kind, r, delta, genus, fixed in pool.imap_unordered(replicate, tasks):
            found = classes(genus)
            same = [x for x, m in multi.items() if m in found]
            for x in same:
                hits[kind][x] += 1
            row = {"kind": kind, "replicate": r, "delta": delta, "genera": len(set(genus.values())),
                   "languages_changing_genus": float(np.mean([genus[x] != RELEASED[x] for x in RELEASED])),
                   "multi_language_genera_identical": len(same) / len(multi),
                   "languages_changing_genus_fixed_delta": float(np.mean([fixed[x] != RELEASED[x] for x in RELEASED])),
                   "multi_language_genera_identical_fixed_delta": sum(m in classes(fixed) for m in multi.values()) / len(multi)}
            rows.append(row)
            print(json.dumps(row), flush=True)
    summary = {"replicates_per_kind": REPLICATES, "languages_with_several_doculects": several,
               "multi_language_genera": len(multi), "replicates": sorted(rows, key=lambda r: (r["kind"], r["replicate"]))}
    for kind in ("correspondences", "doculects"):
        rs = [r for r in rows if r["kind"] == kind]
        reappear = {x: hits[kind][x] / len(rs) for x in multi}
        summary[kind] = {
            "deltas": sorted(r["delta"] for r in rs),
            "mean_languages_changing_genus": round(float(np.mean([r["languages_changing_genus"] for r in rs])), 4),
            "mean_multi_language_genera_identical": round(float(np.mean([r["multi_language_genera_identical"] for r in rs])), 4),
            "mean_languages_changing_genus_fixed_delta": round(float(np.mean([r["languages_changing_genus_fixed_delta"] for r in rs])), 4),
            "mean_multi_language_genera_identical_fixed_delta": round(float(np.mean([r["multi_language_genera_identical_fixed_delta"] for r in rs])), 4),
            "identical_by_stability": [
                {"stability": [lo, min(hi, 1)],
                 "genera": len(grp := [x for x in multi if lo <= STABILITY[x] < hi]),
                 "mean_reappearance": round(float(np.mean([reappear[x] for x in grp])), 4)}
                for lo, hi in ((0.9, 1.01), (0.5, 0.9), (0, 0.5))
            ],
        }
    json.dump(summary, open(OUT / "input_sensitivity.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != "replicates"}, indent=1))
