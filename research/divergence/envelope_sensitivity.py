"""
Sensitivity of the release to the envelope rule: a measured node is judged by
its own crown divergence ("own", released) or by the largest value at or below
it ("max", which leaves no measured sub-clade of a genus above the threshold).
The "max" partition is cut from the released node values (data/nodes.tsv), at
the released threshold and at a threshold recalibrated by the released
criterion, and compared with the release.

Usage: envelope_sensitivity.py OUT   (writes OUT/envelope_sensitivity.json)
"""

import json
import sys
from pathlib import Path

from sklearn.metrics import adjusted_rand_score

sys.path.insert(0, "src")
import glottogenera  # noqa: E402
from glottogenera import divergence as dv  # noqa: E402
from glottogenera.glottolog import Glottolog  # noqa: E402
from glottogenera.wals import load_wals, wals_eval_set  # noqa: E402


def main(out):
    g = Glottolog.load()
    measured = {r["node"]: {"D": float(r["crown_divergence"]), "n_pairs": int(r["crown_pairs"])}
                for r in glottogenera.load_nodes()}
    released = {r["glottocode"]: r["genus_id"] for r in glottogenera.load_genera()}
    delta = json.loads(Path("data/params.json").read_text())["divergence"]["delta"]
    wl = dv.genealogical_wals(wals_eval_set(g, load_wals(Path("data/sources"))))
    langs = sorted(released)
    rows = []
    for rule in ("own", "max"):
        env = dv.envelope(g, measured, rule)
        recalibrated = dv.calibrate_delta(g, env, wl)[0]
        for label, d in (("released delta", delta), ("recalibrated delta", recalibrated)):
            genus = dv.divergence_genera(g, env, d)[0]
            rows.append({
                "rule": rule, "threshold": label, "delta": d, "genera": len(set(genus.values())),
                "languages_changing_genus": int(sum(genus[x] != released[x] for x in langs)),
                "ari_with_release": round(float(adjusted_rand_score([released[x] for x in langs],
                                                                    [genus[x] for x in langs])), 4),
                "mean_family_ari": dv.agreement(g, genus, wl)["mean_family_ari"],
            })
    (Path(out) / "envelope_sensitivity.json").write_text(json.dumps({"rows": rows}, indent=1) + "\n")
    print(json.dumps(rows, indent=1))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
