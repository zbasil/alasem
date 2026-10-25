/* Season: table, projection, changes, importance ranking and the "what if?" simulator. */
(function () {
  "use strict";
  const ZS = window.ZS;
  const { h, pct, num, team, D } = ZS;
  const ui = () => ZS.ui;
  const C = () => ZS.charts;

  function zoneOf(pos, places) {
    for (const pl of places) if (pl.key !== "title" && pos >= pl.from && pos <= pl.to) return pl.key;
    return "";
  }

  async function render(view) {
    const s = await ZS.getJSON("season.json");
    const places = s.rules.places;
    const prefs = ZS.store.prefs();
    view.appendChild(ui().pageHead("الموسم", `الترتيب الحالي، وتوقع نهاية الموسم من ${num(s.n_sims, 0)} موسم محاكى بقواعد الليغا (المواجهات المباشرة ثم فارق الأهداف). وتحت: جربي «ماذا لو؟» بنتائج من اختيارك.`, null,
      `${D.meta.competition.name_ar} ${s.season_label} · آخر تحديث ${ZS.ago(s.generated_utc)}`));

    const TABS = [["projection", "التوقع"], ["table", "الترتيب الآن"], ["whatif", "ماذا لو؟"], ["importance", "أهم المباريات"], ["rules", "القواعد"]];
    let tab = "projection";
    const tabs = h("div.tabs", { role: "tablist" });
    const panel = h("div.stack-lg", { role: "tabpanel" });
    TABS.forEach(([k, lab]) => tabs.appendChild(h("button", { type: "button", role: "tab", id: "stab-" + k, "aria-selected": String(tab === k),
      onclick: () => { tab = k; ZS.$$("button", tabs).forEach((b) => b.setAttribute("aria-selected", String(b.id === "stab-" + k))); draw(); } }, lab)));
    view.append(tabs, panel);

    const legend = h("div.legend-row", places.filter((p) => p.key !== "title").map((pl) => h("span", h("i", { style: { background: `var(--${pl.key})` } }), `${pl.ar} (${pl.from === pl.to ? pl.from : pl.from + "–" + pl.to})`)));

    function draw() {
      ZS.clear(panel);
      if (tab === "projection") drawProjection();
      else if (tab === "table") drawTable();
      else if (tab === "whatif") drawWhatIf();
      else if (tab === "importance") drawImportance();
      else drawRules();
    }

    function drawProjection() {
      const rows = s.projection.slice().sort((a, b) => b.exp_pts - a.exp_pts);
      const tbl = h("div.tbl-wrap", h("table.tbl",
        h("thead", h("tr", h("th", "#"), h("th", "الفريق"), h("th.n", "الآن"), h("th.n", "المتوقع"), h("th.n", "المدى"),
          places.map((pl) => h("th.n", pl.ar)), h("th", { style: { minWidth: "220px" } }, "توزيع المراكز (1 ← 20)"))),
        h("tbody", rows.map((r, i) => h("tr" + (prefs.fav_teams.includes(r.id) ? ".mine" : "") + (zoneOf(i + 1, places) ? ".zone-" + zoneOf(i + 1, places) : ""),
          h("td.n", String(i + 1)),
          h("td", h("div.team-cell", ui().crest(r.id, "s"), h("a", { href: ZS.href("team", r.id) }, team(r.id).ar))),
          h("td.n", String(r.pts_now)), h("td.n", h("strong", num(r.exp_pts, 0))), h("td.n.faint", `${num(r.pts_p10, 0)}–${num(r.pts_p90, 0)}`),
          places.map((pl) => h("td.n", cellPct(r["p_" + pl.key], pl.key))),
          h("td", C().posDist(r.pos_dist, { places })))))));
      panel.append(legend, tbl,
        h("p.tiny.faint", `${s.mc_note_ar}. «المدى» = 80٪ من المواسم المحاكاة تنتهي بهالنقاط. المراكز الأوروبية حسب ملف القواعد للموسم (${s.rules.notes_ar || ""}).`));
      if (s.changes && s.changes.length) {
        panel.appendChild(ui().section("شنو تغيّر من آخر تحديث؟", h("div.tbl-wrap", h("table.tbl",
          h("thead", h("tr", h("th", "الفريق"), h("th", "الفرصة"), h("th.n", "قبل"), h("th.n", "هسه"), h("th.n", "التغيير"), h("th", "حقيقي لو ضجيج؟"))),
          h("tbody", s.changes.slice().sort((a, b) => Math.abs(b.delta_pts) - Math.abs(a.delta_pts)).slice(0, 14).map((c) => h("tr",
            h("td", ui().teamInline(c.id)), h("td", (places.find((p) => "p_" + p.key === c.metric) || {}).ar || c.metric),
            h("td.n", pct(c.before)), h("td.n", pct(c.now)), h("td.n", h("span.delta." + (c.delta_pts > 0 ? "up" : "down"), ZS.signed(c.delta_pts, 1))),
            h("td.small", c.is_noise ? h("span.faint", `ضمن ضجيج المحاكاة (±${num(c.noise_pts, 1)})`) : h("span", "تغيير بالبيانات")))))))));
      } else {
        panel.appendChild(h("p.small.faint", "ماكو تحديث سابق للمقارنة بعد، أو ما تغيّر شي يذكر."));
      }
    }
    function cellPct(v, key) {
      if (!ZS.isNum(v) || v < 0.0005) return h("span.faint", "—");
      return h("span.cellbar", h("i", { style: { width: `${Math.max(2, 46 * v)}px`, background: `var(--${key === "title" ? "title" : key})` } }), pct(v));
    }

    function drawTable() {
      panel.append(legend, h("div.tbl-wrap", h("table.tbl",
        h("thead", h("tr", ["#", "الفريق", "لعب", "فاز", "تعادل", "خسر", "له", "عليه", "الفارق", "النقاط"].map((x, i) => h(i === 1 ? "th" : "th.n", x)))),
        h("tbody", s.table.map((r) => h("tr" + (prefs.fav_teams.includes(r.id) ? ".mine" : "") + (zoneOf(r.pos, places) ? ".zone-" + zoneOf(r.pos, places) : ""),
          h("td.n", String(r.pos)), h("td", h("div.team-cell", ui().crest(r.id, "s"), h("a", { href: ZS.href("team", r.id) }, team(r.id).ar))),
          [r.P, r.W, r.D, r.L, r.GF, r.GA].map((v) => h("td.n", String(v))), h("td.n", ZS.signed(r.GD)), h("td.n", h("strong", String(r.Pts)))))))),
        h("p.tiny.faint", "الترتيب بنفس قواعد كسر التعادل الرسمية (المواجهات المباشرة إذا لعبوا ذهاب وإياب، ثم فارق الأهداف، ثم الأهداف)."));
    }

    // ---------------------------------------------------------------- what if
    const W = s.whatif;
    const fixtureIdx = new Map(W.fixtures.map((f, i) => [f.match_id, i]));
    const scenario = {}; // fixture index -> {outcome} | {score}
    let lastResult = null;
    function drawWhatIf() {
      const mds = [...new Set(W.fixtures.map((f) => (D.fixturesById.get(f.match_id) || {}).matchday).filter(Boolean))].sort((a, b) => a - b);
      let md = mds[0];
      const mdSel = h("select#wi-md", { style: { width: "auto" }, "aria-label": "الجولة" }, mds.map((m) => h("option", { value: m }, `الجولة ${m}`)));
      const list = h("div.stack");
      const resBox = h("div.stack");
      const runBtn = h("button.btn.primary", { type: "button" }, ui().icon("spark"), "احسبي السيناريو");
      const resetBtn = h("button.btn", { type: "button" }, ui().icon("refresh"), "إعادة ضبط");
      const count = h("span.small.muted");
      const box = h("section.scenario",
        h("div.scen-head", h("div.row", h("h2", "ماذا لو؟"), ui().trackTag("scenario")), h("span.small.muted", "سيناريو تجريبي منفصل عن التوقع الرسمي")),
        h("p.small.muted", "اختاري نتيجة لأي مباراة جاية (فوز/تعادل/خسارة أو نتيجة بالأرقام)، والحاسوب يعيد محاكاة الموسم ويبين الفرق بالنقاط المئوية مقارنة بنفس المحاكاة بدون اختياراتك."),
        h("div.row", mdSel, count), list,
        h("div.row", runBtn, resetBtn), resBox);
      panel.appendChild(box);
      function countText() {
        const n = Object.keys(scenario).length;
        count.textContent = n ? `اخترتي ${ZS.countAr(n, "نتيجة وحدة", "نتيجتين", "نتائج", "نتيجة")}` : "ما اخترتي أي نتيجة بعد";
      }
      function drawList() {
        ZS.clear(list);
        const fs = W.fixtures.map((f, i) => ({ ...f, i, fx: D.fixturesById.get(f.match_id) })).filter((f) => f.fx && f.fx.matchday === Number(md));
        for (const f of fs) {
          const cur = scenario[f.i];
          const H = team(f.fx.home), A = team(f.fx.away);
          const opt = (k, lab) => h("button", { type: "button", "aria-pressed": String(!!cur && cur.outcome === k && !cur.score), onclick: () => {
            if (cur && cur.outcome === k && !cur.score) delete scenario[f.i]; else scenario[f.i] = { outcome: k };
            drawList(); countText();
          } }, lab);
          const hs = h("input", { type: "number", min: 0, max: 9, "aria-label": `أهداف ${H.ar}`, value: cur && cur.score ? cur.score[0] : "", style: { width: "58px" } });
          const as = h("input", { type: "number", min: 0, max: 9, "aria-label": `أهداف ${A.ar}`, value: cur && cur.score ? cur.score[1] : "", style: { width: "58px" } });
          const setScore = () => {
            if (hs.value === "" || as.value === "") { if (scenario[f.i] && scenario[f.i].score) delete scenario[f.i]; countText(); return; }
            const a = Math.max(0, Math.min(9, Number(hs.value))), b = Math.max(0, Math.min(9, Number(as.value)));
            scenario[f.i] = { score: [a, b], outcome: a > b ? "H" : a === b ? "D" : "A" };
            countText();
            ZS.$$(".seg button", row).forEach((btn) => btn.setAttribute("aria-pressed", "false"));
          };
          hs.addEventListener("change", setScore); as.addEventListener("change", setScore);
          const row = h("div.panel", { style: { display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center", justifyContent: "space-between" } },
            h("div.row", { style: { minWidth: "200px" } }, ui().teamInline(f.fx.home, { link: false }), h("span.faint", "×"), ui().teamInline(f.fx.away, { link: false })),
            h("div.seg", { role: "group", "aria-label": "النتيجة" }, opt("H", `فوز ${H.ar}`), opt("D", "تعادل"), opt("A", `فوز ${A.ar}`)),
            h("div.row", { style: { gap: "4px" } }, hs, h("span", "–"), as),
            h("span.tiny.faint.num", f.fx.p ? `الرسمي ${pct(f.fx.p[0])} / ${pct(f.fx.p[1])} / ${pct(f.fx.p[2])}` : ""));
          list.appendChild(row);
        }
      }
      mdSel.addEventListener("change", () => { md = mdSel.value; drawList(); });
      resetBtn.addEventListener("click", () => { for (const k of Object.keys(scenario)) delete scenario[k]; lastResult = null; ZS.clear(resBox); drawList(); countText(); });
      runBtn.addEventListener("click", async () => {
        if (!Object.keys(scenario).length) { ZS.toast("اختاري نتيجة وحدة على الأقل"); return; }
        runBtn.disabled = true;
        const prog = h("progress", { max: 1, value: 0, style: { width: "100%" } });
        ZS.clear(resBox).append(h("p.small.muted", "جاري المحاكاة…"), prog);
        try {
          const res = await ZS.models.simulateSeason({ ...W }, [{ name: "base", fixed: {} }, { name: "scenario", fixed: { ...scenario } }],
            { nSims: 10000, seed: 2026, onProgress: (p) => { prog.value = p; } });
          lastResult = res;
          drawResult(res);
        } catch (e) { ZS.clear(resBox).append(ui().errorCard(e)); }
        runBtn.disabled = false;
      });
      function drawResult(res) {
        const base = Object.fromEntries(res.results[0].rows.map((r) => [r.team, r]));
        const sc = res.results[1].rows;
        const keys = places.map((p) => "p_" + p.key);
        const changed = sc.map((r) => ({ r, b: base[r.team], d: keys.reduce((m, k) => m + Math.abs(r[k] - base[r.team][k]), 0) + Math.abs(r.exp_pts - base[r.team].exp_pts) / 10 }))
          .sort((x, y) => y.r.exp_pts - x.r.exp_pts);
        ZS.clear(resBox).append(
          h("div.notice.led", ui().icon("info"), h("span", `النتيجة من ${num(res.nSims, 0)} موسم بنفس الأرقام العشوائية للسيناريو والأساس، فالفرق سببه اختياراتك مو الصدفة. أرقام الأساس ممكن تختلف شوية عن التوقع الرسمي (محاكاة ثانية).`)),
          h("div.tbl-wrap", h("table.tbl",
            h("thead", h("tr", h("th", "الفريق"), h("th.n", "النقاط المتوقعة"), places.map((pl) => h("th.n", pl.ar)))),
            h("tbody", changed.map(({ r, b }) => h("tr" + (prefs.fav_teams.includes(r.team) ? ".mine" : ""),
              h("td", ui().teamInline(r.team)),
              h("td.n", num(r.exp_pts, 1), " ", deltaSpan(r.exp_pts - b.exp_pts, 1, "")),
              keys.map((k) => h("td.n", pct(r[k]), " ", deltaSpan(100 * (r[k] - b[k]), 1, "")))))))),
          h("p.tiny.faint", "الرقم الصغير الملوّن = الفرق عن الأساس بالنقاط المئوية (أو بالنقاط للنقاط المتوقعة). ماكو رقم = ماكو تغيير يذكر."));
      }
      mdSel.value = String(md);
      drawList(); countText();
      if (lastResult) drawResult(lastResult);
    }
    function deltaSpan(d, digits, unit) {
      if (!ZS.isNum(d) || Math.abs(d) < (digits ? 0.5 : 1) / 1) return null;
      return h("span.delta." + (d > 0 ? "up" : "down"), { style: { fontSize: ".78rem" } }, `${ZS.signed(d, digits)}${unit}`);
    }

    // ---------------------------------------------------------------- importance
    function drawImportance() {
      const imp = s.importance || [];
      const metric = { p_title: "اللقب", p_ucl: "دوري الأبطال", p_releg: "الهبوط" };
      const mx = Math.max(1, ...imp.map((i) => i.importance));
      panel.appendChild(h("section.card",
        h("h2", "ترتيب المباريات الجاية حسب أثرها على السباق"),
        h("p.small.muted", "لكل مباراة: الموسم ينعاد محاكاته ثلاث مرات (فوز صاحب الأرض، تعادل، فوز الضيف) بنفس الأرقام العشوائية. الأهمية = مجموع تغيّر فرص اللقب ودوري الأبطال والهبوط لكل الفرق."),
        imp.length ? h("ol.list", imp.map((i, k) => h("li",
          h("strong.num", { style: { minWidth: "24px", fontFamily: "var(--font-display)" } }, String(k + 1)),
          h("div.stack.grow", { style: { gap: "3px" } },
            h("a", { href: ZS.href("match", i.match_id), style: { color: "var(--fg)", fontWeight: 800 } }, `${team(i.home_id).ar} × ${team(i.away_id).ar}`),
            h("span.small.muted", (i.swings || []).slice(0, 2).map((sw) => `${team(sw.team_id).ar} ب${metric[sw.metric]}: ${pct(sw.home_win)} / ${pct(sw.draw)} / ${pct(sw.away_win)}`).join(" · ")),
            h("div", { style: { height: "6px", background: "var(--inset)", borderRadius: "3px" } }, h("i", { style: { display: "block", height: "100%", width: `${(100 * i.importance) / mx}%`, background: "var(--led)", borderRadius: "3px" } }))),
          h("span.num.small", num(i.importance, 1))))) : ui().empty("ماكو مباريات بالأيام الثمانية الجاية")));
      // compute any matchday in the browser
      const mds = [...new Set(W.fixtures.map((f) => (D.fixturesById.get(f.match_id) || {}).matchday).filter(Boolean))].sort((a, b) => a - b);
      const sel = h("select", { style: { width: "auto" }, "aria-label": "الجولة" }, mds.map((m) => h("option", { value: m }, `الجولة ${m}`)));
      const out = h("div.stack");
      const btn = h("button.btn", { type: "button" }, ui().icon("spark"), "رتّبي مباريات هالجولة");
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        const md = Number(sel.value);
        const fs = W.fixtures.map((f, i) => ({ ...f, i, fx: D.fixturesById.get(f.match_id) })).filter((f) => f.fx && f.fx.matchday === md);
        const scen = [{ name: "base", fixed: {} }];
        for (const f of fs) for (const oc of ["H", "D", "A"]) scen.push({ name: `${f.i}|${oc}`, fixed: { [f.i]: { outcome: oc } } });
        const prog = h("progress", { max: 1, value: 0, style: { width: "100%" } });
        ZS.clear(out).append(h("p.small.muted", "جاري الحساب…"), prog);
        try {
          const res = await ZS.models.simulateSeason({ ...W }, scen, { nSims: 2000, seed: 7, onProgress: (p) => { prog.value = p; } });
          const by = Object.fromEntries(res.results.map((r) => [r.name, Object.fromEntries(r.rows.map((x) => [x.team, x]))]));
          const ranked = fs.map((f) => {
            let tot = 0;
            for (const t of W.team_ids) for (const k of ["p_title", "p_ucl", "p_releg"]) tot += Math.abs(by[`${f.i}|H`][t][k] - by[`${f.i}|A`][t][k]);
            return { f, imp: 100 * tot };
          }).sort((a, b) => b.imp - a.imp);
          const mx2 = Math.max(1, ...ranked.map((x) => x.imp));
          ZS.clear(out).append(h("ol.list", ranked.map((x, k) => h("li",
            h("strong.num", { style: { minWidth: "24px" } }, String(k + 1)),
            h("a.grow", { href: ZS.href("match", x.f.match_id), style: { color: "var(--fg)", fontWeight: 700 } }, `${team(x.f.fx.home).ar} × ${team(x.f.fx.away).ar}`),
            h("div", { style: { width: "120px", height: "6px", background: "var(--inset)", borderRadius: "3px" } }, h("i", { style: { display: "block", height: "100%", width: `${(100 * x.imp) / mx2}%`, background: "var(--led)", borderRadius: "3px" } })),
            h("span.num.small", num(x.imp, 1))))),
            h("p.tiny.faint", `محسوبة بالمتصفح من ${num(res.nSims, 0)} موسم لكل نتيجة؛ تقريبية أكثر من الرقم الرسمي فوق.`));
        } catch (e) { ZS.clear(out).append(ui().errorCard(e)); }
        btn.disabled = false;
      });
      panel.appendChild(h("section.scenario", h("div.scen-head", h("h2", "رتّبي أي جولة"), ui().trackTag("scenario")), h("div.row", sel, btn), out));
    }

    function drawRules() {
      panel.appendChild(h("section.card", h("h2", "قواعد الموسم"),
        h("p", s.rules.tiebreak ? s.rules.tiebreak.ar : ""),
        h("ul.list", places.map((pl) => h("li", h("i", { style: { width: "14px", height: "14px", borderRadius: "4px", background: `var(--${pl.key === "title" ? "title" : pl.key})`, marginTop: "6px" } }),
          h("span", `${pl.ar}: ${pl.from === pl.to ? "المركز " + pl.from : "المراكز " + pl.from + "–" + pl.to}`)))),
        s.rules.notes_ar ? h("div.notice.led", ui().icon("info"), h("span", s.rules.notes_ar)) : null,
        h("p.small.faint", "القواعد والمراكز تنقرأ من ملف config/competitions/ESP1.json لكل موسم، فتتعدل بدون تغيير الكود.")));
    }
    draw();
  }

  ZS.routes.season = { render, title: "الموسم" };
})();
