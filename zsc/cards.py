"""Ready-to-post story cards (1080x1920 PNG) rendered with headless Chromium."""

from __future__ import annotations

import html
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "assets", "fonts", "woff2")
HANDLE = "@zahraatalksfootball94"

CSS = """
@font-face{font-family:Cairo;font-weight:400;src:url('file://FD/cairo-arabic-400-normal.woff2') format('woff2');unicode-range:U+0600-06FF,U+200C-200E,U+2010-2011,U+204F,U+2E41,U+FB50-FDFF,U+FE70-FEFC;}
@font-face{font-family:Cairo;font-weight:400;src:url('file://FD/cairo-latin-400-normal.woff2') format('woff2');}
@font-face{font-family:Cairo;font-weight:700;src:url('file://FD/cairo-arabic-700-normal.woff2') format('woff2');unicode-range:U+0600-06FF,U+200C-200E,U+2010-2011,U+204F,U+2E41,U+FB50-FDFF,U+FE70-FEFC;}
@font-face{font-family:Cairo;font-weight:700;src:url('file://FD/cairo-latin-700-normal.woff2') format('woff2');}
@font-face{font-family:Cairo;font-weight:800;src:url('file://FD/cairo-arabic-800-normal.woff2') format('woff2');unicode-range:U+0600-06FF,U+200C-200E,U+2010-2011,U+204F,U+2E41,U+FB50-FDFF,U+FE70-FEFC;}
@font-face{font-family:Cairo;font-weight:800;src:url('file://FD/cairo-latin-800-normal.woff2') format('woff2');}
:root{--bg:#0b1511;--line:rgba(255,255,255,.06);--fg:#f4f6f3;--muted:#9fb2a7;--gold:#e8c468;--home:#2bb673;--away:#4c8df6;--draw:#7d878c;--bad:#ff7a6b}
*{box-sizing:border-box}
body{margin:0;width:1080px;height:1920px;background:var(--bg);color:var(--fg);font-family:Cairo,sans-serif;direction:rtl;overflow:hidden}
.pitch{position:absolute;inset:0;background:
  radial-gradient(circle at 50% 400px, transparent 0 168px, var(--line) 169px 172px, transparent 173px),
  linear-gradient(var(--line),var(--line)) 50% 400px/100% 3px no-repeat,
  repeating-linear-gradient(90deg, rgba(255,255,255,.015) 0 120px, transparent 120px 240px);opacity:.9}
.wrap{position:relative;height:100%;padding:88px 84px 72px;display:flex;flex-direction:column;gap:46px}
.top{display:flex;justify-content:space-between;align-items:center}
.brand{font-weight:800;font-size:40px;letter-spacing:0}
.brand small{display:block;font-weight:400;font-size:26px;color:var(--muted)}
.pill{background:var(--gold);color:#1b1a12;font-weight:800;font-size:32px;padding:10px 30px;border-radius:999px}
.board{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;text-align:center;gap:20px;margin-top:20px}
.team{font-weight:800;font-size:56px;line-height:1.25}
.team.h{color:var(--home)}.team.a{color:var(--away)}
.score{font-weight:800;font-size:190px;line-height:1;display:flex;direction:rtl;gap:28px;align-items:center}
.score .dash{font-size:120px;color:var(--muted)}
.sub{color:var(--muted);font-size:30px;text-align:center;margin-top:-24px}
.prob h3,.points h3{margin:0 0 18px;font-size:34px;font-weight:700;color:var(--gold)}
.bar{display:flex;height:84px;border-radius:18px;overflow:hidden;font-weight:800;font-size:36px}
.bar div{display:flex;align-items:center;justify-content:center;color:#fff;min-width:0;white-space:nowrap}
.legend{display:flex;justify-content:space-between;color:var(--muted);font-size:28px;margin-top:10px}
.points ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:20px}
.points li{font-size:34px;line-height:1.5;padding-right:46px;position:relative}
.points li::before{content:"";position:absolute;right:0;top:20px;width:22px;height:22px;border-radius:50%;background:var(--c)}
.points b{font-weight:800}
.impact{border:2px solid rgba(232,196,104,.45);border-radius:22px;padding:24px 30px;font-size:34px;font-weight:700;line-height:1.5}
.tl h3{margin:0 0 14px;font-size:34px;font-weight:700;color:var(--gold)}
.tl svg{display:block;width:100%;height:300px}
.tl text{font-family:Cairo,sans-serif;font-size:24px;fill:var(--muted)}
.foot{margin-top:auto;display:flex;justify-content:space-between;align-items:flex-end;color:var(--muted);font-size:26px}
.handle{direction:ltr;unicode-bidi:isolate;color:var(--fg);font-weight:800;font-size:38px}
"""


def _e(s) -> str:
    return html.escape(str(s))


def timeline_svg(rep: dict, width: int = 912, height: int = 300) -> str:
    """Stacked win-probability areas over the minutes (home at the bottom), RTL: minute 0 on the right."""
    tl = rep.get("timeline") or []
    if len(tl) < 2:
        return ""
    end = tl[-1]["minute"]
    top, bottom = 10, height - 40
    ph = bottom - top
    xs = lambda m: width - (m / end) * width          # right-to-left
    def pts(lo_key, hi_key):
        up, down = [], []
        for r in tl:
            lo = sum(r[k] for k in lo_key)
            hi = lo + sum(r[k] for k in hi_key)
            up.append(f"{xs(r['minute']):.1f},{bottom - hi * ph:.1f}")
            down.append(f"{xs(r['minute']):.1f},{bottom - lo * ph:.1f}")
        return " ".join(up + down[::-1])
    polys = [
        (pts([], ["p_home"]), "var(--home)"),
        (pts(["p_home"], ["p_draw"]), "var(--draw)"),
        (pts(["p_home", "p_draw"], ["p_away"]), "var(--away)"),
    ]
    shapes = "".join(f'<polygon points="{p}" fill="{c}" fill-opacity=".9"/>' for p, c in polys)
    ticks = ""
    for m in (0, 45, 90):
        if m <= end:
            x = xs(m)
            anchor = "end" if x > width - 40 else ("start" if x < 40 else "middle")
            ticks += (f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{top}" y2="{bottom}" stroke="#0b1511" stroke-width="3"/>'
                      f'<text x="{x:.1f}" y="{height - 6}" text-anchor="{anchor}" direction="ltr">{m}\'</text>')
    goals = ""
    for e in rep.get("events", []):
        if e["kind"] == "goal" and e["minute"] <= end:
            goals += (f'<line x1="{xs(e["minute"]):.1f}" x2="{xs(e["minute"]):.1f}" y1="{top}" y2="{bottom}" '
                      f'stroke="#fff" stroke-width="3" stroke-dasharray="8 6"/>')
    return (f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none">{shapes}{ticks}{goals}</svg>')


def card_html(rep: dict, data_credit: str = "بيانات: SportRadar", subtitle: str = "تحليل مباشر للدوري الإسباني",
              pill: str | None = None) -> str:
    h, a = rep["home_ar"], rep["away_ar"]
    phase = pill or ("الشوط الأول" if rep["phase"] == "HT" else "نهاية المباراة")
    p = rep["now"]["p"] if rep["phase"] == "HT" else rep["pre_match"]["p"]
    prob_title = "فرصة الفوز حسب الموديل الآن" if rep["phase"] == "HT" else "توقع الموديل قبل المباراة"
    seg = []
    for val, col in ((p[0], "var(--home)"), (p[1], "var(--draw)"), (p[2], "var(--away)")):
        label = f"{100 * val:.0f}%" if val >= 0.09 else ""
        seg.append(f'<div style="width:{100 * val:.2f}%;background:{col}">{label}</div>')
    pts = []
    ins = rep["insights"]
    for side, nm, col in (("home", h, "var(--home)"), ("away", a, "var(--away)")):
        if ins[side]["pos"]:
            pts.append((col, nm, ins[side]["pos"][0]))
    for side, nm in (("home", h), ("away", a)):
        if ins[side]["neg"]:
            pts.append(("var(--bad)", nm, ins[side]["neg"][0]))
    extra = [n for n in rep.get("notes", []) if "←" not in n and not n.startswith("حسب")]
    for n in extra:
        if len(pts) >= 4:
            break
        pts.append(("var(--gold)", "", n))
    items = "".join(f'<li style="--c:{c}">' + (f'<b>{_e(nm)}:</b> ' if nm else '') + f'{_e(t)}</li>'
                    for c, nm, t in pts[:4])
    impact = ""
    for n in rep.get("notes", []):
        if "فرصة" in n and ("ب" in n) and "←" in n:
            impact = f'<div class="impact">{_e(n)}</div>'
            break
    sub = ""
    if rep["phase"] == "HT":
        sub = f'<div class="sub">النتيجة الأرجح بالنهاية {_e(rep["now"]["likely_final"])}</div>'
    css = CSS.replace("FD", FONT_DIR)
    return f"""<!doctype html><html lang="ar"><head><meta charset="utf-8"><style>{css}</style></head>
<body><div class="pitch"></div><div class="wrap">
<div class="top"><div class="brand">حاسوب زهراء الخارق<small>{_e(subtitle)}</small></div><div class="pill">{_e(phase)}</div></div>
<div class="board"><div class="team h">{_e(h)}</div><div class="score"><span>{rep['score'][0]}</span><span class="dash">-</span><span>{rep['score'][1]}</span></div><div class="team a">{_e(a)}</div></div>
{sub}
<div class="prob"><h3>{prob_title}</h3><div class="bar">{''.join(seg)}</div>
<div class="legend"><span>فوز {_e(h)}</span><span>تعادل</span><span>فوز {_e(a)}</span></div></div>
<div class="points"><h3>أبرز النقاط</h3><ul>{items}</ul></div>
{impact}
<div class="tl"><h3>مسار فرصة الفوز دقيقة بدقيقة</h3>{timeline_svg(rep)}</div>
<div class="foot"><div>{_e(data_credit)}<br>الاحتمالات من موديل حاسوب زهراء الخارق</div><div class="handle">{HANDLE}</div></div>
</div></body></html>"""


def render_card(rep: dict, out_png: str, data_credit: str = "بيانات: SportRadar",
                subtitle: str = "تحليل مباشر للدوري الإسباني", pill: str | None = None) -> str:
    from playwright.sync_api import sync_playwright
    page_html = card_html(rep, data_credit, subtitle, pill)
    tmp = out_png[:-4] + ".html"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(page_html)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto("file://" + os.path.abspath(tmp))
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(250)
        pg.screenshot(path=out_png)
        b.close()
    os.remove(tmp)
    return out_png
