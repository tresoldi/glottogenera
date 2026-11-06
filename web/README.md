# Glottogenera explorer

A static site, served at <https://glottogenera.tresoldi.org/>, for browsing the
genera, languages and families, mapping them, changing the threshold and
exporting CSV and GeoJSON. It needs no server code: everything is computed in
the browser from the files in `data/`.

## Data

`make web` (with the `web` extra installed and the WALS data fetched) runs
`scripts/build_web.py` and `scripts/dravidian_map.py`, which write:

- `data/glottogenera.json`: the in-scope languages with their Glottolog
  coordinates and WALS genera, every Glottolog node above them with its cut
  value c(u) (the values `glottogenera.genera_at()` recuts from), the released
  genera with their margins and stability, and the curated genus names;
- `data/cells.json`: one Voronoi cell per language, clipped to land (Natural
  Earth 1:50m, extended 15 km around every language for islets missing from
  it, and without Antarctica) and to 3,000 km around the language; languages
  at the same coordinates share a cell. The site cuts the cells to the
  distance set with its slider (25–3,000 km, 150 km by default);
- `data/world.json`: simplified country outlines for the basemap.
- `data/dravidian.png`: the map of the Dravidian genera at four thresholds on
  the About page (also Figure 5 of the data descriptor).

Rebuild them whenever the release changes, and commit them: the Pages workflow
(`.github/workflows/pages.yml`) only copies `web/`.

## How it works

- `js/core.js` recuts the genera at any δ exactly as `genera_at()` does, and
  gives each genus the range of thresholds over which it exists;
  `tests/test_web.py` checks both against the Python release.
- `js/areas.js` draws a genus as the merged Voronoi cells of its languages,
  each cut to the chosen distance from its language, and exports areas as
  GeoJSON or as CSV with WKT. Maps of groups that straddle the antimeridian
  are drawn east of it.
- `js/app.js` holds the pages. The state is in the URL hash
  (`#/genus/germ1287?d=0.750&c=family`), so every view can be linked.

Libraries are bundled in `vendor/` (licences in `vendor/LICENSES.txt`): no
CDN, tiles or other external requests.

## Check

```bash
make web
python -m pytest tests/test_web.py
python -m http.server 8811 --directory web &
pip install playwright && python -m playwright install chromium   # once
python web/tests/browser.py http://127.0.0.1:8811/
```

The browser check visits every page, moves the threshold, checks the mean
family ARI with WALS at the released δ (0.654), draws the areas,
downloads the exports and checks that pages fit a phone's width.

## Deployment

GitHub Pages, from `.github/workflows/pages.yml`, which publishes `web/`
without `tests/` and `README.md`, and copies the released files of `data/` to
`release/`, where the Downloads page links to them. The repository's Pages source must be set
to "GitHub Actions" and the custom domain (`glottogenera.tresoldi.org`, also
in `CNAME`) set in its Pages settings, with a DNS CNAME record to
`tresoldi.github.io`.
