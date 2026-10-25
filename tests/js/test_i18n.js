// English interface: key translations, stability (a translated text never changes again) and speed.
global.window = { ZS: { on() {}, D: {} } };
global.localStorage = { getItem: () => null };
global.document = {};
require("../../app/js/i18n.js");
const { tr } = window.ZS.i18n;
const cases = [
  ["توقع الحاسوب: فوز Real Madrid 58%، تعادل 22%، فوز Rayo Vallecano 20%", "Model: Real Madrid win 58%, draw 22%, Rayo Vallecano win 20%"],
  ["الجولة 10", "Round 10"], ["مباشر 2", "Live 2"], ["أهداف Getafe", "Getafe goals"], ["87٪ / 12٪", "87% / 12%"],
  ["حظوظ أول 8: AEK Athens <1% · LASK 3%", "Top-8 chances: AEK Athens <1% · LASK 3%"],
  ["الأدلة ما تكفي", "Insufficient evidence"],
];
let bad = 0;
for (const [ar, en] of cases) { const out = tr(ar); if (out !== en) { bad++; console.error("MISMATCH", JSON.stringify(ar), "->", JSON.stringify(out)); } }
for (const [ar] of cases) { const a = tr(ar); if (tr(a) !== a) { bad++; console.error("UNSTABLE", ar); } }
const long = "يعني: الحاسوب يختار الاحتمال الأرجح صح بأكثر من نص المباريات بقليل، ".repeat(8);
const t = Date.now(); for (let i = 0; i < 50; i++) tr(long + i);
if (Date.now() - t > 1500) { bad++; console.error("SLOW", Date.now() - t); }
if (bad) process.exit(1);
console.log("i18n ok");
