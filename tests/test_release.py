"""
Release-integrity tests: the shipped tables load, match the repository
artifacts and the CLDF dataset, and carry the released numbers.
"""

import csv
import json
from collections import Counter
from pathlib import Path

import glottogenera
from glottogenera.config import GLOTTOLOG_DUMP, PACKAGE_DATA
from glottogenera.glottolog import Glottolog

REPO = Path(__file__).resolve().parent.parent
REPO_DATA = REPO / "data"


def test_pinned_glottolog_dump_is_present():
    assert GLOTTOLOG_DUMP.name == "glottolog.v5.3-cldf-g072ca0d041.tsv"
    assert GLOTTOLOG_DUMP.is_file()


def test_packaged_tables_match_repository_artifacts():
    for name in ("genera.tsv", "genera_summary.tsv", "nodes.tsv", "genus_names.tsv"):
        packaged = (PACKAGE_DATA / name).read_bytes()
        repo = (REPO_DATA / name).read_bytes()
        assert packaged == repo, f"{name} out of sync; run `make bundle`"


def test_load_genera_and_genus_map():
    rows = glottogenera.load_genera()
    genus = glottogenera.genus_map()
    assert len(rows) == len(genus) == 7674
    assert genus["stan1293"] == genus["dutc1256"]  # English and Dutch: Germanic
    assert {"glottocode", "genus_id", "genus_name", "method"} <= set(rows[0])
    assert glottogenera.load_nodes()


def test_headline_numbers():
    rows = glottogenera.load_genera()
    params = json.loads((REPO_DATA / "params.json").read_text())
    assert params["sources"]["glottolog"]["version"] == "5.3"
    # The propositions of the definition (docs/definition.md) assume this.
    assert params["hierarchy"]["languages_below_another_language"] == 0
    dv = params["divergence"]
    assert dv["languages"] == len(rows) == 7674
    assert dv["n_genera"] == len({r["genus_id"] for r in rows})
    cal = dv["calibration"]
    # leaving out any one family barely moves delta
    assert all(abs(float(d) - dv["delta"]) <= 0.02 for d in cal["leave_one_family_out"]["deltas"])
    assert cal["indo_european"]["ari"] >= 0.95


def test_every_released_genus_is_a_complete_clade():
    rows = glottogenera.load_genera()
    gl = Glottolog.load()
    genus_of = {r["glottocode"]: r["genus_id"] for r in rows}
    members = Counter(genus_of.values())
    under = Counter(
        node for gc in genus_of for node in set(gl.lineage(gc)) if node in members
    )
    assert under == members


def test_full_coverage_of_in_scope_glottolog():
    genus = glottogenera.genus_map()
    in_scope = {r["glottocode"] for r in Glottolog.load().in_scope_languages()}
    assert set(genus) == in_scope


def test_summary_consistent_with_language_table():
    rows = glottogenera.load_genera()
    summary = glottogenera.load_genera_summary()
    sizes = Counter(r["genus_id"] for r in rows)
    assert len(summary) == len(sizes)
    for s in summary:
        assert int(s["n_languages"]) == sizes[s["genus_id"]]


def test_cut_values_respect_delta():
    rows = glottogenera.load_genera()
    delta = json.loads((REPO_DATA / "params.json").read_text())["divergence"]["delta"]
    gl = Glottolog.load()
    genus_of = {r["glottocode"]: r["genus_id"] for r in rows}
    for r in glottogenera.load_genera_summary():
        assert 0 <= float(r["stability"]) <= 1
        assert 0 <= float(r["stability_fixed_delta"]) <= 1
        if r["method"] == "divergence":
            assert float(r["cut_value"]) <= delta
            if r["upper_value"]:
                assert float(r["upper_value"]) > delta
        if r["method"] == "unmeasured-clade":
            assert r["cut_value"] == "" and float(r["upper_value"]) > delta
    for r in rows:
        assert r["method"] in {"divergence", "unmeasured-clade", "single-language", "unmeasured-family", "isolate"}
        if r["method"] == "unmeasured-family":
            assert genus_of[r["glottocode"]] == gl.family_gc(r["glottocode"])
        if r["method"] in ("single-language", "isolate"):
            assert genus_of[r["glottocode"]] == r["glottocode"]


def test_genus_ranges_are_exact():
    params = json.loads((REPO_DATA / "params.json").read_text())["divergence"]
    assert glottogenera.genera_at(params["delta"]) == glottogenera.genus_map()
    summary = [r for r in glottogenera.load_genera_summary() if r["method"] == "divergence"]
    low = {r["genus_id"] for r in summary if r["cut_value"]}
    ups = {float(r["upper_value"]) for r in summary if r["upper_value"]}
    # each genus exists from its cut value up to, not including, its upper value
    for d in sorted({float(r["cut_value"]) for r in summary if r["cut_value"]} | ups)[::40]:
        genus = glottogenera.genera_at(d)
        nodes = set(genus.values())
        for r in summary:
            if r["genus_id"] in low:
                inside = float(r["cut_value"]) <= d and (not r["upper_value"] or d < float(r["upper_value"]))
                assert (r["genus_id"] in nodes) == inside, (r["genus_id"], d)


def test_cldf_matches_release_tables():
    def rows(path):
        with path.open(encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    genus = {r["glottocode"]: (r["genus_id"], r["genus_name"], r["method"]) for r in glottogenera.load_genera()}
    values = rows(REPO / "cldf" / "values.csv")
    assert {v["Language_ID"]: (v["Code_ID"], v["Value"], v["Method"]) for v in values} == genus
    codes = rows(REPO / "cldf" / "codes.csv")
    assert {c["ID"]: int(c["Languages"]) for c in codes} == Counter(g for g, _, _ in genus.values())
    assert len(rows(REPO / "cldf" / "nodes.csv")) == len(glottogenera.load_nodes())
