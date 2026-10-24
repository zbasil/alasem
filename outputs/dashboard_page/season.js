(function () {
  const Z = window.ZS;

  function titleChart(host, rows) {
    Z.clear(host);
    const data = rows.filter((r) => Number(r.title_pct) >= 0.1).sort((a, b) => Number(b.title_pct) - Number(a.title_pct));
    if (!data.length) return;
    const W = Math.max(260, host.clientWidth || 520), rowH = 30, top = 4, H = top + data.length * rowH + 4;
    const svg = d3.select(host).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img').attr('aria-label', 'فرصة الفوز باللقب');
    const probe = svg.append('g');
    let nameW = 0, valW = 0;
    data.forEach((d) => {
      nameW = Math.max(nameW, probe.append('text').style('font-size', '13px').style('font-weight', 600).text(d.ar).node().getComputedTextLength());
      valW = Math.max(valW, probe.append('text').style('font-size', '12px').text(Number(d.title_pct).toFixed(1) + '%').node().getComputedTextLength());
    });
    probe.remove();
    const labelW = Math.ceil(nameW) + 10, gap = 6;
    const x = d3.scaleLinear([0, 100], [0, Math.max(40, W - labelW - valW - gap - 4)]);
    const g = svg.selectAll('g.r').data(data).enter().append('g').attr('transform', (d, i) => `translate(0,${top + i * rowH})`);
    g.append('text').attr('x', W).attr('y', rowH / 2).attr('dy', '0.35em').attr('text-anchor', 'start').attr('direction', 'rtl')
      .style('font-size', '13px').style('font-weight', 600).text((d) => d.ar);
    g.append('rect').attr('x', (d) => W - labelW - Math.max(3, x(Number(d.title_pct)))).attr('y', 6)
      .attr('width', (d) => Math.max(3, x(Number(d.title_pct)))).attr('height', rowH - 12).attr('rx', 4)
      .style('fill', (d, i) => (i === 0 ? Z.H : 'var(--cds-chart-muted)'));
    g.append('text').attr('x', (d) => W - labelW - Math.max(3, x(Number(d.title_pct))) - gap).attr('y', rowH / 2).attr('dy', '0.35em')
      .attr('text-anchor', 'end').attr('direction', 'ltr').style('font-size', '12px').style('fill', 'var(--color-fg-muted)')
      .text((d) => Number(d.title_pct).toFixed(1) + '%');
  }

  function heatmap(host, rows, forecast) {
    Z.clear(host);
    const order = forecast.slice().sort((a, b) => Number(a.exp_pos) - Number(b.exp_pos));
    const names = {}; order.forEach((t) => { names[t.team] = t.ar; });
    const idx = {}; order.forEach((t, i) => { idx[t.team] = i; });
    const nPos = d3.max(rows, (r) => Number(r.pos));
    const avail = Math.max(0, (host.parentNode.clientWidth || 700) - 4);
    const tmp = d3.select(host).append('svg').attr('width', 10).attr('height', 10);
    let nameW = 0;
    order.forEach((t) => { nameW = Math.max(nameW, tmp.append('text').style('font-size', '12px').style('font-weight', 600).text(t.ar).node().getComputedTextLength()); });
    tmp.remove();
    const labelW = Math.ceil(nameW) + 12, top = 22;
    const cs = Math.max(22, Math.min(34, Math.floor((avail - labelW) / nPos)));
    const W = labelW + nPos * cs, H = top + order.length * cs + 2, fits = W <= avail;
    const svg = d3.select(host).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width', fits ? '100%' : W)
      .style('max-width', fits ? '100%' : 'none').attr('role', 'img').attr('aria-label', 'خريطة المراكز');
    const max = d3.max(rows, (r) => Number(r.pct)) || 1;
    const ramp = d3.interpolateRgb(Z.computed('var(--color-panel)'), Z.computed(Z.H));
    const px = (p) => W - labelW - p * cs;
    for (let p = 1; p <= nPos; p++) {
      svg.append('text').attr('x', px(p) + cs / 2).attr('y', 14).attr('text-anchor', 'middle').style('font-size', '11px').style('fill', 'var(--color-fg-muted)').text(p);
    }
    order.forEach((t, i) => {
      svg.append('text').attr('x', W - 2).attr('y', top + i * cs + cs / 2).attr('dy', '0.35em').attr('text-anchor', 'start').attr('direction', 'rtl')
        .style('font-size', '12px').style('font-weight', 600).text(names[t.team]);
    });
    const tp = Z.tip(host);
    svg.selectAll('rect.c').data(rows).enter().append('rect')
      .attr('x', (r) => px(Number(r.pos)) + 1).attr('y', (r) => top + idx[r.team] * cs + 1).attr('width', cs - 2).attr('height', cs - 2).attr('rx', 3)
      .style('fill', (r) => (Number(r.pct) > 0 ? ramp(0.12 + 0.88 * Math.sqrt(Number(r.pct) / max)) : 'var(--color-bg)'))
      .on('mousemove', (ev, r) => tp.show(ev, [names[r.team] + ' · المركز ' + r.pos, Number(r.pct).toFixed(1) + '٪']))
      .on('mouseleave', () => tp.hide());
    svg.selectAll('text.v').data(rows.filter((r) => Number(r.pct) >= 10)).enter().append('text')
      .attr('x', (r) => px(Number(r.pos)) + cs / 2).attr('y', (r) => top + idx[r.team] * cs + cs / 2).attr('dy', '0.35em')
      .attr('text-anchor', 'middle').style('font-size', '10px')
      .style('fill', (r) => (Number(r.pct) / max > 0.45 ? 'var(--color-bg)' : 'var(--color-fg)')).text((r) => Math.round(Number(r.pct)));
  }

  function pill(td, v, color) {
    td.textContent = '';
    const s = Z.el('span', 'pillv', v);
    const n = Number(v);
    if (n >= 0.5) s.style.background = `color-mix(in srgb, ${color} ${Math.round(12 + 0.55 * n)}%, transparent)`;
    td.appendChild(s);
  }

  function draw() {
    const sec = document.getElementById('season');
    if (!sec || !sec.dataset.ready) return;
    Z.fillMarks(sec);
    const f = Z.rows('forecast'), p = Z.rows('positions'), t = Z.rows('table_now');
    const tc = document.getElementById('title-chart'), hm = document.getElementById('heatmap');
    if (f) { titleChart(tc, f); } else Z.fail(tc, 'forecast');
    if (f && p) heatmap(hm, p, f); else Z.fail(hm, 'positions');
    const pt = document.querySelector('#proj-table tbody');
    Z.clear(pt);
    if (f) f.slice().sort((a, b) => Number(a.exp_pos) - Number(b.exp_pos)).forEach((r) => {
      const tr = Z.el('tr'); tr.dataset.key = r.team;
      tr.append(Z.el('td', 't', r.ar), Z.el('td', 'num', r.pts_now), Z.el('td', 'num', r.exp_pts), Z.el('td', 'num', r.pts_low), Z.el('td', 'num', r.pts_high));
      [['title_pct', Z.H], ['top4_pct', Z.H], ['europe_pct', Z.C[2]], ['releg_pct', Z.BAD]].forEach(([k, c]) => { const td = Z.el('td', 'num'); pill(td, r[k], c); tr.appendChild(td); });
      pt.appendChild(tr);
    });
    const nt = document.querySelector('#now-table tbody');
    Z.clear(nt);
    if (t) t.forEach((r) => {
      const tr = Z.el('tr'); tr.dataset.key = r.team;
      const pos = Number(r.pos);
      if (pos <= 4) tr.className = 'z-ucl'; else if (pos <= 6) tr.className = 'z-eur'; else if (pos > t.length - 3) tr.className = 'z-rel';
      tr.append(Z.el('td', 'num', r.pos), Z.el('td', 't', r.ar));
      ['P', 'W', 'D', 'L', 'GD', 'Pts'].forEach((k) => tr.appendChild(Z.el('td', 'num', r[k])));
      nt.appendChild(tr);
    });
  }
  Z.register('season', draw);
})();
