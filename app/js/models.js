/* models.js: the same maths as the Python package, ported for scenarios in the browser.
   - Dixon-Coles score matrix               (zsc/dixon_coles.py score_matrix)
   - in-play model version 2                (zsc/inplay.py InPlayModel)
   - season simulation with La Liga ties    (zsc/simulate.py + zsc/standings.py), run in a Web Worker
   Scenario numbers are always labelled as scenarios and kept apart from the official forecasts. */
(function () {
  "use strict";
  const ZS = (window.ZS = window.ZS || {});
  const MAX_GOALS = 10;

  function poissonPmf(k, lam) {
    // stable for the small rates of football
    let p = Math.exp(-lam);
    for (let i = 1; i <= k; i++) p *= lam / i;
    return p;
  }
  /** P(home = x, away = y), (G+1) x (G+1), Dixon-Coles low-score correction, renormalised */
  function scoreMatrix(lam, mu, rho, G = MAX_GOALS) {
    const ph = [], pa = [];
    for (let k = 0; k <= G; k++) { ph.push(poissonPmf(k, lam)); pa.push(poissonPmf(k, mu)); }
    const m = [];
    let s = 0;
    for (let i = 0; i <= G; i++) {
      const row = [];
      for (let j = 0; j <= G; j++) {
        let v = ph[i] * pa[j];
        if (i === 0 && j === 0) v *= 1 - lam * mu * rho;
        else if (i === 0 && j === 1) v *= 1 + lam * rho;
        else if (i === 1 && j === 0) v *= 1 + mu * rho;
        else if (i === 1 && j === 1) v *= 1 - rho;
        v = Math.max(0, v);
        row.push(v); s += v;
      }
      m.push(row);
    }
    for (const row of m) for (let j = 0; j < row.length; j++) row[j] /= s;
    return m;
  }
  function outcomeProbs(m) {
    let h = 0, d = 0, a = 0;
    for (let i = 0; i < m.length; i++) for (let j = 0; j < m[i].length; j++) {
      if (i > j) h += m[i][j]; else if (i === j) d += m[i][j]; else a += m[i][j];
    }
    return [h, d, a];
  }
  function topScores(m, k = 3) {
    const cells = [];
    for (let i = 0; i < m.length; i++) for (let j = 0; j < m[i].length; j++) cells.push([i, j, m[i][j]]);
    cells.sort((x, y) => y[2] - x[2]);
    return cells.slice(0, k);
  }

  // ------------------------------------------------------------------ in-play (version 2)
  class InPlay {
    constructor(js) {
      this.s = js.first_half_share;
      this.added = js.second_half_added ?? 5;
      const toObj = (o) => { const out = {}; for (const [k, v] of Object.entries(o || {})) out[Number(k)] = Number(v); return out; };
      this.kh = toObj(js.k_home); this.ka = toObj(js.k_away);
      this.bh = toObj(js.b_home); this.ba = toObj(js.b_away);
      this.redOwn = js.red_own; this.redOpp = js.red_opp;
      this.ramp = js.ramp ?? false;
      this.rhoMode = js.rho_mode ?? "none";
      this.version = js.version || "inplay";
    }
    get slope() { const s = this.s; return (45 - 90 * s) / (4050 * s - 1012.5); }
    cum(t) { const c = this.slope; t = Math.min(Math.max(t, 0), 90); return (t + (c * t * t) / 2) / (90 + c * 4050); }
    eff(minute, period) {
      if (period == null) period = minute <= 45 ? 1 : 2;
      if (period === 1) return Math.min(minute, 45);
      const a = this.added;
      return 45 + (Math.max(0, Math.min(minute, 90 + a) - 45) * 45) / (45 + a);
    }
    remaining(minute, period) { return 1 - this.cum(this.eff(minute, period)); }
    info(minute, period) { return this.ramp ? Math.min(1, this.cum(this.eff(minute, period)) / this.cum(45)) : 1; }
    rhoRem(rho, minute, period) {
      if (rho == null || this.rhoMode === "none") return 0;
      if (this.rhoMode === "full") return rho;
      return rho * this.remaining(minute, period);
    }
    rates(lam, mu, minute, hg, ag, rh = 0, ra = 0, period) {
      const r = this.remaining(minute, period), w = this.info(minute, period);
      const d = Math.max(-2, Math.min(2, hg - ag));
      const z = Math.log(Math.max(lam, 1e-9) / Math.max(mu, 1e-9));
      let rl = lam * r * Math.pow(this.kh[d] * Math.exp((this.bh[d] || 0) * z), w);
      let rm = mu * r * Math.pow(this.ka[d] * Math.exp((this.ba[d] || 0) * z), w);
      const man = rh - ra;
      if (man > 0) { rl *= Math.pow(this.redOwn, man); rm *= Math.pow(this.redOpp, man); }
      else if (man < 0) { rl *= Math.pow(this.redOpp, -man); rm *= Math.pow(this.redOwn, -man); }
      return [rl, rm];
    }
    /** final-score matrix offset by the current score: m[i][j] = P(final i - j) */
    finalMatrix(lam, mu, minute, hg, ag, rh = 0, ra = 0, period, rho) {
      const [rl, rm] = this.rates(lam, mu, minute, hg, ag, rh, ra, period);
      const add = scoreMatrix(rl, rm, this.rhoRem(rho, minute, period));
      const G = MAX_GOALS + Math.max(hg, ag) + 1;
      const out = Array.from({ length: G }, () => new Array(G).fill(0));
      for (let i = 0; i <= MAX_GOALS; i++) for (let j = 0; j <= MAX_GOALS; j++) out[hg + i][ag + j] = add[i][j];
      return out;
    }
    probs(lam, mu, minute, hg, ag, rh = 0, ra = 0, period, rho) {
      return outcomeProbs(this.finalMatrix(lam, mu, minute, hg, ag, rh, ra, period, rho));
    }
  }

  // ------------------------------------------------------------------ season simulator (worker)
  // Same structure as zsc/simulate.py: parameter draws carry the season "drift" (form, injuries, transfers),
  // each draw is simulated several times; every remaining match gets ONE uniform random number per season, so a
  // scenario and its baseline share all other results (common random numbers) and the difference is the scenario.
  function workerMain() {
    /* eslint-disable no-restricted-globals */
    function mulberry32(a) { return function () { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
    function gauss(rng) { let u = 0, v = 0; while (u === 0) u = rng(); v = rng(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }
    function pmf(k, l) { let p = Math.exp(-l); for (let i = 1; i <= k; i++) p *= l / i; return p; }
    const G = 11;
    function cdfFor(lam, mu, rho, out) {
      const ph = new Float64Array(G), pa = new Float64Array(G);
      for (let k = 0; k < G; k++) { ph[k] = pmf(k, lam); pa[k] = pmf(k, mu); }
      let s = 0;
      for (let i = 0; i < G; i++) for (let j = 0; j < G; j++) {
        let v = ph[i] * pa[j];
        if (i === 0 && j === 0) v *= 1 - lam * mu * rho; else if (i === 0 && j === 1) v *= 1 + lam * rho;
        else if (i === 1 && j === 0) v *= 1 + mu * rho; else if (i === 1 && j === 1) v *= 1 - rho;
        if (v < 0) v = 0;
        s += v; out[i * G + j] = s;
      }
      for (let k = 0; k < G * G; k++) out[k] /= s;
      out[G * G - 1] = 1;
    }
    // La Liga ranking: points; head-to-head (when every pair met twice: 2 teams -> h2h goal difference, 3+ -> mini
    // league points then mini goal difference, restarting for still-tied subgroups); goal difference; goals for;
    // a random key standing in for fair play.
    function split(g, val) {
      const o = g.slice().sort((a, b) => val[b] - val[a]);
      const parts = []; let cur = [o[0]];
      for (let k = 1; k < o.length; k++) { if (val[o[k]] === val[cur[cur.length - 1]]) cur.push(o[k]); else { parts.push(cur); cur = [o[k]]; } }
      parts.push(cur); return parts;
    }
    function rank(n, pts, gd, gf, hp, hg, key) {
      const overall = (g) => {
        for (const val of [gd, gf, key]) { const parts = split(g, val); if (parts.length > 1) { const out = []; for (const p of parts) out.push(...(p.length > 1 ? overall(p) : p)); return out; } }
        return g.slice();
      };
      const resolve = (g) => {
        if (g.length === 1) return g.slice();
        if (g.length === 2) {
          const [i, j] = g; const d = hg[i * n + j] - hg[j * n + i];
          if (d !== 0) return d > 0 ? [i, j] : [j, i];
          return overall(g);
        }
        const mp = new Float64Array(n), md = new Float64Array(n);
        for (const i of g) for (const j of g) if (i !== j) { mp[i] += hp[i * n + j]; md[i] += hg[i * n + j] - hg[j * n + i]; }
        for (const val of [mp, md]) { const parts = split(g, val); if (parts.length > 1) { const out = []; for (const p of parts) out.push(...resolve(p)); return out; } }
        return overall(g);
      };
      const all = Array.from({ length: n }, (_, i) => i);
      const order = [];
      for (const grp of split(all, pts)) order.push(...resolve(grp));
      return order;
    }
    self.onmessage = (ev) => {
      const { inp, scenarios, nSims, seed, places } = ev.data;
      const n = inp.teams.length, F = inp.fixtures.length;
      const draws = Math.max(1, Math.min(500, nSims));
      const per = Math.ceil(nSims / draws);
      const total = draws * per;
      const sd = inp.drift_sd * Math.sqrt(inp.share_left) * (inp.scale || 1);
      const rngDrift = mulberry32(seed ^ 0x9e3779b9);
      const rngGoals = mulberry32(seed);
      const rngKey = mulberry32(seed ^ 0x51ed27);
      const S = scenarios.length; // scenario 0 is the baseline (no fixed results)
      // fixed[s][f] = -1 (simulate) or a cell index, or an outcome constraint {H,D,A}
      const fixed = scenarios.map((sc) => {
        const arr = new Int32Array(F).fill(-1), oc = new Int8Array(F).fill(0);
        for (const [fi, v] of Object.entries(sc.fixed || {})) {
          if (v.score) arr[fi] = v.score[0] * G + v.score[1];
          else if (v.outcome) oc[fi] = { H: 1, D: 2, A: 3 }[v.outcome];
        }
        return { arr, oc };
      });
      const posCount = scenarios.map(() => new Float64Array(n * n));
      const ptsSum = scenarios.map(() => new Float64Array(n));
      const ptsAll = scenarios.map(() => Array.from({ length: n }, () => new Float32Array(total)));
      const cdf = new Float64Array(F * G * G);
      const tmp = new Float64Array(G * G);
      const att = new Float64Array(n), dfn = new Float64Array(n);
      const pts = new Int32Array(n), gf = new Int32Array(n), ga = new Int32Array(n), gd = new Int32Array(n);
      const hp = new Int32Array(n * n), hgm = new Int32Array(n * n);
      const key = new Float64Array(n);
      const u = new Float64Array(F);
      let sIdx = 0;
      for (let b = 0; b < draws; b++) {
        for (let t = 0; t < n; t++) { att[t] = inp.attack[t] + sd * gauss(rngDrift); dfn[t] = inp.defence[t] + sd * gauss(rngDrift); }
        for (let f = 0; f < F; f++) {
          const fx = inp.fixtures[f];
          const lam = Math.exp(inp.c + inp.h + att[fx.h] - dfn[fx.a]);
          const mu = Math.exp(inp.c + att[fx.a] - dfn[fx.h]);
          cdfFor(lam, mu, inp.rho, tmp);
          cdf.set(tmp, f * G * G);
        }
        for (let r = 0; r < per; r++, sIdx++) {
          for (let f = 0; f < F; f++) u[f] = rngGoals();
          for (let t = 0; t < n; t++) key[t] = rngKey();
          for (let s = 0; s < S; s++) {
            pts.set(inp.pts); gf.set(inp.gf); ga.set(inp.ga);
            for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) { hp[i * n + j] = inp.h2h_pts[i][j]; hgm[i * n + j] = inp.h2h_gf[i][j]; }
            const fxd = fixed[s];
            for (let f = 0; f < F; f++) {
              const fx = inp.fixtures[f];
              let cell = fxd.arr[f];
              if (cell < 0) {
                const base = f * G * G;
                const oc = fxd.oc[f];
                if (oc) {
                  // inverse CDF restricted to the chosen outcome, with the same uniform number
                  let tot = 0, prev = 0;
                  const ok = (k) => { const x = (k / G) | 0, y = k % G; return oc === 1 ? x > y : oc === 2 ? x === y : x < y; };
                  for (let k = 0; k < G * G; k++) { const p = cdf[base + k] - prev; prev = cdf[base + k]; if (ok(k)) tot += p; }
                  let target = u[f] * tot, acc = 0; prev = 0; cell = 0;
                  for (let k = 0; k < G * G; k++) { const p = cdf[base + k] - prev; prev = cdf[base + k]; if (ok(k)) { acc += p; cell = k; if (acc >= target) break; } }
                } else {
                  let lo = 0, hi = G * G - 1;
                  while (lo < hi) { const mid = (lo + hi) >> 1; if (cdf[base + mid] < u[f]) lo = mid + 1; else hi = mid; }
                  cell = lo;
                }
              }
              const x = (cell / G) | 0, y = cell % G;
              const i = fx.h, j = fx.a;
              const pi = x > y ? 3 : x === y ? 1 : 0, pj = x < y ? 3 : x === y ? 1 : 0;
              pts[i] += pi; pts[j] += pj; gf[i] += x; ga[i] += y; gf[j] += y; ga[j] += x;
              hp[i * n + j] += pi; hp[j * n + i] += pj; hgm[i * n + j] += x; hgm[j * n + i] += y;
            }
            for (let t = 0; t < n; t++) gd[t] = gf[t] - ga[t];
            const order = rank(n, pts, gd, gf, hp, hgm, key);
            for (let pos = 0; pos < n; pos++) posCount[s][order[pos] * n + pos] += 1;
            for (let t = 0; t < n; t++) { ptsSum[s][t] += pts[t]; ptsAll[s][t][sIdx] = pts[t]; }
          }
        }
        if (b % 50 === 49) self.postMessage({ progress: (b + 1) / draws });
      }
      const out = scenarios.map((sc, s) => {
        const rows = [];
        for (let t = 0; t < n; t++) {
          const dist = []; for (let p = 0; p < n; p++) dist.push(posCount[s][t * n + p] / total);
          const sorted = Array.from(ptsAll[s][t]).sort((a, b) => a - b);
          const row = { team: inp.team_ids ? inp.team_ids[t] : inp.teams[t], exp_pts: ptsSum[s][t] / total, pos_dist: dist,
            pts_p10: sorted[Math.floor(0.1 * (total - 1))], pts_p90: sorted[Math.floor(0.9 * (total - 1))] };
          for (const pl of places) { let v = 0; for (let p = pl.from; p <= pl.to; p++) v += dist[p - 1]; row["p_" + pl.key] = v; }
          rows.push(row);
        }
        return { name: sc.name, rows };
      });
      self.postMessage({ done: true, results: out, nSims: total });
    };
  }
  let workerUrl = null;
  function seasonWorker() {
    if (!workerUrl) {
      const src = "(" + workerMain.toString() + ")();";
      workerUrl = URL.createObjectURL(new Blob([src], { type: "text/javascript" }));
    }
    return new Worker(workerUrl);
  }
  /** run the season simulator; scenarios: [{name, fixed: {fixtureIndex: {score:[h,a]} | {outcome:'H'|'D'|'A'}}}] */
  function simulateSeason(inp, scenarios, { nSims = 10000, seed = 2026, onProgress } = {}) {
    return new Promise((resolve, reject) => {
      let w;
      try { w = seasonWorker(); } catch (e) { reject(e); return; }
      w.onmessage = (ev) => {
        if (ev.data.progress && onProgress) onProgress(ev.data.progress);
        if (ev.data.done) { w.terminate(); resolve(ev.data); }
      };
      w.onerror = (e) => { w.terminate(); reject(new Error(e.message || "worker failed")); };
      w.postMessage({ inp, scenarios, nSims, seed, places: inp.places });
    });
  }

  ZS.models = { scoreMatrix, outcomeProbs, topScores, InPlay, simulateSeason, MAX_GOALS, _workerMain: workerMain };
})();
