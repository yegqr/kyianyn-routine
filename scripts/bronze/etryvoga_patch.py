"""eTryvoga patch for VA_Kyiv alert ends without a start (docs/PARSING.md section 1). Stdlib only.
Usage: python3 -I scripts/bronze/etryvoga_patch.py [hours]     (hours before the end, default 3)
For each orphan end e (from va_count.py, from T0): search https://t.me/s/UkraineAlarmSignal?before=<id> for the page
that holds time e, read pages back to e minus <hours> and append those posts (format 0.1, no duplicate post_id) to
data/bronze/telegram/UkraineAlarmSignal.jsonl. A rerun adds only what is missing. One request at a time, 1.5 s pause.
The start itself is chosen in silver (src/airalerts/silver/alerts.py)."""
import json, os, re, subprocess, sys, time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # python3 -I does not put the script directory on sys.path
import tg_fetch  # get() and parse()

ROOT = os.path.dirname(os.path.dirname(HERE))
VA = os.path.join(ROOT, "data/bronze/telegram/VA_Kyiv.jsonl")
OUT = os.path.join(ROOT, "data/bronze/telegram/UkraineAlarmSignal.jsonl")
CH, PAUSE = "UkraineAlarmSignal", 1.5
cache, last, requests = {}, [0.0], [0]


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def page(before=None):
    """Posts of ?before=<id> (None = newest page); one request at a time, paused, cached."""
    if before not in cache:
        time.sleep(max(0.0, PAUSE - (time.time() - last[0])))
        cache[before] = list(tg_fetch.parse(tg_fetch.get(CH, before)))
        last[0] = time.time()
        requests[0] += 1
        t = sorted(p["published_at"] for p in cache[before])
        print(f"GET before={before} posts={len(t)} {t[0] if t else '-'} .. {t[-1] if t else '-'}", file=sys.stderr)
    return cache[before]


def span(posts):
    t = [ts(p["published_at"]) for p in posts]
    return min(t), max(t)


def find(e):
    """A before=<id> whose page ends at or after time e, within 20 ids of e (step back, then bisect)."""
    newest = page(None)
    if not newest:
        sys.exit("0 posts on the newest page: markup changed or channel closed")
    if span(newest)[1] < e:
        sys.exit("time e is newer than the newest post")
    hi, step, lo = max(p["post_id"] for p in newest) + 1, 64, None
    while lo is None:
        b = max(hi - step, 1)
        posts = page(b)
        if not posts or span(posts)[1] < e:
            lo = b
        elif span(posts)[0] <= e:
            return b
        else:
            hi, step = b, step * 2
    while hi - lo > 20:
        mid = (lo + hi) // 2
        posts = page(mid)
        if posts and span(posts)[0] <= e <= span(posts)[1]:
            return mid
        if not posts or span(posts)[1] < e:
            lo = mid
        else:
            hi = mid
    return hi


def locate(e):
    """Canonical start of the walk: before=<id of the first post at or after e> + 1, the same on every run."""
    posts = page(find(e))
    return min(p["post_id"] for p in posts if ts(p["published_at"]) >= e) + 1


def walk(b, e, hours):
    """Pages back from before=b until a page starts earlier than e minus hours."""
    got = {}
    while True:
        posts = page(b)
        for p in posts:
            got.setdefault(p["post_id"], p)
        if not posts or span(posts)[0] < e - hours * 3600:
            return got
        nb = min(p["post_id"] for p in posts)
        if nb >= b:
            return got
        b = nb


def load(path):
    rows = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            rows.setdefault(r["post_id"], r)
    return rows


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    out = subprocess.run([sys.executable, "-I", os.path.join(HERE, "va_count.py"), VA],
                         capture_output=True, text=True, check=True).stdout
    ids = [int(x) for x in re.search(r"orphan ends: \[([^\]]*)\]", out).group(1).split(",") if x.strip()]
    va, have, total_new = load(VA), load(OUT), 0
    print("orphan ends:", ids)
    for pid in ids:
        e = ts(va[pid]["published_at"])
        got = walk(locate(e), e, hours)
        new = sorted((p for k, p in got.items() if k not in have), key=lambda p: p["post_id"])
        if new:
            with open(OUT, "a", encoding="utf-8") as fh:
                fh.write("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in new))
            have.update((p["post_id"], p) for p in new)
        total_new += len(new)
        t = sorted(p["published_at"] for p in got.values())
        print(json.dumps({"orphan_post": pid, "end": va[pid]["published_at"], "window_posts": len(got), "first": t[0],
                          "last": t[-1], "ids": [min(got), max(got)], "new_rows": len(new)}))
    t = sorted(p["published_at"] for p in have.values())
    print(json.dumps({"file": os.path.relpath(OUT, ROOT), "rows": len(have), "first": t[0] if t else None,
                      "last": t[-1] if t else None, "new_rows": total_new, "requests": requests[0]}))


if __name__ == "__main__":
    main()
