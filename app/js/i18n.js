/* i18n.js (version 3.1): English interface.
   Arabic stays the source language of the code. In English mode this layer
   - switches direction, language, dates and numbers (core.js reads ZS.lang),
   - gives every team its English name at the source (core.js team()),
   - translates interface text as it is drawn: exact phrases first, then patterns with placeholders
     ({1}, {2}...: numbers, team names or nested phrases, translated in turn).
   Arabic-only by design: the content studio's Iraqi-dialect scripts and Reel scripts (they are the product). */
(function () {
  "use strict";
  const ZS = window.ZS;

  const EXACT = {
    // navigation and shell
    "حاسوب زهراء الكروي": "Zahraa Football Supercomputer", "حاسوب زهراء": "Zahraa Supercomputer",
    "المباريات": "Matches", "الأخبار": "News", "البطولات": "Competitions", "الترتيب": "Standings", "المزيد": "More",
    "التنبيهات": "Alerts", "الاستوديو": "Studio", "مختبر التحقق": "Claim lab", "ملخص اليوم (لاليغا)": "Today (La Liga)",
    "ملخص اليوم": "Today", "موسم الليغا": "La Liga season", "فرق الليغا": "La Liga teams", "المنهجية والدقة": "Methodology & accuracy",
    "البيانات والمصادر": "Data & sources", "تحدي الجمهور": "Fan challenge", "أرشيف التحليل العميق": "Deep-analysis archive",
    "الأرشيف العميق": "Deep archive", "اللاعبين (أرشيف)": "Players (archive)", "اللاعبين": "Players", "الإعدادات": "Settings",
    "الأقسام": "Sections", "الأقسام الرئيسية": "Main sections", "روابط إضافية": "More links", "الصفحة الرئيسية": "Home",
    "حاسوب زهراء الكروي: الصفحة الرئيسية": "Zahraa Football Supercomputer: home", "سد": "Close",
    "حالة البيانات والمصادر ←": "Data status & sources →", "كيف نقيس الدقة": "How we measure accuracy",
    "الوضع: معاينة بالمتصفح": "Mode: browser preview", "الوضع: خادم محلي": "Mode: local server", "الوضع: رابط Claude": "Mode: Claude link",
    "مصادر مجانية: openfootball · football-data.co.uk (عبر GitHub) · ClubElo (عبر xgabora) · SportRadar عبر Claude · StatsBomb Open Data":
      "Free sources: openfootball · football-data.co.uk (via GitHub) · ClubElo (via xgabora) · SportRadar via Claude · ESPN (live) · StatsBomb Open Data",
    "جاري تحميل البيانات…": "Loading data…", "وصل تحديث جديد للبيانات": "New data arrived",
    "آخر تحديث للبيانات فشل؛ التطبيق يعرض آخر نسخة سليمة. التفاصيل بصفحة البيانات.": "The last data update failed; the app shows the last good version. Details on the data page.",
    "قبل لحظات": "just now", "بعد يومين": "in 2 days",
    // matches page
    "لاليغا والبريميرليغ ودوري الأبطال بيوم واحد، وتحت كل مباراة توقع الحاسوب": "La Liga, Premier League and Champions League on one day, with the model's forecast under every match",
    "اليوم": "Today", "أمس": "Yesterday", "باجر": "Tomorrow",
    "الأحد": "Sun", "الاثنين": "Mon", "الثلاثاء": "Tue", "الأربعاء": "Wed", "الخميس": "Thu", "الجمعة": "Fri", "السبت": "Sat",
    "الكل": "All", "المفضلة": "Favourites", "انتهت": "Finished", "قادمة": "Upcoming", "مباشر": "Live", "استراحة": "Half-time",
    "بانتظار النتيجة": "Awaiting result", "مؤجلة": "Postponed", "ملغاة": "Cancelled", "موقوفة مؤقتاً": "Suspended", "أُوقفت": "Abandoned",
    "متأخرة البداية": "Delayed", "استراحة · تقديري": "HT · est.", "بدأت · تقديري": "Started · est.",
    "انتهت · مباشر": "FT · live", "انتهت · ✓": "FT · ✓", "بتوقيت بغداد": "Baghdad time", "تقديري، بدون بيانات مباشرة": "Estimated, no live data",
    "بحث عن فريق": "Search teams", "اختاري يوم": "Pick a day", "التقويم": "Calendar", "ابحثي عن فريق…": "Search a team…",
    "ابحثي عن فريق": "Search a team", "الأيام": "Days", "تصفية": "Filter",
    "النتائج المباشرة تنعرض أول ما يشتغل التحديث التلقائي": "Live scores appear once the automatic update runs",
    "ماكو فريق بهالاسم بالبطولات الثلاث": "No team with that name in the three competitions", "ماكو مباراة جارية هسه": "No match is live right now",
    "ماكو مباريات بهاليوم ضمن البطولات المعروضة": "No matches on this day in the shown competitions",
    "الشريط تحت كل مباراة = توقع الحاسوب (فوز صاحب الأرض · تعادل · فوز الضيف). لاليغا بموديلها الكامل؛ البريميرليغ بنفس الموديل؛ دوري الأبطال بتقييم Elo.":
      "The bar under each match is the model's forecast (home win · draw · away win). La Liga uses the full model, the Premier League the same model, the Champions League Elo ratings.",
    "الدوري الإسباني": "LaLiga", "لاليغا": "LaLiga", "الدوري الإنجليزي الممتاز": "Premier League", "البريميرليغ": "Premier League",
    "الدوري الإنجليزي": "Premier League", "دوري أبطال أوروبا": "UEFA Champions League", "دوري الأبطال": "Champions League",
    "الدوري الأوروبي": "Europa League", "المؤتمر": "Conference League", "دوري المؤتمر الأوروبي": "Conference League",
    "شيلي لاليغا من المفضلة": "Remove LaLiga from favourites",
    // live layer
    "ماكو بيانات مباشرة بعد": "No live data yet", "تعذّر جلب البيانات المباشرة": "Live data could not be fetched",
    "هدف": "Goal", "هدف من ضربة جزاء": "Penalty goal", "هدف بالخطأ": "Own goal", "طرد": "Red card", "طرد (إنذار ثاني)": "Red card (second yellow)",
    "إنذار": "Yellow card", "تبديل": "Substitution", "ضربة جزاء ضائعة": "Penalty missed", "مراجعة الفيديو": "VAR review", "حدث": "Event",
    "بدأت المباراة": "Kick-off", "الهدف انلغى": "Goal ruled out", "نهاية الشوط الأول": "Half-time", "نهاية المباراة": "Full-time",
    "الاستحواذ": "Possession", "التسديدات": "Shots", "على المرمى": "On target", "الركنيات": "Corners", "الأخطاء": "Fouls", "التسلل": "Offsides",
    "الإنذارات": "Yellow cards", "الطرد": "Red cards", "تصديات الحارس": "Saves", "تمريرات صحيحة": "Accurate passes", "التمريرات": "Passes",
    "دقة التمرير": "Pass accuracy", "الافتكاك": "Tackles", "قطع الكرة": "Interceptions", "الأحداث": "Events", "الأرقام": "Stats",
    "المصدر: ESPN": "Source: ESPN", "التشكيلة الرسمية": "Confirmed line-ups", "التشكيلة المعلنة قبل المباراة": "Line-ups announced before kick-off",
    "التشكيلة على الملعب": "Line-ups on the pitch", "الاحتياط": "Substitutes", "↑ دخل": "↑ on", "↓ طلع": "↓ off",
    "مواقع اللاعبين حسب الخطة المعلنة وترتيبها، مو بيانات تتبع.": "Positions follow the announced formation, not tracking data.",
    "التشكيلات تنزل عادة قبل البداية بساعة، والتطبيق يجيبها أول ما تنعلن.": "Line-ups usually come an hour before kick-off; the app shows them as soon as they are announced.",
    "ماكو أحداث مسجلة بالمصدر لحد هسه": "No events recorded by the source yet", " · انلغى أو انسحب من المصدر": " · ruled out or withdrawn by the source",
    "الأحداث والتشكيلات والأرقام المباشرة تظهر هنا من ESPN أول ما يجلبها التحديث التلقائي (قبل البداية بساعة وخلال المباراة).":
      "Live events, line-ups and stats from ESPN appear here as soon as the automatic update fetches them (an hour before kick-off and during the match).",
    "مباشر من ESPN": "Live from ESPN", "إشعارات المباريات المباشرة": "Live match notifications", "مرفوضة من المتصفح": "Blocked by the browser",
    "غير مدعومة بهذا المتصفح": "Not supported in this browser", "طافية": "Off", "ضيفي فريق مفضل": "add a favourite team",
    "طفيت إشعارات المباريات": "Match notifications turned off", "هذا المتصفح ما يدعم الإشعارات": "This browser does not support notifications",
    "الإذن مرفوض من المتصفح": "Permission denied by the browser",
    // match page
    "صاحب الأرض": "Home", "الضيف": "Away", "توقع الحاسوب": "Model forecast", "شنو كان يتوقع الحاسوب": "What the model expected", "تعادل": "Draw",
    "النتيجة الأرجح": "Most likely score", "ليش هالتوقع؟": "Why this forecast?", "ميزة الأرض بالبريميرليغ (عامة)": "Home advantage, Premier League (league-wide)",
    "ميزة الأرض بدوري الأبطال (عامة)": "Home advantage, Champions League (general)", "المواجهات السابقة": "Head-to-head",
    "افتحيها بمختبر التحقق ←": "Open in the claim lab →",
    "سجل المواجهات متوفر لمباريات الدوري الإسباني والإنجليزي بس. دوري الأبطال ما عنده أرشيف نتائج بالمصادر المجانية الحالية.":
      "Head-to-head records cover LaLiga and the Premier League only; the free sources have no Champions League results archive yet.",
    "مباريات الدوري فقط (بدون الكأس والسوبر والبطولات الأوروبية)": "League matches only (no cups, Super Cups or European games)",
    "توقع بأثر رجعي (الموديل الحالي على مباراة انلعبت)؛ السجل الحي للبريميرليغ يبدأ من هسه · الاحتمال الأرجح ما صاب": "Retro forecast (today's model on a played match); the live Premier League log starts now · the favourite did not win",
    "توقع بأثر رجعي بتقييم Elo قبل المباراة · الاحتمال الأرجح صاب ✓": "Retro forecast from pre-match Elo · the favourite won ✓",
    "توقع بأثر رجعي بتقييم Elo قبل المباراة · الاحتمال الأرجح ما صاب": "Retro forecast from pre-match Elo · the favourite did not win",
    "توقع بأثر رجعي (الموديل الحالي على مباراة انلعبت)؛ السجل الحي للبريميرليغ يبدأ من هسه · الاحتمال الأرجح صاب ✓": "Retro forecast (today's model on a played match); the live Premier League log starts now · the favourite won ✓",
    "تابعي وثبّتي": "Follow & pin", "متابَعة ومثبّتة": "Followed & pinned", "قبل المباراة": "Pre-match", "مدعوم بالسوق": "Market-informed",
    "مستقل (بدون السوق)": "Independent (no market)", "الملخص": "Summary", "الملعب": "Pitch",
    "أكبر الأسباب أولاً. الأرقام هي مدخلات الموديل نفسها (قوة الهجوم والدفاع وميزة الأرض)، مو كلام عام.": "Biggest reasons first. The numbers are the model's own inputs (attack, defence, home advantage), not general talk.",
    "الشريط يبين حجم أثر كل سبب على الأهداف المتوقعة وباتجاه أي فريق. اضغطي على أي سبب للتفاصيل.": "Each bar shows how much a reason moves the expected goals and towards which team. Tap a reason for details.",
    "أرجح النتائج الرقمية": "Most likely scores", "النتيجة الرقمية أصعب بكثير من الفائز": "An exact score is much harder than the winner",
    "شنو تغيّر بالتوقع؟": "What changed in the forecast?", "انضافت نتائج أو بيانات جديدة (نسخة بيانات جديدة)": "New results or data were added (new data version)",
    "حساب دقيق (بدون محاكاة)، فأي فرق هو تغيير حقيقي بالمدخلات": "Exact calculation (no simulation), so any difference is a real change in the inputs",
    "أول نسخة مسجلة": "First recorded version", "شنو تعني للموسم؟": "What it means for the season", "الفرصة": "Chance",
    "جربي «ماذا لو؟» بصفحة الموسم ←": "Try “What if?” on the season page →", "توقعك أنتِ؟": "Your prediction?", "الترتيب والقواعد ←": "Leaderboard & rules →",
    "محلي: توقعاتك محفوظة بهذا المتصفح بس": "Local: your picks are saved in this browser only",
    "النتيجة بالأرقام (اختياري، نقطتين إضافيتين):": "Exact score (optional, 2 extra points):", "سجّلي توقعي": "Save my pick",
    "المصدر والبيانات": "Source & data", "إصدار الموديل": "Model version", "نسخة البيانات": "Data version", "وقت التوقع": "Forecast time",
    "معرّف SportRadar": "SportRadar id", "معرّف المباراة الثابت": "Stable match id", "بيانات ناقصة مهمة": "Important missing data",
    "التشكيلات والغيابات غير متوفرة بالمصادر المجانية: التوقع ما يعرف منو راح يلعب": "Line-ups and absences are not in the model's inputs: the forecast does not know who will play",
    "مصدر التوقع": "Forecast source", "أقسام المباراة": "Match sections", "اختيارك": "Your pick", "اسمك بالترتيب": "Your name on the leaderboard",
    "خريطة النتائج المحتملة": "Score probability map", "التشكيلات والمواقع": "Line-ups & positions", "تحتاج تفعيل: مصدر تشكيلات": "Needs a line-up source",
    "شوفي شنو يحتاج تفعيل": "See what needs enabling", "أمثلة كاملة من أرشيف StatsBomb": "Full examples from the StatsBomb archive",
    "احتمال كل نتيجة": "Probability of each score", "مقارنة المصادر": "Source comparison", "المصدر": "Source", "الأهداف المتوقعة": "Expected goals",
    "الخصم": "Opponent", "النتيجة": "Result", "المتوقع قبلها": "Expected before", "مدخلات الموديل": "Model inputs", "المدخل": "Input", "القيمة": "Value",
    "المعنى": "Meaning", "ميزة الأرض": "Home advantage", "عامة لكل فرق الدوري": "Same for every team in the league", "تصحيح النتائج القليلة (rho)": "Low-score correction (rho)",
    "عدد المباريات بالتدريب": "Matches in training", "مع وزن أكبر للمباريات الأحدث": "Recent matches weigh more",
    "الأهداف المتوقعة = معدل الدوري × هجوم الفريق × دفاع الخصم (× ميزة الأرض لصاحب الأرض).": "Expected goals = league average × team attack × opponent defence (× home advantage for the home side).",
    "الأحداث تظهر هنا وقت المباراة: الأهداف والطرد واحتمالات الفوز دقيقة بدقيقة.": "Events appear here during the match: goals, red cards and win probabilities minute by minute.",
    "ماذا لو؟ داخل المباراة": "In-match what-if", "سيناريو": "Scenario", "سيناريو تجريبي، مو التوقع الرسمي": "Hypothetical scenario, not the official forecast",
    "الدقيقة": "Minute", "إعادة ضبط": "Reset", "احتمالات السيناريو": "Scenario probabilities", "توقع استرجاعي": "Retro forecast",
    "التوقع مقابل النتيجة": "Forecast vs result", "ملاحظة": "Note", "مدعوم بالسوق (استرجاعي)": "Market-informed (retro)",
    "مستقل (بدون السوق) (استرجاعي)": "Independent (retro)", "للمقارنة": "For comparison",
    "الخانة المظللة هي اللي صارت. التوقع الاسترجاعي يعيد حساب المباراة بنفس الموديل وبيانات ما قبل أسبوعها، فهو عادل بس مو منشور وقتها.": "The shaded cell is what happened. A retro forecast recomputes the match with the same model and only data from before its week: fair, but not published at the time.",
    "تأثير النتيجة صار جزء من صفحة الموسم.": "The result's impact is now part of the season page.", "حقائق المباراة": "Match facts", "الأهداف": "Goals",
    "أهداف الشوط الأول": "First-half goals", "التسديدات على المرمى": "Shots on target", "ضيفيه للمفضلة": "Add to favourites", "مفضل ✓": "Favourite ✓",
    "البطولة ←": "Competition →", "نقاط متوقعة": "Expected points", "الهبوط": "Relegation", "الخروج": "Out", "الجاية": "Next", "آخر النتائج": "Latest results",
    // competitions / standings / season
    "سباق اللقب": "Title race", "حظوظ اللقب": "Title chances", "معركة البقاء": "Relegation fight", "احتمال الهبوط": "Relegation chance",
    "مين ياخذ الأبطال؟": "Who wins the Champions League?", "كبار بخطر": "Giants in danger", "احتمال الخروج": "Elimination chance", "مفاجأة": "Upset",
    "احتمالها قبل المباراة": "Its pre-match probability", "قمة قادمة": "Big match ahead", "مباراة تحسم": "Decisive match", "تغيّر بالتوقع": "Forecast shift",
    "سلسلة": "Streak", "سباق": "Race", "رقم": "Record", "قصة": "Story", "التفاصيل": "Details", "اصنعي بطاقة": "Make a card",
    "قصص من أرقام الحاسوب نفسه، كل قصة بدليلها وجاهزة تصير محتوى": "Stories drawn from the model's own numbers, each with its evidence and ready to become content",
    "تصفية حسب الفريق": "Filter by team", "ماكو قصص لهالفريق هسه": "No stories for this team right now", "قصص أخرى": "More stories",
    "عناوين من مصادر خارجية": "Headlines from other sources", "مؤشر الأهمية": "Importance index", "النقاط الفعلية": "Actual points",
    "سباق اللقب بالأرقام": "The title race in numbers", "فرصة اللقب": "Title chance", "xA + xG بدون جزاء": "xA + non-penalty xG", "xG الشوط الأول ← الثاني": "xG first half → second",
    "النجمة = مفضلة (تطلع أول)، والأسهم ترتب، والعين تخفي البطولة من صفحة المباريات": "Star = favourite (shown first), arrows reorder, the eye hides a competition from Matches",
    "كل البطولات": "All competitions", "المخفية": "Hidden",
    "بطولات ثانية (الدوري الألماني، الإيطالي…) ممكن تنضاف بنفس الطريقة المجانية؛ شوفي اقتراح النسخة القادمة بصفحة البيانات.": "More leagues (Bundesliga, Serie A…) can be added the same free way; see the roadmap on the data page.",
    "نقاط": "Pts", "أول 8": "Top 8", "ملحق": "Play-off", "خروج": "Out", "اللقب": "Title", "متوقع": "Expected", "أول 4": "Top 4", "هبوط": "Relegated",
    "الأبطال": "UCL", "الفريق": "Team", "المتصدر": "Leader", "المرشح للقب": "Title favourite", "انلعبت": "Played", "محاكاة": "Simulations",
    "مرة لبقية الموسم": "runs of the rest of the season", "حظوظ الموسم": "Season chances", "الترتيب ←": "Standings →", "كل الجولة ←": "Whole round →",
    "كيف انحسبت": "How it was calculated", "الموسم الكامل وماذا لو؟": "Full season & what-if", "الفرق": "Teams",
    "الموديل الكامل: مساران، سجل توقعات، تحليل مباشر": "Full model: two tracks, forecast log, live analysis",
    "الترتيب الحالي، أو المتوقع بنهاية الموسم من المحاكاة": "Current table, or the projected final table from the simulation",
    "الحالي": "Current", "المتوقع": "Projected", "لعب": "P", "ف": "W", "ت": "D", "خ": "L", "فوز": "Win", "خسارة": "Loss", "البطولة": "Competition",
    "نوع الترتيب": "Table type", "دور الـ16 مباشرة": "Straight to round of 16", "الملحق": "Play-off", "مقعد خامس محتمل": "Possible fifth place",
    "كسر التعادل: المواجهات المباشرة أولاً ثم فارق الأهداف (قواعد الليغا)": "Tie-break: head-to-head first, then goal difference (LaLiga rules)",
    "المواجهات المباشرة أولاً ثم فارق الأهداف (قواعد الليغا)": "Head-to-head first, then goal difference (LaLiga rules)", "النقاط ثم فارق الأهداف": "Points, then goal difference",
    "ما ينحسب بعد: نتائج الدوريات المحلية بعد 1 أيلول للأندية الأوروبية (مخطط بالنسخة القادمة).": "Not counted yet: domestic league results after 1 September for European clubs (planned).",
    "الموسم": "Season", "التوقع": "Forecast", "الترتيب الآن": "Table now", "ماذا لو؟": "What if?", "أهم المباريات": "Key matches", "القواعد": "Rules",
    "الآن": "Now", "المدى": "Range", "فاز": "Won", "خسر": "Lost", "له": "For", "عليه": "Against", "الفارق": "GD", "النقاط": "Points",
    "سيناريو تجريبي منفصل عن التوقع الرسمي": "Hypothetical scenario, separate from the official forecast",
    "ما اخترتي أي نتيجة بعد": "No result picked yet", "احسبي السيناريو": "Run the scenario", "الجولة": "Round",
    "ترتيب المباريات الجاية حسب أثرها على السباق": "Upcoming matches ranked by their effect on the races", "رتّبي أي جولة": "Rank any round",
    "قواعد الموسم": "Season rules", "مؤشر الأهمية:": "Importance index:", "قصة تستاهل النشر": "A story worth posting", "كل القصص ←": "All stories →",
    "سوّي منها بطاقة ونص": "Make a card and a script", "احفظها": "Save it", "الموسم كامل ←": "Full season →", "خطر الهبوط": "Relegation danger",
    "دقة الحاسوب": "Model accuracy", "المنهجية كاملة ←": "Full methodology →", "اختيار النتيجة (فوز/تعادل/خسارة)": "Outcome pick (win/draw/loss)",
    "يبدأ يتحسب بعد أول مباريات مسجلة": "Counted after the first logged matches", "مباريات اليوم": "Today's matches", "كل مباريات الجولة ←": "All matches of the round →",
    "جارية": "In play", "النتائج كاملة ←": "All results →", "✗ الأرجح ما صار": "✗ favourite did not win", "✓ الأرجح صار": "✓ favourite won",
    "تنبيه: محاكاة: الفرق الصغير (أقل من نقطتين) ممكن يكون ضجيج": "Note: simulation: small differences (under 2 points) may be noise",
    "ماكو تحديث سابق للمقارنة بعد، أو ما تغيّر شي يذكر.": "No previous update to compare with yet, or nothing notable changed.",
    // team pages
    "فرصه بالموسم": "Season chances", "النقاط المتوقعة بالنهاية": "Expected final points", "المستوى الحقيقي": "True level", "النتائج مقابل المستوى": "Results vs level",
    "المتوقعة قبل المباريات": "Expected before matches", "الأهداف مقابل المتوقع": "Goals vs expected", "سجّل / المتوقع له": "Scored / expected",
    "استقبل / المتوقع عليه": "Conceded / expected", "تسديدات على المرمى له / عليه": "Shots on target for / against", "الفورمة والاتجاه": "Form & trend",
    "اتجاه المستوى (تقييم الموديل الأسبوعي)": "Level trend (weekly model rating)", "الهجوم": "Attack", "الدفاع (أقل = أحسن)": "Defence (lower = better)",
    "الهجوم والدفاع، بالأرض وخارجها": "Attack & defence, home and away", "قوة الهجوم والدفاع حسب الموديل": "Attack and defence strength (model)", "المسار": "Track",
    "الدفاع": "Defence", "بالأرض وخارجها": "Home & away", "له–عليه": "For–against", "نقاط/مباراة": "Pts/match", "بالأرض": "Home", "خارج الأرض": "Away",
    "المباريات الجاية وصعوبتها": "Upcoming matches & difficulty", "الغيابات": "Absences", "التاريخ": "Date", "فوزه قبلها": "Win chance before",
    "المتوقع له–عليه": "Expected for–against", "توزيع المراكز المتوقعة": "Projected positions", "تقييم الهجوم والدفاع أسبوع بأسبوع": "Attack & defence rating week by week",
    "جمع نقاط أكثر من المتوقع بوضوح: فعالية أو حظ، والعينة لسه صغيرة.": "Clearly more points than expected: efficiency or luck, and the sample is still small.",
    "«المتوقع» هنا أهداف ما قبل المباراة من الموديل، مو xG الفرص (xG الفرص يحتاج بيانات أحداث).": "“Expected” here means the model's pre-match goals, not chance xG (that needs event data).",
    "الأهداف المتوقعة هنا هي توقع ما قبل المباراة من الموديل، مو xG الفرص": "Expected goals here are the model's pre-match forecast, not chance xG",
    "أيام الراحة محسوبة من مباريات الدوري بس (الكأس والمباريات الأوروبية غير متوفرة)": "Rest days count league matches only (cup and European fixtures are not available)",
    "الغيابات تحتاج مصدر تشكيلات (API-Football): غير مفعّل. الخطوات بملف docs/ACTIVATION.md": "Absences need a line-up source (API-Football): not enabled. Steps in docs/ACTIVATION.md",
    // more / settings
    "اللغة": "Language", "العربية": "العربية", "المظهر": "Theme", "ليلي": "Dark", "نهاري": "Light", "حسب الجهاز": "System", "حجم الخط": "Text size",
    "صغير": "Small", "متوسط": "Medium", "كبير": "Large", "توقيت المباريات": "Match times", "ترتيب البطولات وإخفاؤها": "Order & hide competitions",
    "البيانات والمصادر المجانية": "Data & free sources", "إعدادات أكثر (الفرق المفضلة، بياناتي)": "More settings (favourite teams, my data)",
    "معاينة بالمتصفح": "Browser preview", "خادم محلي": "Local server", "رابط Claude": "Claude link",
    "العرض": "Display", "داكن": "Dark", "فاتح": "Light", "التوقع المعروض بمركز المباراة": "Forecast shown in the match centre", "الافتراضي": "Default",
    "تقليل الحركة": "Reduce motion", "يوقف الحركات والانتقالات": "Stops animations and transitions", "فرقي ومتابعاتي": "My teams & follows",
    "الفرق المفضلة": "Favourite teams", "المباريات المتابَعة": "Followed matches", "ماكو مباريات متابَعة": "No followed matches",
    "اللاعبين المفضلين": "Favourite players", "صفحة اللاعبين ←": "Players page →", "تغيّر كبير بالتوقع": "Big forecast change",
    "لمبارياتي المتابَعة وفرقي": "For my followed matches and teams", "تقرير الشوط الأول ونهاية المباراة": "Half-time and full-time report",
    "قصة جديدة تستاهل النشر": "New story worth posting", "من صفحة القصص": "From the stories page", "إعلان التشكيلة": "Line-up announced",
    "تحتاج مصدر تشكيلات (غير مفعّل)": "Needs a line-up source (not enabled)", "حد التغيّر": "Change threshold", "التكرار": "Frequency",
    "كل ما أفتح التطبيق": "Every time I open the app", "كل ساعة إذا التطبيق مفتوح": "Hourly while the app is open", "أبداً": "Never",
    "بياناتي": "My data", "نزّلي نسخة من بياناتي": "Download my data", "رجّعي الإعدادات الافتراضية": "Restore defaults", "التوقع المعروض": "Displayed forecast",
    "إعدادات التنبيهات": "Alert settings", "علّمي الكل كمقروء": "Mark all as read",
    "شنو تغيّر من آخر مرة شفتي التطبيق، لفرقج ومتابعاتج.": "What changed since your last visit, for your teams and follows.",
    "ماكو شي جديد. تابعي مباريات أو اختاري فرق مفضلة حتى توصلج تنبيهاتها.": "Nothing new. Follow matches or pick favourite teams to get their alerts.",
    // lab
    "بحث ومحتوى": "Research & content", "مواجهة فريقين": "Two teams head-to-head", "مقارنة فترتين لفريق": "One club, two eras",
    "الفريق الأول": "First team", "الفريق الثاني": "Second team", "من موسم": "From season", "لحد موسم": "To season", "الملعب": "Venue",
    "كل المباريات": "All matches", "الادعاء": "Claim", "مدعوم بالأرقام": "Supported by the numbers", "الأرقام ترفضه": "Contradicted by the numbers",
    "الأدلة ما تكفي": "Insufficient evidence", "انسخي الخلاصة": "Copy the summary", "انسخي النص": "Copy the script", "المباريات": "Matches",
    "اختاري فريقين وفترة وادعاء، والمختبر يرجع للنتائج الحقيقية ويحكم: مدعوم، مرفوض، أو الأدلة ما تكفي. كل حكم وياه أرقامه ومصدره.":
      "Pick two teams, a period and a claim. The lab checks the real results and rules: supported, contradicted or insufficient evidence, with numbers and source.",
    "نقاط بالمباراة": "Points per match", "نسبة الفوز": "Win rate", "أهداف له بالمباراة": "Goals for per match", "أهداف عليه بالمباراة": "Goals against per match",
    "فوز / تعادل / خسارة": "Win / draw / loss", "تنبيه: فترة أقل من موسم كامل؛ الفرق ممكن يكون صدفة.": "Note: less than a full season; the difference may be chance.",
    "لمقارنة مدربين: اختاري المواسم اللي درّب بيها كل واحد. البيانات ما بيها تواريخ تعيين المدربين، فالمقارنة بالمواسم الكاملة، والموسم اللي تغير بيه المدرب يدخل كامل.":
      "To compare coaches, pick the seasons each one led. The data has no appointment dates, so whole seasons are compared; a season with a coaching change counts in full.",
    "انتسخ": "Copied",
    // methodology / data (headings and short items)
    "الخلاصة": "Summary", "كل المقاييس (فترة الاختبار)": "All metrics (test period)", "اختيار صحيح": "Correct pick", "حاسوب زهراء (مدعوم بالسوق)": "Zahraa (market-informed)",
    "حاسوب زهراء (مستقل)": "Zahraa (independent)", "نسب الفوز التاريخية": "Historical win rates", "الفروق ومدى وضوحها": "Differences and how clear they are",
    "المقارنة": "Comparison", "الحكم": "Verdict", "فرق الاختيار الصحيح": "Correct-pick difference", "أسوأ بوضوح": "Clearly worse", "أحسن بوضوح": "Clearly better",
    "فرق غير واضح": "No clear difference", "الاحتمال اللي گاله الموديل": "Probability the model gave", "اللي صار فعلاً": "What actually happened",
    "كم من تفوق السوق يحققه الحاسوب؟": "How much of the market's edge does the model reach?", "المسار المدعوم بالسوق": "Market-informed track",
    "المسار المستقل": "Independent track", "شنو قيمة كل مُدخل؟": "What is each input worth?", "المُدخل": "Input",
    "التوقع المباشر (من نهاية الشوط الأول)": "In-play forecast (from half-time)", "RPS بنهاية الشوط الأول": "RPS at half-time", "اختيار صحيح من الاستراحة": "Correct pick from half-time",
    "هل الشوط الأول يضيف معلومة؟": "Does the first half add information?", "الإشارة": "Signal", "الموديل الحالي (النتيجة والوقت بس)": "Current model (score and time only)",
    "+ xG الشوط الأول": "+ first-half xG", "+ التسديدات على المرمى": "+ shots on target", "عدالة تقييم اللاعبين بين المراكز": "Fair player ratings across positions",
    "المركز": "Position", "متوسط القديم": "Old mean", "متوسط الجديد": "New mean", "حصته من كل المشاركات": "Share of all appearances",
    "صانع لعب / جناح": "Playmaker / winger", "قلب دفاع": "Centre-back", "وسط": "Midfielder", "وسط دفاعي": "Defensive midfielder", "ظهير": "Full-back",
    "مهاجم": "Striker", "حارس": "Goalkeeper", "توقع نهاية الموسم": "End-of-season forecast", "متوسط خطأ النقاط النهائية": "Mean final-points error",
    "Brier اللقب": "Title Brier", "Brier الهبوط": "Relegation Brier", "حسب الموسم": "By season", "مباريات": "Matches", "الحاسوب RPS": "Model RPS",
    "حسب وقت الموسم": "By point in the season", "حسب قوة المرشح": "By favourite strength", "حسب توفر البيانات": "By data availability",
    "فرق لها تاريخ بالدوري": "Teams with league history", "فريق صاعد (تاريخ قصير)": "Promoted team (short history)", "حسب الفريق": "By team",
    "السجل الحي (توقعات مسجلة قبل البداية)": "Live log (forecasts recorded before kick-off)", "الإصدارات": "Versions", "مستقل": "Independent",
    "المباشر": "In-play", "بصمة بيانات التقييم": "Evaluation data fingerprint", "المعروض بالواجهة": "Shown in the app", "قاموس المصطلحات": "Glossary",
    "السوق يعرف التشكيلات والإصابات": "The market knows line-ups and injuries", "لو دائماً نختار صاحب الأرض": "Always picking the home side",
    "إصابة النتيجة بالأرقام": "Exact score hit rate", "اختيار النتيجة الصحيحة (فوز/تعادل/خسارة)": "Correct outcome pick (win/draw/loss)",
    "الحالة": "Status", "آخر تحديث للتطبيق": "Last app update", "سليمة": "Healthy", "آخر بناء للبيانات": "Last data build", "فحص للبيانات": "data checks",
    "كلها ناجحة": "all passing", "التغطية": "Coverage", "أسعار": "Odds", "الشوط الأول": "First half", "المصادر": "Sources", "مفعّل": "Enabled",
    "غير مفعّل": "Not enabled", "الميزات وحالتها": "Features and status", "توقعات ما قبل المباراة (مساران)": "Pre-match forecasts (two tracks)",
    "شغّالة": "Working", "شغّالة جزئياً": "Partly working", "شغّالة محلياً": "Working locally", "تحتاج مفتاح": "Needs a key", "تحتاج مصدر": "Needs a source",
    "محاكاة الموسم وسيناريوهات «ماذا لو؟»": "Season simulation and “what if?” scenarios", "التشكيلات والغيابات": "Line-ups & absences",
    "منين تجي الأرقام، شكد هي حديثة، شنو ناقص، وشنو يحتاج تفعيل.": "Where the numbers come from, how fresh they are, what is missing and what needs enabling.",
    "التحدي": "The challenge", "توقعي المباريات الجاية": "Predict the next matches", "الترتيب يبدأ بعد أول مباراة تنتهي وعليها توقعات.": "The leaderboard starts after the first finished match with picks.",
    "أرشيف": "Archive", "مباريات الأرشيف": "Archive matches", "اللاعب": "Player", "التقييم": "Rating", "الدقائق": "Minutes", "أهداف بدون جزاء": "Non-penalty goals",
    "xG بدون جزاء": "Non-penalty xG", "xA (صناعة متوقعة)": "xA (expected assists)", "تسديدات": "Shots", "لمسات بمنطقة الجزاء": "Touches in the box",
    "مراوغات ناجحة": "Successful dribbles", "ضغط بالثلث الهجومي": "Pressures in the final third", "بحث": "Search", "ابحثي باسم اللاعب أو الفريق": "Search by player or team",
    "المحتوى": "Content", "استوديو زهراء": "Zahraa Studio", "قصص من الأرقام": "Stories from the numbers", "صانعة البطاقات": "Card maker", "القالب": "Template",
    "توقع مباراة": "Match forecast", "نهاية الشوط": "Half-time", "مقارنة فريقين": "Two-team comparison", "قصة من الأرقام": "Story from the numbers",
    "المقاس": "Size", "المباراة": "Match", "العنوان": "Title", "النص تحت العنوان": "Subtitle", "التوقيع": "Signature", "نزّلي PNG": "Download PNG",
    "اعرضيها كصورة": "Show as image", "لهجة عراقية": "Iraqi Arabic", "احفظي النص": "Save script", "انسخي": "Copy", "مسودة جديدة": "New draft",
    "محفوظاتي": "Saved", "القصص المحفوظة": "Saved stories", "ماكو قصص محفوظة": "No saved stories", "النصوص المحفوظة": "Saved scripts",
    "ماكو نصوص محفوظة": "No saved scripts", "ملاحظاتي": "My notes", "ضيفي الملاحظة": "Add note", "لون التمييز": "Accent colour",
    "أخضر الملعب": "Pitch green", "أصفر الشاشة": "Scoreboard amber", "أبيض الطباشير": "Chalk white", "معاينة البطاقة": "Card preview",
    "نص الفيديو": "Video script", "ملاحظة جديدة": "New note", "استخدميها بالبطاقة": "Use in a card", "احفظيها": "Save",
    "الجولة السابقة": "Previous round", "اختاري الجولة": "Pick a round", "الجولة التالية": "Next round", "فرقي": "My teams", "المتابَعة": "Followed",
    "مباريات الجولة (لاليغا)": "Round matches (LaLiga)", "يصنع بدون حصيلة": "Creates without output", "النقاط الفعلية:": "Actual points:",
    "النقاط المتوقعة قبل المباريات:": "Expected points before matches:", "الأهداف له/عليه:": "Goals for/against:", "xA + xG بدون جزاء:": "xA + non-penalty xG:",
    "صناعة + أهداف بدون جزاء:": "Assists + non-penalty goals:", "الدقائق:": "Minutes:",
    "معايرة حاسوب زهراء (مدعوم بالسوق)": "Calibration: Zahraa (market-informed)", "معايرة حاسوب زهراء (مستقل)": "Calibration: Zahraa (independent)",
    "معايرة أسعار Bet365": "Calibration: Bet365 odds",
    "اختاري يوم": "Pick a day", "اسمك بالترتيب": "Your name on the leaderboard", "ز": "Z", "بحث": "Search",
    "هالنسخة ما تجيب عناوين من مواقع ثانية (رابط Claude ما يوصل لمواقع خارجية). لما يشتغل التحديث على جهازج أو على GitHub مجاناً (scripts/free_update.py)، يجيب عناوين من خلاصات RSS اللي تختارينها ويعرضها هنا بالعنوان والمصدر والرابط بس.":
      "No outside headlines yet. When the update runs (on GitHub or your computer, scripts/free_update.py), it brings headlines from the RSS feeds you choose: title, source and link only.",
    "حوّلي الأرقام لبطاقة جاهزة للنشر ونص فيديو قصير. كل بطاقة تحمل اسم المنصة والمصدر ووقت التحديث وإصدار التوقع تلقائياً.": "Turn the numbers into a ready-to-post card and a short video script. Every card carries the platform name, source, update time and forecast version.",
    "مقارنة بتوقعات الموديل نفسه قبل كل مباراة (بدون معرفة النتيجة) · الموسم الحالي لحد هسه": "Against the model's own forecasts before each match (without knowing the result) · this season so far",
    "لون التمييز (ضمن هوية المنصة)": "Accent colour (within the brand)", "رجّعي النص التلقائي": "Restore the automatic text",
    "على الموبايل: «اعرضيها كصورة» ثم اضغطي مطولاً على الصورة واحفظيها.": "On a phone: “Show as image”, then long-press the image to save it.",
    "مسودة من نفس أرقام البطاقة: هوك، الفكرة، أرقام تگدرين تتأكدين منها، وختام يفتح نقاش. عدّليها براحتج.": "A draft from the card's numbers (in Arabic): hook, idea, checkable numbers and an ending that opens debate. Edit freely.",
    "حسّني الصياغة (Claude)": "Improve the wording (Claude)", "مكان الحفظ: هذا المتصفح فقط": "Saved in: this browser only", "فكرة لفيديو، ملاحظة على مباراة…": "A video idea, a note on a match…",
    "كل رقم هنا جاي من تقرير التقييم المحفوظ مع إصدار الموديل وفترة الاختبار، مو مكتوب باليد. الاختبار على مواسم ما شافها الموديل وقت اختيار الإعدادات.": "Every number here comes from the saved evaluation report with its model version and test period, not typed by hand. The test uses seasons the model never saw while settings were chosen.",
    "يعني: الحاسوب يختار الاحتمال الأرجح صح بأكثر من نص المباريات بقليل، أقل من السوق بشوية، وأحسن بوضوح من الطرق البسيطة. توقع النتيجة بالأرقام أصعب بكثير من توقع الفائز.": "In short: the model picks the right outcome in a little over half of matches, slightly below the market and clearly better than simple methods. Exact scores are far harder than winners.",
    "خطأ الاحتمالات المرتبة (RPS): يقيس بُعد التوقع عن النتيجة على سلّم فوز ← تعادل ← خسارة. كل ما أقل أحسن.": "Ranked probability score (RPS): distance between forecast and result on the win → draw → loss scale. Lower is better.",
    "Log loss: يعاقب الثقة الزايدة بالتوقع الغلط. كل ما أقل أحسن.": "Log loss: punishes confident wrong forecasts. Lower is better.",
    "Brier: مربع الفرق بين الاحتمالات الثلاثة والنتيجة. كل ما أقل أحسن.": "Brier: squared difference between the three probabilities and the result. Lower is better.",
    "نسبة الاختيار الصحيح: كم مرة صارت النتيجة الأرجح (فوز/تعادل/خسارة) فعلاً.": "Correct-pick rate: how often the most likely outcome (win/draw/loss) actually happened.",
    "كل نقطة = مجموعة احتمالات متقاربة؛ الخط العمودي = مجال الثقة لللي صار فعلاً. النقاط القريبة من الخط القطري = معايرة جيدة.": "Each dot is a group of similar probabilities; the vertical line is the interval for what happened. Dots near the diagonal = good calibration.",
    "مقارنة": "Comparison", "تقدير الفرق الصاعدة": "Promoted-team prior", "مط التقييمات": "Rating stretch", "مستقل": "Independent",
    "ما ينضاف: ماكو تحسن واضح على 380 مباراة (موسم واحد بيانات أحداث)؛ ينعاد الاختبار لما تتوفر بيانات أكثر": "Not added: no clear gain on 380 matches (one season of event data); retested when more data exists",
    "النتيجة اللي صارت تنحسب مرة وحدة بس (ما تنعاد كإشارة): الإشارة هي أداء الفريق مقارنة بالمتوقع منه بالشوط الأول.": "The score itself counts once (not again as a signal): the signal is how the team performed against expectation in the first half.",
    "تقييم المشروع منفصل عن أي تقييم مزوّد (بيانات StatsBomb المفتوحة ما بيها تقييمات).": "The project's rating is independent of any provider rating (StatsBomb open data has none).",
    "الأهداف المتوقعة قبل المباراة: معدل الأهداف اللي يتوقعه الموديل لكل فريق قبل صافرة البداية. مو xG الفرص.": "Pre-match expected goals: the goals the model expects for each team before kick-off. Not chance xG.",
    "xG الفرص: احتمال كل تسديدة تصير هدف حسب مكانها ونوعها (من بيانات الأحداث). مجموعها xG الفريق بالمباراة.": "Chance xG: the probability each shot becomes a goal from its location and type (event data). The sum is a team's match xG.",
    "RPS: خطأ الاحتمالات على سلّم فوز ← تعادل ← خسارة. صفر = توقع مثالي، وكل ما أقل أحسن.": "RPS: probability error on the win → draw → loss scale. Zero = perfect, lower is better.",
    "نسبة الاختيار الصحيح: كم مرة صارت النتيجة الأرجح (فوز/تعادل/خسارة).": "Correct-pick rate: how often the most likely outcome (win/draw/loss) happened.",
    "مدعوم بالسوق: الموديل تعلّم قوة الفرق من النتائج ومن الأهداف اللي توقعها السوق بالمباريات السابقة.": "Market-informed: the model learns team strength from results and from the goals the market expected in past matches.",
    "مستقل: الموديل يعتمد على الأهداف والتسديدات على المرمى بس، بدون أي معلومة من السوق.": "Independent: goals and shots on target only, no market information at all.",
    "أهمية المباراة: مجموع التغيّر بفرص اللقب ودوري الأبطال والهبوط لكل الفرق بين فوز صاحب الأرض وفوز الضيف.": "Match importance: total change in all teams' title, Champions League and relegation chances between a home win and an away win.",
    "PPDA: عدد تمريرات الخصم بنصف ملعبه مقابل كل محاولة افتكاك. كل ما أقل، الضغط أعلى.": "PPDA: opponent passes in their own half per defensive action. Lower = more pressing.",
    "ميلان الملعب: حصة الفريق من اللمسات بالثلث الهجومي.": "Field tilt: a team's share of touches in the final third.",
    "ضجيج المحاكاة: نسب الموسم جاية من محاكاة عشوائية، فتتغير شوية بين تشغيلين حتى لو ما تغيرت البيانات.": "Simulation noise: season percentages come from random simulation, so they move slightly between runs even with the same data.",
    "التحديث يصير من الحاسوب (python -m zsc update)، أو من جلسات Claude بعد كل جولة.": "Updates run automatically on GitHub Actions (python -m zsc update), or from Claude sessions.",
    "openfootball (الجدول والنتائج)": "openfootball (fixtures and results)", "football-data.co.uk (الأسعار والتسديدات)": "football-data.co.uk (odds and shots)",
    "SportRadar عبر Claude (المباشر)": "SportRadar via Claude (live)", "API-Football (التشكيلات)": "API-Football (line-ups)",
    "التحليل المباشر بنهاية كل شوط": "Live analysis at the end of each half", "يحتاج مفتاح API_FOOTBALL_KEY": "Needs API_FOOTBALL_KEY",
    "يشتغل من جلسات Claude (SportRadar). للتحديث الذاتي دقيقة بدقيقة يحتاج مفتاح API-Football": "Runs from Claude sessions (SportRadar). ESPN live layer runs automatically; minute-by-minute analysis needs an API-Football key",
    "xG مباشر وخرائط حرارية للمباريات الحالية": "Live xG and heatmaps for current matches", "مزود بيانات أحداث بإحداثيات (Opta / StatsBomb تجاري)": "An event-data provider with coordinates (Opta / commercial StatsBomb)",
    "التحليل العميق (أرشيف StatsBomb)": "Deep analysis (StatsBomb archive)", "مشترك بين المتابعين عند تشغيل الخادم على استضافة عامة؛ بالمعاينة يُحفظ على جهازك": "Shared with followers when the server runs on public hosting; in preview it is saved on your device",
    "تشتغل مع الخادم المحلي وإذن إشعارات المتصفح": "Works with the local server and browser notification permission",
    "خطوات تفعيل كل ميزة (المفاتيح والمصادر) مكتوبة بملف docs/ACTIVATION.md بالمشروع.": "Steps to enable each feature (keys and sources) are in docs/ACTIVATION.md.",
    "توقعي نتائج المباريات قبل صافرة البداية، وشوفي ترتيبك مقابل الجمهور ومقابل الحاسوب.": "Predict results before kick-off and see where you rank against other fans and the model.",
    "التوقع ينقفل بصافرة البداية (حسب موعد المباراة الرسمي).": "Picks lock at kick-off (official time).", "النتيجة الصحيحة (فوز/تعادل/خسارة): نقطة وحدة.": "Correct outcome (win/draw/loss): 1 point.",
    "النتيجة الرقمية الصحيحة: نقطتين إضافيتين (المجموع 3).": "Exact score: 2 extra points (3 in total).", "الترتيب الأسبوعي من الاثنين للأحد بتوقيت بغداد، والترتيب العام لكل الموسم.": "Weekly table Monday to Sunday (Baghdad time) and an overall table for the season.",
    "توقعات الجمهور منفصلة عن توقعات الحاسوب، والحاسوب يشارك بالترتيب كمتسابق باسم «الحاسوب».": "Fan picks are separate from the model's; the model plays in the table as “the model”.",
    "StatsBomb Open Data (بيانات: StatsBomb)": "StatsBomb Open Data (Data: StatsBomb)", "خرائط اللمسات من بيانات الأحداث (كل لمسة مسجلة)، مو بيانات تتبّع لكل حركة لاعب": "Touch maps from event data (every recorded touch), not tracking of every movement",
    "اختياراتج تنحفظ تلقائياً: هذا المتصفح فقط.": "Your choices save automatically: this browser only.", "للمباريات اللي عليها تحليل مباشر": "For matches with live analysis",
    "التنبيهات تطلع داخل التطبيق (الجرس فوق). إشعارات الموبايل تحتاج تشغيل التطبيق على خادم عام.": "Alerts appear in the app (the bell). For phone notifications see More → Live match notifications or ntfy.",
    "كل مباريات الموسم بتوقيت بغداد. المباريات اللي انتهت تبيّن التوقع الاسترجاعي: نفس الموديل وبيانات ما قبل الأسبوع بس.": "Every match of the season in Baghdad time. Finished matches show the retro forecast: same model, data from before the week only.",
    "بيانات اللاعبين متوفرة بالأرشيف (StatsBomb) بس؛ للاعبي الموسم الحالي تحتاج مصدر تشكيلات وإحصائيات لاعبين (صفحة البيانات والمصادر).": "Player data is archive-only (StatsBomb); current-season players need a line-up and player-stats source (see Data & sources).",
    "تصحيح النتائج القليلة": "Low-score correction",
    "الهدافين وصناع الأهداف": "Scorers & assists", "الصناعة": "Assists", "الأهداف المتوقعة xG": "Expected goals (xG)", "ملف اللاعبين ما انحمل": "The players file did not load",
    "الهدافين وصناع الأهداف ينزلون هنا من Fantasy Premier League أول ما يشتغل التحديث اليومي.": "Scorers and assists appear here from Fantasy Premier League once the daily update runs.",
    "إحصائيات لاعبي هالموسم ما متوفرة مجاناً لهالبطولة. الأرشيف (StatsBomb 2015/16) بصفحة اللاعبين.": "This season's player stats are not freely available for this competition. The archive (StatsBomb 2015/16) is on the Players page.",
  };

  // {1}, {2}...: a number, a team name or a phrase (translated in turn). Arabic left side, English right side.
  const PATTERNS = [
    ["الجولة {1}", "Round {1}"], ["مرحلة الدوري · الجولة {1}", "League phase · matchday {1}"], ["الجولة {1} من مرحلة الدوري", "League phase, matchday {1}"],
    ["مباشر {1}", "Live {1}"], ["مباشر من ESPN · تحديث {1}", "Live from ESPN · updated {1}"], ["متأخر: آخر تحديث مباشر {1}", "Delayed: last live update {1}"],
    ["{1} · مباشر {2}", "{1} · live {2}"],
    ["قبل {1} دقيقة", "{1} min ago"], ["قبل {1} دقائق", "{1} min ago"], ["قبل دقيقتين", "2 min ago"], ["قبل دقيقة", "1 min ago"],
    ["قبل {1} ساعة", "{1} h ago"], ["قبل {1} ساعات", "{1} h ago"], ["قبل ساعتين", "2 h ago"], ["قبل ساعة", "1 h ago"],
    ["قبل {1} يوم", "{1} days ago"], ["قبل {1} أيام", "{1} days ago"], ["قبل يومين", "2 days ago"], ["قبل يوم", "1 day ago"],
    ["بعد {1} دقيقة", "in {1} min"], ["بعد {1} دقائق", "in {1} min"], ["بعد {1} ساعة", "in {1} h"], ["بعد {1} ساعات", "in {1} h"], ["بعد ساعتين", "in 2 h"],
    ["بعد {1} يوم", "in {1} days"], ["بعد {1} أيام", "in {1} days"],
    ["آخر تحديث {1}", "Updated {1}"], ["آخر تحديث قبل {1}", "Updated {1}"], ["آخر جلب {1}", "Fetched {1}"],
    ["البيانات {1} · {2}", "Data {1} · {2}"], ["تحديث {1} بتوقيت بغداد", "Updated {1} (Baghdad time)"], ["{1} · آخر تحديث {2}", "{1} · updated {2}"],
    ["النسخة {1} · {2}", "Version {1} · {2}"],
    ["{1} {2}، {3} مباريات", "{1} {2}, {3} matches"], ["{1} {2}، ماكو مباريات", "{1} {2}, no matches"],
    ["توقع الحاسوب: فوز {1} {2}، تعادل {3}، فوز {4} {5}", "Model: {1} win {2}, draw {3}, {4} win {5}"],
    ["النتيجة {1} {2}، {3} {4}", "Score {1} {2}, {3} {4}"], ["الدقيقة {1}", "Minute {1}"], ["الدقيقة {1} تقديرياً، بدون بيانات مباشرة", "Minute {1}, estimated, no live data"],
    ["استراحة تقديرياً", "Half-time, estimated"], ["{1} طرد", "{1} red card(s)"],
    ["ضيفي {1} للمفضلة", "Add {1} to favourites"], ["شيلي {1} من المفضلة", "Remove {1} from favourites"], ["صفحة {1}", "{1} page"],
    ["{1} لفوق", "Move {1} up"], ["{1} لجوة", "Move {1} down"], ["أخفي {1}", "Hide {1}"], ["أظهري {1}", "Show {1}"],
    ["فوز {1}", "{1} win"], ["أهداف متوقعة {1}", "Expected goals {1}"], ["أهداف {1}", "{1} goals"], ["طرد {1}", "{1} red cards"], ["هجوم {1}", "{1} attack"], ["دفاع {1}", "{1} defence"],
    ["+ هدف {1}", "+ {1} goal"], ["+ طرد {1}", "+ {1} red card"], ["{1} ناقص واحد", "{1} minus one"], ["{1} زايد واحد", "{1} plus one"],
    ["{1} مرشح بنسبة {2} (بفارق {3} نقطة عن الاحتمال الثاني)", "{1} favoured at {2} ({3} points clear of the next outcome)"],
    ["{1} مرشح بنسبة {2}٪ (بفارق {3} نقطة عن الاحتمال الثاني)", "{1} favoured at {2}% ({3} points clear of the next outcome)"],
    ["{1} مرشح واضح بنسبة {2} (بفارق {3} نقطة عن الاحتمال الثاني)", "{1} clear favourite at {2} ({3} points clear of the next outcome)"],
    ["{1} مرشح واضح بنسبة {2}٪ (بفارق {3} نقطة عن الاحتمال الثاني)", "{1} clear favourite at {2}% ({3} points clear of the next outcome)"],
    ["{1} أفضلية بسيطة بنسبة {2}٪ (بفارق {3} نقطة عن الاحتمال الثاني)", "{1} slight edge at {2}% ({3} points clear of the next outcome)"],
    ["{1} أفضلية بسيطة بنسبة {2} (بفارق {3} نقطة عن الاحتمال الثاني)", "{1} slight edge at {2} ({3} points clear of the next outcome)"],
    ["{1}. النتيجة الأرجح {2}.", "{1}. Most likely score {2}."],
    ["توقع {1} ← صار {2} ({3} احتمال)", "Forecast {1} → result {2} ({3} probability)"], ["احتمالات {1} ضد {2}", "{1} v {2} probabilities"],
    ["المركز {1}: {2}", "Position {1}: {2}"], ["المركز {1} · {2} نقطة", "Position {1} · {2} pts"], ["المركز {1}", "Position {1}"], ["المراكز {1}–{2}", "Positions {1}–{2}"],
    ["{1} (سابقاً)", "{1} (former)"], ["قارني {1}", "Compare {1}"], ["ضد {1}", "v {1}"], ["عند {1}", "at {1}"], ["بملعب {1}", "At {1}'s ground"],
    ["الهبوط {1}", "Relegation {1}"], ["الأبطال {1}", "UCL {1}"], ["اللقب {1}", "Title {1}"], ["أهمية {1}", "Importance {1}"], ["آخر {1}", "Last {1}"], ["أول {1}", "Top {1}"],
    ["{1} نقطة", "{1} pts"], ["{1} نقاط", "{1} pts"], ["العينة: {1}", "Sample: {1}"], ["صعوبة {1} من {2}", "Difficulty {1} of {2}"], ["تعادل {1}", "Draw {1}"],
    ["الشوط الأول {1} – {2}", "Half-time {1} – {2}"], ["{1} × {2}", "{1} v {2}"], ["{1} × {2} · {3}", "{1} v {2} · {3}"],
    ["{1}: هجوم ×{2} من المعدل، دفاع ×{3} (أقل = أحسن)", "{1}: attack ×{2} of average, defence ×{3} (lower = better)"],
    ["متوقع بنهاية الموسم: {1} {2} نقطة · {3} {4} نقطة", "Expected at season end: {1} {2} pts · {3} {4} pts"],
    ["للمقارنة، SportRadar: {1} · {2} · {3}", "For comparison, SportRadar: {1} · {2} · {3}"], ["للمقارنة، SportRadar ينشر: {1} / {2} / {3}", "For comparison, SportRadar publishes: {1} / {2} / {3}"],
    ["المسار المستقل (بدون السوق): {1} · {2} · {3}", "Independent track (no market): {1} · {2} · {3}"],
    ["تقييم Elo: {1} {2} مقابل {3} {4}", "Elo rating: {1} {2} v {3} {4}"], ["حظوظ أول 8: {1} {2} · {3} {4}", "Top-8 chances: {1} {2} · {3} {4}"],
    ["كل 100 نقطة Elo فرق ≈ {1} أهداف أكثر للأقوى حسب موديل الأهداف.", "Every 100 Elo points ≈ {1} more goals for the stronger side (goal model)."],
    ["{1} مباراة بالدوري منذ {2}: أهداف {3} {4} مقابل {5}. معدل {6} هدف بالمباراة.", "{1} league meetings since {2}: {3} scored {4}, conceded {5}. {6} goals per match."],
    ["ما تواجهوا بالدوري منذ {1} حسب البيانات.", "No league meeting since {1} in the data."],
    ["{1}. المصدر: {2}.", "{1}. Source: {2}."], ["{1} تعادل", "{1} draws"],
    ["المرشحين للقب: {1} {2}، {3} {4}، {5} {6}", "Title favourites: {1} {2}, {3} {4}, {5} {6}"],
    ["محاكاة كاملة لمرحلة الدوري والأدوار الإقصائية ({1} مرة) بتقييم Elo يتحدث بكل نتيجة.", "Full simulation of the league phase and knockouts ({1} runs) with Elo updated after every result."],
    ["البريميرليغ: {1} {2} و{3} {4}", "Premier League: {1} {2} and {3} {4}"],
    ["بعد {1} جولات، {2} عنده {3} نقطة ومتوقع يخلص بحدود {4}. {5} الثالث بحظوظ {6}.", "After {1} rounds, {2} has {3} points and is projected to finish around {4}. {5} is third favourite at {6}."],
    ["فرق كبيرة مهددة بالخروج: {1} {2}، {3} {4}، {5} {6}", "Big clubs at risk of elimination: {1} {2}, {3} {4}, {5} {6}"],
    ["احتمال إنهاء مرحلة الدوري بالمركز {1} أو أقل (خروج مباشر).", "Chance of finishing the league phase {1}th or lower (eliminated)."],
    ["خطر الهبوط: {1} {2}، {3} {4}، {5} {6}", "Relegation danger: {1} {2}, {3} {4}, {5} {6}"],
    ["أكثر ثلاث فرق مهددة بالهبوط حسب {1} محاكاة لبقية الموسم.", "The three clubs most at risk, from {1} simulations of the rest of the season."],
    ["{1} فاز على {2} {3} – {4}", "{1} beat {2} {3} – {4}"], ["تعادل {1} و{2} {3} – {4}", "{1} and {2} drew {3} – {4}"],
    ["احتمال هالنتيجة قبل المباراة كان {1} بس (توقع بأثر رجعي بنفس الموديل).", "This result had only {1} before the match (retro forecast, same model)."],
    ["{1}: نتائج أحسن من مستواه", "{1}: results above its level"], ["{1}: نتائج أقل من مستواه", "{1}: results below its level"],
    ["{1} جمع {2} نقطة من {3} مباريات، بينما توقعات ما قبل المباريات كانت تعطيه {4} نقطة بالمعدل ({5}). هل هي فعالية حقيقية لو حظ راح يرجع لمستواه؟",
      "{1} took {2} points from {3} matches, while the pre-match forecasts gave it {4} on average ({5}). Real efficiency, or luck that will even out?"],
    ["{1} جمع {2} نقطة من {3} مباريات، بينما توقعات ما قبل المباريات كانت تعطيه {4} نقطة بالمعدل ({5}). هل هو سوء حظ لو مشكلة أعمق؟",
      "{1} took {2} points from {3} matches, while the pre-match forecasts gave it {4} on average ({5}). Bad luck or a deeper problem?"],
    ["{1} × {2}: مباراة تحسم أشياء", "{1} v {2}: a match that decides things"], ["{1} يتحسن حسب الموديل", "{1} is improving (model)"],
    ["{1}: يصنع أكثر مما يحصد", "{1}: creates more than he gets"], ["{1}: شوطين بوجهين ({2})", "{1}: two different halves ({2})"],
    ["xG {1} بالشوط الأول {2} وبالثاني {3}.", "{1} xG {2} in the first half, {3} in the second."],
    ["{1} {2}٪ مقابل {3} {4}٪. النقاط المتوقعة: {5} مقابل {6}.", "{1} {2}% v {3} {4}%. Expected points: {5} v {6}."],
    ["فرصة {1} بدوري الأبطال: {2}٪ إذا فاز {3}، {4}٪ بالتعادل، و{5}٪ إذا فاز {6}.", "{1}'s Champions League chance: {2}% if {3} win, {4}% with a draw, {5}% if {6} win."],
    ["فرصة {1} بالهبوط: {2}٪ إذا فاز {3}، {4}٪ بالتعادل، و{5}٪ إذا فاز {6}.", "{1}'s relegation chance: {2}% if {3} win, {4}% with a draw, {5}% if {6} win."],
    ["{1} بدوري الأبطال: {2} / {3} / {4} · {5} بالهبوط: {6} / {7} / {8}", "{1} UCL: {2} / {3} / {4} · {5} relegation: {6} / {7} / {8}"],
    ["{1} بالهبوط: {2} / {3} / {4} · {5} بدوري الأبطال: {6} / {7} / {8}", "{1} relegation: {2} / {3} / {4} · {5} UCL: {6} / {7} / {8}"],
    ["{1} بدوري الأبطال: {2} / {3} / {4} · {5} بدوري الأبطال: {6} / {7} / {8}", "{1} UCL: {2} / {3} / {4} · {5} UCL: {6} / {7} / {8}"],
    ["{1} باللقب: {2} / {3} / {4} · {5} باللقب: {6} / {7} / {8}", "{1} title: {2} / {3} / {4} · {5} title: {6} / {7} / {8}"],
    ["{1} بالهبوط: {2} / {3} / {4} · {5} باللقب: {6} / {7} / {8}", "{1} relegation: {2} / {3} / {4} · {5} title: {6} / {7} / {8}"],
    ["{1} بدوري الأبطال: {2} إذا فاز {3} · {4} تعادل · {5} إذا فاز {6}", "{1} UCL: {2} if {3} win · {4} draw · {5} if {6} win"],
    ["{1} بالهبوط: {2} إذا فاز {3} · {4} تعادل · {5} إذا فاز {6}", "{1} relegation: {2} if {3} win · {4} draw · {5} if {6} win"],
    ["فرصة {1} بدوري الأبطال (فوز الأرض/تعادل/فوز الضيف):", "{1}'s UCL chance (home win/draw/away win):"], ["فرصة {1} بالهبوط (فوز الأرض/تعادل/فوز الضيف):", "{1}'s relegation chance (home win/draw/away win):"],
    ["هجوم {1} أقوى من معدل الدوري ({2}٪ أهداف)", "{1} attack stronger than league average ({2}% goals)"],
    ["دفاع {1} يستقبل أقل من المعدل ({2}٪ أهداف عليه)", "{1} defence concedes less than average ({2}% goals against)"],
    ["هجوم {1} أضعف من معدل الدوري ({2}٪ أهداف)", "{1} attack weaker than league average ({2}% goals)"],
    ["دفاع {1} يستقبل أكثر من المعدل ({2}٪ أهداف عليه)", "{1} defence concedes more than average ({2}% goals against)"],
    ["ميزة الأرض (عامة بالدوري): ترفع أهداف {1} المتوقعة {2}٪", "Home advantage (league-wide): raises {1}'s expected goals by {2}%"],
    ["يرجّح {1}", "Favours {1}"], ["ليش الحاسوب يرجّح {1}؟", "Why does the model favour {1}?"],
    ["الرقم على اليمين لـ{1} واليسار لـ{2}. حتى أرجح نتيجة تصير بحدود {3} من كل {4} أو {5} مباريات.", "Left-hand number for {1}, right for {2}. Even the likeliest score happens only about {3} in {4} or {5} matches."],
    ["أيام الراحة قبل هالمباراة: {1} (من مباريات الدوري بس)", "Rest days before this match: {1} (league matches only)"],
    ["الأهداف المتوقعة قبل المباراة: {1} {2} · {3} {4}. هذي مو xG الفرص؛ هي معدل الأهداف اللي يتوقعه الموديل قبل الصافرة.", "Pre-match expected goals: {1} {2} · {3} {4}. Not chance xG: the goals the model expects before kick-off."],
    ["كل خانة: احتمال النتيجة بالضبط (٪). الصفوف أهداف {1}، والأعمدة أهداف {2}.", "Each cell: probability of that exact score (%). Rows {1} goals, columns {2} goals."],
    ["أهداف {1} ↓", "{1} goals ↓"], ["أهداف {1} →", "{1} goals →"],
    ["بالدقيقة {1} والنتيجة {2} {3} – {4} {5}. الفرق تحت كل رقم مقارنة بتوقع ما قبل المباراة.", "At minute {1} with {2} {3} – {4} {5}. The change under each number is against the pre-match forecast."],
    ["تبقى النتيجة +15 دقيقة", "Score stays +15 min"], ["{1} نقطة من {2} مباريات", "{1} pts from {2} matches"], ["{1} فوز · {2} تعادل · {3} خسارة", "{1} W · {2} D · {3} L"],
    ["له {1} · عليه {2}", "For {1} · against {2}"], ["المدى الطبيعي {1}–{2}", "Normal range {1}–{2}"], ["العينة {1} مباريات؛ التذبذب الطبيعي بحدود ±{2} نقطة.", "Sample {1} matches; normal swing about ±{2} points."],
    ["آخر {1} مباريات", "Last {1} matches"], ["{1} = معدل الدوري. الأقدم على اليمين.", "{1} = league average. Oldest on the right."], ["{1} = معدل الدوري", "{1} = league average"],
    ["الفورمة (آخر {1} بالدوري)", "Form (last {1} league matches)"], ["إسبانيا · {1} · {2} مباراة", "Spain · {1} · {2} matches"], ["إنجلترا · {1} · {2} مباراة", "England · {1} · {2} matches"],
    ["أوروبا · {1} · {2} مباراة", "Europe · {1} · {2} matches"], ["إسبانيا · الموسم {1}", "Spain · season {1}"], ["إنجلترا · الموسم {1}", "England · season {1}"], ["أوروبا · الموسم {1}", "Europe · season {1}"],
    ["{1} فريق؛ أول {2} لدوري الأبطال وآخر {3} تهبط", "{1} teams; top {2} to the Champions League, bottom {3} relegated"],
    ["الجولة {1} · {2} · {3} بتوقيت بغداد", "Round {1} · {2} · {3} Baghdad time"], ["الدوري الإسباني {1} · الجولة {2} · {3}", "LaLiga {1} · round {2} · {3}"],
    ["الدوري الإسباني {1} · آخر تحديث {2}", "LaLiga {1} · updated {2}"], ["الدوري الإسباني {1}", "LaLiga {1}"],
    ["{1} مباريات اليوم. أوضح مرشح: {2} بنسبة {3}.", "{1} matches today. Clearest favourite: {2} at {3}."], ["{1} مباراة · {2} · Bet365 {3}", "{1} matches · {2} · Bet365 {3}"],
    ["{1} مباراة · {2}", "{1} matches · {2}"], ["{1} · راحة {2} أيام", "{1} · {2} days' rest"], ["{1} · الوقت غير محدد · راحة {2} أيام", "{1} · time TBC · {2} days' rest"],
    ["كل المواجهات ({1})", "All meetings ({1})"], ["«{1}»", "“{1}”"], ["{1} فوز مقابل {2}.", "{1} wins against {2}."],
    ["{1} فاز على {2} أكثر ما {3} فاز عليه", "{1} beat {2} more often than {3} beat them"], ["{1} سجل أهداف أكثر من {2} بمواجهاتهم", "{1} scored more goals than {2} in their meetings"],
    ["{1} ما خسر من {2} بهالفترة", "{1} did not lose to {2} in this period"], ["{1} فاز بأكثر من نص المواجهات", "{1} won more than half of the meetings"],
    ["متعادلين بعدد الانتصارات: {1} لكل طرف.", "Level on wins: {1} each."], ["{1} فوز مقابل {2}: العكس هو الصحيح.", "{1} wins against {2}: the opposite is true."],
    ["{1} هدف مقابل {2}.", "{1} goals against {2}."], ["نفس عدد الأهداف: {1}.", "Same number of goals: {1}."], ["{1} مباراة بدون خسارة ({2} فوز، {3} تعادل).", "{1} matches unbeaten ({2} W, {3} D)."],
    ["خسر {1} مرة من {2}.", "Lost {1} of {2}."], ["خسر {1} مرات من {2}.", "Lost {1} of {2}."], ["{1} فوز من {2} ({3}).", "{1} wins from {2} ({3})."],
    ["ماكو مواجهات بالبيانات ضمن هالفترة والملعب المختار.", "No meetings in the data for this period and venue."],
    ["النطاق: {1}، {2} لحد {3}، {4}. مباريات الدوري فقط (بدون الكأس والسوبر والبطولات الأوروبية)؛ لو الادعاء يقصد كل البطولات، الحكم هنا جزئي.",
      "Scope: {1}, {2} to {3}, {4}. League matches only (no cups, Super Cups or European games); if the claim means all competitions, this verdict is partial."],
    ["كل الملاعب", "all venues"], ["بملعب {1}", "at {1}"],
    ["البيانات: مباريات الدوري فقط (بدون الكأس والسوبر والبطولات الأوروبية)، من {1} لحد {2} ({3} مباراة). المصدر: {4}.", "Data: league matches only (no cups, Super Cups or European games), {1} to {2} ({3} matches). Source: {4}."],
    ["{1}: {2} مقابل {3}", "{1}: {2} v {3}"], ["نص ريل ({1}–{2} ثانية)", "Reel script ({1}–{2} s, Arabic)"], ["الفترة الأولى: من", "First period: from"], ["الفترة الأولى: لحد", "First period: to"],
    ["الفترة الثانية: من", "Second period: from"], ["الفترة الثانية: لحد", "Second period: to"],
    ["شغالة · {1}", "On · {1}"], ["فريق واحد", "one team"], ["فريقين", "two teams"], ["{1} فرق", "{1} teams"], ["بغداد · {1} ساعة", "Baghdad · {1}h"],
    ["المصدر صحّح النتيجة مرة؛ آخر نتيجة معروضة هي الرسمية من المصدر.", "The source corrected the score once; the latest score shown is the source's official one."],
    ["الملعب: {1}", "Venue: {1}"], ["الحكم: {1}", "Referee: {1}"], ["الحضور: {1}", "Attendance: {1}"],
    ["النتيجة المباشرة: {1}", "Live score: {1}"], ["مباراة بدأت", "Match started"],
    ["قارني {1}", "Compare {1}"],
    ["{1} ن.م", "{1} pp"],
    ["المصدر: Fantasy Premier League (الرسمي؛ xG وxA من Opta) · آخر جلب {1}", "Source: Fantasy Premier League (official; xG and xA from Opta) · fetched {1}"],
    ["{1}، {2} مباريات", "{1}, {2} matches"], ["{1}، ماكو مباريات", "{1}, no matches"], ["{1}: شوطين بوجهين ({2})", "{1}: two different halves ({2})"],
    ["المتوقع من جودة الفرص مقابل الحصيلة الفعلية · الليغا {1}", "Expected from chance quality vs actual output · LaLiga {1}"],
    ["ماكو هدف دقة تسويقي (مثل «{1}»): كرة القدم بيها صدفة كبيرة، وحتى السوق يختار صح بحدود {2}. أي تحسين ينضاف بس إذا الاختبار أثبته.", "No marketing accuracy target (like “{1}”): football is full of chance, and even the market is right only about {2} of the time. An improvement is added only when the test proves it."],
    ["فترة الاختيار (لضبط الإعدادات): {1}، {2} مباراة. فترة الاختبار النهائي: {3}. التدريب أسبوع بأسبوع ببيانات ما قبل كل أسبوع فقط (walk-forward).", "Selection period (for tuning): {1}, {2} matches. Final test period: {3}. Training week by week with data from before each week only (walk-forward)."],
    ["المجال من إعادة سحب المباريات نفسها (paired bootstrap) على {1} مباراة. «غير واضح» = الفرق ممكن يكون صدفة.", "Intervals from resampling the same matches (paired bootstrap) on {1} matches. “No clear difference” = the gap may be chance."],
    ["هذا مو نسبة دقة. هو كم من تحسّن Bet365 على نسب الفوز التاريخية (بمقياس RPS) يحققه الحاسوب: RPS نسب الفوز {1}، Bet365 {2}، والحاسوب {3}.", "This is not an accuracy rate. It is how much of Bet365's improvement over historical win rates (in RPS) the model reaches: historical {1}, Bet365 {2}, model {3}."],
    ["الرقم القديم بالواجهة السابقة (حوالي {1}) كان هذا المقياس نفسه، بس كان مكتوب وكأنه دقة. صححناه.", "The old number in the previous interface (about {1}) was this same measure, but labelled as accuracy. We corrected it."],
    ["أهداف السوق للمباريات السابقة", "Market goals of past matches"],
    ["على فترة الاختيار ({1}). كل سطر يضيف مُدخل واحد ويقيس الفرق على نفس المباريات. أيام الراحة انجربت ورُفضت: ما حسّنت الاختبار.", "On the selection period ({1}). Each row adds one input and measures the difference on the same matches. Rest days were tried and rejected: no improvement."],
    ["النسخة المختارة: «توزيع الوقت + أثر النتيجة + تصحيح النتائج القليلة». بشرط إن الدقيقة {1} تساوي توقع ما قبل المباراة بالضبط؛ كلفة هذا الشرط بفترة الاختيار: RPS {2} [{3}، {4}] (صغيرة جداً).", "Chosen version: “time profile + score effect + low-score correction”, constrained so minute {1} equals the pre-match forecast exactly; cost of that constraint on the selection period: RPS {2} [{3}, {4}] (very small)."],
    ["اختيار {1}، اختبار {2}، وبنفس مدخلات التطبيق (توقعات كل مسار). الطرد: الفريق الناقص يسجل ×{3} والخصم ×{4} (من {5} مباراة بيها طرد، StatsBomb).", "Selection {1}, test {2}, with the app's own inputs (each track's forecasts). Red cards: the short-handed team scores ×{3} and the opponent ×{4} (from {5} matches with a red card, StatsBomb)."],
    ["جربنا نضيف للتوقع المباشر شي من مجريات الشوط الأول (xG والتسديدات على المرمى) فوق النتيجة نفسها، على {1} مباراة (الليغا {2}، الموسم الوحيد الكامل ببيانات أحداث)، بتقييم خارج العينة.", "We tried adding first-half play (xG and shots on target) on top of the score to the in-play forecast, on {1} matches (LaLiga {2}, the only full season with event data), evaluated out of sample."],
    ["على {1} مشاركة ({2} دقيقة أو أكثر) بموسم الليغا {3}: الصيغة القديمة كانت تعطي المهاجمين وصناع اللعب تقييمات أعلى بكثير من المدافعين والحراس. الصيغة الجديدة تقارن كل لاعب بلاعبي مركزه.", "On {1} appearances ({2}+ minutes) in LaLiga {3}: the old formula rated forwards and playmakers far above defenders and keepers. The new one compares each player with his own position."],
    ["من نقطة بعد {1} مباراة بكل موسم؛ إعداد «تغيّر المستوى خلال الموسم» ({2}) انختار على {3} وانختبر على {4} ({5} فريق).", "From the point after {1} matches each season; the in-season drift setting ({2}) was chosen on {3} and tested on {4} ({5} teams)."],
    ["السجل بدأ أكتوبر {1}: النتائج تنحسب لما تنتهي أول مباريات مسجلة.", "The log started in October {1}: results count once the first logged matches finish."],
    ["كل توقع ينحفظ بوقت إصداره وإصدار الموديل ونسخة البيانات، والتوقع اللي ينصدر بعد صافرة البداية ينرفض. المقارنة على نفس المباريات لكل المصادر.", "Every forecast is stored with its issue time, model version and data version; a forecast issued after kick-off is rejected. All sources are compared on the same matches."],
    ["توزيع الوقت + أثر النتيجة + تصحيح النتائج القليلة · مواسم {1}", "Time profile + score effect + low-score correction · seasons {1}"],
    ["إصابة النتيجة الرقمية: كم مرة صارت النتيجة الأرجح بالأرقام (مثل {1}). أصعب بكثير من اختيار الفائز.", "Exact-score hit rate: how often the most likely exact score (e.g. {1}) happened. Much harder than picking the winner."],
    ["المعايرة: لما الموديل يگول {1}، هل يصير الشي تقريباً {2} من المرات؟", "Calibration: when the model says {1}, does it happen about {2} of the time?"],
    ["الناقص يبقى ناقص (ما ينحسب صفر). الأسعار الناقصة سببها إن ملف football-data المفتوح وقف عند {1} أكتوبر؛ التسديدات على المرمى انكملت من SportRadar.", "Missing stays missing (never counted as zero). Odds are missing because the open football-data file stopped on {1} October; shots on target were completed from SportRadar."],
    ["محلي: توقعاتك محفوظة بهذا المتصفح بس. حتى يصير مشترك بين المتابعين: شغّلي الخادم على استضافة عامة (الخطوات بصفحة البيانات والمصادر).", "Local: your picks are saved in this browser only. To share with followers, run the server on public hosting (steps on the data page)."],
    ["«الحاسوب» يلعب بتوقعه المسجل قبل البداية (الأرجح بالفوز/التعادل/الخسارة وأرجح نتيجة)، وينحسب بس بالمباريات اللي عليها توقعات من الجمهور.", "“The model” plays with its forecast logged before kick-off (most likely outcome and score), counted only in matches fans picked."],
    ["مباريات كاملة من بيانات StatsBomb المفتوحة: خريطة التسديدات مع xG لكل فرصة، خرائط اللمسات، شبكة التمريرات، وتقييم اللاعبين. هذا الشكل الكامل اللي يصير متاح للمباريات الحالية لما يتفعل مزوّد بيانات أحداث.", "Complete matches from StatsBomb open data: shot maps with xG per chance, touch maps, passing networks and player ratings. This is what current matches get once an event-data provider is enabled."],
    ["الليغا {1} من بيانات الأحداث المفتوحة: أرقام لكل {2} دقيقة، ومقارنة كل لاعب بلاعبي نفس المركز بس. للاعبي الموسم الحالي تحتاج مزوّد إحصائيات لاعبين.", "LaLiga {1} from open event data: per-{2} numbers, each player compared only with his position. Current-season players need a player-stats provider."],
    ["النسب من {1} موسم محاكى؛ الخطأ العشوائي بحدود ±{2} نقطة مئوية لنسبة {3}. «المدى» = {4} من المواسم المحاكاة تنتهي بهالنقاط. المراكز الأوروبية حسب ملف القواعد للموسم (المراكز الأوروبية قابلة للتغيير: بطل كأس الملك يأخذ مقعد الدوري الأوروبي، وقد يحصل الدوري على مقعد إضافي بدوري الأبطال حسب معامل يويفا. حدّث هذا الملف عند التأكيد.).",
      "From {1} simulated seasons; random error about ±{2} points for a {3} chance. “Range” = {4} of simulated seasons end within these points. European places follow the season's rules file (they can change: the Copa del Rey winner takes a Europa League place, and UEFA coefficients can add a Champions League place)."],
    ["نفس موديل الليغا (Dixon-Coles، مساران) وبنفس الإعدادات المختارة على الليغا، فاختبار البريميرليغ خارج العينة بالكامل. بيانات مجانية: نتائج وتسديدات على المرمى وأسعار Bet365 من {1} لحد {2} آب {3} (xgabora/football-data)، وبعدها النتائج من openfootball وSportRadar. محاكاة {4} مرة لبقية الموسم.",
      "The LaLiga model (Dixon-Coles, two tracks) with the settings chosen on LaLiga, so the Premier League test is fully out of sample. Free data: results, shots on target and Bet365 odds from {1} to {2} August {3} (xgabora/football-data), then results from openfootball and SportRadar. {4} simulations of the rest of the season."],
    ["أندية من دوريات مختلفة، فالقوة من تقييم Elo: تقييمات ClubElo لحد {1} (مجانية عبر xgabora)، وبعدها كل نتيجة بدوري الأبطال تحرك التقييم. الأهداف المتوقعة من موديل Poisson على فرق الـElo، متدرب على {2} مباراة محلية من {3}. {4} و{5} من احتمالات SportRadar، و{6} و{7} بتقدير أولي (ماكو تقييم مجاني إلهم).",
      "Clubs from different leagues, so strength comes from Elo: ClubElo ratings up to {1} (free via xgabora), then every Champions League result moves the rating. Expected goals from a Poisson model on Elo gaps, trained on {2} domestic matches since {3}. {4} and {5} from SportRadar probabilities, {6} and {7} from an initial estimate (no free rating exists)."],
    ["التقييم ({1}) = {2} × متوسط ترتيب اللاعب بين {3} بالأرقام اللي بالجدول، بأوزان: {4}", "Rating ({1}) = {2} × the player's mean percentile among {3} on the table's metrics, weighted: {4}"], ["{1} من آخر {2} مباريات لـ{3} بدون أسعار سوق، فالمسار المدعوم بالسوق يعتمد على الأهداف والتسديدات بهاي المباريات", "{1} of {3}'s last {2} matches have no market odds, so the market-informed track relies on goals and shots there"],
    ["ما تغيّر شي يذكر عن التوقع السابق ({1}).", "Nothing notable changed since the previous forecast ({1})."], ["إصدار الموديل تغيّر: {1} ← {2}", "Model version changed: {1} → {2}"],
    ["مؤشر الأهمية {1}: فرص الفرق حسب نتيجة هالمباراة ({2} موسم محاكى لكل نتيجة):", "Importance {1}: teams' chances by this match's result ({2} simulated seasons per result):"],
    ["توقع استرجاعي: بنفس الموديل وبيانات ما قبل الأسبوع فقط. الاحتمال الأرجح صار ✓ · RPS {1}", "Retro forecast: same model, data from before the week only. The favourite won ✓ · RPS {1}"],
    ["توقع استرجاعي: بنفس الموديل وبيانات ما قبل الأسبوع فقط. الاحتمال الأرجح ما صار ✗ · RPS {1}", "Retro forecast: same model, data from before the week only. The favourite did not win ✗ · RPS {1}"],
    ["أسعار السوق (Bet365) بعد إزالة الهامش", "Market odds (Bet365) with the margin removed"], ["هالمباراة قبل بدء سجل التوقعات (السجل بدأ أكتوبر {1}).", "This match predates the forecast log (started October {1})."],
    ["توزيع المراكز المتوقعة (المركز {1} على اليمين):", "Projected positions (position {1} on the right):"],
    ["النسب من {1} موسم محاكى؛ الخطأ العشوائي بحدود ±{2} نقطة مئوية لنسبة {3}٪", "From {1} simulated seasons; random error about ±{2} points for a {3}% chance"],
    ["الهجوم {1}× = يسجل {2}٪ أكثر من فريق معدل ضد نفس الخصم. الدفاع {3}× = يستقبل {4}٪ أقل.", "Attack {1}× = scores {2}% more than an average team against the same opponent. Defence {3}× = concedes {4}% less."],
    ["الصعوبة = {1} ناقص النقاط المتوقعة من المباراة حسب الموديل (تشمل قوة الخصم والأرض). أيام الراحة من مباريات الدوري بس.", "Difficulty = {1} minus the model's expected points from the match (opponent strength and venue included). Rest days from league matches only."],
    ["كل مبارياته هالموسم", "All matches this season"], ["أهم المباريات للموسم هالأسبوع", "This week's most important matches"], ["السجل الحي من هالموسم", "Live log this season"],
    ["الأهمية = مجموع تغيّر فرص اللقب ودوري الأبطال والهبوط بين فوز صاحب الأرض وفوز الضيف (بنفس المحاكاة). يعني حجم الرهان، مو شهرة الفريقين.", "Importance = total change in title, Champions League and relegation chances between a home win and an away win (same simulation): the stakes, not the teams' fame."],
    ["المقارنة: نفس المحاكاة بثلاث نتائج للمباراة وبنفس الأرقام العشوائية · الفترة: بقية الموسم", "Comparison: the same simulation with the three results and the same random numbers · period: rest of the season"],
    ["نفس المحاكاة بثلاث نتائج للمباراة وبنفس الأرقام العشوائية · بقية الموسم", "Same simulation with the three results and the same random numbers · rest of the season"],
    ["الرقم الأول من اختبار على مواسم ما شافها الموديل وقت الضبط. الثاني من التوقعات المسجلة قبل صافرة البداية فقط.", "The first number comes from a test on seasons the model never saw while tuned; the second from forecasts recorded before kick-off only."],
    ["الترتيب الحالي، وتوقع نهاية الموسم من {1} موسم محاكى بقواعد الليغا (المواجهات المباشرة ثم فارق الأهداف). وتحت: جربي «ماذا لو؟» بنتائج من اختيارك.", "Current table and the end-of-season forecast from {1} simulated seasons under LaLiga rules (head-to-head, then goal difference). Below: try “What if?” with results you choose."],
    ["دوري أبطال أوروبا ({1})", "Champions League ({1})"], ["الدوري الأوروبي ({1})", "Europa League ({1})"], ["دوري المؤتمر الأوروبي ({1})", "Conference League ({1})"], ["الهبوط ({1})", "Relegation ({1})"],
    ["توزيع المراكز ({1} ← {2})", "Position distribution ({1} → {2})"],
    ["اضغطي على أي فريق لبطاقته: الفورمة، المستوى الحقيقي مقابل النتائج، المباريات الجاية وصعوبتها، وفرصه بالموسم. النجمة تخليه من فرقك المفضلة.", "Tap a team for its card: form, true level vs results, upcoming matches and difficulty, and season chances. The star makes it a favourite."],
    ["{1} كلمة ≈ {2} ثانية بالقراءة العادية", "{1} words ≈ {2} seconds read aloud"], ["نص فيديو {1}–{2} ثانية", "Video script {1}–{2} seconds"],
    ["تقرير {1}", "Report {1}"], ["أشيع نتيجة دائماً: {1}", "Always the most common score: {1}"], ["Bet365 بنفس المباريات", "Bet365 on the same matches"], ["أسعار Bet365", "Bet365 odds"],
    ["{1} [{2}، {3}] ن.م", "{1} [{2}, {3}] pp"], ["{1} [{2}, {3}] ن.م", "{1} [{2}, {3}] pp"], ["متوسط خطأ المعايرة: {1}", "Mean calibration error: {1}"],
    ["المعايرة: لما يگول {1}٪، يصير {2}٪؟", "Calibration: when it says {1}%, does it happen {2}% of the time?"], ["{1} مقابل {2}", "{1} v {2}"],
    ["فرق RPS [مجال الثقة {1}٪]", "RPS difference [{1}% interval]"], ["فرق RPS [{1}٪]", "RPS difference [{1}%]"], ["الفرق عن الموديل الحالي [{1}٪]", "Difference from the current model [{1}%]"],
    ["قبل المباراة {1}", "Pre-match {1}"], ["حصته من أعلى {1} (قديم)", "Share of top {1} (old)"], ["حصته من أعلى {1} (جديد)", "Share of top {1} (new)"],
    ["الطريقة البسيطة {1}", "Simple method {1}"], ["النقاط داخل «المدى» (الهدف {1}٪)", "Points inside the range (target {1}%)"], ["بدون معلومات {1}", "No information {1}"],
    ["اختيار {1} · اختبار {2}", "Selection {1} · test {2}"], ["تغيّر المستوى {1}", "Level drift {1}"], ["نسخة البيانات {1}", "Data version {1}"],
    ["{1} مباراة بيها بيانات ناقصة هالموسم", "{1} matches with missing data this season"], ["{1}: {2} v {3} — ناقص: {4}", "{1}: {2} v {3} — missing: {4}"], ["الأسعار", "odds"],
    ["{1} تصحيح موثق للبيانات الخام", "{1} documented corrections to the raw data"], ["يوفر: {1}", "Provides: {1}"], ["{1} لاعب مفضل من أرشيف الليغا {2}.", "{1} favourite players from the LaLiga {2} archive."],
    ["{1} نقاط مئوية أو أكثر", "{1} points or more"], ["المحفوظ: {1} قصة، {2} نص، {3} ملاحظة.", "Saved: {1} stories, {2} scripts, {3} notes."],
    ["{1} دقيقة أو أكثر بس (عينة كافية)", "{1}+ minutes only (enough sample)"],
    ["بموسم الليغا {1} صنع {2} xA {3} وxG بدون جزاء {4}، بس حصيلته {5} صناعة و{6} أهداف.", "In LaLiga {1}, {2} created xA {3} and non-penalty xG {4}, but returned {5} assists and {6} goals."],
    ["تقييم {1} تغيّر خلال آخر {2} أسابيع: الهجوم {3} ← {4}، والدفاع {5} ← {6} ({7} = معدل الدوري؛ الدفاع أقل = أحسن).", "{1}'s rating over the last {2} weeks: attack {3} → {4}, defence {5} → {6} ({7} = league average; lower defence = better)."],
    ["الهجوم قبل {1} أسابيع ← الآن", "Attack {1} weeks ago → now"],
    ["{1} فريق، {2} مباريات لكل فريق بمرحلة الدوري، أول {3} لدور الـ{4} والمراكز {5} للملحق", "{1} teams, {2} league-phase matches each; top {3} to the round of {4}, positions {5} to the play-offs"],
    ["كسر التعادل: {1}", "Tie-break: {1}"], ["النقاط", "points"], ["فارق الأهداف", "goal difference"], ["الأهداف المسجلة", "goals scored"], ["ثم المواجهات المباشرة", "then head-to-head"],
    ["الانتصارات (المعايير الأخرى ما تنحسب)", "wins (other criteria not modelled)"],
    ["مقارنة مع احتمالات SportRadar لـ{1} مباريات من الجولة {2}: متوسط الفرق {3} نقطة مئوية لكل نتيجة.", "Against SportRadar's probabilities for {1} matches of matchday {2}: mean difference {3} points per outcome."],
    ["المحاكاة: بقية مرحلة الدوري + الملحق + الأدوار الإقصائية بنظام الشجرة الرسمي (القرعة عشوائية ضمن الأزواج) {1} مرة.", "Simulation: rest of the league phase + play-offs + knockouts on the official bracket (random draws within the seeded pairs), {1} runs."],
    ["الاختبار ({1}، {2} مباراة): المسار المدعوم بالسوق أصاب الاحتمال الأرجح {3} وRPS {4}؛ Bet365 {5} وRPS {6}.", "Test ({1}, {2} matches): the market-informed track picked the outcome {3} of the time, RPS {4}; Bet365 {5}, RPS {6}."],
    ["تحقق: النتائج تطابق الترتيب الرسمي ✓. التسديدات والأسعار متوفرة لـ{1} مباراة من الموسم الحالي بس (المصدر المجاني يوقف {2} آب)؛ الباقي يتدرب على الأهداف.", "Check: results reproduce the official table ✓. Shots and odds exist for only {1} matches this season (the free source stops on {2} August); the rest trains on goals."],
    ["موديل Dixon-Coles بمسارين (مدعوم بالسوق ومستقل)، اختبار خارج العينة على {1} مواسم، سجل توقعات قبل كل مباراة وتحليل مباشر. التفاصيل بصفحة المنهجية.", "Dixon-Coles model with two tracks (market-informed and independent), out-of-sample test on {1} seasons, a forecast log before every match and live analysis. Details on the methodology page."],

  ];

  // ------------------------------------------------------------------ engine
  const lang = (() => { try { return (JSON.parse(localStorage.getItem("zsc.v2.prefs") || "{}").lang) || "ar"; } catch (e) { return "ar"; } })();
  ZS.lang = lang === "en" ? "en" : "ar";
  const AR = /[؀-ۿ]/;
  for (const k of Object.keys(EXACT)) if (k.includes("٪")) EXACT[k.replace(/٪/g, "%")] = EXACT[k];
  PATTERNS.push(["أمس {1}", "Yesterday {1}"], ["اليوم {1}", "Today {1}"], ["باجر {1}", "Tomorrow {1}"],
    ["{1} أقوى من معدل الدوري ({2} أهداف)", "{1} stronger than league average ({2} goals)"], ["{1} أضعف من معدل الدوري ({2} أهداف)", "{1} weaker than league average ({2} goals)"],
    ["{1} يستقبل أقل من المعدل ({2} أهداف عليه)", "{1} concedes less than average ({2} against)"], ["{1} يستقبل أكثر من المعدل ({2} أهداف عليه)", "{1} concedes more than average ({2} against)"],
    ["الهجوم {1}× = يسجل {2} أكثر من فريق معدل ضد نفس الخصم. الدفاع {3}× = يستقبل {4} أقل.", "Attack {1}× = scores {2} more than an average team against the same opponent. Defence {3}× = concedes {4} less."]);
  const compiled = PATTERNS.map(([ar0, en]) => {
    const ar = ar0.replace(/٪/g, "%");
    const order = [];
    const src = ar.replace(/[.*+?^${}()|[\]\\]/g, (c) => (c === "{" || c === "}" ? c : "\\" + c))
      // "{1} {2}": a name then a number, so the second one matches numbers only ("Real Madrid 20%")
      .replace(/(\{\d\} )?\{(\d)\}/g, (all, prev, k) => {
        let out = "";
        if (prev) { order.push(Number(prev[1])); out = "(.+?) "; }
        order.push(Number(k));
        return out + (prev ? "([<>]?[+−-]?\\d[\\d.,:/]*\\s?[%٪]?|—)" : "(.+?)");
      });
    // literal pieces, all of which must be in a text before its regex runs (keeps long paragraphs fast)
    const parts = ar.split(/\{\d\}/).filter((x) => x.trim());
    return { re: new RegExp("^" + src + "$"), order, en, parts, weight: ar.replace(/\{\d\}/g, "").length };
  }).sort((a, b) => b.weight - a.weight);      // the most specific pattern wins
  let names = null;
  function nameMap() {
    if (names) return names;
    names = new Map();
    const add = (t) => { if (!t) return; const en = t.en || t.id; for (const k of [t.ar, t.short]) if (k && !names.has(k)) names.set(k, en); };
    try {
      for (const t of Object.values((ZS.D.teams && ZS.D.teams.teams) || {})) add(t);
      for (const t of Object.values(ZS.D.xteams || {})) add(t);
      for (const c of ZS.D.comps || []) { names.set(c.name_ar, EXACT[c.name_ar] || c.id); if (c.short_ar) names.set(c.short_ar, EXACT[c.short_ar] || c.id); }
    } catch (e) { names = null; return new Map(); }
    return names;
  }
  const memo = new Map();
  function tr(s, depth = 0) {
    if (!s || depth > 3) return s;
    if (s.includes("٪")) s = s.replace(/٪/g, "%");
    if (!AR.test(s)) return s;
    if (memo.has(s)) return memo.get(s);
    const lead = s.match(/^\s*/)[0], trail = s.match(/\s*$/)[0];
    const core = s.trim();
    let out = EXACT[core];
    if (out === undefined && nameMap().has(core)) out = nameMap().get(core);
    if (out === undefined) {
      for (const p of core.length > 600 ? [] : compiled) {
        if (!p.parts.every((x) => core.includes(x))) continue;
        const m = p.re.exec(core);
        if (!m) continue;
        const parts = {};
        p.order.forEach((k, i) => { parts[k] = tr(m[i + 1], depth + 1); });
        out = p.en.replace(/\{(\d)\}/g, (_, k) => parts[k] ?? "");
        break;
      }
    }
    if (out === undefined) {
      // a list joined by separators: translate each piece
      const seps = core.split(/( · |، | \/ | — )/);
      if (seps.length > 1) out = seps.map((x, i) => (i % 2 ? (x === "، " ? ", " : x) : tr(x, depth + 1))).join("");
    }
    if (out === undefined) out = core;
    out = lead + out + trail;
    if (memo.size < 20000) memo.set(s, out);
    return out;
  }
  const ATTRS = ["aria-label", "placeholder", "title"];
  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { const v = root.nodeValue; if (AR.test(v)) { const t = tr(v); if (t !== v) root.nodeValue = t; } return; }
    if (root.nodeType !== 1) return;
    if (root.closest && root.closest("[data-keep-ar], .script-box")) return;   // Arabic content (scripts) stays Arabic
    for (const a of ATTRS) { const v = root.getAttribute(a); if (v && AR.test(v)) { const t = tr(v); if (t !== v) root.setAttribute(a, t); } }
    for (const c of root.childNodes) walk(c);
  }
  function start() {
    if (ZS.lang !== "en") return;
    document.documentElement.setAttribute("lang", "en");
    document.documentElement.setAttribute("dir", "ltr");
    const root = document.getElementById("zs-root");
    if (!root) return;
    root.setAttribute("dir", "ltr"); root.setAttribute("lang", "en");
    walk(root);
    new MutationObserver((list) => {
      for (const m of list) {
        if (m.type === "characterData") walk(m.target);
        else if (m.type === "attributes") walk(m.target);
        else m.addedNodes.forEach(walk);
      }
    }).observe(root, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS });
    const t0 = document.title;
    new MutationObserver(() => { const t = tr(document.title); if (t !== document.title) document.title = t; }).observe(document.querySelector("title"), { childList: true });
    document.title = tr(t0);
  }
  ZS.i18n = { tr, start, EXACT, PATTERNS };
  ZS.on("core", () => { names = null; memo.clear(); });
})();
