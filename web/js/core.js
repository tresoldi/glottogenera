/*
 * The genera at any threshold, recut from the released cut values exactly as
 * glottogenera.genera_at() does, and helpers shared by the pages. Runs in the
 * browser (window.Core) and under Node (module.exports) for the tests.
 */
(function (root) {
  "use strict";

  function index(data) {
    const nodes = data.nodes;
    const langs = data.languages;
    const byId = {};
    langs.forEach((l) => (byId[l.id] = l));
    const children = {};
    const lineage = {};
    function path(id) {
      const out = [];
      for (let p = id; p; p = nodes[p] ? nodes[p].parent : null) out.push(p);
      return out.reverse();
    }
    langs.forEach((l) => {
      const anc = l.parent ? path(l.parent) : [];
      lineage[l.id] = anc.concat([l.id]);
      if (l.parent) (children[l.parent] = children[l.parent] || []).push(l.id);
    });
    Object.keys(nodes).forEach((id) => {
      const p = nodes[id].parent;
      if (p) (children[p] = children[p] || []).push(id);
    });
    Object.values(children).forEach((list) => list.sort());
    const below = {};
    langs.forEach((l) => lineage[l.id].forEach((n) => (below[n] = below[n] || []).push(l.id)));
    return { data, nodes, byId, children, lineage, below };
  }

  // c(u): the node's cut value, undefined without any measurement at or below it.
  function cutValue(ix, id) {
    const n = ix.nodes[id];
    return n && n.c !== null && n.c !== undefined ? n.c : undefined;
  }

  // {language: [genus, method]}, mirroring divergence.divergence_genera.
  function recut(ix, delta) {
    const out = {};
    ix.data.languages.forEach((l) => {
      const lin = ix.lineage[l.id];
      for (let i = 0; i < lin.length; i++) {
        const node = lin[i];
        const e = cutValue(ix, node);
        if (e === undefined) {
          if (lin.length === 1) out[l.id] = [l.id, "isolate"];
          else if (i === 0) out[l.id] = [node, "unmeasured-family"];
          else if (node === l.id) out[l.id] = [l.id, "single-language"];
          else out[l.id] = [node, "unmeasured-clade"];
          break;
        }
        if (e <= delta) {
          out[l.id] = [node, "divergence"];
          break;
        }
      }
    });
    return out;
  }

  // {genus: {id, members, method}} from a recut.
  function genera(cut) {
    const out = {};
    Object.keys(cut).sort().forEach((lang) => {
      const [g, method] = cut[lang];
      if (!out[g]) out[g] = { id: g, members: [], method };
      out[g].members.push(lang);
    });
    return out;
  }

  // Thresholds over which a genus exists: [from, to), see genera_summary.tsv.
  function range(ix, id, method) {
    const lin = ix.lineage[ix.below[id] ? ix.below[id][0] : id];
    const k = lin.indexOf(id);
    const above = lin.slice(0, k).map((a) => cutValue(ix, a)).filter((v) => v !== undefined);
    const upper = above.length ? Math.min.apply(null, above) : Infinity;
    const lower = method === "divergence" ? cutValue(ix, id) : -Infinity;
    return [lower, upper];
  }

  function name(ix, id) {
    if (ix.data.names[id]) return ix.data.names[id].name;
    if (ix.nodes[id]) return ix.nodes[id].name;
    return ix.byId[id] ? ix.byId[id].name : id;
  }

  function family(ix, langId) {
    return ix.lineage[langId][0];
  }

  // Adjusted Rand index between two labelings of the same items.
  function ari(a, b) {
    const n = a.length;
    if (n < 2) return NaN;
    const table = new Map(), ra = new Map(), rb = new Map();
    for (let i = 0; i < n; i++) {
      const k = a[i] + "\u0000" + b[i];
      table.set(k, (table.get(k) || 0) + 1);
      ra.set(a[i], (ra.get(a[i]) || 0) + 1);
      rb.set(b[i], (rb.get(b[i]) || 0) + 1);
    }
    const c2 = (x) => (x * (x - 1)) / 2;
    let index = 0, sa = 0, sb = 0;
    table.forEach((v) => (index += c2(v)));
    ra.forEach((v) => (sa += c2(v)));
    rb.forEach((v) => (sb += c2(v)));
    const expected = (sa * sb) / c2(n);
    const max = (sa + sb) / 2;
    return max === expected ? 1 : (index - expected) / (max - expected);
  }

  function csv(rows, columns) {
    const esc = (v) => {
      const s = v === null || v === undefined ? "" : String(v);
      return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    };
    return [columns.join(",")].concat(rows.map((r) => columns.map((c) => esc(r[c])).join(","))).join("\r\n") + "\r\n";
  }

  const api = { index, recut, genera, range, name, family, cutValue, ari, csv };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Core = api;
})(this);
