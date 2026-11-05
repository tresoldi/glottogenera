#!/usr/bin/env python3
"""Regenerate the vendored Glottolog classification dump from pinned CLDF.

The source CSVs are verified before the compact, analysis-oriented TSV is
written. Run this script only when deliberately bumping the constants and
checksums below; ordinary reproductions consume the already vendored TSV.
"""

from __future__ import annotations

import csv
import hashlib
import io
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from glottogenera.config import (  # noqa: E402
    GLOTTOLOG_CLDF_COMMIT,
    GLOTTOLOG_DUMP,
)
from glottogenera.resources import (  # noqa: E402
    DEFAULT_MAX_MEMORY_MB,
    configure_process,
)

BASE_URL = (
    "https://raw.githubusercontent.com/glottolog/glottolog-cldf/"
    f"{GLOTTOLOG_CLDF_COMMIT}/cldf"
)
SOURCE_SHA256 = {
    "languages.csv": "1a50a393bc81568b656f9522be18aa4f80f38e94309ba6c863d583234adfbb89",
    "values.csv": "a8601cb04ccc6a310538217f772d2461853aa0ea49e3bfe24c7396570fc4ea25",
}
FIELDS = [
    "glottocode",
    "name",
    "iso",
    "closest_iso",
    "family",
    "category",
    "level",
    "isolate",
    "macroareas",
    "countries",
    "latitude",
    "longitude",
    "ancestors",
    "children",
    "names",
    "timespan",
]


def fetch_csv(name: str) -> str:
    """Fetch and checksum one pinned CLDF CSV."""
    url = f"{BASE_URL}/{name}"
    print(f"Fetching {url}")
    with urllib.request.urlopen(  # noqa: S310 - pinned HTTPS URL
        url, timeout=60
    ) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != SOURCE_SHA256[name]:
        raise RuntimeError(
            f"checksum mismatch for {name}: expected {SOURCE_SHA256[name]}, got {digest}"
        )
    return payload.decode("utf-8-sig")


def main() -> int:
    configure_process(DEFAULT_MAX_MEMORY_MB)
    languages = list(csv.DictReader(io.StringIO(fetch_csv("languages.csv"))))
    values = csv.DictReader(io.StringIO(fetch_csv("values.csv")))

    category: dict[str, str] = {}
    ancestors: dict[str, str] = {}
    for row in values:
        if row["Parameter_ID"] == "category":
            category[row["Language_ID"]] = row["Value"].replace("_", " ")
        elif row["Parameter_ID"] == "classification":
            ancestors[row["Language_ID"]] = row["Value"].replace("/", ";")

    names = {row["ID"]: row["Name"] for row in languages}
    children: dict[str, list[str]] = defaultdict(list)
    for gc, path in ancestors.items():
        if path:
            children[path.rsplit(";", 1)[-1]].append(gc)

    GLOTTOLOG_DUMP.parent.mkdir(parents=True, exist_ok=True)
    for stale in GLOTTOLOG_DUMP.parent.glob("glottolog.*.tsv"):
        if stale != GLOTTOLOG_DUMP:
            stale.unlink()
    with GLOTTOLOG_DUMP.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t")
        writer.writeheader()
        for row in sorted(languages, key=lambda item: item["ID"]):
            gc = row["ID"]
            family_id = row["Family_ID"]
            first = row["First_Year_Of_Documentation"]
            last = row["Last_Year_Of_Documentation"]
            writer.writerow(
                {
                    "glottocode": gc,
                    "name": row["Name"],
                    "iso": row["ISO639P3code"],
                    "closest_iso": row["Closest_ISO369P3code"],
                    "family": names.get(family_id, ""),
                    "category": category[gc],
                    "level": row["Level"],
                    "isolate": (
                        "True" if row["Is_Isolate"].lower() == "true" else "False"
                    ),
                    "macroareas": row["Macroarea"],
                    "countries": row["Countries"],
                    "latitude": row["Latitude"],
                    "longitude": row["Longitude"],
                    "ancestors": ancestors.get(gc, ""),
                    "children": ";".join(sorted(children.get(gc, []))),
                    "names": "",
                    "timespan": f"({first}, {last})" if first or last else "",
                }
            )
    print(f"Wrote {GLOTTOLOG_DUMP} ({len(languages)} languoids)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
