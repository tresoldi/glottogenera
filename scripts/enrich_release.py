"""Add release provenance and sensitivity columns without recomputing distances."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from glottogenera.release_metadata import refresh_release  # noqa: E402

if __name__ == "__main__":
    languages, genera = refresh_release(ROOT / "data")
    print(f"Updated metadata for {len(languages)} languages and {len(genera)} genera")
