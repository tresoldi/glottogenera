"""
The web explorer's data and its JavaScript recut agree with the release:
at any threshold, the browser gives the same genera as genera_at().
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import glottogenera

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
DELTAS = ["0.6", "0.7", "0.75", "0.81", "0.85", "0.9", "1.0"]

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


@pytest.fixture(scope="module")
def data():
    return json.loads((WEB / "data" / "glottogenera.json").read_text(encoding="utf-8"))


def test_web_data_matches_release(data):
    released = {r["glottocode"]: r["genus_id"] for r in glottogenera.load_genera()}
    assert {l["id"] for l in data["languages"]} == set(released)
    assert set(data["genera"]) == set(released.values())
    params = json.loads((ROOT / "data" / "params.json").read_text())
    assert data["meta"]["delta"] == params["divergence"]["delta"]


@needs_node
def test_javascript_recut_matches_genera_at():
    out = json.loads(subprocess.run(["node", str(WEB / "tests" / "recut.js"), *DELTAS],
                                    check=True, capture_output=True, text=True).stdout)
    for d in DELTAS:
        js = {lang: g for lang, (g, _) in out[d].items()}
        assert js == glottogenera.genera_at(float(d)), d
    released = {r["glottocode"]: (r["genus_id"], r["method"]) for r in glottogenera.load_genera()}
    delta = json.loads((ROOT / "data" / "params.json").read_text())["divergence"]["delta"]
    assert {lang: tuple(v) for lang, v in out[f"{delta:g}"].items()} == released


@needs_node
def test_javascript_ranges_match_summary():
    out = json.loads(subprocess.run(["node", str(WEB / "tests" / "ranges.js")],
                                    check=True, capture_output=True, text=True).stdout)
    for r in glottogenera.load_genera_summary():
        lo, hi = out[r["genus_id"]]
        if r["method"] == "divergence":
            assert lo == pytest.approx(float(r["cut_value"]))
        assert (hi is None) == (r["upper_value"] == "")
        if hi is not None:
            assert hi == pytest.approx(float(r["upper_value"]))
