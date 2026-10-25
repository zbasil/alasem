// The browser ports must give the same numbers as the Python models.
//   node tests/js/test_models.js            (run from the project root; also run by tests/test_app.py)
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.resolve(__dirname, "..", "..");
const ctx = { window: {}, console, Math, Float64Array, Int32Array, Int8Array, Float32Array, Blob: function () {}, URL: {}, Worker: function () {} };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(root, "app/js/models.js"), "utf8"), ctx);
const M = ctx.window.ZS.models;
let failures = 0;
const check = (cond, msg) => { if (!cond) { failures++; console.error("FAIL " + msg); } };

// 1. Dixon-Coles probabilities and the in-play model
const ref = JSON.parse(fs.readFileSync(path.join(__dirname, "reference_inplay.json"), "utf8"));
for (const d of ref.dc) {
  const p = M.outcomeProbs(M.scoreMatrix(d.lam, d.mu, d.rho));
  p.forEach((v, i) => check(Math.abs(v - d.p[i]) < 1e-9, `dc ${JSON.stringify(d)} ${p}`));
}
const ip = new M.InPlay(ref.inplay_model);
let worst = 0;
for (const c of ref.cases) {
  const p = ip.probs(c.lam, c.mu, c.minute, c.hg, c.ag, c.rh, c.ra, c.period, c.rho);
  p.forEach((v, i) => { worst = Math.max(worst, Math.abs(v - c.p[i])); check(Math.abs(v - c.p[i]) < 1e-9, `inplay ${JSON.stringify(c)} -> ${p}`); });
}
// minute 0 equals the pre-match forecast
for (const d of ref.dc) {
  const a = ip.probs(d.lam, d.mu, 0, 0, 0, 0, 0, 1, d.rho), b = M.outcomeProbs(M.scoreMatrix(d.lam, d.mu, d.rho));
  a.forEach((v, i) => check(Math.abs(v - b[i]) < 1e-12, "minute 0 differs from pre-match"));
}
console.log(`in-play port: ${ref.cases.length} states, largest difference ${worst.toExponential(2)}`);

// 2. season simulator: baseline vs the official projection (Monte Carlo agreement), scenario logic
const season = JSON.parse(fs.readFileSync(path.join(root, "app/data/season.json"), "utf8"));
const W = season.whatif;
let result = null;
const self = { postMessage: (m) => { if (m.done) result = m; } };
vm.runInNewContext("(" + M._workerMain.toString() + ")()", { self, Math, Float64Array, Int32Array, Int8Array, Float32Array, Array, Object });
const firstFix = 0;
const fx = W.fixtures[firstFix];
self.onmessage({ data: { inp: W, nSims: 6000, seed: 11, places: W.places,
  scenarios: [{ name: "base", fixed: {} }, { name: "home wins", fixed: { [firstFix]: { outcome: "H" } } }, { name: "away 0-3", fixed: { [firstFix]: { score: [0, 3] } } }] } });
check(result && result.results.length === 3, "worker returned three scenarios");
const off = Object.fromEntries(season.projection.map((r) => [r.id, r]));
let maxPts = 0, maxP = 0;
for (const r of result.results[0].rows) {
  const o = off[r.team];
  maxPts = Math.max(maxPts, Math.abs(r.exp_pts - o.exp_pts));
  for (const pl of W.places) maxP = Math.max(maxP, Math.abs(r["p_" + pl.key] - o["p_" + pl.key]));
  const tot = r.pos_dist.reduce((s, v) => s + v, 0);
  check(Math.abs(tot - 1) < 1e-9, "position distribution sums to 1");
}
console.log(`season port: largest gap to the official projection ${maxPts.toFixed(2)} points, ${(100 * maxP).toFixed(1)} percentage points`);
check(maxPts < 1.0, "expected points within 1 point of the official projection");
check(maxP < 0.035, "place probabilities within 3.5 percentage points (Monte Carlo noise)");
// a fixed home win must raise the home team's expected points by about 3 x P(not home win) on average
const home = W.team_ids[fx.h];
const b = result.results[0].rows.find((r) => r.team === home), s = result.results[1].rows.find((r) => r.team === home);
check(s.exp_pts > b.exp_pts, "a fixed home win raises the home team's expected points");
const away = W.team_ids[fx.a];
const s3 = result.results[2].rows.find((r) => r.team === away), b3 = result.results[0].rows.find((r) => r.team === away);
check(s3.exp_pts > b3.exp_pts, "a fixed away win raises the away team's expected points");
// every simulated season gives each team exactly one position
for (const sc of result.results) {
  for (let pos = 0; pos < W.teams.length; pos++) {
    const colSum = sc.rows.reduce((t, r) => t + r.pos_dist[pos], 0);
    check(Math.abs(colSum - 1) < 1e-9, `position ${pos + 1} filled exactly once in scenario ${sc.name}`);
  }
}
if (failures) { console.error(`${failures} check(s) failed`); process.exit(1); }
console.log("all JavaScript model checks passed");
