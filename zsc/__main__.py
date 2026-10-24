"""Command line.

    python -m zsc serve [--port 8000]     run the app at http://127.0.0.1:8000
    python -m zsc update [--offline]      fetch sources, rebuild data, new app snapshot
    python -m zsc data                    rebuild data/standard from data/raw only
    python -m zsc export                  new app snapshot from the current data
    python -m zsc multi [--fetch] [--evaluate]  Premier League + Champions League files (also into app/data)
    python -m zsc evaluate                full honest evaluation (about 6 minutes)
    python -m zsc status                  data status and snapshots
    python -m zsc snapshots               list app snapshots
    python -m zsc restore <stamp>         make an earlier snapshot the app's data again
"""

from __future__ import annotations

import json
import os
import subprocess
import sys


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "serve":
        from .server import serve
        port = int(rest[rest.index("--port") + 1]) if "--port" in rest else None
        host = rest[rest.index("--host") + 1] if "--host" in rest else None
        serve(host, port)
    elif cmd == "update":
        from .update import run
        res = run(offline="--offline" in rest)
        print(json.dumps({k: v.get("status") if isinstance(v, dict) else v for k, v in res["steps"].items()}, indent=1))
    elif cmd == "data":
        from .store import build
        build()
    elif cmd == "export":
        from .export import build
        build()
    elif cmd == "multi":
        from .multi import export as multi_export, fetch as multi_fetch
        from .paths import APP_DATA
        if "--fetch" in rest:
            print(json.dumps(multi_fetch(), indent=1))
        res = multi_export(APP_DATA, evaluate="--evaluate" in rest)
        print(json.dumps({k: v for k, v in res.items() if k != "epl_eval"}, indent=1, ensure_ascii=False, default=str))
    elif cmd == "evaluate":
        from .paths import ROOT
        return subprocess.call([sys.executable, os.path.join(ROOT, "scripts", "evaluate_all.py")] + rest)
    elif cmd == "status":
        from .store import status
        print(json.dumps(status(), indent=1, ensure_ascii=False))
    elif cmd == "snapshots":
        from .paths import SNAPSHOTS
        for d in sorted(os.listdir(SNAPSHOTS)) if os.path.isdir(SNAPSHOTS) else []:
            print(d)
    elif cmd == "restore":
        from .export import publish_snapshot
        if not rest:
            print("usage: python -m zsc restore <stamp>")
            return 2
        publish_snapshot(rest[0])
        print(f"app data restored to snapshot {rest[0]}")
    else:
        print(f"unknown command {cmd}\n{__doc__}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
