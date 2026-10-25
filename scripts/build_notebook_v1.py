"""Build the self-contained weekly Colab notebook (notebook/Zahraa_Supercomputer.ipynb).

The notebook embeds the zsc package source, the tuned settings and the
calibrated drift, downloads fresh data, and reruns the full forecast.
"""

from __future__ import annotations

import json
import os

import nbformat as nbf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES = ["__init__", "teams", "data", "dixon_coles", "market", "standings", "simulate",
           "evaluate", "pipeline", "forecast", "online", "dashboard"]


def main():
    import sys
    sys.path.insert(0, ROOT)
    import pandas as pd
    from zsc.dashboard import accuracy_rows

    out = os.path.join(ROOT, "outputs")
    with open(os.path.join(out, "best_config.json")) as f:
        cfg = json.load(f)
    with open(os.path.join(out, "season_backtest.json")) as f:
        sbj = json.load(f)
    drift = sbj["chosen_drift_sd"]
    with open(os.path.join(out, "backtest_report.json")) as f:
        bt = json.load(f)
    sb = {"metrics": sbj["variants"][f"drift_{drift}"], "seasons": sbj["seasons"]}
    accuracy = accuracy_rows(bt, sb, pd.read_csv(os.path.join(out, "backtest_predictions_test.csv")))

    nb = nbf.v4.new_notebook()
    cells = []
    md = nbf.v4.new_markdown_cell
    code = nbf.v4.new_code_cell

    cells.append(md(
        "# حاسوب زهراء الخارق ⚽\n"
        "### موديل توقعات الدوري الإسباني — تحديث أسبوعي\n\n"
        "**طريقة الاستخدام:** من القائمة اختاري **Runtime ← Run all** (أو Ctrl+F9). "
        "التشغيل ياخذ تقريباً دقيقة.\n\n"
        "الموديل يسحب آخر النتائج والأودز من football-data.co.uk، يحسب قوة كل فريق "
        "(Dixon-Coles + توقعات السوق)، يحاكي باقي الموسم 10,000 مرة بقواعد الليغا الرسمية، "
        "ويطلع نسب اللقب، دوري الأبطال، والهبوط، وتوقعات الجولة الجاية.\n\n"
        "**أفضل وقت للتشغيل:** الاثنين أو الثلاثاء بعد نهاية الجولة (الموقع يحدّث النتائج "
        "مرتين بالأسبوع)، أو الجمعة لتوقعات مباريات نهاية الأسبوع مع الأودز.\n\n"
        "في آخر الدفتر ينزل ملف `dashboard_files.zip` — ابعثيه لـClaude حتى تتحدث صفحة النتائج."
    ))
    cells.append(code("!pip -q install arabic-reshaper python-bidi\n!mkdir -p zsc"))
    for mod in MODULES:
        with open(os.path.join(ROOT, "zsc", f"{mod}.py"), encoding="utf-8") as f:
            src = f.read()
        cells.append(code(f"%%writefile zsc/{mod}.py\n{src}"))

    cells.append(md("## الإعدادات\nهاي القيم طلعت من ضبط الموديل على 11 موسم واختباره على 3 مواسم ما شافها. لا تغيرينها إلا إذا تعرفين شتسوين."))
    cells.append(code(
        f"SEASON = 2026          # 2026 = موسم 2026/27\n"
        f"N_SIMS = 10_000        # عدد المواسم المحاكاة\n"
        f"CONFIG = {cfg!r}\n"
        f"DRIFT_SD = {drift}     # تغيّر مستوى الفرق خلال الموسم (مضبوط على التاريخ)\n"
        f"# دقة الموديل المقاسة على مواسم ما شافها (تنعرض بصفحة النتائج)\n"
        f"ACCURACY = {accuracy!r}\n"
    ))

    cells.append(md(
        "## 1) سحب البيانات والتحقق منها\n"
        "إذا آخر مباراة بالبيانات أقدم من آخر جولة (المواقع أحياناً تتأخر يوم أو يومين)، "
        "اكتبي النتائج الناقصة بالمربع `EXTRA_RESULTS` بهذا الشكل، كل مباراة بسطر:\n\n"
        "`2026-10-25, Barcelona, Real Madrid, 2, 1`\n\n"
        "(التاريخ، صاحب الأرض، الضيف، أهداف الأرض، أهداف الضيف). الأسماء بالإنكليزي مثل جدول football-data."
    ))
    cells.append(code(
        "EXTRA_RESULTS = '''\n"
        "'''\n\n"
        "import pandas as pd, numpy as np\n"
        "from zsc.online import load_online, upcoming_fixtures\n"
        "from zsc.data import validate_season\n"
        "from zsc.dixon_coles import DCConfig\n"
        "from zsc.forecast import run_forecast, to_json\n"
        "from zsc.teams import arabic\n"
        "pd.set_option('display.width', 200)\n\n"
        "cfg = DCConfig(**CONFIG)\n"
        "matches = load_online(SEASON, seasons_back=max(cfg.seasons_back, 2), extra_results=EXTRA_RESULTS)\n"
        "cur = matches[matches.season == SEASON]\n"
        "problems = validate_season(cur, n_teams=20)\n"
        "assert not problems, problems\n"
        "print(f'مباريات الموسم الحالي: {len(cur)} — آخر مباراة: {cur.date.max().date()}')\n"
        "print(f'مباريات بيها أودز: {cur.odds_h.notna().sum()} من {len(cur)}')\n"
        "print('✅ البيانات سليمة: 20 فريق، بدون تكرار')"
    ))
    cells.append(code(
        "try:\n"
        "    upcoming = upcoming_fixtures()\n"
        "    print(f'مباريات الجولة الجاية: {len(upcoming)} (منها {upcoming.mkt_lh.notna().sum()} بيها أودز)')\n"
        "except Exception as e:\n"
        "    upcoming = pd.DataFrame(columns=['date','time_uk','home','away','mkt_lh','mkt_la'])\n"
        "    print('ما كدرت أجيب مباريات الجولة الجاية:', e)\n"
        "# keep only fixtures still to be played\n"
        "done = set(zip(cur.home, cur.away))\n"
        "upcoming = upcoming[[(h, a) not in done for h, a in zip(upcoming.home, upcoming.away)]].reset_index(drop=True)\n"
        "upcoming"
    ))

    cells.append(md("## 2) تشغيل الحاسوب الخارق"))
    cells.append(code(
        "# use every match played up to now\n"
        "ref_date = cur.date.max() + pd.Timedelta(days=1)\n"
        "# for the very next matches the betting market's view is used (it knows team news)\n"
        "res = run_forecast(matches, SEASON, ref_date, cfg, DRIFT_SD,\n"
        "                   upcoming=upcoming if len(upcoming) else None, n_sims=N_SIMS,\n"
        "                   overrides=upcoming if len(upcoming) else None)\n"
        "print(f'✅ خلصت المحاكاة: {N_SIMS:,} موسم — البيانات لغاية {cur.date.max().date()}')"
    ))

    cells.append(md("## 3) النتائج"))
    cells.append(code(
        "s = res['summary'].copy()\n"
        "show = pd.DataFrame({\n"
        "    'الفريق': s.team.map(arabic),\n"
        "    'نقاطه الآن': s.pts_now,\n"
        "    'النقاط المتوقعة': s.exp_pts.round(1),\n"
        "    'اللقب %': (100 * s.p_title).round(1),\n"
        "    'أول 4 %': (100 * s.p_top4).round(1),\n"
        "    'أوروبا (أول 6) %': (100 * s.p_top6).round(1),\n"
        "    'الهبوط %': (100 * s.p_releg).round(1),\n"
        "})\n"
        "show.index = range(1, len(show) + 1)\n"
        "show"
    ))
    cells.append(code(
        "if 'next_round' in res:\n"
        "    n = res['next_round'].copy()\n"
        "    tab = pd.DataFrame({\n"
        "        'المباراة': n.home.map(arabic) + ' × ' + n.away.map(arabic),\n"
        "        'فوز الأرض %': (100 * n.p_home).round(0), 'تعادل %': (100 * n.p_draw).round(0),\n"
        "        'فوز الضيف %': (100 * n.p_away).round(0),\n"
        "        'الأهداف المتوقعة': n.xg_home.round(2).astype(str) + ' - ' + n.xg_away.round(2).astype(str),\n"
        "        'النتيجة الأرجح': n.likely_score,\n"
        "    })\n"
        "    if 'mkt_p_home' in upcoming:\n"
        "        tab['السوق: أرض/تعادل/ضيف %'] = [f\"{a:.0f}/{b:.0f}/{c:.0f}\" if pd.notna(a) else '-' for a, b, c in\n"
        "                                       zip(100*upcoming.mkt_p_home, 100*upcoming.mkt_p_draw, 100*upcoming.mkt_p_away)]\n"
        "    display(tab)"
    ))
    cells.append(code(
        "import matplotlib.pyplot as plt\n"
        "import arabic_reshaper\n"
        "from bidi.algorithm import get_display\n"
        "ar = lambda t: get_display(arabic_reshaper.reshape(t))\n"
        "top = s[s.p_title > 0.001].sort_values('p_title')\n"
        "fig, ax = plt.subplots(figsize=(8, 0.5 * len(top) + 1.5))\n"
        "ax.barh([ar(arabic(t)) for t in top.team], 100 * top.p_title, color='#a50044')\n"
        "for y, v in enumerate(100 * top.p_title):\n"
        "    ax.text(v + 0.5, y, f'{v:.1f}%', va='center')\n"
        "ax.set_title(ar('فرصة الفوز باللقب — حاسوب زهراء الخارق'))\n"
        "ax.set_xlim(0, 105); ax.spines[['top', 'right']].set_visible(False)\n"
        "plt.tight_layout(); plt.show()"
    ))

    cells.append(md("## 4) حفظ الملفات\n`dashboard_files.zip` هو الملف اللي تبعثيه حتى تتحدث صفحة النتائج. "
                    "و`forecast_table.csv` جدول تفتحينه بـExcel."))
    cells.append(code(
        "import json, shutil\n"
        "from zsc.dashboard import dashboard_tables, write_tables\n"
        "data = to_json(res)\n"
        "with open('forecast.json', 'w', encoding='utf-8') as f:\n"
        "    json.dump(data, f, ensure_ascii=False, indent=1)\n"
        "write_tables(dashboard_tables(data, ACCURACY), 'dashboard_files')\n"
        "shutil.make_archive('dashboard_files', 'zip', 'dashboard_files')\n"
        "show.to_csv('forecast_table.csv', encoding='utf-8-sig')\n"
        "try:\n"
        "    from google.colab import files\n"
        "    files.download('dashboard_files.zip'); files.download('forecast_table.csv')\n"
        "except Exception:\n"
        "    print('الملفات محفوظة بنفس المجلد: dashboard_files.zip و forecast_table.csv')"
    ))

    nb["cells"] = cells
    nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3"},
                      "language_info": {"name": "python"}, "colab": {"provenance": []}}
    path = os.path.join(ROOT, "notebook", "Zahraa_Supercomputer.ipynb")
    nbf.write(nb, path)
    print("wrote", path)


if __name__ == "__main__":
    main()
