// Prints the JavaScript recut at the thresholds given as arguments, as JSON:
// {delta: {language: genus}}. Used by tests/test_web.py.
const fs = require("fs");
const path = require("path");
const Core = require("../js/core.js");
const data = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "glottogenera.json"), "utf8"));
const ix = Core.index(data);
const out = {};
process.argv.slice(2).forEach((d) => {
  const cut = Core.recut(ix, Number(d));
  out[d] = Object.fromEntries(Object.entries(cut).map(([l, [g, m]]) => [l, [g, m]]));
});
process.stdout.write(JSON.stringify(out));
