(function () {
  const Z = window.ZS;
  const state = { md: null, team: '' };

  function draw() {
    const mdSel = document.getElementById('fx-md');
    const tSel = document.getElementById('fx-team');
    const tb = document.querySelector('#fx-table tbody');
    if (!mdSel) return;
    const fx = Z.rows('fixtures');
    Z.clear(tb);
    if (!fx) return;
    // selectors
    const mds = Array.from(new Set(fx.map((f) => Number(f.matchday)))).sort((a, b) => a - b);
    if (state.md === null) {
      const cr = Z.rows('current_round');
      state.md = cr && cr.length ? Number(cr[0].matchday) : mds[0];
    }
    if (!mdSel.options.length) {
      mdSel.appendChild(new Option('كل الجولات', 'all'));
      mds.forEach((m) => mdSel.appendChild(new Option('الجولة ' + m, String(m))));
      const teams = Array.from(new Set(fx.map((f) => f.home + '|' + f.home_ar))).sort((a, b) => a.split('|')[1].localeCompare(b.split('|')[1], 'ar'));
      tSel.appendChild(new Option('كل الفرق', ''));
      teams.forEach((t) => { const [k, ar] = t.split('|'); tSel.appendChild(new Option(ar, k)); });
    }
    mdSel.value = state.md === 'all' ? 'all' : String(state.md);
    tSel.value = state.team;
    let rows = fx.filter((f) => (state.md === 'all' || Number(f.matchday) === Number(state.md))
      && (!state.team || f.home === state.team || f.away === state.team));
    rows = rows.sort((a, b) => (Number(a.matchday) - Number(b.matchday)) || (a.date_baghdad + a.time_baghdad).localeCompare(b.date_baghdad + b.time_baghdad));
    const show = (v) => (v === null || v === undefined || v === '' || (typeof v === 'number' && isNaN(v))) ? '' : String(v);
    rows.forEach((f) => {
      const tr = Z.el('tr');
      tr.dataset.key = f.row_id;
      tr.append(Z.el('td', 'num', f.matchday), Z.el('td', 'num ltr', show(f.date_baghdad)), Z.el('td', 'num ltr', show(f.time_baghdad)),
        Z.el('td', 't', f.home_ar), Z.el('td', 'num ltr', show(f.score)), Z.el('td', 't', f.away_ar),
        Z.el('td', 'num', show(f.p_home)), Z.el('td', 'num', show(f.p_draw)), Z.el('td', 'num', show(f.p_away)),
        Z.el('td', 'num', show(f.xg_home)), Z.el('td', 'num', show(f.xg_away)), Z.el('td', '', f.status_ar));
      if (f.status === 'played') tr.children[4].style.fontWeight = 'var(--cds-font-weight-medium)';
      const best = Math.max(Number(f.p_home) || 0, Number(f.p_draw) || 0, Number(f.p_away) || 0);
      [6, 7, 8].forEach((i) => { if (best && Number(tr.children[i].textContent) === best) tr.children[i].style.fontWeight = 'var(--cds-font-weight-medium)'; });
      tb.appendChild(tr);
    });
  }

  Z.register('fixtures:init', () => {
    document.getElementById('fx-md').addEventListener('change', (e) => { state.md = e.target.value === 'all' ? 'all' : Number(e.target.value); draw(); });
    document.getElementById('fx-team').addEventListener('change', (e) => { state.team = e.target.value; draw(); });
  });
  Z.register('fixtures', draw);
})();
