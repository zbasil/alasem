/* Teams: the 20 clubs, then one card per team (form, level, results against chance quality, fixtures, chances). */
(function () {
  "use strict";
  const ZS = window.ZS;
  const { h, pct, num, team, D } = ZS;
  const ui = () => ZS.ui;
  const C = () => ZS.charts;

  async function renderList(view) {
    const s = await ZS.getJSON("season.json");
    const prefs = ZS.store.prefs();
    const proj = Object.fromEntries(s.projection.map((r) => [r.id, r]));
    view.appendChild(ui().pageHead("الفرق", "اضغطي على أي فريق لبطاقته: الفورمة، المستوى الحقيقي مقابل النتائج، المباريات الجاية وصعوبتها، وفرصه بالموسم. النجمة تخليه من فرقك المفضلة.", null, `${D.meta.competition.name_ar} ${D.meta.competition.season_label}`));
    const g = h("div.grid.g-auto-s");
    for (const r of s.table) {
      const pr = proj[r.id] || {};
      const fav = prefs.fav_teams.includes(r.id);
      g.appendChild(h("div.card.tight", { style: { display: "flex", flexDirection: "column", gap: "8px", position: "relative" } },
        h("div.row-between",
          h("a.team-inline", { href: ZS.href("team", r.id), style: { color: "var(--fg)", gap: "10px" } }, ui().crest(r.id, "m"),
            h("span.stack", { style: { gap: 0 } }, h("span.team-name", team(r.id).ar), h("span.tiny.faint", `المركز ${r.pos} · ${r.Pts} نقطة`))),
          favButton(r.id, fav)),
        h("div.chips", { style: { gap: "4px" } },
          pr.p_title >= 0.01 ? h("span.tag.led", `اللقب ${pct(pr.p_title)}`) : null,
          pr.p_ucl >= 0.01 ? h("span.tag", { style: { color: "var(--ucl)" } }, `الأبطال ${pct(pr.p_ucl)}`) : null,
          pr.p_releg >= 0.01 ? h("span.tag.bad", `الهبوط ${pct(pr.p_releg)}`) : null)));
    }
    view.appendChild(g);
  }
  function favButton(id, fav) {
    const b = h("button.icon-btn", { type: "button", "aria-pressed": String(fav), "aria-label": fav ? `شيلي ${team(id).ar} من المفضلة` : `ضيفي ${team(id).ar} للمفضلة`, style: { color: fav ? "var(--led)" : "var(--fg-3)" } }, ui().icon("star"));
    if (fav) b.querySelector("svg").setAttribute("fill", "currentColor");
    b.addEventListener("click", async () => {
      const p = ZS.store.prefs();
      const on = p.fav_teams.includes(id);
      await ZS.store.setPrefs({ fav_teams: on ? p.fav_teams.filter((x) => x !== id) : [...p.fav_teams, id] });
      const nb = favButton(id, !on);
      b.replaceWith(nb);
      ZS.toast(on ? "انشال من المفضلة" : "انضاف للمفضلة");
    });
    return b;
  }

  async function renderTeam(view, params) {
    const id = params.id;
    const [c, s] = await Promise.all([ZS.getJSON(`teams/${id}.json`), ZS.getJSON("season.json")]);
    const T = team(id);
    const prefs = ZS.store.prefs();
    const tot = c.totals;
    const row = s.table.find((r) => r.id === id) || {};
    const pr = s.projection.find((r) => r.id === id) || {};
    const places = s.rules.places;
    view.appendChild(h("div.row", h("a.btn.ghost.small", { href: ZS.href("teams") }, ui().icon("back"), "الفرق")));
    view.appendChild(h("section.card", { style: { display: "flex", gap: "16px", alignItems: "center", flexWrap: "wrap" } },
      ui().crest(id, "xl"),
      h("div.stack.grow", { style: { gap: "4px" } },
        h("h1", T.ar), h("span.muted", T.en),
        h("div.row.small", h("span.tag", `المركز ${row.pos ?? "—"}`), h("span.tag", `${row.Pts ?? 0} نقطة من ${row.P ?? 0} مباريات`),
          h("span.tag", `${row.W} فوز · ${row.D} تعادل · ${row.L} خسارة`), h("span.tag.num", `له ${row.GF} · عليه ${row.GA}`))),
      favButton(id, prefs.fav_teams.includes(id))));

    // ---- season chances
    view.appendChild(ui().section("فرصه بالموسم", h("div.card",
      h("div.kpis",
        h("div.kpi", h("span.k-val.num", num(pr.exp_pts, 0)), h("span.k-lab", "النقاط المتوقعة بالنهاية"), h("span.k-sub", `المدى الطبيعي ${num(pr.pts_p10, 0)}–${num(pr.pts_p90, 0)}`)),
        places.map((pl) => h("div.kpi", h("span.k-val.num", { style: { color: `var(--${pl.key === "title" ? "title" : pl.key})` } }, pct(pr["p_" + pl.key])), h("span.k-lab", pl.ar), h("span.k-sub", pl.from === pl.to ? `المركز ${pl.from}` : `المراكز ${pl.from}–${pl.to}`)))),
      h("div", { style: { marginTop: "12px" } }, h("div.small.muted", { style: { marginBottom: "4px" } }, "توزيع المراكز المتوقعة (المركز 1 على اليمين):"),
        C().posDist(pr.pos_dist || [], { places }),
        h("div.row-between.tiny.faint", h("span", "1"), h("span", "10"), h("span", "20"))),
      h("p.tiny.faint", { style: { marginTop: "8px" } }, s.mc_note_ar))));

    // ---- level vs results
    const gap = tot.pts - tot.xpts_pre;
    const noise = 1.2 * Math.sqrt(Math.max(tot.played, 1));
    const verdict = Math.abs(gap) < noise ? "النتائج قريبة من مستواه: الفرق ضمن التذبذب الطبيعي." : gap > 0 ? "جمع نقاط أكثر من المتوقع بوضوح: فعالية أو حظ، والعينة لسه صغيرة." : "جمع نقاط أقل من المتوقع بوضوح: سوء حظ أو مشكلة أعمق.";
    const lvl = h("div.grid.g-2",
      h("div.card", h("h3", "النتائج مقابل المستوى"),
        h("div.kpis",
          h("div.kpi", h("span.k-val.num", String(tot.pts)), h("span.k-lab", "النقاط الفعلية")),
          h("div.kpi", h("span.k-val.num", num(tot.xpts_pre, 1)), h("span.k-lab", "المتوقعة قبل المباريات")),
          h("div.kpi", h("span.k-val.num", h("span.delta." + (gap >= 0 ? "up" : "down"), ZS.signed(gap, 1))), h("span.k-lab", "الفرق"))),
        h("p.small", { style: { marginTop: "8px" } }, verdict),
        h("p.tiny.faint", `العينة ${tot.played} مباريات؛ التذبذب الطبيعي بحدود ±${num(noise, 1)} نقطة.`)),
      h("div.card", h("h3", "الأهداف مقابل المتوقع"),
        C().mirrorBars([
          { label: "سجّل / المتوقع له", home: tot.gf, away: tot.xg_for_pre, fmt: (v) => num(v, Number.isInteger(v) ? 0 : 1) },
          { label: "استقبل / المتوقع عليه", home: tot.ga, away: tot.xg_against_pre, fmt: (v) => num(v, Number.isInteger(v) ? 0 : 1) },
          { label: "تسديدات على المرمى له / عليه", home: tot.sot_for, away: tot.sot_against },
        ], [T.color, "var(--draw)"]),
        h("p.tiny.faint", { style: { marginTop: "8px" } }, "«المتوقع» هنا أهداف ما قبل المباراة من الموديل، مو xG الفرص (xG الفرص يحتاج بيانات أحداث).")));
    view.appendChild(ui().section("المستوى الحقيقي", lvl));

    // ---- form and trend
    const hist = c.rating_history || [];
    const trend = h("div.grid.g-2",
      h("div.card", h("h3", "آخر 5 مباريات"),
        h("ul.list", (c.form || []).slice().reverse().map((g) => h("li",
          h("span.form-strip", h("span.f." + g.result, { W: "ف", D: "ت", L: "خ" }[g.result])),
          h("a.grow", { href: ZS.href("match", g.match_id), style: { color: "var(--fg)" } }, `${g.home ? "ضد" : "عند"} ${team(g.opponent).ar}`),
          h("strong.num", ZS.scoreText(g.gf, g.ga)),
          h("span.small.faint.num", ZS.isNum(g.p_win_pre) ? `فوز ${pct(g.p_win_pre)}` : ""))))),
      h("div.card", h("h3", "اتجاه المستوى (تقييم الموديل الأسبوعي)"),
        hist.length >= 2 ? C().lines({ series: [
          { name: "الهجوم", color: T.color, values: hist.map((x) => x.attack) },
          { name: "الدفاع (أقل = أحسن)", color: "var(--fg-3)", values: hist.map((x) => x.defence), dash: true }],
        refLine: 1, xLabels: hist.map((x, i) => (i === 0 || i === hist.length - 1 ? ZS.dateShort(x.date + "T12:00:00Z") : "")), ariaLabel: "تقييم الهجوم والدفاع أسبوع بأسبوع" }) : ui().empty("يحتاج أسابيع أكثر"),
        h("p.tiny.faint", "1.00 = معدل الدوري. الأقدم على اليمين.")));
    view.appendChild(ui().section("الفورمة والاتجاه", trend));

    // ---- strengths and split
    const ha = c.home_away;
    view.appendChild(ui().section("الهجوم والدفاع، بالأرض وخارجها", h("div.grid.g-2",
      h("div.card", h("h3", "قوة الهجوم والدفاع حسب الموديل"),
        h("div.tbl-wrap", h("table.tbl", h("thead", h("tr", h("th", "المسار"), h("th.n", "الهجوم"), h("th.n", "الدفاع"))),
          h("tbody", Object.entries(c.ratings).map(([k, v]) => h("tr", h("td", ui().trackLabel(k)), h("td.n", num(v.attack, 2) + "×"), h("td.n", num(v.defence, 2) + "×")))))),
        h("p.tiny.faint", { style: { marginTop: "6px" } }, "الهجوم 1.30× = يسجل 30٪ أكثر من فريق معدل ضد نفس الخصم. الدفاع 0.80× = يستقبل 20٪ أقل.")),
      h("div.card", h("h3", "بالأرض وخارجها"),
        h("div.tbl-wrap", h("table.tbl", h("thead", h("tr", h("th", ""), h("th.n", "لعب"), h("th.n", "نقاط"), h("th.n", "له–عليه"), h("th.n", "نقاط/مباراة"))),
          h("tbody", [["home", "بالأرض"], ["away", "خارج الأرض"]].map(([k, lab]) => h("tr", h("td", lab), h("td.n", ha[k].played), h("td.n", ha[k].pts), h("td.n", `${ha[k].gf}–${ha[k].ga}`), h("td.n", num(ha[k].ppg, 2)))))))))));

    // ---- upcoming fixtures
    const up = c.upcoming || [];
    view.appendChild(ui().section("المباريات الجاية وصعوبتها", h("div.card",
      up.length ? h("ul.list", up.map((u) => {
        const diff = u.difficulty;
        return h("li",
          h("div.stack.grow", { style: { gap: "2px" } },
            h("a", { href: ZS.href("match", u.match_id), style: { color: "var(--fg)", fontWeight: 800 } }, `${u.home ? "ضد" : "عند"} ${team(u.opponent).ar}`),
            h("span.small.faint", `${u.kickoff.date ? ZS.dateLong(u.kickoff.date + "T12:00:00Z") : ""}${u.kickoff.time ? " · " + u.kickoff.time : " · الوقت غير محدد"}${u.rest_days != null ? ` · راحة ${u.rest_days} أيام` : ""}`)),
          h("div.stack", { style: { gap: "2px", alignItems: "flex-end", minWidth: "120px" } },
            h("span.small", ZS.isNum(diff) ? `صعوبة ${num(diff, 1)} من 3` : "—"),
            h("div", { style: { width: "110px", height: "7px", background: "var(--inset)", borderRadius: "4px" } },
              ZS.isNum(diff) ? h("i", { style: { display: "block", height: "100%", width: `${(100 * diff) / 3}%`, background: diff > 1.6 ? "var(--bad)" : diff > 1.1 ? "var(--led)" : "var(--good)", borderRadius: "4px" } }) : null)));
      })) : ui().empty("ماكو مباريات بالجدول"),
      h("p.tiny.faint", { style: { marginTop: "6px" } }, "الصعوبة = 3 ناقص النقاط المتوقعة من المباراة حسب الموديل (تشمل قوة الخصم والأرض). أيام الراحة من مباريات الدوري بس."))));

    // ---- absences
    const ab = c.absences || {};
    view.appendChild(ui().section("الغيابات", ab.status === "active"
      ? (ab.rows && ab.rows.length ? h("div.tbl-wrap", h("table.tbl", h("thead", h("tr", h("th", "اللاعب"), h("th", "الحالة"), h("th", "السبب"), h("th", "المباراة"))),
          h("tbody", ab.rows.map((r) => h("tr", h("td", r.player), h("td", r.type === "Missing Fixture" ? "غايب" : r.type === "Questionable" ? "مشكوك بمشاركته" : r.type), h("td", r.reason || "—"), h("td.small", r.date ? ZS.dateShort(r.date) : "—")))))) : h("p.small.muted", "ماكو غيابات مسجلة (API-Football)."))
      : h("div.notice", ui().icon("lock"), h("span", ab.text_ar || "الغيابات تحتاج مصدر تشكيلات"))));

    // ---- all matches
    view.appendChild(ui().section("كل مبارياته هالموسم", h("div.tbl-wrap", h("table.tbl",
      h("thead", h("tr", h("th", "التاريخ"), h("th", "الخصم"), h("th.n", "النتيجة"), h("th.n", "فوزه قبلها"), h("th.n", "المتوقع له–عليه"), h("th.n", "على المرمى"))),
      h("tbody", (c.matches || []).slice().reverse().map((g) => h("tr",
        h("td", ZS.dateShort(g.date + "T12:00:00Z")),
        h("td", h("a", { href: ZS.href("match", g.match_id), style: { color: "var(--fg)", fontWeight: 700 } }, `${g.home ? "" : "@ "}${team(g.opponent).ar}`)),
        h("td.n", h("span.form-strip", h("span.f." + g.result, { style: { width: "auto", padding: "0 6px" } }, ZS.scoreText(g.gf, g.ga)))),
        h("td.n", pct(g.p_win_pre)), h("td.n", ZS.isNum(g.xg_for_pre) ? `${num(g.xg_for_pre, 1)}–${num(g.xg_against_pre, 1)}` : "—"),
        h("td.n", ZS.isNum(g.sot_for) ? `${num(g.sot_for, 0)}–${num(g.sot_against, 0)}` : "—"))))))));
    view.appendChild(h("ul.small.faint", { style: { paddingInlineStart: "18px" } }, (c.notes_ar || []).map((n) => h("li", n))));
  }

  ZS.routes.teams = { render: renderList, title: "الفرق" };
  ZS.routes.team = { render: renderTeam, title: "الفريق" };
})();
