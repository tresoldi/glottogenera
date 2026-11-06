"""
Write the pair-level evidence of the distance screen as CSV, from the pickles
of compare_sources.py and heldout_training.py: for every evaluation pair of
languages, its expert cognate distance (cognate pairs) or the dated node it
measures (age pairs), with the values of the distances of the screen's table
and of the held-out training.

Usage: export_screen.py SOURCE_VALUES.pkl HELDOUT_VALUES.pkl OUT_DIR
Writes OUT_DIR/screen_pairs.csv.gz and OUT_DIR/screen_nodes.csv.
"""

import csv
import gzip
import math
import pickle
import sys
from pathlib import Path

MEASURES = ["asjp:pmi-asymcat-smoothed", "asjp:pmi", "gled:pmi-asymcat-smoothed", "gled:levenshtein",
            "asjp:ldnd (released)", "asjp-seg:seqsim:nw", "gled:cognates"]
HELDOUT = ["asjp:pmi (all families)", "asjp:pmi (family held out)"]


def fmt(x):
    """A value, blank when undefined."""
    return "" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.6g}"


def main(source_pkl, heldout_pkl, out):
    src = pickle.load(open(source_pkl, "rb"))
    held = pickle.load(open(heldout_pkl, "rb"))
    out.mkdir(parents=True, exist_ok=True)

    def cells(a, b):
        row = []
        for table, names in ((src["values"], MEASURES), (held["values"], HELDOUT)):
            v = table.get((a, b)) or {}
            for name in names:
                raw, norm = v.get(name, (None, None))
                row += [fmt(raw), fmt(norm)]
        return row

    header = [f"{m} {k}" for m in MEASURES + HELDOUT for k in ("raw", "normalized")]
    with gzip.open(out / "screen_pairs.csv.gz", "wt", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["evidence", "dataset_or_node", "language_a", "language_b", "cognate_distance"] + header)
        for s, a, b, cd in src["cognates"]:
            w.writerow(["cognates", s, a, b, f"{cd:.6g}"] + cells(a, b))
        for node, r in sorted(src["clock"].items()):
            for a, b in r["pairs"]:
                w.writerow(["age", node, a, b, ""] + cells(a, b))
    with (out / "screen_nodes.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["node", "family", "age_years", "pairs"])
        for node, r in sorted(src["clock"].items()):
            w.writerow([node, r["family"], r["age"], len(r["pairs"])])


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], Path(sys.argv[3]))
