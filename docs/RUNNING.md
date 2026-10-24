# التشغيل والتحديث

## 1. التثبيت (مرة وحدة)

يحتاج Python 3.11 أو أحدث (مجرّب على 3.13). اختياري: Node.js 18+ لاختبار حسابات المتصفح.

```bash
cd zahraa-supercomputer
python -m venv .venv && source .venv/bin/activate        # بالويندوز: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium                     # اختياري: لصور بطاقات التقارير المباشرة
cp .env.example .env                                      # اختياري: المفاتيح (شوفي docs/ACTIVATION.md)
```

## 2. تشغيل التطبيق

```bash
python -m zsc serve                 # http://127.0.0.1:8000
python -m zsc serve --port 8080     # منفذ ثاني
```

الخادم يقدّم التطبيق (`app/`) وبياناته (`app/data/`، النسخة الحالية) وواجهة صغيرة:

| الطلب | الوظيفة |
|---|---|
| `GET /api/health` | هل الخادم شغّال |
| `GET /api/status` | حالة البيانات والنسخ المحفوظة وآخر تحديث |
| `POST /api/update` | يبدأ تحديث بالخلفية (نفس `python -m zsc update`) |
| `GET/PUT /api/user/<prefs|stories|notes|scripts>` | الإعدادات والمحفوظات (`data/userdata/`) |
| `GET/POST /api/challenge` | توقعات الجمهور (تنقفل بصافرة البداية) والترتيب |

بدون خادم (فتح الصفحة مباشرة أو من رابط Claude) كل شي يشتغل؛ المحفوظات تنحفظ بالمتصفح (أو بحسابك على Claude).

## 3. التحديث

```bash
python -m zsc update            # يجلب openfootball وfootball-data ← يبني ← نسخة جديدة للتطبيق
python -m zsc update --offline  # بدون جلب (مثلاً بعد ما تضيفين نتيجة بـ data/raw/manual/results_2026_27.csv)
```

شلون يبقى آمن:
- كل ملف خام ينحفظ كما وصل مع وقت الجلب (`data/raw/<المصدر>/_source.json`). إذا مصدر عطّل، يبقى آخر ملف سليم.
- البناء يمر بـ45 فحص (تكرار، تضارب نتائج، قيم مستحيلة، هامش الأسعار، مطابقة الترتيب الرسمي...). إذا فشل فحص،
  البيانات القديمة تبقى، والخطأ ينكتب بـ`data/status.json` ويطلع بصفحة «البيانات والمصادر».
- التطبيق ياخذ نسخة جديدة (`snapshots/<الوقت>`) وتنتقل لـ`app/data` بخطوة وحدة. آخر 20 نسخة تبقى.
- تشغيل التحديث مرتين بنفس البيانات ما يغيّر شي (حتى سجل التوقعات ما يتكرر).

إضافة نتيجة يدوياً (مثلاً من التحليل المباشر): سطر بملف `data/raw/manual/results_2026_27.csv`:
`date,home,away,hg,ag,source` بأسماء الفرق المعتمدة (القائمة بـ`LIVE_RUNBOOK.md`)، ثم `python -m zsc update --offline`.

## 4. النسخ الاحتياطي والاستعادة

| الشي | وين | الاستعادة |
|---|---|---|
| بيانات التطبيق | `snapshots/<stamp>/` | `python -m zsc snapshots` ثم `python -m zsc restore <stamp>` |
| البيانات الموحدة | `data/backups/standard-<الوقت>/` (آخر 5) | انسخي المجلد المطلوب مكان `data/standard/` |
| سجلات التوقعات | `data/predictions/*.csv` (إضافة فقط) | انسخي الملف من نسخة احتياطية |
| محفوظات المستخدم | `data/userdata/` | انسخيها |

نسخة كاملة: `python scripts/package.py` ← `outputs/zahraa-supercomputer.zip` (بدون الكاش اللي ينحمّل من جديد).

## 5. النشر

```bash
python scripts/build_app.py            # dist/web/index.html + dist/web/data/
python scripts/build_app.py --plan     # شنو تغيّر من آخر نشر
python scripts/build_app.py --record   # بعد النشر: سجّلي اللي انرفع
```

`dist/web` ينرفع لأي استضافة ملفات ثابتة (GitHub Pages، Netlify...) أو كرابط Claude. بهالوضع ماكو خادم: تحدي الجمهور
يصير محلي (أو مشترك بين أصحاب الصلاحية برابط Claude). لتحدي مشترك للمتابعين: شغّلي `python -m zsc serve` على خادم
عام (التفاصيل بـ`docs/ACTIVATION.md`).

## 6. التقييم والاختبارات

```bash
python -m pytest -q                       # كل الاختبارات
node tests/js/test_models.js              # حسابات المتصفح مقابل Python
python -m zsc evaluate                    # التقييم الكامل ← reports/evaluation.json وoutputs/models/registry.json
python scripts/test_inplay_signal.py      # هل الشوط الأول يضيف معلومة للمباشر؟
python scripts/sb_players_1516.py         # إحصائيات لاعبي 2015/16 وعدالة التقييم (ينزّل 380 مباراة أول مرة)
python scripts/build_archive.py           # التحليل العميق لمباريات الأرشيف
```

## 7. التحليل المباشر

الخطوات بالضبط بملف `LIVE_RUNBOOK.md`. باختصار: إحصائيات SportRadar بنهاية الشوط ← `scripts/live_run.py` (يقرأ توقع
ما قبل المباراة المسجل، فالدقيقة 0 = التوقع المنشور) ← `python -m zsc export` ← نشر الملفات اللي تغيّرت.

## 8. Colab (بدون تثبيت)

`notebook/Zahraa_Supercomputer.ipynb`: ارفعي ملف المشروع، Run all، ينزل `zahraa_web.zip` جاهز للنشر.
