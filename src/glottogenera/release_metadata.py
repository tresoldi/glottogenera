"""Add source provenance and precomputed sensitivity fields without rescoring."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .divergence import divergence_genera, envelope, load_wordlists_with_provenance
from .glottolog import Glottolog
from .names import genus_namer

SENSITIVITY_DELTA = 0.75
LANGUAGE_COLUMNS = ("macroareas", "asjp_doculect_id", "asjp_core_concepts", "has_usable_wordlist",
                    "genus_id_delta_075", "genus_name_delta_075")
SUMMARY_COLUMNS = ("macroareas", "has_above_threshold_subclade")


def enrich_tables(languages, summary, glottolog, measured, provenance, delta, rule):
    """Return enriched copies, asserting that the existing reference IDs match."""
    cut = envelope(glottolog, measured, rule)
    reference, _ = divergence_genera(glottolog, cut, delta)
    alternative, _ = divergence_genera(glottolog, cut, SENSITIVITY_DELTA)
    name = genus_namer(glottolog)
    if {r["glottocode"]: r["genus_id"] for r in languages} != reference:
        raise ValueError("Reference assignments differ from the recorded rule and threshold")
    areas = {}
    for row in languages:
        gc = row["glottocode"]
        areas[gc] = sorted(set(filter(None, glottolog.by_gc[gc].get("macroareas", "").split(";"))))
    genus_areas = {}
    for row in languages:
        genus_areas.setdefault(row["genus_id"], set()).update(areas[row["glottocode"]])
    above = set()
    for node, value in measured.items():
        if value["D"] > delta:
            above.update(glottolog.ancestors(node))  # Proper descendants only.
    language_rows = [dict(row, macroareas=";".join(areas[row["glottocode"]]),
                          **provenance[row["glottocode"]],
                          genus_id_delta_075=alternative[row["glottocode"]],
                          genus_name_delta_075=name(alternative[row["glottocode"]])) for row in languages]
    summary_rows = [dict(row, macroareas=";".join(sorted(genus_areas[row["genus_id"]])),
                        has_above_threshold_subclade=int(row["genus_id"] in above)) for row in summary]
    return language_rows, summary_rows


def refresh_release(data_dir: Path):
    """Refresh metadata from pinned inputs, preserving all existing fields."""
    def read(name):
        with (data_dir / name).open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh, delimiter="\t"))
    glottolog = Glottolog.load()
    _, provenance = load_wordlists_with_provenance(data_dir, glottolog)
    measured = {r["node"]: {"D": float(r["crown_divergence"])} for r in read("nodes.tsv")}
    params = json.loads((data_dir / "params.json").read_text())["divergence"]
    rows = enrich_tables(read("genera.tsv"), read("genera_summary.tsv"), glottolog, measured,
                         provenance, params["delta"], params["envelope_rule"])
    for filename, table in zip(("genera.tsv", "genera_summary.tsv"), rows):
        with (data_dir / filename).open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(table[0]), delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(table)
    return rows
