"""Unit tests for the divergence partition: distance, envelope, cut and bootstrap."""

import csv

import numpy as np

from glottogenera.divergence import (
    ASJP_CORE,
    K,
    MIN_CONCEPTS,
    Components,
    clean_asjp,
    divergence_genera,
    distance,
    envelope,
    load_wordlists,
    pair_components,
)
from glottogenera.glottolog import Glottolog
from glottogenera.pmi import Scorer, align

FORMS = ["pata", "kumi", "sole", "wari", "neto", "laku", "bira", "domu", "tesa",
         "gilo", "mapu", "rino", "suka", "fena", "holi", "jazu", "kevo", "lupa",
         "nizi", "qora"]
SCORER = Scorer()  # identity +1, mismatch -1: no training needed


def wordlist(forms, synonym=None):
    words = [[] for _ in range(K)]
    for i, form in enumerate(forms):
        words[i].append(form)
        if synonym:
            words[i].append(synonym)
    return words


def test_clean_asjp_strips_modifiers_keeps_digits():
    assert clean_asjp("na~ma ") == "nama"
    assert clean_asjp('k"ol$o*') == "kolo"
    assert clean_asjp("3ne5") == "3ne5"  # digits encode phonemes; kept


def test_alignment_scores_identity_highest():
    score, pairs = align("pata", "pata", SCORER)
    assert score == 4 and pairs == [("a", "a"), ("t", "t"), ("a", "a"), ("p", "p")]
    assert SCORER.distance("pata", "pata") == 0.0
    assert SCORER.distance("pata", "kumi") > SCORER.distance("pata", "pato")


def test_identical_wordlists_have_zero_distance():
    assert distance(wordlist(FORMS), wordlist(FORMS), SCORER) == 0.0


def test_distance_needs_enough_shared_concepts():
    assert distance(wordlist(FORMS[: MIN_CONCEPTS - 5]), wordlist(FORMS), SCORER) is None


def test_synonyms_are_averaged_not_minimized():
    # every concept gains an unrelated synonym: the same-concept mean is no
    # longer zero, as it would be if the closest synonym were taken
    assert distance(wordlist(FORMS), wordlist(FORMS, synonym="xxxxxxxx"), SCORER) > 0.2


def test_forms_on_the_wrong_concepts_score_above_one():
    rotated = FORMS[1:] + FORMS[:1]
    assert distance(wordlist(FORMS), wordlist(rotated), SCORER) > 1


def test_weights_resample_concepts():
    # the last ten concepts are rotated, the first ten agree
    a, b = wordlist(FORMS), wordlist(FORMS[:10] + FORMS[11:] + FORMS[10:11])
    comp = Components([pair_components(a, b, SCORER, "x")])
    assert np.isclose(comp.values()[0], distance(a, b, SCORER, "x")) and comp.values()[0] > 0
    weights = np.zeros(K)
    weights[:10] = 1.0  # resample only the concepts on which the lists agree
    assert comp.values(weights)[0] == 0.0


def make_family():
    """Family > (A > a1, a2), (B > b1, b2), with c directly under the root; an isolate."""
    def row(gc, level, ancestors, family="fam"):
        return {"glottocode": gc, "name": gc, "family": family, "level": level,
                "category": "Spoken L1 Language", "isolate": "False",
                "ancestors": ancestors}
    rows = [row("fami0001", "family", ""), row("aaaa0001", "family", "fami0001"),
            row("bbbb0001", "family", "fami0001"),
            row("lana0001", "language", "fami0001;aaaa0001"),
            row("lana0002", "language", "fami0001;aaaa0001"),
            row("lanb0001", "language", "fami0001;bbbb0001"),
            row("lanb0002", "language", "fami0001;bbbb0001"),
            row("lanc0001", "language", "fami0001"),
            row("isol0001", "language", "", family="")]
    return Glottolog(rows)


def test_one_doculect_per_language_and_no_loans(tmp_path):
    sources = tmp_path / "sources"
    sources.mkdir()
    with (sources / "asjp_languages.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ID", "Glottocode"])
        w.writerows([["DOC_A", "lana0001"], ["DOC_B", "lana0001"]])
    with (sources / "asjp_forms.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Language_ID", "Parameter_ID", "Form", "Loan"])
        for i, concept in enumerate(ASJP_CORE[:MIN_CONCEPTS]):
            w.writerow(["DOC_A", concept, FORMS[i], "false"])
        for i, concept in enumerate(ASJP_CORE[: MIN_CONCEPTS + 1]):
            w.writerow(["DOC_B", concept, "zz" + FORMS[i % 20], "true" if i == 0 else "false"])
    lists = load_wordlists(tmp_path, make_family())
    # DOC_B has 21 concepts but loses one loan: 20 against 20, so the tie goes to DOC_A
    chosen = lists["lana0001"]
    assert sum(1 for forms in chosen if forms) == MIN_CONCEPTS
    assert all(not f.startswith("zz") for forms in chosen for f in forms)


def test_envelope_rules():
    gl = make_family()
    crowns = {"fami0001": {"D": 0.9}, "aaaa0001": {"D": 0.5}, "bbbb0001": {"D": 0.95}}
    assert envelope(gl, crowns, "max")["fami0001"] == 0.95
    assert envelope(gl, crowns, "own")["fami0001"] == 0.9
    assert envelope(gl, {"aaaa0001": {"D": 0.5}}, "own")["fami0001"] == 0.5


def test_cut_and_method_labels():
    gl = make_family()
    env = envelope(gl, {"fami0001": {"D": 0.9}, "aaaa0001": {"D": 0.5}}, "own")
    genus, method = divergence_genera(gl, env, 0.8)
    assert genus["lana0001"] == genus["lana0002"] == "aaaa0001"
    assert method["lana0001"] == "divergence"
    assert genus["lanb0001"] == "bbbb0001" and method["lanb0001"] == "unmeasured-clade"
    assert genus["lanc0001"] == "lanc0001" and method["lanc0001"] == "single-language"
    assert genus["isol0001"] == "isol0001" and method["isol0001"] == "isolate"
    genus, _ = divergence_genera(gl, env, 0.99)
    assert {genus[x] for x in genus if x != "isol0001"} == {"fami0001"}


def test_unmeasured_family_is_one_genus():
    gl = make_family()
    genus, method = divergence_genera(gl, {}, 0.8)
    assert {genus[x] for x in genus if x != "isol0001"} == {"fami0001"}
    assert method["lana0001"] == "unmeasured-family"


def test_partitions_nest_as_delta_grows():
    gl = make_family()
    env = envelope(gl, {"fami0001": {"D": 0.9}, "aaaa0001": {"D": 0.5}, "bbbb0001": {"D": 0.95}}, "own")
    deltas = [0.4, 0.6, 0.92, 0.97]
    for low, high in zip(deltas, deltas[1:]):
        fine, _ = divergence_genera(gl, env, low)
        coarse, _ = divergence_genera(gl, env, high)
        for g in set(fine.values()):
            members = [gc for gc, x in fine.items() if x == g]
            assert len({coarse[gc] for gc in members}) == 1
