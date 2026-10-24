# خط الأساس قبل التطوير (النسخة v1)

سُجّل: 2026-10-24T09:53:13Z UTC

| البند | القيمة |
|---|---|
| الاختبارات | 46 من 46 ناجحة |
| مباريات 2026/27 | 90 (74 بيها أسعار سوق وتسديدات على المرمى، 16 ناقصة) |
| RPS قبل المباراة 2023/24-2025/26 (1,140 مباراة) | الموديل 0.1924 · Bet365 0.1893 |
| Log loss | الموديل 0.9662 · Bet365 0.9554 |
| اختيار النتيجة الصحيحة (فوز/تعادل/خسارة) | الموديل 53.7٪ · Bet365 55.2٪ · دائماً صاحب الأرض 45.8٪ |
| خطأ نقاط نهاية الموسم (14 موسم) | 5.15 نقطة، تغطية مدى 80٪: 82.9٪ (الإعداد مختار على نفس المواسم) |
| توقع الاستراحة 2016/17-2025/26 | RPS 0.1510 (مدخلات السوق، والإعداد مختار على نفس المواسم) |
| فرق ما قبل المباراة والدقيقة صفر | لحد 4.0 نقاط مئوية (أتلتيكو × ديبورتيفو: 69.7٪ مقابل 73.6٪) |

## المشكلات المؤكدة

- 1. 'skill' (91.4%) is a share of the bookmaker's RPS improvement over a baseline, but was labelled as the model's accuracy relative to bookmakers
- 2. RPS baseline uses outcome frequencies of the test matches themselves (in-sample)
- 3. Pre-match (Dixon-Coles with rho) and in-play minute 0 disagree by up to 4.0 points: state multipliers at 0-0 (0.98/0.97 plus strength terms) and no low-score correction
- 4. In-play evaluation used market-implied goals; production used the project's model goals
- 5. In-play variant and season drift were chosen on the same seasons they are reported on
- 6. 'goals_plus_shots' variant equals 'goals_only' (beta_sot was 0 in both)
- 7. Prediction log keyed by team names; no model version, data version or fetch time; no separation of live logs
- 8. 16 of 90 current-season matches lack market odds and shots on target
- 9. Missing live stats were turned into 0 (parse_game_stats)
- 10. App depends on the hosting environment's dashboard runtime ('dash')
