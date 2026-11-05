"""
Curated genus names: the corrections file is well formed and current against
Glottolog, and the released tables carry its names.
"""

from collections import Counter

import pytest

import glottogenera
from glottogenera.glottolog import Glottolog
from glottogenera.names import check_corrections, load_corrections


@pytest.fixture(scope="module")
def glottolog():
    return Glottolog.load()


def test_corrections_are_current(glottolog):
    corrections = load_corrections()
    check_corrections(glottolog, corrections)
    for r in corrections.values():
        assert r["name"] != r["glottolog_name"]
        assert r["confidence"] in {"high", "medium", "low"}
        assert set(r["criterion"].split(";")) <= {"label", "wals", "literature", "misleading"}


def test_released_names_follow_corrections(glottolog):
    corrections = load_corrections()
    for r in glottogenera.load_genera_summary():
        gid = r["genus_id"]
        assert r["genus_glottolog_name"] == glottolog.name(gid)
        expected = corrections[gid]["name"] if gid in corrections else glottolog.name(gid)
        assert r["genus_name"] == expected == glottogenera.genus_name(gid)
    names = {r["genus_id"]: r["genus_name"] for r in glottogenera.load_genera_summary()}
    for r in glottogenera.load_genera():
        assert r["genus_name"] == names[r["genus_id"]]


def test_genus_names_are_unique():
    counts = Counter(r["genus_name"] for r in glottogenera.load_genera_summary())
    assert not [n for n, c in counts.items() if c > 1]


def test_corrections_rename_released_genera_or_other_nodes(glottolog):
    # A row may name a node that is a genus only at another threshold, but it
    # must at least be a clade (not a language) or a released genus.
    released = {r["genus_id"] for r in glottogenera.load_genera_summary()}
    for gid in load_corrections():
        assert gid in released or glottolog.by_gc[gid]["level"] == "family"
