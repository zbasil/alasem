"""Print a fingerprint of the live file without its timestamps (the workflow deploys only when it changes).

    python scripts/live_hash.py dist/web/data/live/now.json
"""
import hashlib
import json
import sys

try:
    doc = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, ValueError, IndexError):
    print("none")
    sys.exit(0)
doc.pop("generated_utc", None)
for m in doc.get("matches", {}).values():
    m.pop("fetched_utc", None)
print(hashlib.sha256(json.dumps(doc, sort_keys=True).encode("utf-8")).hexdigest())
