/*
 * Glottogenera explorer: pages for genera, languages and families, maps with
 * areas, a threshold that recuts the genera in the browser, the comparison
 * with WALS, and CSV/GeoJSON export. State lives in the URL hash:
 * #/<page>/<id>?d=<delta>&a=<areas on or off>&r=<area radius, km>&c=<colour by>.
 */
(function () {
  "use strict";

  const S = {
    data: null, ix: null, cells: null, world: null,
    delta: null, area: "voronoi", radius: null, colour: "genus",
    cuts: new Map(), maps: [],
  };
  const PAGE = 200; // table rows shown before "show more"
  const GLOTTOLOG = "https://glottolog.org/resource/languoid/id/";
  const REPO = "https://github.com/tresoldi/glottogenera";
  const RELEASE = "release/"; // the released files, copied into the site by the Pages workflow
  const METHODS = {
    divergence: "cut by divergence",
    "unmeasured-clade": "unmeasured clade",
    "single-language": "single language",
    "unmeasured-family": "unmeasured family",
    isolate: "isolate",
  };
  const AREAS = { none: "none", voronoi: "Voronoi cells" };
  // distances (km) offered for genus areas, finer where differences show most
  const RADII = [25, 50, 75, 100, 150, 200, 250, 300, 400, 500, 750, 1000, 1500, 2000, 3000];
  const WORLD = [15, 20];

  // ---------- utilities ----------
  const $ = (sel, el) => (el || document).querySelector(sel);
  const esc = (s) => String(s === null || s === undefined ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const fmt = (x, d) => (x === null || x === undefined || x === "" || !isFinite(x) ? "–" : Number(x).toFixed(d === undefined ? 3 : d));
  const int = (x) => Number(x).toLocaleString("en-US");
  const isReleased = () => Math.abs(S.delta - S.data.meta.delta) < 1e-9;

  function hue(id) {
    let h = 2166136261;
    for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619);
    return (h >>> 0) % 360;
  }
  function colour(id) {
    const h = hue(id);
    return `hsl(${h}, ${55 + (h % 3) * 10}%, ${42 + (h % 4) * 5}%)`;
  }
  // "; "-separated references, with URLs as links
  const sources = (s) => s.split(";").map((x) => x.trim()).filter(Boolean).map((x) =>
    /^https?:\/\/\S+$/.test(x) ? `<a href="${esc(x)}">${esc(x.replace(/^https?:\/\//, ""))}</a>` : esc(x)).join("; ");
  const swatch = (id) => `<span class="swatch" style="background:${colour(id)}"></span>`;

  function download(name, text, type) {
    const blob = new Blob([text], { type: type || "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }
  const dtag = () => "delta" + S.delta.toFixed(3);

  // ---------- state and routing ----------
  function parse() {
    const h = location.hash.replace(/^#\/?/, "");
    const [path, query] = h.split("?");
    const params = new URLSearchParams(query || "");
    const parts = (path || "").split("/").filter(Boolean).map(decodeURIComponent);
    return { page: parts[0] || "home", arg: parts[1], params };
  }

  function query(extra) {
    const p = new URLSearchParams();
    if (!isReleased()) p.set("d", S.delta.toFixed(3));
    if (S.area !== "voronoi") p.set("a", S.area);
    if (S.radius !== S.data.meta.radius_km) p.set("r", String(S.radius));
    if (S.colour !== "genus") p.set("c", S.colour);
    Object.entries(extra || {}).forEach(([k, v]) => p.set(k, v));
    const s = p.toString();
    return s ? "?" + s : "";
  }
  const link = (path) => "#/" + path + query();

  function readParams(params) {
    const d = parseFloat(params.get("d"));
    S.delta = isFinite(d) ? Math.min(1, Math.max(0.5, d)) : S.data.meta.delta;
    S.area = AREAS[params.get("a")] ? params.get("a") : "voronoi";
    const r = parseInt(params.get("r"), 10);
    S.radius = isFinite(r) ? nearestRadius(r) : S.data.meta.radius_km;
    S.colour = ["genus", "family", "wals"].includes(params.get("c")) ? params.get("c") : "genus";
  }

  const radii = () => RADII.filter((x) => x <= S.data.meta.max_radius_km);
  function nearestRadius(r) {
    return radii().reduce((best, x) => (Math.abs(x - r) < Math.abs(best - r) ? x : best), radii()[0]);
  }

  function current() {
    const key = S.delta.toFixed(4);
    if (!S.cuts.has(key)) {
      const cut = Core.recut(S.ix, S.delta);
      S.cuts.set(key, { cut, gens: Core.genera(cut) });
    }
    return S.cuts.get(key);
  }

  function setUrl(replace) {
    const r = parse();
    const path = [r.page === "home" ? "" : r.page, r.arg].filter(Boolean).map(encodeURIComponent).join("/");
    const keep = {};
    ["q", "f", "m"].forEach((k) => r.params.get(k) && (keep[k] = r.params.get(k)));
    const url = "#/" + path + query(keep);
    if (replace) history.replaceState(null, "", url);
    else location.hash = url;
  }

  // ---------- data helpers ----------
  function familyOf(langId) { return Core.family(S.ix, langId); }
  function familyName(fid) { return Core.name(S.ix, fid); }
  function genusRow(g) {
    const first = g.members[0];
    const fid = familyOf(first);
    const [lo, hi] = Core.range(S.ix, g.id, g.method);
    const node = S.ix.nodes[g.id];
    const released = isReleased() ? S.data.genera[g.id] : null;
    return {
      genus_id: g.id,
      genus_name: Core.name(S.ix, g.id),
      genus_glottolog_name: node ? node.name : S.ix.byId[g.id].name,
      family_id: fid,
      family: familyName(fid),
      n_languages: g.members.length,
      method: g.method,
      cut_value: g.method === "divergence" ? Core.cutValue(S.ix, g.id) : "",
      crown_divergence: node && node.D !== null ? node.D : "",
      from_delta: isFinite(lo) ? lo : "",
      to_delta: isFinite(hi) ? hi : "",
      stability: released ? released.stability : "",
      delta: S.delta.toFixed(3),
    };
  }
  function languageRow(l, cut) {
    const [gid, method] = cut[l.id];
    const fid = familyOf(l.id);
    return {
      glottocode: l.id, name: l.name, iso639_3: l.iso || "", family_id: fid, family: familyName(fid),
      genus_id: gid, genus_name: Core.name(S.ix, gid),
      genus_glottolog_name: S.ix.nodes[gid] ? S.ix.nodes[gid].name : S.ix.byId[gid].name,
      method, latitude: l.lat === null ? "" : l.lat, longitude: l.lon === null ? "" : l.lon,
      macroarea: l.macroarea || "", wals_genus: l.wals || "", delta: S.delta.toFixed(3),
    };
  }
  const LANG_COLUMNS = ["glottocode", "name", "iso639_3", "family_id", "family", "genus_id", "genus_name",
    "genus_glottolog_name", "method", "latitude", "longitude", "macroarea", "wals_genus", "delta"];
  const GENUS_COLUMNS = ["genus_id", "genus_name", "genus_glottolog_name", "family_id", "family", "n_languages",
    "method", "cut_value", "crown_divergence", "from_delta", "to_delta", "stability", "delta"];

  // WALS families used in the calibration: genealogical WALS genera of in-scope
  // languages, families with at least two such languages and two WALS genera.
  function walsFamilies() {
    const by = {};
    S.data.languages.forEach((l) => {
      if (l.wals && l.wals_genealogical) (by[familyOf(l.id)] = by[familyOf(l.id)] || []).push(l);
    });
    return Object.entries(by)
      .filter(([, ls]) => ls.length >= 2 && new Set(ls.map((l) => l.wals)).size >= 2)
      .map(([fid, ls]) => ({ fid, langs: ls }));
  }
  function walsAgreement(cut) {
    return walsFamilies().map(({ fid, langs }) => ({
      fid, n: langs.length, wals_genera: new Set(langs.map((l) => l.wals)).size,
      genera: new Set(langs.map((l) => cut[l.id][0])).size,
      ari: Core.ari(langs.map((l) => l.wals), langs.map((l) => cut[l.id][0])),
    }));
  }

  // ---------- tables ----------
  /*
   * A sortable table with a search box and filters. ``columns``: [{key, label,
   * num, html(row)}]; ``filters``: [{key, label, options:[[value, label]], test(row, v)}].
   */
  function table(el, opts) {
    const r = parse();
    let sortKey = opts.sort || opts.columns[0].key, asc = opts.asc !== false, shown = PAGE;
    const synced = opts.url !== false; // only one table per page keeps its search in the URL
    const state = { q: synced ? r.params.get("q") || "" : "", f: {} };
    (opts.filters || []).forEach((f) => (state.f[f.key] = synced ? r.params.get(f.key) || "" : ""));
    el.innerHTML = `<div class="controls">
        <input type="search" placeholder="${esc(opts.placeholder || "Search")}" value="${esc(state.q)}" aria-label="Search">
        ${(opts.filters || []).map((f) => `<select data-f="${f.key}" aria-label="${esc(f.label)}">
          <option value="">${esc(f.label)}: all</option>
          ${f.options.map(([v, l]) => `<option value="${esc(v)}"${state.f[f.key] === v ? " selected" : ""}>${esc(l)}</option>`).join("")}
        </select>`).join("")}
        <span class="count muted"></span>
        <button type="button" class="csv">Export CSV</button>
      </div>
      <div class="tablewrap"><table><thead><tr>${opts.columns.map((c) =>
        `<th class="sortable${c.num ? " num" : ""}" data-k="${c.key}">${esc(c.label)}</th>`).join("")}</tr></thead><tbody></tbody></table></div>
      <div class="more"></div>`;
    const tbody = $("tbody", el);
    function rows() {
      const q = state.q.trim().toLowerCase();
      let out = opts.rows.filter((row) => !q || opts.search(row).toLowerCase().includes(q));
      (opts.filters || []).forEach((f) => { if (state.f[f.key]) out = out.filter((row) => f.test(row, state.f[f.key])); });
      out.sort((a, b) => {
        const x = a[sortKey], y = b[sortKey];
        const nx = x === "" || x === null || x === undefined, ny = y === "" || y === null || y === undefined;
        if (nx || ny) return nx - ny;
        const c = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y));
        return asc ? c : -c;
      });
      return out;
    }
    function render() {
      const out = rows();
      $(".count", el).textContent = int(out.length) + " of " + int(opts.rows.length);
      tbody.innerHTML = out.slice(0, shown).map((row) => `<tr>${opts.columns.map((c) =>
        `<td${c.num ? ' class="num"' : ""}>${c.html ? c.html(row) : esc(row[c.key])}</td>`).join("")}</tr>`).join("");
      $(".more", el).innerHTML = out.length > shown
        ? `<button type="button">Show ${int(Math.min(PAGE * 5, out.length - shown))} more</button>` : "";
      el.querySelectorAll("th").forEach((th) => {
        th.classList.toggle("asc", th.dataset.k === sortKey && asc);
        th.classList.toggle("desc", th.dataset.k === sortKey && !asc);
      });
      if (!synced) return;
      const keep = {};
      if (state.q) keep.q = state.q;
      Object.entries(state.f).forEach(([k, v]) => v && (keep[k] = v));
      const p = parse();
      history.replaceState(null, "", "#/" + [p.page, p.arg].filter(Boolean).join("/") + query(keep));
    }
    $("input[type=search]", el).addEventListener("input", (e) => { state.q = e.target.value; shown = PAGE; render(); });
    el.querySelectorAll("select[data-f]").forEach((s) => s.addEventListener("change", () => {
      state.f[s.dataset.f] = s.value; shown = PAGE; render();
    }));
    el.querySelectorAll("th").forEach((th) => th.addEventListener("click", () => {
      if (sortKey === th.dataset.k) asc = !asc;
      else { sortKey = th.dataset.k; asc = !opts.columns.find((c) => c.key === sortKey).num; }
      render();
    }));
    $(".more", el).addEventListener("click", () => { shown += PAGE * 5; render(); });
    $(".csv", el).addEventListener("click", () => download(opts.file + "_" + dtag() + ".csv", Core.csv(rows(), opts.csvColumns)));
    render();
  }

  // ---------- maps ----------
  async function loadWorld() {
    if (!S.world) S.world = await (await fetch("data/world.json")).json();
    return S.world;
  }
  async function loadCells() {
    if (!S.cells) S.cells = await (await fetch("data/cells.json")).json();
    return S.cells;
  }

  // Whether a set of longitudes reads better with western ones moved east by
  // 360 degrees (for groups that straddle the antimeridian, e.g. Austronesian).
  function needsShift(lons) {
    if (lons.length < 2) return false;
    const span = (xs) => Math.max.apply(null, xs) - Math.min.apply(null, xs);
    return span(lons) > 180 && span(lons.map((x) => (x < 0 ? x + 360 : x))) < span(lons);
  }
  const shiftLon = (map, x) => (map._shift && x < 0 ? x + 360 : x);
  function shiftGeom(map, geom) {
    if (!map._shift) return geom;
    return geom.map((poly) => poly.map((ring) => ring.map(([x, y]) => [x < 0 ? x + 360 : x, y])));
  }

  // The map's place: a recut (new δ) keeps the view of the same page.
  function viewKey() {
    const r = parse();
    return [r.page, r.arg || "", r.params.get("f") || ""].join("|");
  }
  const worldView = (map) => map.setView(map._shift ? [5, 160] : WORLD, 2);

  const WorldControl = L.Control.extend({
    options: { position: "topleft" },
    onAdd(map) {
      const div = L.DomUtil.create("div", "leaflet-bar");
      const a = L.DomUtil.create("a", "world", div);
      a.href = "#";
      a.title = "Show the whole world";
      a.setAttribute("role", "button");
      a.textContent = "World";
      L.DomEvent.on(a, "click", (e) => { L.DomEvent.preventDefault(e); L.DomEvent.stopPropagation(e); worldView(map); });
      return div;
    },
  });

  // Points shrink and areas strengthen as the map zooms out.
  function styleForZoom(map) {
    const z = map.getZoom();
    const many = map._many;
    const r = z <= 2 ? (many ? 1.6 : 3) : z <= 4 ? (many ? 2.5 : 3.5) : 4.5;
    if (map._points) map._points.eachLayer((m) => m.setStyle && m.setStyle({ radius: r, weight: z <= 3 && many ? 0 : 0.6 }));
    if (map._areas) {
      const fill = z <= 3 ? 0.65 : z <= 5 ? 0.45 : 0.3;
      map._areas.eachLayer((g) => g.setStyle && g.setStyle({ fillOpacity: fill, weight: z <= 3 ? 0.4 : 1 }));
    }
  }

  async function makeMap(el, shift) {
    const map = L.map(el, { preferCanvas: true, worldCopyJump: false, minZoom: 1, maxZoom: 10, attributionControl: true });
    map._shift = !!shift;
    map._key = viewKey();
    new WorldControl().addTo(map);
    map.on("zoomend", () => styleForZoom(map));
    map.attributionControl.setPrefix(false);
    map.attributionControl.addAttribution('Outlines: <a href="https://www.naturalearthdata.com/">Natural Earth</a>');
    const css = getComputedStyle(document.documentElement);
    const landStyle = { color: css.getPropertyValue("--border").trim(), weight: 0.6, fillColor: css.getPropertyValue("--land").trim(), fillOpacity: 1 };
    const world = await loadWorld();
    L.geoJSON(world, { interactive: false, style: landStyle }).addTo(map);
    if (map._shift) {
      // a second copy of the outlines east of the antimeridian
      L.geoJSON(world, { interactive: false, style: landStyle, coordsToLatLng: (c) => L.latLng(c[1], c[0] + 360) }).addTo(map);
    }
    const last = S.lastView;
    if (last && last.key === map._key) {
      map.setView(last.center, last.zoom, { animate: false });
      map._restored = true;
    } else {
      worldView(map);
    }
    S.maps.push(map);
    window.glottogeneraMaps = S.maps; // read by the browser check
    return map;
  }

  const shiftFor = (ids) => needsShift(ids.map((m) => S.ix.byId[m]).filter((l) => l.lat !== null).map((l) => l.lon));
  function fitTo(map, ids, pad) {
    if (map._restored) return;
    const pts = ids.map((m) => S.ix.byId[m]).filter((l) => l.lat !== null).map((l) => [l.lat, shiftLon(map, l.lon)]);
    if (pts.length) map.fitBounds(L.latLngBounds(pts).pad(pad), { maxZoom: 7 });
  }

  function langColour(l, cut) {
    if (S.colour === "family") return colour(familyOf(l.id));
    if (S.colour === "wals") return l.wals ? colour("wals:" + l.wals) : "#999999";
    return colour(cut[l.id][0]);
  }

  function addPoints(map, langs, cut, fit) {
    const layer = L.layerGroup();
    const pts = [];
    langs.forEach((l) => {
      if (l.lat === null) return;
      const lon = shiftLon(map, l.lon);
      pts.push([l.lat, lon]);
      const [gid] = cut[l.id];
      L.circleMarker([l.lat, lon], {
        radius: 4, weight: 0.6, color: "#333", fillColor: langColour(l, cut), fillOpacity: 0.95,
      }).bindPopup(`<b><a href="${link("language/" + l.id)}">${esc(l.name)}</a></b> <span class="mono">${l.id}</span><br>
        Genus: <a href="${link("genus/" + gid)}">${esc(Core.name(S.ix, gid))}</a><br>
        Family: ${esc(familyName(familyOf(l.id)))}${l.wals ? "<br>WALS genus: " + esc(l.wals) : ""}`).addTo(layer);
    });
    layer.addTo(map);
    map._points = layer;
    map._many = langs.length > 1500;
    styleForZoom(map);
    if (fit && pts.length && !map._restored) map.fitBounds(L.latLngBounds(pts).pad(0.25), { maxZoom: 7 });
    return layer;
  }

  async function genusAreas(gens) {
    if (S.area === "none") return [];
    const opts = await areaOpts();
    return gens.map((g) => ({ g, geom: Areas.area(g.id, g.members, opts) }));
  }

  async function addAreas(map, gens, opts) {
    const areas = await genusAreas(gens);
    const layer = L.layerGroup();
    areas.forEach(({ g, geom }) => {
      if (!geom.length) return;
      const c = S.colour === "family" ? colour(familyOf(g.members[0])) : colour(g.id);
      L.geoJSON({ type: "MultiPolygon", coordinates: shiftGeom(map, geom) }, {
        style: { color: c, weight: 1, opacity: 0.9, fillColor: c, fillOpacity: (opts && opts.opacity) || 0.3 },
      }).bindPopup(`<b><a href="${link("genus/" + g.id)}">${esc(Core.name(S.ix, g.id))}</a></b><br>
        ${int(g.members.length)} language${g.members.length > 1 ? "s" : ""}, ${esc(familyName(familyOf(g.members[0])))}`).addTo(layer);
    });
    layer.addTo(map);
    map._areas = layer;
    styleForZoom(map);
    return layer;
  }

  async function areaOpts() {
    return { cells: await loadCells(), byId: S.ix.byId, radius: S.radius, maxRadius: S.data.meta.max_radius_km };
  }

  async function exportAreas(gens, format) {
    const opts = await areaOpts();
    const areas = gens.map((g) => ({ g, geom: Areas.area(g.id, g.members, opts) }));
    const features = areas.map(({ g, geom }) => ({
      properties: {
        genus_id: g.id, genus_name: Core.name(S.ix, g.id), family: familyName(familyOf(g.members[0])),
        n_languages: g.members.length, method: g.method, radius_km: S.radius, delta: Number(S.delta.toFixed(3)),
      },
      geometry: geom,
    }));
    const name = `glottogenera_areas_${S.radius}km_${dtag()}`;
    if (format === "geojson") {
      download(name + ".geojson", JSON.stringify(Areas.geojson(features)), "application/geo+json");
    } else {
      const rows = features.map((f) => Object.assign({}, f.properties, { wkt: Areas.wkt(f.geometry) }));
      download(name + ".csv", Core.csv(rows, ["genus_id", "genus_name", "family", "n_languages", "method", "radius_km", "delta", "wkt"]));
    }
  }

  function mapControls(onChange, extra) {
    const div = document.createElement("div");
    div.className = "controls";
    div.innerHTML = `
      <label><input type="checkbox" data-c="area"${S.area === "voronoi" ? " checked" : ""}> Genus areas</label>
      <label class="radius"${S.area === "voronoi" ? "" : " hidden"}>within
        <input type="range" data-c="radius" min="0" max="${radii().length - 1}" step="1" value="${radii().indexOf(S.radius)}"
          aria-label="Largest distance from a language, in km">
        <output>${int(S.radius)} km</output></label>
      <label>Colour by <select data-c="colour">
        <option value="genus"${S.colour === "genus" ? " selected" : ""}>genus</option>
        <option value="family"${S.colour === "family" ? " selected" : ""}>family</option>
        <option value="wals"${S.colour === "wals" ? " selected" : ""}>WALS genus (points)</option></select></label>
      ${extra || ""}`;
    div.querySelector('[data-c="area"]').addEventListener("change", (e) => {
      S.area = e.target.checked ? "voronoi" : "none";
      div.querySelector(".radius").hidden = S.area !== "voronoi";
      setUrl(true); onChange();
    });
    const radius = div.querySelector('[data-c="radius"]');
    const km = () => radii()[Number(radius.value)];
    radius.addEventListener("input", () => (div.querySelector(".radius output").textContent = int(km()) + " km"));
    radius.addEventListener("change", () => { S.radius = km(); setUrl(true); onChange(); });
    div.querySelector('[data-c="colour"]').addEventListener("change", (e) => { S.colour = e.target.value; setUrl(true); onChange(); });
    return div;
  }

  const AREA_NOTE = () => `<p class="note">${S.area === "voronoi"
    ? `Genus areas: each language gets the land closer to it than to any other language, up to ${S.radius} km away
      (its Voronoi cell), and the cells of a genus are merged. The distance can be set from ${RADII[0]} to ${int(S.data.meta.max_radius_km)} km.`
    : "Points are the languages' Glottolog coordinates."}
    Coordinates are Glottolog's single points per language, not speaker distributions.</p>`;

  // ---------- pages ----------
  function stats(gens) {
    const by = {};
    Object.values(gens).forEach((g) => (by[g.method] = (by[g.method] || 0) + 1));
    return by;
  }

  function home(main) {
    const { gens } = current();
    const by = stats(gens);
    const fams = new Set(S.data.languages.map((l) => familyOf(l.id))).size;
    main.innerHTML = `
      <h1>Glottogenera</h1>
      <p>Genera defined by a divergence threshold on a language tree, for genealogically balanced language samples.
      This site shows the released genera for the ${int(S.data.languages.length)} languages of Glottolog ${esc(S.data.meta.glottolog)}.</p>
      <div class="definition">Given a rooted tree over a set of languages and a divergence for its clades, a <i>genus</i> is the largest
      clade whose divergence does not exceed a threshold δ; a clade whose own divergence cannot be measured takes the largest value among
      its immediate sub-clades, and one with no measurement anywhere within it counts as not exceeding δ. The tree can be an expert
      classification or one estimated from data, and the divergence any measure of how far apart a clade's languages are.</div>
      <p>In the release, the tree is Glottolog ${esc(S.data.meta.glottolog)}; the divergence of a clade is the mean lexical distance between
      its languages on different branches, computed from alignments of their 40-concept ASJP wordlists; and δ = ${S.data.meta.delta}
      is the value at which these genera agree best with the genera of WALS on average across language families.</p>
      <div class="stats">
        <div><b>${int(Object.keys(gens).length)}</b>genera at δ = ${S.delta.toFixed(3)}</div>
        <div><b>${int(S.data.languages.length)}</b>languages</div>
        <div><b>${int(fams)}</b>families and isolates</div>
        <div><b>${int(by.divergence || 0)}</b>cut by divergence</div>
      </div>
      <p>Browse the <a href="${link("genera")}">genera</a>, <a href="${link("languages")}">languages</a> and
      <a href="${link("families")}">families</a>, see them on the <a href="${link("map")}">map</a>, compare them with the
      <a href="${link("wals")}">WALS genera</a>, or <a href="${link("downloads")}">download</a> the data. The threshold above recuts
      the genera at any δ; tables, maps and exports follow it.</p>
      <h2>Genera by how they were reached</h2>
      <div class="tablewrap"><table><thead><tr><th>method</th><th class="num">genera</th><th class="num">languages</th></tr></thead><tbody>
      ${Object.keys(METHODS).map((m) => {
        const gs = Object.values(gens).filter((g) => g.method === m);
        return `<tr><td>${esc(METHODS[m])}</td><td class="num">${int(gs.length)}</td><td class="num">${int(gs.reduce((s, g) => s + g.members.length, 0))}</td></tr>`;
      }).join("")}</tbody></table></div>`;
  }

  function familyOptions(rows) {
    const seen = new Map();
    rows.forEach((r) => seen.set(r.family_id, r.family));
    return [...seen.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }

  function generaPage(main) {
    const { gens } = current();
    const rows = Object.values(gens).map(genusRow);
    main.innerHTML = `<h1>Genera</h1><p class="muted">The genera at δ = ${S.delta.toFixed(3)}. ${isReleased()
      ? "Stability is the share of bootstrap replicates in which the genus reappears with exactly its members."
      : "Stability scores are given for the released threshold only."}</p><div id="t"></div>`;
    table($("#t", main), {
      rows, file: "glottogenera_genera", csvColumns: GENUS_COLUMNS, sort: "n_languages", asc: false,
      placeholder: "Search name, glottocode or family",
      search: (r) => [r.genus_name, r.genus_glottolog_name, r.genus_id, r.family].join(" "),
      filters: [
        { key: "f", label: "Family", options: familyOptions(rows), test: (r, v) => r.family_id === v },
        { key: "m", label: "Method", options: Object.entries(METHODS), test: (r, v) => r.method === v },
      ],
      columns: [
        { key: "genus_name", label: "Genus", html: (r) => `${swatch(r.genus_id)}<a href="${link("genus/" + r.genus_id)}">${esc(r.genus_name)}</a>` },
        { key: "genus_id", label: "Glottocode", html: (r) => `<span class="mono">${r.genus_id}</span>` },
        { key: "family", label: "Family", html: (r) => `<a href="${link("family/" + r.family_id)}">${esc(r.family)}</a>` },
        { key: "n_languages", label: "Languages", num: true },
        { key: "method", label: "Method", html: (r) => esc(METHODS[r.method]) },
        { key: "cut_value", label: "Cut value", num: true, html: (r) => fmt(r.cut_value, 3) },
        { key: "from_delta", label: "Genus for δ in", html: (r) => `[${fmt(r.from_delta)}, ${fmt(r.to_delta)})` },
        { key: "stability", label: "Stability", num: true, html: (r) => fmt(r.stability, 2) },
      ],
    });
  }

  function languagesPage(main) {
    const { cut } = current();
    const rows = S.data.languages.map((l) => languageRow(l, cut));
    const areas = [...new Set(S.data.languages.flatMap((l) => (l.macroarea || "").split(";")).filter(Boolean))].sort();
    main.innerHTML = `<h1>Languages</h1><p class="muted">The in-scope languages of Glottolog ${esc(S.data.meta.glottolog)} and their genera at δ = ${S.delta.toFixed(3)}.</p><div id="t"></div>`;
    table($("#t", main), {
      rows, file: "glottogenera_languages", csvColumns: LANG_COLUMNS, sort: "name",
      placeholder: "Search name, glottocode, ISO code or genus",
      search: (r) => [r.name, r.glottocode, r.iso639_3, r.genus_name, r.family].join(" "),
      filters: [
        { key: "f", label: "Family", options: familyOptions(rows), test: (r, v) => r.family_id === v },
        { key: "m", label: "Macroarea", options: areas.map((a) => [a, a]), test: (r, v) => r.macroarea.split(";").includes(v) },
      ],
      columns: [
        { key: "name", label: "Language", html: (r) => `<a href="${link("language/" + r.glottocode)}">${esc(r.name)}</a>` },
        { key: "glottocode", label: "Glottocode", html: (r) => `<span class="mono">${r.glottocode}</span>` },
        { key: "iso639_3", label: "ISO 639-3", html: (r) => `<span class="mono">${esc(r.iso639_3)}</span>` },
        { key: "genus_name", label: "Genus", html: (r) => `${swatch(r.genus_id)}<a href="${link("genus/" + r.genus_id)}">${esc(r.genus_name)}</a>` },
        { key: "family", label: "Family", html: (r) => `<a href="${link("family/" + r.family_id)}">${esc(r.family)}</a>` },
        { key: "macroarea", label: "Macroarea" },
        { key: "wals_genus", label: "WALS genus" },
      ],
    });
  }

  function familiesPage(main) {
    const { cut } = current();
    const by = {};
    S.data.languages.forEach((l) => {
      const f = familyOf(l.id);
      (by[f] = by[f] || { langs: 0, genera: new Set() }).langs++;
      by[f].genera.add(cut[l.id][0]);
    });
    const agreement = {};
    walsAgreement(cut).forEach((a) => (agreement[a.fid] = a.ari));
    const rows = Object.entries(by).map(([fid, v]) => ({
      family_id: fid, family: familyName(fid), n_languages: v.langs, n_genera: v.genera.size,
      isolate: !S.ix.nodes[fid], wals_ari: agreement[fid] === undefined ? "" : Number(agreement[fid].toFixed(3)),
      delta: S.delta.toFixed(3),
    }));
    main.innerHTML = `<h1>Families</h1><p class="muted">Top-level Glottolog families and isolates, with their genera at δ = ${S.delta.toFixed(3)}
      and, for families with at least two WALS genera, the agreement (adjusted Rand index) with WALS.</p><div id="t"></div>`;
    table($("#t", main), {
      rows, file: "glottogenera_families", csvColumns: ["family_id", "family", "isolate", "n_languages", "n_genera", "wals_ari", "delta"],
      sort: "n_languages", asc: false, placeholder: "Search family",
      search: (r) => r.family + " " + r.family_id,
      filters: [{ key: "m", label: "Type", options: [["family", "families"], ["isolate", "isolates"]], test: (r, v) => (v === "isolate") === r.isolate }],
      columns: [
        { key: "family", label: "Family", html: (r) => `<a href="${link((r.isolate ? "language/" : "family/") + r.family_id)}">${esc(r.family)}</a>${r.isolate ? ' <span class="badge">isolate</span>' : ""}` },
        { key: "family_id", label: "Glottocode", html: (r) => `<span class="mono">${r.family_id}</span>` },
        { key: "n_languages", label: "Languages", num: true },
        { key: "n_genera", label: "Genera", num: true },
        { key: "wals_ari", label: "ARI with WALS", num: true, html: (r) => fmt(r.wals_ari, 3) },
      ],
    });
  }

  function lineageTable(langId, cut) {
    const lin = S.ix.lineage[langId];
    const gid = cut[langId][0];
    return `<div class="tablewrap"><table><thead><tr><th>Glottolog node</th><th class="num">cut value c</th><th class="num">crown divergence</th><th class="num">pairs</th><th></th></tr></thead><tbody>
      ${lin.map((id) => {
        const n = S.ix.nodes[id];
        const c = Core.cutValue(S.ix, id);
        const label = id === gid ? '<span class="badge genus">genus</span>' : c !== undefined && c > S.delta && lin.indexOf(id) < lin.indexOf(gid) ? '<span class="badge">above δ</span>' : "";
        const nm = n ? n.name : S.ix.byId[id].name;
        const target = S.ix.byId[id] ? "language/" : (id === lin[0] ? "family/" : "genus/");
        return `<tr${id === gid ? ' class="current"' : ""}><td><a href="${link(target + id)}">${esc(nm)}</a> <span class="mono muted">${id}</span></td>
          <td class="num">${fmt(c)}</td><td class="num">${fmt(n && n.D)}</td><td class="num">${n && n.pairs ? int(n.pairs) : "–"}</td><td>${label}</td></tr>`;
      }).join("")}</tbody></table></div>`;
  }

  async function genusPage(main, id) {
    const { cut, gens } = current();
    const node = S.ix.nodes[id];
    const lang = S.ix.byId[id];
    if (!node && !lang) { main.innerHTML = `<h1>Not found</h1><p>No Glottolog node <span class="mono">${esc(id)}</span>.</p>`; return; }
    const members = S.ix.below[id] || [];
    const g = gens[id];
    const nameRow = S.data.names[id];
    const glName = node ? node.name : lang.name;
    const fid = familyOf(members[0] || id);
    const released = S.data.genera[id];
    let status;
    if (g) {
      const [lo, hi] = Core.range(S.ix, id, g.method);
      status = `<dt>Genus for δ in</dt><dd>[${fmt(lo)}, ${fmt(hi)})</dd>`;
    } else {
      const now = [...new Set(members.map((m) => cut[m][0]))];
      status = `<dt>At δ = ${S.delta.toFixed(3)}</dt><dd>not a genus; its languages fall in ${now.length === 1
        ? `the genus <a href="${link("genus/" + now[0])}">${esc(Core.name(S.ix, now[0]))}</a>`
        : `${int(now.length)} genera: ${now.slice(0, 12).map((x) => `<a href="${link("genus/" + x)}">${esc(Core.name(S.ix, x))}</a>`).join(", ")}${now.length > 12 ? ", …" : ""}`}.</dd>`;
    }
    const walsCount = {};
    members.forEach((m) => { const w = S.ix.byId[m].wals; if (w) walsCount[w] = (walsCount[w] || 0) + 1; });
    const walsTotal = {};
    S.data.languages.forEach((l) => l.wals && (walsTotal[l.wals] = (walsTotal[l.wals] || 0) + 1));
    main.innerHTML = `
      <p class="muted"><a href="${link("genera")}">Genera</a> › <a href="${link("family/" + fid)}">${esc(familyName(fid))}</a></p>
      <h1>${swatch(id)}${esc(Core.name(S.ix, id))}</h1>
      <dl class="facts">
        <dt>Glottolog node</dt><dd><a href="${GLOTTOLOG + id}">${esc(glName)}</a> <span class="mono">${id}</span></dd>
        ${nameRow ? `<dt>Name</dt><dd>${esc(nameRow.name)} replaces the Glottolog name (${esc(nameRow.criterion.replace(/;/g, ", "))}; ${esc(nameRow.confidence)} confidence). ${esc(nameRow.rationale)}<br><span class="note">Sources: ${sources(nameRow.sources)}</span></dd>` : ""}
        <dt>Family</dt><dd><a href="${link("family/" + fid)}">${esc(familyName(fid))}</a></dd>
        <dt>Languages</dt><dd>${int(members.length)}</dd>
        ${g ? `<dt>Method</dt><dd>${esc(METHODS[g.method])}</dd>` : ""}
        <dt>Cut value c</dt><dd>${fmt(Core.cutValue(S.ix, id))}${node && node.D !== null ? ` (own crown divergence ${fmt(node.D)} from ${int(node.pairs)} language pairs)` : node ? " (not measured; the largest value among its sub-clades)" : ""}</dd>
        ${status}
        ${released && isReleased() ? `<dt>Stability</dt><dd>${fmt(released.stability, 2)} with δ recalibrated, ${fmt(released.stability_fixed_delta, 2)} with δ fixed; margins ${fmt(released.margin_below)} below and ${fmt(released.margin_above)} above δ</dd>` : ""}
      </dl>
      <h2>Map</h2><div id="mapctl"></div><div class="map" id="map"></div><div id="areanote"></div>
      <div class="cols">
        <div><h2>Languages</h2><div id="t"></div></div>
        <div><h2>WALS genera of its languages</h2>
          ${Object.keys(walsCount).length ? `<div class="tablewrap"><table><thead><tr><th>WALS genus</th><th class="num">here</th><th class="num">in WALS (mapped)</th></tr></thead><tbody>
          ${Object.entries(walsCount).sort((a, b) => b[1] - a[1]).map(([w, n]) => `<tr><td>${esc(w)}</td><td class="num">${n}</td><td class="num">${walsTotal[w]}</td></tr>`).join("")}
          </tbody></table></div>` : '<p class="muted">None of its languages is in WALS.</p>'}
          <h2>Position in the classification</h2>${lineageTable(members[0], cut).replace(/<tr class="current">/, '<tr class="current">')}</div>
      </div>`;
    const rows = members.map((m) => languageRow(S.ix.byId[m], cut));
    table($("#t", main), {
      rows, file: "glottogenera_" + id + "_languages", url: false, csvColumns: LANG_COLUMNS, sort: "name", placeholder: "Search languages",
      search: (r) => [r.name, r.glottocode, r.iso639_3].join(" "),
      columns: [
        { key: "name", label: "Language", html: (r) => `<a href="${link("language/" + r.glottocode)}">${esc(r.name)}</a>` },
        { key: "glottocode", label: "Glottocode", html: (r) => `<span class="mono">${r.glottocode}</span>` },
        { key: "genus_name", label: "Genus now", html: (r) => r.genus_id === id ? "–" : `<a href="${link("genus/" + r.genus_id)}">${esc(r.genus_name)}</a>` },
        { key: "wals_genus", label: "WALS genus" },
      ],
    });
    const map = await makeMap($("#map", main), shiftFor(members));
    const draw = async () => {
      map.eachLayer((l) => l._glg && map.removeLayer(l));
      const shown = g ? [g] : [...new Set(members.map((m) => cut[m][0]))].map((x) => gens[x]);
      const a = await addAreas(map, shown);
      a._glg = true;
      const p = addPoints(map, members.map((m) => S.ix.byId[m]), cut, false);
      p._glg = true;
      $("#areanote", main).innerHTML = AREA_NOTE();
    };
    $("#mapctl", main).appendChild(mapControls(draw));
    await draw();
    fitTo(map, members, 0.3);
  }

  async function languagePage(main, id) {
    const { cut, gens } = current();
    const l = S.ix.byId[id];
    if (!l) {
      if (S.ix.nodes[id]) { location.hash = link("genus/" + id); return; }
      main.innerHTML = `<h1>Not found</h1><p>No in-scope language <span class="mono">${esc(id)}</span>.</p>`;
      return;
    }
    const [gid, method] = cut[id];
    const fid = familyOf(id);
    main.innerHTML = `
      <p class="muted"><a href="${link("languages")}">Languages</a> › <a href="${link((S.ix.nodes[fid] ? "family/" : "language/") + fid)}">${esc(familyName(fid))}</a></p>
      <h1>${esc(l.name)}</h1>
      <dl class="facts">
        <dt>Glottocode</dt><dd><a href="${GLOTTOLOG + id}">${id}</a></dd>
        ${l.iso ? `<dt>ISO 639-3</dt><dd class="mono">${esc(l.iso)}</dd>` : ""}
        <dt>Genus at δ = ${S.delta.toFixed(3)}</dt><dd>${swatch(gid)}<a href="${link("genus/" + gid)}">${esc(Core.name(S.ix, gid))}</a> (${esc(METHODS[method])}, ${int(gens[gid].members.length)} language${gens[gid].members.length > 1 ? "s" : ""})</dd>
        <dt>Family</dt><dd>${S.ix.nodes[fid] ? `<a href="${link("family/" + fid)}">${esc(familyName(fid))}</a>` : "isolate"}</dd>
        <dt>Coordinates</dt><dd>${l.lat === null ? "none in Glottolog" : `${l.lat}, ${l.lon}`}</dd>
        ${l.macroarea ? `<dt>Macroarea</dt><dd>${esc(l.macroarea.replace(/;/g, ", "))}</dd>` : ""}
        ${l.wals ? `<dt>WALS</dt><dd>genus ${esc(l.wals)}; ${l.wals_ids.map((w) => `<a href="https://wals.info/languoid/lect/wals_code_${encodeURIComponent(w)}">${esc(w)}</a>`).join(", ")}</dd>` : ""}
      </dl>
      <h2>Position in the classification</h2>
      <p class="note">Walking down from the family, the genus is the first node whose cut value is at most δ.</p>
      ${lineageTable(id, cut)}
      <h2>Map</h2><div id="mapctl"></div><div class="map" id="map"></div><div id="areanote"></div>`;
    if (l.lat === null) { $("#map", main).remove(); return; }
    const map = await makeMap($("#map", main), shiftFor(gens[gid].members));
    const draw = async () => {
      map.eachLayer((x) => x._glg && map.removeLayer(x));
      const a = await addAreas(map, [gens[gid]]);
      a._glg = true;
      const p = addPoints(map, gens[gid].members.map((m) => S.ix.byId[m]), cut, false);
      p._glg = true;
      const me = L.circleMarker([l.lat, shiftLon(map, l.lon)], { radius: 7, weight: 2, color: "#000", fill: false });
      me._glg = true;
      me.addTo(map);
      $("#areanote", main).innerHTML = AREA_NOTE();
    };
    $("#mapctl", main).appendChild(mapControls(draw));
    await draw();
    if (!map._restored) map.setView([l.lat, shiftLon(map, l.lon)], 5);
  }

  function treeHtml(id, gens, depth) {
    const kids = S.ix.children[id] || [];
    const isLang = !!S.ix.byId[id];
    const n = S.ix.nodes[id];
    const c = Core.cutValue(S.ix, id);
    const g = gens[id];
    const count = (S.ix.below[id] || []).length;
    const nm = isLang ? S.ix.byId[id].name : n.name;
    const label = `${g ? swatch(id) : ""}<a href="${link((isLang ? "language/" : "genus/") + id)}" class="${g ? "isgenus" : ""}">${esc(g ? Core.name(S.ix, id) : nm)}</a>
      <span class="val">${isLang ? "" : `${int(count)} lang. · c ${fmt(c)}`}${g ? ` · <span class="badge genus">genus</span>` : (!isLang && c !== undefined && c > S.delta ? " · above δ" : "")}</span>`;
    if (!kids.length) return `<li>${label}</li>`;
    const open = !g && depth < 6 ? " open" : "";
    return `<li><details${open}><summary>${label}</summary><ul>${kids.map((k) => treeHtml(k, gens, depth + 1)).join("")}</ul></details></li>`;
  }

  async function familyPage(main, id) {
    const { cut, gens } = current();
    if (!S.ix.nodes[id]) { location.hash = link("language/" + id); return; }
    const members = S.ix.below[id] || [];
    const famGens = [...new Set(members.map((m) => cut[m][0]))].map((x) => gens[x]);
    const wa = walsAgreement(cut).find((a) => a.fid === id);
    main.innerHTML = `
      <p class="muted"><a href="${link("families")}">Families</a></p>
      <h1>${esc(familyName(id))}</h1>
      <dl class="facts">
        <dt>Glottocode</dt><dd><a href="${GLOTTOLOG + id}">${id}</a></dd>
        <dt>Languages</dt><dd>${int(members.length)}</dd>
        <dt>Genera at δ = ${S.delta.toFixed(3)}</dt><dd>${int(famGens.length)}</dd>
        ${wa ? `<dt>Agreement with WALS</dt><dd>ARI ${fmt(wa.ari)} over ${int(wa.n)} WALS languages in ${int(wa.wals_genera)} WALS genera</dd>` : ""}
      </dl>
      <h2>Map</h2><div id="mapctl"></div><div class="map" id="map"></div><div id="areanote"></div>
      <h2>Tree</h2>
      <p class="note">The Glottolog classification with each node's cut value c. Genera at the current δ are marked; nodes above δ are split.
      Languages are listed under their genera.</p>
      <ul class="tree">${treeHtml(id, gens, 0)}</ul>`;
    const map = await makeMap($("#map", main), shiftFor(members));
    const draw = async () => {
      map.eachLayer((x) => x._glg && map.removeLayer(x));
      const a = await addAreas(map, famGens);
      a._glg = true;
      const p = addPoints(map, members.map((m) => S.ix.byId[m]), cut, false);
      p._glg = true;
      $("#areanote", main).innerHTML = AREA_NOTE();
    };
    const extra = `<button type="button" data-x="geojson">Export areas (GeoJSON)</button><button type="button" data-x="csv">Export areas (CSV, WKT)</button>`;
    const ctl = mapControls(draw, extra);
    ctl.querySelectorAll("[data-x]").forEach((b) => b.addEventListener("click", () => exportAreas(famGens, b.dataset.x)));
    $("#mapctl", main).appendChild(ctl);
    await draw();
    fitTo(map, members, 0.15);
  }

  async function mapPage(main) {
    const { cut, gens } = current();
    const r = parse();
    const fam = r.params.get("f") || "";
    const fams = [...new Set(S.data.languages.map((l) => familyOf(l.id)))].filter((f) => S.ix.nodes[f])
      .sort((a, b) => familyName(a).localeCompare(familyName(b)));
    main.innerHTML = `<h1>Map</h1><div id="mapctl"></div><div class="map large" id="map"></div><div id="areanote"></div>`;
    const extra = `<label>Family <select data-c="fam"><option value="">all</option>${fams.map((f) =>
      `<option value="${f}"${f === fam ? " selected" : ""}>${esc(familyName(f))}</option>`).join("")}</select></label>
      <button type="button" data-x="geojson">Export areas (GeoJSON)</button>
      <button type="button" data-x="csv">Export areas (CSV, WKT)</button>
      <button type="button" data-x="langs">Export languages (CSV)</button>`;
    const famLangs = fam ? S.data.languages.filter((l) => familyOf(l.id) === fam).map((l) => l.id) : [];
    const map = await makeMap($("#map", main), fam && shiftFor(famLangs));
    let selected = fam;
    const scope = () => {
      const langs = S.data.languages.filter((l) => !selected || familyOf(l.id) === selected);
      const gs = [...new Set(langs.map((l) => cut[l.id][0]))].map((x) => gens[x]);
      return { langs, gs };
    };
    const draw = async (fit) => {
      map.eachLayer((x) => x._glg && map.removeLayer(x));
      const { langs, gs } = scope();
      const a = await addAreas(map, gs, { opacity: 0.35 });
      a._glg = true;
      const p = addPoints(map, langs, cut, false);
      if (fit && selected) fitTo(map, langs.map((l) => l.id), 0.15);
      p._glg = true;
      $("#areanote", main).innerHTML = AREA_NOTE() + `<p class="note">${int(gs.length)} genera, ${int(langs.length)} languages at δ = ${S.delta.toFixed(3)}.</p>`;
    };
    const ctl = mapControls(() => draw(false), extra);
    ctl.querySelector('[data-c="fam"]').addEventListener("change", (e) => {
      location.hash = "#/map" + query(e.target.value ? { f: e.target.value } : {});
    });
    ctl.querySelectorAll("[data-x]").forEach((b) => b.addEventListener("click", () => {
      const { langs, gs } = scope();
      if (b.dataset.x === "langs") download("glottogenera_languages_" + dtag() + ".csv", Core.csv(langs.map((l) => languageRow(l, cut)), LANG_COLUMNS));
      else exportAreas(gs, b.dataset.x);
    }));
    $("#mapctl", main).appendChild(ctl);
    await draw(true);
  }

  function walsPage(main) {
    const { cut } = current();
    const rows = walsAgreement(cut).map((a) => ({
      family_id: a.fid, family: familyName(a.fid), wals_languages: a.n, wals_genera: a.wals_genera,
      genera: a.genera, ari: Number(a.ari.toFixed(4)), delta: S.delta.toFixed(3),
    }));
    const mean = rows.reduce((s, r) => s + r.ari, 0) / rows.length;
    const byW = {};
    S.data.languages.forEach((l) => {
      if (!l.wals) return;
      const w = (byW[l.wals] = byW[l.wals] || { langs: 0, genera: {} });
      w.langs++;
      const g = cut[l.id][0];
      w.genera[g] = (w.genera[g] || 0) + 1;
    });
    const wrows = Object.entries(byW).map(([w, v]) => {
      const top = Object.entries(v.genera).sort((a, b) => b[1] - a[1])[0];
      return {
        wals_genus: w, languages: v.langs, genera: Object.keys(v.genera).length,
        largest_genus_id: top[0], largest_genus: Core.name(S.ix, top[0]), share_in_largest: Number((top[1] / v.langs).toFixed(3)),
        delta: S.delta.toFixed(3),
      };
    });
    main.innerHTML = `<h1>Comparison with WALS</h1>
      <p>WALS assigns ${int(Object.values(byW).reduce((s, v) => s + v.langs, 0))} of these languages to genera (Dryer's genera, WALS ${esc(S.data.meta.wals)}).
      The threshold was calibrated to maximize the mean agreement (adjusted Rand index, ARI) between these genera and the WALS genera
      over the ${rows.length} families with at least two WALS genera; WALS's non-genealogical "Creoles and Pidgins" is left out.</p>
      <div class="stats"><div><b>${fmt(mean, 3)}</b>mean family ARI at δ = ${S.delta.toFixed(3)}</div>
      <div><b>${rows.length}</b>families</div></div>
      <p class="note">The calibration averages this agreement over a window of ±0.02 around each δ; the value here is unsmoothed.
      Use the colour option "WALS genus" on the <a href="${link("map")}">map</a> to compare the two visually.</p>
      <h2>Agreement by family</h2><div id="t1"></div>
      <h2>WALS genera</h2><p class="muted">For each WALS genus: into how many genera its languages fall, and which genus holds most of them.</p><div id="t2"></div>`;
    table($("#t1", main), {
      rows, file: "glottogenera_wals_families", csvColumns: ["family_id", "family", "wals_languages", "wals_genera", "genera", "ari", "delta"],
      sort: "wals_languages", asc: false, placeholder: "Search family", search: (r) => r.family,
      columns: [
        { key: "family", label: "Family", html: (r) => `<a href="${link("family/" + r.family_id)}">${esc(r.family)}</a>` },
        { key: "wals_languages", label: "WALS languages", num: true },
        { key: "wals_genera", label: "WALS genera", num: true },
        { key: "genera", label: "Genera here", num: true },
        { key: "ari", label: "ARI", num: true, html: (r) => fmt(r.ari, 3) },
      ],
    });
    table($("#t2", main), {
      rows: wrows, file: "glottogenera_wals_genera", url: false,
      csvColumns: ["wals_genus", "languages", "genera", "largest_genus_id", "largest_genus", "share_in_largest", "delta"],
      sort: "languages", asc: false, placeholder: "Search WALS genus", search: (r) => r.wals_genus + " " + r.largest_genus,
      columns: [
        { key: "wals_genus", label: "WALS genus" },
        { key: "languages", label: "Languages", num: true },
        { key: "genera", label: "Genera here", num: true },
        { key: "largest_genus", label: "Main genus here", html: (r) => `${swatch(r.largest_genus_id)}<a href="${link("genus/" + r.largest_genus_id)}">${esc(r.largest_genus)}</a>` },
        { key: "share_in_largest", label: "Share in it", num: true, html: (r) => fmt(r.share_in_largest, 2) },
      ],
    });
  }

  function downloadsPage(main) {
    const { cut, gens } = current();
    main.innerHTML = `<h1>Downloads</h1>
      <h2>Released files</h2>
      <p>The released dataset, at δ = ${S.data.meta.delta}, as tab-separated files (see the data description in the repository).</p>
      <div class="tablewrap"><table><thead><tr><th>file</th><th>content</th></tr></thead><tbody>
        <tr><td><a href="${RELEASE}genera.tsv">genera.tsv</a></td><td>one row per language: its genus and how it was reached</td></tr>
        <tr><td><a href="${RELEASE}genera_summary.tsv">genera_summary.tsv</a></td><td>one row per genus: size, crown divergence, margins, stability</td></tr>
        <tr><td><a href="${RELEASE}nodes.tsv">nodes.tsv</a></td><td>one row per measured Glottolog node: crown divergence</td></tr>
        <tr><td><a href="${RELEASE}genus_names.tsv">genus_names.tsv</a></td><td>curated genus names, with criteria, rationale and sources</td></tr>
        <tr><td><a href="${RELEASE}params.json">params.json</a></td><td>sources, parameters, calibration curve and evaluation</td></tr>
      </tbody></table></div>
      <p>The same data as a CLDF StructureDataset are in the <a href="${REPO}/tree/main/cldf">cldf/</a> directory of the repository. Licence: CC BY 4.0.</p>
      <h2>At the current threshold, δ = ${S.delta.toFixed(3)}</h2>
      <p>CSV files with comma separators and a header row, UTF-8; every row records δ.</p>
      <p class="controls">
        <button type="button" data-x="langs">Languages (CSV)</button>
        <button type="button" data-x="genera">Genera (CSV)</button>
      </p>
      <h3>Areas of all genera</h3>
      <p class="note">The merged Voronoi cells of each genus's languages, as GeoJSON (WGS 84 longitude/latitude) or as CSV with
      the shapes as WKT MULTIPOLYGON. A language's cell is the land closer to it than to any other language, up to
      ${S.radius} km away (set the distance on the <a href="${link("map")}">map</a>; Natural Earth ${esc(S.data.meta.natural_earth)} 1:50m land, extended 15 km around every
      language for small islands).</p>
      <p class="controls">
        <button type="button" data-f="geojson">Areas (GeoJSON)</button>
        <button type="button" data-f="csv">Areas (CSV, WKT)</button>
      </p>`;
    main.querySelector('[data-x="langs"]').addEventListener("click", () => download("glottogenera_languages_" + dtag() + ".csv",
      Core.csv(S.data.languages.map((l) => languageRow(l, cut)), LANG_COLUMNS)));
    main.querySelector('[data-x="genera"]').addEventListener("click", () => download("glottogenera_genera_" + dtag() + ".csv",
      Core.csv(Object.values(gens).map(genusRow), GENUS_COLUMNS)));
    main.querySelectorAll("[data-f]").forEach((b) => b.addEventListener("click", async () => {
      b.disabled = true;
      await exportAreas(Object.values(gens), b.dataset.f);
      b.disabled = false;
    }));
  }

  async function aboutPage(main) {
    const m = S.data.meta;
    main.innerHTML = `<h1>About</h1>
      <p>Glottogenera sorts the world's languages into <i>genera</i>: groups of closely related languages, roughly as deep as
      Germanic or Romance. Genera help build balanced samples of languages: taking one or a few languages per genus keeps large
      families from dominating a study.</p>
      <h2>How the genera are made</h2>
      <p>A genus is the largest branch of the family tree whose languages are not more different from each other than a threshold, δ.
      Here the tree is the Glottolog ${esc(m.glottolog)} classification, and the difference between languages is measured on their basic
      vocabulary, the 40-word ASJP lists. The released threshold, δ = ${m.delta}, is the one that best matches the genera of WALS. Raising
      δ merges genera, lowering it splits them; the threshold control on every page shows this live.</p>
      <figure class="about-figure">
        <img src="data/dravidian.png" alt="Four maps of South Asia showing the Dravidian genera at δ = 0.55, 0.65, 0.73 and 0.81" loading="lazy">
        <figcaption>The Dravidian languages at four thresholds: 19 genera at δ = 0.55, six at 0.73 (close to the WALS genera), and a
        single genus at the released 0.81. <a href="${link("map")}">Explore the map</a>.</figcaption>
      </figure>
      <p>The same rule works on any language tree, including trees estimated from data, and with any measure of difference; the
      <a href="${REPO}">Python package</a> applies it. The exact definition is in
      <a href="${REPO}/blob/main/docs/definition.md">docs/definition.md</a> and the method in
      <a href="${REPO}/blob/main/docs/methods.md">docs/methods.md</a>.</p>
      <h2>Using the site</h2>
      <ul>
        <li>Browse genera, languages and families, and compare them with WALS.</li>
        <li>On the map, a genus's area is drawn around its languages' Glottolog locations; it shows where the languages are
        recorded, not where their speakers live.</li>
        <li>Genus names are Glottolog's, except for a few curated ones.</li>
        <li>Every table can be downloaded as CSV, and the areas as GeoJSON; the full dataset is on the
        <a href="${link("downloads")}">Downloads</a> page.</li>
      </ul>
      <h2>Citation</h2>
      <p>Tresoldi, Tiago. Glottogenera: genera defined by a divergence threshold on a language tree, with a release for Glottolog ${esc(m.glottolog)}, version ${esc(m.version)}. Zenodo, doi:<a href="https://doi.org/10.5281/zenodo.24010019">10.5281/zenodo.24010019</a>.
      <a href="${REPO}">${REPO}</a>. Please also cite Glottolog (doi:${esc(m.glottolog_doi)}), ASJP and, if you use the comparison, WALS.
      A paper describing the dataset is in preparation.</p>
      <h2>Author</h2>
      <p>Tiago Tresoldi, Department of Linguistics and Philology / Center for the Human Past, Uppsala University.</p>
      <h2>Licences</h2>
      <p>Data CC BY 4.0, from Glottolog, ASJP and WALS ${esc(m.wals)} (all CC BY 4.0); code MIT. Map outlines from Natural Earth
      ${esc(m.natural_earth)} (public domain). The site uses Leaflet 1.9.4 (BSD-2-Clause) and polygon-clipping 0.15.7 (MIT).</p>`;
  }

  // ---------- shell ----------
  const PAGES = {
    home, genera: generaPage, languages: languagesPage, families: familiesPage, genus: genusPage,
    language: languagePage, family: familyPage, map: mapPage, wals: walsPage, downloads: downloadsPage, about: aboutPage,
  };

  function updateHeader() {
    const { gens } = current();
    $("#delta").value = S.delta;
    $("#delta-num").value = S.delta.toFixed(3);
    const m = S.data.meta;
    $("#delta-info").textContent = `${int(Object.keys(gens).length)} genera · released δ = ${m.delta}` +
      ` (resampling range ${m.resampling_range[0]}–${m.resampling_range[2]})`;
    $("#delta-reset").disabled = isReleased();
  }

  async function render() {
    const r = parse();
    readParams(r.params);
    updateHeader();
    if (S.maps.length) {
      const m = S.maps[0];
      S.lastView = { key: m._key, center: m.getCenter(), zoom: m.getZoom() };
    }
    S.maps.forEach((m) => m.remove());
    S.maps = [];
    document.querySelectorAll("nav a").forEach((a) => a.classList.toggle("active", a.dataset.nav === r.page ||
      (a.dataset.nav === "genera" && r.page === "genus") || (a.dataset.nav === "languages" && r.page === "language") ||
      (a.dataset.nav === "families" && r.page === "family")));
    const main = $("#main");
    const page = PAGES[r.page];
    if (!page) { main.innerHTML = `<h1>Not found</h1><p><a href="#/">Home</a></p>`; return; }
    const titleArg = r.arg ? " – " + Core.name(S.ix, r.arg) : "";
    document.title = "Glottogenera" + (r.page === "home" ? "" : " – " + r.page[0].toUpperCase() + r.page.slice(1) + titleArg);
    try {
      await page(main, r.arg);
    } catch (e) {
      main.innerHTML = `<h1>Something went wrong</h1><p class="mono">${esc(e && e.message)}</p>`;
      throw e;
    }
  }

  function setDelta(d) {
    if (!isFinite(d)) return;
    S.delta = Math.min(1, Math.max(0.5, Math.round(d * 1000) / 1000));
    setUrl(true);
    render();
  }

  // Shown once per browser session (every visit when storage is unavailable).
  function showNotice() {
    const dialog = $("#notice");
    let seen = false;
    try { seen = sessionStorage.getItem("glottogenera-notice") === "seen"; } catch (e) { /* storage blocked */ }
    if (seen || !dialog || typeof dialog.showModal !== "function") return;
    dialog.addEventListener("close", () => {
      try { sessionStorage.setItem("glottogenera-notice", "seen"); } catch (e) { /* storage blocked */ }
    });
    dialog.showModal();
  }

  async function start() {
    S.data = await (await fetch("data/glottogenera.json")).json();
    S.ix = Core.index(S.data);
    $("#version").textContent = S.data.meta.version;
    let timer = null;
    $("#delta").addEventListener("input", (e) => {
      $("#delta-num").value = Number(e.target.value).toFixed(3);
      clearTimeout(timer);
      timer = setTimeout(() => setDelta(Number(e.target.value)), 200);
    });
    $("#delta-num").addEventListener("change", (e) => setDelta(Number(e.target.value)));
    $("#delta-reset").addEventListener("click", () => setDelta(S.data.meta.delta));
    window.addEventListener("hashchange", render);
    render();
    showNotice();
  }

  start().catch((e) => {
    $("#main").innerHTML = `<h1>Could not load the data</h1><p class="mono">${esc(e && e.message)}</p>`;
  });
})();
