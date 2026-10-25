dash.calc('current_round', {
  title: 'الجولة الحالية',
  description: 'The earliest matchday that still has a scheduled match, with all of its fixtures.',
  inputs: ['fixtures'],
  fn: (fixtures) => {
    const sched = fixtures.filter((f) => f.status === 'scheduled').map((f) => Number(f.matchday));
    if (!sched.length) return [];
    const md = Math.min(...sched);
    return fixtures.filter((f) => Number(f.matchday) === md)
      .sort((a, b) => (a.date_baghdad + a.time_baghdad).localeCompare(b.date_baghdad + b.time_baghdad));
  },
});

dash.calc('next_big', {
  title: 'مباراة الأسبوع',
  description: 'The scheduled match of the current round whose two teams have the most expected points.',
  inputs: ['current_round', 'forecast'],
  fn: (current_round, forecast) => {
    const pts = {};
    forecast.forEach((t) => { pts[t.team] = Number(t.exp_pts); });
    let best = null, score = -1;
    current_round.filter((f) => f.status === 'scheduled').forEach((f) => {
      const s = (pts[f.home] || 0) + (pts[f.away] || 0);
      if (s > score) { score = s; best = f; }
    });
    return best ? [best] : [];
  },
});

(function () {
  const Z = window.ZS;
  const state = { event: null, part: null };

  // takeaway: next big match
  function drawTake() {
    const host = document.getElementById('take-next');
    Z.clear(host);
    const nb = Z.rows('next_big');
    if (!nb || !nb.length) return;
    const r = nb[0];
    const mk = (field, cls) => {
      const s = Z.el('span', cls || '', r[field]);
      s.dataset.source = 'next_big'; s.dataset.field = field; s.dataset.row = '0';
      return s;
    };
    host.append('مباراة الأسبوع: ', mk('home_ar'), ' × ', mk('away_ar'), ' (', mk('date_baghdad', 'ltr num'), ' الساعة ',
      mk('time_baghdad', 'ltr num'), ')، والحاسوب يعطي ', mk('home_ar'), ' ', mk('p_home', 'num'), '٪.');
  }

  function liveByKey() {
    const lm = Z.rows('live_matches') || [];
    const k = {};
    lm.forEach((m) => { k[m.home + '|' + m.away] = m; });
    return k;
  }

  function drawRound() {
    const host = document.getElementById('round-list');
    const rr = Z.rows('current_round');
    if (!rr) { Z.fail(host, 'fixtures'); return; }
    Z.clear(host); Z.done(host);
    if (!rr.length) { host.appendChild(Z.el('div', 'empty', 'ماكو مباريات قادمة.')); return; }
    const live = liveByKey();
    rr.forEach((f) => {
      const m = Z.el('div', 'm');
      const when = Z.el('div', 'when');
      when.append(Z.el('div', 'ltr', f.date_baghdad ? f.date_baghdad.slice(5).replace('-', '/') : ''), Z.el('div', 'ltr', f.time_baghdad || 'لم يحدد'));
      const teams = Z.el('div', 'teams');
      const lv = live[f.home + '|' + f.away];
      let mid;
      if (f.status === 'played') mid = Z.el('div', 'mid done ltr', f.score);
      else if (lv && lv.status === 'HT') mid = Z.el('div', 'mid done ltr', lv.hg + '-' + lv.ag);
      else mid = Z.el('div', 'mid', '×');
      teams.append(Z.el('div', 't', f.home_ar), mid, Z.el('div', 't a', f.away_ar));
      const right = Z.el('div');
      right.style.display = 'grid'; right.style.gap = '6px';
      right.appendChild(teams);
      if (f.status === 'scheduled' && Z.num(f.p_home) !== null) {
        right.appendChild(Z.probBar(f.p_home, f.p_draw, f.p_away));
        if (Z.num(f.sr_p_home) !== null) {
          right.appendChild(Z.el('div', 'sr', 'SportRadar: ' + Z.fmt(f.sr_p_home) + '٪ / ' + Z.fmt(f.sr_p_draw) + '٪ / ' + Z.fmt(f.sr_p_away) + '٪'));
        }
      }
      if (lv) {
        const p = Z.el('span', 'pill live', lv.status === 'HT' ? 'استراحة: التحليل جاهز' : 'التحليل الكامل جاهز');
        p.style.cursor = 'pointer';
        p.addEventListener('click', () => { state.event = lv.event_id; state.part = null; drawLive(); document.getElementById('live').scrollIntoView(); });
        right.appendChild(p);
      } else if (f.status === 'pending') {
        right.appendChild(Z.el('span', 'pill', f.status_ar));
      }
      m.append(when, right);
      host.appendChild(m);
    });
  }

  function partsFor(ev) {
    const st = (Z.rows('live_stats') || []).filter((r) => r.event_id === ev);
    const order = [['first_half', 'الشوط الأول'], ['second_half', 'الشوط الثاني'], ['full', 'المباراة']];
    return order.filter(([p]) => st.some((r) => r.part === p));
  }

  function drawLive() {
    const sel = document.getElementById('live-match');
    const head = document.getElementById('live-head');
    const ins = document.getElementById('live-ins');
    const lm = Z.rows('live_matches');
    if (!lm) { Z.fail(head, 'live_matches'); return; }
    Z.clear(head); Z.clear(ins);
    if (!lm.length) {
      head.appendChild(Z.el('div', 'empty', 'أول تحليل مباشر ينزل هنا بنهاية الشوط الأول من المباراة الجاية.'));
      sel.hidden = true;
      return;
    }
    sel.hidden = false;
    const sorted = lm.slice().sort((a, b) => String(b.updated_utc).localeCompare(String(a.updated_utc)));
    if (!state.event || !lm.some((m) => m.event_id === state.event)) state.event = sorted[0].event_id;
    Z.clear(sel);
    sorted.forEach((m) => {
      const o = new Option(m.home_ar + ' ' + m.hg + '-' + m.ag + ' ' + m.away_ar + ' · ' + m.status_ar, m.event_id);
      sel.appendChild(o);
    });
    sel.value = state.event;
    const m = lm.find((x) => x.event_id === state.event);

    const row = Z.el('div', 'm');
    const when = Z.el('div', 'when');
    when.append(Z.el('div', 'pill live', m.status_ar), Z.el('div', 'ltr', m.time_baghdad || ''));
    const right = Z.el('div');
    right.style.display = 'grid'; right.style.gap = '6px';
    const teams = Z.el('div', 'teams');
    teams.append(Z.el('div', 't', m.home_ar), Z.el('div', 'mid done ltr', m.hg + '-' + m.ag), Z.el('div', 't a', m.away_ar));
    right.append(teams);
    right.append(Z.el('div', 'sr', 'قبل المباراة'), Z.probBar(m.pre_home_pct, m.pre_draw_pct, m.pre_away_pct));
    if (m.status === 'HT') {
      right.append(Z.el('div', 'sr', 'الآن، والنتيجة الأرجح بالنهاية ' + m.likely_final), Z.probBar(m.now_home_pct, m.now_draw_pct, m.now_away_pct));
    }
    row.append(when, right);
    head.appendChild(row);
    document.getElementById('wp-k-h').textContent = 'فوز ' + m.home_ar;
    document.getElementById('wp-k-a').textContent = 'فوز ' + m.away_ar;

    const li = Z.rows('live_insights');
    if (!li) { Z.fail(ins, 'live_insights'); } else {
      const mine = li.filter((r) => r.event_id === m.event_id && r.phase === m.status);
      const block = (title, items, color) => {
        const d = Z.el('div');
        d.appendChild(Z.el('h3', '', title));
        const ul = Z.el('ul');
        items.forEach((t) => { const x = Z.el('li', '', t); x.style.setProperty('--k', color); ul.appendChild(x); });
        d.appendChild(ul);
        return d;
      };
      [['home', m.home_ar, Z.H], ['away', m.away_ar, Z.A]].forEach(([side, nm, col]) => {
        const pos = mine.filter((r) => r.side === side && r.kind === 'pos').sort((a, b) => a.rank - b.rank).map((r) => r.text);
        const neg = mine.filter((r) => r.side === side && r.kind === 'neg').sort((a, b) => a.rank - b.rank).map((r) => r.text);
        if (pos.length) ins.appendChild(block(nm + ': الإيجابيات', pos, col));
        if (neg.length) ins.appendChild(block(nm + ': السلبيات', neg, Z.BAD));
      });
      const notes = mine.filter((r) => r.kind === 'note').sort((a, b) => a.rank - b.rank).map((r) => r.text);
      if (notes.length) { const b = block('أبرز الملاحظات', notes, 'var(--color-fg-muted)'); b.classList.add('notes'); ins.appendChild(b); }
    }
    drawStats();
    drawTimeline();
    drawImpact();
  }

  function drawStats() {
    const host = document.getElementById('live-stats');
    const seg = document.getElementById('live-part');
    const st = Z.rows('live_stats');
    if (!st) { Z.fail(host, 'live_stats'); return; }
    Z.clear(host); Z.clear(seg);
    const lm = Z.rows('live_matches') || [];
    const m = lm.find((x) => x.event_id === state.event);
    if (!m) { host.appendChild(Z.el('div', 'empty', 'الإحصائيات تنزل مع أول تحليل مباشر.')); return; }
    const parts = partsFor(m.event_id);
    if (!state.part || !parts.some(([p]) => p === state.part)) state.part = parts.length ? parts[parts.length - 1][0] : null;
    parts.forEach(([p, lab]) => {
      const b = Z.el('button', '', lab);
      b.type = 'button';
      b.setAttribute('aria-pressed', String(p === state.part));
      b.addEventListener('click', () => { state.part = p; drawStats(); });
      seg.appendChild(b);
    });
    const rows = st.filter((r) => r.event_id === m.event_id && r.part === state.part);
    window.ZS_cmp(host, rows, m.home_ar, m.away_ar);
  }

  function drawTimeline() {
    const host = document.getElementById('live-timeline');
    const tl = Z.rows('live_timeline');
    if (!tl) { Z.fail(host, 'live_timeline'); return; }
    Z.clear(host); Z.done(host);
    const rows = tl.filter((r) => r.event_id === state.event).map((r) => ({
      minute: Number(r.minute), ph: Number(r.p_home), pd: Number(r.p_draw), pa: Number(r.p_away), hg: Number(r.hg), ag: Number(r.ag) }));
    if (rows.length < 2) { host.appendChild(Z.el('div', 'empty', 'المسار يظهر مع أول تحليل مباشر.')); return; }
    window.ZS_wp(host, rows);
  }

  function drawImpact() {
    const tb = document.querySelector('#live-impact tbody');
    const im = Z.rows('live_impact');
    Z.clear(tb);
    if (!im) return;
    const rows = im.filter((r) => r.event_id === state.event && Math.abs(Number(r.change_pts)) >= 0.1)
      .sort((a, b) => Math.abs(Number(b.change_pts)) - Math.abs(Number(a.change_pts)));
    rows.forEach((r) => {
      const tr = Z.el('tr');
      tr.dataset.key = r.row_id;
      tr.append(Z.el('td', 't', r.team_ar), Z.el('td', '', r.label_ar), Z.el('td', 'num', r.before_pct), Z.el('td', 'num', r.now_pct));
      const ch = Z.el('td', 'num', r.change_pts);
      ch.style.color = Number(r.change_pts) > 0 ? 'var(--color-ok)' : 'var(--color-bad)';
      if (r.metric === 'p_releg') ch.style.color = Number(r.change_pts) > 0 ? 'var(--color-bad)' : 'var(--color-ok)';
      tr.appendChild(ch);
      tb.appendChild(tr);
    });
    const note = document.getElementById('live-impact-empty');
    if (note) note.hidden = rows.length > 0;
  }

  document.getElementById('live-match').addEventListener('change', (e) => { state.event = e.target.value; state.part = null; drawLive(); });

  Z.register('today', () => { drawTake(); drawRound(); drawLive(); Z.fillMarks(document.getElementById('today')); });
  window.ZS_drawTake = drawTake;
})();
