"""
Central configuration: vendored-data locations, pinned source references, and
scope constants shared across the pipeline stages.
"""

from __future__ import annotations

from pathlib import Path

# Vendored input shipped with the package: the Glottolog dump.
PACKAGE_DATA = Path(__file__).resolve().parent / "data"

# Glottolog 5.3 is the current released classification used by the project.
# The analysis consumes the corresponding CLDF release, whose annotated v5.3
# tag peels to GLOTTOLOG_CLDF_COMMIT. The curation repository's annotated v5.3
# tag object, the commit it peels to, and the DOI are recorded separately for
# citation and provenance.
GLOTTOLOG_VERSION = "5.3"
GLOTTOLOG_RELEASE_TAG_OBJECT = "0e0d80653e4087cd4ded6b5664ac5dc06426c08b"
GLOTTOLOG_RELEASE_COMMIT = "eb7d58221bea745a21cb7b96582118e990a295c2"
GLOTTOLOG_CLDF_COMMIT = "072ca0d0410039fb8b779be8fc165bac575d2cda"
GLOTTOLOG_DOI = "10.5281/zenodo.18840935"
GLOTTOLOG_DUMP = PACKAGE_DATA / (
    f"glottolog.v{GLOTTOLOG_VERSION}-cldf-g{GLOTTOLOG_CLDF_COMMIT[:10]}.tsv"
)

# Curated genus names that replace the Glottolog node name where that is not
# the name users know (applied after the genera are computed; see names.py).
GENUS_NAMES = PACKAGE_DATA / "genus_names.tsv"

# Pinned to a specific WALS CLDF release for reproducibility. Bump deliberately.
WALS_REF = "v2020.1"

# ASJP (lexibank/asjp) has no CLDF-layout release tag exposing cldf/*.csv, so we
# pin to a specific master commit for reproducibility. Bump deliberately.
ASJP_REF = "012795349540ba0dabfdcf2be16f2e77622f62d6"

# {cache filename: pinned URL} for everything `glottogenera fetch` downloads.
SOURCES_SPEC = {
    "wals_languages.csv": (
        f"https://raw.githubusercontent.com/cldf-datasets/wals/{WALS_REF}"
        "/cldf/languages.csv"
    ),
    # ASJP wordlists: languages.csv maps ASJP doculects to Glottocodes;
    # forms.csv (~50 MB) holds the ASJP-transcribed word forms per concept.
    "asjp_languages.csv": (
        f"https://raw.githubusercontent.com/lexibank/asjp/{ASJP_REF}/cldf/languages.csv"
    ),
    "asjp_forms.csv": (
        f"https://raw.githubusercontent.com/lexibank/asjp/{ASJP_REF}/cldf/forms.csv"
    ),
}

# Glottolog categories that are not genealogical language units.
EXCLUDED_CATEGORIES = {
    "Bookkeeping",
    "Artificial Language",
    "Sign Language",
    "Unattested",
    "Unclassifiable",
    "Speech Register",
    "Mixed Language",
    "Pidgin",
}


def sources_dir(data_dir: Path) -> Path:
    """Directory holding the fetched source caches under a data directory."""
    return data_dir / "sources"
