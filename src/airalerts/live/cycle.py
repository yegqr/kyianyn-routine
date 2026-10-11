"""One live cycle of the site (docs/ARCHITECTURE.md, "Живий сайт"): fetch the new posts, rebuild the silver tables the
finalist reads, then publish api/*.json from the live features. The systemd timer kyianyn-routine-cycle runs it every 5 minutes.

- DATA/cycle.lock keeps two cycles apart: a second one exits at once with code 0.
- The silver steps run only when the fetch brought new posts (or a step failed last time); else only the JSON is
  rewritten, so the hour rolls over and a stale page says so.
- New posts go to Jev through airalerts.jev (TYPESAFE_API_KEY from the service env file, else the vault). A failed step
  does not stop the cycle: the JSON is still written from what is there and now.json says it is stale.
- DATA/cycle_state.json keeps the last state; meta.json shows it as "pipeline".

    AIRALERTS_DATA=data/live .venv/bin/python -I -m airalerts.live.cycle --out DIR [--no-fetch]
"""
import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .. import paths
from . import fetch, model, publish

STEPS = (  # the order of docs/ARCHITECTURE.md "Як запустити", only what the finalist and the alert status read
    ("alerts", ("airalerts.silver.alerts",)),
    ("telegram_posts", ("airalerts.silver.telegram_posts",)),
    ("threat_classify", ("airalerts.silver.threat_hourly", "classify")),
    ("threat_hourly", ("airalerts.silver.threat_hourly",)),
    ("signals", ("airalerts.silver.signals",)),
)
STEP_TIMEOUT = 600  # seconds; the full rebuild of all five took about 65 s on 2026-10-11


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_posts(data):
    """New posts of the latest fetch pass, from DATA/fetch_log.jsonl (0 if there is none)."""
    try:
        last = (data / "fetch_log.jsonl").read_text(encoding="utf-8").splitlines()[-1]
        return sum(json.loads(last)["new"].values())
    except (OSError, IndexError, ValueError, KeyError):
        return 0


def silver(data):
    """Run the silver steps one by one in child processes; returns ({step: seconds}, error text or None)."""
    took = {}
    env = dict(os.environ, AIRALERTS_DATA=str(data))
    for name, args in STEPS:
        t0 = time.time()
        r = subprocess.run([sys.executable, "-I", "-m", *args], cwd=paths.ROOT, env=env, capture_output=True, text=True,
                           timeout=STEP_TIMEOUT)
        took[name] = round(time.time() - t0, 1)
        if r.returncode:
            tail = (r.stderr or r.stdout).strip().splitlines()[-1:] or ["no output"]
            return took, f"{name}: exit {r.returncode}: {tail[0][:300]}"
    return took, None


def run(out, data=None, do_fetch=True):
    data = paths.DATA if data is None else Path(data)
    lock = open(data / "cycle.lock", "a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("another cycle is running: nothing done")
        return 0
    with lock:
        t0, state_path = time.time(), data / "cycle_state.json"
        try:
            prev = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prev = {}
        state = {"last_cycle": now_iso(), "ok": True, "error": None, "new_posts": 0, "steps": {}}
        if do_fetch and fetch.run_once(data):
            state["error"] = "частина каналів не відповіла"
        state["new_posts"] = new_posts(data) if do_fetch else 0
        if state["new_posts"] or prev.get("ok") is False or not prev:
            state["steps"], err = silver(data)
            if err:
                state.update(ok=False, error=err)
        elif prev.get("silver_at"):
            state["silver_at"] = prev["silver_at"]
        if state["ok"]:
            state["silver_at"] = state.get("silver_at") or state["last_cycle"]
        try:
            m = json.loads((data / "live_model" / f"{model.NAME}.json").read_text(encoding="utf-8"))
            state["last_train"] = m["trained_at"]
        except (OSError, ValueError, KeyError):
            state["last_train"] = None
        state["cycle_seconds"] = round(time.time() - t0, 1)
        n = publish.publish(out, data=data, pipeline=state)
        state["cycle_seconds"], state["last_train"] = round(time.time() - t0, 1), n["model"]["trained_at"]
        model.write_json(state_path, state)
        f = n["forecast"]
        print(f"{state['last_cycle']}: {state['new_posts']} new posts, hour {n['hour']}, p {f['p']:.3f} {f['tier']}, "
              f"{state['cycle_seconds']} s" + (f"; error: {state['error']}" if state["error"] else "")
              + (f"; stale: {n['stale_reason']}" if n["stale"] else ""), flush=True)
        return 0 if state["ok"] else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -I -m airalerts.live.cycle")
    ap.add_argument("--out", required=True, type=Path, help="the site folder; the JSON goes to OUT/api/")
    ap.add_argument("--no-fetch", action="store_true", help="skip the Telegram fetch (rebuild and publish only)")
    a = ap.parse_args(argv)
    sys.exit(run(a.out, do_fetch=not a.no_fetch))


if __name__ == "__main__":
    main()
