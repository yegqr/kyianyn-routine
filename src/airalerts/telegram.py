"""Bronze Telegram JSONL (docs/PARSING.md 0.1) for silver builders, and the check times the live fetch records."""
import json

from .paths import BRONZE

TG = BRONZE / "telegram"
CHECKED = "_checked.json"  # in TG, {channel: ISO UTC}: written only by the live fetch, absent from the research bronze


def load(channel):
    """Posts of one channel: the first stored version of each post_id, sorted by post_id."""
    rows = {}
    with open(TG / f"{channel}.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            rows.setdefault(r["post_id"], r)
    return [rows[k] for k in sorted(rows)]


def channels():
    return sorted(p.stem for p in TG.glob("*.jsonl"))


def checks(tg=None):
    """{channel: ISO UTC} of TG/_checked.json (or of the dir `tg`): when the live fetch last fetched each channel without
    error, the time just before its first page request of that pass, so bronze holds every post published before it.
    Empty when the file is missing."""
    try:
        with open((TG if tg is None else tg) / CHECKED, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def checked_at(channel):
    """The recorded check time of `channel` (ISO UTC), or None when the file or the entry is missing."""
    return checks().get(channel)
