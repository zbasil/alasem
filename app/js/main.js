/* main.js: start-up, navigation, theme, data status, alerts. */
(function () {
  "use strict";
  const ZS = window.ZS;
  const { h, $, D } = ZS;
  const ui = () => ZS.ui;

  const NAV = [["matches", "المباريات"], ["news", "الأخبار"], ["comps", "البطولات"], ["standings", "الترتيب"], ["more", "المزيد"]];
  const MORE = [["studio", "الاستوديو"], ["lab", "مختبر التحقق"], ["today", "ملخص اليوم (لاليغا)"], ["season", "موسم الليغا"], ["teams", "فرق الليغا"], ["method", "المنهجية والدقة"], ["data", "البيانات والمصادر"], ["challenge", "تحدي الجمهور"], ["archive", "أرشيف التحليل العميق"], ["players", "اللاعبين (أرشيف)"], ["prefs", "الإعدادات"]];
  const SECTION_OF = { lab: "more", match: "matches", xmatch: "matches", round: "matches", team: "comps", xteam: "comps", comp: "comps", archive: "more", challenge: "more", alerts: "more", players: "more", today: "more", season: "comps", teams: "comps", studio: "more", method: "more", data: "more", prefs: "more" };
  const NAV_ICON = { matches: "matches", news: "news", comps: "comps", standings: "standings", more: "more" };

  function applyTheme() {
    const p = ZS.store.prefs();
    const root = document.documentElement;
    if (p.theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", p.theme || "dark");
    root.classList.toggle("reduce-motion", !!p.reduce_motion);
    root.setAttribute("data-fs", p.font_size || "m");
  }
  ZS.applyTheme = applyTheme;

  function buildNav() {
    const main = $(".nav-main"), more = $(".nav-more"), bottom = $(".bottom-nav"), top = $("#topbar-actions");
    for (const [k, lab] of NAV) {
      if (k !== "more") main.appendChild(h("a.nav-item", { href: ZS.href(k), "data-nav": k }, ui().icon(NAV_ICON[k]), h("span", lab)));
      bottom.appendChild(h("a.nav-item", { href: ZS.href(k), "data-nav": k }, ui().icon(NAV_ICON[k]), h("span", lab)));
    }
    main.appendChild(h("a.nav-item", { href: ZS.href("more"), "data-nav": "more" }, ui().icon("more"), h("span", "المزيد")));
    for (const [k, lab] of MORE) more.appendChild(h("a.nav-item", { href: ZS.href(k), "data-nav": k }, ui().icon(k === "archive" ? "matches" : k === "prefs" ? "settings" : k === "players" ? "teams" : k), h("span", lab)));
    const bell = () => h("a.icon-btn.bell", { href: ZS.href("alerts"), "aria-label": "التنبيهات" }, ui().icon("bell"));
    more.prepend(h("a.nav-item", { href: ZS.href("alerts"), "data-nav": "alerts" }, ui().icon("bell"), h("span", "التنبيهات"), h("span.tag.led.alert-count", { hidden: true }, "")));
    top.append(bell(),
      h("a.icon-btn", { href: ZS.href("method"), "aria-label": "المنهجية والدقة" }, ui().icon("method")),
      h("button.icon-btn", { type: "button", "aria-label": "المزيد", onclick: moreSheet }, ui().icon("settings")));
  }
  function moreSheet() {
    ui().openSheet("المزيد", h("div.stack", MORE.map(([k, lab]) => h("a.nav-item", { href: ZS.href(k), onclick: () => ui().closeSheet() }, ui().icon(k === "archive" ? "matches" : k === "prefs" ? "settings" : k === "players" ? "teams" : k), h("span", lab))),
      h("hr.sep"), sideStatus(true)));
  }
  function markNav(r) {
    const key = SECTION_OF[r.page] || r.page;
    ZS.$$("[data-nav]").forEach((a) => {
      if (a.classList.contains("brand")) return;
      if (a.dataset.nav === key) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
    const t = ZS.routes[r.page] && ZS.routes[r.page].title;
    document.title = (t ? t + " · " : "") + "حاسوب زهراء الكروي";
  }

  function sideStatus(inSheet) {
    const m = D.meta;
    const hours = (Date.now() - new Date(m.generated_utc).getTime()) / 3600e3;
    const ok = (m.data_status || {}).last_build_ok !== false;
    const dot = (col) => h("i", { style: { width: "9px", height: "9px", borderRadius: "50%", background: col, display: "inline-block", flex: "0 0 9px" } });
    const mode = { server: "خادم محلي", artifact: "رابط Claude", local: "معاينة بالمتصفح" }[ZS.env.mode];
    return h("div.stack", { style: { gap: "6px" } },
      h("div.status-line", dot(hours > 36 || !ok ? "var(--led)" : "var(--good)"), h("span", `آخر تحديث ${ZS.ago(m.generated_utc)}`)),
      h("div.status-line.tiny", `البيانات ${m.versions.data} · ${m.versions.prematch_market}`),
      h("div.status-line.tiny", `الوضع: ${mode}`),
      inSheet ? null : h("a.tiny", { href: ZS.href("data") }, "حالة البيانات والمصادر ←"));
  }
  function drawStatus() {
    const box = $("#side-status");
    ZS.clear(box).appendChild(sideStatus(false));
    const foot = $("#foot");
    ZS.clear(foot).append(
      h("span", `${D.meta.platform.name} ${D.meta.platform.version}`),
      h("span", `تحديث ${ZS.dateTime(D.meta.generated_utc)} بتوقيت بغداد`),
      h("span", "مصادر مجانية: openfootball · football-data.co.uk (عبر GitHub) · ClubElo (عبر xgabora) · SportRadar عبر Claude · StatsBomb Open Data"),
      h("a", { href: ZS.href("method") }, "كيف نقيس الدقة"));
  }
  function drawBanner() {
    const b = $("#banner");
    ZS.clear(b);
    const m = D.meta;
    const hours = (Date.now() - new Date(m.generated_utc).getTime()) / 3600e3;
    const ds = m.data_status || {};
    if (ds.last_build_ok === false) b.appendChild(h("div.notice.bad", ui().icon("warn"), h("span", "آخر تحديث للبيانات فشل؛ التطبيق يعرض آخر نسخة سليمة. التفاصيل بصفحة البيانات.")));
    else if (hours > 36) b.appendChild(h("div.notice.led", ui().icon("warn"), h("span", `البيانات عمرها ${Math.round(hours)} ساعة: النتائج الجديدة ممكن ما تكون داخلة بعد.`)));
  }
  function drawAlertDot() {
    const n = ZS.alerts ? ZS.alerts.compute().length : 0;
    ZS.$$(".bell").forEach((b) => { const d = b.querySelector(".dot"); if (n && !d) b.appendChild(h("span.dot")); if (!n && d) d.remove(); });
    ZS.$$(".alert-count").forEach((c) => { c.hidden = !n; c.textContent = String(n); });
  }

  async function boot() {
    document.documentElement.setAttribute("lang", "ar");
    document.documentElement.setAttribute("dir", "rtl");
    applyTheme();
    buildNav();
    ZS.on("route", (r) => { markNav(r); });
    ZS.on("prefs", () => { applyTheme(); drawAlertDot(); });
    ZS.on("alerts", drawAlertDot);
    await ZS.detectEnv();
    if (ZS.env.server) await ZS.store.syncFromServer();
    applyTheme();
    try {
      await ZS.loadCore();
    } catch (e) {
      const view = $("#view");
      ZS.clear(view).appendChild(ui().errorCard(e, () => location.reload()));
      return;
    }
    ZS.emit("core");
    drawStatus();
    drawBanner();
    if (ZS.live) ZS.live.refresh();
    // first visit: remember what was seen so the next visit can show what changed
    if (!ZS.store.prefs().seen) await ZS.alerts.markSeen();
    drawAlertDot();
    await ZS.render();
    // a newer snapshot appears (server mode or a republished artifact): reload the data quietly
    setInterval(async () => {
      try {
        const m = await ZS.getJSON("meta.json", { fresh: true });
        if (m.generated_utc !== D.meta.generated_utc) {
          ZS.invalidate();
          await ZS.loadCore();
          ZS.emit("core");
          drawStatus(); drawBanner(); drawAlertDot();
          ZS.toast("وصل تحديث جديد للبيانات");
          if (["today", "matches", "match", "season", "news", "standings", "comp"].includes(ZS.current().page)) ZS.render();
        }
      } catch (e) { /* offline: keep the last data */ }
      const fr = ZS.store.prefs().alerts.frequency;
      if (fr === "hourly") drawAlertDot();
    }, 5 * 60 * 1000);
  }
  // installable app and offline copy: only on a real web host or the local server (not inside a Claude artifact)
  function registerSW() {
    if (!("serviceWorker" in navigator) || !/^https?:$/.test(location.protocol) || (window.claude && window.claude.use)) return;
    navigator.serviceWorker.register("sw.js").catch(() => { /* not allowed here: the app works without it */ });
  }
  window.addEventListener("load", registerSW);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
