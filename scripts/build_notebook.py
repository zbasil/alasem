"""Build the weekly Colab notebook (notebook/Zahraa_Supercomputer.ipynb), version 2.

The notebook runs the project itself (no copied code): upload the project ZIP, install the pinned requirements,
run one safe update (fetch sources -> data checks -> app snapshot), look at the main numbers, and download the
updated web page (dist/web) ready to publish. The version-1 notebook is kept in notebook/archive/.
"""

from __future__ import annotations

import os

import nbformat as nbf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    nb = nbf.v4.new_notebook()
    md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
    nb.cells = [
        md("# حاسوب زهراء الكروي: التحديث الأسبوعي (النسخة 2)\n\n"
           "1. Runtime ← Run all.\n2. لما يطلب، ارفعي ملف المشروع `zahraa-supercomputer.zip`.\n"
           "3. بالنهاية ينزل `zahraa_web.zip`: الصفحة والبيانات الجديدة، جاهزة للنشر (ابعثيها لـClaude أو ارفعيها لأي استضافة).\n\n"
           "التحديث آمن: إذا مصدر عطّل، تبقى آخر بيانات سليمة؛ وإذا فشل فحص البيانات، ما يتغير شي."),
        code("from google.colab import files\nimport zipfile, os\nup = files.upload()\nname = next(iter(up))\n"
             "zipfile.ZipFile(name).extractall('.')\nos.chdir('zahraa-supercomputer')\nprint('المشروع جاهز:', os.getcwd())"),
        code("!pip -q install numpy==2.5.3 pandas==3.0.5 scipy==1.18.1\nimport numpy, pandas, scipy\nprint('numpy', numpy.__version__, '· pandas', pandas.__version__, '· scipy', scipy.__version__)"),
        code("!python -m zsc update"),
        code("import json, pandas as pd\nmeta = json.load(open('app/data/meta.json'))\n"
             "print('آخر تحديث:', meta['generated_utc'], '· البيانات', meta['versions']['data'])\n"
             "fx = pd.DataFrame(json.load(open('app/data/fixtures.json'))['fixtures'])\n"
             "teams = json.load(open('app/data/teams.json'))['teams']\n"
             "up = fx[fx['score'].isna() & fx['p'].notna()].sort_values('kickoff_utc').head(10).copy()\n"
             "up['المباراة'] = up.apply(lambda r: f\"{teams[r.home]['ar']} × {teams[r.away]['ar']}\", axis=1)\n"
             "up[['فوز الأرض', 'تعادل', 'فوز الضيف']] = pd.DataFrame(up['p'].tolist(), index=up.index).mul(100).round(0)\n"
             "display(up[['المباراة', 'kickoff_utc', 'فوز الأرض', 'تعادل', 'فوز الضيف']])"),
        code("s = json.load(open('app/data/season.json'))\nt = pd.DataFrame(s['projection'])\n"
             "t['الفريق'] = t['id'].map(lambda i: teams[i]['ar'])\n"
             "cols = {'exp_pts': 'النقاط المتوقعة', 'p_title': 'اللقب', 'p_ucl': 'الأبطال', 'p_releg': 'الهبوط'}\n"
             "t = t.sort_values('exp_pts', ascending=False)[['الفريق'] + list(cols)].rename(columns=cols)\n"
             "for c in ['اللقب', 'الأبطال', 'الهبوط']: t[c] = (100 * t[c]).round(1)\n"
             "display(t.round(1))"),
        code("!python scripts/build_app.py\nimport shutil\nshutil.make_archive('zahraa_web', 'zip', 'dist/web')\nfiles.download('zahraa_web.zip')"),
    ]
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3"}
    path = os.path.join(ROOT, "notebook", "Zahraa_Supercomputer.ipynb")
    nbf.write(nb, path)
    print("wrote", path)


if __name__ == "__main__":
    main()
