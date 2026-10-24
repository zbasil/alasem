/* hub.js (version 3): the new home, built like a scores app.
   Matches by day across La Liga, the Premier League and the Champions League (live ring, date strip, favourite
   competitions), News (stories drawn from the computer's own numbers), Competitions (favourites, order, hiding),
   Standings (current and projected), More (profile, shortcuts, settings), and a match / team page for the
   Premier League and the Champions League. La Liga keeps its full match centre, team pages and season page. */
(function () {
  "use strict";
  const ZS = window.ZS;
  const { h, pct, team, D } = ZS;
  const ui = () => ZS.ui;
  const oldMatches = ZS.routes.matches;
  if (oldMatches) ZS.routes.round = { ...oldMatches, title: "مباريات الجولة (لاليغا)" };

  // ------------------------------------------------------------------ competitions
  const comp = (id) => (D.comps || []).find((c) => c.id === id) || { id, name_ar: id, short_ar: id, color: "#888", base: "" };
  const fixtureComp = (f) => f.comp || (String(f.match_id).split("-")[0]);
  function allFixtures() { return [...D.fixtures, ...Object.values(D.xfixtures || {}).flat()]; }
  function fixtureById(mid) { return D.fixturesById.get(mid) || (D.xfixturesById && D.xfixturesById.get(mid)); }
  function compOrder({ withHidden = false } = {}) {
    const p = ZS.store.prefs();
    const ids = (D.comps || []).map((c) => c.id);
    const order = [...(p.comp_order || []).filter((x) => ids.includes(x)), ...ids.filter((x) => !(p.comp_order || []).includes(x))];
    const fav = p.fav_comps || [];
    const sorted = [...order.filter((x) => fav.includes(x)), ...order.filter((x) => !fav.includes(x))];
    return withHidden ? sorted : sorted.filter((x) => !(p.comp_hidden || []).includes(x));
  }
  function compBadge(id, size = "") {
    const c = comp(id);
    const glyph = id === "UCL" ? "★" : id === "ENG1" ? "EN" : id === "ESP1" ? "ES" : id.slice(0, 2);
    return h("span.comp-badge" + (size ? "." + size : ""), { style: { "--cc": c.color }, "aria-hidden": "true" }, glyph);
  }
  const matchHref = (f) => fixtureComp(f) === "ESP1" ? ZS.href("match", f.match_id) : ZS.href("xmatch", f.match_id);
  const teamHref = (id, cid) => (D.teams.teams[id] && (!cid || cid === "ESP1")) ? ZS.href("team", id) : ZS.href("xteam", id);
  const seasonCache = {};
  async function compSeason(cid) {
    if (cid === "ESP1") return ZS.getJSON("season.json");
    if (!seasonCache[cid]) seasonCache[cid] = ZS.getJSON(comp(cid).base + "season.json");
    return seasonCache[cid];
  }

  // ------------------------------------------------------------------ state of a fixture and the live ring
  const LIVE_WARN = { postponed: "مؤجلة", cancelled: "ملغاة", suspended: "موقوفة مؤقتاً", abandoned: "أُوقفت", delayed: "متأخرة البداية" };
  function stateOf(f, now = Date.now()) {
    // 1. the live file (ESPN through the update job): verified state, minute and score
    const L = f.live;
    if (L && !f.score) {
      if (L.state === "live") return { kind: "live", minute: L.minute != null ? L.minute : 1, clock: L.clock, label: "مباشر", verified: true };
      if (L.state === "ht") return { kind: "ht", minute: 45, label: "استراحة", verified: true };
      if (L.state === "ft" && L.score) return { kind: "ft", label: "انتهت", verified: true };
      if (LIVE_WARN[L.state]) return { kind: "warn", label: LIVE_WARN[L.state], verified: true };
    }
    if (f.status === "HT") return { kind: "ht", minute: 45, label: "استراحة" };
    if (f.score) return { kind: "ft", label: "انتهت" };
    if (f.status === "abandoned") return { kind: "warn", label: "أُوقفت" };
    if (f.status === "postponed") return { kind: "warn", label: "مؤجلة" };
    const ko = f.kickoff_utc ? new Date(f.kickoff_utc).getTime() : null;
    if (ko && now >= ko && now < ko + 115 * 60000) {
      let m = Math.floor((now - ko) / 60000) + 1;
      if (m > 45 && m <= 60) return { kind: "ht", minute: 45, label: "استراحة", estimated: !f.live_score };
      if (m > 60) m -= 15;
      return { kind: "live", minute: Math.min(m, 90), label: "مباشر", estimated: !f.live_score && !(L && L.state === "live") };
    }
    if (f.status === "result_pending" || (ko && now >= ko + 115 * 60000)) return { kind: "warn", label: "بانتظار النتيجة" };
    return { kind: "pre", label: ko ? ZS.timeHM(f.kickoff_utc) : "—" };
  }
  /** final or live score from the snapshot first, then from the live file; null when unknown */
  function scoreOf(f) {
    if (f.score) return f.score;
    if (f.live && f.live.score && ["live", "ht", "ft"].includes(f.live.state)) return f.live.score;
    return f.live_score || null;
  }
  const GOALS = ["goal", "penalty_goal", "own_goal"];
  function goalMinutes(f) { return ((f.live && f.live.events) || []).filter((e) => GOALS.includes(e.kind) && e.minute != null).map((e) => e.minute); }
  function reds(f, side) { return ((f.live && f.live.events) || []).filter((e) => (e.kind === "red" || e.kind === "second_yellow") && e.side === side).length; }
  function ring(minute, label, goals = [], approx = false) {
    const r = 16.5, c = 2 * Math.PI * r, frac = Math.max(0.02, Math.min(1, minute / 90));
    const dots = goals.map((g) => {
      const a = (Math.min(g, 90) / 90) * 2 * Math.PI - Math.PI / 2;
      return `<circle cx="${(20 + r * Math.cos(a)).toFixed(2)}" cy="${(20 + r * Math.sin(a)).toFixed(2)}" r="2.3" class="ring-goal"/>`;
    }).join("");
    return ZS.svgEl(`<svg class="ring" viewBox="0 0 40 40" role="img" aria-label="${ZS.esc(label)}">` +
      `<circle cx="20" cy="20" r="${r}" class="ring-track"/>` +
      `<circle cx="20" cy="20" r="${r}" class="ring-prog" stroke-dasharray="${(frac * c).toFixed(2)} ${c.toFixed(2)}" transform="rotate(-90 20 20)"/>` +
      dots + `<text x="20" y="23.6" text-anchor="middle" class="ring-text">${approx ? "~" : ""}${minute}'</text></svg>`);
  }
  function miniBar(f) {
    if (!f.p) return null;
    const H = team(f.home), A = team(f.away);
    const [hc, ac] = ZS.pairColours(H, A);
    const cols = [hc, "var(--draw)", ac];
    const best = f.p.indexOf(Math.max(...f.p));
    return h("div.mini", { "aria-label": `توقع الحاسوب: فوز ${H.ar} ${pct(f.p[0])}، تعادل ${pct(f.p[1])}، فوز ${A.ar} ${pct(f.p[2])}` },
      h("div.mini-track", { "aria-hidden": "true" }, f.p.map((v, i) => h("i", { style: { flexBasis: `${(100 * v).toFixed(1)}%`, background: cols[i] } }))),
      h("div.mini-nums", { "aria-hidden": "true" }, f.p.map((v, i) => h("span" + (i === best ? ".best" : ""), pct(v)))));
  }
  function matchRow(f, { showComp = false, showDate = false } = {}) {
    const H = team(f.home), A = team(f.away);
    const st = stateOf(f);
    const p = ZS.store.prefs();
    const fav = p.fav_teams.includes(f.home) || p.fav_teams.includes(f.away);
    let center;
    const sc = scoreOf(f);
    if (st.kind === "live" || st.kind === "ht") {
      center = h("div.mrow-mid.live",
        ring(st.minute, st.kind === "ht" ? `استراحة${st.estimated ? " تقديرياً" : ""}` : `الدقيقة ${st.clock || st.minute}${st.estimated ? " تقديرياً، بدون بيانات مباشرة" : ""}`, goalMinutes(f), st.estimated),
        sc ? h("div.mrow-score.num", { "aria-label": `النتيجة ${H.ar} ${sc[0]}، ${A.ar} ${sc[1]}` }, h("span", sc[0]), h("i", "–"), h("span", sc[1]))
          : h("span.mrow-sub.live-t", st.estimated ? (st.kind === "ht" ? "استراحة · تقديري" : "بدأت · تقديري") : st.kind === "ht" ? "استراحة" : "مباشر"));
    } else if (st.kind === "ft" && sc) {
      center = h("div.mrow-mid",
        h("div.mrow-score.num", { "aria-label": `النتيجة ${H.ar} ${sc[0]}، ${A.ar} ${sc[1]}` }, h("span", sc[0]), h("i", "–"), h("span", sc[1])),
        h("span.mrow-sub", !f.score ? "انتهت · مباشر" : f.retro_hit === true ? "انتهت · ✓" : "انتهت"));
    } else {
      center = h("div.mrow-mid" + (st.kind === "warn" ? ".pending" : ""),
        h("span.mrow-time.num", f.kickoff_utc && f.time_known !== false ? ZS.timeHM(f.kickoff_utc) : "—"),
        h("span.mrow-sub", st.kind === "warn" ? st.label : showDate && f.kickoff_utc ? ZS.dateShort(f.kickoff_utc) : "بتوقيت بغداد"));
    }
    const won = st.kind === "ft" && sc ? (sc[0] > sc[1] ? 0 : sc[0] < sc[1] ? 2 : 1) : -1;
    const redTag = (side) => { const n = reds(f, side); return n ? h("span.red-tag", { "aria-label": `${n} طرد` }, n > 1 ? String(n) : "") : null; };
    return h("a.mrow" + (fav ? ".fav" : "") + (st.kind === "live" || st.kind === "ht" ? ".is-live" : ""), { href: matchHref(f) },
      h("div.mrow-team.home" + (won === 2 ? ".lost" : ""), ui().crest(f.home, "s"), h("span.nm", H.short || H.ar), redTag("home")),
      center,
      h("div.mrow-team.away" + (won === 0 ? ".lost" : ""), ui().crest(f.away, "s"), h("span.nm", A.short || A.ar), redTag("away")),
      showComp ? h("span.mrow-comp", compBadge(fixtureComp(f), "xs"), comp(fixtureComp(f)).short_ar) : null,
      miniBar(f));
  }
  ZS.hub = { comp, compOrder, compBadge, allFixtures, fixtureById, matchRow, matchHref, teamHref, compSeason, stateOf, scoreOf, ring, goalMinutes };

  // ------------------------------------------------------------------ Matches (home)
  const dayLabel = (key, today) => {
    const diff = Math.round((Date.parse(key) - Date.parse(today)) / 864e5);
    if (diff === 0) return "اليوم";
    if (diff === -1) return "أمس";
    if (diff === 1) return "باجر";
    return ZS.fmtDay ? ZS.fmtDay(key) : new Intl.DateTimeFormat("ar-IQ-u-nu-latn", { weekday: "short", timeZone: "UTC" }).format(new Date(key + "T12:00:00Z"));
  };
  const addDays = (key, n) => new Date(Date.parse(key + "T12:00:00Z") + n * 864e5).toISOString().slice(0, 10);

  async function renderMatches(view, params) {
    if (params.id && /^md\d+$/.test(params.id) && oldMatches) return oldMatches.render(view, params);
    const today = ZS.dayKey(new Date().toISOString());
    const all = allFixtures().filter((f) => f.kickoff_utc);
    const byDay = new Map();
    for (const f of all) { const k = ZS.dayKey(f.kickoff_utc); if (!byDay.has(k)) byDay.set(k, []); byDay.get(k).push(f); }
    const firstWithMatches = () => {
      for (let i = 0; i < 14; i++) { const k = addDays(today, i); if (byDay.has(k)) return k; }
      return today;
    };
    let day = params.id && /^\d{4}-\d{2}-\d{2}$/.test(params.id) ? params.id : (byDay.has(today) ? today : firstWithMatches());
    let filter = "all", query = "";
    const liveNow = () => all.filter((f) => ["live", "ht"].includes(stateOf(f).kind));

    const livePill = h("button.live-pill", { type: "button", "aria-pressed": "false" });
    const searchBtn = h("button.icon-btn", { type: "button", "aria-label": "بحث عن فريق" }, ui().icon("search"));
    const calInput = h("input.cal-input", { type: "date", "aria-label": "اختاري يوم", value: day });
    const calBtn = h("label.icon-btn.cal-btn", { "aria-label": "التقويم" }, ui().icon("calendar"), calInput);
    view.appendChild(h("div.hub-head",
      h("div", h("h1.hub-title", "المباريات"), h("p.hub-lead", "لاليغا والبريميرليغ ودوري الأبطال بيوم واحد، وتحت كل مباراة توقع الحاسوب")),
      h("div.hub-actions", livePill, searchBtn, calBtn)));
    const search = h("input.hub-search", { type: "search", placeholder: "ابحثي عن فريق…", hidden: true, "aria-label": "ابحثي عن فريق" });
    view.appendChild(search);
    const freshBox = h("div.fresh-row");
    view.appendChild(freshBox);
    const strip = h("div.datestrip", { role: "tablist", "aria-label": "الأيام" });
    view.appendChild(strip);
    const chips = h("div.chips.scroll", { role: "toolbar", "aria-label": "تصفية" });
    view.appendChild(chips);
    const body = h("div.hub-body");
    view.appendChild(body);

    function drawStrip() {
      ZS.clear(strip);
      const days = [];
      for (let i = -3; i <= 10; i++) days.push(addDays(today, i));
      if (!days.includes(day)) days.push(day);
      days.sort();
      for (const k of days) {
        const n = (byDay.get(k) || []).length;
        const d = new Date(k + "T12:00:00Z");
        const b = h("button.dchip" + (k === day ? ".on" : "") + (n ? ".has" : ""), {
          type: "button", role: "tab", "aria-selected": String(k === day), "aria-label": `${dayLabel(k, today)} ${ZS.dateShort(k + "T12:00:00Z")}${n ? `، ${n} مباريات` : "، ماكو مباريات"}`,
          onclick: () => { day = k; calInput.value = k; drawStrip(); draw(); history.replaceState(null, "", ZS.href("matches", k)); },
        }, h("span.dchip-d", dayLabel(k, today)), h("span.dchip-n.num", `${d.getUTCDate()}/${d.getUTCMonth() + 1}`), n ? h("i.dchip-dot") : null);
        strip.appendChild(b);
      }
      requestAnimationFrame(() => { const on = strip.querySelector(".on"); if (on && on.scrollIntoView) on.scrollIntoView({ block: "nearest", inline: "center" }); });
    }
    function draw() {
      if (ZS.live) {
        const fr = ZS.live.freshness();
        ZS.clear(freshBox).appendChild(fr.kind === "none" ? h("span.fresh.none", h("i.fresh-dot"), "النتائج المباشرة تنعرض أول ما يشتغل التحديث التلقائي") : ZS.live.freshTag());
      }
      const ln = liveNow();
      ZS.clear(livePill).append(h("i.live-dot"), h("span", `مباشر ${ln.length}`));
      livePill.setAttribute("aria-pressed", String(filter === "live"));
      livePill.disabled = !ln.length;
      ZS.clear(chips);
      for (const [k, lab] of [["all", "الكل"], ["fav", "المفضلة"], ["played", "انتهت"], ["upcoming", "قادمة"]]) {
        chips.appendChild(h("button.chip", { type: "button", "aria-pressed": String(filter === k), onclick: () => { filter = filter === k ? "all" : k; draw(); } }, lab));
      }
      ZS.clear(body);
      const p = ZS.store.prefs();
      let list = filter === "live" ? ln : (byDay.get(day) || []);
      if (query) {
        const q = query.trim();
        list = all.filter((f) => [team(f.home), team(f.away)].some((t) => (t.ar || "").includes(q) || (t.en || "").toLowerCase().includes(q.toLowerCase()) || (t.short || "").includes(q)))
          .sort((a, b) => a.kickoff_utc.localeCompare(b.kickoff_utc)).filter((f) => ZS.dayKey(f.kickoff_utc) >= addDays(today, -7)).slice(0, 40);
      }
      if (filter === "fav") list = list.filter((f) => p.fav_teams.includes(f.home) || p.fav_teams.includes(f.away) || (p.fav_comps || []).includes(fixtureComp(f)));
      if (filter === "played") list = list.filter((f) => f.score);
      if (filter === "upcoming") list = list.filter((f) => !f.score);
      const order = compOrder();
      list = list.filter((f) => order.includes(fixtureComp(f)));
      if (!list.length) {
        const next = firstWithMatches();
        body.appendChild(h("div.empty-day",
          h("div.empty-ball", { "aria-hidden": "true" }),
          h("p", query ? "ماكو فريق بهالاسم بالبطولات الثلاث" : filter === "live" ? "ماكو مباراة جارية هسه" : "ماكو مباريات بهاليوم ضمن البطولات المعروضة"),
          !query && next !== day ? h("button.btn.ghost", { type: "button", onclick: () => { day = next; calInput.value = next; drawStrip(); draw(); } }, `روحي لأقرب يوم بيه مباريات (${dayLabel(next, today)})`) : null));
        return;
      }
      const groups = new Map(order.map((c) => [c, []]));
      for (const f of list) groups.get(fixtureComp(f)).push(f);
      for (const [cid, fs] of groups) {
        if (!fs.length) continue;
        fs.sort((a, b) => a.kickoff_utc.localeCompare(b.kickoff_utc));
        const c = comp(cid);
        const collapsed = (p.collapsed || []).includes(cid);
        const isFav = (p.fav_comps || []).includes(cid);
        const md = [...new Set(fs.map((f) => f.matchday))];
        const head = h("div.cgroup-head",
          h("button.cgroup-toggle", { type: "button", "aria-expanded": String(!collapsed), onclick: () => toggleCollapse(cid) },
            compBadge(cid), h("span.cgroup-name", c.short_ar || c.name_ar), h("span.cgroup-sub", md.length === 1 ? (cid === "UCL" ? `مرحلة الدوري · الجولة ${md[0]}` : `الجولة ${md[0]}`) : `${fs.length} مباريات`),
            h("span.cgroup-chev" + (collapsed ? ".closed" : ""), ui().icon("down"))),
          h("button.star-btn" + (isFav ? ".on" : ""), { type: "button", "aria-pressed": String(isFav), "aria-label": isFav ? `شيلي ${c.short_ar} من المفضلة` : `ضيفي ${c.short_ar} للمفضلة`, onclick: () => toggleFavComp(cid) }, ui().icon("star")),
          h("a.cgroup-more", { href: ZS.href("comp", cid), "aria-label": `صفحة ${c.name_ar}` }, ui().icon("chevron")));
        const g = h("section.cgroup", { "aria-label": c.name_ar }, head);
        if (!collapsed) g.appendChild(h("div.cgroup-rows", fs.map((f) => matchRow(f, { showDate: !!query || filter === "live" }))));
        body.appendChild(g);
      }
      const shown = list.filter((f) => f.p);
      if (shown.length) body.appendChild(h("p.hub-note", ui().icon("info"), h("span", "الشريط تحت كل مباراة = توقع الحاسوب (فوز صاحب الأرض · تعادل · فوز الضيف). لاليغا بموديلها الكامل؛ البريميرليغ بنفس الموديل؛ دوري الأبطال بتقييم Elo.")));
    }
    async function toggleCollapse(cid) {
      const p = ZS.store.prefs();
      const set = new Set(p.collapsed || []);
      set.has(cid) ? set.delete(cid) : set.add(cid);
      await ZS.store.setPrefs({ collapsed: [...set] });
      draw();
    }
    async function toggleFavComp(cid) {
      const p = ZS.store.prefs();
      const set = new Set(p.fav_comps || []);
      set.has(cid) ? set.delete(cid) : set.add(cid);
      await ZS.store.setPrefs({ fav_comps: [...set] });
      draw();
    }
    livePill.addEventListener("click", () => { filter = filter === "live" ? "all" : "live"; draw(); });
    searchBtn.addEventListener("click", () => { search.hidden = !search.hidden; if (!search.hidden) search.focus(); else { query = ""; search.value = ""; draw(); } });
    search.addEventListener("input", () => { query = search.value; draw(); });
    calInput.addEventListener("change", () => { if (calInput.value) { day = calInput.value; drawStrip(); draw(); } });
    drawStrip();
    draw();
    const t = setInterval(() => { if (liveNow().length) draw(); }, 60000);
    const off = ZS.on("live", () => draw());
    return () => { clearInterval(t); off(); };
  }

  // ------------------------------------------------------------------ stories for News (from the computer's numbers)
  async function buildStories() {
    const out = [];
    try {
      const st = await ZS.getJSON("stories.json");
      for (const s of st.stories || []) {
        const mids = s.matches || [];
        const f = mids.length ? D.fixturesById.get(mids[0]) : null;
        out.push({ id: s.id, comp: "ESP1", kind: kindAr(s.type), title: s.title_ar, text: s.text_ar,
          teams: f ? [f.home, f.away] : (s.teams || []), stat: (s.evidence || [])[0] || null,
          href: f ? ZS.href("match", f.match_id) : ZS.href("season"), studio: ZS.href("studio", "story-" + s.id), score: s.score || 1 });
      }
    } catch (e) { /* no La Liga stories */ }
    for (const cid of ["ENG1", "UCL"]) {
      if (!D.xfixtures || !D.xfixtures[cid]) continue;
      let ss;
      try { ss = await compSeason(cid); } catch (e) { continue; }
      const c = comp(cid);
      const fx = D.xfixtures[cid];
      const T = (id) => team(id).ar;
      if (cid === "ENG1") {
        const pr = ss.projection.slice().sort((a, b) => b.p_title - a.p_title);
        const [a, b, c3] = pr;
        out.push({ id: "eng-title", comp: cid, kind: "سباق اللقب", title: `البريميرليغ: ${T(a.team)} ${pct(a.p_title)} و${T(b.team)} ${pct(b.p_title)}`,
          text: `بعد ${ss.table[0].P} جولات، ${T(a.team)} عنده ${a.pts_now} نقطة ومتوقع يخلص بحدود ${Math.round(a.exp_pts)}. ${T(c3.team)} الثالث بحظوظ ${pct(c3.p_title)}.`,
          teams: [a.team, b.team, c3.team], stat: { label_ar: "حظوظ اللقب", value: pct(a.p_title) }, href: ZS.href("comp", cid), score: 3 });
        const rel = ss.projection.slice().sort((x, y) => y.p_releg - x.p_releg).slice(0, 3);
        out.push({ id: "eng-releg", comp: cid, kind: "معركة البقاء", title: `خطر الهبوط: ${rel.map((r) => `${T(r.team)} ${pct(r.p_releg)}`).join("، ")}`,
          text: `أكثر ثلاث فرق مهددة بالهبوط حسب ${ss.n_sims.toLocaleString("en")} محاكاة لبقية الموسم.`, teams: rel.map((r) => r.team),
          stat: { label_ar: "احتمال الهبوط", value: pct(rel[0].p_releg) }, href: ZS.href("standings", cid), score: 2.2 });
      } else {
        const pr = ss.projection.slice().sort((a, b) => b.p_win - a.p_win);
        out.push({ id: "ucl-win", comp: cid, kind: "مين ياخذ الأبطال؟", title: `المرشحين للقب: ${pr.slice(0, 3).map((r) => `${T(r.team)} ${pct(r.p_win)}`).join("، ")}`,
          text: `محاكاة كاملة لمرحلة الدوري والأدوار الإقصائية (${ss.n_sims.toLocaleString("en")} مرة) بتقييم Elo يتحدث بكل نتيجة.`,
          teams: pr.slice(0, 3).map((r) => r.team), stat: { label_ar: "حظوظ اللقب", value: pct(pr[0].p_win) }, href: ZS.href("comp", cid), score: 3.2 });
        const risk = ss.projection.filter((r) => r.elo >= 1800 && r.p_out >= 0.08).sort((a, b) => b.p_out - a.p_out).slice(0, 3);
        if (risk.length) out.push({ id: "ucl-risk", comp: cid, kind: "كبار بخطر", title: `فرق كبيرة مهددة بالخروج: ${risk.map((r) => `${T(r.team)} ${pct(r.p_out)}`).join("، ")}`,
          text: "احتمال إنهاء مرحلة الدوري بالمركز 25 أو أقل (خروج مباشر).", teams: risk.map((r) => r.team),
          stat: { label_ar: "احتمال الخروج", value: pct(risk[0].p_out) }, href: ZS.href("standings", cid), score: 2.4 });
      }
      // biggest surprise of the last 10 days and the biggest match of the next 10 days
      const now = Date.now();
      const recent = fx.filter((f) => f.score && f.p && now - Date.parse(f.kickoff_utc) < 10 * 864e5);
      if (recent.length) {
        const sur = recent.map((f) => { const o = f.score[0] > f.score[1] ? 0 : f.score[0] < f.score[1] ? 2 : 1; return { f, o, q: f.p[o] }; }).sort((a, b) => a.q - b.q)[0];
        const f = sur.f;
        const what = sur.o === 1 ? `تعادل ${T(f.home)} و${T(f.away)}` : `${T(sur.o === 0 ? f.home : f.away)} فاز على ${T(sur.o === 0 ? f.away : f.home)}`;
        out.push({ id: cid + "-surprise", comp: cid, kind: "مفاجأة", title: `${what} ${ZS.scoreText(f.score[0], f.score[1])}`,
          text: `احتمال هالنتيجة قبل المباراة كان ${pct(sur.q)} بس (توقع بأثر رجعي بنفس الموديل).`, teams: [f.home, f.away],
          stat: { label_ar: "احتمالها قبل المباراة", value: pct(sur.q) }, href: matchHref(f), score: 2.6 - sur.q });
      }
      const soon = fx.filter((f) => !f.score && f.kickoff_utc && Date.parse(f.kickoff_utc) > now && Date.parse(f.kickoff_utc) - now < 12 * 864e5);
      if (soon.length) {
        const strength = (id) => { const r = ss.projection.find((x) => x.team === id); return r ? (r.elo || r.exp_pts * 30) : 0; };
        const big = soon.slice().sort((a, b) => Math.min(strength(b.home), strength(b.away)) - Math.min(strength(a.home), strength(a.away)))[0];
        out.push({ id: cid + "-big", comp: cid, kind: "قمة قادمة", title: `${T(big.home)} × ${T(big.away)}`,
          text: `${big.takeaway_ar}. النتيجة الأرجح ${big.top_score}.`, teams: [big.home, big.away],
          stat: { label_ar: ZS.dateShort(big.kickoff_utc), value: ZS.timeHM(big.kickoff_utc) }, href: matchHref(big), score: 2.5 });
      }
    }
    const p = ZS.store.prefs();
    for (const s of out) if ((s.teams || []).some((t) => p.fav_teams.includes(t))) s.score += 2;
    return out.sort((a, b) => b.score - a.score);
  }
  function kindAr(t) {
    return { high_stakes: "مباراة تحسم", forecast_shift: "تغيّر بالتوقع", streak: "سلسلة", upset: "مفاجأة", race: "سباق", milestone: "رقم" }[t] || "قصة";
  }
  function storyCard(s, { hero = false } = {}) {
    const teamsRow = h("div.story-crests", (s.teams || []).slice(0, 3).map((t) => ui().crest(t, "s")));
    return h("article.story" + (hero ? ".hero" : ""),
      h("div.story-top", compBadge(s.comp, "xs"), h("span.story-kind", s.kind), teamsRow),
      h("h3.story-title", h("a", { href: s.href }, s.title)),
      h("p.story-text", s.text),
      s.stat ? h("div.story-stat", h("span.num", String(s.stat.value)), h("small", s.stat.label_ar)) : null,
      h("div.story-actions", h("a.btn.ghost.sm", { href: s.href }, "التفاصيل"), s.studio ? h("a.btn.ghost.sm", { href: s.studio }, ui().icon("studio"), "اصنعي بطاقة") : null));
  }
  async function renderNews(view) {
    view.appendChild(h("div.hub-head", h("div", h("h1.hub-title", "الأخبار"), h("p.hub-lead", "قصص من أرقام الحاسوب نفسه، كل قصة بدليلها وجاهزة تصير محتوى"))));
    const stories = await buildStories();
    let headlines = null;
    if ((D.freeFiles || []).includes("headlines.json")) try { headlines = await ZS.getJSON("free/headlines.json"); } catch (e) { /* not fetched */ }
    const p = ZS.store.prefs();
    let teamFilter = null;
    const teamsInStories = [...new Set([...p.fav_teams, ...stories.flatMap((s) => s.teams || [])])].slice(0, 18);
    const rail = h("div.team-rail", { role: "toolbar", "aria-label": "تصفية حسب الفريق" });
    const body = h("div.stack-lg");
    view.append(rail, body);
    function draw() {
      ZS.clear(rail);
      rail.appendChild(h("button.team-chip" + (!teamFilter ? ".on" : ""), { type: "button", "aria-pressed": String(!teamFilter), onclick: () => { teamFilter = null; draw(); } }, h("span.all-dot", ui().icon("news")), h("span", "الكل")));
      for (const t of teamsInStories) rail.appendChild(h("button.team-chip" + (teamFilter === t ? ".on" : ""), { type: "button", "aria-pressed": String(teamFilter === t), onclick: () => { teamFilter = teamFilter === t ? null : t; draw(); } }, ui().crest(t, "s"), h("span", team(t).short || team(t).ar)));
      ZS.clear(body);
      const list = teamFilter ? stories.filter((s) => (s.teams || []).includes(teamFilter)) : stories;
      if (!list.length) { body.appendChild(ui().empty("ماكو قصص لهالفريق هسه")); return; }
      body.appendChild(storyCard(list[0], { hero: true }));
      if (list.length > 1) body.appendChild(ui().section("قصص أخرى", h("div.hscroll", list.slice(1, 9).map((s) => storyCard(s)))));
      if (list.length > 9) body.appendChild(h("div.grid.g-auto", list.slice(9).map((s) => storyCard(s))));
      if (headlines && headlines.items && headlines.items.length) {
        body.appendChild(ui().section("عناوين من مصادر خارجية", h("div.head-list", headlines.items.slice(0, 20).map((it) =>
          h("a.head-item", { href: it.link, target: "_blank", rel: "noopener noreferrer" }, h("strong", it.title),
            h("small", `${it.source}${it.published ? " · " + ZS.ago(it.published) : ""}`)))),
          h("span.small.muted", `آخر جلب ${ZS.ago(headlines.fetched_utc)}`)));
      } else {
        body.appendChild(ui().section("عناوين من مصادر خارجية", h("div.notice", ui().icon("info"),
          h("span", "هالنسخة ما تجيب عناوين من مواقع ثانية (رابط Claude ما يوصل لمواقع خارجية). لما يشتغل التحديث على جهازج أو على GitHub مجاناً (scripts/free_update.py)، يجيب عناوين من خلاصات RSS اللي تختارينها ويعرضها هنا بالعنوان والمصدر والرابط بس."))));
      }
    }
    draw();
  }

  // ------------------------------------------------------------------ Competitions
  async function renderComps(view, params) {
    if (params.id) return renderComp(view, params.id);
    view.appendChild(h("div.hub-head", h("div", h("h1.hub-title", "البطولات"), h("p.hub-lead", "النجمة = مفضلة (تطلع أول)، والأسهم ترتب، والعين تخفي البطولة من صفحة المباريات"))));
    const body = h("div.stack-lg");
    view.appendChild(body);
    function draw() {
      ZS.clear(body);
      const p = ZS.store.prefs();
      const order = compOrder({ withHidden: true });
      const fav = order.filter((c) => (p.fav_comps || []).includes(c) && !(p.comp_hidden || []).includes(c));
      const rest = order.filter((c) => !(p.fav_comps || []).includes(c) && !(p.comp_hidden || []).includes(c));
      const hidden = order.filter((c) => (p.comp_hidden || []).includes(c));
      const row = (cid, i, arr) => {
        const c = comp(cid);
        const isFav = (p.fav_comps || []).includes(cid), isHidden = (p.comp_hidden || []).includes(cid);
        const n = cid === "ESP1" ? D.fixtures.length : (D.xfixtures[cid] || []).length;
        return h("div.comp-row",
          h("span.grip", { "aria-hidden": "true" }, ui().icon("grip")),
          h("a.comp-main", { href: ZS.href("comp", cid) }, compBadge(cid, "lg"), h("span.comp-txt", h("strong", c.name_ar), h("small", `${c.country_ar || ""} · ${c.season || "2026/27"} · ${n} مباراة`))),
          h("div.comp-tools",
            h("button.icon-btn.sm", { type: "button", "aria-label": `${c.short_ar} لفوق`, disabled: i === 0, onclick: () => move(cid, -1, arr) }, ui().icon("up")),
            h("button.icon-btn.sm", { type: "button", "aria-label": `${c.short_ar} لجوة`, disabled: i === arr.length - 1, onclick: () => move(cid, 1, arr) }, ui().icon("down")),
            h("button.icon-btn.sm" + (isHidden ? ".on" : ""), { type: "button", "aria-pressed": String(isHidden), "aria-label": isHidden ? `أظهري ${c.short_ar}` : `أخفي ${c.short_ar}`, onclick: () => toggle("comp_hidden", cid) }, ui().icon(isHidden ? "eyeoff" : "eye")),
            h("button.star-btn" + (isFav ? ".on" : ""), { type: "button", "aria-pressed": String(isFav), "aria-label": isFav ? `شيلي ${c.short_ar} من المفضلة` : `ضيفي ${c.short_ar} للمفضلة`, onclick: () => toggle("fav_comps", cid) }, ui().icon("star"))));
      };
      if (fav.length) body.appendChild(ui().section("المفضلة", h("div.comp-list", fav.map((c, i, a) => row(c, i, a)))));
      if (rest.length) body.appendChild(ui().section("كل البطولات", h("div.comp-list", rest.map((c, i, a) => row(c, i, a)))));
      if (hidden.length) body.appendChild(ui().section("المخفية", h("div.comp-list", hidden.map((c, i, a) => row(c, i, a)))));
      body.appendChild(h("p.hub-note", ui().icon("info"), h("span", "بطولات ثانية (الدوري الألماني، الإيطالي…) ممكن تنضاف بنفس الطريقة المجانية؛ شوفي اقتراح النسخة القادمة بصفحة البيانات.")));
    }
    async function toggle(key, cid) {
      const p = ZS.store.prefs();
      const set = new Set(p[key] || []);
      set.has(cid) ? set.delete(cid) : set.add(cid);
      await ZS.store.setPrefs({ [key]: [...set] });
      draw();
    }
    async function move(cid, dir, arr) {
      const i = arr.indexOf(cid), j = i + dir;
      if (j < 0 || j >= arr.length) return;
      const swap = arr[j];
      const order = compOrder({ withHidden: true }).slice();
      const a = order.indexOf(cid), b = order.indexOf(swap);
      [order[a], order[b]] = [order[b], order[a]];
      await ZS.store.setPrefs({ comp_order: order });
      draw();
    }
    draw();
  }

  function oddsTable(cid, ss) {
    const ucl = cid === "UCL";
    const cols = ucl
      ? [["elo", "Elo", (r) => Math.round(r.elo)], ["pts_now", "نقاط", (r) => r.pts_now], ["p_top8", "أول 8", (r) => pct(r.p_top8)], ["p_playoff", "ملحق", (r) => pct(r.p_playoff)], ["p_out", "خروج", (r) => pct(r.p_out)], ["p_win", "اللقب", (r) => pct(r.p_win)]]
      : cid === "ENG1"
        ? [["pts_now", "نقاط", (r) => r.pts_now], ["exp_pts", "متوقع", (r) => Math.round(r.exp_pts)], ["p_title", "اللقب", (r) => pct(r.p_title)], ["p_top4", "أول 4", (r) => pct(r.p_top4)], ["p_releg", "هبوط", (r) => pct(r.p_releg)]]
        : [["pts_now", "نقاط", (r) => r.pts_now], ["exp_pts", "متوقع", (r) => Math.round(r.exp_pts)], ["p_title", "اللقب", (r) => pct(r.p_title)], ["p_ucl", "الأبطال", (r) => pct(r.p_ucl)], ["p_releg", "هبوط", (r) => pct(r.p_releg)]];
    let sortKey = ucl ? "p_win" : "exp_pts";
    const wrap = h("div.tbl-wrap");
    function draw() {
      const rows = ss.projection.map((r) => ({ ...r, id: r.id || r.team })).sort((a, b) => (b[sortKey] || 0) - (a[sortKey] || 0));
      ZS.clear(wrap).appendChild(h("table.tbl.odds",
        h("thead", h("tr", h("th", "#"), h("th.l", "الفريق"), cols.map(([k, lab]) => h("th", h("button.th-sort" + (k === sortKey ? ".on" : ""), { type: "button", onclick: () => { sortKey = k; draw(); } }, lab))))),
        h("tbody", rows.map((r, i) => h("tr" + (ZS.store.prefs().fav_teams.includes(r.id) ? ".fav" : ""),
          h("td.num.muted", i + 1),
          h("td.l", h("a.team-inline", { href: teamHref(r.id, cid) }, ui().crest(r.id, "s"), h("span.team-name", team(r.id).short || team(r.id).ar))),
          cols.map(([k, , fmt]) => h("td.num" + (k === sortKey ? ".hl" : ""), fmt(r))))))));
    }
    draw();
    return wrap;
  }

  async function renderComp(view, cid) {
    const c = comp(cid);
    const ss = await compSeason(cid);
    if (cid === "ESP1") {
      ss.projection.forEach((r) => { r.id = r.id || (D.keyToId[r.team] || r.team); });
      ss.projection = ss.projection.map((r) => ({ ...r, team: r.id }));
    }
    const fx = cid === "ESP1" ? D.fixtures : D.xfixtures[cid];
    view.appendChild(h("div.comp-hero", { style: { "--cc": c.color } },
      compBadge(cid, "xl"),
      h("div", h("p.eyebrow", `${c.country_ar || ""} · الموسم 2026/27`), h("h1.hub-title", c.name_ar),
        h("p.hub-lead", cid === "UCL" ? "36 فريق، 8 مباريات لكل فريق بمرحلة الدوري، أول 8 لدور الـ16 والمراكز 9-24 للملحق" : cid === "ENG1" ? "20 فريق؛ أول 4 لدوري الأبطال وآخر 3 تهبط" : "الموديل الكامل: مساران، سجل توقعات، تحليل مباشر"))));
    const top = ss.projection.slice().sort((a, b) => (cid === "UCL" ? b.p_win - a.p_win : b.p_title - a.p_title))[0];
    const leader = ss.table[0];
    const kp = (lab, val, sub) => h("div.kpi", h("span.kpi-lab", lab), h("strong.kpi-val", val), sub ? h("span.kpi-sub", sub) : null);
    view.appendChild(h("div.kpis",
      kp("المتصدر", team(leader.id || leader.team).ar, `${leader.Pts} نقطة`),
      kp(cid === "UCL" ? "المرشح للقب" : "المرشح للقب", team(top.id || top.team).ar, pct(cid === "UCL" ? top.p_win : top.p_title)),
      cid === "UCL" ? kp("المباريات", `${fx.filter((f) => f.score).length}/${fx.length}`, "انلعبت") : kp("محاكاة", (ss.n_sims || 0).toLocaleString("en"), "مرة لبقية الموسم")));
    view.appendChild(ui().section("حظوظ الموسم", oddsTable(cid, ss), h("a.small", { href: ZS.href("standings", cid) }, "الترتيب ←")));
    const now = Date.now();
    const next = fx.filter((f) => !f.score && f.kickoff_utc && Date.parse(f.kickoff_utc) > now - 3 * 3600e3).sort((a, b) => a.kickoff_utc.localeCompare(b.kickoff_utc));
    if (next.length) {
      const md = next[0].matchday;
      view.appendChild(ui().section(cid === "UCL" ? `الجولة ${md} من مرحلة الدوري` : `الجولة ${md}`,
        h("div.cgroup-rows", next.filter((f) => f.matchday === md).map((f) => matchRow(f, { showDate: true }))),
        cid === "ESP1" ? h("a.small", { href: ZS.href("round", "md" + md) }, "كل الجولة ←") : null));
    }
    const recent = fx.filter((f) => f.score).sort((a, b) => b.kickoff_utc.localeCompare(a.kickoff_utc)).slice(0, 8);
    if (recent.length) view.appendChild(ui().section("آخر النتائج", h("div.cgroup-rows", recent.map((f) => matchRow(f, { showDate: true })))));
    view.appendChild(ui().section("كيف انحسبت", modelNote(cid, ss)));
    if (cid === "ESP1") view.appendChild(h("div.row.wrap", h("a.btn", { href: ZS.href("season") }, "الموسم الكامل وماذا لو؟"), h("a.btn.ghost", { href: ZS.href("teams") }, "الفرق"), h("a.btn.ghost", { href: ZS.href("method") }, "المنهجية والدقة")));
  }

  function modelNote(cid, ss) {
    if (cid === "ESP1") return h("p.small", "موديل Dixon-Coles بمسارين (مدعوم بالسوق ومستقل)، اختبار خارج العينة على 3 مواسم، سجل توقعات قبل كل مباراة وتحليل مباشر. التفاصيل بصفحة المنهجية.");
    if (cid === "ENG1") {
      const ev = ss.evaluation;
      return h("div.stack",
        h("p.small", `نفس موديل الليغا (Dixon-Coles، مساران) وبنفس الإعدادات المختارة على الليغا، فاختبار البريميرليغ خارج العينة بالكامل. بيانات مجانية: نتائج وتسديدات على المرمى وأسعار Bet365 من 2000 لحد 31 آب 2026 (xgabora/football-data)، وبعدها النتائج من openfootball وSportRadar. محاكاة ${(ss.n_sims || 0).toLocaleString("en")} مرة لبقية الموسم.`),
        ev ? h("p.small", `الاختبار (${ev.seasons.join("، ")}، ${ev.n} مباراة): المسار المدعوم بالسوق أصاب الاحتمال الأرجح ${pct(ev.market.hit)} وRPS ${ev.market.rps}؛ Bet365 ${ev.bet365 ? pct(ev.bet365.hit) + " وRPS " + ev.bet365.rps : "—"}.`) : null,
        h("p.small.muted", `تحقق: النتائج تطابق الترتيب الرسمي ${ss.checks && ss.checks.official_table_matches ? "✓" : "✗"}. التسديدات والأسعار متوفرة لـ${ss.checks ? ss.checks.with_odds : "?"} مباراة من الموسم الحالي بس (المصدر المجاني يوقف 31 آب)؛ الباقي يتدرب على الأهداف.`));
    }
    const gm = ss.goal_model || {};
    return h("div.stack",
      h("p.small", `أندية من دوريات مختلفة، فالقوة من تقييم Elo: تقييمات ClubElo لحد ${ss.elo ? ss.elo.date : "؟"} (مجانية عبر xgabora)، وبعدها كل نتيجة بدوري الأبطال تحرك التقييم. الأهداف المتوقعة من موديل Poisson على فرق الـElo، متدرب على ${(gm.n || 0).toLocaleString("en")} مباراة محلية من 2016. شاختار وسلوفان من احتمالات SportRadar، وسلافيا وصباح بتقدير أولي (ماكو تقييم مجاني إلهم).`),
      h("p.small", `المحاكاة: بقية مرحلة الدوري + الملحق + الأدوار الإقصائية بنظام الشجرة الرسمي (القرعة عشوائية ضمن الأزواج) ${(ss.n_sims || 0).toLocaleString("en")} مرة.`),
      ss.checks && ss.checks.vs_sportradar_n ? h("p.small.muted", `مقارنة مع احتمالات SportRadar لـ${ss.checks.vs_sportradar_n} مباريات من الجولة 4: متوسط الفرق ${(100 * ss.checks.vs_sportradar_mean_abs_diff).toFixed(1)} نقطة مئوية لكل نتيجة.`) : null,
      h("p.small.muted", "ما ينحسب بعد: نتائج الدوريات المحلية بعد 1 أيلول للأندية الأوروبية (مخطط بالنسخة القادمة)."));
  }

  // ------------------------------------------------------------------ Standings
  async function renderStandings(view, params) {
    const order = compOrder();
    let cid = params.id && (D.comps || []).some((c) => c.id === params.id) ? params.id : order[0];
    let mode = "now";
    view.appendChild(h("div.hub-head", h("div", h("h1.hub-title", "الترتيب"), h("p.hub-lead", "الترتيب الحالي، أو المتوقع بنهاية الموسم من المحاكاة"))));
    const chips = h("div.chips.scroll", { role: "tablist", "aria-label": "البطولة" });
    const seg = h("div.seg", { role: "group", "aria-label": "نوع الترتيب" });
    const body = h("div");
    view.append(chips, h("div.row", seg), body);
    async function draw() {
      ZS.clear(chips);
      for (const c of order) chips.appendChild(h("button.chip", { type: "button", role: "tab", "aria-selected": String(c === cid), "aria-pressed": String(c === cid), onclick: () => { cid = c; history.replaceState(null, "", ZS.href("standings", c)); draw(); } }, compBadge(c, "xs"), comp(c).short_ar));
      ZS.clear(seg);
      for (const [k, lab] of [["now", "الحالي"], ["proj", "المتوقع"]]) seg.appendChild(h("button", { type: "button", "aria-pressed": String(mode === k), onclick: () => { mode = k; draw(); } }, lab));
      ZS.clear(body).appendChild(ui().skeleton ? ui().skeleton(6) : h("p", "…"));
      const ss = await compSeason(cid);
      const idOf = (r) => r.id || (cid === "ESP1" ? (D.keyToId[r.team] || r.team) : r.team);
      const zone = (pos, n) => {
        if (cid === "UCL") return pos <= 8 ? "z-top" : pos <= 24 ? "z-mid" : "z-out";
        if (cid === "ENG1") return pos <= 4 ? "z-top" : pos === 5 ? "z-mid2" : pos >= n - 2 ? "z-out" : "";
        return pos <= 4 ? "z-top" : pos === 5 ? "z-mid" : pos === 6 ? "z-mid2" : pos >= n - 2 ? "z-out" : "";
      };
      ZS.clear(body);
      const n = ss.table.length;
      if (mode === "now") {
        const rows = ss.table.map((r, i) => ({ ...r, id: idOf(r), pos: r.rank || r.pos || i + 1 }));
        body.appendChild(h("div.tbl-wrap", h("table.tbl.stand",
          h("thead", h("tr", h("th", "#"), h("th.l", "الفريق"), h("th", "لعب"), h("th.wdl", "ف"), h("th.wdl", "ت"), h("th.wdl", "خ"), h("th", "±"), h("th", "نقاط"), h("th.form-h", "آخر 5"))),
          h("tbody", rows.map((r) => h("tr" + (ZS.store.prefs().fav_teams.includes(r.id) ? ".fav" : ""),
            h("td.num.pos." + (zone(r.pos, n) || "z-none"), r.pos),
            h("td.l", h("a.team-inline", { href: teamHref(r.id, cid) }, ui().crest(r.id, "s"), h("span.team-name", team(r.id).short || team(r.id).ar))),
            h("td.num", r.P), h("td.num.wdl", r.W), h("td.num.wdl", r.D), h("td.num.wdl", r.L), h("td.num.gd", "\u2066" + (r.GD > 0 ? "+" + r.GD : String(r.GD)) + "\u2069"), h("td.num.pts", r.Pts),
            h("td.form", (r.form || []).map((x) => h("i.fd." + x, { title: { W: "فوز", D: "تعادل", L: "خسارة" }[x] }, { W: "ف", D: "ت", L: "خ" }[x])))))))));
      } else {
        const rows = ss.projection.map((r) => ({ ...r, id: idOf(r) })).sort((a, b) => a.exp_pos - b.exp_pos);
        body.appendChild(oddsTable(cid, { ...ss, projection: rows }));
      }
      const legend = cid === "UCL" ? [["z-top", "دور الـ16 مباشرة"], ["z-mid", "الملحق"], ["z-out", "خروج"]]
        : cid === "ENG1" ? [["z-top", "دوري الأبطال"], ["z-mid2", "مقعد خامس محتمل"], ["z-out", "هبوط"]]
          : [["z-top", "دوري الأبطال"], ["z-mid", "الدوري الأوروبي"], ["z-mid2", "المؤتمر"], ["z-out", "هبوط"]];
      body.appendChild(h("div.zone-legend", legend.map(([z, lab]) => h("span", h("i.zl." + z), lab))));
      body.appendChild(h("p.hub-note", ui().icon("info"), h("span", `كسر التعادل: ${ss.tiebreak_ar || (cid === "ESP1" ? "المواجهات المباشرة أولاً ثم فارق الأهداف (قواعد الليغا)" : "النقاط ثم فارق الأهداف")}`)));
    }
    draw();
  }

  // ------------------------------------------------------------------ Premier League / Champions League match page
  async function renderXMatch(view, params) {
    const f = fixtureById(params.id);
    if (!f) throw new Error("مباراة غير معروفة");
    const cid = fixtureComp(f);
    const c = comp(cid);
    const H = team(f.home), A = team(f.away);
    view.appendChild(h("a.back-link", { href: ZS.href("matches", f.kickoff_utc ? ZS.dayKey(f.kickoff_utc) : "") }, ui().icon("back"), "المباريات"));
    // header and live panel redraw in place when the live file changes (no jump to the top of the page)
    const top = h("div.stack");
    const drawTop = () => {
      const st = stateOf(f);
      const sc = scoreOf(f);
      const scoreEl = sc ? h("div.xm-score.num", h("span", sc[0]), h("i", "–"), h("span", sc[1])) : null;
      const mid = st.kind === "live" || st.kind === "ht" ? h("div.xm-mid", ring(st.minute, st.label, goalMinutes(f), st.estimated), scoreEl, h("span.mrow-sub", st.estimated ? "تقديري، بدون بيانات مباشرة" : (st.clock || st.label)))
        : scoreEl ? h("div.xm-mid", scoreEl, h("span.mrow-sub", st.label)) : h("div.xm-time.num", f.kickoff_utc ? ZS.timeHM(f.kickoff_utc) : "—");
      ZS.clear(top).appendChild(h("div.xm-head", { style: { "--cc": c.color } },
        h("div.xm-meta", compBadge(cid, "xs"), h("a", { href: ZS.href("comp", cid) }, c.name_ar), h("span", cid === "UCL" ? `مرحلة الدوري · الجولة ${f.matchday}` : `الجولة ${f.matchday}`), h("span", f.kickoff_utc ? ZS.dateLong(f.kickoff_utc) : "")),
        h("div.xm-teams",
          h("a.xm-team", { href: teamHref(f.home, cid) }, ui().crest(f.home, "l"), h("strong", H.ar), h("small", "صاحب الأرض")),
          mid,
          h("a.xm-team", { href: teamHref(f.away, cid) }, ui().crest(f.away, "l"), h("strong", A.ar), h("small", "الضيف")))));
      const lp = ZS.live && ZS.live.panel(f);
      top.appendChild(lp || h("p.hub-note", ui().icon("info"), h("span", "الأحداث والتشكيلات والأرقام المباشرة تظهر هنا من ESPN أول ما يجلبها التحديث التلقائي (قبل البداية بساعة وخلال المباراة).")));
    };
    drawTop();
    view.appendChild(top);
    const box = h("div.stack");
    box.appendChild(ui().probBar(f.home, f.away, f.p, { big: true }));
    box.appendChild(h("p.big-line", f.takeaway_ar));
    const g = h("div.kpis",
      h("div.kpi", h("span.kpi-lab", `أهداف متوقعة ${H.short || H.ar}`), h("strong.kpi-val.num", (f.xg[0]).toFixed(2))),
      h("div.kpi", h("span.kpi-lab", `أهداف متوقعة ${A.short || A.ar}`), h("strong.kpi-val.num", (f.xg[1]).toFixed(2))),
      h("div.kpi", h("span.kpi-lab", "النتيجة الأرجح"), h("strong.kpi-val.num", (f.top_scores && f.top_scores[0][0]) || f.top_score), f.top_scores ? h("span.kpi-sub", pct(f.top_scores[0][1])) : null));
    box.appendChild(g);
    if (f.top_scores) box.appendChild(h("div.chips", f.top_scores.map(([s, q]) => h("span.chip.static", h("span.num", s), " ", h("small.num", pct(q))))));
    if (f.sr_p) box.appendChild(h("div.notice", ui().icon("info"), h("span", `للمقارنة، SportRadar: ${pct(f.sr_p[0])} · ${pct(f.sr_p[1])} · ${pct(f.sr_p[2])}`)));
    if (f.p_independent) box.appendChild(h("p.small.muted", `المسار المستقل (بدون السوق): ${pct(f.p_independent[0])} · ${pct(f.p_independent[1])} · ${pct(f.p_independent[2])}`));
    if (f.note_ar) box.appendChild(h("p.small.muted", f.note_ar + (f.retro_hit !== undefined ? (f.retro_hit ? " · الاحتمال الأرجح صاب ✓" : " · الاحتمال الأرجح ما صاب") : "")));
    view.appendChild(ui().section(f.score ? "شنو كان يتوقع الحاسوب" : "توقع الحاسوب", box));
    // why: ratings (EPL) or Elo (UCL)
    const ss = await compSeason(cid);
    const why = h("div.stack");
    if (cid === "UCL" && f.elo) {
      const gap = f.elo[0] - f.elo[1];
      why.append(
        h("div.reason", h("span", `تقييم Elo: ${H.ar} ${Math.round(f.elo[0])} مقابل ${A.ar} ${Math.round(f.elo[1])}`), h("strong.num", (gap >= 0 ? "+" : "") + Math.round(gap))),
        h("div.reason", h("span", "ميزة الأرض بدوري الأبطال (عامة)"), h("strong.num", `+${Math.round((ss.elo && ss.elo.hfa_elo) || 65)} Elo`)),
        h("p.small.muted", `كل 100 نقطة Elo فرق ≈ ${((Math.exp((ss.goal_model.b_home) * 0.25) - 1) * 100).toFixed(0)}% أهداف أكثر للأقوى حسب موديل الأهداف.`));
      const ph = ss.projection.find((r) => r.team === f.home), pa = ss.projection.find((r) => r.team === f.away);
      if (ph && pa) why.appendChild(h("p.small", `حظوظ أول 8: ${H.ar} ${pct(ph.p_top8)} · ${A.ar} ${pct(pa.p_top8)}`));
    } else if (ss.ratings) {
      const rh = ss.ratings.find((r) => r.team === f.home), ra = ss.ratings.find((r) => r.team === f.away);
      const line = (t, r) => r ? h("div.reason", h("span", `${t.ar}: هجوم ×${r.attack} من المعدل، دفاع ×${r.defence} (أقل = أحسن)`)) : null;
      why.append(line(H, rh), line(A, ra), h("div.reason", h("span", "ميزة الأرض بالبريميرليغ (عامة)"), h("strong.num", `×${ss.home_adv_x}`)));
      const ph = ss.projection.find((r) => r.team === f.home), pa = ss.projection.find((r) => r.team === f.away);
      if (ph && pa) why.appendChild(h("p.small", `متوقع بنهاية الموسم: ${H.ar} ${Math.round(ph.exp_pts)} نقطة · ${A.ar} ${Math.round(pa.exp_pts)} نقطة`));
    }
    view.appendChild(ui().section("ليش هالتوقع؟", why));
    if (ZS.history) ZS.history.section(f).then((s) => view.appendChild(s)).catch(() => {});
    if (cid === "ENG1" && (D.freeFiles || []).includes("fpl_availability.json")) {
      try {
        const av = await ZS.getJSON("free/fpl_availability.json");
        const fplCode = { CFC: "CHE", LFC: "LIV", MCI: "MCI", MUN: "MUN", NFO: "NFO", BRI: "BHA", HUL: "HUL", COV: "COV", IPS: "IPS", SUN: "SUN", LEE: "LEE" };
        const code = (id) => fplCode[id] || id;
        const rows = av.players.filter((x) => [code(f.home), code(f.away)].includes(x.team));
        view.appendChild(ui().section("الغيابات (Fantasy Premier League)", rows.length
          ? h("div.stack", rows.map((x) => h("div.reason", h("span", `${x.team === code(f.home) ? H.ar : A.ar}: ${x.player} · ${x.status_ar}${x.chance_next !== null && x.chance_next !== undefined ? " · فرصة اللعب " + x.chance_next + "%" : ""}`), h("small.muted", x.news))), h("span.small.muted", `آخر جلب ${ZS.ago(av.fetched_utc)}`))
          : h("p.small", "ماكو غيابات مسجلة للفريقين بآخر جلب")));
      } catch (e) { /* FPL file not fetched in this build */ }
    }
    return ZS.on("live", drawTop);
  }

  // ------------------------------------------------------------------ any team (Premier League / Champions League / La Liga in Europe)
  async function renderXTeam(view, params) {
    const id = params.id;
    const t = team(id);
    view.appendChild(h("div.comp-hero", { style: { "--cc": t.color } }, ui().crest(id, "xl"),
      h("div", h("p.eyebrow", t.en || ""), h("h1.hub-title", t.ar), D.teams.teams[id] ? h("a.small", { href: ZS.href("team", id) }, "صفحة الفريق الكاملة بالليغا ←") : null)));
    const p = ZS.store.prefs();
    const isFav = p.fav_teams.includes(id);
    view.appendChild(h("div.row", h("button.btn" + (isFav ? ".ghost" : ""), { type: "button", onclick: async () => {
      const s = new Set(ZS.store.prefs().fav_teams); s.has(id) ? s.delete(id) : s.add(id);
      await ZS.store.setPrefs({ fav_teams: [...s] }); ZS.render();
    } }, ui().icon("star"), isFav ? "مفضل ✓" : "ضيفيه للمفضلة")));
    const fx = allFixtures().filter((f) => f.home === id || f.away === id).sort((a, b) => (a.kickoff_utc || "").localeCompare(b.kickoff_utc || ""));
    const comps = [...new Set(fx.map(fixtureComp))];
    for (const cid of comps) {
      try {
        const ss = await compSeason(cid);
        const r = ss.projection.find((x) => (x.id || (cid === "ESP1" ? D.keyToId[x.team] : x.team)) === id);
        if (!r) continue;
        const kp = (lab, val) => h("div.kpi", h("span.kpi-lab", lab), h("strong.kpi-val.num", val));
        const k = cid === "UCL" ? [kp("أول 8", pct(r.p_top8)), kp("الخروج", pct(r.p_out)), kp("اللقب", pct(r.p_win)), kp("Elo", Math.round(r.elo))]
          : [kp("نقاط متوقعة", Math.round(r.exp_pts)), kp("اللقب", pct(r.p_title)), kp(cid === "ENG1" ? "أول 4" : "الأبطال", pct(cid === "ENG1" ? r.p_top4 : r.p_ucl)), kp("الهبوط", pct(r.p_releg))];
        view.appendChild(ui().section(comp(cid).name_ar, h("div.kpis", k), h("a.small", { href: ZS.href("comp", cid) }, "البطولة ←")));
      } catch (e) { /* skip */ }
    }
    const now = Date.now();
    const next = fx.filter((f) => !f.score && f.kickoff_utc && Date.parse(f.kickoff_utc) > now - 3 * 3600e3).slice(0, 6);
    const last = fx.filter((f) => f.score).slice(-6).reverse();
    if (next.length) view.appendChild(ui().section("الجاية", h("div.cgroup-rows", next.map((f) => matchRow(f, { showComp: true, showDate: true })))));
    if (last.length) view.appendChild(ui().section("آخر النتائج", h("div.cgroup-rows", last.map((f) => matchRow(f, { showComp: true, showDate: true })))));
  }

  // ------------------------------------------------------------------ More
  function liveNotifyLabel(p) {
    if (!("Notification" in window)) return "غير مدعومة بهذا المتصفح";
    if (Notification.permission === "denied") return "مرفوضة من المتصفح";
    const on = p.live_notify && p.live_notify.enabled && Notification.permission === "granted";
    return on ? `شغالة · ${p.fav_teams.length ? countTeams(p.fav_teams.length) : "ضيفي فريق مفضل"}` : "طافية";
  }
  const countTeams = (n) => (n === 1 ? "فريق واحد" : n === 2 ? "فريقين" : `${n} فرق`);
  async function toggleLiveNotify() {
    const p = ZS.store.prefs();
    try {
      if (p.live_notify && p.live_notify.enabled && Notification.permission === "granted") {
        await ZS.store.setPrefs({ live_notify: { ...p.live_notify, enabled: false } });
        ZS.toast("طفيت إشعارات المباريات");
      } else {
        await ZS.live.enableNotifications();
        ZS.toast(p.fav_teams.length ? "إشعارات البداية والأهداف والطرد والنهاية لفرقج المفضلة توصل وقت التطبيق مفتوح. وهو مسدود: تطبيق ntfy (docs/LIVE.md)" : "اشتغلت. ضيفي فريق للمفضلة من صفحته حتى توصلج إشعاراته");
      }
    } catch (e) { ZS.toast(e.message); }
    ZS.render();
  }
  async function renderMore(view) {
    const p = ZS.store.prefs();
    let name = "";
    try { if (ZS.env.user && ZS.env.user.me) { const me = await ZS.env.user.me(); name = (me && me.name) || ""; } } catch (e) { /* ignore */ }
    const mode = { server: "خادم محلي", artifact: "رابط Claude", local: "معاينة بالمتصفح" }[ZS.env.mode] || "";
    view.appendChild(h("div.profile",
      h("span.avatar", { "aria-hidden": "true" }, (name || "ز").trim().charAt(0)),
      h("div", h("strong", name || "حاسوب زهراء الكروي"), h("small", { dir: "ltr" }, "@zahraatalksfootball94"), h("small", `${mode} · آخر تحديث ${ZS.ago(D.meta.generated_utc)}`))));
    const pills = [["studio", "الاستوديو", "studio"], ["lab", "مختبر التحقق", "lab"], ["challenge", "تحدي الجمهور", "challenge"], ["players", "اللاعبين", "teams"], ["archive", "الأرشيف العميق", "matches"], ["today", "ملخص اليوم", "today"], ["teams", "فرق الليغا", "teams"], ["season", "موسم الليغا", "season"], ["alerts", "التنبيهات", "bell"]];
    view.appendChild(h("div.pill-grid", pills.map(([k, lab, ic]) => h("a.pill-link", { href: ZS.href(k) }, ui().icon(ic), h("span", lab)))));
    const themeAr = { dark: "ليلي", light: "نهاري", system: "حسب الجهاز" }[p.theme || "dark"];
    const fsAr = { s: "صغير", m: "متوسط", l: "كبير" }[p.font_size || "m"];
    const row = (ic, lab, val, on) => h(on.href ? "a.set-row" : "button.set-row", on.href ? { href: on.href } : { type: "button", onclick: on.click },
      h("span.set-ico", ui().icon(ic)), h("span.set-lab", lab), val ? h("span.set-val", val) : null, h("span.set-chev", ui().icon("chevron")));
    const cycle = async (key, vals) => { const cur = ZS.store.prefs()[key]; const nx = vals[(vals.indexOf(cur) + 1) % vals.length]; await ZS.store.setPrefs({ [key]: nx }); ZS.applyTheme(); ZS.render(); };
    view.appendChild(h("div.set-list", { role: "list" },
      row("globe", "اللغة", "العربية", { click: () => ZS.toast("الواجهة عربية حالياً؛ الإنجليزية مقترحة للنسخة القادمة") }),
      row("moon", "المظهر", themeAr, { click: () => cycle("theme", ["dark", "light", "system"]) }),
      row("text", "حجم الخط", fsAr, { click: () => cycle("font_size", ["s", "m", "l"]) }),
      row("clock", "توقيت المباريات", `بغداد · ${p.clock === "12" ? "12 ساعة" : "24 ساعة"}`, { click: () => cycle("clock", ["24", "12"]) }),
      row("bell", "إشعارات المباريات المباشرة", liveNotifyLabel(p), { click: toggleLiveNotify }),
      row("bell", "التنبيهات", "", { href: ZS.href("alerts") }),
      row("comps", "ترتيب البطولات وإخفاؤها", "", { href: ZS.href("comps") }),
      row("method", "المنهجية والدقة", "", { href: ZS.href("method") }),
      row("data", "البيانات والمصادر المجانية", "", { href: ZS.href("data") }),
      row("settings", "إعدادات أكثر (الفرق المفضلة، بياناتي)", "", { href: ZS.href("prefs") })));
    view.appendChild(h("p.hub-note", ui().icon("info"), h("span", `النسخة 3.0 · ${D.meta.platform ? D.meta.platform.name : ""}`)));
  }

  Object.assign(ZS.routes, {
    matches: { render: renderMatches, title: "المباريات", currentMatchday: oldMatches && oldMatches.currentMatchday },
    news: { render: renderNews, title: "الأخبار" },
    comps: { render: renderComps, title: "البطولات" },
    comp: { render: (v, p) => renderComp(v, p.id || "ESP1"), title: "البطولة" },
    standings: { render: renderStandings, title: "الترتيب" },
    more: { render: renderMore, title: "المزيد" },
    xmatch: { render: renderXMatch, title: "المباراة" },
    xteam: { render: renderXTeam, title: "الفريق" },
  });
})();
