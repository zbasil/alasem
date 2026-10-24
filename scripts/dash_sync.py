"""Keep the published app's data in step with outputs/dashboard/*.csv.

    python scripts/dash_sync.py status                 # datasets whose CSV changed since the last upload
    python scripts/dash_sync.py record ID URL VERSION  # after uploading ID's CSV and updating its document

The manifest (outputs/dashboard_manifest.json) remembers, for every dataset the app
reads, the uploaded file's url, its sha256 and the store document's version, so an
update pins the right version and re-uploads only what changed.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASH = os.path.join(ROOT, "outputs", "dashboard")
MANIFEST = os.path.join(ROOT, "outputs", "dashboard_manifest.json")
ARTIFACT = "https://claude.ai/artifact/Y6aQg9z4MxgUrQRp5NvjRX"


def sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load() -> dict:
    with open(MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)


def save(man: dict) -> None:
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=1, ensure_ascii=False)


def changed(man: dict) -> list[str]:
    out = []
    for ds, info in sorted(man["datasets"].items()):
        p = os.path.join(DASH, f"{ds}.csv")
        if os.path.exists(p) and sha256(p) != info["sha256"]:
            out.append(ds)
    return out


def main(argv: list[str]) -> None:
    man = load()
    if not argv or argv[0] == "status":
        ch = changed(man)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        print(json.dumps({"artifact": man["artifact"], "now": now, "changed": [
            {"id": d, "file": os.path.join(DASH, f"{d}.csv"), "if_version": man["datasets"][d]["version"]} for d in ch]},
            ensure_ascii=False, indent=1))
    elif argv[0] == "record":
        ds, url, version = argv[1], argv[2], int(argv[3])
        p = os.path.join(DASH, f"{ds}.csv")
        man["datasets"][ds] = {"url": url, "sha256": sha256(p), "version": version}
        save(man)
        print(f"recorded {ds}: {url} v{version}")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
