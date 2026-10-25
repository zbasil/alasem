"""Build the web app for hosting as one page plus its data files.

    python scripts/build_app.py            -> dist/web/index.html (+ dist/web/data/...)

The local app (app/index.html, served by `python -m zsc serve`) loads its CSS and JS as separate files.
This build inlines them into one page and drops the local font files (the page then uses the same
typefaces from Google Fonts), which is what a static host or a Claude artifact needs. The data snapshot
is copied next to it unchanged.

    python scripts/build_app.py --plan     list the data files that changed since the last recorded publish
    python scripts/build_app.py --record   record the current files as published (after a successful publish)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
DIST = os.path.join(ROOT, "dist", "web")
MANIFEST = os.path.join(ROOT, "outputs", "web_publish_manifest.json")


def between(text: str, tag: str) -> str:
    m = re.search(rf"<!--ZS:{tag}-START-->(.*?)<!--ZS:{tag}-END-->", text, re.S)
    if not m:
        raise SystemExit(f"marker {tag} not found in app/index.html")
    return m.group(1)


def build() -> str:
    src = open(os.path.join(APP, "index.html"), encoding="utf-8").read()
    head = between(src, "HEAD")
    body = between(src, "BODY")
    head = re.sub(r"<!--ZS:FONTS-LOCAL-START-->.*?<!--ZS:FONTS-LOCAL-END-->", "", head, flags=re.S)
    css = open(os.path.join(APP, "css", "app.css"), encoding="utf-8").read()
    head = re.sub(r"<!--ZS:CSS-START-->.*?<!--ZS:CSS-END-->", lambda _: f"<style>\n{css}\n</style>", head, flags=re.S)
    scripts = re.findall(r'<script src="([^"]+)"></script>', between(src, "JS"))
    js = "\n".join(f"/* ---- {s} ---- */\n" + open(os.path.join(APP, s), encoding="utf-8").read() for s in scripts)
    js = js.replace("</script", "<\\/script")
    body = re.sub(r"<!--ZS:JS-START-->.*?<!--ZS:JS-END-->",
                  lambda _: f'<script>window.ZS_BUILD = "web";</script>\n<script>\n{js}\n</script>', body, flags=re.S)
    # charset and viewport first: a static host may not send a charset (the Claude artifact wrapper adds its own too)
    meta = '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    page = meta + head.strip() + "\n" + body.strip() + "\n"
    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    # installable app: manifest, icons and the service worker (its cache name changes with every build)
    shutil.copy2(os.path.join(APP, "manifest.webmanifest"), os.path.join(DIST, "manifest.webmanifest"))
    shutil.rmtree(os.path.join(DIST, "icons"), ignore_errors=True)
    shutil.copytree(os.path.join(APP, "icons"), os.path.join(DIST, "icons"))
    build_id = hashlib.sha256(page.encode("utf-8")).hexdigest()[:12]
    sw = open(os.path.join(APP, "sw.js"), encoding="utf-8").read().replace("__BUILD__", build_id)
    with open(os.path.join(DIST, "sw.js"), "w", encoding="utf-8") as f:
        f.write(sw)
    data_out = os.path.join(DIST, "data")
    shutil.rmtree(data_out, ignore_errors=True)
    shutil.copytree(os.path.join(APP, "data"), data_out, ignore=shutil.ignore_patterns("_manifest.json"))
    return out


def sha(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def current_files() -> dict:
    out = {}
    for dirpath, _, names in os.walk(DIST):
        for n in names:
            p = os.path.join(dirpath, n)
            rel = os.path.relpath(p, DIST).replace(os.sep, "/")
            if rel != "index.html":
                out[rel] = sha(p)
    return out


def plan() -> dict:
    old = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {"files": {}}
    cur = current_files()
    changed = {k: os.path.relpath(os.path.join(DIST, k), ROOT) for k, v in cur.items() if old["files"].get(k) != v}
    removed = {k: None for k in old["files"] if k not in cur}
    page_changed = old.get("index_sha") != sha(os.path.join(DIST, "index.html"))
    return {"page_changed": page_changed, "files": {**changed, **removed}}


def record(url: str = "") -> None:
    old = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    json.dump({"url": url or old.get("url", ""), "index_sha": sha(os.path.join(DIST, "index.html")), "files": current_files()},
              open(MANIFEST, "w"), indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--url", default="")
    a = ap.parse_args()
    if a.record:
        record(a.url)
        print("recorded", MANIFEST)
        sys.exit(0)
    path = build()
    size = os.path.getsize(path)
    print(f"built {os.path.relpath(path, ROOT)} ({size / 1024:.0f} KB) and {len(current_files())} data files")
    if a.plan:
        pl = plan()
        print(json.dumps(pl, indent=1))
