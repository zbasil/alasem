/* live.js (version 3.1): verified live scores for all three competitions.
   The update job (GitHub Actions or your computer) reads ESPN once and writes data/live/now.json; every viewer
   polls that one small file, so viewers never multiply requests to the source. When a live proxy is configured
   (workers/live-proxy, see docs/LIVE.md), live matches also read the shared edge cache every 30 seconds.
   Rules: a score or minute is shown as live only when the source says so; the age of every number is visible;
   a goal the source takes back (VAR) is shown as ruled out, never silently removed. */
(function () {
  "use strict";
  const ZS = window.ZS;
  const { h, D } = ZS;
  const ui = () => ZS.ui;

  const FAST = 60 * 1000, SLOW = 10 * 60 * 1000, PROXY = 30 * 1000;
  const STALE_MIN = 20;                 // a live file older than this is labelled delayed
  let doc = null, timer = null, lastErr = null, lastOk = 0, proxyTimer = null;
  const LEAGUE = { ESP1: "esp.1", ENG1: "eng.1", UCL: "uefa.champions" };

  function fixtures() { return [...(D.fixtures || []), ...Object.values(D.xfixtures || {}).flat()]; }
  function byId(mid) { return (D.fixturesById && D.fixturesById.get(mid)) || (D.xfixturesById && D.xfixturesById.get(mid)); }

  function ageMin() { return doc && doc.generated_utc ? (Date.now() - Date.parse(doc.generated_utc)) / 60000 : Infinity; }
  /** how much to trust the live layer right now: live, delayed, none */
  function freshness() {
    if (!doc) return { kind: "none", text: lastErr ? "تعذّر جلب البيانات المباشرة" : "ماكو بيانات مباشرة بعد" };
    const a = ageMin();
    const when = ZS.ago(doc.generated_utc);
    if (a <= STALE_MIN) return { kind: "live", text: `مباشر من ESPN · تحديث ${when}`, age: a };
    return { kind: "delayed", text: `متأخر: آخر تحديث مباشر ${when}`, age: a };
  }

  function apply() {
    const ms = (doc && doc.matches) || {};
    for (const f of fixtures()) {
      const e = ms[f.match_id];
      f.live = e && !(e.stale && e.state !== "ft") ? e : null;
    }
  }

  async function refresh() {
    try {
      const js = await ZS.getJSON("live/now.json", { fresh: true, retries: 0 });
      const changed = !doc || js.generated_utc !== doc.generated_utc;
      const before = doc;
      doc = js; lastErr = null; lastOk = Date.now();
      apply();
      if (changed) { notifyNew(before, js); ZS.emit("live", js); }
    } catch (e) {
      lastErr = e;
      if (doc) ZS.emit("live", doc);   // freshness labels move on even without new data
    }
    schedule();
  }

  /** poll fast only while it matters: a match live, or one starting within the next 15 minutes or begun in the
      last 2.5 hours; otherwise every 10 minutes. Hidden tabs do not poll. */
  function busy() {
    const now = Date.now();
    if (doc && doc.n_live) return true;
    return fixtures().some((f) => {
      if (!f.kickoff_utc || f.score) return false;
      const ko = Date.parse(f.kickoff_utc);
      return now >= ko - 15 * 60000 && now <= ko + 150 * 60000;
    });
  }
  function schedule() {
    clearTimeout(timer);
    if (document.hidden) return;
    timer = setTimeout(refresh, busy() ? FAST : SLOW);
    scheduleProxy();
  }
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); else { clearTimeout(timer); clearTimeout(proxyTimer); } });
  window.addEventListener("online", () => refresh());

  // ------------------------------------------------------------------ optional edge proxy (fresher than the job)
  function proxyBase() { return (doc && doc.proxy) || (D.meta && D.meta.live_proxy) || ""; }
  function scheduleProxy() {
    clearTimeout(proxyTimer);
    if (!proxyBase() || !doc || !doc.n_live || document.hidden) return;
    proxyTimer = setTimeout(pollProxy, PROXY);
  }
  async function pollProxy() {
    const base = proxyBase().replace(/\/$/, "");
    const comps = [...new Set(Object.values(doc.matches).filter((e) => ["live", "ht"].includes(e.state)).map((e) => e.comp))];
    const byEspn = new Map(Object.entries(doc.matches).map(([mid, e]) => [String(e.espn_id), mid]));
    let touched = false;
    for (const c of comps) {
      try {
        const r = await fetch(`${base}/${LEAGUE[c]}/scoreboard`, { cache: "no-store" });
        if (!r.ok) continue;
        const js = await r.json();
        for (const ev of js.events || []) {
          const mid = byEspn.get(String(ev.id));
          if (!mid) continue;
          const e = doc.matches[mid];
          const cp = (ev.competitions || [{}])[0];
          const st = ev.status || cp.status || {};
          const sides = {};
          for (const t of cp.competitors || []) sides[t.homeAway] = t.score === "" || t.score == null ? null : Number(t.score);
          const name = (st.type || {}).name || "";
          const state = /HALFTIME/.test(name) ? "ht" : /FINAL|FULL_TIME/.test(name) ? "ft" : (st.type || {}).state === "in" ? "live" : e.state;
          const score = sides.home != null && sides.away != null ? [sides.home, sides.away] : e.score;
          if (state !== e.state || String(score) !== String(e.score) || st.displayClock !== e.clock) {
            Object.assign(e, { state, score, clock: state === "live" ? st.displayClock : null,
              minute: state === "live" ? parseInt(st.displayClock, 10) || e.minute : null, via_proxy_utc: new Date().toISOString() });
            touched = true;
          }
        }
      } catch (err) { /* the static file stays the source */ }
    }
    if (touched) { apply(); ZS.emit("live", doc); }
    scheduleProxy();
  }

  // ------------------------------------------------------------------ browser notifications for favourite teams
  const SEEN_KEY = "zsc.v2.live_seen";
  function seenSet() { try { return new Set(JSON.parse(localStorage.getItem(SEEN_KEY) || "[]")); } catch (e) { return new Set(); } }
  function saveSeen(s) { try { localStorage.setItem(SEEN_KEY, JSON.stringify([...s].slice(-400))); } catch (e) { /* blocked */ } }
  const KIND_AR = { goal: "هدف", penalty_goal: "هدف من ضربة جزاء", own_goal: "هدف بالخطأ", red: "طرد", second_yellow: "طرد (إنذار ثاني)",
    yellow: "إنذار", sub: "تبديل", penalty_missed: "ضربة جزاء ضائعة", var: "مراجعة الفيديو", other: "حدث" };
  function notifyNew(before, after) {
    const p = ZS.store.prefs();
    const want = p.live_notify || {};
    if (!want.enabled || !("Notification" in window) || Notification.permission !== "granted") return;
    const seen = seenSet();
    const first = !before;   // the first load of a visit never fires for events that already happened
    for (const [mid, e] of Object.entries(after.matches || {})) {
      const f = byId(mid);
      if (!f || !(p.fav_teams.includes(f.home) || p.fav_teams.includes(f.away))) continue;
      const H = ZS.team(f.home), A = ZS.team(f.away);
      const line = e.score ? `${H.ar} ${e.score[0]} – ${e.score[1]} ${A.ar}` : `${H.ar} × ${A.ar}`;
      const fire = (key, title, body) => {
        if (seen.has(key)) return;
        seen.add(key);
        if (!first) show(title, body, key, mid);
      };
      if (want.start !== false && ["live", "ht", "ft"].includes(e.state)) fire(mid + ":start", "بدأت المباراة", line);
      for (const ev of e.events || []) {
        const isGoal = ["goal", "penalty_goal", "own_goal"].includes(ev.kind), isRed = ["red", "second_yellow"].includes(ev.kind);
        if ((isGoal && want.goals !== false) || (isRed && want.reds !== false)) fire(ev.id, `${KIND_AR[ev.kind]} ${ev.clock || ""}`, `${(ev.players || []).join("، ")} · ${line}`);
      }
      for (const r of e.retracted || []) if (["goal", "penalty_goal", "own_goal"].includes(r.kind)) fire(r.id + ":x", "الهدف انلغى", line);
      if (e.state === "ht" && want.ht) fire(mid + ":ht", "نهاية الشوط الأول", line);
      if (e.state === "ft" && want.ft !== false) fire(mid + ":ft", "نهاية المباراة", line);
    }
    saveSeen(seen);
  }
  async function show(title, body, tag, mid) {
    if (ZS.lang === "en" && ZS.i18n) { title = ZS.i18n.tr(title); body = ZS.i18n.tr(body); }
    const opts = { body, tag, lang: ZS.lang, dir: ZS.lang === "en" ? "ltr" : "rtl", data: { url: location.pathname + ZS.href(D.fixturesById.has(mid) ? "match" : "xmatch", mid) } };
    try {
      const reg = navigator.serviceWorker && (await navigator.serviceWorker.getRegistration());
      if (reg) return reg.showNotification(title, opts);
      new Notification(title, opts);
    } catch (e) { /* unsupported here */ }
  }
  async function enableNotifications() {
    if (!("Notification" in window)) throw new Error("هذا المتصفح ما يدعم الإشعارات");
    const r = await Notification.requestPermission();
    if (r !== "granted") throw new Error("الإذن مرفوض من المتصفح");
    const cur = ZS.store.prefs().live_notify || {};
    await ZS.store.setPrefs({ live_notify: { goals: true, reds: true, start: true, ft: true, ht: false, ...cur, enabled: true } });
    seenSet().size || saveSeen(new Set(Object.values((doc && doc.matches) || {}).flatMap((e) => (e.events || []).map((x) => x.id))));
  }

  // ------------------------------------------------------------------ live panel for a match page
  const STAT_AR = [
    ["possessionPct", "الاستحواذ", "%"], ["totalShots", "التسديدات", ""], ["shotsOnTarget", "على المرمى", ""],
    ["wonCorners", "الركنيات", ""], ["foulsCommitted", "الأخطاء", ""], ["offsides", "التسلل", ""],
    ["yellowCards", "الإنذارات", ""], ["redCards", "الطرد", ""], ["saves", "تصديات الحارس", ""],
    ["accuratePasses", "تمريرات صحيحة", ""], ["totalPasses", "التمريرات", ""], ["passPct", "دقة التمرير", "%"],
    ["totalTackles", "الافتكاك", ""], ["interceptions", "قطع الكرة", ""],
  ];
  function statRows(stats, f) {
    const hs = stats.home || {}, as = stats.away || {};
    const [hc, ac] = ZS.pairColours(ZS.team(f.home), ZS.team(f.away));
    const rows = [];
    for (const [k, lab, unit] of STAT_AR) {
      let a = hs[k], b = as[k];
      if (k === "passPct") { a = a != null && a <= 1 ? a * 100 : a; b = b != null && b <= 1 ? b * 100 : b; }
      if (a == null && b == null) continue;          // unknown on both sides: no row, never zeros
      const tot = (a || 0) + (b || 0);
      const fa = tot ? (a || 0) / tot : 0.5;
      const fmt = (v) => (v == null ? "—" : (Number.isInteger(v) ? v : v.toFixed(1)) + unit);
      rows.push(h("div.lstat", h("span.num.lstat-v", fmt(a)), h("span.lstat-l", lab), h("span.num.lstat-v", fmt(b)),
        h("div.lstat-bar", { "aria-hidden": "true" }, h("i", { style: { flexBasis: `${(100 * fa).toFixed(1)}%`, background: hc } }), h("i", { style: { flexBasis: `${(100 * (1 - fa)).toFixed(1)}%`, background: ac } }))));
    }
    return rows;
  }
  const ICON = { goal: "⚽", penalty_goal: "⚽", own_goal: "⚽", yellow: "▮", red: "▮", second_yellow: "▮", sub: "⇄", penalty_missed: "✕", var: "VAR", other: "•" };
  function timeline(e, f) {
    const evs = (e.events || []).filter((x) => x.kind !== "other");
    const items = evs.map((x) => h("li.tl-ev." + x.kind + "." + (x.side || "nos"),
      h("span.tl-min.num", x.clock || (x.minute != null ? x.minute + "'" : "")),
      h("span.tl-ico", { "aria-hidden": "true" }, ICON[x.kind]),
      h("span.tl-txt", h("strong", KIND_AR[x.kind]), (x.players || []).length ? " · " + x.players.join("، ") : "",
        x.side ? h("small.muted", " · " + ZS.team(x.side === "home" ? f.home : f.away).ar) : null)));
    for (const r of e.retracted || []) items.push(h("li.tl-ev.retracted", h("span.tl-min.num", r.clock || ""), h("span.tl-ico", "✕"),
      h("span.tl-txt", h("s", KIND_AR[r.kind] + ((r.players || []).length ? " · " + r.players.join("، ") : "")), h("small.muted", " · انلغى أو انسحب من المصدر"))));
    return items.length ? h("ol.tl-list", items) : h("p.small.muted", "ماكو أحداث مسجلة بالمصدر لحد هسه");
  }
  /** formation board: players placed by the announced formation and ESPN's formation places; positions are the
      line-up shape, not tracking data */
  function pitch(lineups, f) {
    const sides = ["home", "away"].map((s) => lineups.find((l) => l.side === s)).filter(Boolean);
    if (!sides.length) return null;
    const W = 68, L = 105;
    let marks = "";
    const nodes = [];
    sides.forEach((lu) => {
      const home = lu.side === "home";
      const starters = lu.players.filter((p) => p.starter);
      if (starters.length < 11) return;
      const ordered = starters.every((p) => p.place) ? starters.slice().sort((a, b) => a.place - b.place) : starters;
      const lines = String(lu.formation || "").split("-").map(Number).filter((n) => n > 0);
      if (lines.reduce((a, b) => a + b, 0) !== 10) return;
      const rows = [[ordered[0]]];
      let i = 1;
      for (const n of lines) { rows.push(ordered.slice(i, i + n)); i += n; }
      const col = ZS.team(home ? f.home : f.away);
      rows.forEach((row, ri) => {
        const depth = 4 + ri * (46 / rows.length);           // own half only
        const y = home ? L - depth - 2 : depth + 2;
        row.forEach((p, pi) => {
          const x = ((pi + 1) / (row.length + 1)) * W;
          const out = p.subbed_out ? " out" : "";
          marks += `<g class="pl${out}" transform="translate(${x.toFixed(1)} ${y.toFixed(1)})"><circle r="3.1" fill="${col.color}" stroke="${ZS.inkOn(col.color) === "#ffffff" ? "#fff" : "#0b0f0c"}" stroke-width=".5"/>` +
            `<text y="1.1" text-anchor="middle" font-size="2.6" font-weight="800" fill="${ZS.inkOn(col.color)}">${ZS.esc(p.jersey || "")}</text>` +
            `<text y="6.4" text-anchor="middle" font-size="2.3" class="pl-name">${ZS.esc(String(p.name || "").split(" ").slice(-1)[0])}</text></g>`;
          nodes.push(p);
        });
      });
    });
    if (!marks) return null;
    const lines = `<rect x="0" y="0" width="${W}" height="${L}" class="pt-grass"/>` +
      `<g class="pt-line" fill="none"><rect x="1" y="1" width="${W - 2}" height="${L - 2}"/><line x1="1" y1="${L / 2}" x2="${W - 1}" y2="${L / 2}"/>` +
      `<circle cx="${W / 2}" cy="${L / 2}" r="9.15"/><rect x="${W / 2 - 20.16}" y="1" width="40.32" height="16.5"/><rect x="${W / 2 - 20.16}" y="${L - 17.5}" width="40.32" height="16.5"/>` +
      `<rect x="${W / 2 - 9.16}" y="1" width="18.32" height="5.5"/><rect x="${W / 2 - 9.16}" y="${L - 6.5}" width="18.32" height="5.5"/></g>`;
    return ZS.svgEl(`<svg class="pitch-board" viewBox="0 0 ${W} ${L}" role="img" aria-label="التشكيلة على الملعب">${lines}${marks}</svg>`);
  }
  function lineupList(lu, f) {
    const t = ZS.team(lu.side === "home" ? f.home : f.away);
    const row = (p) => h("li", h("span.num.jn", p.jersey || ""), h("span", p.name || "—"), h("small.muted", p.pos || ""),
      p.subbed_in ? h("small.in", " ↑ دخل") : null, p.subbed_out ? h("small.out", " ↓ طلع") : null);
    return h("div.lu-col", h("h4", t.ar, lu.formation ? h("small.muted.num", " · ", h("bdi", { dir: "ltr" }, lu.formation)) : null),
      h("ul.lu-list", lu.players.filter((p) => p.starter).map(row)),
      h("p.small.muted", "الاحتياط"), h("ul.lu-list.bench", lu.players.filter((p) => !p.starter).map(row)));
  }
  function freshTag(e) {
    const fr = freshness();
    const via = e && e.via_proxy_utc ? ` · مباشر ${ZS.ago(e.via_proxy_utc)}` : "";
    return h("span.fresh." + fr.kind, { role: "status" }, h("i.fresh-dot"), fr.text + via);
  }
  // ------------------------------------------------------------------ live win probabilities and grounded insights
  const L = (ar, en) => (ZS.lang === "en" ? en : ar);
  /** in-play probabilities from the verified live state: pre-match expected goals + score + minute + red cards */
  function liveProbs(f, e) {
    if (!doc || !doc.inplay || !ZS.models || !f.xg || !e.score || !["live", "ht"].includes(e.state)) return null;
    const minute = e.state === "ht" ? 45 : e.minute;
    if (minute == null) return null;
    const period = e.state === "ht" ? 1 : (e.period || (minute <= 45 ? 1 : 2));
    const reds = (side) => (e.events || []).filter((x) => (x.kind === "red" || x.kind === "second_yellow") && x.side === side).length;
    try {
      const m = new ZS.models.InPlay(doc.inplay);
      return { p: m.probs(f.xg[0], f.xg[1], minute, e.score[0], e.score[1], reds("home"), reds("away"), period, 0), minute, version: m.version, rh: reds("home"), ra: reds("away") };
    } catch (err) { return null; }
  }
  /** short explanations, each tagged with what backs it: an observation from the source, an inference from those
      numbers, or a model estimate. Nothing about movement or tactics that the data cannot show. */
  function insights(f, e, lp) {
    const out = [];
    const H = ZS.team(f.home).ar, A = ZS.team(f.away).ar;
    const st = e.stats || {}, hs = st.home || {}, as = st.away || {};
    const num = (v) => (v == null ? null : Number(v));
    const pos = [num(hs.possessionPct), num(as.possessionPct)], sot = [num(hs.shotsOnTarget), num(as.shotsOnTarget)], sh = [num(hs.totalShots), num(as.totalShots)];
    const name = [H, A];
    if (pos[0] != null && pos[1] != null && sot[0] != null && sot[1] != null) {
      const k = pos[0] >= pos[1] ? 0 : 1, o = 1 - k;
      if (pos[k] - pos[o] >= 15 && sot[k] <= sot[o])
        out.push({ tag: "infer", text: L(`${name[k]} عنده الكرة ${Math.round(pos[k])}% بس تسديداته على المرمى ${sot[k]} مقابل ${sot[o]}: الاستحواذ لحد هسه ما تحوّل لخطورة أكثر.`,
          `${name[k]} has ${Math.round(pos[k])}% of the ball but ${sot[k]} shots on target to ${sot[o]}: possession has not turned into more danger so far.`) });
    }
    if (e.score && sot[0] != null && sot[1] != null && e.score[0] !== e.score[1]) {
      const lead = e.score[0] > e.score[1] ? 0 : 1, o = 1 - lead;
      if (sot[o] - sot[lead] >= 2)
        out.push({ tag: "infer", text: L(`${name[lead]} متقدم بس ${name[o]} سدد على المرمى أكثر (${sot[o]} مقابل ${sot[lead]}): النتيجة ممكن ما تعكس الفرص بالكامل.`,
          `${name[lead]} lead, but ${name[o]} have more shots on target (${sot[o]} to ${sot[lead]}): the score may not fully reflect the chances.`) });
    }
    if (sh[0] != null && sh[1] != null && Math.max(...sh) >= 8) {
      const k = sh[0] >= sh[1] ? 0 : 1, o = 1 - k;
      if (sh[k] >= 2 * Math.max(1, sh[o]))
        out.push({ tag: "obs", text: L(`${name[k]} يسدد أكثر بوضوح: ${sh[k]} تسديدة مقابل ${sh[o]}.`, `${name[k]} are out-shooting their opponents: ${sh[k]} shots to ${sh[o]}.`) });
    }
    if (lp && (lp.rh || lp.ra))
      out.push({ tag: "model", text: L(`الطرد بالموديل: الفريق الناقص يسجل بالمعدل ×${doc.inplay.red_own} من معدله والخصم ×${doc.inplay.red_opp} (مقدّر من مباريات بيها طرد، StatsBomb).`,
        `Red card in the model: the side down a man scores ×${doc.inplay.red_own} of its rate and the opponent ×${doc.inplay.red_opp} (estimated from matches with a red card, StatsBomb).`) });
    if (lp && f.p) {
      const i = [0, 1, 2].sort((a, b) => Math.abs(lp.p[b] - f.p[b]) - Math.abs(lp.p[a] - f.p[a]))[0];
      const d = lp.p[i] - f.p[i];
      if (Math.abs(d) >= 0.2) {
        const what = [L(`فوز ${H}`, `a ${H} win`), L("التعادل", "a draw"), L(`فوز ${A}`, `an ${A} win`.replace(/^an (?![AEIOU])/, "a "))][i];
        out.push({ tag: "model", text: L(`احتمال ${what} صار ${Math.round(100 * lp.p[i])}% بعد ما كان ${Math.round(100 * f.p[i])}% قبل المباراة.`,
          `The chance of ${what} is now ${Math.round(100 * lp.p[i])}%, from ${Math.round(100 * f.p[i])}% before kick-off.`) });
      }
    }
    return out;
  }
  const TAG = { obs: ["ملاحظة من الأرقام", "Observed"], infer: ["استنتاج إحصائي", "Inference"], model: ["تقدير الموديل", "Model estimate"] };
  function insightBox(items) {
    return h("div.stack", items.map((x) => h("div.insight." + x.tag, h("span.insight-tag", L(...TAG[x.tag])), h("span", x.text))),
      h("p.tiny.faint", L("التحليل من الأحداث والأرقام المنشورة بس. ماكو بيانات تتبع، فما نحكي عن تحركات أو ضغط ما تبينه الأرقام.",
        "Analysis uses published events and stats only. There is no tracking data, so nothing is said about movement or pressing the numbers cannot show.")));
  }

  /** everything the live file knows about one match; null when it knows nothing */
  function panel(f) {
    const e = f.live;
    if (!e) return null;
    const box = h("div.stack.live-panel");
    const info = e.info || {};
    const meta = [info.venue && `الملعب: ${info.venue}`, info.referee && `الحكم: ${info.referee}`, info.attendance && `الحضور: ${info.attendance.toLocaleString("en")}`].filter(Boolean);
    box.appendChild(h("div.row.wrap", freshTag(e), meta.length ? h("span.small.muted", meta.join(" · ")) : null));
    if (["postponed", "cancelled", "suspended", "abandoned", "delayed"].includes(e.state)) box.appendChild(h("div.notice.led", ui().icon("warn"), h("span", e.detail || e.state)));
    const corr = (e.score_history || []).filter((x) => x.correction);
    if (corr.length) box.appendChild(h("div.notice.led", ui().icon("warn"), h("span", `المصدر صحّح النتيجة ${corr.length === 1 ? "مرة" : corr.length + " مرات"}؛ آخر نتيجة معروضة هي الرسمية من المصدر.`)));
    const lp = liveProbs(f, e);
    if (lp) box.appendChild(ui().section(L("الاحتمالات المباشرة", "Live probabilities"), h("div.stack",
      ui().probBar(f.home, f.away, lp.p, { prev: f.p || null, label: L("الاحتمالات المباشرة", "Live probabilities") }),
      h("p.tiny.faint", L(`الدقيقة ${lp.minute}، النتيجة والطرد من المصدر، والأهداف المتوقعة قبل المباراة من الحاسوب. الموديل ${lp.version} انضبط على الليغا؛ تحت كل رقم الفرق عن توقع ما قبل المباراة.`,
        `Minute ${lp.minute}; score and red cards from the source, pre-match expected goals from the model. Model ${lp.version}, fitted on LaLiga; the change under each number is against the pre-match forecast.`)))));
    const ins = insights(f, e, lp);
    if (ins.length) box.appendChild(ui().section(L("قراءة المباراة", "Reading the match"), insightBox(ins)));
    box.appendChild(ui().section("الأحداث", timeline(e, f)));
    if (e.stats && (e.stats.home || e.stats.away)) {
      const rows = statRows(e.stats, f);
      if (rows.length) box.appendChild(ui().section("الأرقام", h("div.lstats", rows), h("span.small.muted", "المصدر: ESPN")));
    }
    if (e.has_lineups && e.lineups && e.lineups.length) {
      const confirmed = ["live", "ht", "ft"].includes(e.state) ? "التشكيلة الرسمية" : "التشكيلة المعلنة قبل المباراة";
      const pb = pitch(e.lineups, f);
      box.appendChild(ui().section(confirmed, h("div.stack",
        pb ? h("div.pitch-wrap", pb, h("p.small.muted", "مواقع اللاعبين حسب الخطة المعلنة وترتيبها، مو بيانات تتبع.")) : null,
        h("div.lu-grid", e.lineups.map((lu) => lineupList(lu, f))))));
    } else if (e.state === "pre") {
      box.appendChild(h("p.small.muted", "التشكيلات تنزل عادة قبل البداية بساعة، والتطبيق يجيبها أول ما تنعلن."));
    }
    return box;
  }

  ZS.live = { refresh, freshness, panel, freshTag, enableNotifications, doc: () => doc, KIND_AR, lastOk: () => lastOk, liveProbs, insights };
  ZS.on("core", () => { apply(); });
})();
