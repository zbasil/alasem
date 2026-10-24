"""Zip the project for delivery (code, tests, data, outputs, notebook, the ready-to-host page in dist/web).

    python scripts/package.py [destination.zip]
"""

import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# cache = re-downloadable StatsBomb files; snapshots and backups are local restore points (app/data is the current one)
SKIP_DIRS = {"__pycache__", ".pytest_cache", "nbrun", "cache", "node_modules", "snapshots", "backups", "userdata",
             "xgabora-full"}   # 56 MB, downloaded again by `python -m zsc multi --fetch`
SKIP_FILES = {"tune_stdout.txt", "season_backtest_stdout.txt", ".env"}


def main(dest: str):
    n = 0
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and (not d.startswith(".") or d == ".github")]
            for f in files:
                if f in SKIP_FILES or f.endswith(".pyc") or f.endswith(".zip"):
                    continue
                p = os.path.join(base, f)
                z.write(p, os.path.join("zahraa-supercomputer", os.path.relpath(p, ROOT)))
                n += 1
    print(f"wrote {dest} ({n} files, {os.path.getsize(dest) / 1e6:.1f} MB)")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "outputs", "zahraa-supercomputer.zip"))
