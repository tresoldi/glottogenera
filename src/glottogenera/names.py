"""
Curated genus names. A genus takes the name of its Glottolog node unless
genus_names.tsv gives another: an established or WALS name, or the node name
without Glottolog's bookkeeping labels. Rows are keyed by the node's
glottocode, so they apply to the genera at any threshold.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Optional

from .config import GENUS_NAMES

COLUMNS = ["genus_id", "glottolog_name", "name", "criterion", "confidence", "rationale", "sources"]


def load_corrections(path: Optional[Path] = None) -> Dict[str, dict]:
    """{genus_id: row} from genus_names.tsv."""
    with (path or GENUS_NAMES).open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    if rows and list(rows[0]) != COLUMNS:
        raise ValueError(f"genus_names.tsv must have the columns {COLUMNS}")
    out = {}
    for r in rows:
        if r["genus_id"] in out:
            raise ValueError(f"genus_names.tsv lists {r['genus_id']} twice")
        out[r["genus_id"]] = r
    return out


def check_corrections(glottolog, corrections: Dict[str, dict]) -> None:
    """Every row names an existing node under its current Glottolog name."""
    for gid, r in corrections.items():
        if gid not in glottolog.by_gc:
            raise ValueError(f"genus_names.tsv: {gid} is not a Glottolog node")
        if glottolog.name(gid) != r["glottolog_name"]:
            raise ValueError(
                f"genus_names.tsv: {gid} is now {glottolog.name(gid)!r} in Glottolog, "
                f"not {r['glottolog_name']!r}; review the row"
            )
        if not r["name"].strip():
            raise ValueError(f"genus_names.tsv: {gid} has no name")


def genus_namer(glottolog, path: Optional[Path] = None):
    """A function from genus_id to the genus name, curated or Glottolog's."""
    corrections = load_corrections(path)
    check_corrections(glottolog, corrections)
    return lambda gid: corrections[gid]["name"] if gid in corrections else glottolog.name(gid)
