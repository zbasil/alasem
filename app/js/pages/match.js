/* Match centre: a clear summary first, then reasons, numbers, events and scenarios.
   Also the deep-analysis archive pages (StatsBomb open data) with pitch maps. */
(function () {
  "use strict";
  const ZS = window.ZS;
  const { h, pct, num, pp, team, D } = ZS;
  const ui = () => ZS.ui;
  const C = () => ZS.charts;

  const TRACK_ORDER = ["market", "independent", "sportradar"];

  async function render(view, params) {
    const mid = params.id;
    view.appendChild(ui().skeleton(2, 160));
    const mf = await ZS.matchFile(mid);
    const f = D.fixturesById.get(mid);
    const [homeCard, awayCard] = await Promise.all([
      ZS.getJSON(`teams/${mf.home}.json`).catch(() => null), ZS.getJSON(`teams/${mf.away}.json`).catch(() => null)]);
    ZS.clear(view);
    const prefs = ZS.store.prefs();
    const H = team(mf.home), A = team(mf.away);
    const colours = ZS.pairColours(H, A);
    const played = !!mf.score;
    const live = mf.live;
    const available = TRACK_ORDER.filter((t) => mf.tracks[t]);
    // page state shared by every tab (selections persist across tabs)
    const st = {
      track: available.includes(prefs.track) ? prefs.track : (available.includes(mf.displayed_track) ? mf.displayed_track : available[0]),
      tab: "summary", part: live && live.stats && live.stats.second_half ? "full" : (live ? "first_half" : "full"),
      minute: null, scenario: null,
    };

    view.appendChild(h("div.row", h("a.btn.ghost.small", { href: ZS.href("matches", "md" + mf.matchday) }, ui().icon("back"), `الجولة ${mf.matchday}`)));

    // ---------------------------------------------------------------- header
    const head = h("section.card", { style: { display: "flex", flexDirection: "column", gap: "14px" } });
    view.appendChild(head);
    const followBtn = h("button.btn.small", { type: "button", "aria-pressed": String(prefs.watchlist.includes(mid)) });
    function drawFollow() {
      const on = ZS.store.prefs().watchlist.includes(mid);
      followBtn.setAttribute("aria-pressed", String(on));
      ZS.clear(followBtn).append(ui().icon(on ? "check" : "star"), on ? "متابَعة ومثبّتة" : "تابعي وثبّتي");
    }
    followBtn.addEventListener("click", async () => {
      const p = ZS.store.prefs();
      const on = p.watchlist.includes(mid);
      await ZS.store.setPrefs({ watchlist: on ? p.watchlist.filter((x) => x !== mid) : [...p.watchlist, mid] });
      drawFollow();
      ZS.toast(on ? "شلتها من المتابعة" : "تنضاف للمتابعة: تطلع أول شي باليوم وتجيج تنبيهاتها");
    });
    drawFollow();
    const statusLine = h("div.row-between",
      h("div.row", ui().pill(f || mf), h("span.small.muted", `الجولة ${mf.matchday} · ${ui().kickoffLabel(mf)} بتوقيت بغداد`)),
      h("div.row", followBtn));
    const scoreBlock = played
      ? h("div.sb-mid", h("div.sb-score", { style: { fontSize: "2.6rem" }, "aria-label": `النتيجة ${H.ar} ${mf.score[0]}، ${A.ar} ${mf.score[1]}` },
        h("span.g", mf.score[0]), h("span.sep", "–"), h("span.g", mf.score[1])),
        mf.ht ? h("span.sb-sub", `الشوط الأول ${ZS.scoreText(mf.ht[0], mf.ht[1])}`) : null)
      : live && live.score
        ? h("div.sb-mid", h("div.sb-score", { style: { fontSize: "2.6rem" } }, h("span.g", live.score[0]), h("span.sep", "–"), h("span.g", live.score[1])),
          h("span.sb-sub", live.phase === "HT" ? "نهاية الشوط الأول" : "النتيجة"))
        : h("div.sb-mid", h("span.sb-time", { style: { fontSize: "2rem" } }, mf.kickoff_utc ? ZS.timeHM(mf.kickoff_utc) : "—"),
          h("span.sb-sub", mf.kickoff_utc ? ZS.dateShort(mf.kickoff_utc) : "الموعد غير محدد"));
    head.append(statusLine,
      h("div.sb-teams",
        h("a.sb-team.wide", { href: ZS.href("team", mf.home), style: { color: "var(--fg)" } }, ui().crest(mf.home, "l"), h("div.stack", { style: { gap: 0 } }, h("span.team-name", { style: { fontSize: "1.25rem", fontFamily: "var(--font-display)" } }, H.ar), h("span.tiny.faint", "صاحب الأرض"))),
        scoreBlock,
        h("a.sb-team.wide.away", { href: ZS.href("team", mf.away), style: { color: "var(--fg)" } }, ui().crest(mf.away, "l"), h("div.stack", { style: { gap: 0, alignItems: "flex-end" } }, h("span.team-name", { style: { fontSize: "1.25rem", fontFamily: "var(--font-display)" } }, A.ar), h("span.tiny.faint", "الضيف")))));
    const forecastBox = h("div.stack");
    head.appendChild(forecastBox);
    // version 3.1: ESPN live layer (events, line-ups, stats) for matches the SportRadar session did not cover
    const espnBox = h("div");
    view.appendChild(espnBox);
    const drawEspn = () => {
      ZS.clear(espnBox);
      const fx = f || {};
      if (played || !ZS.live || !fx.live) return;
      const sc = ZS.hub && ZS.hub.scoreOf(fx);
      if (sc && !(live && live.score)) espnBox.appendChild(h("div.notice.pitch", ui().icon("info"), h("span", `النتيجة المباشرة: ${H.ar} ${sc[0]} – ${sc[1]} ${A.ar}${fx.live.clock ? " · " + fx.live.clock : ""}`)));
      const p = ZS.live.panel(fx);
      if (p) espnBox.appendChild(ui().section("مباشر من ESPN", p));
    };
    drawEspn();
    const offLive = ZS.on("live", drawEspn);

    function shownForecast() {
      // live state beats the pre-match forecast once a live report exists
      if (live && live.reports) {
        const rep = live.reports.FT || live.reports.HT;
        if (rep && rep.now && !played) return { kind: "live", p: rep.now.p, phase: live.reports.FT ? "FT" : "HT", pre: rep.pre_match && rep.pre_match.p, issued_at: rep.generated_at };
      }
      const t = mf.tracks[st.track];
      return t ? { ...t, kindLabel: t.kind } : null;
    }
    function drawForecast() {
      ZS.clear(forecastBox);
      const t = shownForecast();
      const seg = h("div.seg", { role: "group", "aria-label": "مصدر التوقع" }, available.map((k) =>
        h("button", { type: "button", "aria-pressed": String(st.track === k), onclick: () => { st.track = k; ZS.store.setPrefs({ track: k === "sportradar" ? ZS.store.prefs().track : k }); drawForecast(); drawTab(); } }, ui().trackLabel(k))));
      const kindTag = t ? (t.kind === "live" ? ui().trackTag("live") : t.kind === "retro" ? h("span.tag", "توقع استرجاعي") : t.kind === "published" ? h("span.tag", "منشور من SportRadar") : h("span.tag.pitch", "قبل المباراة")) : null;
      forecastBox.append(h("div.row-between", h("div.row", kindTag, t && t.issued_at ? h("span.tiny.faint", `آخر تحديث ${ZS.ago(t.issued_at)}`) : null), available.length > 1 && !(t && t.kind === "live") ? seg : null));
      if (!t) { forecastBox.appendChild(ui().empty("ماكو توقع لهالمباراة")); return; }
      // live: compare with the pre-match forecast; pre-match: with the previous logged version
      const prev = t.kind === "live" ? (t.pre || null) : (!played && st.track === mf.displayed_track && f && f.prev_p ? f.prev_p : null);
      forecastBox.appendChild(ui().probBar(mf.home, mf.away, t.p, { big: true, prev }));
      const lines = [];
      if (t.kind === "live") lines.push(h("p", { style: { fontWeight: 700 } }, `${t.phase === "FT" ? "بنهاية المباراة" : "بنهاية الشوط الأول"}: ${H.ar} ${pct(t.p[0])} · تعادل ${pct(t.p[1])} · ${A.ar} ${pct(t.p[2])}.`));
      else if (mf.takeaway_ar && st.track === mf.displayed_track) lines.push(h("p", { style: { fontWeight: 700 } }, mf.takeaway_ar));
      if (t.kind === "retro") lines.push(h("p.small.muted", `${t.label_ar}. ${t.hit ? "الاحتمال الأرجح صار ✓" : "الاحتمال الأرجح ما صار ✗"} · RPS ${num(t.rps, 3)}`));
      if (prev && t.kind === "live") lines.push(h("p.small.muted", "الفرق تحت كل رقم مقارنة بتوقع ما قبل المباراة (بالنقاط المئوية)."));
      else if (prev) {
        const moved = t.p.some((v, i) => Math.abs(v - prev[i]) >= 0.005);
        lines.push(h("p.small.muted", moved ? `الفرق عن التوقع السابق (${ZS.dateTime(f.prev_issued_at)}) مكتوب تحت كل رقم بالنقاط المئوية (ن.م).`
          : `ما تغيّر شي يذكر عن التوقع السابق (${ZS.dateTime(f.prev_issued_at)}).`));
      }
      if (mf.p_sr && st.track !== "sportradar" && !played) lines.push(h("p.small.faint", `للمقارنة، SportRadar ينشر: ${pct(mf.p_sr[0])} / ${pct(mf.p_sr[1])} / ${pct(mf.p_sr[2])}`));
      forecastBox.append(...lines);
    }
    drawForecast();

    // ---------------------------------------------------------------- tabs
    const TABS = [["summary", "الملخص"], ["pitch", "الملعب"], ["numbers", "الأرقام"], ["events", "الأحداث"]];
    const tabs = h("div.tabs", { role: "tablist", "aria-label": "أقسام المباراة" });
    const panel = h("div.stack-lg", { role: "tabpanel", id: "match-panel" });
    TABS.forEach(([k, lab]) => tabs.appendChild(h("button", {
      type: "button", role: "tab", id: "tab-" + k, "aria-selected": String(st.tab === k), "aria-controls": "match-panel",
      onclick: () => { st.tab = k; ZS.$$("button", tabs).forEach((b) => b.setAttribute("aria-selected", String(b.id === "tab-" + k))); drawTab(); },
    }, lab)));
    tabs.addEventListener("keydown", (ev) => {
      const idx = TABS.findIndex(([k]) => k === st.tab);
      let n = null;
      if (ev.key === "ArrowLeft") n = (idx + 1) % TABS.length;     // RTL: left = next
      if (ev.key === "ArrowRight") n = (idx - 1 + TABS.length) % TABS.length;
      if (n !== null) { ev.preventDefault(); const b = ZS.$("#tab-" + TABS[n][0]); b.click(); b.focus(); }
    });
    view.append(tabs, panel);

    function drawTab() {
      ZS.clear(panel);
      panel.setAttribute("aria-labelledby", "tab-" + st.tab);
      ({ summary: tabSummary, pitch: tabPitch, numbers: tabNumbers, events: tabEvents })[st.tab]();
    }

    // ---------------------------------------------------------------- summary
    function tabSummary() {
      const t = mf.tracks[st.track];
      const grid = h("div.grid.g-main");
      const L = h("div.stack-lg"), R = h("div.stack-lg");
      grid.append(L, R);
      panel.appendChild(grid);
      if (live && live.reports) L.appendChild(liveReports());
      if (t && t.reasons) L.appendChild(reasonsCard(t));
      if (t && t.top_scores) L.appendChild(topScoresCard(t));
      if (played) L.appendChild(resultCheckCard());
      L.appendChild(historyCard());
      R.appendChild(seasonCard());
      if (!played && !(live && live.reports)) R.appendChild(challengeWidget(mf));
      R.appendChild(dataCard(t));
    }
    function reasonsCard(t) {
      const best = t.p.indexOf(Math.max(...t.p));
      const who = best === 0 ? H.ar : best === 2 ? A.ar : null;
      const mx = Math.max(...t.reasons.map((r) => r.size), 0.01);
      const list = h("ul.list", t.reasons.map((r) => {
        const col = r.favours === "home" ? colours[0] : colours[1];
        const w = (50 * r.size) / mx;
        return h("li", { style: { display: "block" } },
          h("button", { type: "button", class: "reason", style: { width: "100%", background: "none", border: 0, textAlign: "start", padding: 0, minHeight: "44px" }, onclick: () => reasonSheet(r) },
            h("span", r.text_ar),
            h("span.stack", { style: { gap: "3px" } },
              h("span.r-who", `يرجّح ${r.favours === "home" ? H.ar : A.ar}`),
              h("span.r-bar", h("i", { style: { background: col, width: w + "%", [r.favours === "home" ? "left" : "right"]: "50%" } }),
                h("i", { style: { left: "calc(50% - 1px)", width: "2px", background: "var(--fg-3)" } })))));
      }));
      return h("section.card",
        h("div.card-head", h("h2", who ? `ليش الحاسوب يرجّح ${who}؟` : "ليش التعادل محتمل؟"), ui().trackTag(st.track)),
        h("p.small.muted", "أكبر الأسباب أولاً. الأرقام هي مدخلات الموديل نفسها (قوة الهجوم والدفاع وميزة الأرض)، مو كلام عام."),
        list,
        h("p.tiny.faint", { style: { marginTop: "8px" } }, "الشريط يبين حجم أثر كل سبب على الأهداف المتوقعة وباتجاه أي فريق. اضغطي على أي سبب للتفاصيل."));
    }
    function reasonSheet(r) {
      const lines = {
        attack_home: `قوة هجوم ${H.ar} مقارنة بمعدل الدوري، محسوبة من نتائجه السابقة مع وزن أكبر للمباريات الأحدث.`,
        attack_away: `قوة هجوم ${A.ar} مقارنة بمعدل الدوري.`,
        defence_home: `كم يستقبل ${H.ar} مقارنة بالمعدل (أقل من 1 = أحسن من المعدل).`,
        defence_away: `كم يستقبل ${A.ar} مقارنة بالمعدل (أكثر من 1 = يستقبل أكثر).`,
        home: "ميزة اللعب بالأرض عامة لكل فرق الدوري، محسوبة من كل المباريات.",
      };
      ui().openSheet("تفصيل السبب", h("div.stack",
        h("p", { style: { fontWeight: 700 } }, r.text_ar),
        h("p.muted", lines[r.key] || ""),
        h("p.small.faint", `الأثر على لوغاريتم الأهداف المتوقعة: ${num(r.effect, 3)} (موجب = لصالح صاحب الأرض).`)));
    }
    function topScoresCard(t) {
      return h("section.card",
        h("div.card-head", h("h2", "أرجح النتائج الرقمية"), h("span.tag", "النتيجة الرقمية أصعب بكثير من الفائز")),
        h("div.grid.g-3", t.top_scores.slice(0, 3).map(([s, p], i) => {
          const [a, b] = s.split("-").map(Number);
          return h("div.panel", { style: { textAlign: "center" } },
            h("div.tiny.faint", `#${i + 1}`),
            h("div.sb-score", { style: { justifyContent: "center", fontSize: "1.5rem" }, "aria-label": `${H.ar} ${a}، ${A.ar} ${b}` }, h("span.g", a), h("span.sep", "–"), h("span.g", b)),
            h("div.num", { style: { fontFamily: "var(--font-display)", fontWeight: 800, fontSize: "1.1rem", marginTop: "4px" } }, pct(p, 1)));
        })),
        h("p.tiny.faint", { style: { marginTop: "8px" } }, `الرقم على اليمين لـ${H.ar} واليسار لـ${A.ar}. حتى أرجح نتيجة تصير بحدود 1 من كل 7 أو 8 مباريات.`));
    }
    function resultCheckCard() {
      const out = h("section.card", h("h2", "التوقع مقابل النتيجة"));
      const rows = [];
      if (f && f.logged) rows.push(["التوقع المسجل قبل البداية", f.logged.p, `${f.logged.model_version} · ${ZS.dateTime(f.logged.issued_at)}`]);
      for (const k of ["market", "independent"]) if (mf.tracks[k]) rows.push([`${ui().trackLabel(k)} (استرجاعي)`, mf.tracks[k].p, `RPS ${num(mf.tracks[k].rps, 3)}`]);
      if (mf.facts && mf.facts.market_p) rows.push(["أسعار السوق (Bet365) بعد إزالة الهامش", mf.facts.market_p, "للمقارنة"]);
      const res = mf.score[0] > mf.score[1] ? 0 : mf.score[0] === mf.score[1] ? 1 : 2;
      out.appendChild(h("div.tbl-wrap", h("table.tbl",
        h("thead", h("tr", h("th", "المصدر"), h("th.n", H.ar), h("th.n", "تعادل"), h("th.n", A.ar), h("th", "ملاحظة"))),
        h("tbody", rows.map(([lab, p, note]) => h("tr", h("td", lab), p.map((v, i) => h("td.n", { style: i === res ? { fontWeight: 800, color: "var(--fg)", background: "var(--pitch-soft)" } : {} }, pct(v))), h("td.small.faint", note)))))));
      out.appendChild(h("p.tiny.faint", { style: { marginTop: "8px" } }, "الخانة المظللة هي اللي صارت. التوقع الاسترجاعي يعيد حساب المباراة بنفس الموديل وبيانات ما قبل أسبوعها، فهو عادل بس مو منشور وقتها."));
      return out;
    }
    function historyCard() {
      const hist = (mf.history || []).filter((x) => x.track === st.track || (st.track !== "sportradar" && x.track === "sportradar" && false));
      const box = h("section.card", h("div.card-head", h("h2", "شنو تغيّر بالتوقع؟"), ui().trackTag(st.track)));
      if (!hist.length) { box.appendChild(h("p.small.muted", played ? "هالمباراة قبل بدء سجل التوقعات (السجل بدأ أكتوبر 2026)." : "ماكو نسخ سابقة مسجلة لهالمسار بعد.")); return box; }
      const list = h("ol.list", hist.slice().reverse().map((x, i) => h("li", { style: { display: "block" } },
        h("div.row-between", h("strong", ZS.dateTime(x.issued_at)), h("span.tiny.faint", x.model_version)),
        h("div.row.small", { style: { gap: "14px" } }, x.p.map((v, k) => h("span.num", `${[H.ar, "تعادل", A.ar][k]} ${pct(v)}`, x.delta_pts ? h("span.delta." + (x.delta_pts[k] > 0 ? "up" : x.delta_pts[k] < 0 ? "down" : ""), ` (${ZS.signed(x.delta_pts[k], 1)})`) : null))),
        x.changes && x.changes.length ? h("ul.small.muted", { style: { margin: "6px 0 0", paddingInlineStart: "18px" } }, x.changes.map((c) => h("li", c.text_ar))) : h("p.small.faint", i === hist.length - 1 ? "أول نسخة مسجلة" : ""),
        x.noise_ar ? h("p.tiny.faint", x.noise_ar) : null)));
      box.appendChild(list);
      return box;
    }
    function seasonCard() {
      const box = h("section.card", h("div.card-head", h("h2", "شنو تعني للموسم؟")));
      const imp = mf.importance;
      if (live && live.impact && live.impact.length) {
        box.appendChild(h("p.small.muted", live.phase === "HT" ? "حسب وضع المباراة بنهاية الشوط الأول (توزيع النتائج النهائية المتوقعة):" : "بعد النتيجة:"));
        box.appendChild(impactTable(live.impact));
      }
      if (imp && imp.swings && imp.swings.length) {
        box.appendChild(h("p.small.muted", `مؤشر الأهمية ${num(imp.importance, 1)}: فرص الفرق حسب نتيجة هالمباراة (${num(imp.n_sims, 0)} موسم محاكى لكل نتيجة):`));
        const metric = { p_title: "اللقب", p_ucl: "دوري الأبطال", p_releg: "الهبوط" };
        box.appendChild(h("div.tbl-wrap", h("table.tbl",
          h("thead", h("tr", h("th", "الفريق"), h("th", "الفرصة"), h("th.n", `فوز ${H.short}`), h("th.n", "تعادل"), h("th.n", `فوز ${A.short}`))),
          h("tbody", imp.swings.slice(0, 6).map((s) => h("tr", h("td", ui().teamInline(s.team_id)), h("td", metric[s.metric] || s.metric), h("td.n", pct(s.home_win)), h("td.n", pct(s.draw)), h("td.n", pct(s.away_win))))))));
      } else if (!(live && live.impact && live.impact.length)) {
        box.appendChild(h("p.small.muted", played ? "تأثير النتيجة صار جزء من صفحة الموسم." : "أهمية المباراة تنحسب للمباريات اللي بالأيام الثمانية الجاية."));
      }
      box.appendChild(h("a.small", { href: ZS.href("season") }, "جربي «ماذا لو؟» بصفحة الموسم ←"));
      return box;
    }
    function impactTable(rows) {
      const lab = { p_title: "اللقب", p_top4: "دوري الأبطال", p_releg: "الهبوط" };
      const body = [];
      for (const r of rows.slice(0, 6)) for (const k of ["p_title", "p_top4", "p_releg"]) {
        const b = r[k + "_before"], n = r[k + "_now"];
        if (!ZS.isNum(b) || Math.max(b, n) < 0.01 || Math.abs(n - b) < 0.005) continue;
        body.push(h("tr", h("td", ui().teamInline(ZS.D.keyToId[r.team] || r.team)), h("td", lab[k]), h("td.n", pct(b)), h("td.n", pct(n)), h("td.n", h("span.delta." + (n > b ? "up" : "down"), ZS.signed(100 * (n - b), 1)))));
      }
      if (!body.length) return h("p.small.faint", "ماكو تغيير يذكر بالفرص");
      return h("div.tbl-wrap", h("table.tbl", h("thead", h("tr", h("th", "الفريق"), h("th", "الفرصة"), h("th.n", "قبل"), h("th.n", "هسه"), h("th.n", "ن.م"))), h("tbody", body)));
    }
    function dataCard(t) {
      const box = h("section.card", h("h2", "المصدر والبيانات"));
      const items = [];
      if (t && t.model_version) items.push(["إصدار الموديل", t.model_version]);
      if (t && t.data_version) items.push(["نسخة البيانات", t.data_version]);
      if (t && t.issued_at) items.push(["وقت التوقع", ZS.dateTime(t.issued_at)]);
      if (mf.external_ids && mf.external_ids.sportradar) items.push(["معرّف SportRadar", mf.external_ids.sportradar]);
      items.push(["معرّف المباراة الثابت", mf.match_id]);
      box.appendChild(h("dl.stack", { style: { gap: "4px", margin: 0 } }, items.map(([k, v]) => h("div.row-between.small", h("dt.muted", k), h("dd.num", { style: { margin: 0, direction: "ltr" } }, v)))));
      const notes = [...(mf.data_notes || [])];
      if (mf.facts && mf.facts.missing && mf.facts.missing.length) notes.unshift("ناقص لهالمباراة: " + mf.facts.missing.map((x) => ({ odds: "أسعار السوق", shots_on_target: "التسديدات على المرمى", half_time: "نتيجة الشوط الأول" })[x] || x).join("، "));
      if (notes.length) box.appendChild(h("div.stack", { style: { marginTop: "10px", gap: "6px" } }, h("h3", "بيانات ناقصة مهمة"), notes.map((n) => h("div.notice", ui().icon("info"), h("span", n)))));
      return box;
    }
    function liveReports() {
      const box = h("section.card", h("div.card-head", h("h2", live.phase === "FT" ? "تقرير نهاية المباراة" : "تقرير الشوط الأول"), ui().trackTag("live")));
      const phases = ["HT", "FT"].filter((p) => live.reports[p]);
      for (const ph of phases.reverse()) {
        const r = live.reports[ph];
        if (phases.length > 1) box.appendChild(h("h3", ph === "FT" ? "نهاية المباراة" : "الشوط الأول"));
        const cols = h("div.grid.g-2");
        for (const [side, name] of [["home", H.ar], ["away", A.ar]]) {
          const ins = r.insights && r.insights[side];
          if (!ins) continue;
          cols.appendChild(h("div.panel", h("strong", name),
            h("ul.list", (ins.pos || []).map((x) => h("li.small", h("span", { style: { color: "var(--good)" } }, "＋"), h("span", x))),
              (ins.neg || []).map((x) => h("li.small", h("span", { style: { color: "var(--bad)" } }, "−"), h("span", x))))));
        }
        box.appendChild(cols);
        if (r.notes && r.notes.length) box.appendChild(h("ul.small", { style: { paddingInlineStart: "18px", margin: "8px 0 0" } }, r.notes.map((n) => h("li", n))));
        box.appendChild(h("p.tiny.faint", `أُنشئ ${ZS.dateTime(r.generated_at)} · ${live.source}`));
      }
      return box;
    }

    // ---------------------------------------------------------------- pitch
    function tabPitch() {
      const t = mf.tracks[st.track];
      const si = mf.scenario_inputs;
      if (!played && t && t.xg) {
        const rho = t.rho ?? (si && si.rho) ?? 0;
        const m = ZS.models.scoreMatrix(t.xg[0], t.xg[1], rho);
        panel.appendChild(h("section.card",
          h("div.card-head", h("h2", "خريطة النتائج المحتملة"), ui().trackTag(st.track)),
          h("p.small.muted", `كل خانة: احتمال النتيجة بالضبط (٪). الصفوف أهداف ${H.ar}، والأعمدة أهداف ${A.ar}.`),
          h("div.row", { style: { alignItems: "stretch", gap: "6px" } },
            h("div.tiny.faint", { style: { writingMode: "vertical-rl", textAlign: "center" } }, `أهداف ${H.ar} ↓`),
            h("div.grow.stack", { style: { gap: "4px", maxWidth: "460px" } },
              h("div.tiny.faint", { style: { direction: "ltr", textAlign: "center" } }, `أهداف ${A.ar} →`),
              C().scoreGrid(m, colours, { names: [H.ar, A.ar] }))),
          h("p.tiny.faint", `الأهداف المتوقعة قبل المباراة: ${H.ar} ${num(t.xg[0], 2)} · ${A.ar} ${num(t.xg[1], 2)}. هذي مو xG الفرص؛ هي معدل الأهداف اللي يتوقعه الموديل قبل الصافرة.`)));
      }
      if (mf.lineups) { panel.appendChild(lineupsCard(mf.lineups)); return; }
      panel.appendChild(h("section.card",
        h("h2", "التشكيلات والمواقع"),
        h("div.notice", ui().icon("lock"), h("div.stack", { style: { gap: "4px" } },
          h("strong", "تحتاج تفعيل: مصدر تشكيلات"),
          h("span.small", "التشكيلات والغيابات وخرائط اللمسات للمباريات الحالية تحتاج مزوّد بيانات (API-Football للتشكيلات، وOpta أو StatsBomb التجاري للإحداثيات). الخطوات بصفحة البيانات والمصادر."))),
        h("div.row", { style: { marginTop: "10px" } },
          h("a.btn.small", { href: ZS.href("data") }, ui().icon("data"), "شوفي شنو يحتاج تفعيل"),
          h("a.btn.small", { href: ZS.href("archive") }, ui().icon("matches"), "أمثلة كاملة من أرشيف StatsBomb"))));
    }

    function lineupsCard(lu) {
      const pitch = (tid, col) => {
        const t = lu[tid];
        if (!t) return null;
        const rows = {};
        for (const p of t.starters) { const [r, c] = String(p.grid || "1:1").split(":").map(Number); (rows[r] = rows[r] || []).push({ ...p, c }); }
        const R = Math.max(...Object.keys(rows).map(Number), 1);
        let svg = `<svg viewBox="0 0 68 105" role="img" aria-label="تشكيلة ${ZS.esc(team(tid).ar)}"><rect width="68" height="105" fill="rgba(0,0,0,.06)"/>` +
          `<rect x=".4" y=".4" width="67.2" height="104.2" fill="none" stroke="rgba(255,255,255,.7)" stroke-width=".5"/><line x1="0" y1="52.5" x2="68" y2="52.5" stroke="rgba(255,255,255,.7)" stroke-width=".5"/>` +
          `<rect x="13.8" y="88.5" width="40.3" height="16.5" fill="none" stroke="rgba(255,255,255,.7)" stroke-width=".5"/>`;
        for (const [r, ps] of Object.entries(rows)) {
          ps.sort((a, b) => a.c - b.c);
          ps.forEach((p, i) => {
            const x = ((i + 0.5) / ps.length) * 68, y = 105 - ((Number(r) - 0.5) / R) * 100;
            svg += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3.6" fill="${col}" stroke="#fff" stroke-width=".5"/>` +
              `<text x="${x.toFixed(1)}" y="${(y + 1.2).toFixed(1)}" text-anchor="middle" font-size="3.2" font-weight="800" style="fill:${ZS.inkOn(col)}">${p.number ?? ""}</text>` +
              `<text x="${x.toFixed(1)}" y="${(y + 7.6).toFixed(1)}" text-anchor="middle" font-size="3" font-weight="700" style="fill:#fff;paint-order:stroke;stroke:rgba(0,0,0,.6);stroke-width:.6px">${ZS.esc(String(p.player || "").split(" ").slice(-1)[0])}</text>`;
          });
        }
        svg += "</svg>";
        const wrap = h("div.pitch-wrap");
        wrap.innerHTML = svg;
        return h("div.stack", h("div.row-between", ui().teamInline(tid), h("span.tag", t.formation || "")), wrap,
          t.subs && t.subs.length ? h("p.tiny.faint", "الاحتياط: " + t.subs.map((p) => p.player).join("، ")) : null,
          t.coach ? h("p.tiny.faint", `المدرب: ${t.coach}`) : null);
      };
      return h("section.card", h("h2", "التشكيلات"),
        h("div.grid.g-2", pitch(mf.home, colours[0]), pitch(mf.away, colours[1])),
        h("p.tiny.faint", { style: { marginTop: "6px" } }, "المصدر: API-Football. التوقع نفسه ما يتغير بالتشكيلة بعد (الموديل ما يعرف منو لعب)؛ اختبار أثرها يحتاج موسم بيانات تشكيلات."));
    }

    // ---------------------------------------------------------------- numbers
    function tabNumbers() {
      if (live && live.stats && Object.keys(live.stats).length) {
        const parts = [["first_half", "الشوط الأول"], ["second_half", "الشوط الثاني"], ["full", "المباراة"]].filter(([k]) => live.stats[k]);
        if (!live.stats[st.part]) st.part = parts[parts.length - 1][0];
        const seg = h("div.seg", { role: "group", "aria-label": "الفترة" }, parts.map(([k, lab]) => h("button", { type: "button", "aria-pressed": String(st.part === k), onclick: () => { st.part = k; drawTab(); } }, lab)));
        const s = live.stats[st.part];
        const labels = { goals: "الأهداف", ball_possession: "الاستحواذ ٪", shots_total: "التسديدات", shots_on_target: "على المرمى", shots_off_target: "خارج المرمى", shots_blocked: "مصدودة", saves: "تصديات الحارس", corner_kicks: "الركنيات", fouls: "الأخطاء", yellow_cards: "الإنذارات", sent_off: "الطرد", offsides: "التسلل" };
        panel.appendChild(h("section.card", h("div.card-head", h("h2", "أرقام المباراة"), seg),
          C().mirrorBars(Object.entries(labels).map(([k, lab]) => ({ label: lab, home: s.home[k], away: s.away[k] })), colours),
          s.approx_possession ? h("p.tiny.faint", { style: { marginTop: "8px" } }, "استحواذ الشوط الثاني تقريبي: محسوب من الرقمين التراكميين.") : null,
          h("p.tiny.faint", { style: { marginTop: "6px" } }, `المصدر: ${live.source}. أي رقم ما وصل من المصدر يبقى «—» وما ينحسب صفر.`)));
      }
      if (played && mf.facts) {
        const fc = mf.facts;
        panel.appendChild(h("section.card", h("h2", "حقائق المباراة"),
          C().mirrorBars([
            { label: "الأهداف", home: mf.score[0], away: mf.score[1] },
            { label: "أهداف الشوط الأول", home: fc.ht ? fc.ht[0] : null, away: fc.ht ? fc.ht[1] : null },
            { label: "التسديدات على المرمى", home: fc.sot ? fc.sot[0] : null, away: fc.sot ? fc.sot[1] : null },
          ], colours),
          h("p.tiny.faint", { style: { marginTop: "8px" } }, `المصادر: النتيجة ${fc.sources.result || "—"} · التسديدات ${fc.sources.stats || "—"} · الشوط الأول ${fc.sources.half_time || "—"} · الأسعار ${fc.sources.odds || "—"}`)));
      }
      // model inputs, both tracks
      const tr = TRACK_ORDER.filter((k) => mf.tracks[k] && mf.tracks[k].p);
      panel.appendChild(h("section.card", h("h2", "مقارنة المصادر"),
        h("div.tbl-wrap", h("table.tbl",
          h("thead", h("tr", h("th", "المصدر"), h("th.n", H.ar), h("th.n", "تعادل"), h("th.n", A.ar), h("th.n", "الأهداف المتوقعة"))),
          h("tbody", tr.map((k) => { const t = mf.tracks[k]; return h("tr", h("td", ui().trackLabel(k)), t.p.map((v) => h("td.n", pct(v))), h("td.n", t.xg ? `${num(t.xg[0], 2)} – ${num(t.xg[1], 2)}` : "—")); })))),
        h("p.tiny.faint", { style: { marginTop: "8px" } }, "المسار المدعوم بالسوق تعلّم قوة الفرق من نتائجها ومن أسعار مبارياتها السابقة؛ المستقل ما يستخدم السوق نهائياً. الاختبار على 1140 مباراة ما بيّن فرق واضح بيناتهم.")));
      if (homeCard && awayCard) {
        const formRows = (c) => (c.form || []).slice(-5);
        const fcard = (c, side) => h("div.panel",
          h("div.row-between", ui().teamInline(c.team.id), h("span.form-strip", formRows(c).map((g) => h("span.f." + g.result, { title: `${team(g.opponent).ar} ${g.gf}-${g.ga}` }, { W: "ف", D: "ت", L: "خ" }[g.result])))),
          h("div.tbl-wrap", { style: { marginTop: "8px" } }, h("table.tbl",
            h("thead", h("tr", h("th", "الخصم"), h("th.n", "النتيجة"), h("th.n", "المتوقع قبلها"))),
            h("tbody", formRows(c).slice().reverse().map((g) => h("tr", h("td", (g.home ? "" : "@ "), team(g.opponent).ar), h("td.n", ZS.scoreText(g.gf, g.ga)), h("td.n", ZS.isNum(g.xg_for_pre) ? `${num(g.xg_for_pre, 1)} – ${num(g.xg_against_pre, 1)}` : "—")))))),
          restLine(c));
        panel.appendChild(h("section.card", h("h2", "الفورمة (آخر 5 بالدوري)"), h("div.grid.g-2", fcard(homeCard, "home"), fcard(awayCard, "away")),
          h("p.tiny.faint", { style: { marginTop: "8px" } }, "«المتوقع قبلها» = الأهداف المتوقعة له وعليه قبل كل مباراة حسب الموديل. ف = فوز، ت = تعادل، خ = خسارة.")));
      }
      const t = mf.tracks[st.track];
      if (t && t.inputs) {
        const inp = t.inputs;
        const row = (lab, v, note) => h("tr", h("td", lab), h("td.n", v), h("td.small.muted", { style: { whiteSpace: "normal" } }, note));
        panel.appendChild(h("section.card", h("div.card-head", h("h2", "مدخلات الموديل"), ui().trackTag(st.track)),
          h("div.tbl-wrap", h("table.tbl",
            h("thead", h("tr", h("th", "المدخل"), h("th.n", "القيمة"), h("th", "المعنى"))),
            h("tbody",
              row(`هجوم ${H.ar}`, num(inp.attack_home_x, 2) + "×", "1.00 = معدل الدوري"),
              row(`دفاع ${H.ar}`, num(inp.defence_home_x, 2) + "×", "أقل من 1 = يستقبل أقل من المعدل"),
              row(`هجوم ${A.ar}`, num(inp.attack_away_x, 2) + "×", "1.00 = معدل الدوري"),
              row(`دفاع ${A.ar}`, num(inp.defence_away_x, 2) + "×", "أقل من 1 = يستقبل أقل من المعدل"),
              row("ميزة الأرض", num(inp.home_adv_x, 2) + "×", "عامة لكل فرق الدوري"),
              row("تصحيح النتائج القليلة (rho)", num(inp.rho, 3), "يعدّل احتمالات 0-0 و1-1 و1-0 و0-1"),
              row("عدد المباريات بالتدريب", num(inp.n_matches, 0), "مع وزن أكبر للمباريات الأحدث")))),
          h("p.tiny.faint", { style: { marginTop: "8px" } }, "الأهداف المتوقعة = معدل الدوري × هجوم الفريق × دفاع الخصم (× ميزة الأرض لصاحب الأرض).")));
      }
    }
    function restLine(c) {
      const u = (c.upcoming || []).find((x) => x.match_id === mid);
      if (!u || u.rest_days == null) return null;
      return h("p.small.muted", { style: { marginTop: "6px" } }, `أيام الراحة قبل هالمباراة: ${u.rest_days} (من مباريات الدوري بس)`);
    }

    // ---------------------------------------------------------------- events + scenario
    function tabEvents() {
      if (live && live.timeline && live.timeline.length) {
        const rows = live.timeline;
        const evs = (live.events || []).filter((e) => e.kind === "goal" || e.kind === "red");
        const info = h("div.panel.tl-cursor-info");
        let tl;
        const showAt = (m) => {
          const r = rows.find((x) => x.minute === m) || rows[rows.length - 1];
          st.minute = r.minute;
          ZS.clear(info).append(h("strong.num", `الدقيقة ${r.minute}`), h("span.num", `النتيجة ${H.ar} ${r.hg} – ${r.ag} ${A.ar}`),
            h("span.num", `${H.ar} ${pct(r.p_home)} · تعادل ${pct(r.p_draw)} · ${A.ar} ${pct(r.p_away)}`),
            h("button.btn.small", { type: "button", onclick: () => { tl.select(rows[rows.length - 1].minute); } }, "ارجعي للنهاية"));
          ZS.$$(".ev-btn", panel).forEach((b) => b.setAttribute("aria-pressed", String(Number(b.dataset.m) === r.minute)));
        };
        tl = C().timeline({ rows, events: evs, colours, names: [H.ar, A.ar], onSelect: (m) => showAt(m), selected: st.minute ?? rows[rows.length - 1].minute });
        const evList = h("div.ev-list", evs.length ? evs.map((e) => h("button.ev-btn", { type: "button", "data-m": e.minute + 1, "aria-pressed": "false", onclick: () => tl.select(e.minute + 1) },
          h("span.ev-min.num", `${e.minute}'`), ui().icon(e.kind === "goal" ? "ball" : "card", "ev-icon"),
          h("span", `${e.kind === "goal" ? "هدف" : "طرد"} ${e.team === "home" ? H.ar : A.ar}`))) : h("p.small.muted", "ماكو أهداف أو طرد"));
        panel.appendChild(h("section.card", h("div.card-head", h("h2", "الاحتمالات خلال المباراة"), ui().trackTag("live")),
          tl.el, info,
          h("p.tiny.faint", { style: { marginTop: "8px" } }, "اضغطي على الرسم أو اسحبي، أو استخدمي الأسهم بالكيبورد. الدقيقة 0 هي توقع ما قبل المباراة نفسه بالضبط. الأحداث من SportRadar بعد التصحيح: الهدف الملغي ما ينحسب، والهدف بالخطأ ينحسب للفريق الصحيح من النتيجة الجارية.")));
        panel.appendChild(h("section.card", h("h2", "الأحداث"), evList));
        showAt(st.minute ?? rows[rows.length - 1].minute);
      } else {
        panel.appendChild(h("section.card", h("h2", "الأحداث"),
          h("p.muted", played ? "ماكو تغطية مباشرة لهالمباراة (التحليل المباشر يشتغل على المباريات المختارة)." : "الأحداث تظهر هنا وقت المباراة: الأهداف والطرد واحتمالات الفوز دقيقة بدقيقة.")));
      }
      panel.appendChild(scenarioTool());
    }

    function scenarioInputs() {
      if (live && live.reports) {
        const r = live.reports.HT || live.reports.FT;
        if (r && r.pre_match && mf.scenario_inputs) return { lam: r.pre_match.xg[0], mu: r.pre_match.xg[1], rho: r.pre_match.rho, inplay: mf.scenario_inputs.inplay };
      }
      return mf.scenario_inputs || null;
    }
    function scenarioTool() {
      const si = scenarioInputs();
      const box = h("section.scenario");
      box.appendChild(h("div.scen-head", h("div.row", h("h2", "ماذا لو؟ داخل المباراة"), ui().trackTag("scenario")),
        h("span.small.muted", "سيناريو تجريبي، مو التوقع الرسمي")));
      if (!si) { box.appendChild(h("p.small.muted", "ماكو مدخلات سيناريو لهالمباراة (تتوفر للمباريات القادمة وللي عليها تحليل مباشر).")); return box; }
      const model = new ZS.models.InPlay(si.inplay);
      const s0 = st.scenario || { minute: live && live.score ? 45 : 0, hg: live && live.score ? live.score[0] : 0, ag: live && live.score ? live.score[1] : 0, rh: 0, ra: 0 };
      const s = (st.scenario = { ...s0 });
      const out = h("div.stack");
      const minute = h("input#scen-minute", { type: "range", min: 0, max: 95, step: 1, value: s.minute, "aria-label": "الدقيقة" });
      const minLab = h("strong.num", `${s.minute}'`);
      const stepper = (label, key) => {
        const val = h("strong.num", { style: { minWidth: "24px", textAlign: "center", fontFamily: "var(--font-display)", fontSize: "1.2rem" } }, String(s[key]));
        const set = (d) => { s[key] = Math.max(0, Math.min(key.startsWith("r") ? 3 : 9, s[key] + d)); val.textContent = String(s[key]); calc(); };
        return h("div.row", { style: { gap: "6px" } }, h("span.small.muted", { style: { minWidth: "88px" } }, label),
          h("button.icon-btn", { type: "button", "aria-label": `${label} ناقص واحد`, onclick: () => set(-1) }, "−"), val,
          h("button.icon-btn", { type: "button", "aria-label": `${label} زايد واحد`, onclick: () => set(+1) }, "+"));
      };
      function calc() {
        s.minute = Number(minute.value);
        minLab.textContent = `${s.minute}'`;
        const p = model.probs(si.lam, si.mu, s.minute, s.hg, s.ag, s.rh, s.ra, s.minute <= 45 ? 1 : 2, si.rho);
        const p0 = model.probs(si.lam, si.mu, 0, 0, 0, 0, 0, 1, si.rho);
        ZS.clear(out).append(ui().probBar(mf.home, mf.away, p, { prev: p0, label: "احتمالات السيناريو" }),
          h("p.small.muted", `بالدقيقة ${s.minute} والنتيجة ${H.ar} ${s.hg} – ${s.ag} ${A.ar}${s.rh || s.ra ? ` وطرد (${H.ar} ${s.rh}، ${A.ar} ${s.ra})` : ""}. الفرق تحت كل رقم مقارنة بتوقع ما قبل المباراة.`));
      }
      minute.addEventListener("input", calc);
      const quick = h("div.chips",
        h("button.chip", { type: "button", onclick: () => { s.hg += 1; rebuild(); } }, `+ هدف ${H.ar}`),
        h("button.chip", { type: "button", onclick: () => { s.ag += 1; rebuild(); } }, `+ هدف ${A.ar}`),
        h("button.chip", { type: "button", onclick: () => { s.rh = Math.min(3, s.rh + 1); rebuild(); } }, `+ طرد ${H.ar}`),
        h("button.chip", { type: "button", onclick: () => { s.ra = Math.min(3, s.ra + 1); rebuild(); } }, `+ طرد ${A.ar}`),
        h("button.chip", { type: "button", onclick: () => { minute.value = Math.min(95, s.minute + 15); calc(); } }, "تبقى النتيجة +15 دقيقة"),
        h("button.chip", { type: "button", onclick: () => { st.scenario = null; drawTab(); } }, "إعادة ضبط"));
      function rebuild() { st.scenario = { ...s }; drawTab(); }
      box.append(
        h("div.row", h("span.small.muted", "الدقيقة"), h("div.grow", minute), minLab),
        h("div.grid.g-2", stepper(`أهداف ${H.ar}`, "hg"), stepper(`أهداف ${A.ar}`, "ag"), stepper(`طرد ${H.ar}`, "rh"), stepper(`طرد ${A.ar}`, "ra")),
        quick, out,
        h("p.tiny.faint", `نفس موديل المباراة المباشر (${model.version}) وبنفس الأهداف المتوقعة قبل المباراة (${num(si.lam, 2)} – ${num(si.mu, 2)}).`));
      calc();
      return box;
    }

    drawTab();
    return offLive;
  }

  // ------------------------------------------------------------------ audience challenge widget
  function challengeWidget(mf) {
    const H = team(mf.home), A = team(mf.away);
    const box = h("section.card", h("div.card-head", h("h2", "توقعك أنتِ؟"), h("a.small", { href: ZS.href("challenge") }, "الترتيب والقواعد ←")));
    const ko = mf.kickoff_utc ? new Date(mf.kickoff_utc) : null;
    if (!ko) { box.appendChild(h("p.small.muted", "التوقع ينفتح لما ينحدد موعد المباراة.")); return box; }
    if (ko <= new Date()) { box.appendChild(h("p.small.muted", "انقفل التوقع: المباراة بدأت.")); return box; }
    const where = ZS.challenge.where();
    let pick = null;
    const seg = h("div.seg", { role: "group", "aria-label": "اختيارك" }, [["H", `فوز ${H.ar}`], ["D", "تعادل"], ["A", `فوز ${A.ar}`]].map(([k, lab]) =>
      h("button", { type: "button", "aria-pressed": "false", "data-k": k, onclick: (ev) => { pick = k; ZS.$$("button", seg).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.k === k))); } }, lab)));
    const hs = h("input", { type: "number", min: 0, max: 15, inputmode: "numeric", "aria-label": `أهداف ${H.ar}`, placeholder: "—", style: { width: "72px" } });
    const as = h("input", { type: "number", min: 0, max: 15, inputmode: "numeric", "aria-label": `أهداف ${A.ar}`, placeholder: "—", style: { width: "72px" } });
    const name = h("input", { type: "text", maxlength: 40, "aria-label": "اسمك بالترتيب", placeholder: "اسمك بالترتيب", value: ZS.store.prefs().player_name || "" });
    const msg = h("p.small", { role: "status" });
    const submit = h("button.btn.primary", { type: "button" }, ui().icon("check"), "سجّلي توقعي");
    submit.addEventListener("click", async () => {
      if (!pick) { msg.textContent = "اختاري فوز أو تعادل أو خسارة أول."; return; }
      const score = hs.value !== "" && as.value !== "" ? `${Number(hs.value)}-${Number(as.value)}` : null;
      const nm = name.value.trim();
      if (!ZS.env.db && !nm && ZS.env.server) { msg.textContent = "اكتبي اسم للترتيب."; return; }
      submit.disabled = true;
      try {
        await ZS.challenge.submit(mf.match_id, pick, score, nm || "أنا");
        if (nm) ZS.store.setPrefs({ player_name: nm });
        msg.textContent = "انسجل توقعك. ينقفل بصافرة البداية، وتگدرين تغيرينه لحد ذاك الوقت.";
      } catch (e) { msg.textContent = e.message; }
      submit.disabled = false;
    });
    box.append(h("p.small.muted", where.text), seg,
      h("div.row", h("span.small.muted", "النتيجة بالأرقام (اختياري، نقطتين إضافيتين):"), h("span.small", H.ar), hs, h("span", "–"), as, h("span.small", A.ar)),
      ZS.env.db ? null : name, h("div.row", submit), msg);
    // show an existing pick
    ZS.challenge.picks().then((ps) => {
      const mine = ps.filter((p) => p.match_id === mf.match_id && (ZS.env.db ? p.player_id === ZS.env.uid : p.player === (ZS.store.prefs().player_name || "أنا")));
      if (mine.length) {
        const m = mine[mine.length - 1];
        pick = m.pick;
        ZS.$$("button", seg).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.k === m.pick)));
        if (m.score) { const [a, b] = m.score.split("-"); hs.value = a; as.value = b; }
        msg.textContent = `توقعك المسجل: ${{ H: "فوز " + H.ar, D: "تعادل", A: "فوز " + A.ar }[m.pick]}${m.score ? ` (${m.score.replace("-", " – ")})` : ""}`;
      }
    }).catch(() => {});
    return box;
  }

  // ================================================================== archive (StatsBomb open data)
  async function renderArchive(view, params) {
    const idx = await ZS.getJSON("archive/index.json");
    if (!params.id) {
      view.appendChild(ui().pageHead("أرشيف التحليل العميق", "مباريات كاملة من بيانات StatsBomb المفتوحة: خريطة التسديدات مع xG لكل فرصة، خرائط اللمسات، شبكة التمريرات، وتقييم اللاعبين. هذا الشكل الكامل اللي يصير متاح للمباريات الحالية لما يتفعل مزوّد بيانات أحداث.", null, idx.source));
      const g = h("div.grid.g-auto");
      for (const m of idx.matches) {
        g.appendChild(h("a.sb", { href: ZS.href("archive", m.match_id) },
          h("div.sb-top", h("span", ZS.dateLong(m.date + "T12:00:00Z")), h("span.pill.ft", "أرشيف")),
          h("div.sb-teams",
            h("div.sb-team", ui().crest(ZS.D.keyToId[m.home] || m.home, "m"), h("span.team-name", m.home_ar)),
            h("div.sb-mid", h("div.sb-score", h("span.g", m.hg), h("span.sep", "–"), h("span.g", m.ag)), h("span.sb-sub", `xG ${num(m.xg_home, 2)} – ${num(m.xg_away, 2)}`)),
            h("div.sb-team.away", ui().crest(ZS.D.keyToId[m.away] || m.away, "m"), h("span.team-name", m.away_ar)))));
      }
      view.appendChild(g);
      view.appendChild(h("p.small.faint", idx.note_ar));
      return;
    }
    const a = await ZS.getJSON(`archive/${params.id}.json`);
    const m = a.match;
    const hid = ZS.D.keyToId[m.home] || m.home, aid = ZS.D.keyToId[m.away] || m.away;
    const colours = ZS.pairColours(team(hid), team(aid));
    const st = { tab: "pitch", part: "all", side: "both", player: null, minute: null };
    view.appendChild(h("div.row", h("a.btn.ghost.small", { href: ZS.href("archive") }, ui().icon("back"), "الأرشيف")));
    view.appendChild(h("section.card", { style: { display: "flex", flexDirection: "column", gap: "12px" } },
      h("div.row-between", h("span.small.muted", `${ZS.dateLong(m.date + "T12:00:00Z")} · ${idx.source}`), h("span.pill.ft", "أرشيف")),
      h("div.sb-teams",
        h("div.sb-team", ui().crest(hid, "l"), h("span.team-name", { style: { fontSize: "1.2rem" } }, m.home_ar)),
        h("div.sb-mid", h("div.sb-score", { style: { fontSize: "2.4rem" } }, h("span.g", m.hg), h("span.sep", "–"), h("span.g", m.ag)), h("span.sb-sub", `xG ${num(m.xg_home, 2)} – ${num(m.xg_away, 2)}`)),
        h("div.sb-team.away", ui().crest(aid, "l"), h("span.team-name", { style: { fontSize: "1.2rem" } }, m.away_ar))),
      ui().probBar(hid, aid, [m.pre_home_pct / 100, m.pre_draw_pct / 100, m.pre_away_pct / 100], { label: "توقع ما قبل المباراة (موديل الحاسوب)" }),
      h("p.tiny.faint", "توقع ما قبل المباراة محسوب بموديل الحاسوب من بيانات ما قبلها.")));
    const TABS = [["summary", "الملخص"], ["pitch", "الملعب"], ["numbers", "الأرقام"], ["events", "الأحداث"]];
    const tabs = h("div.tabs", { role: "tablist" });
    const panel = h("div.stack-lg", { role: "tabpanel" });
    TABS.forEach(([k, lab]) => tabs.appendChild(h("button", { type: "button", role: "tab", "aria-selected": String(st.tab === k), id: "atab-" + k,
      onclick: () => { st.tab = k; ZS.$$("button", tabs).forEach((b) => b.setAttribute("aria-selected", String(b.id === "atab-" + k))); draw(); } }, lab)));
    view.append(tabs, panel);
    const partFilter = () => h("div.seg", { role: "group", "aria-label": "الفترة" }, [["all", "المباراة"], ["1", "الشوط الأول"], ["2", "الشوط الثاني"]].map(([k, lab]) =>
      h("button", { type: "button", "aria-pressed": String(st.part === k), onclick: () => { st.part = k; draw(); } }, lab)));
    const sideFilter = () => h("div.seg", { role: "group", "aria-label": "الفريق" }, [["both", "الفريقين"], ["home", m.home_ar], ["away", m.away_ar]].map(([k, lab]) =>
      h("button", { type: "button", "aria-pressed": String(st.side === k), onclick: () => { st.side = k; draw(); } }, lab)));
    function playerSheet(name, side) {
      const p = (a.players || []).find((x) => x.name_ar === name && x.side === side);
      const grids = (a.heat_players[side] || {})[name] || {};
      const keys = Object.keys(grids);
      const merged = keys.length ? mergeGrids(keys.map((k) => grids[k])) : null;
      ui().openSheet(name, h("div.stack",
        p ? h("div.kpis", [["التقييم", num(p.rating, 1)], ["الدقائق", p.minutes], ["أهداف", p.goals], ["صناعة", p.assists], ["xG", num(p.xg, 2)], ["xA", num(p.xa, 2)], ["تمريرات مفتاحية", p.key_passes], ["مراوغات", p.dribbles], ["افتكاك + قطع", p.tackles_int], ["ضغط", p.pressures]].map(([k, v]) =>
          h("div.kpi", h("span.k-val.num", String(v)), h("span.k-lab", k)))) : null,
        merged ? C().heatmap(merged, side === "home" ? colours[0] : colours[1], { mirror: side === "home", label: `لمسات ${name}` }) : null,
        h("p.tiny.faint", "التقييم من صيغة المشروع (0-10) مقارنة بلاعبي نفس المركز، مو تقييم مزوّد. لمسات اللاعب من بيانات الأحداث، مو تتبّع.")));
    }
    function tacticsCard(t) {
      const nm = (side) => (side === "home" ? m.home_ar : m.away_ar);
      const other = (side) => (side === "home" ? "away" : "home");
      const mx = Math.max(1, ...t.flanks.map((f) => Math.max(f.attack_actions, f.defend_actions)));
      const bar = (v, col) => h("div", { style: { height: "7px", background: "var(--inset)", borderRadius: "4px" } }, h("i", { style: { display: "block", height: "100%", width: `${(100 * v) / mx}%`, background: col, borderRadius: "4px" } }));
      const rows = t.flanks.filter((f) => f.channel !== "centre").map((f) => {
        const col = f.team_side === "home" ? colours[0] : colours[1];
        const ocol = f.team_side === "home" ? colours[1] : colours[0];
        return h("div.panel.stack", { style: { gap: "6px" } },
          h("strong", `${f.channel === "left" ? "الجبهة اليسرى" : "الجبهة اليمنى"} لـ${nm(f.team_side)} ضد ${f.opp_channel_ar === "اليمين" ? "الجبهة اليمنى" : "الجبهة اليسرى"} لـ${nm(other(f.team_side))}`),
          h("div.row-between.small", h("span", `هجوم: ${f.attack_actions} فعل للثلث الأخير (${f.attack_completed} ناجح)، ${f.crosses} عرضية، xG ${num(f.xg, 2)}`), h("span.faint", (f.attackers || []).join("، "))),
          bar(f.attack_actions, col),
          h("div.row-between.small", h("span", `دفاع الخصم بهالجبهة: ${f.defend_actions} فعل (افتكاك، قطع، إبعاد، ضغط)`), h("span.faint", (f.defenders || []).join("، "))),
          bar(f.defend_actions, ocol));
      });
      const pr = t.pressing;
      return h("section.card", h("h2", "مواجهات تكتيكية"),
        h("div.grid.g-2", rows),
        h("h3", { style: { marginTop: "12px" } }, "الضغط مقابل البناء"),
        h("div.tbl-wrap", h("table.tbl",
          h("thead", h("tr", h("th", "الفريق"), h("th.n", "PPDA"), h("th.n", "استرجاع عالي"), h("th.n", "ضغط بالثلث الهجومي"), h("th.n", "تمريرات الخصم تحت الضغط (نجاح)"))),
          h("tbody", pr.map((x) => h("tr", h("td", nm(x.team_side)), h("td.n", x.ppda ?? "—"), h("td.n", String(x.high_recoveries)), h("td.n", String(x.pressures_high)),
            h("td.n", `${x.opp_pressed_passes} (${x.opp_pressed_pass_pct ?? "—"}%)`)))))),
        h("p.tiny.faint", { style: { marginTop: "6px" } }, t.note_ar));
    }
    function mergeGrids(gs) { const out = JSON.parse(JSON.stringify(gs[0])); for (const g of gs.slice(1)) for (let j = 0; j < g.ny; j++) for (let i = 0; i < g.nx; i++) out.cells[j][i] += g.cells[j][i]; out.n = gs.reduce((s, g) => s + g.n, 0); return out; }
    function draw() {
      ZS.clear(panel);
      if (st.tab === "summary") {
        const g = h("div.grid.g-2");
        for (const side of ["home", "away"]) {
          const ins = a.insights.filter((x) => x.side === side);
          g.appendChild(h("section.card", h("h2", side === "home" ? m.home_ar : m.away_ar),
            ["h1", "h2", "full"].map((part) => {
              const rows = ins.filter((x) => x.part === part);
              if (!rows.length) return null;
              return h("div", h("h3", { style: { marginTop: "8px" } }, { h1: "الشوط الأول", h2: "الشوط الثاني", full: "المباراة" }[part]),
                h("ul.list", rows.map((x) => h("li.small", h("span", { style: { color: x.kind === "pos" ? "var(--good)" : "var(--bad)" } }, x.kind === "pos" ? "＋" : "−"), h("span", x.text)))));
            })));
        }
        panel.appendChild(g);
        if (a.tactics) panel.appendChild(tacticsCard(a.tactics));
      } else if (st.tab === "pitch") {
        let shots = a.shots.filter((s) => (st.part === "all" || String(s.period) === st.part) && (st.side === "both" || s.side === st.side));
        panel.appendChild(h("section.card", h("div.card-head", h("h2", "خريطة التسديدات"), h("div.row", partFilter(), sideFilter())),
          C().shotMap(shots, colours, { onPick: (s) => ui().openSheet(`${s.player_ar} · ${s.minute}'`, h("div.stack",
            h("div.kpis", h("div.kpi", h("span.k-val.num", num(s.xg, 2)), h("span.k-lab", "xG الفرصة")), h("div.kpi", h("span.k-val", s.is_goal ? "هدف" : s.outcome), h("span.k-lab", "النتيجة"))),
            h("p.small.muted", `النوع: ${s.pattern}`), h("button.btn.small", { type: "button", onclick: () => playerSheet(s.player_ar, s.side) }, "ملف اللاعب"))) }),
          h("p.tiny.faint", { style: { marginTop: "6px" } }, `${m.home_ar} يهاجم لليسار و${m.away_ar} لليمين. الدائرة الممتلئة = هدف، وحجمها = xG. اضغطي على أي تسديدة.`)));
        const hm = h("div.grid.g-2");
        for (const side of st.side === "both" ? ["home", "away"] : [st.side]) {
          const byPeriod = a.heat[side] || {};
          const gs = st.part === "all" ? Object.values(byPeriod) : [byPeriod[st.part]].filter(Boolean);
          if (!gs.length) continue;
          hm.appendChild(h("div.stack", h("h3", `لمسات ${side === "home" ? m.home_ar : m.away_ar}`),
            C().heatmap(mergeGrids(gs), side === "home" ? colours[0] : colours[1], { mirror: side === "home" })));
        }
        panel.appendChild(h("section.card", h("div.card-head", h("h2", "خرائط اللمسات"), partFilter()), hm,
          h("p.tiny.faint", { style: { marginTop: "6px" } }, a.note_ar || "من بيانات الأحداث (كل لمسة مسجلة)، مو بيانات تتبّع.")));
        const pn = h("div.grid.g-2");
        for (const side of st.side === "both" ? ["home", "away"] : [st.side]) {
          pn.appendChild(h("div.stack", h("h3", `شبكة تمريرات ${side === "home" ? m.home_ar : m.away_ar}`),
            C().passNetwork(a.pass_nodes.filter((x) => x.side === side), a.pass_edges.filter((x) => x.side === side), side === "home" ? colours[0] : colours[1], { mirror: side === "home", onPick: (n) => playerSheet(n.player_ar, side) })));
        }
        panel.appendChild(h("section.card", h("div.card-head", h("h2", "شبكة التمريرات"), sideFilter()), pn,
          h("p.tiny.faint", { style: { marginTop: "6px" } }, "متوسط مكان كل لاعب لحد أول تبديل، وسمك الخط = عدد التمريرات بين اللاعبين. اضغطي على لاعب.")));
      } else if (st.tab === "numbers") {
        const part = st.part === "all" ? "full" : "h" + st.part;
        const rows = a.stats.filter((x) => x.part === part);
        panel.appendChild(h("section.card", h("div.card-head", h("h2", "أرقام المباراة"), partFilter()),
          C().mirrorBars(rows.map((x) => ({ label: x.label_ar, home: x.home, away: x.away })), colours)));
        const pl = (a.players || []).filter((p) => st.side === "both" || p.side === st.side).sort((x, y) => y.rating - x.rating);
        panel.appendChild(h("section.card", h("div.card-head", h("h2", "اللاعبين"), sideFilter()),
          h("div.tbl-wrap", h("table.tbl",
            h("thead", h("tr", ["اللاعب", "التقييم", "د", "أهداف", "صناعة", "xG", "xA", "تسديد", "مفتاحية", "تقدمية", "مراوغة", "ضغط"].map((x, i) => h(i ? "th.n" : "th", x)))),
            h("tbody", pl.map((p) => h("tr", h("td", h("button.btn.ghost.small", { type: "button", onclick: () => playerSheet(p.name_ar, p.side), style: { padding: "0 4px" } }, h("i", { style: { width: "8px", height: "8px", borderRadius: "50%", background: p.side === "home" ? colours[0] : colours[1], display: "inline-block" } }), p.name_ar)),
              h("td.n", num(p.rating, 1)), h("td.n", p.minutes), h("td.n", p.goals), h("td.n", p.assists), h("td.n", num(p.xg, 2)), h("td.n", num(p.xa, 2)), h("td.n", p.shots), h("td.n", p.key_passes), h("td.n", p.progressive), h("td.n", p.dribbles), h("td.n", p.pressures)))))),
          h("p.tiny.faint", { style: { marginTop: "6px" } }, "التقييم من صيغة المشروع (الإصدار 2): أرقام اللاعب بالمباراة مقارنة بلاعبي نفس المركز بموسم الليغا 2015/16، فكل المراكز تاخذ نفس فرصة التقييم العالي. مو تقييم StatsBomb."),
          h("a.small", { href: ZS.href("players") }, "مقارنة كل لاعبي الليغا 2015/16 ←")));
      } else {
        const rows = a.timeline.map((r) => ({ minute: r.minute, p_home: r.p_home / 100, p_draw: r.p_draw / 100, p_away: r.p_away / 100, hg: r.hg, ag: r.ag, xg_home: r.xg_home, xg_away: r.xg_away }));
        const evs = [];
        for (let i = 1; i < rows.length; i++) {
          if (rows[i].hg > rows[i - 1].hg) evs.push({ minute: rows[i].minute - 1, kind: "goal", team: "home" });
          if (rows[i].ag > rows[i - 1].ag) evs.push({ minute: rows[i].minute - 1, kind: "goal", team: "away" });
        }
        const info = h("div.panel.tl-cursor-info");
        const tl = C().timeline({ rows, events: evs, colours, names: [m.home_ar, m.away_ar], onSelect: (mm, r) => {
          r = r || rows[rows.length - 1];
          ZS.clear(info).append(h("strong.num", `الدقيقة ${r.minute}`), h("span.num", `النتيجة ${r.hg} – ${r.ag}`), h("span.num", `xG ${num(r.xg_home, 2)} – ${num(r.xg_away, 2)}`),
            h("span.num", `${m.home_ar} ${pct(r.p_home)} · تعادل ${pct(r.p_draw)} · ${m.away_ar} ${pct(r.p_away)}`));
        }, selected: rows[rows.length - 1].minute });
        panel.appendChild(h("section.card", h("h2", "الاحتمالات وxG خلال المباراة"), tl.el, info));
        tl.select(rows[rows.length - 1].minute);
      }
    }
    draw();
  }

  ZS.routes.match = { render, title: "مركز المباراة" };
  ZS.routes.archive = { render: renderArchive, title: "الأرشيف" };
  ZS.challengeWidget = challengeWidget;
})();
