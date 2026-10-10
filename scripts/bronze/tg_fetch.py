"""Public Telegram channel -> raw JSONL via https://t.me/s/<channel> (stdlib only).
Usage: python3 -I tg_fetch.py <channel> <out.jsonl> [since] [delay] [before stop_id]
  since  default 2026-04-23T21:00:00Z, delay default 1.5 s between requests.
  before stop_id: range mode, to split one long backfill across processes: only posts with
  stop_id < post_id < before go to out (a part file); a rerun resumes from the part's oldest post.
       python3 -I tg_fetch.py merge <out.jsonl> <part.jsonl>...
  appends the part posts missing from out.
Run 1 walks back from the newest post to `since`, appending page by page.
Later runs append only posts newer than the file, then finish an interrupted backfill.
A post_id already in the file is never rewritten (its first version is kept). Rows are not sorted.
get() and parse() can be imported by other fetchers."""
import html, http.client, json, os, re, sys, time, urllib.request
from datetime import datetime, timezone

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


def utc(s):
    return datetime.fromisoformat(s).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(ch, before=None):
    url = f"https://t.me/s/{ch}" + (f"?before={before}" if before else "")
    for k in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except (OSError, http.client.HTTPException) as e:  # HTTPError, URLError, timeouts, resets
            code = getattr(e, "code", None)
            if code is not None and code != 429 and code < 500:
                raise
            print("retry", k + 1, url, e, file=sys.stderr)
            time.sleep(20 * (k + 1))
    sys.exit(f"fetch failed: {url}")


def clean(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    return html.unescape(re.sub(r"<[^>]+>", "", s)).replace("\xa0", " ").strip()


def text_of(b):
    # main text only: the reply quote is js-message_reply_text and does not match
    m = re.search(r'<div class="tgme_widget_message_text[^"]*js-message_text[^"]*"[^>]*>', b)
    if not m:
        return ""
    depth, i = 1, m.end()
    for t in re.finditer(r"<(/?)div\b[^>]*>", b[i:]):
        depth += -1 if t.group(1) else 1
        if depth == 0:
            return clean(b[i:i + t.start()])
    return clean(b[i:])


def parse(page):
    now = utc(datetime.now(timezone.utc).isoformat())
    for b in page.split('<div class="tgme_widget_message_wrap')[1:]:
        m = re.search(r'data-post="([^"/]+)/(\d+)"', b)
        t = re.search(r'class="tgme_widget_message_date"[^>]*>\s*<time[^>]*datetime="([^"]+)"', b)
        if not (m and t):
            continue
        v = re.search(r'<span class="tgme_widget_message_views">([^<]*)</span>', b)
        f = re.search(r'class="tgme_widget_message_forwarded_from_name"(?:\s+href="https://t\.me/([^"]+)")?[^>]*>(.*?)</(?:a|span)>', b, re.S)
        yield {"channel": m.group(1), "post_id": int(m.group(2)), "published_at": utc(t.group(1)),
               "text": text_of(b), "edited": bool(re.search(r'tgme_widget_message_meta">\s*edited', b)),
               "views": v.group(1) if v else None,
               "forwarded_from": (f.group(1) or clean(f.group(2))) if f else None,
               "url": f"https://t.me/{m.group(1)}/{m.group(2)}", "fetched_at": now}


def walk(before, stop_id, sink):
    """Pages back from `before` (None = newest) until `since` or a post_id <= stop_id."""
    pages = 0
    while True:
        posts = list(parse(get(ch, before)))
        pages += 1
        if not posts:
            if before is None:
                sys.exit(f"{ch}: 0 posts on the newest page (no such public channel or markup changed)")
            break
        sink([p for p in posts if p["post_id"] not in have and p["post_id"] > stop_id and p["published_at"] >= since])
        low = min(p["post_id"] for p in posts)
        if min(p["published_at"] for p in posts) < since or low <= stop_id or (before and low >= before):
            break
        before = low
        time.sleep(delay)
    return pages


def write(rows):
    rows = sorted(rows, key=lambda r: r["post_id"])
    if not rows:
        return
    with open(out, "a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            have[r["post_id"]] = r


if __name__ == "__main__" and sys.argv[1] == "merge":
    out, have, new = sys.argv[2], {}, {}
    for line in open(out, encoding="utf-8") if os.path.exists(out) else []:
        have.setdefault(json.loads(line)["post_id"], 1)
    for part in sys.argv[3:]:
        for line in open(part, encoding="utf-8"):
            r = json.loads(line)
            if r["post_id"] not in have:
                new.setdefault(r["post_id"], r)
    write(new.values())
    print(json.dumps({"out": out, "added": len(new), "rows": len(have)}))
elif __name__ == "__main__":
    ch, out = sys.argv[1], sys.argv[2]
    since = sys.argv[3] if len(sys.argv) > 3 else "2026-04-23T21:00:00Z"
    delay = float(sys.argv[4]) if len(sys.argv) > 4 else 1.5
    before, stop_id = (int(sys.argv[5]), int(sys.argv[6])) if len(sys.argv) > 6 else (None, 0)
    have = {}
    if os.path.exists(out):
        for line in open(out, encoding="utf-8"):
            r = json.loads(line)
            have.setdefault(r["post_id"], r)
    if before:  # range mode: page by page from the part's oldest post, or from `before`
        pages = walk(min(have, default=before), stop_id, write)
    elif not have:  # first run: append page by page, an interruption leaves a contiguous newest part
        pages = walk(None, 0, write)
    else:  # newer posts are buffered and written together, so a crash cannot leave a hole
        buf, top = [], max(have)
        pages = walk(None, top, buf.extend)
        write({r["post_id"]: r for r in buf}.values())
        oldest = min(have.values(), key=lambda r: r["post_id"])
        if oldest["published_at"] > since:  # finish an interrupted backfill
            time.sleep(delay)
            pages += walk(oldest["post_id"], 0, write)

    ts = sorted(r["published_at"] for r in have.values())
    print(json.dumps({"channel": ch, "pages": pages, "rows": len(have), "first": ts[0] if ts else None,
                      "last": ts[-1] if ts else None, "min_id": min(have, default=None), "max_id": max(have, default=None)}))
