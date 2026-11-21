"""Provenance edge cases and cross-format sensitivity fields."""
import csv
from collections import defaultdict
from pathlib import Path

import glottogenera
from glottogenera.divergence import ASJP_CORE, load_wordlists_with_provenance
from glottogenera.glottolog import Glottolog


def test_wordlist_provenance_distinguishes_empty_short_and_missing(tmp_path):
    g = Glottolog([dict(glottocode=x, name=x, level="language", category="Spoken L1 Language")
                   for x in ("a", "b", "c", "d")])
    source = tmp_path / "sources"
    source.mkdir()
    with (source / "asjp_languages.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ID", "Glottocode"])
        w.writerows([["z", "a"], ["a", "a"], ["empty", "b"], ["short", "c"]])
    with (source / "asjp_forms.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Language_ID", "Parameter_ID", "Form", "Loan"])
        for doc in ("z", "a"):
            w.writerows([[doc, c, "pata", "false"] for c in ASJP_CORE[:20]])
        w.writerow(["empty", ASJP_CORE[0], "mama", "true"])
        w.writerow(["short", ASJP_CORE[0], "pata", "false"])
    lists, provenance = load_wordlists_with_provenance(tmp_path, g)
    assert set(lists) == {"a"}
    assert provenance["a"] == dict(asjp_doculect_id="a", asjp_core_concepts=20, has_usable_wordlist=1)
    assert provenance["b"] == dict(asjp_doculect_id="empty", asjp_core_concepts=0, has_usable_wordlist=0)
    assert provenance["c"] == dict(asjp_doculect_id="short", asjp_core_concepts=1, has_usable_wordlist=0)
    assert provenance["d"] == dict(asjp_doculect_id="", asjp_core_concepts=0, has_usable_wordlist=0)


def test_sensitivity_and_provenance_match_released_evidence():
    g = Glottolog.load()
    rows = glottogenera.load_genera()
    alternative = glottogenera.genera_at(0.75)
    assert {r["glottocode"]: r["genus_id_delta_075"] for r in rows} == alternative
    assert len(set(alternative.values())) == 1587
    assert sum(int(r["has_usable_wordlist"]) for r in rows) == 5791
    for row in rows:
        assert int(row["has_usable_wordlist"]) == (int(row["asjp_core_concepts"]) >= 20)
        assert row["genus_name_delta_075"] == glottogenera.genus_name(row["genus_id_delta_075"])
    areas = defaultdict(set)
    for row in rows:
        areas[row["genus_id"]].update(filter(None, row["macroareas"].split(";")))
    above = set()
    for row in glottogenera.load_nodes():
        if float(row["crown_divergence"]) > 0.81:
            above.update(g.ancestors(row["node"]))
    summary = glottogenera.load_genera_summary()
    assert sum(int(r["has_above_threshold_subclade"]) for r in summary) == 27
    for row in summary:
        assert row["macroareas"] == ";".join(sorted(areas[row["genus_id"]]))
        assert bool(int(row["has_above_threshold_subclade"])) == (row["genus_id"] in above)


def test_cldf_and_web_preserve_new_metadata():
    import json
    root = Path(__file__).resolve().parents[1]
    with (root / "cldf/languages.csv").open() as f:
        cldf = {r["ID"]: r for r in csv.DictReader(f)}
    data = json.loads((root / "web/data/glottogenera.json").read_text())
    web = {r["id"]: r for r in data["languages"]}
    for r in glottogenera.load_genera():
        c, w = cldf[r["glottocode"]], web[r["glottocode"]]
        assert c["Genus_075_ID"] == w["genus_id_delta_075"] == r["genus_id_delta_075"]
        assert c["ASJP_Doculect_ID"] == (w["asjp_doculect_id"] or "") == r["asjp_doculect_id"]
        assert int(c["ASJP_Core_Concepts"]) == w["asjp_core_concepts"] == int(r["asjp_core_concepts"])
        assert (c["Has_Usable_Wordlist"] == "true") == w["has_usable_wordlist"] == bool(int(r["has_usable_wordlist"]))
    with (root / "cldf/codes.csv").open() as f:
        codes = {r["ID"]: r for r in csv.DictReader(f)}
    for r in glottogenera.load_genera_summary():
        c, w = codes[r["genus_id"]], data["genera"][r["genus_id"]]
        assert c["Macroareas"] == w["macroareas"] == r["macroareas"]
        assert (c["Has_Above_Threshold_Subclade"] == "true") == bool(int(w["has_above_threshold_subclade"])) == bool(int(r["has_above_threshold_subclade"]))
