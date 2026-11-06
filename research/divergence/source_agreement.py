"""
Robustness of the released (ASJP, PMI) partition to the word distance and the
lexical source: partitions from standard LDND on the same ASJP wordlists and
from PMI alignment on GLED wordlists, each cut both at the released delta and
at a delta recalibrated with the released criterion (mean ARI over families).

GLED derives from ASJP forms, so agreement between the two is a robustness
check, not an independent replication.

Usage: python research/divergence/source_agreement.py OUT
"""
import json, sys
from pathlib import Path
import numpy as np
from sklearn.metrics import adjusted_rand_score
sys.path.insert(0, "src"); sys.path.insert(0, str(Path(__file__).parent))
import glottogenera
from glottogenera import divergence as dv, pmi
from glottogenera.glottolog import Glottolog
from glottogenera.wals import load_wals, wals_eval_set
import ldnd_reference as lr
import measures as ms

OUT = Path(sys.argv[1])
g = Glottolog.load()
released = {r["glottocode"]: r["genus_id"] for r in glottogenera.load_genera()}
stab = {r["genus_id"]: float(r["stability"]) for r in glottogenera.load_genera_summary()}
DELTA = json.loads(Path("data/params.json").read_text())["divergence"]["delta"]
wl = dv.genealogical_wals(wals_eval_set(g, load_wals(Path("data/sources"))))
asjp = dv.load_wordlists(Path("data"), g)
gled = ms.load_gled(g)


def partitions(env):
    delta, objective, tied = dv.calibrate_delta(g, env, wl)
    return delta, dv.divergence_genera(g, env, delta)[0], dv.divergence_genera(g, env, DELTA)[0]


def compare(other, label, covered):
    langs = sorted(released)
    sets = lambda part: {frozenset(x for x in langs if part[x] == gg) for gg in set(part.values())}
    rel_sets, oth_sets = sets(released), sets(other)
    node_of = {frozenset(x for x in langs if released[x] == gg): gg for gg in set(released.values())}
    multi = [s for s in rel_sets if len(s) > 1]
    by = []
    for lo, hi in ((0.9, 1.01), (0.5, 0.9), (0, 0.5)):
        grp = [s for s in multi if lo <= stab[node_of[s]] < hi]
        by.append({"stability": [lo, min(hi, 1)], "genera": len(grp), "identical": float(np.mean([s in oth_sets for s in grp]))})
    # recovery by how much of the genus the compared source covers: a genus with fewer than two covered
    # members cannot be tested by that source, only kept by the rules for unmeasured clades
    by_coverage = []
    for lo, hi, name in ((2, 10**6, "at least two members covered"), (1, 2, "one member covered"),
                         (0, 1, "no member covered")):
        grp = [s for s in multi if lo <= len(s & covered) < hi]
        by_coverage.append({"coverage": name, "genera": len(grp),
                            "stable_genera": sum(stab[node_of[s]] >= 0.9 for s in grp),
                            "identical": float(np.mean([s in oth_sets for s in grp])) if grp else None})
    both = [x for x in langs if x in covered]
    r = {"against": label, "ari": float(adjusted_rand_score([released[x] for x in langs], [other[x] for x in langs])),
         "changing_genus": float(np.mean([released[x] != other[x] for x in langs])),
         "changing_genus_covered": float(np.mean([released[x] != other[x] for x in both])), "covered": len(both),
         "ari_covered": float(adjusted_rand_score([released[x] for x in both], [other[x] for x in both])),
         "identical_multi": sum(s in oth_sets for s in multi), "released_multi": len(multi), "by_stability": by,
         "by_coverage": by_coverage}
    print(json.dumps(r), flush=True)
    return r


ldnd_delta, ldnd_recal, ldnd_fixed = partitions(dv.envelope(g, lr.LdndCrowns(g, asjp).divergence(), dv.ENVELOPE_RULE))
print("LDND delta", ldnd_delta, flush=True)
scorer, _ = pmi.train(gled, g)
gled_delta, gled_recal, gled_fixed = partitions(dv.envelope(g, dv.Crowns(g, gled, scorer).divergence(), dv.ENVELOPE_RULE))
print("GLED delta", gled_delta, flush=True)
covered_asjp, covered_both = set(asjp), set(asjp) & set(gled)
out = {"released_delta": DELTA, "ldnd_delta": ldnd_delta, "gled_delta": gled_delta,
       "gled_languages_with_wordlists": len(gled), "asjp_languages_with_wordlists": len(asjp),
       "comparisons": [compare(ldnd_recal, "LDND, delta recalibrated", covered_asjp),
                       compare(ldnd_fixed, "LDND, released delta", covered_asjp),
                       compare(gled_recal, "GLED PMI, delta recalibrated", covered_both),
                       compare(gled_fixed, "GLED PMI, released delta", covered_both)]}
json.dump(out, open(OUT / "source_agreement.json", "w"), indent=1)
