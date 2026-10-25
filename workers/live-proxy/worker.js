/* Live edge proxy (optional): one shared, 20-second cache in front of ESPN's public scoreboard.
   Every viewer of the app reads this cache, so ESPN sees at most about 3 requests a minute per competition,
   however many people are watching. Deploy: see docs/LIVE.md (Cloudflare Workers free plan: 100,000
   requests a day). Only the three scoreboards and match summaries can be asked for; nothing else is proxied. */
const LEAGUES = new Set(["esp.1", "eng.1", "uefa.champions"]);
const TTL = 20;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const allowed = (env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim()).filter(Boolean);
    const origin = request.headers.get("Origin") || "";
    const cors = {
      "Access-Control-Allow-Origin": allowed.length === 0 ? "*" : (allowed.includes(origin) ? origin : allowed[0]),
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Vary": "Origin",
    };
    if (request.method === "OPTIONS") return new Response(null, { headers: cors });
    if (request.method !== "GET") return new Response("method not allowed", { status: 405, headers: cors });

    const m = url.pathname.match(/^\/([a-z0-9.]+)\/(scoreboard|summary)$/);
    if (!m || !LEAGUES.has(m[1])) return new Response("not found", { status: 404, headers: cors });
    let qs = "";
    if (m[2] === "summary") {
      const ev = url.searchParams.get("event") || "";
      if (!/^\d{1,12}$/.test(ev)) return new Response("bad event id", { status: 400, headers: cors });
      qs = `?event=${ev}`;
    } else if (url.searchParams.has("dates")) {
      const d = url.searchParams.get("dates");
      if (!/^\d{8}$/.test(d)) return new Response("bad date", { status: 400, headers: cors });
      qs = `?dates=${d}`;
    }
    const upstream = `https://site.api.espn.com/apis/site/v2/sports/soccer/${m[1]}/${m[2]}${qs}`;
    const cache = caches.default;
    const key = new Request(upstream);
    let res = await cache.match(key);
    if (!res) {
      const r = await fetch(upstream, { headers: { "User-Agent": "Zahraa Football Supercomputer (personal use)" } });
      if (!r.ok) return new Response(JSON.stringify({ error: `upstream ${r.status}` }), { status: 502, headers: { ...cors, "Content-Type": "application/json" } });
      res = new Response(r.body, { headers: { "Content-Type": "application/json", "Cache-Control": `public, max-age=${TTL}` } });
      ctx.waitUntil(cache.put(key, res.clone()));
    }
    const out = new Response(res.body, res);
    for (const [k, v] of Object.entries(cors)) out.headers.set(k, v);
    out.headers.set("X-Fetched-At", new Date().toISOString());
    return out;
  },
};
