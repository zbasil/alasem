/* lab.js (version 3.1): head-to-head records and the claim lab, from real league results only.
   Data: data/history/<comp>.json (La Liga since 1993/94, Premier League since 2000/01), loaded only here.
   Every answer states its scope (league matches only: no cups, Super Cups or European games), its period and
   its source, and says "insufficient evidence" instead of stretching the data. */
(function () {
  "use strict";
  const ZS = window.ZS;
  const { h, D } = ZS;
  const ui = () => ZS.ui;
  const COMPS = { ESP1: "الدوري الإسباني", ENG1: "الدوري الإنجليزي" };
  const cache = {};

  async function load(comp) {
    if (!COMPS[comp]) return null;
    if (!cache[comp]) cache[comp] = ZS.getJSON(`history/${comp}.json`).catch((e) => { delete cache[comp]; throw e; });
    return cache[comp];
  }
  const ymd = (n) => `${String(n).slice(0, 4)}-${String(n).slice(4, 6)}-${String(n).slice(6, 8)}`;
  const seasonLabel = (s) => `${s}/${String((s + 1) % 100).padStart(2, "0")}`;
  function teamName(doc, id) {
    const t = (D.teams && D.teams.teams[id]) || (D.xteams && D.xteams[id]);
    if (t) return t.ar;
    const x = doc.teams[id] || {};
    return x.ar || x.en || id;
  }

  /** every league meeting of a and b in [from, to] seasons; venue: all | a_home | b_home */
  function meetings(doc, a, b, { from = -Infinity, to = Infinity, venue = "all" } = {}) {
    return doc.rows.filter((r) => r[7] >= from && r[7] <= to &&
      ((r[1] === a && r[2] === b && venue !== "b_home") || (r[1] === b && r[2] === a && venue !== "a_home")));
  }
  function tally(rows, a) {
    const t = { n: rows.length, w: 0, d: 0, l: 0, gf: 0, ga: 0 };
    for (const r of rows) {
      const gf = r[1] === a ? r[3] : r[4], ga = r[1] === a ? r[4] : r[3];
      t.gf += gf; t.ga += ga;
      if (gf > ga) t.w++; else if (gf === ga) t.d++; else t.l++;
    }
    return t;
  }
  function teamRecord(doc, a, from, to) {
    const rows = doc.rows.filter((r) => r[7] >= from && r[7] <= to && (r[1] === a || r[2] === a));
    const t = tally(rows, a);
    t.pts = 3 * t.w + t.d;
    t.seasons = new Set(rows.map((r) => r[7])).size;
    return t;
  }

  // ------------------------------------------------------------------ head-to-head block for match pages
  function bar(t, A, B, ca, cb) {
    const seg = (n, col) => h("i", { style: { flexBasis: `${t.n ? (100 * n) / t.n : 33.3}%`, background: col } });
    return h("div.stack", { style: { gap: "6px" } },
      h("div.h2h-bar", { "aria-hidden": "true" }, seg(t.w, ca), seg(t.d, "var(--draw)"), seg(t.l, cb)),
      h("div.h2h-nums", h("span", h("strong.num", t.w), ` فوز ${A}`), h("span", h("strong.num", t.d), " تعادل"), h("span", h("strong.num", t.l), ` فوز ${B}`)));
  }
  async function section(f) {
    const comp = f.comp || String(f.match_id).split("-")[0];
    const box = h("div.stack");
    if (!COMPS[comp]) {
      box.appendChild(h("p.small.muted", "سجل المواجهات متوفر لمباريات الدوري الإسباني والإنجليزي بس. دوري الأبطال ما عنده أرشيف نتائج بالمصادر المجانية الحالية."));
      return ui().section("المواجهات السابقة", box);
    }
    let doc;
    try { doc = await load(comp); } catch (e) { box.appendChild(h("p.small.muted", "سجل المواجهات ما انحمل؛ جربي بعدين.")); return ui().section("المواجهات السابقة", box); }
    const rows = meetings(doc, f.home, f.away).filter((r) => ymd(r[0]) < (f.kickoff_utc || "9999").slice(0, 10));
    const A = teamName(doc, f.home), B = teamName(doc, f.away);
    if (!rows.length) {
      box.appendChild(h("p.small.muted", `ما تواجهوا بالدوري منذ ${seasonLabel(doc.coverage.seasons[0])} حسب البيانات.`));
      return ui().section("المواجهات السابقة", box);
    }
    const [ca, cb] = ZS.pairColours(ZS.team(f.home), ZS.team(f.away));
    const t = tally(rows, f.home);
    box.appendChild(bar(t, A, B, ca, cb));
    box.appendChild(h("p.small", `${rows.length} مباراة بالدوري منذ ${seasonLabel(rows[0][7])}: أهداف ${A} ${t.gf} مقابل ${t.ga}. معدل ${(((t.gf + t.ga) / t.n) || 0).toFixed(2)} هدف بالمباراة.`));
    const last = rows.slice(-6).reverse();
    box.appendChild(h("ol.h2h-list", last.map((r) => h("li",
      h("span.small.muted.num", ymd(r[0])),
      h("span", teamName(doc, r[1])), h("strong.num", `${r[3]} – ${r[4]}`), h("span", teamName(doc, r[2]))))));
    box.appendChild(h("p.tiny.faint", `${doc.scope_ar}. المصدر: ${doc.source}.`));
    box.appendChild(h("a.small", { href: ZS.href("lab", `${comp}.${f.home}.${f.away}`) }, "افتحيها بمختبر التحقق ←"));
    return ui().section("المواجهات السابقة", box);
  }

  // ------------------------------------------------------------------ the claim lab
  const CLAIMS = [
    ["more_wins", (A, B) => `${A} فاز على ${B} أكثر ما ${B} فاز عليه`],
    ["more_goals", (A, B) => `${A} سجل أهداف أكثر من ${B} بمواجهاتهم`],
    ["unbeaten", (A, B) => `${A} ما خسر من ${B} بهالفترة`],
    ["majority", (A, B) => `${A} فاز بأكثر من نص المواجهات`],
  ];
  function verdict(kind, t) {
    if (!t.n) return { v: "insufficient", why: "ماكو مواجهات بالبيانات ضمن هالفترة والملعب المختار." };
    if (kind === "more_wins") return t.w > t.l ? { v: "supported", why: `${t.w} فوز مقابل ${t.l}.` } : { v: "contradicted", why: t.w === t.l ? `متعادلين بعدد الانتصارات: ${t.w} لكل طرف.` : `${t.w} فوز مقابل ${t.l}: العكس هو الصحيح.` };
    if (kind === "more_goals") return t.gf > t.ga ? { v: "supported", why: `${t.gf} هدف مقابل ${t.ga}.` } : { v: "contradicted", why: t.gf === t.ga ? `نفس عدد الأهداف: ${t.gf}.` : `${t.gf} هدف مقابل ${t.ga}.` };
    if (kind === "unbeaten") return t.l === 0 ? { v: "supported", why: `${t.n} مباراة بدون خسارة (${t.w} فوز، ${t.d} تعادل).` } : { v: "contradicted", why: `خسر ${t.l} ${t.l === 1 ? "مرة" : "مرات"} من ${t.n}.` };
    if (kind === "majority") return t.w * 2 > t.n ? { v: "supported", why: `${t.w} فوز من ${t.n} (${Math.round((100 * t.w) / t.n)}%).` } : { v: "contradicted", why: `${t.w} فوز من ${t.n} (${Math.round((100 * t.w) / t.n)}%).` };
    return { v: "insufficient", why: "" };
  }
  const V_AR = { supported: "مدعوم بالأرقام", contradicted: "الأرقام ترفضه", insufficient: "الأدلة ما تكفي" };

  function reelScript(ctx) {
    const { A, B, t, period, claimText, ver, comp } = ctx;
    const hook = ver.v === "supported" ? `يگولون «${claimText}»… والأرقام تگول: صح.` : ver.v === "contradicted" ? `يگولون «${claimText}»… بس الأرقام عدها رأي ثاني.` : `«${claimText}»؟ خلونا نشوف شنو تگول الأرقام.`;
    return [
      `[الافتتاحية 0–5 ثواني]`, hook, "",
      `[الأرقام 5–40 ثانية]`,
      `بـ${COMPS[comp]}، من ${period}، تواجهوا ${t.n} مرة.`,
      `${A}: ${t.w} فوز. ${B}: ${t.l} فوز. والتعادل ${t.d}.`,
      `الأهداف: ${A} ${t.gf} مقابل ${t.ga} لـ${B}.`, "",
      `[الخلاصة 40–70 ثانية]`,
      `الحكم: ${V_AR[ver.v]}. ${ver.why}`,
      `انتبهوا: هاي مباريات الدوري بس، بدون الكأس والسوبر وأوروبا.`, "",
      `[الختام]`, `إنتو شتگولون؟ اكتبوا بالتعليقات.`, "",
      `المصدر: ${ctx.source}. تحقق: حاسوب زهراء الكروي.`,
    ].join("\n");
  }

  async function render(view, params) {
    view.appendChild(ui().pageHead("مختبر التحقق", "اختاري فريقين وفترة وادعاء، والمختبر يرجع للنتائج الحقيقية ويحكم: مدعوم، مرفوض، أو الأدلة ما تكفي. كل حكم وياه أرقامه ومصدره.", null, "بحث ومحتوى"));
    const [c0, a0, b0] = String(params.id || "").split(".");
    const st = { comp: COMPS[c0] ? c0 : "ESP1", a: a0 || "BAR", b: b0 || "RMA", from: null, to: null, venue: "all", claim: "more_wins", mode: "h2h", t2from: null, t2to: null };
    const form = h("div.card.stack");
    const out = h("div.stack");
    view.append(form, out);

    async function draw() {
      ZS.clear(form); ZS.clear(out);
      let doc;
      try { doc = await load(st.comp); } catch (e) { out.appendChild(ui().errorCard(e, draw)); return; }
      const [s0, s1] = doc.coverage.seasons;
      if (st.from === null || st.from < s0 || st.from > s1) st.from = s0;
      if (st.to === null || st.to > s1 || st.to < s0) st.to = s1;
      const current = new Set(((st.comp === "ESP1" ? D.teams.current : Object.keys((D.xfixtures.ENG1 || []).reduce((o, f) => (o[f.home] = 1, o), {}))) || []));
      const ids = Object.keys(doc.teams).sort((x, y) => (current.has(y) - current.has(x)) || teamName(doc, x).localeCompare(teamName(doc, y), "ar"));
      if (!ids.includes(st.a)) st.a = ids[0];
      if (!ids.includes(st.b) || st.b === st.a) st.b = ids.find((x) => x !== st.a);
      const sel = (label, key, opts) => {
        const s = h("select", { "aria-label": label, onchange: (e) => { st[key] = isNaN(Number(e.target.value)) || key === "a" || key === "b" ? e.target.value : Number(e.target.value); draw(); } },
          opts.map(([v, lab]) => h("option", { value: v, selected: String(v) === String(st[key]) }, lab)));
        return h("label.field", h("span.small.muted", label), s);
      };
      const seasons = []; for (let s = s0; s <= s1; s++) seasons.push([s, seasonLabel(s)]);
      const teamOpts = ids.map((x) => [x, teamName(doc, x) + (current.has(x) ? "" : " (سابقاً)")]);
      form.append(
        h("div.chips", [["h2h", "مواجهة فريقين"], ["eras", "مقارنة فترتين لفريق"]].map(([k, lab]) =>
          h("button.chip", { type: "button", "aria-pressed": String(st.mode === k), onclick: () => { st.mode = k; draw(); } }, lab))),
        h("div.lab-grid",
          sel("البطولة", "comp", Object.entries(COMPS)),
          sel(st.mode === "h2h" ? "الفريق الأول" : "الفريق", "a", teamOpts),
          st.mode === "h2h" ? sel("الفريق الثاني", "b", teamOpts.filter(([x]) => x !== st.a)) : null,
          sel(st.mode === "h2h" ? "من موسم" : "الفترة الأولى: من", "from", seasons),
          sel(st.mode === "h2h" ? "لحد موسم" : "الفترة الأولى: لحد", "to", seasons.filter(([s]) => s >= st.from)),
          st.mode === "h2h" ? sel("الملعب", "venue", [["all", "كل المباريات"], ["a_home", `بملعب ${teamName(doc, st.a)}`], ["b_home", `بملعب ${teamName(doc, st.b)}`]]) : null,
          st.mode === "eras" ? sel("الفترة الثانية: من", "t2from", seasons) : null,
          st.mode === "eras" ? sel("الفترة الثانية: لحد", "t2to", seasons) : null,
          st.mode === "h2h" ? sel("الادعاء", "claim", CLAIMS.map(([k, fn]) => [k, fn(teamName(doc, st.a), teamName(doc, st.b))])) : null),
        h("p.tiny.faint", `البيانات: ${doc.scope_ar}، من ${doc.coverage.from} لحد ${doc.coverage.to} (${doc.coverage.n.toLocaleString("en")} مباراة). المصدر: ${doc.source}.`));
      if (st.mode === "h2h") drawH2H(doc); else drawEras(doc, s0, s1);
    }

    function drawH2H(doc) {
      const A = teamName(doc, st.a), B = teamName(doc, st.b);
      const rows = meetings(doc, st.a, st.b, { from: st.from, to: st.to, venue: st.venue });
      const t = tally(rows, st.a);
      const claimText = CLAIMS.find(([k]) => k === st.claim)[1](A, B);
      const ver = verdict(st.claim, t);
      const period = `${seasonLabel(st.from)} لحد ${seasonLabel(st.to)}`;
      const [ca, cb] = ZS.pairColours(ZS.team(st.a), ZS.team(st.b));
      out.appendChild(h("div.card.stack.verdict." + ver.v,
        h("p.eyebrow", "الادعاء"), h("h2.verdict-claim", `«${claimText}»`),
        h("div.verdict-tag", V_AR[ver.v]), h("p", ver.why),
        h("p.small.muted", `النطاق: ${COMPS[st.comp]}، ${period}، ${st.venue === "all" ? "كل الملاعب" : st.venue === "a_home" ? "بملعب " + A : "بملعب " + B}. ${doc.scope_ar}؛ لو الادعاء يقصد كل البطولات، الحكم هنا جزئي.`),
        t.n ? bar(t, A, B, ca, cb) : null,
        t.n ? h("div.kpis", h("div.kpi", h("span.kpi-lab", "المباريات"), h("strong.kpi-val.num", t.n)), h("div.kpi", h("span.kpi-lab", `أهداف ${A}`), h("strong.kpi-val.num", t.gf)), h("div.kpi", h("span.kpi-lab", `أهداف ${B}`), h("strong.kpi-val.num", t.ga))) : null));
      if (t.n) {
        const text = `${claimText}: ${V_AR[ver.v]}. ${ver.why} (${COMPS[st.comp]}، ${period}، الدوري فقط. المصدر: ${doc.source})`;
        const script = reelScript({ A, B, t, period, claimText, ver, comp: st.comp, source: doc.source });
        const scriptBox = h("pre.script-box", { hidden: true }, script);
        out.appendChild(h("div.row.wrap",
          h("button.btn", { type: "button", onclick: () => copy(text) }, ui().icon("check"), "انسخي الخلاصة"),
          h("button.btn", { type: "button", onclick: () => { scriptBox.hidden = !scriptBox.hidden; } }, ui().icon("studio"), "نص ريل (60–90 ثانية)"),
          h("button.btn.ghost", { type: "button", onclick: () => copy(script) }, "انسخي النص")));
        out.appendChild(scriptBox);
        out.appendChild(ui().section(`كل المواجهات (${t.n})`, h("ol.h2h-list.full", rows.slice().reverse().map((r) => h("li",
          h("span.small.muted.num", ymd(r[0])), h("span", teamName(doc, r[1])), h("strong.num", `${r[3]} – ${r[4]}`), h("span", teamName(doc, r[2])),
          r[5] != null ? h("small.muted.num", `(${r[5]}–${r[6]})`) : null)))));
      }
    }

    function drawEras(doc, s0, s1) {
      if (st.t2from === null) st.t2from = Math.max(s0, s1 - 2);
      if (st.t2to === null || st.t2to < st.t2from) st.t2to = s1;
      const A = teamName(doc, st.a);
      const r1 = teamRecord(doc, st.a, st.from, st.to), r2 = teamRecord(doc, st.a, st.t2from, st.t2to);
      const p1 = `${seasonLabel(st.from)}–${seasonLabel(st.to)}`, p2 = `${seasonLabel(st.t2from)}–${seasonLabel(st.t2to)}`;
      const per = (x, n) => (n ? (x / n).toFixed(2) : "—");
      const pc = (x, n) => (n ? Math.round((100 * x) / n) + "%" : "—");
      const rows = [["المباريات", r1.n, r2.n], ["نقاط بالمباراة", per(r1.pts, r1.n), per(r2.pts, r2.n)], ["نسبة الفوز", pc(r1.w, r1.n), pc(r2.w, r2.n)],
        ["أهداف له بالمباراة", per(r1.gf, r1.n), per(r2.gf, r2.n)], ["أهداف عليه بالمباراة", per(r1.ga, r1.n), per(r2.ga, r2.n)], ["فوز / تعادل / خسارة", `${r1.w}/${r1.d}/${r1.l}`, `${r2.w}/${r2.d}/${r2.l}`]];
      out.appendChild(h("div.card.stack",
        h("h2", `${A}: ${p1} مقابل ${p2}`),
        h("div.tbl-wrap", h("table.tbl", h("thead", h("tr", h("th", ""), h("th", p1), h("th", p2))), h("tbody", rows.map(([l, a, b]) => h("tr", h("td", l), h("td.num", String(a)), h("td.num", String(b))))))),
        h("p.small.muted", "لمقارنة مدربين: اختاري المواسم اللي درّب بيها كل واحد. البيانات ما بيها تواريخ تعيين المدربين، فالمقارنة بالمواسم الكاملة، والموسم اللي تغير بيه المدرب يدخل كامل."),
        r1.n < 38 || r2.n < 38 ? h("p.small", "تنبيه: فترة أقل من موسم كامل؛ الفرق ممكن يكون صدفة.") : null));
    }
    function copy(text) {
      try { navigator.clipboard.writeText(text).then(() => ZS.toast("انتسخ"), () => ZS.toast("ما گدرت أنسخ؛ ظلليه وانسخيه")); } catch (e) { ZS.toast("ما گدرت أنسخ"); }
    }
    await draw();
  }

  ZS.history = { load, meetings, tally, verdict, section };
  ZS.routes.lab = { render, title: "مختبر التحقق" };
})();
