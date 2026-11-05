// Prints [from, to) of every released genus as JSON (null for unbounded).
const fs = require("fs");
const path = require("path");
const Core = require("../js/core.js");
const data = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "glottogenera.json"), "utf8"));
const ix = Core.index(data);
const out = {};
Object.entries(data.genera).forEach(([id, g]) => {
  const [lo, hi] = Core.range(ix, id, g.method);
  out[id] = [isFinite(lo) ? lo : null, isFinite(hi) ? hi : null];
});
process.stdout.write(JSON.stringify(out));
