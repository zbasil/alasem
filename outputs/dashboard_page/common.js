window.ZS = (function () {
  const C = dash.colors;
  const root = document.querySelector('.zs');
  const H = C[0], A = C[1], D = 'var(--cds-chart-muted)', BAD = 'var(--cds-chart-status-critical)';
  root.style.setProperty('--z-ucl', C[0]);
  root.style.setProperty('--z-eur', C[2]);

  function setKeys(scope) {
    (scope || root).querySelectorAll('.k-h').forEach((e) => e.style.setProperty('--k', H));
    (scope || root).querySelectorAll('.k-a').forEach((e) => e.style.setProperty('--k', A));
    (scope || root).querySelectorAll('.k-d').forEach((e) => e.style.setProperty('--k', D));
    (scope || root).querySelectorAll('.k-ucl').forEach((e) => e.style.setProperty('--k', C[0]));
    (scope || root).querySelectorAll('.k-eur').forEach((e) => e.style.setProperty('--k', C[2]));
    (scope || root).querySelectorAll('.k-rel').forEach((e) => e.style.setProperty('--k', BAD));
  }
  setKeys();

  const clear = (el) => { if (el) while (el.firstChild) el.removeChild(el.firstChild); };
  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = String(text);
    return e;
  }
  const num = (v) => (v === null || v === undefined || v === '' || isNaN(Number(v))) ? null : Number(v);
  const fmt = (v, nd) => { const n = num(v); return n === null ? '—' : n.toFixed(nd || 0); };
  function rows(id) {
    const d = dash.data(id);
    return d.status === 'ok' && Array.isArray(d.data) ? d.data : null;
  }
  function done(e) { if (e) e.classList.remove('dash-skeleton'); }
  // fill every single-value mark (data-row or data-where) outside tables
  function fillMarks(scope) {
    if (!scope) return;
    scope.querySelectorAll('[data-source][data-field]').forEach((e) => {
      if (e.closest('table')) return;
      const d = dash.data(e.dataset.source);
      if (d.status !== 'ok') { e.textContent = '—'; if (d.status !== 'loading') done(e); return; }
      done(e);
      const rs = Array.isArray(d.data) ? d.data : [];
      let row;
      if (e.dataset.where) {
        const conds = e.dataset.where.split('&').map((kv) => kv.split('=').map((s) => decodeURIComponent(s)));
        row = rs.find((r) => conds.every(([k, v]) => String(r[k]) === v));
      } else row = rs[Number(e.dataset.row || 0)];
      const v = row ? row[e.dataset.field] : null;
      e.textContent = v === null || v === undefined || v === '' ? '—' : String(v);
    });
  }
  function fail(host, id) {
    const st = dash.data(id).status;
    clear(host);
    if (st === 'error' || st === 'connect') host.appendChild(el('div', 'fail', 'Failed to load'));
    if (st !== 'loading') done(host);
  }
  function computed(color) {
    const p = document.createElement('span');
    p.style.color = color; p.style.display = 'none';
    root.appendChild(p);
    const c = getComputedStyle(p).color;
    root.removeChild(p);
    return c;
  }

  // three-way probability bar (home on the right in RTL)
  function probBar(ph, pd, pa) {
    const bar = el('div', 'pbar');
    [[ph, H], [pd, D], [pa, A]].forEach(([v, c]) => {
      const n = num(v) || 0;
      const s = el('div');
      s.style.width = n + '%';
      s.style.background = c;
      s.textContent = n >= 12 ? Math.round(n) + '%' : '';
      bar.appendChild(s);
    });
    return bar;
  }

  // tooltip inside a chart box
  function tip(host) {
    let t = host.querySelector(':scope > .tip');
    if (!t) { t = el('div', 'tip'); host.appendChild(t); }
    return {
      show(ev, lines) {
        clear(t);
        lines.forEach((ln, i) => t.appendChild(el('div', i === 0 ? 't2' : '', ln)));
        const box = host.getBoundingClientRect();
        t.style.opacity = 1;
        const w = t.offsetWidth || 150;
        const left = Math.min(Math.max(0, ev.clientX - box.left + 12), Math.max(0, box.width - w));
        t.style.left = left + 'px';
        t.style.top = Math.max(0, ev.clientY - box.top + 12) + 'px';
      },
      hide() { t.style.opacity = 0; },
    };
  }

  // football pitch 120 x 80 (StatsBomb yards); returns {svg, g, sx, sy}
  function pitch(host, width) {
    const W = Math.max(260, width), Hh = W * 80 / 120;
    const svg = d3.select(host).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${Hh}`)
      .attr('role', 'img');
    const sx = d3.scaleLinear([0, 120], [0, W]);
    const sy = d3.scaleLinear([0, 80], [0, Hh]);
    const g = svg.append('g');
    const line = 'var(--cds-chart-axis)';
    g.append('rect').attr('x', 0).attr('y', 0).attr('width', W).attr('height', Hh).attr('rx', 6)
      .style('fill', 'var(--color-bg)').style('stroke', line);
    const L = (x1, y1, x2, y2) => g.append('line').attr('x1', sx(x1)).attr('y1', sy(y1)).attr('x2', sx(x2)).attr('y2', sy(y2))
      .style('stroke', line).style('stroke-width', 1);
    const R = (x, y, w, h) => g.append('rect').attr('x', sx(x)).attr('y', sy(y)).attr('width', sx(w) - sx(0)).attr('height', sy(h) - sy(0))
      .style('fill', 'none').style('stroke', line).style('stroke-width', 1);
    L(60, 0, 60, 80);
    g.append('circle').attr('cx', sx(60)).attr('cy', sy(40)).attr('r', sx(10) - sx(0)).style('fill', 'none').style('stroke', line);
    R(0, 18, 18, 44); R(102, 18, 18, 44); R(0, 30, 6, 20); R(114, 30, 6, 20);
    [[12, 40], [108, 40], [60, 40]].forEach(([x, y]) => g.append('circle').attr('cx', sx(x)).attr('cy', sy(y)).attr('r', 2).style('fill', line));
    return { svg, g, sx, sy, W, H: Hh };
  }

  // tabs and pages
  const pages = {};
  let current = 'today';
  function register(name, draw) { pages[name] = draw; }
  function show(name) {
    if (!pages[name] && name !== 'today') return;
    current = name;
    root.querySelectorAll('.zs-tabs button').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.tab === name)));
    root.querySelectorAll('.page').forEach((p) => { p.hidden = p.dataset.page !== name; });
    const sec = document.getElementById(name);
    const tpl = document.getElementById('tpl-' + name);
    if (tpl && !sec.dataset.ready) {
      sec.appendChild(tpl.content.cloneNode(true));
      sec.dataset.ready = '1';
      setKeys(sec);
      if (pages[name + ':init']) pages[name + ':init']();
    }
    dash.setLink(name);
    redraw();
  }
  function redraw() { if (pages[current]) pages[current](); }
  root.querySelectorAll('.zs-tabs button').forEach((b) => b.addEventListener('click', () => show(b.dataset.tab)));

  return { C, H, A, D, BAD, clear, el, num, fmt, rows, done, fail, fillMarks, computed, probBar, tip, pitch, register, show, redraw,
    current: () => current, setKeys };
})();

// ---- shared charts -------------------------------------------------------
window.ZS_cmp = function (host, rows, homeAr, awayAr) {
  const Z = window.ZS;
  Z.clear(host); Z.done(host);
  if (!rows.length) { host.appendChild(Z.el('div', 'empty', 'ماكو أرقام لهذا الجزء.')); return; }
  const head = Z.el('div', 'r');
  head.append(Z.el('div', 'v', ''), Z.el('div', 'lab', homeAr), Z.el('div', 'lab', ''), Z.el('div', 'lab', awayAr), Z.el('div', 'v', ''));
  head.children[1].style.textAlign = 'right';
  head.children[3].style.textAlign = 'left';
  host.appendChild(head);
  rows.forEach((r) => {
    const h = Z.num(r.home), a = Z.num(r.away);
    const row = Z.el('div', 'r');
    const tot = (h || 0) + (a || 0);
    const mk = (v, side, col) => {
      const t = Z.el('div', 'track ' + side);
      const f = Z.el('div', 'fill');
      f.style.width = tot > 0 && v !== null ? (100 * v / tot) + '%' : '0%';
      f.style.background = col;
      t.appendChild(f);
      return t;
    };
    const fmtv = (v) => v === null ? '—' : (Math.abs(v - Math.round(v)) < 1e-9 ? String(Math.round(v)) : v.toFixed(v < 10 ? 2 : 1));
    row.append(Z.el('div', 'v', fmtv(h)), mk(h, 'h', Z.H), Z.el('div', 'lab', r.label_ar), mk(a, 'a', Z.A), Z.el('div', 'v', fmtv(a)));
    host.appendChild(row);
  });
};

// stacked win probability (home bottom), minute 0 on the right
window.ZS_wp = function (host, rows, height) {
  const Z = window.ZS;
  const W = Math.max(280, host.clientWidth || 600), Ht = height || 220, pad = { t: 8, r: 8, b: 26, l: 34 };
  const end = d3.max(rows, (r) => r.minute);
  const x = d3.scaleLinear([0, end], [W - pad.r, pad.l]);
  const y = d3.scaleLinear([0, 100], [Ht - pad.b, pad.t]);
  const svg = d3.select(host).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${Ht}`).attr('role', 'img')
    .attr('aria-label', 'مسار فرصة الفوز');
  const area = (lo, hi) => d3.area().x((r) => x(r.minute)).y0((r) => y(lo(r))).y1((r) => y(hi(r))).curve(d3.curveStepAfter);
  svg.append('path').datum(rows).attr('d', area(() => 0, (r) => r.ph)).style('fill', Z.H).style('fill-opacity', .85);
  svg.append('path').datum(rows).attr('d', area((r) => r.ph, (r) => r.ph + r.pd)).style('fill', Z.D).style('fill-opacity', .85);
  svg.append('path').datum(rows).attr('d', area((r) => r.ph + r.pd, () => 100)).style('fill', Z.A).style('fill-opacity', .85);
  [0, 50, 100].forEach((v) => {
    svg.append('text').attr('x', pad.l - 6).attr('y', y(v) + (v === 100 ? 4 : v === 0 ? -2 : 0)).attr('dy', '0.35em').attr('text-anchor', 'end')
      .attr('direction', 'ltr').style('font-size', '11px').style('fill', 'var(--color-fg-muted)').text(v + '%');
  });
  [0, 45, 90].filter((m) => m <= end).forEach((m) => {
    svg.append('line').attr('x1', x(m)).attr('x2', x(m)).attr('y1', pad.t).attr('y2', Ht - pad.b)
      .style('stroke', 'var(--color-bg)').style('stroke-width', 2);
    svg.append('text').attr('x', x(m)).attr('y', Ht - 8).attr('text-anchor', m === 0 ? 'end' : 'middle').attr('direction', 'ltr')
      .style('font-size', '11px').style('fill', 'var(--color-fg-muted)').text(m + "'");
  });
  for (let i = 1; i < rows.length; i++) {
    if (rows[i].hg !== rows[i - 1].hg || rows[i].ag !== rows[i - 1].ag) {
      const xm = x(rows[i].minute);
      svg.append('line').attr('x1', xm).attr('x2', xm).attr('y1', pad.t).attr('y2', Ht - pad.b)
        .style('stroke', 'var(--color-fg)').style('stroke-width', 1.5).style('stroke-dasharray', '4 4');
    }
  }
  const tp = Z.tip(host);
  const rule = svg.append('line').attr('y1', pad.t).attr('y2', Ht - pad.b).style('stroke', 'var(--color-fg)').style('opacity', 0);
  svg.append('rect').attr('x', pad.l).attr('y', pad.t).attr('width', W - pad.l - pad.r).attr('height', Ht - pad.t - pad.b)
    .style('fill', 'transparent')
    .on('mousemove', (ev) => {
      const [mx] = d3.pointer(ev);
      const m = Math.round(x.invert(mx));
      const r = rows.reduce((b, c) => Math.abs(c.minute - m) < Math.abs(b.minute - m) ? c : b, rows[0]);
      rule.attr('x1', x(r.minute)).attr('x2', x(r.minute)).style('opacity', .6);
      tp.show(ev, ['الدقيقة ' + r.minute + ' · النتيجة ' + r.hg + '-' + r.ag,
        'فوز الأرض ' + r.ph.toFixed(0) + '٪ · تعادل ' + r.pd.toFixed(0) + '٪ · فوز الضيف ' + r.pa.toFixed(0) + '٪']);
    })
    .on('mouseleave', () => { rule.style('opacity', 0); tp.hide(); });
};
