(function () {
  const Z = window.ZS;

  // calibration: forecast (across) against what happened (up); on the dashed line = honest
  function calChart(host, rows) {
    Z.clear(host); Z.done(host);
    const W = Math.max(260, host.clientWidth || 420), Ht = 250, pad = { t: 12, r: 16, b: 28, l: 40 };
    const x = d3.scaleLinear([0, 100], [pad.l, W - pad.r]);
    const y = d3.scaleLinear([0, 100], [Ht - pad.b, pad.t]);
    const svg = d3.select(host).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${Ht}`).attr('role', 'img')
      .attr('aria-label', 'معايرة توقعات الاستراحة');
    [0, 25, 50, 75, 100].forEach((v) => {
      svg.append('line').attr('x1', x(0)).attr('x2', x(100)).attr('y1', y(v)).attr('y2', y(v)).style('stroke', 'var(--cds-chart-grid)');
      svg.append('text').attr('x', pad.l - 6).attr('y', y(v)).attr('dy', '0.35em').attr('text-anchor', 'end').attr('direction', 'ltr')
        .style('font-size', '11px').style('fill', 'var(--color-fg-muted)').text(v + '%');
      svg.append('text').attr('x', x(v)).attr('y', Ht - 8).attr('text-anchor', 'middle').attr('direction', 'ltr')
        .style('font-size', '11px').style('fill', 'var(--color-fg-muted)').text(v + '%');
    });
    svg.append('line').attr('x1', x(0)).attr('y1', y(0)).attr('x2', x(100)).attr('y2', y(100))
      .style('stroke', 'var(--cds-chart-reference)').style('stroke-dasharray', '5 4');
    const tp = Z.tip(host);
    const maxn = d3.max(rows, (r) => Number(r.n)) || 1;
    svg.selectAll('circle').data(rows).enter().append('circle')
      .attr('cx', (r) => x(Number(r.forecast_pct))).attr('cy', (r) => y(Number(r.observed_pct)))
      .attr('r', (r) => 3.5 + 5 * Math.sqrt(Number(r.n) / maxn)).style('fill', Z.H).style('fill-opacity', 0.85)
      .style('stroke', 'var(--color-bg)').style('stroke-width', 1.5)
      .on('mousemove', (ev, r) => tp.show(ev, [r.bin_ar + ' · ' + r.n + ' توقع', 'الموديل ' + r.forecast_pct + '٪ · صار فعلاً ' + r.observed_pct + '٪']))
      .on('mouseleave', () => tp.hide());
  }

  function draw() {
    const sec = document.getElementById('accuracy');
    if (!sec || !sec.dataset.ready) return;
    Z.fillMarks(sec);
    const acc = Z.rows('accuracy');
    const tb = document.querySelector('#acc-table tbody');
    Z.clear(tb);
    if (acc) acc.forEach((r) => {
      const tr = Z.el('tr'); tr.dataset.key = r.id;
      tr.append(Z.el('td', 't wrap', r.ar), Z.el('td', 'num', r.model), Z.el('td', 'num', r.bookmaker), Z.el('td', 'num', r.baseline),
        Z.el('td', 'num ltr', r.period), Z.el('td', 'num', r.n));
      tr.children[1].style.fontWeight = 'var(--cds-font-weight-medium)';
      tb.appendChild(tr);
    });
    const cal = Z.rows('inplay_calibration');
    const ch = document.getElementById('cal-chart');
    if (cal) calChart(ch, cal); else Z.fail(ch, 'inplay_calibration');

    const ts = Z.rows('track_summary'), tr_ = Z.rows('track');
    const sb = document.querySelector('#track-sum tbody'), tt = document.querySelector('#track-table tbody');
    Z.clear(sb); Z.clear(tt);
    const empty = document.getElementById('track-empty');
    empty.hidden = !(ts && !ts.length);
    if (ts) ts.forEach((r) => {
      const tr = Z.el('tr'); tr.dataset.key = r.source;
      tr.append(Z.el('td', 't', r.source_ar), Z.el('td', 'num', r.n), Z.el('td', 'num', r.rps), Z.el('td', 'num', r.hit_pct));
      sb.appendChild(tr);
    });
    if (tr_) tr_.forEach((r) => {
      const tr = Z.el('tr'); tr.dataset.key = r.row_id;
      tr.append(Z.el('td', 't', r.home_ar), Z.el('td', 'num ltr', r.score), Z.el('td', 't', r.away_ar), Z.el('td', '', r.source_ar),
        Z.el('td', 'num', r.p_home), Z.el('td', 'num', r.p_draw), Z.el('td', 'num', r.p_away), Z.el('td', 'num', r.rps));
      tt.appendChild(tr);
    });
  }
  Z.register('accuracy', draw);
})();
