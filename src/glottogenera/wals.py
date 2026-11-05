"""WALS: Dryer genera, the yardstick for calibrating delta."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict


def load_wals(sources: Path) -> Dict[str, str]:
    """Return {glottocode: WALS genus} for WALS rows carrying both."""
    path = sources / "wals_languages.csv"
    out: Dict[str, str] = {}
    with path.open(encoding="utf-8") as fh:
        for w in csv.DictReader(fh):
            gc, genus = w.get("Glottocode"), w.get("Genus")
            if gc and genus:
                out[gc] = genus
    return out


# A WALS "genus" that is not genealogical; excluded from the calibration.
NON_GENEALOGICAL_WALS_GENUS = "Creoles and Pidgins"


def wals_eval_set(glottolog, wals: Dict[str, str]) -> Dict[str, str]:
    """WALS genera of the in-scope Glottolog languages."""
    inscope = {r["glottocode"] for r in glottolog.in_scope_languages()}
    return {gc: g for gc, g in wals.items() if gc in inscope and gc in glottolog.by_gc}
