/* core.js: shared helpers, data access, saved user data and routing. Plain script, no build step.
   Everything lives under window.ZS. */
(function () {
  "use strict";
  const ZS = (window.ZS = window.ZS || {});

  // ------------------------------------------------------------------ DOM helpers
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));
  /** h("div.card#x", {attrs}, ...children): tiny element builder. Strings become text nodes (never HTML). */
  function h(tag, attrs, ...kids) {
    const m = /^([a-z0-9]+)?((?:[.#][\w-]+)*)$/i.exec(tag);
    const el = document.createElement((m && m[1]) || "div");
    if (m && m[2]) {
      for (const part of m[2].match(/[.#][\w-]+/g)) {
        if (part[0] === ".") el.classList.add(part.slice(1));
        else el.id = part.slice(1);
      }
    }
    if (attrs !== null && attrs !== undefined && (typeof attrs !== "object" || attrs instanceof Node || Array.isArray(attrs))) {
      kids.unshift(attrs); // a first child that is a number (0 included), text, node or list
      attrs = null;
    }
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") el.className += (el.className ? " " : "") + v;
      else if (k === "style" && typeof v === "object") {
        for (const [sk, sv] of Object.entries(v)) {
          if (sk.startsWith("--")) el.style.setProperty(sk, sv); else el.style[sk] = sv;
        }
      }
      else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
      else if (k === "html") el.innerHTML = v; // only ever used with markup built here (SVG), never with data
      else if (k === "dataset") Object.assign(el.dataset, v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    append(el, kids);
    return el;
  }
  function append(el, kids) {
    for (const k of kids.flat(Infinity)) {
      if (k === null || k === undefined || k === false || k === "") continue;
      el.appendChild(k instanceof Node ? k : document.createTextNode(String(k)));
    }
    return el;
  }
  function svgEl(markup) {
    const t = document.createElement("template");
    t.innerHTML = markup.trim();
    return t.content.firstChild;
  }
  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ------------------------------------------------------------------ numbers and words
  const isNum = (x) => typeof x === "number" && isFinite(x);
  const PCT = "%";
  function pct(p, digits = 0) {
    if (!isNum(p)) return "—";
    const v = 100 * p;
    if (digits === 0 && v > 0 && v < 0.5) return "<1" + PCT;
    if (digits === 0 && v < 100 && v > 99.5) return ">99" + PCT;
    return v.toFixed(digits) + PCT;
  }
  function num(x, digits = 0) { return isNum(x) ? Number(x).toFixed(digits) : "—"; }
  function signed(x, digits = 0) {
    if (!isNum(x)) return "—";
    const r = Number(x).toFixed(digits);
    if (Number(r) === 0) return (0).toFixed(digits);
    return (x > 0 ? "+" : "−") + Math.abs(x).toFixed(digits);
  }
  /** change in percentage points, e.g. +4.2 */
  const pp = (d, digits = 1) => signed(100 * d, digits);
  /** Arabic counted noun: 1 -> one, 2 -> two, 3-10 -> "N few", 11+ -> "N many" */
  function countAr(n, one, two, few, many) {
    n = Math.round(n);
    if (n === 1) return one;
    if (n === 2) return two;
    if ((n >= 3 && n <= 10) || n === 0) return `${n} ${few}`;
    return `${n} ${many || one}`;
  }
  /** score text that reads correctly inside Arabic sentences: home goals sit next to the home team */
  const scoreText = (h, a) => `${h} – ${a}`;

  // ------------------------------------------------------------------ dates (Baghdad)
  const TZ = "Asia/Baghdad";
  const fmtCache = {};
  function fmt(opts) {
    const key = JSON.stringify(opts);
    if (!fmtCache[key]) {
      try { fmtCache[key] = new Intl.DateTimeFormat(ZS.lang === "en" ? "en-GB" : "ar-IQ-u-nu-latn", { timeZone: TZ, ...opts }); }
      catch (e) { fmtCache[key] = new Intl.DateTimeFormat("ar", { ...opts }); }
    }
    return fmtCache[key];
  }
  const toDate = (iso) => (iso instanceof Date ? iso : iso ? new Date(iso) : null);
  function dateLong(iso) { const d = toDate(iso); return d && !isNaN(d) ? fmt({ weekday: "long", day: "numeric", month: "long" }).format(d) : "—"; }
  function dateShort(iso) { const d = toDate(iso); return d && !isNaN(d) ? fmt({ day: "numeric", month: "short" }).format(d) : "—"; }
  function timeHM(iso) {
    const d = toDate(iso);
    if (!d || isNaN(d)) return "—";
    let h12 = false;
    try { h12 = ZS.store && ZS.store.prefs().clock === "12"; } catch (e) { /* prefs not ready */ }
    return fmt({ hour: h12 ? "numeric" : "2-digit", minute: "2-digit", hour12: h12 }).format(d);
  }
  function dateTime(iso) { const d = toDate(iso); return d && !isNaN(d) ? fmt({ day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: false }).format(d) : "—"; }
  function dayKey(iso) { // YYYY-MM-DD in Baghdad
    const d = toDate(iso); if (!d || isNaN(d)) return "";
    const p = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
    return p;
  }
  function enRel(s, suffix) {
    if (s < 60) return suffix ? "just now" : "under a minute";
    const m = Math.round(s / 60), hr = Math.round(s / 3600), dy = Math.round(s / 86400);
    if (s < 3600) return `${m} min${suffix}`;
    if (s < 86400) return `${hr} h${suffix}`;
    return `${dy} day${dy === 1 ? "" : "s"}${suffix}`;
  }
  function ago(iso, now) {
    const d = toDate(iso); if (!d || isNaN(d)) return "—";
    const s = Math.max(0, ((now || Date.now()) - d.getTime()) / 1000);
    if (ZS.lang === "en") return enRel(s, " ago");
    if (s < 60) return "قبل لحظات";
    const m = s / 60, hr = m / 60, dy = hr / 24;
    if (m < 60) return "قبل " + countAr(m, "دقيقة", "دقيقتين", "دقائق", "دقيقة");
    if (hr < 24) return "قبل " + countAr(hr, "ساعة", "ساعتين", "ساعات", "ساعة");
    return "قبل " + countAr(dy, "يوم", "يومين", "أيام", "يوم");
  }
  function until(iso, now) {
    const d = toDate(iso); if (!d || isNaN(d)) return "";
    const s = (d.getTime() - (now || Date.now())) / 1000;
    if (s <= 0) return "";
    if (ZS.lang === "en") return "in " + enRel(s, "");
    const m = s / 60, hr = m / 60, dy = hr / 24;
    if (m < 60) return "بعد " + countAr(Math.ceil(m), "دقيقة", "دقيقتين", "دقائق", "دقيقة");
    if (hr < 24) return "بعد " + countAr(Math.round(hr), "ساعة", "ساعتين", "ساعات", "ساعة");
    return "بعد " + countAr(Math.round(dy), "يوم", "يومين", "أيام", "يوم");
  }

  // ------------------------------------------------------------------ colours
  function hexRgb(hex) {
    const m = /^#?([0-9a-f]{6})$/i.exec(hex || "");
    if (!m) return [128, 128, 128];
    const n = parseInt(m[1], 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function lum(hex) {
    const c = hexRgb(hex).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  }
  const inkOn = (hex) => (lum(hex) > 0.42 ? "#0b0f0c" : "#ffffff");
  function colourDist(a, b) {
    const x = hexRgb(a), y = hexRgb(b);
    return Math.sqrt((x[0] - y[0]) ** 2 * 0.3 + (x[1] - y[1]) ** 2 * 0.59 + (x[2] - y[2]) ** 2 * 0.11);
  }
  /** colours for a home/away pair that stay apart from each other and from the draw grey */
  function pairColours(home, away) {
    const hc = home.color, ac0 = away.color;
    let ac = ac0;
    if (colourDist(hc, ac0) < 70) {
      const alt = (away.kit || []).find((k) => k && colourDist(k, hc) >= 70 && lum(k) < 0.85);
      ac = alt || (lum(hc) > 0.4 ? "#2a3b8f" : "#d9d9d9");
    }
    return [hc, ac];
  }

  // ------------------------------------------------------------------ data access
  const DATA_BASE = "data/";
  const cache = new Map();
  async function getJSON(path, { fresh = false, retries = 2 } = {}) {
    if (!fresh && cache.has(path)) return cache.get(path);
    const p = (async () => {
      let lastErr;
      for (let i = 0; i <= retries; i++) {
        try {
          const r = await fetch(DATA_BASE + path + (fresh ? (path.includes("?") ? "&" : "?") + "t=" + Date.now() : ""), { cache: fresh ? "no-store" : "default" });
          if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
          return await r.json();
        } catch (e) {
          lastErr = e;
          await new Promise((res) => setTimeout(res, 300 * (i + 1)));
        }
      }
      throw new Error(`تعذّر تحميل ${path}: ${lastErr && lastErr.message}`);
    })();
    cache.set(path, p);
    p.catch(() => cache.delete(path));
    return p;
  }
  function invalidate() { cache.clear(); }

  const D = {}; // loaded core files
  async function loadCore() {
    const [meta, teams, fixtures] = await Promise.all([getJSON("meta.json"), getJSON("teams.json"), getJSON("fixtures.json")]);
    D.meta = meta; D.teams = teams; D.fixtures = fixtures.fixtures;
    for (const f of D.fixtures) f.comp = "ESP1";
    D.fixturesById = new Map(D.fixtures.map((f) => [f.match_id, f]));
    D.keyToId = teams.key_to_id || {};
    // version 3: the Premier League and the Champions League (each in data/c/<id>/); La Liga stays at the root
    D.comps = [{ id: "ESP1", name_ar: "الدوري الإسباني", short_ar: "لاليغا", base: "", type: "league", color: "#E8572B" }];
    D.xteams = {}; D.xfixtures = {}; D.xfixturesById = new Map();
    try {
      const cj = await getJSON("comps.json");
      D.comps = cj.competitions;
      D.freeFiles = cj.free || [];
      await Promise.all(D.comps.filter((c) => c.base).map(async (c) => {
        const [t, fx] = await Promise.all([getJSON(c.base + "teams.json"), getJSON(c.base + "fixtures.json")]);
        for (const [id, tm] of Object.entries(t.teams)) if (!(D.teams.teams[id])) D.xteams[id] = tm;
        D.xfixtures[c.id] = fx.fixtures;
        for (const f of fx.fixtures) D.xfixturesById.set(f.match_id, f);
      }));
    } catch (e) { console.warn("competitions not loaded", e); }
    return D;
  }
  const team = (id) => {
    const t = (D.teams && D.teams.teams[id]) || (D.xteams && D.xteams[id]) || { id, ar: id, en: id, color: "#777777", kit: ["#777777", "#cccccc"] };
    if (!t.short) t.short = t.ar;
    // English interface: every page that prints a team name prints the English one
    if (ZS.lang === "en") return { ...t, ar: t.en || t.ar, short: t.short_en || t.en || t.short };
    return t;
  };
  const teamByKey = (key) => team(D.keyToId[key] || key);
  async function matchFile(mid) {
    const f = D.fixturesById && D.fixturesById.get(mid);
    if (!f) throw new Error("مباراة غير معروفة");
    const md = await getJSON(`matches/md${String(f.matchday).padStart(2, "0")}.json`);
    const m = md.matches[mid];
    if (!m) throw new Error("ملف المباراة غير موجود");
    return m;
  }

  // ------------------------------------------------------------------ environment
  const env = { mode: "local", db: null, user: null, uid: null, downloads: null, sample: null, server: false, artifact: false };
  async function detectEnv() {
    // 1. the local Python server (python -m zsc serve); a hosted one-page build has no server to ask
    if (window.ZS_BUILD !== "web") try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 1500);
      const r = await fetch("api/health", { signal: ctl.signal, cache: "no-store" });
      clearTimeout(t);
      if (r.ok) {
        const js = await r.json();
        if (js && js.mode === "server") { env.mode = "server"; env.server = true; }
      }
    } catch (e) { /* not served by the local server */ }
    // 2. a published Claude artifact: runtime capabilities light up later, never block the first paint
    if (window.claude && typeof window.claude.use === "function") {
      env.artifact = true;
      if (!env.server) env.mode = "artifact";
      const safeUse = (n) => window.claude.use(n).catch(() => null);
      safeUse("downloads").then((d) => { env.downloads = d; });
      safeUse("sample").then((s) => { env.sample = s; ZS.emit && ZS.emit("env"); });
      Promise.all([safeUse("db"), safeUse("user")]).then(async ([db, user]) => {
        env.user = user;
        if (db && user) {
          let uid = null;
          try { uid = await user.id(); } catch (e) { uid = null; }
          if (uid) { env.db = db; env.uid = uid; await store.syncFromDb(); }
        }
        ZS.emit && ZS.emit("env");
      });
    }
    return env;
  }

  // ------------------------------------------------------------------ saved user data
  const LS = "zsc.v2.";
  function lsGet(k, def) { try { const v = localStorage.getItem(LS + k); return v ? JSON.parse(v) : def; } catch (e) { return def; } }
  function lsSet(k, v) { try { localStorage.setItem(LS + k, JSON.stringify(v)); } catch (e) { /* storage blocked: keep in memory */ } }
  const DEFAULT_PREFS = {
    theme: "dark", track: "", fav_teams: [], fav_players: [], watchlist: [], filters: {},
    alerts: { forecast_change: true, reports: true, stories: true, threshold_pp: 5, frequency: "visit" },
    reduce_motion: false, player_name: "", seen: null,
    comp_order: ["ESP1", "ENG1", "UCL"], comp_hidden: [], fav_comps: ["ESP1"], font_size: "m", clock: "24", lang: "ar",
    collapsed: [],
  };
  const mem = { prefs: null, lists: {} };
  const LIST_NAMES = ["stories", "notes", "scripts"];
  const store = {
    prefs() {
      if (!mem.prefs) mem.prefs = { ...DEFAULT_PREFS, ...lsGet("prefs", {}) };
      mem.prefs.alerts = { ...DEFAULT_PREFS.alerts, ...(mem.prefs.alerts || {}) };
      return mem.prefs;
    },
    async setPrefs(patch) {
      const p = { ...store.prefs(), ...patch };
      mem.prefs = p;
      lsSet("prefs", p);
      // "seen" (what this viewer already looked at) stays in this browser; everything else is saved remotely too
      if (Object.keys(patch).some((k) => k !== "seen")) {
        const { seen, ...shared } = p;
        await store._push("prefs", shared);
      }
      ZS.emit("prefs");
      return p;
    },
    list(name) {
      if (!mem.lists[name]) mem.lists[name] = lsGet("list." + name, []);
      return mem.lists[name];
    },
    async saveList(name, items) {
      mem.lists[name] = items;
      lsSet("list." + name, items);
      await store._push(name, { items });
      ZS.emit("list:" + name);
    },
    where() {
      if (env.server) return "الخادم المحلي (data/userdata)";
      if (env.db) return "حسابك على Claude (محفوظ بهذا الرابط)";
      return "هذا المتصفح فقط";
    },
    async _push(name, body) {
      try {
        if (env.server) {
          await fetch(`api/user/${name}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
        } else if (env.db && env.uid) {
          await env.db.doc(`data/users/${env.uid}/${name}`).set(body);
        }
      } catch (e) { toast("ما انحفظ بالخادم، انحفظ بهذا المتصفح بس"); }
    },
    async syncFromServer() {
      try {
        const pr = await (await fetch("api/user/prefs", { cache: "no-store" })).json();
        if (pr && Object.keys(pr).length) { mem.prefs = { ...DEFAULT_PREFS, ...pr, seen: store.prefs().seen }; lsSet("prefs", mem.prefs); }
        for (const n of LIST_NAMES) {
          const js = await (await fetch(`api/user/${n}`, { cache: "no-store" })).json();
          if (js && Array.isArray(js.items)) { mem.lists[n] = js.items; lsSet("list." + n, js.items); }
        }
      } catch (e) { /* keep local copies */ }
    },
    async syncFromDb() {
      try {
        const pr = await env.db.doc(`data/users/${env.uid}/prefs`).get();
        if (pr.exists) { mem.prefs = { ...DEFAULT_PREFS, ...pr.data(), seen: store.prefs().seen }; lsSet("prefs", mem.prefs); }
        for (const n of LIST_NAMES) {
          const d = await env.db.doc(`data/users/${env.uid}/${n}`).get();
          if (d.exists && Array.isArray(d.data().items)) { mem.lists[n] = d.data().items; lsSet("list." + n, d.data().items); }
        }
        ZS.emit("prefs");
      } catch (e) { /* keep local copies */ }
    },
  };

  // ------------------------------------------------------------------ audience challenge
  const RULES_AR = [
    "التوقع ينقفل بصافرة البداية (حسب موعد المباراة الرسمي).",
    "النتيجة الصحيحة (فوز/تعادل/خسارة): نقطة وحدة.",
    "النتيجة الرقمية الصحيحة: نقطتين إضافيتين (المجموع 3).",
    "الترتيب الأسبوعي من الاثنين للأحد بتوقيت بغداد، والترتيب العام لكل الموسم.",
    "توقعات الجمهور منفصلة عن توقعات الحاسوب، والحاسوب يشارك بالترتيب كمتسابق باسم «الحاسوب».",
  ];
  const challenge = {
    rules: RULES_AR,
    where() {
      if (env.server) return { shared: true, text: "مشترك: كل من يفتح هذا الخادم يشوف نفس الترتيب" };
      if (env.db) return { shared: true, text: "مشترك بين اللي يگدرون يعدلون هالصفحة على Claude (المشاهدون يقرون بس)" };
      return { shared: false, text: "محلي: توقعاتك محفوظة بهذا المتصفح بس" };
    },
    /** all picks: [{player, player_id, match_id, pick, score, at}] */
    async picks() {
      if (env.server) {
        const js = await (await fetch("api/challenge", { cache: "no-store" })).json();
        return js.picks || [];
      }
      if (env.db) {
        const snap = await env.db.collection("picks").get();
        const out = [];
        const ids = snap.docs.map((d) => d.id);
        let names = {};
        try { names = env.user ? await env.user.profiles(ids) : {}; } catch (e) { names = {}; }
        for (const d of snap.docs) {
          const body = d.data() || {};
          for (const [mid, p] of Object.entries(body.picks || {})) {
            out.push({ player: (names[d.id] && names[d.id].name) || (d.id === env.uid ? "أنتِ" : "متسابق"), player_id: d.id, match_id: mid, ...p });
          }
        }
        return out;
      }
      return lsGet("challenge", []);
    },
    async submit(matchId, pick, score, player) {
      const f = D.fixturesById.get(matchId);
      if (!f || !f.kickoff_utc || new Date(f.kickoff_utc) <= new Date()) throw new Error("انقفل التوقع: المباراة بدأت");
      if (score) {
        const [a, b] = score.split("-").map(Number);
        const oc = a > b ? "H" : a === b ? "D" : "A";
        if (oc !== pick) throw new Error("النتيجة الرقمية ما تطابق اختيارك");
      }
      const at = new Date().toISOString().replace(/\.\d+Z$/, "Z");
      if (env.server) {
        const r = await fetch("api/challenge", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ player, match_id: matchId, pick, score: score || null }) });
        const js = await r.json();
        if (!r.ok) throw new Error(js.error || "ما انحفظ");
        return;
      }
      if (env.db) {
        const ref = env.db.doc(`picks/${env.uid}`);
        const cur = await ref.get();
        const body = cur.exists ? JSON.parse(JSON.stringify(cur.data())) : { picks: {} };
        body.picks = body.picks || {};
        body.picks[matchId] = { pick, score: score || null, at };
        await ref.set(body);
        return;
      }
      const all = lsGet("challenge", []).filter((x) => x.match_id !== matchId);
      all.push({ player: player || "أنا", match_id: matchId, pick, score: score || null, at });
      lsSet("challenge", all);
    },
    /** leaderboard computed in the page from the current results (the same rules everywhere) */
    board(picks) {
      const res = (f) => (f.score ? (f.score[0] > f.score[1] ? "H" : f.score[0] === f.score[1] ? "D" : "A") : null);
      const rows = {};
      const weekly = {};
      const add = (who, f, pick, score, at) => {
        if (!f || !f.score || !f.kickoff_utc) return;
        if (at && new Date(at) >= new Date(f.kickoff_utc)) return; // late picks never count
        const pts = (pick === res(f) ? 1 : 0) + (score === `${f.score[0]}-${f.score[1]}` ? 2 : 0);
        const r = (rows[who] = rows[who] || { player: who, points: 0, played: 0, exact: 0, right: 0 });
        r.points += pts; r.played += 1; r.exact += pts === 3 ? 1 : 0; r.right += pts >= 1 ? 1 : 0;
        const wk = isoWeek(f.kickoff_utc);
        const w = (weekly[wk] = weekly[wk] || {});
        w[who] = (w[who] || 0) + pts;
      };
      for (const p of picks) add(p.player, D.fixturesById.get(p.match_id), p.pick, p.score, p.at);
      // the computer: its most likely outcome and most likely score, issued before kick-off
      const pickedIds = new Set(picks.map((p) => p.match_id));
      for (const f of D.fixtures) {
        if (!f.score || !pickedIds.has(f.match_id) || !f.logged) continue;   // only forecasts logged before kick-off
        const p = f.logged.p;
        const i = p.indexOf(Math.max(...p));
        add("الحاسوب", f, ["H", "D", "A"][i], f.logged.score || null, f.logged.issued_at);
      }
      const total = Object.values(rows).sort((a, b) => b.points - a.points || b.exact - a.exact);
      const weeks = Object.keys(weekly).sort().reverse().map((wk) => ({ week: wk, rows: Object.entries(weekly[wk]).map(([player, points]) => ({ player, points })).sort((a, b) => b.points - a.points) }));
      return { total, weeks };
    },
  };
  function isoWeek(iso) {
    const key = dayKey(iso); // Baghdad calendar day
    const d = new Date(key + "T12:00:00Z");
    const day = (d.getUTCDay() + 6) % 7;
    d.setUTCDate(d.getUTCDate() - day + 3);
    const firstThu = new Date(Date.UTC(d.getUTCFullYear(), 0, 4));
    const wk = 1 + Math.round(((d - firstThu) / 86400000 - 3 + ((firstThu.getUTCDay() + 6) % 7)) / 7);
    return `${d.getUTCFullYear()}-W${String(wk).padStart(2, "0")}`;
  }

  // ------------------------------------------------------------------ events
  const listeners = {};
  ZS.on = (name, fn) => { (listeners[name] = listeners[name] || []).push(fn); return () => { listeners[name] = listeners[name].filter((f) => f !== fn); }; };
  ZS.emit = (name, arg) => { for (const fn of listeners[name] || []) { try { fn(arg); } catch (e) { console.error(e); } } };

  // ------------------------------------------------------------------ toasts
  function toast(text, ms = 3200) {
    const box = $("#toasts");
    if (!box) return;
    const t = h("div.toast", { role: "status" }, text);
    box.appendChild(t);
    setTimeout(() => t.remove(), ms);
  }

  // ------------------------------------------------------------------ routing
  // routes are plain tokens so a link to one view survives in the artifact viewer: #today, #match-ESP1-2026-ATM-DEP
  const routes = {};
  let current = { page: "", params: {} };
  let cleanup = null;
  function parseHash(hash) {
    const raw = (hash || "").replace(/^#/, "");
    const home = routes.matches ? "matches" : "today";
    if (!raw) return { page: home, params: {} };
    const m = /^([a-z]+)(?:-(.+))?$/.exec(raw);
    if (!m || !routes[m[1]]) return { page: home, params: {} };
    return { page: m[1], params: m[2] ? { id: m[2] } : {} };
  }
  function href(page, id) { return "#" + page + (id ? "-" + id : ""); }
  function go(page, id, { replace = false } = {}) {
    const target = href(page, id);
    if (location.hash === target) { render(); return; }
    try {
      if (replace) history.replaceState(null, "", target);
      else location.hash = target;
    } catch (e) { /* sandboxed: render anyway */ }
    if (replace || location.hash !== target) render(target);
  }
  async function render(hashOverride) {
    const r = parseHash(hashOverride || location.hash);
    current = r;
    if (cleanup) { try { cleanup(); } catch (e) { /* ignore */ } cleanup = null; }
    const view = $("#view");
    clear(view);
    ZS.emit("route", r);
    const page = routes[r.page];
    try {
      const res = await page.render(view, r.params);
      if (typeof res === "function") cleanup = res;
    } catch (e) {
      console.error(e);
      clear(view);
      view.appendChild(ZS.ui.errorCard(e, () => render()));
    }
    if (!hashOverride || hashOverride === location.hash) {
      const main = $("#main");
      if (main && document.activeElement && document.activeElement.closest && document.activeElement.closest(".nav-item")) main.focus({ preventScroll: true });
      window.scrollTo({ top: 0 });
    }
  }
  window.addEventListener("hashchange", () => render());

  Object.assign(ZS, {
    $, $$, h, append, svgEl, clear, esc, isNum, pct, num, signed, pp, countAr, scoreText, PCT,
    dateLong, dateShort, timeHM, dateTime, dayKey, ago, until, isoWeek,
    hexRgb, lum, inkOn, colourDist, pairColours,
    getJSON, invalidate, loadCore, D, team, teamByKey, matchFile,
    env, detectEnv, store, challenge, toast, routes, go, href, render, current: () => current,
  });
})();
