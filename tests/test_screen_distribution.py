"""Distribution exports omit the source without established permission."""
import csv
import gzip
import importlib.util
import hashlib
import json
import pickle
from collections import Counter
from pathlib import Path


def test_screen_export_requires_explicit_private_option_for_kogan(tmp_path):
    path = Path(__file__).parents[1] / "research/divergence/export_screen.py"
    spec = importlib.util.spec_from_file_location("screen_export", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "source.pkl"
    heldout = tmp_path / "heldout.pkl"
    source.write_bytes(pickle.dumps({"values": {}, "cognates": [
        ("kogansemitic", "a", "b", 0.3), ("grollemundbantu", "c", "d", 0.4)], "clock": {}}))
    heldout.write_bytes(pickle.dumps({"values": {}}))
    for private in (False, True):
        out = tmp_path / str(private)
        module.main(source, heldout, out, include_undistributed=private)
        for name in ("screen_pairs.csv.gz", "screen_pairs_all.csv.gz"):
            with gzip.open(out / name, "rt") as f:
                datasets = {r["dataset_or_node"] for r in csv.DictReader(f)}
            assert "grollemundbantu" in datasets
            assert ("kogansemitic" in datasets) == private


def test_distributed_sources_and_exports_have_explicit_exceptions():
    root = Path(__file__).parents[1] / "research/divergence"
    assert not (root / "cognates/kogansemitic.csv").exists()
    assert (root / "cognates/LICENSE-grollemundbantu").is_file()
    assert (root / "results/LICENSE-screen-pairs").is_file()
    for name in ("screen_pairs.csv.gz", "screen_pairs_all.csv.gz"):
        with gzip.open(root / "results" / name, "rt") as f:
            assert all(r["dataset_or_node"] != "kogansemitic" for r in csv.DictReader(f))
    provenance = json.loads((root / "results/screen_provenance.json").read_text())
    meta = json.loads((root / "results/sources_meta.json").read_text())
    assert sum(provenance["historical"]["pairs_by_dataset"].values()) == meta["cognate_pairs"]
    path = root / "results/screen_pairs.csv.gz"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == provenance["redistributed"]["export_sha256"]
    with gzip.open(path, "rt") as f:
        counts = Counter(r["dataset_or_node"] for r in csv.DictReader(f) if r["evidence"] == "cognates")
    assert counts == provenance["redistributed"]["pairs_by_dataset"]
    assert provenance["historical"]["pairs_by_dataset"]["kogansemitic"] == 66
