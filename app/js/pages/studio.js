/* Studio: story ideas from the data, post cards (9:16, 4:5, 1:1) exported as PNG, a 60-90 second script
   draft in Iraqi Arabic, saved stories and notes. Also the audience challenge page. */
(function () {
  "use strict";
  const ZS = window.ZS;
  const { h, pct, num, team, D } = ZS;
  const ui = () => ZS.ui;

  const FORMATS = { "9:16": [1080, 1920], "4:5": [1080, 1350], "1:1": [1080, 1080] };
  const TEMPLATES = [
    ["prediction", "توقع مباراة"], ["ht", "نهاية الشوط"], ["ft", "نهاية المباراة"], ["race", "سباق اللقب"], ["compare", "مقارنة فريقين"], ["story", "قصة من الأرقام"],
  ];
  const BRAND_AR = "حاسوب زهراء الكروي";
  const SHIELD = "M20 1L38 6v16c0 12-8 20-18 24C10 42 2 34 2 22V6z";
  const FONT_D = '"Changa Local", "Changa", "Cairo Local", "Cairo", sans-serif';
  const FONT_B = '"Cairo Local", "Cairo", sans-serif';

  // ------------------------------------------------------------------ canvas helpers
  function font(weight, size, display = false) { return `${weight} ${size}px ${display ? FONT_D : FONT_B}`; }
  function wrapLines(ctx, text, maxW) {
    const words = String(text || "").split(/\s+/);
    const lines = [];
    let cur = "";
    for (const w of words) {
      const t = cur ? cur + " " + w : w;
      if (ctx.measureText(t).width > maxW && cur) { lines.push(cur); cur = w; } else cur = t;
    }
    if (cur) lines.push(cur);
    return lines;
  }
  function text(ctx, str, x, y, { size = 40, weight = 700, color = "#fff", align = "right", display = false, maxW = 0, lh = 1.35, maxLines = 99 } = {}) {
    ctx.font = font(weight, size, display);
    ctx.fillStyle = color;
    ctx.textAlign = align;
    ctx.direction = "rtl";
    ctx.textBaseline = "alphabetic";
    if (!maxW) { ctx.fillText(str, x, y); return y; }
    let lines = wrapLines(ctx, str, maxW);
    if (lines.length > maxLines) { lines = lines.slice(0, maxLines); lines[maxLines - 1] += "…"; }
    lines.forEach((l, i) => ctx.fillText(l, x, y + i * size * lh));
    return y + (lines.length - 1) * size * lh;
  }
  function ltrText(ctx, str, x, y, size, color, align = "center", weight = 800) {
    ctx.font = font(weight, size, true);
    ctx.fillStyle = color;
    ctx.textAlign = align;
    ctx.direction = "ltr";
    ctx.fillText(str, x, y);
  }
  function roundRect(ctx, x, y, w, h_, r) { ctx.beginPath(); ctx.roundRect ? ctx.roundRect(x, y, w, h_, r) : ctx.rect(x, y, w, h_); }
  function drawCrest(ctx, id, x, y, w) {
    const t = team(id);
    const s = w / 40;
    const k0 = (t.kit && t.kit[0]) || t.color, k1 = (t.kit && t.kit[1]) || "#ffffff";
    const pat = { ATM: "stripes", BAR: "stripes", ATH: "stripes", RBB: "stripes", ESP: "stripes", DEP: "stripes", MCF: "stripes", RSO: "stripes", LEV: "stripes", ALA: "stripes", GIR: "stripes", RVC: "sash", ELC: "band" }[t.id] || "plain";
    ctx.save();
    ctx.translate(x, y); ctx.scale(s, s);
    const p = new Path2D(SHIELD);
    ctx.save(); ctx.clip(p);
    ctx.fillStyle = k0; ctx.fillRect(0, 0, 40, 47);
    ctx.fillStyle = k1;
    if (pat === "stripes") for (let i = 1; i < 8; i += 2) ctx.fillRect(i * 5, 0, 5, 47);
    else if (pat === "sash") { ctx.beginPath(); ctx.moveTo(-4, 36); ctx.lineTo(36, -4); ctx.lineTo(46, 4); ctx.lineTo(6, 46); ctx.fill(); }
    else if (pat === "band") ctx.fillRect(0, 14, 40, 11);
    ctx.fillStyle = "rgba(11,15,12,.72)"; ctx.fillRect(0, 29, 40, 11);
    ctx.font = font(800, 8.4, true); ctx.fillStyle = "#fff"; ctx.textAlign = "center"; ctx.direction = "ltr";
    ctx.fillText(t.id, 20, 37.6);
    ctx.restore();
    ctx.lineWidth = 1.4; ctx.strokeStyle = "rgba(255,255,255,.35)"; ctx.stroke(p);
    ctx.restore();
  }
  function background(ctx, W, H, accent) {
    ctx.fillStyle = "#0e1310"; ctx.fillRect(0, 0, W, H);
    // mowing stripes and chalk lines of a pitch, very faint
    for (let i = 0; i < 12; i++) if (i % 2) { ctx.fillStyle = "rgba(52,180,108,.035)"; ctx.fillRect(0, (H / 12) * i, W, H / 12); }
    ctx.strokeStyle = "rgba(232,238,233,.07)"; ctx.lineWidth = 4;
    ctx.strokeRect(40, 40, W - 80, H - 80);
    ctx.beginPath(); ctx.moveTo(40, H / 2); ctx.lineTo(W - 40, H / 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(W / 2, H / 2, 150, 0, Math.PI * 2); ctx.stroke();
    // accent bar at the top
    ctx.fillStyle = accent; ctx.fillRect(0, 0, W, 14);
  }
  function header(ctx, W, label, accent) {
    // brand mark: a small pitch with the centre circle
    roundRect(ctx, W - 80 - 64, 70, 64, 64, 14); ctx.fillStyle = "#34b46c"; ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,.9)"; ctx.lineWidth = 3.5;
    ctx.beginPath(); ctx.arc(W - 80 - 32, 102, 15, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(W - 80 - 32, 76); ctx.lineTo(W - 80 - 32, 128); ctx.stroke();
    text(ctx, BRAND_AR, W - 80 - 84, 112, { size: 36, weight: 800, display: true });
    // template label pill
    ctx.font = font(800, 30, true);
    const lw = ctx.measureText(label).width + 48;
    roundRect(ctx, 80, 72, lw, 58, 29); ctx.fillStyle = accent; ctx.fill();
    text(ctx, label, 80 + lw - 24, 112, { size: 30, weight: 800, color: ZS.inkOn(accent.startsWith("#") ? accent : "#34b46c"), display: true });
  }
  function footer(ctx, W, H, m) {
    ctx.fillStyle = "rgba(255,255,255,.06)"; ctx.fillRect(0, H - 190, W, 190);
    if (m.handle) {
      const rtlHandle = /[\u0600-\u06FF]/.test(m.handle);
      if (rtlHandle) text(ctx, m.handle, W - 80, H - 128, { size: 34, weight: 800, display: true });
      else ltrText(ctx, m.handle, W - 80, H - 128, 34, "#ffffff", "right");
    }
    text(ctx, `المصدر: ${m.source}`, W - 80, H - 82, { size: 24, weight: 600, color: "rgba(255,255,255,.72)", maxW: W - 160, maxLines: 1 });
    ctx.direction = "ltr"; ctx.textAlign = "right"; ctx.font = font(600, 21); ctx.fillStyle = "rgba(255,255,255,.55)";
    ctx.fillText(`${m.version} · ${m.updated}`, W - 80, H - 44);
  }
  function probRow(ctx, x, y, w, p, cols, labels) {
    let cx = x + w; // right to left
    const gap = 8, avail = w - 2 * gap;
    p.forEach((v, i) => {
      const sw = Math.max(6, avail * v);
      roundRect(ctx, cx - sw, y, sw, 34, 8); ctx.fillStyle = cols[i]; ctx.fill();
      cx -= sw + gap;
    });
    // numbers under the bar
    const pos = [x + w, x + w / 2, x];
    const al = ["right", "center", "left"];
    p.forEach((v, i) => {
      ctx.font = font(800, 76, true); ctx.fillStyle = i === 1 ? "rgba(255,255,255,.85)" : "#fff"; ctx.textAlign = al[i]; ctx.direction = "ltr";
      ctx.fillText(`${Math.round(100 * v)}%`, pos[i], y + 120);
      ctx.font = font(700, 28); ctx.fillStyle = "rgba(255,255,255,.75)"; ctx.direction = "rtl";
      ctx.fillText(labels[i], pos[i], y + 166);
    });
  }

  // ------------------------------------------------------------------ card drawing per template
  function drawCard(canvas, m) {
    const [W, H] = FORMATS[m.format];
    canvas.width = W; canvas.height = H;
    const ctx = canvas.getContext("2d");
    background(ctx, W, H, m.accent);
    header(ctx, W, m.label, m.accent);
    // measure the content once off screen, then centre it between the header and the footer
    const probe = document.createElement("canvas");
    probe.width = W; probe.height = H;
    const top = 200, bottom = H - 220;
    const used = drawContent(probe.getContext("2d"), W, H, m, top) - top;
    const offset = Math.max(0, (bottom - top - used) / 2);
    drawContent(ctx, W, H, m, top + offset);
    footer(ctx, W, H, m);
  }
  function drawContent(ctx, W, H, m, y0) {
    const tall = H / W > 1.5, square = H === W;
    let y = y0 + 70;
    y = text(ctx, m.title, W - 80, y, { size: tall ? 68 : 56, weight: 800, display: true, maxW: W - 160, maxLines: 3, lh: 1.25 }) + (tall ? 64 : 50);
    if (m.subtitle) y = text(ctx, m.subtitle, W - 80, y, { size: tall ? 34 : 30, weight: 600, color: "rgba(255,255,255,.78)", maxW: W - 160, maxLines: 3 }) + (tall ? 70 : 46);
    const d = m.data || {};
    if (m.template === "prediction" || m.template === "ht" || m.template === "ft") {
      const cy = y;
      const cw = square ? 150 : tall ? 230 : 190;
      drawCrest(ctx, d.home, W - 80 - cw, cy, cw);
      drawCrest(ctx, d.away, 80, cy, cw);
      const nameY = cy + cw * 1.175 + 56;
      text(ctx, team(d.home).ar, W - 80 - cw / 2, nameY, { size: tall ? 40 : 36, weight: 800, align: "center", display: true });
      text(ctx, team(d.away).ar, 80 + cw / 2, nameY, { size: tall ? 40 : 36, weight: 800, align: "center", display: true });
      if (d.score) {
        ltrText(ctx, `${d.score[1]}  –  ${d.score[0]}`, W / 2, cy + cw * 0.72, square ? 120 : 160, "#fff");
        if (d.scoreNote) text(ctx, d.scoreNote, W / 2, cy + cw * 0.72 + 66, { size: 28, weight: 700, align: "center", color: "rgba(255,255,255,.75)" });
      } else if (d.time) {
        ltrText(ctx, d.time, W / 2, cy + cw * 0.6, tall ? 96 : 84, "#fff");
        text(ctx, d.dateText || "", W / 2, cy + cw * 0.6 + 58, { size: 28, weight: 700, align: "center", color: "rgba(255,255,255,.75)" });
      }
      y = nameY + (square ? 60 : 90);
      if (d.p) {
        const [hc, ac] = ZS.pairColours(team(d.home), team(d.away));
        probRow(ctx, 80, y, W - 160, d.p, [hc, "#7d8a83", ac], [`فوز ${team(d.home).short || team(d.home).ar}`, "تعادل", `فوز ${team(d.away).short || team(d.away).ar}`]);
        y += square ? 230 : 260;
      }
      for (const line of (d.lines || []).slice(0, square ? 2 : tall ? 4 : 3)) {
        y = text(ctx, "• " + line, W - 80, y, { size: tall ? 34 : 31, weight: 600, maxW: W - 160, maxLines: 2 }) + (tall ? 64 : 54);
      }
    } else if (m.template === "race" || m.template === "compare") {
      const rows = d.rows || [];
      const rowH = square ? 118 : 160;
      for (const r of rows.slice(0, square ? 5 : 6)) {
        drawCrest(ctx, r.id, W - 80 - 80, y, 80);
        text(ctx, team(r.id).ar, W - 80 - 104, y + 44, { size: 38, weight: 800, display: true });
        if (r.sub) text(ctx, r.sub, W - 80 - 104, y + 86, { size: 26, weight: 600, color: "rgba(255,255,255,.7)", maxW: W - 400, maxLines: 1 });
        const bw = (W - 160 - 520) * Math.max(0.02, r.v || 0);
        roundRect(ctx, 80 + 160, y + 30, bw, 26, 13); ctx.fillStyle = r.color || m.accent; ctx.fill();
        ltrText(ctx, r.text, 80, y + 62, 54, "#fff", "left");
        y += rowH;
      }
      for (const line of (d.lines || []).slice(0, 2)) y = text(ctx, "• " + line, W - 80, y + 20, { size: 30, weight: 600, maxW: W - 160, maxLines: 2 }) + 56;
    } else if (m.template === "story") {
      y = text(ctx, d.text || "", W - 80, y, { size: tall ? 40 : 36, weight: 600, maxW: W - 160, maxLines: tall ? 9 : square ? 4 : 6, lh: 1.45 }) + 90;
      for (const ev of (d.evidence || []).slice(0, square ? 2 : 4)) {
        roundRect(ctx, 80, y - 54, W - 160, 88, 18); ctx.fillStyle = "rgba(255,255,255,.07)"; ctx.fill();
        text(ctx, ev.label_ar, W - 110, y, { size: 30, weight: 700, color: "rgba(255,255,255,.8)", maxW: W - 460, maxLines: 1 });
        text(ctx, String(ev.value), 110, y, { size: 38, weight: 800, display: true, color: m.accent.startsWith("#") && m.accent !== "#e8eee9" ? m.accent : "#f3c14f", align: "left" });
        y += 110;
      }
    }
    return y;
  }

  function latinTime(iso) {
    const d = new Date(iso);
    const f = new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Baghdad", day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false }).format(d);
    return `updated ${f.replace(",", "")} Baghdad`;
  }

  // ------------------------------------------------------------------ data for each template
  async function buildModel(st) {
    const meta = D.meta;
    const base = {
      template: st.template, format: st.format, accent: st.accent, handle: st.handle,
      label: TEMPLATES.find((t) => t[0] === st.template)[1],
      version: `${meta.versions.prematch_market} · data ${meta.versions.data}`,
      updated: latinTime(meta.generated_utc), source: "حاسوب زهراء الكروي (موديل ديكسون-كولز)، نتائج football-data وopenfootball",
    };
    const auto = { title: "", subtitle: "", data: {} };
    if (["prediction", "ht", "ft"].includes(st.template)) {
      const mf = st.match ? await ZS.matchFile(st.match) : null;
      if (!mf) return { ...base, ...auto, title: "اختاري مباراة" };
      const H = team(mf.home), A = team(mf.away);
      const t = mf.tracks[mf.displayed_track] || mf.tracks.market || Object.values(mf.tracks)[0];
      const live = mf.live;
      auto.data = { home: mf.home, away: mf.away };
      if (st.template === "prediction") {
        auto.title = `${H.ar} × ${A.ar}`;
        auto.subtitle = mf.takeaway_ar || "";
        auto.data.time = mf.kickoff_utc ? ZS.timeHM(mf.kickoff_utc) : "";
        auto.data.dateText = mf.kickoff_utc ? `${ZS.dateLong(mf.kickoff_utc)} · بتوقيت بغداد` : "";
        auto.data.p = t && t.p;
        const lines = [];
        if (t && t.top_scores) lines.push(`أرجح نتيجة: ${H.ar} ${t.top_scores[0][0].split("-")[0]} – ${t.top_scores[0][0].split("-")[1]} ${A.ar} (${pct(t.top_scores[0][1])})`);
        if (t && t.reasons && t.reasons[0]) lines.push(t.reasons[0].text_ar);
        const sw = mf.importance && mf.importance.swings && mf.importance.swings[0];
        if (sw) lines.push(`فرصة ${team(sw.team_id).ar} ب${{ p_title: "اللقب", p_ucl: "الأبطال", p_releg: "الهبوط" }[sw.metric]}: ${pct(sw.home_win)} إذا فاز ${H.ar}، ${pct(sw.away_win)} إذا فاز ${A.ar}`);
        auto.data.lines = lines;
        // context for the script: table position and recent form of both teams, pre-match expected goals
        try {
          const [s, ch, ca] = await Promise.all([ZS.getJSON("season.json"), ZS.getJSON(`teams/${mf.home}.json`), ZS.getJSON(`teams/${mf.away}.json`)]);
          const row = (id) => s.table.find((r) => r.id === id) || {};
          const form = (c) => { const f = (c.form || []).slice(-5); const w = f.filter((g) => g.result === "W").length, dr = f.filter((g) => g.result === "D").length; return { pts: f.reduce((a, g) => a + g.pts, 0), n: f.length, w, d: dr, l: f.length - w - dr }; };
          auto.data.ctx = { posH: row(mf.home).pos, ptsH: row(mf.home).Pts, posA: row(mf.away).pos, ptsA: row(mf.away).Pts, formH: form(ch), formA: form(ca), xg: t && t.xg, sr: mf.p_sr };
        } catch (e) { auto.data.ctx = null; }
        base.source = "حاسوب زهراء الكروي: توقع ما قبل المباراة";
        if (t && t.model_version) base.version = `${t.model_version} · data ${t.data_version}`;
      } else {
        const rep = live && live.reports && (st.template === "ht" ? live.reports.HT : live.reports.FT);
        const score = st.template === "ft" ? (mf.score || (live && live.score)) : (rep ? rep.now && live.reports.HT ? [rep.score ? rep.score[0] : (mf.ht || [0, 0])[0], rep.score ? rep.score[1] : (mf.ht || [0, 0])[1]] : mf.ht : mf.ht);
        auto.title = st.template === "ht" ? "نص الوقت" : "صافرة النهاية";
        auto.subtitle = `${H.ar} × ${A.ar}`;
        auto.data.score = score || null;
        auto.data.scoreNote = st.template === "ht" ? "نهاية الشوط الأول" : "النتيجة النهائية";
        if (rep && rep.now && st.template === "ht") auto.data.p = rep.now.p;
        const lines = [];
        if (rep) {
          for (const side of ["home", "away"]) { const ins = rep.insights && rep.insights[side]; if (ins && ins.pos && ins.pos[0]) lines.push(`${side === "home" ? H.ar : A.ar}: ${ins.pos[0]}`); }
          for (const n of rep.notes || []) lines.push(n);
          base.source = "SportRadar (إحصائيات وأحداث) + موديل الحاسوب المباشر";
        } else if (mf.facts) {
          if (mf.facts.sot) lines.push(`التسديدات على المرمى: ${H.ar} ${mf.facts.sot[0]} – ${mf.facts.sot[1]} ${A.ar}`);
          const tr = mf.tracks[mf.displayed_track];
          if (tr && tr.p) lines.push(`الحاسوب كان يعطي ${H.ar} ${pct(tr.p[0])} والتعادل ${pct(tr.p[1])} و${A.ar} ${pct(tr.p[2])}`);
        }
        auto.data.lines = lines;
      }
    } else if (st.template === "race") {
      const s = await ZS.getJSON("season.json");
      const sorted = s.projection.slice().sort((a, b) => b.p_title - a.p_title);
      const rows = sorted.filter((r, i) => i < 3 || r.p_title >= 0.005).slice(0, 5);
      auto.title = "سباق اللقب بالأرقام";
      auto.subtitle = `فرص اللقب من ${num(s.n_sims, 0)} موسم محاكى`;
      auto.data.rows = rows.map((r) => ({ id: r.id, v: r.p_title, text: pct(r.p_title), sub: `${r.pts_now} نقطة الآن · المتوقع ${num(r.exp_pts, 0)}`, color: "#f3c14f" }));
      base.source = "حاسوب زهراء الكروي: محاكاة الموسم";
      base.version = `${D.meta.versions.season} · data ${D.meta.versions.data}`;
    } else if (st.template === "compare") {
      const s = await ZS.getJSON("season.json");
      const ids = [st.teamA || "BAR", st.teamB || "RMA"];
      const pr = Object.fromEntries(s.projection.map((r) => [r.id, r]));
      const cards = await Promise.all(ids.map((id) => ZS.getJSON(`teams/${id}.json`)));
      auto.title = `${team(ids[0]).ar} × ${team(ids[1]).ar}`;
      auto.subtitle = "مقارنة بالأرقام";
      const rows = [];
      ids.forEach((id, k) => {
        const c = cards[k], r = pr[id] || {};
        rows.push({ id, v: (r.exp_pts || 0) / 100, text: num(r.exp_pts, 0), sub: `نقاط متوقعة · الآن ${r.pts_now} · هجوم ${num(c.ratings.market.attack, 2)}× · دفاع ${num(c.ratings.market.defence, 2)}×`, color: team(id).color });
      });
      auto.data.rows = rows;
      auto.data.lines = ids.map((id, k) => `${team(id).ar}: اللقب ${pct((pr[id] || {}).p_title)} · الأبطال ${pct((pr[id] || {}).p_ucl)} · نقاط ${cards[k].totals.pts} مقابل متوقع ${num(cards[k].totals.xpts_pre, 1)}`);
      base.source = "حاسوب زهراء الكروي";
    } else if (st.template === "story") {
      const story = st.story;
      if (!story) return { ...base, ...auto, title: "اختاري قصة" };
      auto.title = story.title_ar;
      auto.data.text = story.text_ar;
      auto.data.evidence = story.evidence || [];
      base.source = `حاسوب زهراء الكروي · ${story.comparison_ar || ""}`;
    }
    return { ...base, ...auto, title: st.title ?? auto.title, subtitle: st.subtitle ?? auto.subtitle };
  }

  // ------------------------------------------------------------------ script draft (Iraqi Arabic, 60-90 s)
  function scriptFor(model, mfLike) {
    const d = model.data || {};
    const parts = [];
    if (model.template === "prediction" && d.home) {
      const H = team(d.home).ar, A = team(d.away).ar;
      const p = d.p || [0.33, 0.33, 0.33];
      const best = p.indexOf(Math.max(...p));
      const fav = best === 0 ? H : A;
      parts.push(["الهوك", best === 1 ? `${H} ضد ${A}… مباراة ما بيها مرشح واضح، والحاسوب نفسه محتار!`
        : p[best] >= 0.6 ? `${H} ضد ${A}… الحاسوب حسمها قبل لا تبدي؟` : `${H} ضد ${A}… ${fav} مرشح، بس الحاسوب يگول: مو مضمونة!`]);
      parts.push(["الفكرة", `حاسوب زهراء يعطي ${H} ${pct(p[0])} للفوز، والتعادل ${pct(p[1])}، و${A} ${pct(p[2])}. ${model.subtitle || ""}`]);
      const c = d.ctx;
      if (c) {
        const fl = (f) => [f.w ? ZS.countAr(f.w, "فوز وحيد", "فوزين", "انتصارات", "فوز") : "بدون فوز",
          f.d ? ZS.countAr(f.d, "تعادل وحيد", "تعادلين", "تعادلات", "تعادل") : "",
          f.l ? ZS.countAr(f.l, "خسارة وحدة", "خسارتين", "خسارات", "خسارة") : "بدون خسارة"].filter(Boolean).join("، ");
        parts.push(["الوضع", `${H} بالمركز ${c.posH} برصيد ${c.ptsH} نقطة، و${A} بالمركز ${c.posA} برصيد ${c.ptsA}. آخر ${c.formH.n} مباريات: ${H} ${fl(c.formH)}، و${A} ${fl(c.formA)}.`]);
      }
      parts.push(["الأرقام", (d.lines || []).join(". ") + "." + (c && c.xg ? ` والأهداف المتوقعة قبل المباراة: ${H} ${c.xg[0].toFixed(1)} مقابل ${c.xg[1].toFixed(1)} لـ${A}.` : "")
        + (c && c.sr ? ` وللمقارنة، SportRadar يعطي ${H} ${pct(c.sr[0])}.` : "")]);
      parts.push(["ليش؟", "هالأرقام مو إحساس: الموديل يحسب قوة هجوم ودفاع كل فريق من نتائجه، وميزة الأرض، وهو مجرّب على أكثر من ألف مباراة ما شافها قبل."]);
      parts.push(["الختام", `وإنتو؟ تتفقون ويا الحاسوب لو عندكم مفاجأة؟ اكتبوا توقعكم بالأرقام بالتعليقات، ونشوف منو يطلع أشطر: الجمهور لو الحاسوب!`]);
    } else if ((model.template === "ht" || model.template === "ft") && d.home) {
      const H = team(d.home).ar, A = team(d.away).ar;
      const sc = d.score ? `${H} ${d.score[0]} و${A} ${d.score[1]}` : "";
      parts.push(["الهوك", model.template === "ht" ? `نص الوقت وصار عدنا قصة: ${sc}!` : `خلصت! ${sc}، وهاي القصة بالأرقام.`]);
      if (d.p) parts.push(["الفكرة", `حسب الحاسوب هسه: ${H} ${pct(d.p[0])}، تعادل ${pct(d.p[1])}، ${A} ${pct(d.p[2])}.`]);
      parts.push(["الأرقام", (d.lines || []).join(". ") + "."]);
      parts.push(["الختام", model.template === "ht" ? "الشوط الثاني راح يقلبها لو تبقى؟ اكتبوا توقعكم قبل لا تنتهي!" : "النتيجة عادلة لو ظالمة حسب رأيكم؟ ناقشوني بالتعليقات."]);
    } else if (model.template === "race") {
      const r = d.rows || [];
      parts.push(["الهوك", "منو ياخذ الليغا هالموسم؟ الحاسوب لعب الموسم عشرة آلاف مرة!"]);
      parts.push(["الفكرة", r.map((x) => `${team(x.id).ar} ${x.text}`).join("، ") + "."]);
      parts.push(["الأرقام", r.slice(0, 2).map((x) => `${team(x.id).ar}: ${x.sub}`).join(". ") + "."]);
      parts.push(["الختام", "الأرقام تگول شي، والملعب يگول شي ثاني… منو مرشحكم؟ اكتبوه بالتعليقات."]);
    } else if (model.template === "compare") {
      parts.push(["الهوك", `${model.title}: منو أقوى فعلاً بالأرقام؟`]);
      parts.push(["الأرقام", (d.lines || []).join(". ") + "."]);
      parts.push(["الختام", "إنتو مع منو؟ وليش؟ أريد أسبابكم مو بس الاسم!"]);
    } else if (model.template === "story") {
      parts.push(["الهوك", model.title]);
      parts.push(["الفكرة", d.text || ""]);
      parts.push(["الأرقام", (d.evidence || []).map((e) => `${e.label_ar}: ${e.value}`).join("، ") + "."]);
      parts.push(["الختام", "هل هي صدفة لو شي حقيقي راح يكمل؟ ناقشوني بالتعليقات."]);
    }
    return parts.map(([k, v]) => `[${k}]\n${v.trim()}`).join("\n\n");
  }
  function wordStats(t) {
    const words = t.replace(/\[[^\]]+\]/g, "").split(/\s+/).filter(Boolean).length;
    return { words, seconds: Math.round(words / 2.3) };
  }

  // ------------------------------------------------------------------ page
  async function render(view, params) {
    const [storiesJs] = await Promise.all([ZS.getJSON("stories.json").catch(() => ({ stories: [] }))]);
    const stories = storiesJs.stories || [];
    const upcoming = D.fixtures.filter((f) => !f.score && f.kickoff_utc && new Date(f.kickoff_utc) > new Date()).sort((a, b) => a.kickoff_utc.localeCompare(b.kickoff_utc)).slice(0, 20);
    const finished = D.fixtures.filter((f) => f.score || f.has_live).sort((a, b) => (b.kickoff_utc || "").localeCompare(a.kickoff_utc || "")).slice(0, 20);
    const prefs = ZS.store.prefs();
    const st = { template: "prediction", format: "9:16", accent: "#34b46c", handle: prefs.handle ?? "@zahraatalksfootball94", match: upcoming[0] && upcoming[0].match_id, story: null, teamA: "BAR", teamB: "RMA", title: undefined, subtitle: undefined };
    if (params.id && params.id.startsWith("story-")) {
      const sid = params.id.slice(6);
      const s = stories.find((x) => x.id === sid);
      if (s) { st.template = "story"; st.story = s; }
    }
    view.appendChild(ui().pageHead("استوديو زهراء", "حوّلي الأرقام لبطاقة جاهزة للنشر ونص فيديو قصير. كل بطاقة تحمل اسم المنصة والمصدر ووقت التحديث وإصدار التوقع تلقائياً.", null, "المحتوى"));

    // ---- stories
    const storyBox = h("div.grid.g-auto");
    for (const s of stories.slice(0, 9)) {
      storyBox.appendChild(h("article.card.story-card",
        h("div.row", h("span.tag.led", ZS.routes.today.storyType(s.type)), s.sample ? h("span.tag", `العينة: ${s.sample}`) : null),
        h("h3", s.title_ar), h("p.small", s.text_ar),
        h("div.ev", (s.evidence || []).slice(0, 3).map((e) => h("span", `${e.label_ar}: `, h("strong.num", String(e.value))))),
        h("p.tiny.faint", `${s.comparison_ar} · ${s.period_ar}`),
        h("div.row", h("button.btn.small.primary", { type: "button", onclick: () => { st.template = "story"; st.story = s; st.title = undefined; st.subtitle = undefined; sync(); composer.scrollIntoView({ behavior: "smooth" }); } }, "استخدميها بالبطاقة"),
          h("button.btn.small", { type: "button", onclick: () => ZS.routes.today.saveStory(s).then(drawSaved) }, ui().icon("star"), "احفظيها"))));
    }
    view.appendChild(ui().section("قصص من الأرقام", stories.length ? storyBox : ui().empty("ماكو قصص واضحة هسه")));

    // ---- composer
    const composer = h("section.studio");
    view.appendChild(ui().section("صانعة البطاقات", composer));
    const controls = h("div.card.stack");
    const preview = h("div.studio-preview");
    composer.append(controls, preview);
    const canvas = h("canvas", { width: 1080, height: 1920, role: "img", "aria-label": "معاينة البطاقة" });
    const exportImg = h("img.export", { alt: "البطاقة كصورة: اضغطي مطولاً لحفظها", hidden: true });
    const exportBtn = h("button.btn.primary", { type: "button" }, ui().icon("download"), "نزّلي PNG");
    const imgBtn = h("button.btn", { type: "button" }, ui().icon("eye"), "اعرضيها كصورة");
    preview.append(canvas, h("div.row", exportBtn, imgBtn), exportImg, h("p.tiny.faint", "على الموبايل: «اعرضيها كصورة» ثم اضغطي مطولاً على الصورة واحفظيها."));

    const tplSeg = h("div.seg", { role: "group", "aria-label": "القالب" });
    const fmtSeg = h("div.seg", { role: "group", "aria-label": "المقاس" });
    const dataSlot = h("div.stack");
    const titleIn = h("input#studio-title", { type: "text", "aria-label": "العنوان" });
    const subIn = h("textarea#studio-sub", { rows: 2, "aria-label": "النص تحت العنوان", style: { minHeight: "70px" } });
    const handleIn = h("input#studio-handle", { type: "text", value: st.handle, "aria-label": "التوقيع" });
    const swatches = h("div.swatches", { role: "group", "aria-label": "لون التمييز" });
    controls.append(
      h("label.field", "القالب", tplSeg), h("label.field", "المقاس", fmtSeg), dataSlot,
      h("label.field", "العنوان", titleIn), h("label.field", "النص تحت العنوان", subIn),
      h("div.field", h("span.small.muted", { style: { fontWeight: 700 } }, "لون التمييز (ضمن هوية المنصة)"), swatches),
      h("label.field", "التوقيع", handleIn),
      h("button.btn.small.ghost", { type: "button", onclick: () => { st.title = undefined; st.subtitle = undefined; sync(); } }, ui().icon("refresh"), "رجّعي النص التلقائي"));

    function drawControls() {
      ZS.clear(tplSeg).append(...TEMPLATES.map(([k, lab]) => h("button", { type: "button", "aria-pressed": String(st.template === k), onclick: () => { st.template = k; st.title = undefined; st.subtitle = undefined; sync(); } }, lab)));
      ZS.clear(fmtSeg).append(...Object.keys(FORMATS).map((k) => h("button", { type: "button", "aria-pressed": String(st.format === k), onclick: () => { st.format = k; sync(); } }, k)));
      ZS.clear(dataSlot);
      if (st.template === "prediction") {
        if (!upcoming.find((f) => f.match_id === st.match)) st.match = upcoming[0] && upcoming[0].match_id;
        dataSlot.appendChild(h("label.field", "المباراة", select(upcoming, st.match, (v) => { st.match = v; st.title = undefined; st.subtitle = undefined; sync(); })));
      }
      if (st.template === "ht" || st.template === "ft") {
        if (!finished.find((f) => f.match_id === st.match)) st.match = finished[0] && finished[0].match_id;
        dataSlot.appendChild(h("label.field", "المباراة", select(finished, st.match, (v) => { st.match = v; st.title = undefined; st.subtitle = undefined; sync(); })));
      }
      if (st.template === "compare") {
        const teamSel = (val, on) => h("select", { onchange: (e) => on(e.target.value) }, D.teams.current.map((id) => h("option", { value: id, selected: id === val }, team(id).ar)));
        dataSlot.appendChild(h("div.grid.g-2", h("label.field", "الفريق الأول", teamSel(st.teamA, (v) => { st.teamA = v; st.title = undefined; sync(); })), h("label.field", "الفريق الثاني", teamSel(st.teamB, (v) => { st.teamB = v; st.title = undefined; sync(); }))));
      }
      if (st.template === "story") {
        const all = [...stories, ...ZS.store.list("stories").filter((x) => !stories.find((y) => y.id === x.id))];
        if (!st.story && all[0]) st.story = all[0];
        dataSlot.appendChild(h("label.field", "القصة", h("select", { onchange: (e) => { st.story = all.find((x) => x.id === e.target.value); st.title = undefined; sync(); } },
          all.map((s) => h("option", { value: s.id, selected: st.story && s.id === st.story.id }, s.title_ar)))));
      }
      const accents = [["#34b46c", "أخضر الملعب"], ["#f3c14f", "أصفر الشاشة"], ["#e8eee9", "أبيض الطباشير"]];
      if (st.match && ["prediction", "ht", "ft"].includes(st.template)) { const f = D.fixturesById.get(st.match); if (f) accents.push([team(f.home).color, team(f.home).ar], [team(f.away).color, team(f.away).ar]); }
      ZS.clear(swatches).append(...accents.map(([c, lab]) => h("button.swatch", { type: "button", title: lab, "aria-label": lab, "aria-pressed": String(st.accent === c), style: { background: c }, onclick: () => { st.accent = c; sync(); } })));
    }
    function select(list, val, on) {
      return h("select", { onchange: (e) => on(e.target.value) }, list.map((f) => h("option", { value: f.match_id, selected: f.match_id === val },
        `${team(f.home).ar} × ${team(f.away).ar}${f.score ? ` (${f.score[0]}–${f.score[1]})` : f.kickoff_utc ? ` · ${ZS.dateShort(f.kickoff_utc)}` : ""}`)));
    }
    titleIn.addEventListener("input", () => { st.title = titleIn.value; redraw(); });
    subIn.addEventListener("input", () => { st.subtitle = subIn.value; redraw(); });
    handleIn.addEventListener("input", () => { st.handle = handleIn.value; redraw(); });
    handleIn.addEventListener("change", () => ZS.store.setPrefs({ handle: handleIn.value }));

    let model = null;
    let raf = 0;
    async function sync() { drawControls(); model = await buildModel(st); titleIn.value = model.title || ""; subIn.value = model.subtitle || ""; redraw(); refreshScript(); }
    function redraw() {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(async () => {
        if (!model) return;
        try { await Promise.all([document.fonts.load(font(800, 40, true)), document.fonts.load(font(600, 30)), document.fonts.load(font(700, 30))]); } catch (e) { /* draw with fallbacks */ }
        drawCard(canvas, { ...model, title: st.title ?? model.title, subtitle: st.subtitle ?? model.subtitle, accent: st.accent, handle: st.handle, format: st.format });
        exportImg.hidden = true;
      });
    }
    function fileName() { return `zahraa-${st.template}-${st.format.replace(":", "x")}-${new Date().toISOString().slice(0, 10)}.png`; }
    exportBtn.addEventListener("click", () => canvas.toBlob(async (b) => { if (b) await ui().saveFile(fileName(), b); }, "image/png"));
    imgBtn.addEventListener("click", () => { exportImg.src = canvas.toDataURL("image/png"); exportImg.hidden = false; exportImg.scrollIntoView({ behavior: "smooth", block: "nearest" }); });

    // ---- script
    const scriptBox = h("textarea#studio-script", { rows: 12, "aria-label": "نص الفيديو" });
    const stats = h("p.small.muted", { role: "status" });
    const improveBtn = h("button.btn", { type: "button", hidden: true }, ui().icon("spark"), "حسّني الصياغة (Claude)");
    const scriptCard = h("div.card.stack",
      h("div.card-head", h("h2", "نص فيديو 60–90 ثانية"), h("span.tag", "لهجة عراقية")),
      h("p.small.muted", "مسودة من نفس أرقام البطاقة: هوك، الفكرة، أرقام تگدرين تتأكدين منها، وختام يفتح نقاش. عدّليها براحتج."),
      scriptBox, stats,
      h("div.row",
        h("button.btn.primary", { type: "button", onclick: saveScript }, ui().icon("check"), "احفظي النص"),
        h("button.btn", { type: "button", onclick: () => ui().copyText(scriptBox.value) }, ui().icon("copy"), "انسخي"),
        h("button.btn", { type: "button", onclick: () => { scriptBox.value = scriptFor(model); count(); } }, ui().icon("refresh"), "مسودة جديدة"),
        improveBtn));
    view.appendChild(scriptCard);
    function count() {
      const w = wordStats(scriptBox.value);
      stats.textContent = `${w.words} كلمة ≈ ${w.seconds} ثانية بالقراءة العادية${w.seconds < 60 ? " (قصيّر: ضيفي تفصيل)" : w.seconds > 90 ? " (طويل: اختصري)" : ""}`;
    }
    scriptBox.addEventListener("input", count);
    function refreshScript() { if (model) { scriptBox.value = scriptFor(model); count(); } }
    async function saveScript() {
      const list = ZS.store.list("scripts");
      list.unshift({ id: "s" + Date.now(), title: st.title ?? (model && model.title) ?? "", text: scriptBox.value, template: st.template, created_at: new Date().toISOString() });
      await ZS.store.saveList("scripts", list.slice(0, 60));
      drawSaved();
      ZS.toast("انحفظ النص");
    }
    const showImprove = () => { improveBtn.hidden = !ZS.env.sample; };
    showImprove();
    const off = ZS.on("env", showImprove);
    improveBtn.addEventListener("click", async () => {
      const sample = ZS.env.sample;
      if (!sample) return;
      improveBtn.disabled = true;
      const before = scriptBox.value;
      try {
        const res = await sample([{ role: "user", content:
          "أنت كاتبة محتوى كرة قدم عراقية. حسّني صياغة نص فيديو قصير (60-90 ثانية) باللهجة العراقية المحكية، بنفس الأقسام بين الأقواس المربعة. " +
          "قواعد صارمة: لا تغيّري ولا تضيفي أي رقم أو اسم أو حقيقة؛ كل رقم يبقى بنفس قيمته. لا تضيفي إيموجي. أعيدي النص فقط.\n\n" + before }], { cache: false });
        if (res && res.text) {
          const nums = (t) => (t.match(/\d+(?:\.\d+)?/g) || []).sort().join(",");
          if (nums(res.text) !== nums(before)) ZS.toast("الصياغة الجديدة غيّرت أرقام، فخليت النص الأصلي");
          else { scriptBox.value = res.text.trim(); count(); ZS.toast("تحسّنت الصياغة بنفس الأرقام"); }
        }
      } catch (e) { ZS.toast("ما گدرت أوصل لـClaude هسه"); }
      improveBtn.disabled = false;
    });

    // ---- saved
    const savedBox = h("div.grid.g-2");
    view.appendChild(ui().section("محفوظاتي", h("div.stack", h("p.small.muted", `مكان الحفظ: ${ZS.store.where()}`), savedBox)));
    function drawSaved() {
      ZS.clear(savedBox);
      const ss = ZS.store.list("stories"), sc = ZS.store.list("scripts"), nt = ZS.store.list("notes");
      savedBox.appendChild(h("div.card", h("h3", "القصص المحفوظة"),
        ss.length ? h("ul.list", ss.map((s, i) => h("li", { style: { display: "block" } },
          h("div.row-between", h("strong", s.title_ar), h("button.icon-btn", { type: "button", "aria-label": "احذفي", onclick: async () => { ss.splice(i, 1); await ZS.store.saveList("stories", ss); drawSaved(); } }, ui().icon("trash"))),
          h("p.small.muted", s.text_ar),
          h("textarea", { rows: 2, placeholder: "ملاحظتج على القصة", "aria-label": "ملاحظة", style: { minHeight: "60px", marginTop: "6px" }, value: s.note || "",
            onchange: async (e) => { ss[i].note = e.target.value; await ZS.store.saveList("stories", ss); ZS.toast("انحفظت الملاحظة"); } })))) : h("p.small.faint", "ماكو قصص محفوظة")));
      savedBox.appendChild(h("div.card", h("h3", "النصوص المحفوظة"),
        sc.length ? h("ul.list", sc.map((s, i) => h("li", { style: { display: "block" } },
          h("div.row-between", h("strong", s.title || "نص"), h("span.tiny.faint", ZS.dateTime(s.created_at))),
          h("p.small.muted", { style: { whiteSpace: "pre-line", maxHeight: "6.5em", overflow: "hidden" } }, s.text),
          h("div.row", h("button.btn.small", { type: "button", onclick: () => { scriptBox.value = s.text; count(); scriptCard.scrollIntoView({ behavior: "smooth" }); } }, ui().icon("edit"), "افتحيه"),
            h("button.btn.small", { type: "button", onclick: () => ui().copyText(s.text) }, ui().icon("copy"), "انسخي"),
            h("button.btn.small.ghost", { type: "button", onclick: async () => { sc.splice(i, 1); await ZS.store.saveList("scripts", sc); drawSaved(); } }, ui().icon("trash"), "احذفي"))))) : h("p.small.faint", "ماكو نصوص محفوظة")));
      const noteIn = h("textarea", { rows: 3, placeholder: "فكرة لفيديو، ملاحظة على مباراة…", "aria-label": "ملاحظة جديدة", style: { minHeight: "80px" } });
      savedBox.appendChild(h("div.card", { style: { gridColumn: "1 / -1" } }, h("h3", "ملاحظاتي"),
        h("div.stack", noteIn, h("div", h("button.btn.small", { type: "button", onclick: async () => { if (!noteIn.value.trim()) return; nt.unshift({ id: "n" + Date.now(), text: noteIn.value.trim(), created_at: new Date().toISOString() }); await ZS.store.saveList("notes", nt); drawSaved(); } }, ui().icon("plus"), "ضيفي الملاحظة"))),
        nt.length ? h("ul.list", nt.map((n, i) => h("li", h("span.grow", { style: { whiteSpace: "pre-line" } }, n.text), h("span.tiny.faint.nowrap", ZS.dateShort(n.created_at)),
          h("button.icon-btn", { type: "button", "aria-label": "احذفي الملاحظة", onclick: async () => { nt.splice(i, 1); await ZS.store.saveList("notes", nt); drawSaved(); } }, ui().icon("trash"))))) : null));
    }
    drawSaved();
    const offPrefs = ZS.on("prefs", () => drawSaved());
    await sync();
    return () => { off(); offPrefs(); };
  }

  // ================================================================== audience challenge
  async function renderChallenge(view) {
    const where = ZS.challenge.where();
    view.appendChild(ui().pageHead("تحدي الجمهور", "توقعي نتائج المباريات قبل صافرة البداية، وشوفي ترتيبك مقابل الجمهور ومقابل الحاسوب.", null, "التحدي"));
    view.appendChild(h("div.notice" + (where.shared ? ".pitch" : ".led"), ui().icon("info"), h("span", where.text + (where.shared ? "" : ". حتى يصير مشترك بين المتابعين: شغّلي الخادم على استضافة عامة (الخطوات بصفحة البيانات والمصادر)."))));
    const grid = h("div.grid.g-main");
    const L = h("div.stack-lg"), R = h("div.stack-lg");
    grid.append(L, R);
    view.appendChild(grid);
    R.appendChild(h("section.card", h("h2", "القواعد"), h("ol.small", { style: { paddingInlineStart: "18px", margin: 0 } }, ZS.challenge.rules.map((r) => h("li", r)))));
    const upcoming = D.fixtures.filter((f) => !f.score && f.kickoff_utc && new Date(f.kickoff_utc) > new Date()).sort((a, b) => a.kickoff_utc.localeCompare(b.kickoff_utc)).slice(0, 10);
    const pickList = h("div.stack");
    L.appendChild(ui().section("توقعي المباريات الجاية", pickList));
    for (const f of upcoming.slice(0, 6)) {
      const mf = await ZS.matchFile(f.match_id).catch(() => null);
      if (mf) pickList.appendChild(ZS.challengeWidget(mf));
    }
    const boardBox = h("div.stack", ui().skeleton(1, 140));
    R.prepend(h("section.card", h("h2", "الترتيب"), boardBox));
    try {
      const picks = await ZS.challenge.picks();
      const b = ZS.challenge.board(picks);
      ZS.clear(boardBox);
      if (!b.total.length) boardBox.appendChild(h("p.small.muted", "الترتيب يبدأ بعد أول مباراة تنتهي وعليها توقعات."));
      else {
        boardBox.appendChild(h("div.tbl-wrap", h("table.tbl", h("thead", h("tr", h("th", "#"), h("th", "المتسابق"), h("th.n", "نقاط"), h("th.n", "مباريات"), h("th.n", "نتيجة بالضبط"))),
          h("tbody", b.total.map((r, i) => h("tr" + (r.player === "الحاسوب" ? ".mine" : ""), h("td.n", String(i + 1)), h("td", r.player), h("td.n", h("strong", String(r.points))), h("td.n", String(r.played)), h("td.n", String(r.exact))))))));
        if (b.weeks[0]) boardBox.appendChild(h("div", h("h3", { style: { marginTop: "10px" } }, `هالأسبوع (${b.weeks[0].week})`),
          h("ol.small", { style: { paddingInlineStart: "18px" } }, b.weeks[0].rows.slice(0, 10).map((r) => h("li", `${r.player}: ${r.points}`)))));
      }
      boardBox.appendChild(h("p.tiny.faint", "«الحاسوب» يلعب بتوقعه المسجل قبل البداية (الأرجح بالفوز/التعادل/الخسارة وأرجح نتيجة)، وينحسب بس بالمباريات اللي عليها توقعات من الجمهور."));
    } catch (e) { ZS.clear(boardBox); boardBox.appendChild(ui().errorCard(e)); }
  }

  ZS.routes.studio = { render, title: "الاستوديو" };
  ZS.routes.challenge = { render: renderChallenge, title: "تحدي الجمهور" };
})();
