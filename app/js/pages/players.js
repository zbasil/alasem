/* Players (archive season with event data): per-90 numbers by position, percentiles, ratings and comparisons. */
(function () {
  "use strict";
  const ZS = window.ZS;
  const { h, num, team } = ZS;
  const ui = () => ZS.ui;

  const SHOW = {
    FW: ["np_goals", "np_xg", "xa", "shots", "touches_box", "dribbles", "pressures_high"],
    AM: ["xa", "key_passes", "np_xg", "dribbles", "prog_carries", "prog_passes", "np_goals"],
    CM: ["prog_passes", "pass_pct", "xa", "key_passes", "tackles_int", "recoveries", "pressures"],
    DM: ["tackles_int", "recoveries", "prog_passes", "pass_pct", "pressures", "blocks"],
    FB: ["tackles_int", "prog_passes", "prog_carries", "xa", "crosses", "recoveries", "dribbles"],
    CB: ["tackles_int", "clearances", "aerials_won", "blocks", "pass_pct", "prog_passes"],
    GK: ["save_pct", "goals_prevented"],
  };
  const fmtMetric = (k, v) => (v === null || v === undefined ? "—" : k === "pass_pct" || k === "save_pct" ? num(v, 0) + "%" : num(v, 2));

  async function render(view, params) {
    const js = await ZS.getJSON("players.json");
    if (!js.players || !js.players.length) {
      view.appendChild(ui().pageHead("اللاعبين", "", null, "الأرشيف"));
      view.appendChild(ui().empty("ملف اللاعبين ما انبنى بعد (python scripts/sb_players_1516.py)."));
      return;
    }
    const prefs = ZS.store.prefs();
    const saved = (prefs.filters && prefs.filters.players) || {};
    const st = { group: saved.group || "FW", enough: saved.enough !== false, sort: saved.sort || "rating", q: "", compare: [] };
    view.appendChild(ui().pageHead("اللاعبين",
      `${js.season_label} من بيانات الأحداث المفتوحة: أرقام لكل 90 دقيقة، ومقارنة كل لاعب بلاعبي نفس المركز بس. للاعبي الموسم الحالي تحتاج مزوّد إحصائيات لاعبين.`,
      h("a.btn.small", { href: ZS.href("archive") }, ui().icon("matches"), "مباريات الأرشيف"), js.source));
    const controls = h("div.stack");
    const body = h("div.stack-lg");
    view.append(controls, body);
    const groups = Object.entries(js.groups);
    function persist() { ZS.store.setPrefs({ filters: { ...(ZS.store.prefs().filters || {}), players: { group: st.group, enough: st.enough, sort: st.sort } } }); }
    function draw() {
      ZS.clear(controls).append(
        h("div.chips.scroll", { role: "toolbar", "aria-label": "المركز" }, groups.map(([g, lab]) => h("button.chip", { type: "button", "aria-pressed": String(st.group === g), onclick: () => { st.group = g; st.sort = "rating"; persist(); draw(); } }, lab))),
        h("div.row",
          h("input", { type: "search", placeholder: "ابحثي باسم اللاعب أو الفريق", "aria-label": "بحث", value: st.q, style: { maxWidth: "320px" }, oninput: (e) => { st.q = e.target.value; drawTable(); } }),
          h("label.row.small", { style: { gap: "6px" } }, h("input", { type: "checkbox", checked: st.enough, onchange: (e) => { st.enough = e.target.checked; persist(); drawTable(); } }), `${js.min_minutes} دقيقة أو أكثر بس (عينة كافية)`)));
      drawTable();
    }
    function drawTable() {
      ZS.clear(body);
      const keys = SHOW[st.group] || [];
      let rows = js.players.filter((p) => p.group === st.group && (!st.enough || p.enough_minutes));
      const q = st.q.trim().toLowerCase();
      if (q) rows = rows.filter((p) => p.name.toLowerCase().includes(q) || (p.team_name || "").toLowerCase().includes(q) || (team(p.team).ar || "").includes(st.q.trim()));
      const val = (p) => (st.sort === "rating" ? p.rating ?? -1 : st.sort === "minutes" ? p.minutes : (p.per90[st.sort] ?? -1));
      rows.sort((a, b) => val(b) - val(a));
      const favs = ZS.store.prefs().fav_players || [];
      const th = (k, lab) => h("th.n", h("button.btn.ghost.small", { type: "button", style: { minHeight: "30px", padding: "0 4px", fontWeight: st.sort === k ? 800 : 600, color: st.sort === k ? "var(--fg)" : "var(--fg-3)" }, onclick: () => { st.sort = k; persist(); drawTable(); } }, lab, st.sort === k ? " ↓" : ""));
      const weights = js.weights[st.group] || {};
      body.appendChild(h("div.tbl-wrap", h("table.tbl",
        h("thead", h("tr", h("th", ""), h("th", "اللاعب"), th("rating", "التقييم"), th("minutes", "الدقائق"), keys.map((k) => th(k, js.metrics_ar[k] || k)))),
        h("tbody", rows.slice(0, 120).map((p) => h("tr" + (favs.includes(p.player_id) ? ".mine" : ""),
          h("td", h("input", { type: "checkbox", "aria-label": `قارني ${p.name}`, checked: st.compare.includes(p.player_id), onchange: (e) => toggleCompare(p, e.target.checked) })),
          h("td", h("button.btn.ghost.small", { type: "button", style: { padding: "0 4px", fontWeight: 800, color: "var(--fg)" }, onclick: () => playerSheet(p) }, ui().crest(p.team, "s"), p.name)),
          h("td.n", h("strong", p.rating != null ? num(p.rating, 1) : "—")),
          h("td.n", String(p.minutes)),
          keys.map((k) => h("td.n", fmtMetric(k, p.per90[k]), p.pct && p.pct[k] != null ? h("span.tiny.faint", ` (${Math.round(100 * p.pct[k])})`) : null))))))));
      body.appendChild(h("p.tiny.faint", `التقييم (0–10) = 10 × متوسط ترتيب اللاعب بين ${js.groups[st.group]}ين بالأرقام اللي بالجدول، بأوزان: ${Object.entries(weights).map(([k, w]) => `${js.metrics_ar[k]} ${Math.round(100 * w)}٪`).join("، ")}. الرقم بين القوسين = ترتيب اللاعب المئوي بمركزه. هذا تقييم المشروع (${js.version})، مو تقييم مزوّد.`));
      if (st.compare.length) body.prepend(compareBox());
    }
    function toggleCompare(p, on) {
      st.compare = on ? [...st.compare.filter((x) => x !== p.player_id), p.player_id].slice(-2) : st.compare.filter((x) => x !== p.player_id);
      drawTable();
    }
    function compareBox() {
      const ps = st.compare.map((id) => js.players.find((p) => p.player_id === id)).filter(Boolean);
      if (ps.length < 2) return h("div.notice.led", ui().icon("info"), h("span", `اخترتي ${ps[0] ? ps[0].name : ""}. اختاري لاعب ثاني للمقارنة.`));
      const [a, b] = ps;
      const keys = [...new Set([...(SHOW[a.group] || []), ...(SHOW[b.group] || [])])];
      const cols = [team(a.team).color, ZS.colourDist(team(a.team).color, team(b.team).color) < 70 ? "var(--fg-3)" : team(b.team).color];
      return h("section.card", h("div.card-head", h("h2", `${a.name} × ${b.name}`), h("button.btn.small", { type: "button", onclick: () => { st.compare = []; drawTable(); } }, "سدّي المقارنة")),
        a.group !== b.group ? h("p.small.muted", `تنبيه: المركزين مختلفين (${a.group_ar} و${b.group_ar})، فالترتيب المئوي كل واحد بمركزه.`) : null,
        ZS.charts.mirrorBars(keys.map((k) => ({ label: `${js.metrics_ar[k]} (لكل 90)`, home: a.per90[k], away: b.per90[k], fmt: (v) => fmtMetric(k, v) })), cols),
        h("p.tiny.faint", { style: { marginTop: "8px" } }, `الدقائق: ${a.name} ${a.minutes}، ${b.name} ${b.minutes}. التقييم: ${a.rating ?? "—"} مقابل ${b.rating ?? "—"}.`));
    }
    function playerSheet(p) {
      const keys = SHOW[p.group] || [];
      const favs = ZS.store.prefs().fav_players || [];
      const on = favs.includes(p.player_id);
      ui().openSheet(p.name, h("div.stack",
        h("div.row", ui().teamInline(p.team, { link: false }), h("span.tag", p.group_ar), h("span.tag", `${p.minutes} دقيقة · ${p.matches} مباراة`)),
        h("div.kpis",
          h("div.kpi", h("span.k-val.num", p.rating != null ? num(p.rating, 1) : "—"), h("span.k-lab", "تقييم المشروع بمركزه")),
          h("div.kpi", h("span.k-val.num", `${p.np_goals}+${p.pens}`), h("span.k-lab", "أهداف (بدون جزاء + جزاء)")),
          h("div.kpi", h("span.k-val.num", String(p.assists)), h("span.k-lab", "صناعة")),
          h("div.kpi", h("span.k-val.num", `${num(p.np_xg, 1)} / ${num(p.xa, 1)}`), h("span.k-lab", "xG بدون جزاء / xA"))),
        h("div.stack", { style: { gap: "8px" } }, keys.map((k) => {
          const pc = p.pct && p.pct[k];
          return h("div", h("div.row-between.small", h("span", js.metrics_ar[k]), h("span.num", `${fmtMetric(k, p.per90[k])}${pc != null ? ` · الترتيب ${Math.round(100 * pc)}` : ""}`)),
            h("div", { style: { height: "7px", background: "var(--inset)", borderRadius: "4px" } }, pc != null ? h("i", { style: { display: "block", height: "100%", width: `${100 * pc}%`, background: "var(--pitch)", borderRadius: "4px" } }) : null));
        })),
        !p.enough_minutes ? h("p.small.muted", `أقل من ${js.min_minutes} دقيقة: الأرقام لكل 90 دقيقة متذبذبة وما ينحسب له تقييم.`) : null,
        h("button.btn.small", { type: "button", onclick: async () => {
          const cur = ZS.store.prefs().fav_players || [];
          await ZS.store.setPrefs({ fav_players: on ? cur.filter((x) => x !== p.player_id) : [...cur, p.player_id] });
          ui().closeSheet(); drawTable(); ZS.toast(on ? "انشال من المفضلين" : "انضاف للمفضلين");
        } }, ui().icon("star"), on ? "شيليه من المفضلين" : "ضيفيه للمفضلين")));
    }
    draw();
  }

  ZS.routes.players = { render, title: "اللاعبين" };
})();
