"""The parsing of the deposited cognate judgements used by the distance screen."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research" / "divergence"))
from cognacy import memberships  # noqa: E402


def test_several_sets():
    assert memberships("abvd2026_tooth-1;abvd2026_tooth-35") == {"abvd2026_tooth-1", "abvd2026_tooth-35"}


def test_placeholder_is_no_judgement():
    # two forms coded 0 must not count as cognate
    assert memberships("peirosaustroasiatic_0") == set()
    assert memberships("peirosaustroasiatic_0;peirosaustroasiatic_12") == {"peirosaustroasiatic_12"}
    assert memberships("peirosaustroasiatic_10") == {"peirosaustroasiatic_10"}
    # a class label ending in 0 is a real set
    assert memberships("dunnaslian_8_blood_0") == {"dunnaslian_8_blood_0"}


def test_empty():
    assert memberships("") == set() and memberships(" ; ") == set()
