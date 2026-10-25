/* charts.js: small SVG charts drawn by hand (no library).
   Time runs from right to left (kick-off on the right), the reading direction of the app.
   Every chart labels its values in text as well as colour. */
(function () {
  "use strict";
  const ZS = window.ZS;
  const { h, svgEl, esc, pct, num } = ZS;

  const f1 = (x) => (Math.round(x * 10) / 10).toString();

  // ------------------------------------------------------------------ win-probability timeline
  /**
   * rows: [{minute, p_home, p_draw, p_away, hg, ag}] (probabilities 0..1)
   * events: [{minute, kind: 'goal'|'red', team: 'home'|'away'}]
   * returns {el, select(minute)}; onSelect(minute) fires on click, drag or arrow keys
   */
  function timeline({ rows, events = [], colours, names, onSelect, selected = null, height = 230, xgRows = null }) {
    const W = 760, H = height, padT = 26, padB = 30, padL = 40, padR = 14;
    const maxMin = Math.max(90, rows[rows.length - 1].minute);
    const x = (m) => W - padR - ((W - padR - padL) * m) / maxMin; // right to left
    const y = (p) => padT + (H - padT - padB) * (1 - p);
    const [hc, ac] = colours;
    // stacked areas: home at the bottom, draw in the middle, away on top
    const ptsH = rows.map((r) => [x(r.minute), y(r.p_home)]);
    const ptsD = rows.map((r) => [x(r.minute), y(r.p_home + r.p_draw)]);
    const path = (top, bottom) => "M" + top.map((p) => p.map(f1).join(",")).join("L") + "L" + bottom.slice().reverse().map((p) => p.map(f1).join(",")).join("L") + "Z";
    const base = rows.map((r) => [x(r.minute), y(0)]);
    const roof = rows.map((r) => [x(r.minute), y(1)]);
    let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="تطور احتمالات الفوز خلال المباراة" tabindex="0">`;
    svg += `<path d="${path(ptsH, base)}" fill="${hc}" fill-opacity=".85"/>`;
    svg += `<path d="${path(ptsD, ptsH)}" fill="var(--draw)" fill-opacity=".55"/>`;
    svg += `<path d="${path(roof, ptsD)}" fill="${ac}" fill-opacity=".85"/>`;
    // grid
    for (const p of [0.25, 0.5, 0.75]) svg += `<line x1="${padL}" x2="${W - padR}" y1="${f1(y(p))}" y2="${f1(y(p))}" stroke="var(--bg)" stroke-opacity=".55" stroke-dasharray="3 4"/>`;
    for (const p of [0, 0.5, 1]) svg += `<text x="${padL - 6}" y="${f1(y(p) + 4)}" text-anchor="end" direction="ltr">${Math.round(p * 100)}%</text>`;
    for (const m of [0, 15, 30, 45, 60, 75, 90]) {
      svg += `<line x1="${f1(x(m))}" x2="${f1(x(m))}" y1="${H - padB}" y2="${H - padB + 5}" stroke="var(--line-strong)"/>`;
      svg += `<text x="${f1(x(m))}" y="${H - padB + 18}" text-anchor="middle" direction="ltr">${m}'</text>`;
    }
    svg += `<line x1="${f1(x(45))}" x2="${f1(x(45))}" y1="${padT}" y2="${H - padB}" stroke="var(--fg)" stroke-opacity=".35" stroke-width="1.5"/>`;
    svg += `<text x="${f1(x(45))}" y="${padT - 8}" text-anchor="middle">الاستراحة</text>`;
    // events on the top edge
    for (const e of events) {
      const ex = x(e.minute);
      const col = e.team === "home" ? hc : ac;
      svg += `<line x1="${f1(ex)}" x2="${f1(ex)}" y1="${padT}" y2="${H - padB}" stroke="var(--fg)" stroke-opacity=".55" stroke-width="1"/>`;
      if (e.kind === "goal") svg += `<circle cx="${f1(ex)}" cy="${padT - 10}" r="6" fill="${col}" stroke="var(--fg)" stroke-width="1.5"><title>هدف ${e.minute}'</title></circle>`;
      else svg += `<rect x="${f1(ex - 4)}" y="${padT - 17}" width="8" height="11" rx="1.5" fill="var(--bad)" stroke="var(--fg)" stroke-width="1"><title>طرد ${e.minute}'</title></rect>`;
    }
    svg += `<g class="cursor" visibility="hidden"><line y1="${padT}" y2="${H - padB}" stroke="var(--led)" stroke-width="2.5"/><circle r="5" fill="var(--led)" cy="${padT}"/></g>`;
    svg += `<rect class="hit" x="${padL}" y="${padT}" width="${W - padL - padR}" height="${H - padT - padB}" fill="transparent" style="cursor:crosshair"/>`;
    svg += `</svg>`;
    const wrap = h("div.chart.tl-wrap");
    wrap.innerHTML = svg;
    const s = wrap.querySelector("svg");
    const cur = s.querySelector(".cursor");
    const byMin = new Map(rows.map((r) => [r.minute, r]));
    let sel = selected;
    function select(m, fire = true) {
      m = Math.max(0, Math.min(rows[rows.length - 1].minute, Math.round(m)));
      sel = m;
      cur.setAttribute("visibility", "visible");
      cur.querySelector("line").setAttribute("x1", f1(x(m)));
      cur.querySelector("line").setAttribute("x2", f1(x(m)));
      cur.querySelector("circle").setAttribute("cx", f1(x(m)));
      if (fire && onSelect) onSelect(m, byMin.get(m));
    }
    function fromEvent(ev) {
      const r = s.getBoundingClientRect();
      const px = ((ev.clientX - r.left) / r.width) * W;
      return ((W - padR - px) / (W - padR - padL)) * maxMin;
    }
    let dragging = false;
    s.addEventListener("pointerdown", (ev) => { dragging = true; s.setPointerCapture(ev.pointerId); select(fromEvent(ev)); });
    s.addEventListener("pointermove", (ev) => { if (dragging) select(fromEvent(ev)); });
    s.addEventListener("pointerup", () => { dragging = false; });
    s.addEventListener("keydown", (ev) => {
      if (sel === null) sel = 0;
      if (ev.key === "ArrowLeft") { select(sel + 1); ev.preventDefault(); }       // later (time runs right to left)
      else if (ev.key === "ArrowRight") { select(sel - 1); ev.preventDefault(); }
      else if (ev.key === "End") { select(rows[rows.length - 1].minute); ev.preventDefault(); }
      else if (ev.key === "Home") { select(0); ev.preventDefault(); }
    });
    if (sel !== null) select(sel, false);
    const legend = h("div.legend-row", { style: { marginTop: "6px" } },
      h("span", h("i", { style: { background: hc } }), `فوز ${names[0]}`),
      h("span", h("i", { style: { background: "var(--draw)" } }), "تعادل"),
      h("span", h("i", { style: { background: ac } }), `فوز ${names[1]}`),
      h("span.faint", "الوقت يمشي من اليمين (البداية) لليسار"));
    wrap.appendChild(legend);
    return { el: wrap, select };
  }

  // ------------------------------------------------------------------ sparkline / lines
  function lines({ series, height = 150, yFormat = (v) => num(v, 2), xLabels = [], refLine = null, ariaLabel = "" }) {
    const W = 520, H = height, padT = 14, padB = 24, padL = 42, padR = 10;
    const all = series.flatMap((s) => s.values).filter((v) => ZS.isNum(v));
    if (!all.length) return h("div.empty", "ماكو بيانات كافية");
    let lo = Math.min(...all, refLine ?? Infinity), hi = Math.max(...all, refLine ?? -Infinity);
    if (hi - lo < 1e-6) { hi += 0.5; lo -= 0.5; }
    const padV = (hi - lo) * 0.12; lo -= padV; hi += padV;
    const n = Math.max(...series.map((s) => s.values.length));
    const x = (i) => W - padR - ((W - padR - padL) * i) / Math.max(1, n - 1); // oldest on the right
    const y = (v) => padT + (H - padT - padB) * (1 - (v - lo) / (hi - lo));
    let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(ariaLabel)}">`;
    for (const t of [lo + padV, (lo + hi) / 2, hi - padV]) {
      svg += `<line x1="${padL}" x2="${W - padR}" y1="${f1(y(t))}" y2="${f1(y(t))}" class="grid-line" stroke-dasharray="2 4"/>`;
      svg += `<text x="${padL - 6}" y="${f1(y(t) + 4)}" text-anchor="end" direction="ltr">${esc(yFormat(t))}</text>`;
    }
    if (refLine !== null) svg += `<line x1="${padL}" x2="${W - padR}" y1="${f1(y(refLine))}" y2="${f1(y(refLine))}" stroke="var(--fg-3)" stroke-width="1.2"/>`;
    for (const s of series) {
      const pts = s.values.map((v, i) => (ZS.isNum(v) ? [x(i), y(v)] : null)).filter(Boolean);
      if (!pts.length) continue;
      svg += `<polyline points="${pts.map((p) => p.map(f1).join(",")).join(" ")}" fill="none" stroke="${s.color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" ${s.dash ? 'stroke-dasharray="5 4"' : ""}/>`;
      const last = pts[pts.length - 1];
      svg += `<circle cx="${f1(last[0])}" cy="${f1(last[1])}" r="4.5" fill="${s.color}" stroke="var(--card)" stroke-width="2"/>`;
    }
    xLabels.forEach((lab, i) => {
      if (!lab) return;
      svg += `<text x="${f1(x(i))}" y="${H - 6}" text-anchor="middle">${esc(lab)}</text>`;
    });
    svg += `</svg>`;
    const wrap = h("div.chart");
    wrap.innerHTML = svg;
    const legend = h("div.legend-row", series.map((s) => h("span", h("i", { style: { background: s.color } }), s.name)));
    wrap.appendChild(legend);
    return wrap;
  }

  // ------------------------------------------------------------------ calibration
  function calibration(bins, { color = "var(--pitch)", label = "" } = {}) {
    const W = 360, H = 300, pad = 42;
    const sx = (v) => pad + (W - pad - 12) * v;
    const sy = (v) => H - pad - (H - pad - 12) * v;
    let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label || "المعايرة")}">`;
    for (const t of [0, 0.25, 0.5, 0.75, 1]) {
      svg += `<line x1="${sx(0)}" x2="${sx(1)}" y1="${f1(sy(t))}" y2="${f1(sy(t))}" class="grid-line"/>`;
      svg += `<text x="${pad - 6}" y="${f1(sy(t) + 4)}" text-anchor="end" direction="ltr">${t * 100}%</text>`;
      svg += `<text x="${f1(sx(t))}" y="${H - pad + 16}" text-anchor="middle" direction="ltr">${t * 100}%</text>`;
    }
    svg += `<line x1="${sx(0)}" y1="${sy(0)}" x2="${sx(1)}" y2="${sy(1)}" stroke="var(--fg-3)" stroke-dasharray="4 4"/>`;
    for (const b of bins) {
      if (!b.n) continue;
      svg += `<line x1="${f1(sx(b.forecast))}" x2="${f1(sx(b.forecast))}" y1="${f1(sy(b.obs_low))}" y2="${f1(sy(b.obs_high))}" stroke="${color}" stroke-width="2" stroke-opacity=".6"/>`;
      const r = Math.max(3.5, Math.min(9, Math.sqrt(b.n) / 3.2));
      svg += `<circle cx="${f1(sx(b.forecast))}" cy="${f1(sy(b.observed))}" r="${f1(r)}" fill="${color}" stroke="var(--card)" stroke-width="1.5"><title>توقع ${pct(b.forecast)} ← صار ${pct(b.observed)} (${b.n} احتمال)</title></circle>`;
    }
    svg += `<text x="${(W + pad) / 2}" y="${H - 6}" text-anchor="middle">الاحتمال اللي گاله الموديل</text>`;
    svg += `<text x="12" y="${(H - pad) / 2}" text-anchor="middle" transform="rotate(-90 12 ${(H - pad) / 2})">اللي صار فعلاً</text>`;
    svg += `</svg>`;
    const wrap = h("div.chart");
    wrap.innerHTML = svg;
    return wrap;
  }

  // ------------------------------------------------------------------ mirrored stat bars
  function mirrorBars(rows, colours, { names } = {}) {
    // rows: [{label, home, away, fmt}] ; missing values stay missing
    return h("div.stack", { style: { gap: "10px" } }, rows.map((r) => {
      const hv = r.home, av = r.away;
      const known = ZS.isNum(hv) && ZS.isNum(av);
      const tot = known ? Math.max(hv + av, 1e-9) : 1;
      const fmt = r.fmt || ((v) => num(v, Number.isInteger(v) ? 0 : 1));
      return h("div", { style: { display: "grid", gap: "4px" } },
        h("div.row-between.small", { style: { fontWeight: 700 } },
          h("span.num", known || ZS.isNum(hv) ? fmt(hv) : missing()),
          h("span.muted", r.label),
          h("span.num", known || ZS.isNum(av) ? fmt(av) : missing())),
        known ? h("div", { style: { display: "flex", gap: "3px", height: "8px" } },
          h("i", { style: { flex: `${hv / tot} 1 0`, background: colours[0], borderRadius: "4px", minWidth: hv > 0 ? "3px" : "0" } }),
          h("i", { style: { flex: `${av / tot} 1 0`, background: colours[1], borderRadius: "4px", minWidth: av > 0 ? "3px" : "0" } }))
          : h("div.tiny.faint", "غير متوفر من المصدر"));
    }));
  }
  function missing(reason) { return h("span.missing", { title: reason || "غير متوفر من المصدر" }, "—"); }

  // ------------------------------------------------------------------ pitch (StatsBomb 120 x 80)
  function pitchBase(W = 120, H = 80) {
    const l = 'stroke="rgba(255,255,255,.75)" stroke-width=".45" fill="none"';
    return `<rect x="0" y="0" width="${W}" height="${H}" fill="rgba(0,0,0,.06)"/>` +
      `<rect x=".3" y=".3" width="${W - .6}" height="${H - .6}" ${l}/>` +
      `<line x1="60" y1="0" x2="60" y2="80" ${l}/><circle cx="60" cy="40" r="10" ${l}/>` +
      `<rect x="0" y="18" width="18" height="44" ${l}/><rect x="102" y="18" width="18" height="44" ${l}/>` +
      `<rect x="0" y="30" width="6" height="20" ${l}/><rect x="114" y="30" width="6" height="20" ${l}/>` +
      `<circle cx="12" cy="40" r=".5" fill="rgba(255,255,255,.8)"/><circle cx="108" cy="40" r=".5" fill="rgba(255,255,255,.8)"/>` +
      `<path d="M18 32 A10 10 0 0 1 18 48" ${l}/><path d="M102 32 A10 10 0 0 0 102 48" ${l}/>`;
  }
  /** shots: home shoots at the LEFT goal (the app reads right to left), away at the right goal */
  function shotMap(shots, colours, { onPick, label } = {}) {
    let svg = `<svg viewBox="-2 -2 124 84" role="img" aria-label="${esc(label || "خريطة التسديدات")}">` + pitchBase();
    shots.forEach((s, i) => {
      const home = s.side === "home";
      const px = home ? 120 - s.x : s.x, py = home ? 80 - s.y : s.y;
      const r = 0.9 + Math.sqrt(Math.max(s.xg, 0.005)) * 4.2;
      const col = home ? colours[0] : colours[1];
      svg += `<circle data-i="${i}" cx="${f1(px)}" cy="${f1(py)}" r="${f1(r)}" fill="${s.is_goal ? col : "none"}" stroke="${col}" stroke-width="${s.is_goal ? 0.6 : 0.8}" fill-opacity=".9" style="cursor:pointer"><title>${esc(s.player_ar)} ${s.minute}' · xG ${s.xg.toFixed(2)}${s.is_goal ? " · هدف" : ""}</title></circle>`;
    });
    svg += `</svg>`;
    const wrap = h("div.pitch-wrap");
    wrap.innerHTML = svg;
    if (onPick) wrap.querySelector("svg").addEventListener("click", (ev) => {
      const c = ev.target.closest("circle[data-i]");
      if (c) onPick(shots[Number(c.dataset.i)]);
    });
    return wrap;
  }
  /** touch heat map: grid {nx, ny, cells[ny][nx]} on the 120 x 80 pitch; mirror for the home side */
  function heatmap(grid, colour, { mirror = false, label } = {}) {
    const { nx, ny, cells } = grid;
    const cw = 120 / nx, ch = 80 / ny;
    let mx = 0;
    for (const row of cells) for (const v of row) mx = Math.max(mx, v);
    let svg = `<svg viewBox="-2 -2 124 84" role="img" aria-label="${esc(label || "خريطة اللمسات")}">`;
    svg += `<rect x="0" y="0" width="120" height="80" fill="rgba(0,0,0,.06)"/>`;
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      const v = cells[j][i];
      if (!v) continue;
      const a = Math.pow(v / mx, 0.75);
      const x = mirror ? 120 - (i + 1) * cw : i * cw, y = mirror ? 80 - (j + 1) * ch : j * ch;
      svg += `<rect x="${f1(x)}" y="${f1(y)}" width="${f1(cw)}" height="${f1(ch)}" fill="${colour}" fill-opacity="${(0.08 + 0.85 * a).toFixed(2)}"/>`;
    }
    svg += pitchBase().replace('<rect x="0" y="0" width="120" height="80" fill="rgba(0,0,0,.06)"/>', "");
    svg += `</svg>`;
    const wrap = h("div.pitch-wrap");
    wrap.innerHTML = svg;
    return wrap;
  }
  function passNetwork(nodes, edges, colour, { mirror = false, onPick } = {}) {
    const P = (x, y) => (mirror ? [120 - x, 80 - y] : [x, y]);
    const mxE = Math.max(1, ...edges.map((e) => e.passes));
    const mxT = Math.max(1, ...nodes.map((n) => n.touches));
    let svg = `<svg viewBox="-2 -2 124 84" role="img" aria-label="شبكة التمريرات">` + pitchBase();
    for (const e of edges) {
      const [x1, y1] = P(e.x1, e.y1), [x2, y2] = P(e.x2, e.y2);
      svg += `<line x1="${f1(x1)}" y1="${f1(y1)}" x2="${f1(x2)}" y2="${f1(y2)}" stroke="${colour}" stroke-opacity="${(0.25 + 0.7 * e.passes / mxE).toFixed(2)}" stroke-width="${(0.3 + 2.2 * e.passes / mxE).toFixed(2)}" stroke-linecap="round"><title>${esc(e.a_ar)} ↔ ${esc(e.b_ar)}: ${e.passes} تمريرة</title></line>`;
    }
    nodes.forEach((n, i) => {
      const [x, y] = P(n.x, n.y);
      const r = 1.6 + 2.6 * Math.sqrt(n.touches / mxT);
      svg += `<g data-i="${i}" style="cursor:pointer"><circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(r)}" fill="${colour}" stroke="#fff" stroke-width=".5"/>` +
        `<text x="${f1(x)}" y="${f1(y + 0.9)}" text-anchor="middle" font-size="2.6" font-weight="800" style="fill:${ZS.inkOn(colour)}">${n.number ?? ""}</text>` +
        `<text x="${f1(x)}" y="${f1(y + r + 3)}" text-anchor="middle" font-size="2.7" font-weight="700" style="fill:#fff;paint-order:stroke;stroke:rgba(0,0,0,.6);stroke-width:.6px">${esc(n.player_ar)}</text>` +
        `<title>${esc(n.player_ar)}: ${n.touches} لمسة</title></g>`;
    });
    svg += `</svg>`;
    const wrap = h("div.pitch-wrap");
    wrap.innerHTML = svg;
    if (onPick) wrap.querySelector("svg").addEventListener("click", (ev) => {
      const g = ev.target.closest("g[data-i]");
      if (g) onPick(nodes[Number(g.dataset.i)]);
    });
    return wrap;
  }

  // ------------------------------------------------------------------ position distribution
  function posDist(dist, { places = [] } = {}) {
    const zone = (pos) => {
      for (const pl of places) if (pl.key !== "title" && pos >= pl.from && pos <= pl.to) return pl.key;
      return "";
    };
    const colourOf = { ucl: "var(--ucl)", uel: "var(--uel)", uecl: "var(--uecl)", releg: "var(--releg)", "": "var(--fg-3)" };
    const mx = Math.max(...dist, 0.0001);
    return h("div.heat-row", { role: "img", "aria-label": "توزيع المراكز المتوقعة" },
      dist.map((p, i) => h("i", {
        title: `المركز ${i + 1}: ${pct(p, p < 0.01 && p > 0 ? 1 : 0)}`,
        style: { background: colourOf[zone(i + 1)], opacity: p === 0 ? 0.06 : (0.15 + 0.85 * Math.sqrt(p / mx)).toFixed(2) },
      })));
  }

  // ------------------------------------------------------------------ score grid (pre-match score probabilities)
  function scoreGrid(matrix, colours, { max = 5, names = ["", ""] } = {}) {
    let mx = 0;
    for (let i = 0; i <= max; i++) for (let j = 0; j <= max; j++) mx = Math.max(mx, matrix[i][j]);
    const grid = h("div.sgrid", { style: { gridTemplateColumns: `28px repeat(${max + 1}, minmax(0, 1fr))` }, role: "table", "aria-label": "احتمال كل نتيجة" });
    grid.appendChild(h("div.h", ""));
    for (let j = 0; j <= max; j++) grid.appendChild(h("div.h", String(j)));
    for (let i = 0; i <= max; i++) {
      grid.appendChild(h("div.h", String(i)));
      for (let j = 0; j <= max; j++) {
        const p = matrix[i][j];
        const col = i > j ? colours[0] : i === j ? "var(--draw)" : colours[1];
        grid.appendChild(h("div.c", {
          title: `${names[0]} ${i} – ${j} ${names[1]}: ${pct(p, 1)}`,
          style: { background: `color-mix(in srgb, ${col} ${Math.round(8 + 80 * Math.sqrt(p / mx))}%, var(--card-2))` },
        }, p >= 0.005 ? (100 * p).toFixed(0) : ""));
      }
    }
    return grid;
  }

  ZS.charts = { timeline, lines, calibration, mirrorBars, missing, shotMap, heatmap, passNetwork, posDist, scoreGrid, pitchBase };
})();
