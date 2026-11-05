/*
 * Areas of genera: the merged Voronoi cells of their languages, as GeoJSON
 * MultiPolygon coordinates, and their export as GeoJSON or as CSV with WKT.
 * Cells are stored up to a maximum radius around their language and cut here
 * to the radius chosen. A genus's membership is fixed by its node, so areas
 * are cached by radius and genus.
 */
(function (root) {
  "use strict";

  const KM_PER_DEGREE = 111.32;
  const cache = new Map();
  const cellCache = new Map();

  // A circle of ``km`` around a point, as an ellipse in degrees.
  function disc(lon, lat, km, shift) {
    const n = 32;
    const dlat = km / KM_PER_DEGREE;
    const dlon = dlat / Math.max(Math.cos((lat * Math.PI) / 180), 0.05);
    const ring = [];
    for (let k = 0; k < n; k++) {
      const a = (2 * Math.PI * k) / n;
      ring.push([lon + shift + dlon * Math.cos(a), lat + dlat * Math.sin(a)]);
    }
    ring.push(ring[0]);
    return { ring: [ring], dlon };
  }

  // A language's cell within ``km`` of it. Cells near the antimeridian are
  // split there, so the circle is repeated 360 degrees away.
  function cell(lang, cells, km, maxKm) {
    const stored = cells[lang.id];
    if (!stored || km >= maxKm) return stored;
    const key = km + "|" + lang.id;
    if (cellCache.has(key)) return cellCache.get(key);
    const d = disc(lang.lon, lang.lat, km, 0);
    const discs = [d.ring];
    if (lang.lon + d.dlon > 180) discs.push(disc(lang.lon, lang.lat, km, -360).ring);
    if (lang.lon - d.dlon < -180) discs.push(disc(lang.lon, lang.lat, km, 360).ring);
    const out = snap(root.polygonClipping.intersection(stored, discs));
    cellCache.set(key, out);
    return out;
  }

  // Coordinates rounded to 0.001 degrees, as the stored cells are; repeated
  // vertices and rings left with fewer than four points are dropped.
  function snap(geom) {
    const r = (x) => Math.round(x * 1000) / 1000;
    return geom.map((poly) => poly.map((ring) => {
      const out = [];
      ring.forEach(([x, y]) => {
        const p = [r(x), r(y)];
        const last = out[out.length - 1];
        if (!last || last[0] !== p[0] || last[1] !== p[1]) out.push(p);
      });
      return out;
    }).filter((ring) => ring.length >= 4)).filter((poly) => poly.length);
  }

  // Merges cells; the cells of different languages do not overlap, so if
  // the merge fails on degenerate geometry they are kept as separate parts.
  function merge(polys) {
    try {
      return root.polygonClipping.union.apply(null, polys);
    } catch (e) {
      return [].concat.apply([], polys);
    }
  }

  /*
   * The area of a genus within ``opts.radius`` km of its languages.
   * ``opts``: {cells, byId (glottocode to language), radius, maxRadius}.
   */
  function area(id, members, opts) {
    const key = opts.radius + "|" + id;
    if (cache.has(key)) return cache.get(key);
    const polys = members.map((m) => cell(opts.byId[m], opts.cells, opts.radius, opts.maxRadius))
      .filter((c) => c && c.length);
    const geom = polys.length ? merge(polys) : [];
    cache.set(key, geom);
    return geom;
  }

  function wkt(geom) {
    if (!geom.length) return "MULTIPOLYGON EMPTY";
    const ring = (r) => "(" + r.map(([x, y]) => x + " " + y).join(", ") + ")";
    return "MULTIPOLYGON (" + geom.map((poly) => "(" + poly.map(ring).join(", ") + ")").join(", ") + ")";
  }

  function geojson(features) {
    return {
      type: "FeatureCollection",
      features: features.map((f) => ({
        type: "Feature",
        properties: f.properties,
        geometry: { type: "MultiPolygon", coordinates: f.geometry },
      })),
    };
  }

  const api = { area, wkt, geojson };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Areas = api;
})(this);
