# wx_fetch_run.py: python3 -I wx_fetch_run.py <out_dir> <run> [<run> ...]   run = 2026-10-09T12:00 (UTC)
# Also importable: wx_backfill.py uses http_get, fetch_run, rows_from_body, raw_path.
import csv, json, os, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

UTC, Z = timezone.utc, "%Y-%m-%dT%H:%M:%SZ"
VARS = ["cloud_cover", "precipitation", "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m", "visibility"]
COLS = ["run_utc", "valid_utc", "lead_h", "cloud_cover_pct", "precipitation_mm", "wind_speed_10m_kmh",
        "wind_gusts_10m_kmh", "wind_direction_10m_deg", "visibility_m", "available_at_utc", "fetched_at_utc"]
UNITS = {"time": "iso8601", "cloud_cover": "%", "precipitation": "mm", "wind_speed_10m": "km/h",
         "wind_gusts_10m": "km/h", "wind_direction_10m": "°", "visibility": "m"}
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
PAUSE_S = 1.0  # one request at a time, 1-2 s between requests (the caller sleeps)
ATTEMPTS = 5   # per request, on HTTP 429, 5xx and network errors; backoff 4, 8, 16, 32 s


class RunNotAvailable(Exception):
    """HTTP 400: the run is not published (yet) or is missing from the archive."""


class UnitsChanged(Exception):
    """hourly_units differ from UNITS: stop, do not guess (PARSING 3)."""


def http_get(url):
    for attempt in range(1, ATTEMPTS + 1):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        wait = 4 * 2 ** (attempt - 1)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 400:
                raise RunNotAvailable(e.read().decode("utf-8", "replace")[:300]) from None
            if e.code != 429 and e.code < 500:
                raise
            ra = e.headers.get("Retry-After", "")
            wait = min(int(ra), 120) if ra.isdigit() else wait
            err = e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            err = e
        if attempt == ATTEMPTS:
            raise err
        print(f"retry {attempt}/{ATTEMPTS - 1} in {wait}s after {err!r}", file=sys.stderr, flush=True)
        time.sleep(wait)


def raw_path(run, out_dir):
    return os.path.join(out_dir, "openmeteo_single_runs", f"ecmwf_ifs_{run:%Y%m%dT%H}.json")


def rows_from_body(run, body, fetched):
    """CSV rows of one run from the raw JSON bytes; stops (UnitsChanged) if the units are not the known ones."""
    j = json.loads(body)
    if j.get("hourly_units") != UNITS:
        raise UnitsChanged(j.get("hourly_units"))
    h = j["hourly"]
    avail = (run + timedelta(hours=8)).strftime(Z)
    out = []
    for i, t in enumerate(h["time"]):
        valid = datetime.fromisoformat(t).replace(tzinfo=UTC)
        out.append([run.strftime(Z), valid.strftime(Z), int((valid - run).total_seconds() // 3600)]
                   + [h[v][i] for v in VARS] + [avail, fetched])
    return out


def fetch_run(run, out_dir):
    q = urllib.parse.urlencode(dict(latitude=50.4501, longitude=30.5234, hourly=",".join(VARS), models="ecmwf_ifs",
                                    run=run.strftime("%Y-%m-%dT%H:%M"), timezone="UTC", format="json"), safe=",:")
    body = http_get("https://single-runs-api.open-meteo.com/v1/forecast?" + q)  # RunNotAvailable on HTTP 400
    fetched = datetime.now(UTC).strftime(Z)
    rows = rows_from_body(run, body, fetched)  # units are checked before anything is written
    path = raw_path(run, out_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "wb") as f:
        f.write(body)
    os.replace(path + ".tmp", path)
    yield from rows


if __name__ == "__main__":
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "ecmwf_ifs_runs.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(COLS)
        for n, arg in enumerate(sys.argv[2:]):
            if n:
                time.sleep(PAUSE_S)
            try:
                rows = list(fetch_run(datetime.fromisoformat(arg).replace(tzinfo=UTC), out_dir))
            except RunNotAvailable as e:
                print(arg, "HTTP 400", e)
                continue
            w.writerows(rows)
            print(arg, len(rows), rows[24])
