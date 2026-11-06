"""
glottogenera — genera defined by a divergence threshold on a language tree.

On a rooted language tree, a genus is the largest clade whose divergence does
not exceed a threshold delta. ``glottogenera.tree`` applies the rule to any
tree (expert or estimated: Newick, a parent table, UPGMA or neighbour-joining)
and any divergence (a distance between languages, or node values such as
ages). The released genera are one instance: the Glottolog 5.3 tree, crown
divergence from PMI alignment over the 40-concept ASJP wordlists, and delta
calibrated on the genera of WALS across language families. Every in-scope
Glottolog 5.3 language has one. See the repository README and docs/methods.md.

The released tables ship with the package:

    >>> import glottogenera
    >>> rows = glottogenera.load_genera()        # list of per-language dicts
    >>> genus = glottogenera.genus_map()         # {glottocode: genus_id}
    >>> other = glottogenera.genera_at(0.75)     # the genera at another threshold
    >>> glottogenera.genus_name(other["stan1293"])  # a genus's name, curated or Glottolog's
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional

from .config import PACKAGE_DATA

__version__ = "1.2.0"

__all__ = [
    "load_genera",
    "load_genera_summary",
    "load_nodes",
    "genus_map",
    "genera_at",
    "genus_name",
    "__version__",
]


def _read_tsv(path: Path) -> List[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def load_genera(path: Optional[Path] = None) -> List[dict]:
    """
    The per-language genus table: one dict per in-scope Glottolog language with
    ``glottocode``, ``name``, ``family``, ``genus_id``, ``genus_name``,
    ``genus_glottolog_name`` and ``method`` (see data/README.md). Reads the packaged release copy unless
    ``path`` points at another genera.tsv.
    """
    return _read_tsv(path or PACKAGE_DATA / "genera.tsv")


def load_genera_summary(path: Optional[Path] = None) -> List[dict]:
    """The per-genus table, with crown divergence, margins and stability."""
    return _read_tsv(path or PACKAGE_DATA / "genera_summary.tsv")


def load_nodes(path: Optional[Path] = None) -> List[dict]:
    """The crown divergence of every measured Glottolog node."""
    return _read_tsv(path or PACKAGE_DATA / "nodes.tsv")


def genus_map(path: Optional[Path] = None) -> Dict[str, str]:
    """{glottocode: genus_id} over every in-scope language."""
    return {r["glottocode"]: r["genus_id"] for r in load_genera(path)}


def genera_at(delta: float, path: Optional[Path] = None) -> Dict[str, str]:
    """
    {glottocode: genus_id} at another threshold ``delta``, recut from the
    released crown divergences (nodes.tsv) without recomputing any distance.
    ``genera_at(released delta)`` reproduces ``genus_map()``.
    """
    from .divergence import ENVELOPE_RULE, divergence_genera, envelope
    from .glottolog import Glottolog

    glottolog = Glottolog.load()
    measured = {r["node"]: {"D": float(r["crown_divergence"])} for r in load_nodes(path)}
    genus, _ = divergence_genera(glottolog, envelope(glottolog, measured, ENVELOPE_RULE), delta)
    return genus


def genus_name(genus_id: str) -> str:
    """
    The name of a genus: the curated name in genus_names.tsv when there is one,
    otherwise its Glottolog node's name. Works for the genera at any threshold.
    """
    global _namer
    if _namer is None:
        from .glottolog import Glottolog
        from .names import genus_namer

        _namer = genus_namer(Glottolog.load())
    return _namer(genus_id)


_namer = None
