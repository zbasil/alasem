"""One safe update: fetch sources -> rebuild standard data -> new app snapshot.

Each step records its result in data/status.json. A failed fetch keeps the previous raw file; a failed
data check keeps the previous standard data; a failed export keeps the previous app snapshot. The app
always shows the last good data together with its age and what failed.
"""

from __future__ import annotations

import traceback

from . import export, store


def run(offline: bool = False, log=print) -> dict:
    result = {"started": store.now_utc(), "steps": {}}
    st_update = {"last_update_attempt": result["started"]}
    if not offline:
        try:
            fetched = store.fetch_all(log=log)
            result["steps"]["fetch"] = fetched
            st_update["fetch"] = {k: {"status": v["status"], "at": result["started"], **({"error": v["error"]} if "error" in v else {})}
                                  for k, v in fetched.items()}
        except Exception as e:  # never stop the update because a source is down
            result["steps"]["fetch"] = {"status": "failed", "error": str(e)}
        try:                                                    # lineups and absences (only with a key)
            from . import apifootball
            result["steps"]["api_football"] = apifootball.fetch(log=log)
        except Exception as e:
            result["steps"]["api_football"] = {"status": "failed", "error": str(e)}
    try:
        man = store.build(log=log)
        result["steps"]["build"] = {"status": "ok", "data_version": man["data_version"]}
    except Exception as e:
        result["steps"]["build"] = {"status": "failed", "error": str(e).splitlines()[:6]}
        log(f"data build failed, previous data kept: {e}")
    try:
        export.build(log=log)
        result["steps"]["export"] = {"status": "ok"}
        st_update["last_good_export"] = store.now_utc()
    except Exception as e:
        result["steps"]["export"] = {"status": "failed", "error": str(e), "trace": traceback.format_exc()[-2000:]}
        log(f"export failed, previous app data kept: {e}")
    result["finished"] = store.now_utc()
    st_update["last_update"] = result
    store._write_status(st_update)
    return result
