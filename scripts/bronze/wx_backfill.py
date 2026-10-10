# wx_backfill.py: python3 -I scripts/bronze/wx_backfill.py [--out DIR] [--from 2026-04-23T00:00] [--to RUN] [--dry-run]
# Every 6-hourly ECMWF IFS run from --from to the newest published one (PARSING 3): one raw JSON per run in
# <out>/openmeteo_single_runs/, rows in <out>/ecmwf_ifs_runs.csv, HTTP 400 runs in <out>/ecmwf_ifs_missing_runs.csv.
# Resumable: a run that has a file is not fetched again, a CSV row is never written twice. A run listed as
# HTTP 400 is asked again only while it is younger than 48 h (it may be "not published yet").
import argparse, csv, json, os, sys, time
from collections import Counter
from datetime import datetime, timedelta, timezone

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wx_fetch_run as wx  # noqa: E402

UTC, Z = wx.UTC, wx.Z
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
META_URL = "https://api.open-meteo.com/data/ecmwf_ifs/static/meta.json"
MISSING_COLS = ["run_utc", "http_status", "reason", "checked_at_utc"]
RETRY_WINDOW, STEP = timedelta(hours=48), timedelta(hours=6)


def parse(s):
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


def read_col(path, col=0):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        r = csv.reader(f)
        next(r, None)
        return [row[col] for row in r if row]


def append(path, header, rows):
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerows(rows)
        f.flush()
        os.fsync(f.fileno())


def newest_run(now):
    """Newest run whose availability time (meta.json) is in the past."""
    meta = json.loads(wx.http_get(META_URL))
    init = datetime.fromtimestamp(meta["last_run_initialisation_time"], UTC)
    avail = datetime.fromtimestamp(meta["last_run_availability_time"], UTC)
    return init if avail <= now else init - STEP


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "bronze", "weather"))
    ap.add_argument("--from", dest="first", default="2026-04-23T00:00")
    ap.add_argument("--to", default=None, help="last run to take (never later than the newest published)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    out = args.out
    runs_csv, miss_csv = os.path.join(out, "ecmwf_ifs_runs.csv"), os.path.join(out, "ecmwf_ifs_missing_runs.csv")
    os.makedirs(os.path.join(out, "openmeteo_single_runs"), exist_ok=True)

    now = datetime.now(UTC)
    last = newest_run(now)
    if args.to:
        last = min(last, parse(args.to))
    runs, r = [], parse(args.first)
    while r <= last:
        runs.append(r)
        r += STEP
    key = {r: r.strftime(Z) for r in runs}
    has_file = {r: os.path.exists(wx.raw_path(r, out)) for r in runs}
    in_csv, missing = set(read_col(runs_csv)), set(read_col(miss_csv))
    todo = [r for r in runs if not has_file[r] and not (key[r] in missing and r < now - RETRY_WINDOW)]
    heal = [r for r in runs if has_file[r] and key[r] not in in_csv]  # file written, crash before its CSV rows
    print(f"now {now.strftime(Z)}  runs in range {len(runs)} ({runs[0]:%Y-%m-%dT%H:%M}..{runs[-1]:%Y-%m-%dT%H:%M})  "
          f"to fetch {len(todo)}  to heal from file {len(heal)}", flush=True)

    fetched_n, failed = 0, []
    if not args.dry_run:
        for r in heal:
            p = wx.raw_path(r, out)
            with open(p, "rb") as f:
                rows = wx.rows_from_body(r, f.read(), datetime.fromtimestamp(os.path.getmtime(p), UTC).strftime(Z))
            append(runs_csv, wx.COLS, rows)
            in_csv.add(key[r])
        for n, r in enumerate(todo):
            if n:
                time.sleep(wx.PAUSE_S)
            try:
                rows = list(wx.fetch_run(r, out))
            except wx.RunNotAvailable as e:
                if key[r] not in missing:
                    append(miss_csv, MISSING_COLS, [[key[r], 400, str(e), datetime.now(UTC).strftime(Z)]])
                    missing.add(key[r])
                print(key[r], "HTTP 400, listed and skipped", flush=True)
                continue
            except wx.UnitsChanged as e:
                sys.exit(f"STOP {key[r]}: hourly_units changed: {e}")
            except Exception as e:  # network or HTTP error after the retries: left for the next run
                failed.append(key[r])
                print(key[r], "FAILED", repr(e), flush=True)
                continue
            if key[r] not in in_csv:
                append(runs_csv, wx.COLS, rows)
                in_csv.add(key[r])
            has_file[r] = True
            fetched_n += 1
            if fetched_n % 25 == 0 or n == len(todo) - 1:
                print(f"{n + 1}/{len(todo)} {key[r]} {len(rows)} rows", flush=True)

    files = [r for r in runs if os.path.exists(wx.raw_path(r, out))]
    gap = [key[r] for r in runs if r not in set(files) and key[r] in missing]
    open_ = [key[r] for r in runs if r not in set(files) and key[r] not in missing]
    per_run = Counter(read_col(runs_csv))
    odd = {key[r]: per_run[key[r]] for r in files if per_run[key[r]] != 168}
    print(f"runs in range: {len(runs)}  HTTP 400 runs (listed, no file): {len(gap)} {gap}")
    print(f"run files in range: {len(files)}  runs in range minus HTTP 400 runs: {len(runs) - len(gap)}")
    print(f"runs with no file and not listed (to retry): {open_}")
    print(f"CSV rows: {sum(per_run.values())}  168 x files: {168 * len(files)}  runs with other row count: {odd}")
    print(f"fetched this run: {fetched_n}  failed: {failed}", flush=True)
    return 1 if failed or open_ else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
