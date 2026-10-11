"""Jev (TypeSafe System One) client shared by silver builders. How to ask good questions: docs/JEV.md.

- Each request goes through `vault call typesafe-general`, so the API key never enters this process. On a server
  without the vault, set TYPESAFE_API_KEY: the request then goes straight to the API with `Authorization: Bearer`;
  the key is never printed, logged or cached.
- The model is pinned to jev-1.13.0, so reruns do not change when the jev-latest alias moves.
- Every answer is cached in data/silver/_jev_cache/<tag>/ under a hash of the whole request:
  a rerun with the same state and questions costs nothing and returns the same answer.
- HTTP 429, 529 and 5xx are retried with exponential backoff; any other error raises JevError.
"""
import hashlib
import http.client
import json
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from .paths import SILVER

MODEL = "jev-1.13.0"
URL = "https://api.typesafe.ai/v1/systemone"
CACHE = SILVER / "_jev_cache"
USD_PER_MTOK = 0.042  # input tokens only, output is free (docs.typesafe.ai/models)


class JevError(RuntimeError):
    pass


def _post_key(body, key, timeout=120):
    """One HTTPS call with the key from TYPESAFE_API_KEY, the same request as through the vault. Returns (status, body
    text); a network error or timeout is 599, retried like a 5xx. An error text never carries the key."""
    key = key.strip()  # a key saved with its line end
    if not key or not key.isascii() or not key.isprintable() or " " in key:
        # http.client would refuse such a header with the whole key in its error, so stop here and name no key
        raise JevError("TYPESAFE_API_KEY is not a valid key: printable ASCII without spaces expected")
    req = urllib.request.Request(URL, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8").strip()
    except urllib.error.HTTPError as e:
        status, text = e.code, e.read().decode("utf-8", "replace")
    except (OSError, http.client.HTTPException) as e:  # URLError, timeouts, resets
        status, text = 599, type(e).__name__
    return status, text.replace(key, "<key>").strip()


def _post(body, timeout=120):
    """One HTTPS call: with TYPESAFE_API_KEY when it is set, else through the vault broker. Returns (status, body text)."""
    if key := os.environ.get("TYPESAFE_API_KEY"):
        return _post_key(body, key, timeout)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False)
    try:
        r = subprocess.run(["vault", "call", "typesafe-general", "POST", URL, "-H", "Content-Type: application/json",
                            "-d", "@" + f.name, "-i"], capture_output=True, text=True, timeout=timeout)
    finally:
        os.unlink(f.name)
    if r.returncode == 3:
        raise JevError("vault is closed: the user has to run `vault unlock`")
    head = r.stderr.splitlines()  # with -i the status line and headers go to stderr, the body to stdout
    if not head or not head[0].strip().isdigit():
        raise JevError(f"unexpected vault output (exit {r.returncode}): {(r.stderr or r.stdout)[:300]}")
    return int(head[0]), r.stdout.strip()


def ask(state, questions, tag, retries=6):
    """Evaluate `questions` (dict of noul/choice/score) against `state`; returns the `answers` dict."""
    body = {"model": MODEL, "state": state, "questions": questions}
    key = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    path = CACHE / tag / key[:2] / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))["response"]["answers"]
    status, text = None, ""
    for attempt in range(retries):
        try:
            status, text = _post(body)
        except subprocess.TimeoutExpired:
            status = 599
        if status == 200:
            resp = json.loads(text)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"request": body, "response": resp}, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, path)
            return resp["answers"]
        if status in (429, 529) or status >= 500:
            time.sleep(min(60, 2 ** attempt))
            continue
        raise JevError(f"HTTP {status}: {text[:500]}")
    raise JevError(f"gave up after {retries} attempts, last HTTP {status}: {text[:300]}")


def ask_many(items, tag, workers=4):
    """items: list of (state, questions). Answers come back in the same order. 4 workers: far below 80 requests/s."""
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(lambda sq: ask(sq[0], sq[1], tag), items))


def usage(tag=None):
    """Paid calls, input tokens and USD so far, counted from the cache (one cached file = one paid call)."""
    calls = tokens = 0
    for p in (CACHE / tag if tag else CACHE).rglob("*.json"):
        calls += 1
        tokens += json.loads(p.read_text(encoding="utf-8"))["response"].get("usage", {}).get("input_tokens", 0)
    return {"calls": calls, "input_tokens": tokens, "usd": round(tokens / 1e6 * USD_PER_MTOK, 4)}


if __name__ == "__main__":  # python -m airalerts.jev [tag]: spend so far
    import sys
    print(usage(sys.argv[1] if len(sys.argv) > 1 else None))
