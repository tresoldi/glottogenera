"""Unit tests for the Glottolog backbone."""

from glottogenera.glottolog import Glottolog


def make_glottolog():
    """A tiny synthetic classification: one family, one shallow group, an isolate."""
    rows = [
        # A family with two depth-3 subgroups.
        {"glottocode": "fami1234", "name": "Family", "family": "Family",
         "category": "Spoken L1 Language", "level": "family", "isolate": "False",
         "ancestors": ""},
        {"glottocode": "lang1111", "name": "L1", "family": "Family",
         "category": "Spoken L1 Language", "level": "language", "isolate": "False",
         "ancestors": "fami1234;bran1234;subg1111"},
        {"glottocode": "lang2222", "name": "L2", "family": "Family",
         "category": "Spoken L1 Language", "level": "language", "isolate": "False",
         "ancestors": "fami1234;bran1234;subg1111"},
        {"glottocode": "lang3333", "name": "L3", "family": "Family",
         "category": "Spoken L1 Language", "level": "language", "isolate": "False",
         "ancestors": "fami1234;bran1234;subg2222"},
        # A shallow family: languages attach directly below the root.
        {"glottocode": "shal1234", "name": "Shallow", "family": "Shallow",
         "category": "Spoken L1 Language", "level": "family", "isolate": "False",
         "ancestors": ""},
        {"glottocode": "lang4444", "name": "L4", "family": "Shallow",
         "category": "Spoken L1 Language", "level": "language", "isolate": "False",
         "ancestors": "shal1234"},
        # An isolate.
        {"glottocode": "isol1234", "name": "Iso", "family": "",
         "category": "Spoken L1 Language", "level": "language", "isolate": "True",
         "ancestors": ""},
        # Out of scope: a pidgin and a dialect.
        {"glottocode": "pidg1234", "name": "P", "family": "",
         "category": "Pidgin", "level": "language", "isolate": "False",
         "ancestors": ""},
        {"glottocode": "dial1234", "name": "D", "family": "Family",
         "category": "Spoken L1 Language", "level": "dialect", "isolate": "False",
         "ancestors": "fami1234;bran1234;subg1111;lang1111"},
    ]
    return Glottolog(rows)


def test_scope_excludes_non_genetic_and_non_language():
    gl = make_glottolog()
    in_scope = {r["glottocode"] for r in gl.in_scope_languages()}
    assert in_scope == {"lang1111", "lang2222", "lang3333", "lang4444", "isol1234"}


def test_lineage_and_family():
    gl = make_glottolog()
    assert gl.lineage("lang1111") == ["fami1234", "bran1234", "subg1111", "lang1111"]
    assert gl.family_gc("lang1111") == "fami1234"
    assert gl.lineage("isol1234") == ["isol1234"]
