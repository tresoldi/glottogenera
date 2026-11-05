"""
Build the data of the web explorer (web/data/) from the released tables.

Writes:
  web/data/glottogenera.json   languages, Glottolog nodes with their cut values,
                               the released genera, curated names and WALS genera
  web/data/cells.json          one Voronoi cell per language, clipped to land and
                               to RADIUS_KM around the language (the site cuts
                               them to the radius chosen there)
  web/data/world.json          country outlines for the basemap

Needs the fetched sources (`make fetch`) and the web extra
(`pip install -e ".[web]"`); the Natural Earth outlines are downloaded to
data/sources/naturalearth/ on first use.

Usage: python scripts/build_web.py
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import Voronoi
from shapely import make_valid, set_precision
from shapely.geometry import MultiPolygon, Polygon, box, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import glottogenera  # noqa: E402
from glottogenera import config  # noqa: E402
from glottogenera.divergence import ENVELOPE_RULE, envelope  # noqa: E402
from glottogenera.glottolog import Glottolog  # noqa: E402
from glottogenera.names import load_corrections  # noqa: E402
from glottogenera.wals import NON_GENEALOGICAL_WALS_GENUS  # noqa: E402

SOURCES = ROOT / "data" / "sources"
NATURAL_EARTH = SOURCES / "naturalearth"
NATURAL_EARTH_VERSION = "v5.1.2"
OUT = ROOT / "web" / "data"

RADIUS_KM = 3000  # cells are stored up to this far from their language; the site cuts them to its radius
DEFAULT_RADIUS_KM = 150  # the radius the site starts with
ISLAND_KM = 15  # land is extended by this much around every language, for islets missing from the outlines
PRECISION = 0.001  # coordinates are rounded to this many degrees (about 100 m)
SIMPLIFY = 0.01  # cells and countries are simplified to this tolerance in degrees
KM_PER_DEGREE = 111.32


def disc(lon: float, lat: float, km: float, n: int = 32) -> Polygon:
    """A circle of ``km`` around a point, as an ellipse in degrees."""
    dlat = km / KM_PER_DEGREE
    dlon = dlat / max(math.cos(math.radians(lat)), 0.05)
    return Polygon(
        [(lon + dlon * math.cos(2 * math.pi * k / n), lat + dlat * math.sin(2 * math.pi * k / n)) for k in range(n)]
    )


def rings(geom) -> list:
    """GeoJSON-style polygon coordinates (list of polygons of rings), rounded."""
    if geom.is_empty:
        return []
    polys = geom.geoms if isinstance(geom, MultiPolygon) else [geom] if isinstance(geom, Polygon) else [
        g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon)
    ]
    out = []
    for p in polys:
        out.append(
            [[[round(x, 3), round(y, 3)] for x, y in ring.coords] for ring in [p.exterior, *p.interiors]]
        )
    return out


def voronoi_cells(points: dict, land) -> dict:
    """
    {glottocode: cell}. Languages at the same coordinates share a cell. Points
    near the antimeridian are repeated 360 degrees away so that cells there are
    bounded by their true neighbours; cells are then cut back to [-180, 180].
    """
    sites = sorted({xy for xy in points.values()})
    index = {xy: i for i, xy in enumerate(sites)}
    coords = list(sites)
    coords += [(x + 360, y) for x, y in sites if x < -150]
    coords += [(x - 360, y) for x, y in sites if x > 150]
    # a frame of far points closes the outer cells
    coords += [(x, y) for x in range(-540, 541, 60) for y in (-180, 180)]
    coords += [(x, y) for x in (-540, 540) for y in range(-150, 151, 30)]
    vor = Voronoi(np.array(coords))
    world = box(-180, -90, 180, 90)
    cells = {}
    for xy, i in index.items():
        region = vor.regions[vor.point_region[i]]
        if not region or -1 in region:
            continue
        cell = Polygon(vor.vertices[region]).intersection(disc(*xy, RADIUS_KM))
        pieces = [cell]
        for shift in (-360, 360):  # the part of the disc beyond the antimeridian
            moved = Polygon([(x + shift, y) for x, y in cell.exterior.coords]) if not cell.is_empty else cell
            pieces.append(moved)
        cell = unary_union([p.intersection(world) for p in pieces if not p.is_empty])
        cell = make_valid(cell.intersection(land))
        cells[xy] = set_precision(cell.simplify(SIMPLIFY, preserve_topology=True), PRECISION)
    return {gc: cells.get(xy) for gc, xy in points.items()}


def fetch_natural_earth() -> None:
    """Download the pinned Natural Earth outlines once."""
    import urllib.request

    NATURAL_EARTH.mkdir(parents=True, exist_ok=True)
    for name in ("ne_50m_land", "ne_50m_admin_0_countries"):
        path = NATURAL_EARTH / f"{name}.geojson"
        if not path.exists():
            url = (f"https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
                   f"{NATURAL_EARTH_VERSION}/geojson/{name}.geojson")
            urllib.request.urlretrieve(url, path)


def load_land(points: dict):
    land = shape({"type": "GeometryCollection", "geometries": [
        f["geometry"] for f in json.loads((NATURAL_EARTH / "ne_50m_land.geojson").read_text())["features"]
    ]})
    land = land.intersection(box(-180, -60, 180, 90))  # no languages in Antarctica
    islets = unary_union([disc(x, y, ISLAND_KM, 16) for x, y in set(points.values())])
    return make_valid(unary_union([make_valid(land), islets]))


def world_outlines() -> dict:
    features = []
    for f in json.loads((NATURAL_EARTH / "ne_50m_admin_0_countries.geojson").read_text())["features"]:
        geom = set_precision(make_valid(shape(f["geometry"])).simplify(SIMPLIFY * 2, preserve_topology=True), PRECISION)
        if geom.is_empty:
            continue
        features.append({"type": "Feature", "properties": {"name": f["properties"]["NAME"]},
                         "geometry": {"type": "MultiPolygon", "coordinates": rings(geom)}})
    return {"type": "FeatureCollection", "features": features}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fetch_natural_earth()
    g = Glottolog.load()
    params = json.loads((ROOT / "data" / "params.json").read_text())
    delta = params["divergence"]["delta"]
    languages = glottogenera.load_genera()
    summary = {r["genus_id"]: r for r in glottogenera.load_genera_summary()}
    measured = {r["node"]: {"D": float(r["crown_divergence"]), "n_pairs": int(r["crown_pairs"])}
                for r in glottogenera.load_nodes()}
    env = envelope(g, measured, ENVELOPE_RULE)
    corrections = load_corrections()

    wals = {}
    with (SOURCES / "wals_languages.csv").open(encoding="utf-8") as fh:
        for w in csv.DictReader(fh):
            if w.get("Glottocode") and w.get("Genus"):
                wals.setdefault(w["Glottocode"], []).append(
                    {"id": w["ID"], "name": w["Name"], "genus": w["Genus"], "family": w["Family"]})

    # every Glottolog node above an in-scope language, with its cut value
    nodes = {}
    for r in languages:
        for a in g.ancestors(r["glottocode"]):
            if a not in nodes:
                anc = g.ancestors(a)
                nodes[a] = {
                    "name": g.name(a),
                    "parent": anc[-1] if anc else None,
                    "D": measured[a]["D"] if a in measured else None,
                    "pairs": measured[a]["n_pairs"] if a in measured else None,
                    "c": env.get(a),
                }
    langs, points = [], {}
    for r in languages:
        gc = r["glottocode"]
        row = g.by_gc[gc]
        anc = g.ancestors(gc)
        lat, lon = row["latitude"], row["longitude"]
        if lat and lon:
            points[gc] = (round(float(lon), 4), round(float(lat), 4))
        ws = wals.get(gc, [])
        langs.append({
            "id": gc,
            "name": r["name"],
            "parent": anc[-1] if anc else None,
            "lat": round(float(lat), 4) if lat else None,
            "lon": round(float(lon), 4) if lon else None,
            "iso": row["iso"] or None,
            "macroarea": row["macroareas"] or None,
            "countries": row["countries"] or None,
            "wals": ws[-1]["genus"] if ws else None,  # the row load_wals() keeps
            "wals_ids": [w["id"] for w in ws],
            "wals_genealogical": bool(ws) and ws[-1]["genus"] != NON_GENEALOGICAL_WALS_GENUS,
        })
    data = {
        "meta": {
            "delta": delta,
            "version": glottogenera.__version__,
            "glottolog": config.GLOTTOLOG_VERSION,
            "glottolog_doi": config.GLOTTOLOG_DOI,
            "asjp_commit": params["sources"]["asjp"]["commit"],
            "wals": config.WALS_REF,
            "resampling_range": params["divergence"]["calibration"]["family_resampling"]["delta_percentiles_5_50_95"],
            "radius_km": DEFAULT_RADIUS_KM,
            "max_radius_km": RADIUS_KM,
            "natural_earth": NATURAL_EARTH_VERSION,
        },
        "nodes": nodes,
        "languages": langs,
        "genera": {gid: {k: s[k] for k in ("method", "crown_divergence", "crown_pairs", "cut_value", "upper_value",
                                           "margin_below", "margin_above", "stability", "stability_fixed_delta")}
                   for gid, s in summary.items()},
        "names": {gid: {k: r[k] for k in ("name", "criterion", "confidence", "rationale", "sources")}
                  for gid, r in corrections.items()},
    }
    (OUT / "glottogenera.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    land = load_land(points)
    cells = voronoi_cells(points, land)
    (OUT / "cells.json").write_text(json.dumps({gc: rings(c) for gc, c in cells.items() if c is not None and not c.is_empty},
                                               separators=(",", ":")), encoding="utf-8")
    (OUT / "world.json").write_text(json.dumps(world_outlines(), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for f in ("glottogenera.json", "cells.json", "world.json"):
        print(f, f"{(OUT / f).stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
