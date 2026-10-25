/* Today: what is on, who the model favours, what it means for the season, which story to post. */
(function () {
  "use strict";
  const ZS = window.ZS;
  const { h, pct, num, team, D } = ZS;
  const ui = () => ZS.ui;

  function pickDay(fixtures, now) {
    const today = ZS.dayKey(new Date(now));
    const todays = fixtures.filter((f) => f.kickoff_utc && ZS.dayKey(f.kickoff_utc) === today);
    if (todays.length) return { label: "مباريات اليوم", list: todays, today: true };
    const next = fixtures.filter((f) => f.kickoff_utc && new Date(f.kickoff_utc).getTime() > now && !f.score)
      .sort((a, b) => a.kickoff_utc.localeCompare(b.kickoff_utc));
    if (!next.length) return { label: "ماكو مباريات قادمة بالجدول", list: [], today: false };
    const day = ZS.dayKey(next[0].kickoff_utc);
    return { label: `المباريات الجاية: ${ZS.dateLong(next[0].kickoff_utc)}`, list: next.filter((f) => ZS.dayKey(f.kickoff_utc) === day), today: false };
  }

  async function render(view) {
    const now = Date.now();
    const fx = D.fixtures;
    const day = pickDay(fx, now);
    const md = day.list.length ? day.list[0].matchday : null;
    const fav = day.list.filter((f) => f.p).map((f) => ({ f, best: Math.max(...f.p), i: f.p.indexOf(Math.max(...f.p)) }))
      .sort((a, b) => b.best - a.best)[0];
    const leadBits = [];
    if (day.list.length) leadBits.push(`${ZS.countAr(day.list.length, "مباراة وحدة", "مباراتين", "مباريات", "مباراة")} ${day.today ? "اليوم" : "بالموعد الجاي"}.`);
    if (fav && fav.i !== 1) leadBits.push(`أوضح مرشح: ${team(fav.i === 0 ? fav.f.home : fav.f.away).ar} بنسبة ${pct(fav.best)}.`);
    view.appendChild(ui().pageHead(day.today ? "اليوم" : "الجاي", leadBits.join(" "), null,
      `${D.meta.competition.name_ar} ${D.meta.competition.season_label}${md ? ` · الجولة ${md}` : ""} · ${ZS.dateLong(new Date(now))}`));

    const grid = h("div.grid.g-main");
    const left = h("div.stack-lg");
    const right = h("div.stack-lg");
    grid.append(left, right);
    view.appendChild(grid);

    // ---- matches of the day
    const prefs = ZS.store.prefs();
    const ordered = day.list.slice().sort((a, b) => {
      const w = (f) => (prefs.watchlist.includes(f.match_id) || prefs.fav_teams.includes(f.home) || prefs.fav_teams.includes(f.away) ? 0 : 1);
      return w(a) - w(b) || (a.kickoff_utc || "").localeCompare(b.kickoff_utc || "");
    });
    const cards = h("div.grid.g-2");
    for (const f of ordered) cards.appendChild(ui().matchCard(f, { prev: f.prev_p || null, line: f.takeaway_ar || "" }));
    left.appendChild(ui().section(day.label, ordered.length ? cards : ui().empty("ماكو مباريات بهالموعد"),
      h("a.more", { href: ZS.href("matches", md ? "md" + md : "") }, "كل مباريات الجولة ←")));

    // ---- latest results (last finished matches)
    const done = fx.filter((f) => f.score).sort((a, b) => (b.kickoff_utc || "").localeCompare(a.kickoff_utc || "")).slice(0, 4);
    if (done.length) {
      const g = h("div.grid.g-2");
      for (const f of done) g.appendChild(ui().matchCard(f, { compact: false }));
      left.appendChild(ui().section("آخر النتائج", g, h("a.more", { href: ZS.href("matches", "md" + done[0].matchday) }, "النتائج كاملة ←")));
    }

    // ---- right column: story, title race, relegation (loaded in parallel; each fails on its own)
    const storySlot = h("div", ui().skeleton(1, 160));
    const raceSlot = h("div", ui().skeleton(1, 200));
    const impSlot = h("div", ui().skeleton(1, 160));
    const recSlot = h("div", ui().skeleton(1, 120));
    right.append(storySlot, raceSlot);
    left.append(impSlot);
    right.append(recSlot);

    ZS.getJSON("stories.json").then((js) => {
      ZS.clear(storySlot);
      const s = (js.stories || [])[0];
      if (!s) { storySlot.appendChild(ui().section("قصة تستاهل النشر", ui().empty("ماكو قصة واضحة بالأرقام هسه"))); return; }
      storySlot.appendChild(ui().section("قصة تستاهل النشر", storyCard(s, true), h("a.more", { href: ZS.href("studio") }, "كل القصص ←")));
    }).catch((e) => { ZS.clear(storySlot); storySlot.appendChild(ui().errorCard(e)); });

    ZS.getJSON("season.json").then((s) => {
      ZS.clear(raceSlot);
      raceSlot.appendChild(racePanel(s));
      ZS.clear(impSlot);
      impSlot.appendChild(importancePanel(s));
    }).catch((e) => { ZS.clear(raceSlot); raceSlot.appendChild(ui().errorCard(e)); ZS.clear(impSlot); });

    ZS.getJSON("accuracy.json").then((a) => { ZS.clear(recSlot); recSlot.appendChild(recordPanel(a)); })
      .catch((e) => { ZS.clear(recSlot); recSlot.appendChild(ui().errorCard(e)); });
  }

  function storyCard(s, withActions) {
    return h("article.card.story-card",
      h("div.row", h("span.tag.led", storyType(s.type)), s.sample ? h("span.tag", `العينة: ${s.sample}`) : null),
      h("h3", s.title_ar),
      h("p", s.text_ar),
      h("div.ev", (s.evidence || []).map((e) => h("span", `${e.label_ar}: `, h("strong.num", String(e.value))))),
      h("p.tiny.faint", `المقارنة: ${s.comparison_ar} · الفترة: ${s.period_ar}`),
      s.caution_ar ? h("p.tiny.faint", `تنبيه: ${s.caution_ar}`) : null,
      withActions ? h("div.row",
        h("a.btn.small.primary", { href: ZS.href("studio", "story-" + s.id) }, ui().icon("studio"), "سوّي منها بطاقة ونص"),
        h("button.btn.small", { type: "button", onclick: () => saveStory(s) }, ui().icon("star"), "احفظها")) : null);
  }
  function storyType(t) {
    return ({ results_vs_level: "النتائج مقابل المستوى", rating_trend: "اتجاه المستوى", high_stakes: "مباراة تحسم", title_race: "سباق اللقب",
      half_shift: "شوط بوجهين", creator_without_output: "يصنع بدون حصيلة" })[t] || "قصة";
  }
  async function saveStory(s) {
    const list = ZS.store.list("stories").filter((x) => x.id !== s.id);
    list.unshift({ id: s.id, title_ar: s.title_ar, text_ar: s.text_ar, type: s.type, saved_at: new Date().toISOString(), note: "" });
    await ZS.store.saveList("stories", list.slice(0, 100));
    ZS.toast("انحفظت بالاستوديو");
  }

  function racePanel(s) {
    const rows = s.projection.slice().sort((a, b) => b.p_title - a.p_title).filter((r) => r.p_title >= 0.005).slice(0, 4);
    const rel = s.projection.slice().sort((a, b) => b.p_releg - a.p_releg).slice(0, 4);
    const bar = (r, key, col) => h("div", { style: { display: "grid", gridTemplateColumns: "minmax(0,1fr) 54px", gap: "8px", alignItems: "center" } },
      h("div.stack", { style: { gap: "3px" } },
        ui().teamInline(r.id),
        h("div", { style: { height: "7px", background: "var(--inset)", borderRadius: "4px", overflow: "hidden" } },
          h("i", { style: { display: "block", height: "100%", width: `${Math.max(1, 100 * r[key])}%`, background: col } }))),
      h("strong.num", { style: { textAlign: "end", fontFamily: "var(--font-display)", fontSize: "1.1rem" } }, pct(r[key])));
    return h("section.card",
      h("div.card-head", h("h2", "سباق اللقب"), h("a.small", { href: ZS.href("season") }, "الموسم كامل ←")),
      h("div.stack", rows.map((r) => bar(r, "p_title", "var(--title)"))),
      h("hr.sep"),
      h("h3", { style: { marginTop: "6px" } }, "خطر الهبوط"),
      h("div.stack", rel.map((r) => bar(r, "p_releg", "var(--releg)"))),
      h("p.tiny.faint", { style: { marginTop: "8px" } }, s.mc_note_ar));
  }

  function importancePanel(s) {
    const imp = (s.importance || []).slice(0, 5);
    if (!imp.length) return ui().section("أهم المباريات للموسم", ui().empty("ماكو مباريات بالأيام الجاية"));
    const mx = Math.max(...imp.map((i) => i.importance), 1);
    const list = h("ol.list", imp.map((i, k) => {
      const f = D.fixturesById.get(i.match_id);
      const sw = i.swings && i.swings[0];
      const metric = { p_title: "اللقب", p_ucl: "دوري الأبطال", p_releg: "الهبوط" }[sw && sw.metric] || "";
      return h("li",
        h("strong.num", { style: { fontFamily: "var(--font-display)", fontSize: "1.2rem", minWidth: "22px" } }, String(k + 1)),
        h("div.stack.grow", { style: { gap: "4px" } },
          h("a", { href: ZS.href("match", i.match_id), style: { color: "var(--fg)", fontWeight: 800 } }, `${team(i.home_id).ar} × ${team(i.away_id).ar}`),
          sw ? h("span.small.muted", `${team(sw.team_id).ar} ب${metric}: ${pct(sw.home_win)} إذا فاز ${team(i.home_id).ar} · ${pct(sw.draw)} تعادل · ${pct(sw.away_win)} إذا فاز ${team(i.away_id).ar}`) : null,
          h("div", { style: { height: "6px", background: "var(--inset)", borderRadius: "3px" } },
            h("i", { style: { display: "block", height: "100%", width: `${(100 * i.importance) / mx}%`, background: "var(--led)", borderRadius: "3px" } }))),
        f && f.kickoff_utc ? h("span.small.faint.nowrap", ZS.dateShort(f.kickoff_utc)) : null);
    }));
    return ui().section("أهم المباريات للموسم هالأسبوع",
      h("div.card", list, h("p.tiny.faint", "الأهمية = مجموع تغيّر فرص اللقب ودوري الأبطال والهبوط بين فوز صاحب الأرض وفوز الضيف (بنفس المحاكاة). يعني حجم الرهان، مو شهرة الفريقين.")));
  }

  function recordPanel(a) {
    const t = a.prematch.test;
    const disp = a.registry.displayed_track;
    const s = t.scores[disp], b = t.scores.bet365;
    const live = (a.live_record && a.live_record.summary) || [];
    const mine = live.find((r) => r.track === disp);
    return h("section.card",
      h("div.card-head", h("h2", "دقة الحاسوب"), h("a.small", { href: ZS.href("method") }, "المنهجية كاملة ←")),
      h("div.kpis",
        h("div.kpi", h("span.k-val.num", pct(s.hit, 1)), h("span.k-lab", "اختيار النتيجة (فوز/تعادل/خسارة)"), h("span.k-sub", `${t.n} مباراة · ${t.seasons} · Bet365 ${pct(b.hit, 1)}`)),
        h("div.kpi", h("span.k-val.num", mine ? `${pct(mine.hit)}` : "—"), h("span.k-lab", "السجل الحي من هالموسم"),
          h("span.k-sub", mine ? `${mine.n} مباراة مسجلة قبل البداية` : "يبدأ يتحسب بعد أول مباريات مسجلة"))),
      h("p.tiny.faint", { style: { marginTop: "8px" } }, "الرقم الأول من اختبار على مواسم ما شافها الموديل وقت الضبط. الثاني من التوقعات المسجلة قبل صافرة البداية فقط."));
  }

  ZS.routes.today = { render, title: "اليوم", storyCard, saveStory, storyType };
})();
