"""Bronze Telegram JSONL (docs/PARSING.md 0.1) for silver builders."""
import json

from .paths import BRONZE

TG = BRONZE / "telegram"


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
