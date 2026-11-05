"""
The Glottolog classification backbone: the vendored dump, indexed by
glottocode, with the lineage helpers the divergence stage walks.
"""

from __future__ import annotations

import csv
from typing import Dict, List

from .config import EXCLUDED_CATEGORIES, GLOTTOLOG_DUMP


class Glottolog:
    """The vendored Glottolog dump, indexed by glottocode."""

    def __init__(self, rows: List[dict]):
        self.rows = rows
        self.by_gc: Dict[str, dict] = {r["glottocode"]: r for r in rows}

    @classmethod
    def load(cls) -> "Glottolog":
        with GLOTTOLOG_DUMP.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh, delimiter="\t"))
        return cls(rows)

    def ancestors(self, gc: str) -> List[str]:
        """Glottocodes from family root down to the immediate parent (top-first)."""
        r = self.by_gc.get(gc)
        if not r or not r["ancestors"]:
            return []
        return r["ancestors"].split(";")

    def family_gc(self, gc: str) -> str:
        """Top-level family glottocode; isolates/top-level nodes return themselves."""
        anc = self.ancestors(gc)
        return anc[0] if anc else gc

    def family_name(self, gc: str) -> str:
        r = self.by_gc.get(gc, {})
        return r.get("family") or r.get("name") or ""

    def name(self, gc: str) -> str:
        return self.by_gc.get(gc, {}).get("name", gc)

    def in_scope_languages(self) -> List[dict]:
        """`level == language` rows outside the non-genetic categories."""
        return [
            r
            for r in self.rows
            if r["level"] == "language" and r["category"] not in EXCLUDED_CATEGORIES
        ]

    def lineage(self, gc: str) -> List[str]:
        """Full top-down path including the node itself (family..node)."""
        return self.ancestors(gc) + [gc]

    def tree(self):
        """The classification of the in-scope languages as a generic tree.Tree (cached)."""
        if getattr(self, "_tree", None) is None:
            from .tree import Tree

            parent = {}
            languages = [r["glottocode"] for r in self.in_scope_languages()]
            for gc in languages:
                lineage = self.lineage(gc)
                parent.setdefault(lineage[0], None)
                for up, down in zip(lineage, lineage[1:]):
                    parent[down] = up
            self._tree = Tree(parent, languages)
        return self._tree
