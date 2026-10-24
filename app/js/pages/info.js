/* Methodology and accuracy, data and sources (with what needs activating), settings, alerts. */
(function () {
  "use strict";
  const ZS = window.ZS;
  const { h, pct, num, team, D } = ZS;
  const ui = () => ZS.ui;
  const C = () => ZS.charts;

  const SRC_AR = { market: "حاسوب زهراء (مدعوم بالسوق)", independent: "حاسوب زهراء (مستقل)", bet365: "أسعار Bet365", base_rates: "نسب الفوز التاريخية", always_home: "دائماً صاحب الأرض", most_common_score: "أشيع نتيجة بالدوري" };
  const n3 = (x) => num(x, 3);

  function ciText(c, digits = 4, scale = 1) {
    if (!c) return "—";
    return `${ZS.signed(c.diff * scale, digits)} [${num(c.ci_low * scale, digits)}، ${num(c.ci_high * scale, digits)}]`;
  }
  function clearTag(c, lowerBetter = true) {
    if (!c) return null;
    if (!c.clear) return h("span.tag", "فرق غير واضح");
    const better = lowerBetter ? c.diff < 0 : c.diff > 0;
    return h("span.tag." + (better ? "pitch" : "bad"), better ? "أحسن بوضوح" : "أسوأ بوضوح");
  }

  // ================================================================== methodology and accuracy
  async function renderMethod(view) {
    const a = await ZS.getJSON("accuracy.json");
    const t = a.prematch.test, sel = a.prematch.selection;
    const reg = a.registry;
    const disp = reg.displayed_track;
    const g = (D.meta && D.meta.glossary) || {};
    view.appendChild(ui().pageHead("المنهجية والدقة", "كل رقم هنا جاي من تقرير التقييم المحفوظ مع إصدار الموديل وفترة الاختبار، مو مكتوب باليد. الاختبار على مواسم ما شافها الموديل وقت اختيار الإعدادات.", null,
      `تقرير ${ZS.dateTime(a.generated_utc)} · ${reg.prematch_market.version} · ${reg.prematch_independent.version} · ${reg.inplay.version}`));

    // ---- headline
    const s = t.scores;
    view.appendChild(ui().section("الخلاصة", h("div.card.stack",
      h("div.kpis",
        h("div.kpi", h("span.k-val.num", pct(s[disp].hit, 1)), h("span.k-lab", "اختيار النتيجة الصحيحة (فوز/تعادل/خسارة)"), h("span.k-sub", `${t.n} مباراة · ${t.seasons}`)),
        h("div.kpi", h("span.k-val.num", pct(s.bet365.hit, 1)), h("span.k-lab", "Bet365 بنفس المباريات"), h("span.k-sub", "السوق يعرف التشكيلات والإصابات")),
        h("div.kpi", h("span.k-val.num", pct(s.always_home.hit, 1)), h("span.k-lab", "لو دائماً نختار صاحب الأرض")),
        h("div.kpi", h("span.k-val.num", pct(t.exact_scores[disp].exact_hit, 1)), h("span.k-lab", "إصابة النتيجة بالأرقام"), h("span.k-sub", `أشيع نتيجة دائماً: ${pct(t.exact_scores.most_common_score.exact_hit, 1)}`))),
      h("p", "يعني: الحاسوب يختار الاحتمال الأرجح صح بأكثر من نص المباريات بقليل، أقل من السوق بشوية، وأحسن بوضوح من الطرق البسيطة. توقع النتيجة بالأرقام أصعب بكثير من توقع الفائز."),
      h("div.notice", ui().icon("info"), h("span", "ماكو هدف دقة تسويقي (مثل «90٪»): كرة القدم بيها صدفة كبيرة، وحتى السوق يختار صح بحدود 55٪. أي تحسين ينضاف بس إذا الاختبار أثبته.")))));

    // ---- table of scores
    const rows = ["market", "independent", "bet365", "base_rates"].map((k) => [k, s[k]]);
    view.appendChild(ui().section("كل المقاييس (فترة الاختبار)", h("div.stack",
      h("div.tbl-wrap", h("table.tbl",
        h("thead", h("tr", h("th", "المصدر"), h("th.n", "اختيار صحيح"), h("th.n", "RPS"), h("th.n", "Log loss"), h("th.n", "Brier"))),
        h("tbody", rows.map(([k, v]) => h("tr" + (k === disp ? ".mine" : ""), h("td", SRC_AR[k]), h("td.n", pct(v.hit, 1)), h("td.n", n3(v.rps)), h("td.n", n3(v.logloss)), h("td.n", n3(v.brier))))))),
      h("div.grid.g-2", ["rps", "logloss", "brier", "hit"].map((k) => h("div.panel.small", (a.explain && a.explain[k]) || g[k] || ""))),
      h("p.small.faint", `فترة الاختيار (لضبط الإعدادات): ${sel.seasons}، ${sel.n} مباراة. فترة الاختبار النهائي: ${t.seasons}. التدريب أسبوع بأسبوع ببيانات ما قبل كل أسبوع فقط (walk-forward).`))));

    // ---- comparisons
    view.appendChild(ui().section("الفروق ومدى وضوحها", h("div.stack",
      h("div.tbl-wrap", h("table.tbl",
        h("thead", h("tr", h("th", "المقارنة"), h("th", "فرق RPS [مجال الثقة 95٪]"), h("th", "الحكم"), h("th", "فرق الاختيار الصحيح"))),
        h("tbody", t.comparisons.map((c) => h("tr", h("td", `${SRC_AR[c.a]} مقابل ${SRC_AR[c.b]}`), h("td.num", ciText(c.rps)), h("td", clearTag(c.rps)), h("td.num", ciText(c.hit, 1, 100) + " ن.م")))))),
      h("p.small.faint", `المجال من إعادة سحب المباريات نفسها (paired bootstrap) على ${t.n} مباراة. «غير واضح» = الفرق ممكن يكون صدفة.`))));

    // ---- calibration
    const cal = h("div.grid.g-3");
    for (const k of ["market", "independent", "bet365"]) {
      if (!t.calibration[k]) continue;
      cal.appendChild(h("div.card.tight", h("h3", SRC_AR[k]), C().calibration(t.calibration[k], { color: k === "bet365" ? "var(--fg-3)" : "var(--pitch)", label: `معايرة ${SRC_AR[k]}` }),
        h("p.small.muted", `متوسط خطأ المعايرة: ${pct(t.calibration_error[k], 1)}`)));
    }
    view.appendChild(ui().section("المعايرة: لما يگول 70٪، يصير 70٪؟", h("div.stack", cal,
      h("p.small.faint", "كل نقطة = مجموعة احتمالات متقاربة؛ الخط العمودي = مجال الثقة لللي صار فعلاً. النقاط القريبة من الخط القطري = معايرة جيدة."))));

    // ---- share of bet365 gain (moved here, renamed)
    view.appendChild(ui().section("كم من تفوق السوق يحققه الحاسوب؟", h("div.card.stack",
      h("div.kpis",
        h("div.kpi", h("span.k-val.num", pct(t.share_of_bet365_gain_market, 0)), h("span.k-lab", "المسار المدعوم بالسوق")),
        h("div.kpi", h("span.k-val.num", pct(t.share_of_bet365_gain_independent, 0)), h("span.k-lab", "المسار المستقل"))),
      h("p", `هذا مو نسبة دقة. هو كم من تحسّن Bet365 على نسب الفوز التاريخية (بمقياس RPS) يحققه الحاسوب: RPS نسب الفوز ${n3(s.base_rates.rps)}، Bet365 ${n3(s.bet365.rps)}، والحاسوب ${n3(s[disp].rps)}.`),
      h("p.small.faint", "الرقم القديم بالواجهة السابقة (حوالي 91٪) كان هذا المقياس نفسه، بس كان مكتوب وكأنه دقة. صححناه."))));

    // ---- value of each input
    const ab = a.ablations || {};
    if (ab.value_of_each_input) {
      view.appendChild(ui().section("شنو قيمة كل مُدخل؟", h("div.stack",
        h("div.tbl-wrap", h("table.tbl",
          h("thead", h("tr", h("th", "المُدخل"), h("th", "مقارنة"), h("th", "فرق RPS [95٪]"), h("th", "الحكم"))),
          h("tbody", ab.value_of_each_input.map((v) => h("tr", h("td", inputAr(v.input)), h("td.small", `${v.a} مقابل ${v.b}`), h("td.num", ciText(v.rps)), h("td", clearTag(v.rps))))))),
        h("p.small.faint", `على فترة الاختيار (${ab.seasons}). كل سطر يضيف مُدخل واحد ويقيس الفرق على نفس المباريات. أيام الراحة انجربت ورُفضت: ما حسّنت الاختبار.`))));
    }

    // ---- in play
    const ip = a.inplay && a.inplay[disp];
    if (ip) {
      const ts = ip.test_scores || {};
      view.appendChild(ui().section("التوقع المباشر (من نهاية الشوط الأول)", h("div.card.stack",
        h("div.kpis",
          h("div.kpi", h("span.k-val.num", n3((ts[ip.chosen] || {}).rps)), h("span.k-lab", "RPS بنهاية الشوط الأول"), h("span.k-sub", `قبل المباراة ${n3((ts["pre-match only"] || {}).rps)}`)),
          h("div.kpi", h("span.k-val.num", pct((ts[ip.chosen] || {}).hit, 1)), h("span.k-lab", "اختيار صحيح من الاستراحة"))),
        h("p", `النسخة المختارة: «${variantAr(ip.chosen)}». بشرط إن الدقيقة 0 تساوي توقع ما قبل المباراة بالضبط؛ كلفة هذا الشرط بفترة الاختيار: RPS ${ciText(ip.cost_of_constraint_selection && ip.cost_of_constraint_selection.rps, 4)} (صغيرة جداً).`),
        h("p.small.faint", `اختيار ${ip.selection_seasons}، اختبار ${ip.test_seasons}، وبنفس مدخلات التطبيق (توقعات كل مسار). الطرد: الفريق الناقص يسجل ×${num(a.statsbomb.red_own, 2)} والخصم ×${num(a.statsbomb.red_opp, 2)} (من ${a.statsbomb.red_matches} مباراة بيها طرد، StatsBomb).`))));
    }

    // ---- first-half signal test
    const sig = a.inplay_signal;
    if (sig) {
      view.appendChild(ui().section("هل الشوط الأول يضيف معلومة؟", h("div.card.stack",
        h("p", `جربنا نضيف للتوقع المباشر شي من مجريات الشوط الأول (xG والتسديدات على المرمى) فوق النتيجة نفسها، على ${sig.n} مباراة (الليغا 2015/16، الموسم الوحيد الكامل ببيانات أحداث)، بتقييم خارج العينة.`),
        h("div.tbl-wrap", h("table.tbl", h("thead", h("tr", h("th", "الإشارة"), h("th.n", "RPS"), h("th", "الفرق عن الموديل الحالي [95٪]"), h("th", "الحكم"))),
          h("tbody", h("tr", h("td", "الموديل الحالي (النتيجة والوقت بس)"), h("td.n", n3(sig.baseline_rps)), h("td", "—"), h("td", "—")),
            Object.entries(sig.signals).map(([k, v]) => h("tr", h("td", k === "xg" ? "+ xG الشوط الأول" : "+ التسديدات على المرمى"), h("td.n", n3(v.rps)), h("td.num", ciText(v.vs_baseline)), h("td", clearTag(v.vs_baseline))))))),
        h("p.small", { style: { fontWeight: 700 } }, sig.decision_ar),
        h("p.small.faint", "النتيجة اللي صارت تنحسب مرة وحدة بس (ما تنعاد كإشارة): الإشارة هي أداء الفريق مقارنة بالمتوقع منه بالشوط الأول."))));
    }
    // ---- rating fairness
    const rf = a.rating_fairness;
    if (rf) {
      view.appendChild(ui().section("عدالة تقييم اللاعبين بين المراكز", h("div.card.stack",
        h("p", `على ${rf.player_matches_60min} مشاركة (60 دقيقة أو أكثر) بموسم الليغا 2015/16: الصيغة القديمة كانت تعطي المهاجمين وصناع اللعب تقييمات أعلى بكثير من المدافعين والحراس. الصيغة الجديدة تقارن كل لاعب بلاعبي مركزه.`),
        h("div.tbl-wrap", h("table.tbl", h("thead", h("tr", h("th", "المركز"), h("th.n", "متوسط القديم"), h("th.n", "متوسط الجديد"), h("th.n", "حصته من أعلى 200 (قديم)"), h("th.n", "حصته من أعلى 200 (جديد)"), h("th.n", "حصته من كل المشاركات"))),
          h("tbody", rf.mean_rating_by_group.map((r) => h("tr", h("td", ({ GK: "حارس", CB: "قلب دفاع", FB: "ظهير", DM: "وسط دفاعي", CM: "وسط", AM: "صانع لعب / جناح", FW: "مهاجم" })[r.group] || r.group),
            h("td.n", num(r.rating_v1, 2)), h("td.n", num(r.rating_v2, 2)),
            h("td.n", pct(rf.share_of_top200_match_ratings.v1[r.group] || 0)), h("td.n", pct(rf.share_of_top200_match_ratings.v2[r.group] || 0)),
            h("td.n", pct(rf.share_of_top200_match_ratings.share_of_all_player_matches[r.group] || 0))))))),
        h("p.small.faint", "تقييم المشروع منفصل عن أي تقييم مزوّد (بيانات StatsBomb المفتوحة ما بيها تقييمات)."))));
    }

    // ---- season
    const se = a.season && a.season.test;
    if (se) {
      view.appendChild(ui().section("توقع نهاية الموسم", h("div.card.stack",
        h("div.kpis",
          h("div.kpi", h("span.k-val.num", num(se.points_MAE, 1)), h("span.k-lab", "متوسط خطأ النقاط النهائية"), h("span.k-sub", `الطريقة البسيطة ${num(se.naive_points_MAE, 1)}`)),
          h("div.kpi", h("span.k-val.num", pct(se.coverage_80)), h("span.k-lab", "النقاط داخل «المدى» (الهدف 80٪)")),
          h("div.kpi", h("span.k-val.num", n3(se.brier_title)), h("span.k-lab", "Brier اللقب"), h("span.k-sub", `بدون معلومات ${n3(se.brier_title_structural_base)}`)),
          h("div.kpi", h("span.k-val.num", n3(se.brier_releg)), h("span.k-lab", "Brier الهبوط"), h("span.k-sub", `بدون معلومات ${n3(se.brier_releg_structural_base)}`))),
        h("p.small.faint", `من نقطة بعد ${a.season.cut_after_matches} مباراة بكل موسم؛ إعداد «تغيّر المستوى خلال الموسم» (${a.registry.season.drift_sd}) انختار على ${a.season.selection_seasons} وانختبر على ${a.season.test_seasons} (${se.teams} فريق).`))));
    }

    // ---- breakdowns
    const bd = a.breakdowns || {};
    const bdTable = (rowsB, labKey) => h("div.tbl-wrap", h("table.tbl",
      h("thead", h("tr", h("th", ""), h("th.n", "مباريات"), h("th.n", "الحاسوب RPS"), h("th.n", "اختيار صحيح"), h("th.n", "Bet365 RPS"))),
      h("tbody", rowsB.map((r) => h("tr", h("td", groupAr(r[labKey] || r.group)), h("td.n", String(r.n)), h("td.n", n3(r[disp + "_rps"])), h("td.n", ZS.isNum(r[disp + "_hit"]) ? pct(r[disp + "_hit"], 1) : "—"), h("td.n", ZS.isNum(r.bet365_rps) ? n3(r.bet365_rps) : "—"))))));
    const bdBox = h("div.grid.g-2");
    for (const [k, lab] of [["season", "حسب الموسم"], ["phase", "حسب وقت الموسم"], ["favourite", "حسب قوة المرشح"], ["data", "حسب توفر البيانات"]]) if (bd[k]) bdBox.appendChild(h("div.card.tight", h("h3", lab), bdTable(bd[k], "group")));
    view.appendChild(ui().section("التفاصيل", bdBox));
    if (bd.team) {
      view.appendChild(h("details.card", h("summary", { style: { cursor: "pointer", fontWeight: 800 } }, "حسب الفريق"),
        h("div.tbl-wrap", { style: { marginTop: "10px" } }, h("table.tbl", h("thead", h("tr", h("th", "الفريق"), h("th.n", "مباريات"), h("th.n", "RPS"))),
          h("tbody", bd.team.slice().sort((x, y) => x[disp + "_rps"] - y[disp + "_rps"]).map((r) => h("tr", h("td", r.team), h("td.n", String(r.n)), h("td.n", n3(r[disp + "_rps"])))))))));
    }

    // ---- live record
    const lr = a.live_record || {};
    view.appendChild(ui().section("السجل الحي (توقعات مسجلة قبل البداية)", h("div.card.stack",
      lr.summary && lr.summary.length ? h("div.tbl-wrap", h("table.tbl", h("thead", h("tr", h("th", "المصدر"), h("th.n", "مباريات"), h("th.n", "اختيار صحيح"), h("th.n", "RPS"))),
        h("tbody", lr.summary.map((r) => h("tr", h("td", SRC_AR[r.track] || r.track), h("td.n", String(r.n)), h("td.n", pct(r.hit, 0)), h("td.n", n3(r.rps)))))))
        : h("p.muted", "السجل بدأ أكتوبر 2026: النتائج تنحسب لما تنتهي أول مباريات مسجلة."),
      h("p.small.faint", "كل توقع ينحفظ بوقت إصداره وإصدار الموديل ونسخة البيانات، والتوقع اللي ينصدر بعد صافرة البداية ينرفض. المقارنة على نفس المباريات لكل المصادر."))));

    // ---- versions
    view.appendChild(ui().section("الإصدارات", h("div.tbl-wrap", h("table.tbl", h("tbody",
      [["مدعوم بالسوق", reg.prematch_market.version, `اختيار ${reg.prematch_market.selection_seasons} · اختبار ${reg.prematch_market.test_seasons}`],
        ["مستقل", reg.prematch_independent.version, `اختيار ${reg.prematch_independent.selection_seasons} · اختبار ${reg.prematch_independent.test_seasons}`],
        ["المباشر", reg.inplay.version, `${variantAr(reg.inplay.variant)} · مواسم ${reg.inplay.trained_seasons}`],
        ["الموسم", reg.season.version, `تغيّر المستوى ${reg.season.drift_sd}`],
        ["بصمة بيانات التقييم", reg.data_fingerprint, ""],
        ["المعروض بالواجهة", ui().trackLabel(reg.displayed_track), ""]].map(([k, v, n]) => h("tr", h("td", k), h("td.num", { style: { direction: "ltr", textAlign: "start" } }, v), h("td.small.faint", n))))))));

    // ---- glossary
    view.appendChild(ui().section("قاموس المصطلحات", h("div.grid.g-2", Object.entries(g).map(([k, v]) => h("div.panel.small", v)))));
  }
  function inputAr(x) { return ({ "shots on target": "التسديدات على المرمى", "market-implied goals": "أهداف السوق للمباريات السابقة", "promoted-team prior": "تقدير الفرق الصاعدة", "rating stretch": "مط التقييمات", "time decay": "وزن المباريات الأحدث" })[x] || x; }
  function variantAr(v) { return ({ "time profile + score + low-score correction": "توزيع الوقت + أثر النتيجة + تصحيح النتائج القليلة", "time profile + score": "توزيع الوقت + أثر النتيجة", "time profile": "توزيع الوقت", "pre-match only": "توقع ما قبل المباراة فقط" })[v] || v; }
  function groupAr(gp) { return ({ "established teams": "فرق لها تاريخ بالدوري", "promoted team (short history)": "فريق صاعد (تاريخ قصير)" })[gp] || gp; }

  // ================================================================== data and sources
  async function renderData(view) {
    const m = D.meta;
    const ds = m.data_status || {};
    view.appendChild(ui().pageHead("البيانات والمصادر", "منين تجي الأرقام، شكد هي حديثة، شنو ناقص، وشنو يحتاج تفعيل.", null, `نسخة البيانات ${m.versions.data}`));
    // status
    const okBuild = ds.last_build_ok !== false;
    const stale = (Date.now() - new Date(m.generated_utc).getTime()) / 3600e3;
    view.appendChild(ui().section("الحالة", h("div.card.stack",
      h("div.kpis",
        h("div.kpi", h("span.k-val", ZS.ago(m.generated_utc)), h("span.k-lab", "آخر تحديث للتطبيق"), h("span.k-sub", ZS.dateTime(m.generated_utc))),
        h("div.kpi", h("span.k-val", okBuild ? "سليمة" : "فيها مشكلة"), h("span.k-lab", "آخر بناء للبيانات"), h("span.k-sub", ds.last_build ? ZS.dateTime(ds.last_build) : "")),
        h("div.kpi", h("span.k-val.num", `${ds.n_checks || 0}`), h("span.k-lab", "فحص للبيانات"), h("span.k-sub", ds.checks_ok ? "كلها ناجحة" : "بعضها فشل"))),
      stale > 36 ? h("div.notice.led", ui().icon("warn"), h("span", `البيانات عمرها ${Math.round(stale)} ساعة. التطبيق يعرض آخر نسخة سليمة لحد ما ينجح التحديث الجاي.`)) : null,
      (ds.update_problems || []).length ? h("div.notice.bad", ui().icon("warn"), h("span", "مشاكل آخر تحديث: " + ds.update_problems.join(" · "))) : null,
      ZS.env.server ? updateButton() : h("p.small.faint", "التحديث يصير من الحاسوب (python -m zsc update)، أو من جلسات Claude بعد كل جولة."))));
    // coverage and gaps
    const cov = ds.coverage || [];
    view.appendChild(ui().section("التغطية", h("div.stack",
      h("div.tbl-wrap", h("table.tbl", h("thead", h("tr", h("th", "الموسم"), h("th.n", "مباريات"), h("th.n", "أسعار"), h("th.n", "على المرمى"), h("th.n", "الشوط الأول"))),
        h("tbody", cov.map((c) => h("tr", h("td", `${c.season}/${String(c.season + 1).slice(2)}`), h("td.n", String(c.matches)), h("td.n", String(c.with_odds)), h("td.n", String(c.with_shots_on_target)), h("td.n", String(c.with_half_time))))))),
      (ds.gaps || []).length ? h("details.card", h("summary", { style: { cursor: "pointer", fontWeight: 800 } }, `${ds.gaps.length} مباراة بيها بيانات ناقصة هالموسم`),
        h("ul.small", { style: { paddingInlineStart: "18px" } }, ds.gaps.map((gp) => h("li", `${gp.date}: ${(ZS.teamByKey(gp.home) || {}).ar || gp.home} × ${(ZS.teamByKey(gp.away) || {}).ar || gp.away} — ناقص: ${gp.missing.map((x) => ({ odds: "الأسعار", shots_on_target: "على المرمى", half_time: "الشوط الأول" })[x] || x).join("، ")}`))),
        h("p.small.faint", "الناقص يبقى ناقص (ما ينحسب صفر). الأسعار الناقصة سببها إن ملف football-data المفتوح وقف عند 11 أكتوبر؛ التسديدات على المرمى انكملت من SportRadar.")) : null,
      (ds.corrections || []).length ? h("details.card", h("summary", { style: { cursor: "pointer", fontWeight: 800 } }, `${ds.corrections.length} تصحيح موثق للبيانات الخام`),
        h("ul.small", { style: { paddingInlineStart: "18px" } }, ds.corrections.map((c) => h("li", `${c.date} ${c.home} × ${c.away}: ${c.field} = ${c.value} (${c.reason})`)))) : null)));
    // sources
    const src = m.sources || {};
    view.appendChild(ui().section("المصادر", h("div.grid.g-2", Object.entries(src).map(([k, v]) => h("div.card.tight.stack", { style: { gap: "6px" } },
      h("div.row-between", h("strong", sourceAr(k)), h("span.tag" + (v.enabled === false ? "" : ".pitch"), v.enabled === false ? "غير مفعّل" : "مفعّل")),
      v.provides ? h("p.small.muted", `يوفر: ${[].concat(v.provides).join("، ")}`) : null,
      v.url ? h("p.tiny.faint", { style: { direction: "ltr", textAlign: "start", overflowWrap: "anywhere" } }, v.url) : null,
      v.note ? h("p.tiny.faint", v.note) : null)))));
    // features
    view.appendChild(ui().section("الميزات وحالتها", h("div.stack", (m.features || []).map((f) => h("div.card.tight.row-between",
      h("div.stack", { style: { gap: "2px" } }, h("strong", f.ar), f.needs_ar ? h("span.small.muted", f.needs_ar) : null),
      h("span.tag." + ({ active: "pitch", partial: "led", active_local: "led", free_adapter: "led", needs_key: "bad", needs_source: "bad" }[f.status] || ""), featureAr(f.status)))))));
    view.appendChild(h("div.notice", ui().icon("info"), h("span", "خطوات تفعيل كل ميزة (المفاتيح والمصادر) مكتوبة بملف docs/ACTIVATION.md بالمشروع.")));
  }
  function sourceAr(k) { return ({ openfootball: "openfootball (الجدول والنتائج)", football_data: "football-data.co.uk (الأسعار والتسديدات)", history: "أرشيف المواسم السابقة", statsbomb: "StatsBomb Open Data (الأرشيف العميق)", sportradar_via_claude: "SportRadar عبر Claude (المباشر)", api_football: "API-Football (التشكيلات)" })[k] || k; }
  function featureAr(s) { return ({ active: "شغّالة", partial: "شغّالة جزئياً", active_local: "شغّالة محلياً", free_adapter: "مجانية: تشتغل خارج رابط Claude", needs_key: "تحتاج مفتاح", needs_source: "تحتاج مصدر" })[s] || s; }
  function updateButton() {
    const btn = h("button.btn.primary", { type: "button" }, ui().icon("refresh"), "حدّثي البيانات هسه");
    const log = h("pre.small", { style: { whiteSpace: "pre-wrap", maxHeight: "220px", overflow: "auto", background: "var(--inset)", padding: "10px", borderRadius: "8px" }, hidden: true });
    btn.addEventListener("click", async () => {
      btn.disabled = true; log.hidden = false; log.textContent = "بدأ التحديث…";
      try {
        const r = await fetch("api/update", { method: "POST" });
        if (!r.ok) throw new Error((await r.json()).error || r.statusText);
        const poll = setInterval(async () => {
          const js = await (await fetch("api/update", { cache: "no-store" })).json();
          log.textContent = (js.log || []).join("\n");
          if (!js.running) {
            clearInterval(poll); btn.disabled = false;
            ZS.toast("خلص التحديث");
            ZS.invalidate(); await ZS.loadCore(); ZS.render();
          }
        }, 2000);
      } catch (e) { log.textContent = "ما اشتغل التحديث: " + e.message; btn.disabled = false; }
    });
    return h("div.stack", h("div", btn), log);
  }

  // ================================================================== settings
  async function renderSettings(view) {
    const p = ZS.store.prefs();
    view.appendChild(ui().pageHead("الإعدادات", `اختياراتج تنحفظ تلقائياً: ${ZS.store.where()}.`, null, "الإعدادات"));
    const theme = h("div.seg", { role: "group", "aria-label": "المظهر" }, [["dark", "داكن"], ["light", "فاتح"], ["system", "حسب الجهاز"]].map(([k, lab]) =>
      h("button", { type: "button", "aria-pressed": String(p.theme === k), onclick: async () => { await ZS.store.setPrefs({ theme: k }); ZS.applyTheme(); ZS.render(); } }, lab)));
    const track = h("div.seg", { role: "group", "aria-label": "التوقع المعروض" }, [["", "الافتراضي"], ["market", ui().trackLabel("market")], ["independent", ui().trackLabel("independent")]].map(([k, lab]) =>
      h("button", { type: "button", "aria-pressed": String((p.track || "") === k), onclick: async () => { await ZS.store.setPrefs({ track: k }); ZS.render(); } }, lab)));
    const motion = h("input", { type: "checkbox", checked: !!p.reduce_motion, onchange: async (e) => { await ZS.store.setPrefs({ reduce_motion: e.target.checked }); ZS.applyTheme(); } });
    view.appendChild(ui().section("العرض", h("div.card.stack",
      h("label.field", "المظهر", theme),
      h("label.field", "التوقع المعروض بمركز المباراة", track),
      h("label.switch", h("span.s-text", h("span", "تقليل الحركة"), h("small", "يوقف الحركات والانتقالات")), motion))));
    // favourites
    const favBox = h("div.chips");
    function drawFav() {
      ZS.clear(favBox).append(...D.teams.current.map((id) => {
        const on = ZS.store.prefs().fav_teams.includes(id);
        return h("button.chip", { type: "button", "aria-pressed": String(on), onclick: async () => {
          const cur = ZS.store.prefs().fav_teams;
          await ZS.store.setPrefs({ fav_teams: on ? cur.filter((x) => x !== id) : [...cur, id] }); drawFav();
        } }, ui().crest(id, "s"), team(id).ar);
      }));
    }
    drawFav();
    const watch = p.watchlist.map((mid) => D.fixturesById.get(mid)).filter(Boolean);
    view.appendChild(ui().section("فرقي ومتابعاتي", h("div.card.stack",
      h("h3", "الفرق المفضلة"), favBox,
      h("h3", "المباريات المتابَعة"),
      watch.length ? h("ul.list", watch.map((f) => h("li", h("a.grow", { href: ZS.href("match", f.match_id), style: { color: "var(--fg)" } }, `${team(f.home).ar} × ${team(f.away).ar}`),
        h("button.btn.small.ghost", { type: "button", onclick: async () => { await ZS.store.setPrefs({ watchlist: ZS.store.prefs().watchlist.filter((x) => x !== f.match_id) }); ZS.render(); } }, "شيليها")))) : h("p.small.faint", "ماكو مباريات متابَعة"),
      h("h3", "اللاعبين المفضلين"),
      h("p.small", `${(p.fav_players || []).length} لاعب مفضل من أرشيف الليغا 2015/16. `, h("a", { href: ZS.href("players") }, "صفحة اللاعبين ←")),
      h("p.small.faint", "بيانات اللاعبين متوفرة بالأرشيف (StatsBomb) بس؛ للاعبي الموسم الحالي تحتاج مصدر تشكيلات وإحصائيات لاعبين (صفحة البيانات والمصادر)."))));
    // alerts
    const al = p.alerts;
    const sw = (key, label, sub, disabled) => h("label.switch", h("span.s-text", h("span", label), h("small", sub)),
      h("input", { type: "checkbox", checked: !!al[key] && !disabled, disabled: !!disabled, onchange: async (e) => { await ZS.store.setPrefs({ alerts: { ...ZS.store.prefs().alerts, [key]: e.target.checked } }); } }));
    const thr = h("select", { onchange: async (e) => ZS.store.setPrefs({ alerts: { ...ZS.store.prefs().alerts, threshold_pp: Number(e.target.value) } }) },
      [3, 5, 8, 12].map((v) => h("option", { value: v, selected: al.threshold_pp === v }, `${v} نقاط مئوية أو أكثر`)));
    const freq = h("select", { onchange: async (e) => ZS.store.setPrefs({ alerts: { ...ZS.store.prefs().alerts, frequency: e.target.value } }) },
      [["visit", "كل ما أفتح التطبيق"], ["hourly", "كل ساعة إذا التطبيق مفتوح"], ["off", "أبداً"]].map(([k, lab]) => h("option", { value: k, selected: al.frequency === k }, lab)));
    view.appendChild(ui().section("التنبيهات", h("div.card.stack",
      sw("forecast_change", "تغيّر كبير بالتوقع", "لمبارياتي المتابَعة وفرقي"),
      sw("reports", "تقرير الشوط الأول ونهاية المباراة", "للمباريات اللي عليها تحليل مباشر"),
      sw("stories", "قصة جديدة تستاهل النشر", "من صفحة القصص"),
      sw("lineups", "إعلان التشكيلة", "تحتاج مصدر تشكيلات (غير مفعّل)", true),
      h("label.field", "حد التغيّر", thr), h("label.field", "التكرار", freq),
      h("p.small.faint", "التنبيهات تطلع داخل التطبيق (الجرس فوق). إشعارات الموبايل تحتاج تشغيل التطبيق على خادم عام."))));
    // data
    view.appendChild(ui().section("بياناتي", h("div.card.stack",
      h("p.small.muted", `المحفوظ: ${ZS.store.list("stories").length} قصة، ${ZS.store.list("scripts").length} نص، ${ZS.store.list("notes").length} ملاحظة.`),
      h("div.row",
        h("button.btn.small", { type: "button", onclick: () => ui().saveFile("zahraa-my-data.json", new Blob([JSON.stringify({ prefs: ZS.store.prefs(), stories: ZS.store.list("stories"), scripts: ZS.store.list("scripts"), notes: ZS.store.list("notes") }, null, 1)], { type: "application/json" })) }, ui().icon("download"), "نزّلي نسخة من بياناتي"),
        h("button.btn.small.ghost", { type: "button", onclick: confirmReset }, ui().icon("trash"), "رجّعي الإعدادات الافتراضية")))));
  }
  function confirmReset() {
    ui().openSheet("رجّعي الإعدادات الافتراضية؟", h("div.stack",
      h("p", "ترجع المظهر والفرق المفضلة والمتابعات والتنبيهات لوضعها الأصلي. القصص والنصوص والملاحظات تبقى."),
      h("div.row", h("button.btn.primary", { type: "button", onclick: async () => {
        const keep = ZS.store.prefs();
        await ZS.store.setPrefs({ theme: "dark", track: "", fav_teams: [], watchlist: [], filters: {}, alerts: { forecast_change: true, reports: true, stories: true, threshold_pp: 5, frequency: "visit" }, reduce_motion: false, handle: keep.handle });
        ui().closeSheet(); ZS.applyTheme(); ZS.render(); ZS.toast("رجعت الإعدادات الافتراضية");
      } }, "إي، رجّعيها"), h("button.btn", { type: "button", onclick: ui().closeSheet }, "لا"))));
  }

  // ================================================================== alerts (what changed since the last visit)
  function computeAlerts() {
    const p = ZS.store.prefs();
    const al = p.alerts || {};
    const seen = p.seen || {};
    const out = [];
    if (al.frequency === "off") return out;
    const mine = (f) => p.watchlist.includes(f.match_id) || p.fav_teams.includes(f.home) || p.fav_teams.includes(f.away);
    for (const f of D.fixtures) {
      if (!mine(f)) continue;
      if (al.forecast_change && f.p && !f.score) {
        const old = seen.p && seen.p[f.match_id];
        if (old) {
          const d = Math.max(...f.p.map((v, i) => Math.abs(v - old[i])));
          if (100 * d >= (al.threshold_pp || 5)) out.push({ kind: "forecast", match: f.match_id, text: `${team(f.home).ar} × ${team(f.away).ar}: التوقع تغيّر ${Math.round(100 * d)} نقطة مئوية` });
        }
      }
      if (al.reports && f.has_live && !(seen.live || []).includes(f.match_id)) out.push({ kind: "report", match: f.match_id, text: `تقرير جديد: ${team(f.home).ar} × ${team(f.away).ar}` });
    }
    if (al.stories && seen.generated && seen.generated !== D.meta.generated_utc) out.push({ kind: "data", text: `تحديث جديد للبيانات (${ZS.ago(D.meta.generated_utc)})` });
    return out;
  }
  async function markSeen() {
    const p = {};
    for (const f of D.fixtures) if (f.p && !f.score) p[f.match_id] = f.p.map((x) => Math.round(x * 1000) / 1000);
    await ZS.store.setPrefs({ seen: { generated: D.meta.generated_utc, p, live: D.fixtures.filter((f) => f.has_live).map((f) => f.match_id) } });
  }
  async function renderAlerts(view) {
    const list = computeAlerts();
    view.appendChild(ui().pageHead("التنبيهات", "شنو تغيّر من آخر مرة شفتي التطبيق، لفرقج ومتابعاتج.", h("a.btn.small", { href: ZS.href("prefs") }, ui().icon("settings"), "إعدادات التنبيهات"), "التنبيهات"));
    view.appendChild(list.length ? h("ul.list.card", list.map((a) => h("li", ui().icon(a.kind === "report" ? "whistle" : a.kind === "data" ? "refresh" : "bell"),
      a.match ? h("a.grow", { href: ZS.href("match", a.match), style: { color: "var(--fg)" } }, a.text) : h("span.grow", a.text)))) : ui().empty("ماكو شي جديد. تابعي مباريات أو اختاري فرق مفضلة حتى توصلج تنبيهاتها."));
    view.appendChild(h("div", h("button.btn", { type: "button", onclick: async () => { await markSeen(); ZS.emit("alerts"); ZS.render(); } }, ui().icon("check"), "علّمي الكل كمقروء")));
  }

  ZS.routes.method = { render: renderMethod, title: "المنهجية والدقة" };
  ZS.routes.data = { render: renderData, title: "البيانات والمصادر" };
  ZS.routes.prefs = { render: renderSettings, title: "الإعدادات" };
  ZS.routes.alerts = { render: renderAlerts, title: "التنبيهات" };
  ZS.alerts = { compute: computeAlerts, markSeen };
})();
