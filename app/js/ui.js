/* ui.js: shared components (icons, crests, probability bars, match cards, sheets, states). */
(function () {
  "use strict";
  const ZS = window.ZS;
  const { h, svgEl, esc, pct, num, pp, team } = ZS;

  // ------------------------------------------------------------------ icons (drawn for this app)
  const P = {
    lab: '<path d="M9 3h6"/><path d="M10 3v6l-5 9a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3l-5-9V3"/><path d="M7.5 15h9"/>',
    today: '<path d="M4 9h16M8 3v4M16 3v4"/><rect x="4" y="5" width="16" height="15" rx="2.5"/><circle cx="12" cy="14" r="2.6"/>',
    matches: '<rect x="3.5" y="5" width="17" height="14" rx="2"/><path d="M12 5v14M3.5 10h3v4h-3M20.5 10h-3v4h3"/><circle cx="12" cy="12" r="2.2"/>',
    teams: '<path d="M12 3l7 2.2v6.3c0 4.6-3 7.8-7 9.5-4-1.7-7-4.9-7-9.5V5.2z"/><path d="M9 11.5l2 2 4-4"/>',
    season: '<path d="M8 4h8v4.5a4 4 0 0 1-8 0zM8 6H5a2.5 2.5 0 0 0 3 3.5M16 6h3a2.5 2.5 0 0 1-3 3.5M12 12.5V16M8.5 20h7M10 16h4v4h-4z"/>',
    studio: '<rect x="3.5" y="6" width="17" height="13" rx="2.5"/><path d="M8.5 6l1.5-2.5h4L15.5 6"/><circle cx="12" cy="12.5" r="3.4"/>',
    method: '<path d="M4 19h16M6.5 16v-4M11 16V8M15.5 16v-6M20 16V5"/>',
    data: '<ellipse cx="12" cy="6" rx="7" ry="2.6"/><path d="M5 6v12c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6V6M5 12c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M12 3v2.5M12 18.5V21M3 12h2.5M18.5 12H21M5.6 5.6l1.8 1.8M16.6 16.6l1.8 1.8M5.6 18.4l1.8-1.8M16.6 7.4l1.8-1.8"/>',
    challenge: '<path d="M7 4h10v3a5 5 0 0 1-10 0zM12 12v4M8 20h8l-1-4H9z"/><path d="M4.5 5.5h2.5M17 5.5h2.5"/>',
    bell: '<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15zM10 20.5a2.2 2.2 0 0 0 4 0"/>',
    star: '<path d="M12 3.6l2.6 5.3 5.8.8-4.2 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.2-4.1 5.8-.8z"/>',
    pin: '<path d="M9 3.5h6l-1 5 3.5 3.5h-11L10 8.5zM12 12v8.5"/>',
    back: '<path d="M9 5l7 7-7 7"/>',
    info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.6v.4"/>',
    warn: '<path d="M12 4l9 16H3zM12 10v4.5M12 17.4v.3"/>',
    refresh: '<path d="M19.5 8.5A8 8 0 1 0 20 13M20 4v4.5h-4.5"/>',
    download: '<path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M5 19.5h14"/>',
    copy: '<rect x="8" y="8" width="11.5" height="11.5" rx="2"/><path d="M5 15.5V6a1.5 1.5 0 0 1 1.5-1.5H15"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    edit: '<path d="M4.5 19.5l1-4.2L15.8 5a2 2 0 0 1 2.9 0l.3.3a2 2 0 0 1 0 2.9L8.7 18.5z"/>',
    trash: '<path d="M5 7h14M10 7V5h4v2M7 7l1 12.5h8L17 7"/>',
    ball: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5l3.6 2.6-1.4 4.3H9.8L8.4 10.1z"/><path d="M12 3.5v4M20.2 9.4l-4.6.7M17 19l-2.8-4.6M7 19l2.8-4.6M3.8 9.4l4.6.7"/>',
    card: '<rect x="7" y="4" width="10" height="15" rx="1.8"/>',
    whistle: '<circle cx="9" cy="14" r="5"/><path d="M13 11.5l8-3.5v4l-6.5 2"/>',
    external: '<path d="M14 4h6v6M20 4l-9 9M18 14v5.5H4.5V6H10"/>',
    eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="3"/>',
    lock: '<rect x="5" y="11" width="14" height="9.5" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    spark: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>',
    flag: '<path d="M6 21V4M6 4.5h11l-2.5 4 2.5 4H6"/>',
  };
  Object.assign(P, {
    news: '<rect x="4" y="4.5" width="16" height="15" rx="2.2"/><path d="M8 9h8M8 12.5h8M8 16h5"/>',
    comps: '<path d="M8 4h8v4.5a4 4 0 0 1-8 0zM12 12.5V16M8.5 20h7M10 16h4v4h-4z"/><path d="M5 6.5h3M16 6.5h3"/>',
    standings: '<path d="M4 6h16M4 12h16M4 18h16"/><path d="M8 4v16"/>',
    more: '<circle cx="6" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="18" cy="12" r="1.6"/>',
    search: '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
    calendar: '<rect x="4" y="5.5" width="16" height="14.5" rx="2.4"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>',
    filter: '<path d="M4 6h16M7 12h10M10 18h4"/>',
    up: '<path d="M6 14l6-6 6 6"/>',
    down: '<path d="M6 10l6 6 6-6"/>',
    grip: '<circle cx="9" cy="7" r="1.2"/><circle cx="15" cy="7" r="1.2"/><circle cx="9" cy="12" r="1.2"/><circle cx="15" cy="12" r="1.2"/><circle cx="9" cy="17" r="1.2"/><circle cx="15" cy="17" r="1.2"/>',
    eyeoff: '<path d="M3 3l18 18M10.6 6a9.6 9.6 0 0 1 1.4-.1c6 0 9.5 6.5 9.5 6.5a17 17 0 0 1-2.8 3.6M6.3 7.6A17 17 0 0 0 2.5 12S6 18.5 12 18.5a9 9 0 0 0 4-.9"/>',
    globe: '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.6 2.6 3.8 5.4 3.8 8.5s-1.2 5.9-3.8 8.5c-2.6-2.6-3.8-5.4-3.8-8.5s1.2-5.9 3.8-8.5z"/>',
    moon: '<path d="M19 14.5A7.5 7.5 0 0 1 9.5 5a7.5 7.5 0 1 0 9.5 9.5z"/>',
    text: '<path d="M4 18L9 6l5 12M5.8 14h6.4M15 18l3-7 3 7M15.8 16h4.4"/>',
    clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    user: '<circle cx="12" cy="8.5" r="3.6"/><path d="M5 20c.8-3.8 3.6-5.8 7-5.8s6.2 2 7 5.8"/>',
    trophy: '<path d="M8 4h8v4.5a4 4 0 0 1-8 0zM8 6H5a2.5 2.5 0 0 0 3 3.5M16 6h3a2.5 2.5 0 0 1-3 3.5M12 12.5V16M8.5 20h7M10 16h4v4h-4z"/>',
    chevron: '<path d="M15 6l-6 6 6 6"/>',
  });
  function icon(name, cls = "") {
    return svgEl(`<svg class="ico ico-${name} ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[name] || P.info}</svg>`);
  }

  // ------------------------------------------------------------------ crests (generic shields in club colours)
  const PATTERN = {
    ATM: "stripes", BAR: "stripes", ATH: "stripes", RBB: "stripes", ESP: "stripes", DEP: "stripes", MCF: "stripes",
    RSO: "stripes", LEV: "stripes", ALA: "stripes", GIR: "stripes", SPO: "stripes", SAN: "stripes", RVC: "sash",
    ELC: "band", OVI: "plain", LPA: "band", CAD: "plain", ALM: "halves", HUE: "halves", LEG: "plain",
    // version 3: Premier League and Champions League clubs (generic patterns, not their badges)
    NEW: "stripes", BRE: "stripes", SUN: "stripes", CRY: "stripes", BOU: "stripes", INT: "stripes", FCP: "stripes",
    PSV: "stripes", ASK: "stripes", FEN: "stripes", BRU: "stripes", RCL: "stripes", VFB: "band", FEY: "halves",
    GAL: "halves", SLA: "halves", BLA: "halves", AVL: "band", MCI: "plain", LFC: "plain",
  };
  let crestN = 0;
  function crest(id, size = "") {
    const t = team(id);
    const k0 = (t.kit && t.kit[0]) || t.color, k1 = (t.kit && t.kit[1]) || "#ffffff";
    const cid = "cr" + (++crestN);
    const pat = PATTERN[t.id] || "plain";
    let fill = `<rect width="40" height="47" fill="${k0}"/>`;
    if (pat === "stripes") for (let i = 1; i < 8; i += 2) fill += `<rect x="${i * 5}" width="5" height="47" fill="${k1}"/>`;
    else if (pat === "sash") fill += `<path d="M-4 36L36 -4 46 4 6 46z" fill="${k1}"/>`;
    else if (pat === "band") fill += `<rect y="14" width="40" height="11" fill="${k1}"/>`;
    else if (pat === "halves") fill += `<rect x="20" width="20" height="47" fill="${k1}"/>`;
    else fill += `<path d="M2 6L20 1v45C10 42 2 34 2 22z" fill="#000" fill-opacity=".08"/>`;
    const code = esc(t.id || "");
    const markup = `<svg class="crest ${size}" viewBox="0 0 40 47" role="img" aria-label="${esc(t.ar || t.id)}">` +
      `<clipPath id="${cid}"><path d="M20 1L38 6v16c0 12-8 20-18 24C10 42 2 34 2 22V6z"/></clipPath>` +
      `<g clip-path="url(#${cid})">${fill}<rect y="29" width="40" height="11" fill="#0b0f0c" fill-opacity=".72"/>` +
      `<text x="20" y="37.6" text-anchor="middle" font-size="8.4" font-weight="800" fill="#fff" font-family="Changa, Cairo, sans-serif" letter-spacing=".4">${code}</text></g>` +
      `<path d="M20 1L38 6v16c0 12-8 20-18 24C10 42 2 34 2 22V6z" fill="none" stroke="currentColor" stroke-opacity=".28" stroke-width="1.4"/></svg>`;
    return svgEl(markup);
  }
  function teamInline(id, { link = true } = {}) {
    const t = team(id);
    const inner = [crest(id, "s"), h("span.team-name", t.ar)];
    return link ? h("a.team-inline", { href: ZS.href("team", id) }, inner) : h("span.team-inline", inner);
  }

  // ------------------------------------------------------------------ probability bar
  /** p = [home, draw, away]; prev = previous forecast (shows the change) */
  function probBar(homeId, awayId, p, { big = false, prev = null, label = "" } = {}) {
    const H = team(homeId), A = team(awayId);
    const [hc, ac] = ZS.pairColours(H, A);
    const names = big ? [H.ar, "تعادل", A.ar] : [H.short, "تعادل", A.short];
    const cols = [hc, "var(--draw)", ac];
    const wrap = h("div.pbar" + (big ? ".big" : ""), { role: "group", "aria-label": label || `احتمالات ${H.ar} ضد ${A.ar}` });
    if (!p) { wrap.appendChild(h("div.small.faint", "ماكو توقع لهالمباراة")); return wrap; }
    wrap.appendChild(h("div.pbar-track", { "aria-hidden": "true" }, p.map((v, i) =>
      h("i.pbar-seg" + (i === 1 ? ".draw" : ""), { style: { flexBasis: `${(100 * v).toFixed(2)}%`, background: cols[i] } }))));
    wrap.appendChild(h("div.pbar-legend", p.map((v, i) => {
      const d = prev ? v - prev[i] : null;
      return h("div",
        h("span.lab", h("i.sw", { style: { background: cols[i] } }), h("span", i === 1 ? "تعادل" : (big ? "فوز " : "") + names[i])),
        h("span.val.num", pct(v)),
        d !== null && Math.abs(d) >= 0.005 ? h("span.chg.delta." + (d > 0 ? "up" : "down"), `${pp(d)} ن.م`) : null);
    })));
    return wrap;
  }

  // ------------------------------------------------------------------ status of a fixture
  function statusOf(f, now = Date.now()) {
    if (f.status === "HT") return { cls: "ht", text: "استراحة" };
    if (f.score) return { cls: "ft", text: "انتهت" };
    if (f.status === "abandoned") return { cls: "warn", text: "أُوقفت" };
    if (f.status === "result_pending") return { cls: "warn", text: "بانتظار النتيجة" };
    if (f.status === "postponed") return { cls: "warn", text: "مؤجلة" };
    const ko = f.kickoff_utc ? new Date(f.kickoff_utc).getTime() : null;
    if (ko && now >= ko && now < ko + 115 * 60000) return { cls: "live", text: "جارية" };
    return { cls: "soon", text: ko ? ZS.until(f.kickoff_utc, now) || "قادمة" : "الموعد غير محدد" };
  }
  function pill(f) { const s = statusOf(f); return h("span.pill." + s.cls, s.text); }
  function kickoffLabel(f) {
    if (!f.kickoff_utc) return f.kickoff_baghdad && f.kickoff_baghdad.date ? `${ZS.dateShort(f.kickoff_baghdad.date + "T12:00:00Z")} · الوقت غير محدد` : "غير محدد";
    return `${ZS.dateLong(f.kickoff_utc)} · ${ZS.timeHM(f.kickoff_utc)}`;
  }

  // ------------------------------------------------------------------ match card (scoreboard)
  function matchCard(f, { prev = null, compact = false, line = "" } = {}) {
    const prefs = ZS.store.prefs();
    const watched = prefs.watchlist.includes(f.match_id);
    const H = team(f.home), A = team(f.away);
    const mid = !f.score && f.live_score
      ? h("div.sb-mid",
        h("div.sb-score", { "aria-label": `النتيجة الحالية ${H.ar} ${f.live_score[0]}، ${A.ar} ${f.live_score[1]}` }, h("span.g", f.live_score[0]), h("span.sep", "–"), h("span.g", f.live_score[1])),
        h("span.sb-sub", f.status === "HT" ? "نهاية الشوط الأول" : "مباشر"))
      : f.score
      ? h("div.sb-mid",
        h("div.sb-score", { "aria-label": `النتيجة ${H.ar} ${f.score[0]}، ${A.ar} ${f.score[1]}` }, h("span.g", f.score[0]), h("span.sep", "–"), h("span.g", f.score[1])),
        f.ht ? h("span.sb-sub", `الشوط الأول ${ZS.scoreText(f.ht[0], f.ht[1])}`) : null)
      : h("div.sb-mid",
        h("span.sb-time", f.kickoff_utc ? ZS.timeHM(f.kickoff_utc) : "—"),
        h("span.sb-sub", f.kickoff_utc ? ZS.dateShort(f.kickoff_utc) : "الموعد غير محدد"));
    const p = f.p || null;
    const card = h("a.sb" + (watched ? ".watch" : ""), { href: ZS.href("match", f.match_id) },
      h("div.sb-top",
        h("span", `الجولة ${f.matchday}`, watched ? " · ★ متابَعة" : ""),
        pill(f)),
      h("div.sb-teams",
        h("div.sb-team", crest(f.home, "m"), h("span.team-name", H.ar)),
        mid,
        h("div.sb-team.away", crest(f.away, "m"), h("span.team-name", A.ar))),
      compact ? null : probBar(f.home, f.away, p, { prev }),
      line ? h("div.sb-line", line) : null,
      compact ? null : h("div.sb-foot",
        h("span", f.score ? (f.retro_hit === true ? "✓ الأرجح صار" : f.retro_hit === false ? "✗ الأرجح ما صار" : "") : (f.importance ? `أهمية ${num(f.importance, 0)}` : "")),
        h("span", f.score ? "توقع استرجاعي" : (p ? "توقع الحاسوب" : ""))));
    return card;
  }

  // ------------------------------------------------------------------ states
  function errorCard(err, retry) {
    return h("div.card", h("div.notice.bad", icon("warn"),
      h("div.stack", { style: { gap: "8px" } },
        h("strong", "صار خطأ بتحميل هالصفحة"),
        h("span.small", String((err && err.message) || err)),
        retry ? h("div", h("button.btn.small", { type: "button", onclick: retry }, icon("refresh"), "حاول مرة ثانية")) : null)));
  }
  function skeleton(n = 3, height = 120) {
    return h("div.grid.g-auto", Array.from({ length: n }, () => h("div.skel", { style: { height: height + "px" } })));
  }
  function empty(text) { return h("div.empty", text); }
  function pageHead(title, lead, actions, eyebrow) {
    return h("div.page-head",
      h("div", eyebrow ? h("div.eyebrow", eyebrow) : null, h("h1", title), lead ? h("p.lead", lead) : null),
      actions ? h("div.row", actions) : null);
  }
  function section(title, content, more) {
    return h("section.stack", h("div.section-title", h("h2", title), more || null), content);
  }

  // ------------------------------------------------------------------ sheet (details; bottom sheet on phones)
  let lastFocus = null;
  function openSheet(title, content) {
    const sheet = ZS.$("#sheet");
    lastFocus = document.activeElement;
    ZS.clear(sheet);
    const close = h("button.icon-btn", { type: "button", "aria-label": "سد", onclick: closeSheet }, icon("x"));
    const card = h("div.sheet-card", { role: "dialog", "aria-modal": "true", "aria-label": title },
      h("div.sheet-head", h("h2", title), close), content);
    sheet.appendChild(card);
    sheet.hidden = false;
    sheet.onclick = (ev) => { if (ev.target === sheet) closeSheet(); };
    close.focus();
  }
  function closeSheet() {
    const sheet = ZS.$("#sheet");
    sheet.hidden = true;
    ZS.clear(sheet);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !ZS.$("#sheet").hidden) closeSheet(); });

  /** a term with an explanation from the glossary */
  function term(key, text) {
    const g = (ZS.D.meta && ZS.D.meta.glossary) || {};
    if (!g[key]) return h("span", text);
    return h("button.btn.ghost.small", { type: "button", style: { minHeight: "28px", padding: "0 6px", textDecoration: "underline dotted" },
      onclick: () => openSheet(text, h("p", g[key])) }, text);
  }

  function trackLabel(track) {
    const map = (ZS.D.meta && ZS.D.meta.tracks_ar) || {};
    return map[track] || track;
  }
  function trackTag(track) {
    const cls = track === "live" ? "led" : track === "scenario" ? "scenario" : "pitch";
    return h("span.tag." + cls, trackLabel(track));
  }

  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); ZS.toast("انسخ"); return true; }
    catch (e) { ZS.toast("ما گدرت أنسخ تلقائياً: ظلّلي النص وانسخيه"); return false; }
  }
  async function saveFile(filename, blob) {
    const dl = ZS.env.downloads;
    if (dl) {
      try { await dl.save({ filename, data: blob }); ZS.toast("انحفظ الملف"); return true; }
      catch (e) { if (e && e.code === "declined") return false; }
    }
    try {
      const url = URL.createObjectURL(blob);
      const a = h("a", { href: url, download: filename });
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      return true;
    } catch (e) { return false; }
  }

  ZS.ui = { icon, crest, teamInline, probBar, statusOf, pill, kickoffLabel, matchCard, errorCard, skeleton, empty, pageHead, section, openSheet, closeSheet, term, trackLabel, trackTag, copyText, saveFile };
})();
