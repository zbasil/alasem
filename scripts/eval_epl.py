"""Walk-forward test of the La Liga model settings on three Premier League seasons (out of sample)."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from zsc import multi
from zsc.market import add_market_goals

t = time.time()
allm, _, _ = multi.epl_matches()
allm = add_market_goals(allm)
res = multi.evaluate_epl(allm)
res["seconds"] = round(time.time() - t, 1)
res["note_ar"] = "إعدادات الموديل مختارة على الليغا فقط، فهذا اختبار خارج العينة بالكامل للبريميرليغ"
os.makedirs("reports", exist_ok=True)
json.dump(res, open("reports/epl_evaluation.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(res, ensure_ascii=False)[:1500])
