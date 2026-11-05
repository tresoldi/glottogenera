"""
Map of the genera of the Dravidian languages at four thresholds, drawn as on
the web explorer: each genus is the merged Voronoi cells of its languages,
cut at 150 km from each language. Needs the explorer's data (``make web``)
and the web extra. Writes web/data/dravidian.png for the About page, or the
file given with --out; Figure 4 of the data descriptor calls ``figure()``.

Usage: python scripts/dravidian_map.py [--out PATH] [--dpi N]
"""

import argparse
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402
from matplotlib.patheffects import withStroke  # noqa: E402
from shapely.geometry import Polygon, box, shape  # noqa: E402
from shapely.ops import polylabel, unary_union  # noqa: E402

import glottogenera  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "data"
INK, MUTED = "#222222", "#8A8A8A"
FAMILY = "drav1251"
BOX = (72, 89, 7.5, 26)  # lon min, lon max, lat min, lat max; Brahui (Pakistan) lies outside
DELTAS = (0.55, 0.65, 0.73, 0.81)
RADIUS_KM = 150
KM_PER_DEGREE = 111.32
LAND, EDGE = "#F2F2F2", "#BBBBBB"
LABEL_MIN = 3  # languages in the frame for a genus to be labelled
# Twenty colours, so that every genus in a panel has its own.
PALETTE = ["#3A6EA5", "#C4622D", "#5B9A5B", "#8E6BB0", "#C9A227", "#4BA3A8", "#B5546F",
           "#7A7A3A", "#9DB8DA", "#E3A47A", "#A7CFA0", "#C8B3DE", "#E6CF7A", "#9FD0D3",
           "#E0A3B6", "#5E4B8B", "#8C6D4F", "#2F6B5E", "#D9785A", "#6B7FA8"]


def disc(lon, lat, km):
    """A circle of ``km`` around a point, as an ellipse in degrees (as on the site)."""
    dlat = km / KM_PER_DEGREE
    dlon = dlat / max(math.cos(math.radians(lat)), 0.05)
    return Polygon([(lon + dlon * math.cos(a), lat + dlat * math.sin(a))
                    for a in (2 * math.pi * k / 64 for k in range(64))])


def polygon(coords):
    return shape({"type": "MultiPolygon", "coordinates": coords}).buffer(0)


def draw(ax, geom, **kw):
    for poly in getattr(geom, "geoms", [geom]):
        if poly.is_empty:
            continue
        verts, codes = [], []
        for ring in [poly.exterior, *poly.interiors]:
            xy = list(ring.coords)
            verts += xy
            codes += [MPath.MOVETO] + [MPath.LINETO] * (len(xy) - 2) + [MPath.CLOSEPOLY]
        ax.add_patch(PathPatch(MPath(verts, codes), **kw))


def colours(cuts, members):
    """
    A colour for every genus node, unique within a panel and kept across
    panels. From the coarsest panel down, a new genus takes the colour of the
    genus it splits from when that is free in its panel (so the largest part
    of a split keeps it), and otherwise the first free colour.
    """
    colour = {}
    previous = None
    for d in sorted(DELTAS, reverse=True):
        genera = sorted(members[d], key=lambda g: -len(members[d][g]))
        taken = {colour[g] for g in genera if g in colour}
        for g in genera:
            if g in colour:
                continue
            parent = previous[members[d][g][0]["id"]] if previous else None
            wanted = [colour[parent]] if parent in colour else []
            colour[g] = next(c for c in wanted + PALETTE if c not in taken)
            taken.add(colour[g])
        previous = cuts[d]
    return colour


def place_label(ax, text, x, y, placed):
    """
    Writes ``text`` at (x, y), or moved up or down by a line or two when it
    would overlap a label already ``placed``; dropped when no place is free.
    """
    for shift in (0, -1, 1, -2, 2):
        t = ax.annotate(text, (x, y), xytext=(0, 9 * shift), textcoords="offset points", ha="center",
                        va="center", fontsize=6.5, color=INK, zorder=4,
                        path_effects=[withStroke(linewidth=2, foreground="white")])
        renderer = ax.figure.canvas.get_renderer()
        t.update_positions(renderer)
        extent = t.get_window_extent(renderer).expanded(1.05, 1.1)
        if not any(extent.overlaps(other) for other in placed):
            placed.append(extent)
            return
        t.remove()


def family_of(nodes, node):
    while nodes[node]["parent"]:
        node = nodes[node]["parent"]
    return node


def figure():
    """The four-panel map, as a matplotlib figure."""
    data = json.loads((WEB / "glottogenera.json").read_text())
    cells = json.loads((WEB / "cells.json").read_text())
    world = json.loads((WEB / "world.json").read_text())
    x0, x1, y0, y1 = BOX
    langs = [l for l in data["languages"] if l.get("parent") and l.get("lat") is not None
             and l["id"] in cells and family_of(data["nodes"], l["parent"]) == FAMILY]
    area = {l["id"]: polygon(cells[l["id"]]).intersection(disc(l["lon"], l["lat"], RADIUS_KM)) for l in langs}
    land = [polygon(f["geometry"]["coordinates"] if f["geometry"]["type"] == "MultiPolygon"
                    else [f["geometry"]["coordinates"]]) for f in world["features"]]
    inside = {l["id"] for l in langs if x0 <= l["lon"] <= x1 and y0 <= l["lat"] <= y1}

    cuts = {d: glottogenera.genera_at(d) for d in DELTAS}
    members = {d: {} for d in DELTAS}
    for d in DELTAS:
        for l in langs:
            members[d].setdefault(cuts[d][l["id"]], []).append(l)
    geoms = {g: unary_union([area[l["id"]] for l in ls]) for d in DELTAS for g, ls in members[d].items()}
    colour = colours(cuts, members)
    frame = box(x0 + 0.5, y0 + 0.5, x1 - 0.5, y1 - 0.5)

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 7.8))
    for ax, d in zip(axes.flat, DELTAS):
        ax.set_facecolor("white")
        ax.grid(False)
        for poly in land:
            draw(ax, poly, facecolor=LAND, edgecolor=EDGE, lw=0.3)
        for g in members[d]:
            draw(ax, geoms[g], facecolor=colour[g], edgecolor=INK, lw=0.4, alpha=0.85)
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect(1 / math.cos(math.radians((y0 + y1) / 2)))
        placed = []
        for g, ls in sorted(members[d].items(), key=lambda item: -len(item[1])):
            if sum(l["id"] in inside for l in ls) < LABEL_MIN:
                continue
            visible = geoms[g].intersection(frame)
            if visible.is_empty:
                continue
            p = polylabel(max(getattr(visible, "geoms", [visible]), key=lambda q: q.area), 0.01)
            place_label(ax, glottogenera.genus_name(g), p.x, p.y, placed)
        ax.scatter([l["lon"] for l in langs], [l["lat"] for l in langs], s=2, color=INK, lw=0, zorder=3)
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(True)
            s.set_color(MUTED)
        label = "δ* = " if d == data["meta"]["delta"] else "δ = "
        n = len(members[d])
        ax.set_title(f"{label}{d:g}: {n} genus" if n == 1 else f"{label}{d:g}: {n} genera", fontsize=9)
    fig.tight_layout()
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=WEB / "dravidian.png")
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()
    with plt.rc_context({"font.size": 9}):
        figure().savefig(args.out, dpi=args.dpi, bbox_inches="tight")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
