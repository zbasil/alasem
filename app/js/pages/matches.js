/* Matches: every fixture of the season by matchday, with results, forecasts and the retro check. */
(function () {
  "use strict";
  const ZS = window.ZS;
  const { h, pct, team, D } = ZS;
  const ui = () => ZS.ui;

  function currentMatchday(now = Date.now()) {
    const next = D.fixtures.filter((f) => !f.score && f.kickoff_utc && new Date(f.kickoff_utc).getTime() > now - 3 * 3600e3)
      .sort((a, b) => a.kickoff_utc.localeCompare(b.kickoff_utc))[0];
    if (next) return next.matchday;
    const last = D.fixtures.filter((f) => f.score).sort((a, b) => b.matchday - a.matchday)[0];
    return last ? last.matchday : 1;
  }

  const FILTERS = [
    ["all", "الكل"], ["fav", "فرقي"], ["watch", "المتابَعة"], ["played", "انتهت"], ["upcoming", "قادمة"],
  ];

  async function render(view, params) {
    const prefs = ZS.store.prefs();
    const saved = (prefs.filters && prefs.filters.matches) || {};
    let md = params.id && /^md\d+$/.test(params.id) ? Number(params.id.slice(2)) : currentMatchday();
    let filter = saved.filter || "all";
    const maxMd = Math.max(...D.fixtures.map((f) => f.matchday));

    const mdSelect = h("select#md-select", { "aria-label": "اختاري الجولة", style: { width: "auto", minWidth: "140px" } },
      Array.from({ length: maxMd }, (_, i) => h("option", { value: i + 1, selected: i + 1 === md }, `الجولة ${i + 1}`)));
    const prevBtn = h("button.icon-btn", { type: "button", "aria-label": "الجولة السابقة" }, ui().icon("back"));
    const nextBtn = h("button.icon-btn", { type: "button", "aria-label": "الجولة التالية", style: { transform: "scaleX(-1)" } }, ui().icon("back"));
    view.appendChild(ui().pageHead("المباريات", "كل مباريات الموسم بتوقيت بغداد. المباريات اللي انتهت تبيّن التوقع الاسترجاعي: نفس الموديل وبيانات ما قبل الأسبوع بس.",
      h("div.row", prevBtn, mdSelect, nextBtn), `${D.meta.competition.name_ar} ${D.meta.competition.season_label}`));
    const chips = h("div.chips.scroll", { role: "toolbar", "aria-label": "تصفية" });
    view.appendChild(chips);
    const body = h("div.stack-lg");
    view.appendChild(body);

    function draw() {
      ZS.clear(chips);
      for (const [k, lab] of FILTERS) {
        chips.appendChild(h("button.chip", { type: "button", "aria-pressed": String(filter === k), onclick: () => { filter = k; persist(); draw(); } }, lab));
      }
      ZS.clear(body);
      mdSelect.value = String(md);
      prevBtn.disabled = md <= 1; nextBtn.disabled = md >= maxMd;
      const p = ZS.store.prefs();
      let list = D.fixtures.filter((f) => f.matchday === md);
      if (filter === "fav") list = D.fixtures.filter((f) => p.fav_teams.includes(f.home) || p.fav_teams.includes(f.away));
      if (filter === "watch") list = D.fixtures.filter((f) => p.watchlist.includes(f.match_id));
      if (filter === "played") list = list.filter((f) => f.score);
      if (filter === "upcoming") list = list.filter((f) => !f.score);
      if ((filter === "fav" && !p.fav_teams.length)) { body.appendChild(ui().empty("ما اخترتي فرق مفضلة بعد. اختاريها من صفحة أي فريق أو من الإعدادات.")); return; }
      if ((filter === "watch" && !p.watchlist.length)) { body.appendChild(ui().empty("ماكو مباريات متابَعة. اضغطي «تابعي» بمركز أي مباراة.")); return; }
      if (!list.length) { body.appendChild(ui().empty("ماكو مباريات بهالتصفية")); return; }
      if (filter === "fav" || filter === "watch") body.appendChild(h("p.small.muted", "تشمل كل الجولات"));
      // summary of the matchday: retro accuracy of the displayed track
      const played = list.filter((f) => f.score && f.retro_hit !== undefined);
      if (filter !== "fav" && filter !== "watch" && played.length >= 3) {
        const hits = played.filter((f) => f.retro_hit).length;
        body.appendChild(h("div.notice.pitch", ui().icon("check"), h("span", `بهالجولة صار الاحتمال الأرجح بـ${hits} من ${played.length} مباريات (توقع استرجاعي بنفس الموديل).`)));
      }
      const groups = new Map();
      for (const f of list.slice().sort((a, b) => (a.kickoff_utc || a.kickoff_baghdad.date || "").localeCompare(b.kickoff_utc || b.kickoff_baghdad.date || ""))) {
        const key = f.kickoff_utc ? ZS.dayKey(f.kickoff_utc) : (f.kickoff_baghdad.date || "غير محدد");
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(f);
      }
      for (const [day, fs] of groups) {
        const title = fs[0].kickoff_utc ? ZS.dateLong(fs[0].kickoff_utc) : (day !== "غير محدد" ? `${ZS.dateLong(day + "T12:00:00Z")} (الوقت غير محدد بعد)` : "الموعد غير محدد");
        const g = h("div.grid.g-auto");
        for (const f of fs) g.appendChild(ui().matchCard(f, { prev: f.prev_p || null }));
        body.appendChild(ui().section(title, g));
      }
    }
    function persist() {
      const p = ZS.store.prefs();
      ZS.store.setPrefs({ filters: { ...(p.filters || {}), matches: { filter } } });
    }
    mdSelect.addEventListener("change", () => { md = Number(mdSelect.value); ZS.go("matches", "md" + md, { replace: true }); });
    prevBtn.addEventListener("click", () => { if (md > 1) { md -= 1; ZS.go("matches", "md" + md, { replace: true }); } });
    nextBtn.addEventListener("click", () => { if (md < maxMd) { md += 1; ZS.go("matches", "md" + md, { replace: true }); } });
    draw();
  }

  ZS.routes.matches = { render, title: "المباريات", currentMatchday };
})();
