(function () {
  const Z = window.ZS;
  const state = { match: null, part: 'full', player: '' };
  const PARTS = [['h1', 'الشوط الأول', [1]], ['h2', 'الشوط الثاني', [2]], ['full', 'المباراة كاملة', [1, 2]]];
  const periodsOf = (p) => (PARTS.find((x) => x[0] === p) || PARTS[2])[2];
  const HOSTS = [['dp-head', 'deep_matches'], ['dp-ins', 'deep_insights'], ['dp-stats', 'deep_stats'], ['dp-shots', 'deep_shots'],
    ['dp-xg', 'deep_timeline'], ['dp-heat', 'deep_touches'], ['dp-net', 'deep_pass_nodes']];

  // contour MultiPolygon (already in pixels) -> svg path
  const geoPath = (g) => g.coordinates.map((poly) => poly.map((ring) =>
    'M' + ring.map((p) => p[0].toFixed(1) + ',' + p[1].toFixed(1)).join('L') + 'Z').join('')).join('');
  const meets = (a, b) => !(a.x2 < b.x1 || a.x1 > b.x2 || a.y2 < b.y1 || a.y1 > b.y2);
  const outcomeAr = (o) => ({ 'Saved': 'تصدى لها الحارس', 'Off T': 'خارج المرمى', 'Blocked': 'مصدودة', 'Post': 'القائم',
    'Wayward': 'بعيدة عن المرمى', 'Saved to Post': 'تصدي وارتدت من القائم', 'Saved Off Target': 'تصدي' })[o] || o;

  function header(m) {
    const head = document.getElementById('dp-head');
    Z.clear(head); Z.done(head);
    const row = Z.el('div', 'm');
    const when = Z.el('div', 'when');
    when.append(Z.el('div', 'ltr', m.date), Z.el('div', 'pill', m.source));
    const right = Z.el('div'); right.style.display = 'grid'; right.style.gap = '6px';
    const teams = Z.el('div', 'teams');
    teams.append(Z.el('div', 't', m.home_ar), Z.el('div', 'mid done ltr', m.hg + '-' + m.ag), Z.el('div', 't a', m.away_ar));
    right.append(teams,
      Z.el('div', 'sr', 'xG: ' + m.home_ar + ' ' + m.xg_home + ' · ' + m.away_ar + ' ' + m.xg_away),
      Z.el('div', 'sr', 'توقع الموديل قبل المباراة (من أسعار Bet365)'), Z.probBar(m.pre_home_pct, m.pre_draw_pct, m.pre_away_pct));
    row.append(when, right);
    head.appendChild(row);
  }

  function insights(m) {
    const host = document.getElementById('dp-ins');
    const all = Z.rows('deep_insights');
    if (!all) { Z.fail(host, 'deep_insights'); return; }
    Z.clear(host); Z.done(host);
    const mine = all.filter((r) => r.match_id === m.match_id && r.part === state.part);
    const block = (title, items, color, extra) => {
      const d = Z.el('div'); if (extra) d.classList.add(extra);
      d.appendChild(Z.el('h3', '', title));
      const ul = Z.el('ul');
      items.forEach((t) => { const x = Z.el('li', '', t); x.style.setProperty('--k', color); ul.appendChild(x); });
      d.appendChild(ul); return d;
    };
    const pick = (side, kind) => mine.filter((r) => r.side === side && r.kind === kind).sort((a, b) => a.rank - b.rank).map((r) => r.text);
    [['home', m.home_ar, Z.H], ['away', m.away_ar, Z.A]].forEach(([side, nm, col]) => {
      const pos = pick(side, 'pos'), neg = pick(side, 'neg');
      if (pos.length) host.appendChild(block(nm + ': الإيجابيات', pos, col));
      if (neg.length) host.appendChild(block(nm + ': السلبيات', neg, Z.BAD));
    });
    const notes = pick('match', 'note');
    if (notes.length) host.appendChild(block('أبرز الملاحظات', notes, 'var(--color-fg-muted)', 'notes'));
  }

  function stats(m) {
    const host = document.getElementById('dp-stats');
    const all = Z.rows('deep_stats');
    if (!all) { Z.fail(host, 'deep_stats'); return; }
    window.ZS_cmp(host, all.filter((r) => r.match_id === m.match_id && r.part === state.part), m.home_ar, m.away_ar);
  }

  function shotMap(m) {
    const host = document.getElementById('dp-shots');
    const all = Z.rows('deep_shots');
    if (!all) { Z.fail(host, 'deep_shots'); return; }
    Z.clear(host); Z.done(host);
    const per = periodsOf(state.part);
    const shots = all.filter((s) => s.match_id === m.match_id && per.includes(Number(s.period)))
      .sort((a, b) => Number(b.xg) - Number(a.xg));
    const P = Z.pitch(host, host.clientWidth || 700);
    P.svg.attr('aria-label', 'خريطة التسديدات');
    const r = (xg) => Math.min(P.W / 28, 3 + (P.W / 40) * Math.sqrt(Math.max(0, Number(xg) || 0)));
    const tp = Z.tip(host);
    P.g.selectAll('circle.s').data(shots).enter().append('circle')
      .attr('cx', (s) => P.sx(Number(s.x))).attr('cy', (s) => P.sy(Number(s.y))).attr('r', (s) => r(s.xg))
      .style('fill', (s) => (s.side === 'home' ? Z.H : Z.A)).style('fill-opacity', (s) => (Number(s.is_goal) ? 0.95 : 0.25))
      .style('stroke', (s) => (Number(s.is_goal) ? 'var(--color-fg)' : (s.side === 'home' ? Z.H : Z.A)))
      .style('stroke-width', (s) => (Number(s.is_goal) ? 2 : 1.2))
      .on('mousemove', (ev, s) => tp.show(ev, [s.player_ar + ' · الدقيقة ' + s.minute,
        'xG ' + s.xg + ' · ' + (Number(s.is_goal) ? 'هدف' : outcomeAr(s.outcome))]))
      .on('mouseleave', () => tp.hide());
    // who shoots where: home at the right goal, away at the left
    P.svg.append('text').attr('x', P.W - 10).attr('y', 18).attr('direction', 'rtl').attr('text-anchor', 'start')
      .style('font-size', '12px').style('fill', 'var(--color-fg-muted)').text('تسديدات ' + m.home_ar);
    P.svg.append('text').attr('x', 10).attr('y', 18).attr('direction', 'rtl').attr('text-anchor', 'end')
      .style('font-size', '12px').style('fill', 'var(--color-fg-muted)').text('تسديدات ' + m.away_ar);
  }

  function flow(m) {
    const host = document.getElementById('dp-xg');
    const all = Z.rows('deep_timeline');
    if (!all) { Z.fail(host, 'deep_timeline'); return; }
    Z.clear(host); Z.done(host);
    const rows = all.filter((r) => r.match_id === m.match_id).map((r) => ({ minute: Number(r.minute), xh: Number(r.xg_home),
      xa: Number(r.xg_away), ph: Number(r.p_home), pd: Number(r.p_draw), pa: Number(r.p_away), hg: Number(r.hg), ag: Number(r.ag) }))
      .sort((a, b) => a.minute - b.minute);
    if (rows.length < 2) return;
    const box1 = Z.el('div', 'chart'), box2 = Z.el('div', 'chart');
    host.append(box1, box2);
    const W = Math.max(280, box1.clientWidth || host.clientWidth || 700), Ht = 180, pad = { t: 12, r: 8, b: 26, l: 34 };
    const end = d3.max(rows, (r) => r.minute);
    const x = d3.scaleLinear([0, end], [W - pad.r, pad.l]);
    const ymax = Math.max(0.5, d3.max(rows, (r) => Math.max(r.xh, r.xa)));
    const y = d3.scaleLinear([0, ymax], [Ht - pad.b, pad.t]).nice();
    const svg = d3.select(box1).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${Ht}`).attr('role', 'img')
      .attr('aria-label', 'تراكم الأهداف المتوقعة');
    y.ticks(3).forEach((v) => {
      svg.append('line').attr('x1', pad.l).attr('x2', W - pad.r).attr('y1', y(v)).attr('y2', y(v)).style('stroke', 'var(--cds-chart-grid)');
      svg.append('text').attr('x', pad.l - 6).attr('y', y(v)).attr('dy', '0.35em').attr('text-anchor', 'end').attr('direction', 'ltr')
        .style('font-size', '11px').style('fill', 'var(--color-fg-muted)').text(v.toFixed(1));
    });
    [0, 45, 90].filter((mm) => mm <= end).forEach((mm) => {
      svg.append('text').attr('x', x(mm)).attr('y', Ht - 8).attr('text-anchor', mm === 0 ? 'end' : 'middle').attr('direction', 'ltr')
        .style('font-size', '11px').style('fill', 'var(--color-fg-muted)').text(mm + "'");
    });
    [['xh', Z.H], ['xa', Z.A]].forEach(([k, c]) => {
      svg.append('path').datum(rows).attr('d', d3.line().x((r) => x(r.minute)).y((r) => y(r[k])).curve(d3.curveStepAfter))
        .style('fill', 'none').style('stroke', c).style('stroke-width', 2).style('stroke-linejoin', 'round').style('stroke-linecap', 'round');
    });
    for (let i = 1; i < rows.length; i++) {
      const a = rows[i - 1], b = rows[i];
      if (b.hg > a.hg) svg.append('circle').attr('cx', x(b.minute)).attr('cy', y(b.xh)).attr('r', 4.5).style('fill', Z.H)
        .style('stroke', 'var(--color-bg)').style('stroke-width', 1.5);
      if (b.ag > a.ag) svg.append('circle').attr('cx', x(b.minute)).attr('cy', y(b.xa)).attr('r', 4.5).style('fill', Z.A)
        .style('stroke', 'var(--color-bg)').style('stroke-width', 1.5);
    }
    // end labels at the final minute (left end), kept apart
    const last = rows[rows.length - 1];
    const yh = y(last.xh), ya = y(last.xa);
    const GAP = 18;
    let lh = yh <= ya ? yh - 7 : yh + 16, la = yh <= ya ? ya + 16 : ya - 7;
    const lo = pad.t + 10, hi = Ht - pad.b - 4;
    lh = Math.min(hi, Math.max(lo, lh)); la = Math.min(hi, Math.max(lo, la));
    if (Math.abs(lh - la) < GAP) {
      if (lh <= la) { la = lh + GAP; if (la > hi) { la = hi; lh = hi - GAP; } } else { lh = la + GAP; if (lh > hi) { lh = hi; la = hi - GAP; } }
    }
    [[lh, m.home_ar + ' ' + last.xh.toFixed(2)], [la, m.away_ar + ' ' + last.xa.toFixed(2)]].forEach(([yy, txt]) => {
      svg.append('text').attr('x', pad.l + 6).attr('y', yy).attr('direction', 'rtl').attr('text-anchor', 'end')
        .style('font-size', '11px').style('font-weight', 600).style('fill', 'var(--color-fg)')
        .style('paint-order', 'stroke').style('stroke', 'var(--color-panel)').style('stroke-width', 3).text(txt);
    });
    window.ZS_wp(box2, rows, 170);
  }

  function heat(m) {
    const host = document.getElementById('dp-heat');
    const sel = document.getElementById('dp-player');
    const all = Z.rows('deep_touches');
    if (!all) { Z.fail(host, 'deep_touches'); return; }
    Z.clear(host); Z.done(host);
    const per = periodsOf(state.part);
    const pts = all.filter((t) => t.match_id === m.match_id && per.includes(Number(t.period)));
    const players = Array.from(new Set(pts.map((t) => t.side + '|' + t.player_ar)));
    Z.clear(sel);
    sel.appendChild(new Option('الفريقين', ''));
    [['home', m.home_ar], ['away', m.away_ar]].forEach(([side, nm]) => {
      const og = document.createElement('optgroup'); og.label = nm;
      players.filter((p) => p.startsWith(side + '|')).map((p) => p.slice(side.length + 1)).sort((a, b) => a.localeCompare(b, 'ar'))
        .forEach((p) => og.appendChild(new Option(p, side + '|' + p)));
      sel.appendChild(og);
    });
    if (state.player && !players.includes(state.player)) state.player = '';
    sel.value = state.player;
    const cut = state.player.indexOf('|');
    const pick = state.player ? [state.player.slice(0, cut), state.player.slice(cut + 1)] : null;
    const panels = pick ? [pick] : [['home', m.home_ar], ['away', m.away_ar]];
    panels.forEach(([side, label]) => {
      const box = Z.el('div');
      box.appendChild(Z.el('h3', '', pick ? label : label + ' · كل الفريق'));
      host.appendChild(box);
      const P = Z.pitch(box, box.clientWidth || host.clientWidth || 600);
      P.svg.attr('aria-label', 'خريطة حرارية: ' + label);
      const data = pts.filter((t) => t.side === side && (!pick || t.player_ar === pick[1]));
      const col = side === 'home' ? Z.H : Z.A;
      if (data.length >= 3) {
        const dens = d3.contourDensity().x((d) => P.sx(Number(d.x))).y((d) => P.sy(Number(d.y))).size([P.W, P.H])
          .bandwidth(Math.max(6, P.W / (pick ? 24 : 30))).thresholds(12)(data);
        const vmax = d3.max(dens, (d) => d.value) || 1;
        P.g.insert('g', ':nth-child(2)').selectAll('path').data(dens).enter().append('path').attr('d', geoPath)
          .style('fill', col).style('fill-opacity', (d) => 0.05 + 0.7 * d.value / vmax).style('stroke', 'none');
      }
      P.svg.append('text').attr('x', P.W - 8).attr('y', P.H - 8).attr('direction', 'rtl').attr('text-anchor', 'start')
        .style('font-size', '11px').style('fill', 'var(--color-fg-muted)').text('عدد اللمسات: ' + data.length);
    });
  }

  function network(m) {
    const host = document.getElementById('dp-net');
    const N = Z.rows('deep_pass_nodes'), E = Z.rows('deep_pass_edges');
    if (!N || !E) { Z.fail(host, N ? 'deep_pass_edges' : 'deep_pass_nodes'); return; }
    Z.clear(host); Z.done(host);
    [['home', m.home_ar, Z.H], ['away', m.away_ar, Z.A]].forEach(([side, nm, col]) => {
      const nodes = N.filter((n) => n.match_id === m.match_id && n.side === side);
      const edges = E.filter((e) => e.match_id === m.match_id && e.side === side);
      const box = Z.el('div');
      const until = nodes.length && nodes[0].until_minute ? ' · لحد الدقيقة ' + nodes[0].until_minute : '';
      box.appendChild(Z.el('h3', '', nm + until));
      host.appendChild(box);
      const P = Z.pitch(box, box.clientWidth || host.clientWidth || 600);
      P.svg.attr('aria-label', 'شبكة تمريرات ' + nm);
      const tp = Z.tip(box);
      const maxp = d3.max(edges, (e) => Number(e.passes)) || 1;
      P.g.selectAll('line.e').data(edges).enter().append('line')
        .attr('x1', (e) => P.sx(Number(e.x1))).attr('y1', (e) => P.sy(Number(e.y1))).attr('x2', (e) => P.sx(Number(e.x2))).attr('y2', (e) => P.sy(Number(e.y2)))
        .style('stroke', col).style('stroke-opacity', (e) => 0.25 + 0.6 * Number(e.passes) / maxp)
        .style('stroke-width', (e) => 1 + 6 * Number(e.passes) / maxp).style('stroke-linecap', 'round')
        .on('mousemove', (ev, e) => tp.show(ev, [e.a_ar + ' ↔ ' + e.b_ar, e.passes + ' تمريرة بيناتهم']))
        .on('mouseleave', () => tp.hide());
      const maxT = d3.max(nodes, (n) => Number(n.touches)) || 1;
      const rad = (n) => 4 + (P.W / 60) * Math.sqrt(Number(n.touches) / maxT);
      P.g.selectAll('circle.n').data(nodes).enter().append('circle')
        .attr('cx', (n) => P.sx(Number(n.x))).attr('cy', (n) => P.sy(Number(n.y))).attr('r', rad)
        .style('fill', col).style('stroke', 'var(--color-bg)').style('stroke-width', 1.5)
        .on('mousemove', (ev, n) => tp.show(ev, [n.player_ar + (n.number ? ' (' + n.number + ')' : ''), n.touches + ' لمسة قبل أول تبديل']))
        .on('mouseleave', () => tp.hide());
      // names: busiest players first, below the dot, else above, else left out (the tooltip has it)
      const placed = [];
      const labels = P.svg.append('g');
      nodes.slice().sort((a, b) => Number(b.touches) - Number(a.touches)).forEach((n) => {
        const cx = P.sx(Number(n.x)), cy = P.sy(Number(n.y)), r = rad(n);
        const t = labels.append('text').attr('text-anchor', 'middle').style('font-size', '11px').style('font-weight', 600)
          .style('paint-order', 'stroke').style('stroke', 'var(--color-bg)').style('stroke-width', 3).style('pointer-events', 'none')
          .text(n.player_ar);
        const w = t.node().getComputedTextLength();
        const xm = Math.min(P.W - w / 2 - 3, Math.max(w / 2 + 3, cx));
        let spot = null;
        for (const yy of [cy + r + 12, cy - r - 5]) {
          t.attr('x', xm).attr('y', yy);
          const bb = t.node().getBBox();
          const b = { x1: bb.x - 1, x2: bb.x + bb.width + 1, y1: bb.y - 1, y2: bb.y + bb.height + 1 };
          if (b.x1 >= 0 && b.x2 <= P.W && b.y1 >= 0 && b.y2 <= P.H && !placed.some((p) => meets(p, b))) { spot = b; break; }
        }
        if (!spot) { t.remove(); return; }
        placed.push(spot);
      });
    });
  }

  function players(m) {
    const tb = document.querySelector('#dp-players tbody');
    const all = Z.rows('deep_players');
    Z.clear(tb);
    if (!all) return;
    all.filter((p) => p.match_id === m.match_id).sort((a, b) => Number(b.rating) - Number(a.rating)).forEach((p) => {
      const tr = Z.el('tr'); tr.dataset.key = p.row_id;
      const nm = Z.el('td', 't', p.name_ar);
      nm.style.boxShadow = 'inset -3px 0 0 ' + (p.side === 'home' ? Z.H : Z.A);
      tr.appendChild(nm);
      ['minutes', 'rating', 'goals', 'assists', 'xg', 'xa', 'key_passes', 'progressive', 'pass_pct', 'dribbles', 'tackles_int', 'pressures']
        .forEach((k) => tr.appendChild(Z.el('td', 'num', p[k])));
      tr.children[2].style.fontWeight = 'var(--cds-font-weight-medium)';
      tb.appendChild(tr);
    });
  }

  function draw() {
    const sec = document.getElementById('deep');
    if (!sec || !sec.dataset.ready) return;
    const sel = document.getElementById('dp-match');
    const seg = document.getElementById('dp-part');
    const ms = Z.rows('deep_matches');
    if (!ms || !ms.length) {
      HOSTS.forEach(([id]) => Z.fail(document.getElementById(id), 'deep_matches'));
      Z.clear(document.querySelector('#dp-players tbody'));
      return;
    }
    if (!state.match || !ms.some((x) => x.match_id === state.match)) state.match = ms[0].match_id;
    Z.clear(sel);
    ms.forEach((m) => sel.appendChild(new Option(m.label_ar + ' · ' + m.date, m.match_id)));
    sel.value = state.match;
    Z.clear(seg);
    PARTS.forEach(([p, lab]) => {
      const b = Z.el('button', '', lab); b.type = 'button'; b.setAttribute('aria-pressed', String(p === state.part));
      b.addEventListener('click', () => { state.part = p; draw(); });
      seg.appendChild(b);
    });
    const m = ms.find((x) => x.match_id === state.match);
    header(m); insights(m); stats(m); shotMap(m); flow(m); heat(m); network(m); players(m);
  }

  Z.register('deep:init', () => {
    document.getElementById('dp-match').addEventListener('change', (e) => { state.match = e.target.value; state.player = ''; draw(); });
    document.getElementById('dp-player').addEventListener('change', (e) => {
      state.player = e.target.value;
      const ms = Z.rows('deep_matches');
      if (ms) heat(ms.find((x) => x.match_id === state.match));
    });
  });
  Z.register('deep', draw);
})();
