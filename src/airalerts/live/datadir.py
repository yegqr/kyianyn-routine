"""Live data dir made from the research data, so the live steps (AIRALERTS_DATA=DIR) never write into data/bronze,
data/silver or data/gold.
Usage: .venv/bin/python -I -m airalerts.live.datadir init DIR      (DIR relative to the repository root, e.g. data/live)
- bronze Telegram JSONL of the live channels (CHANNELS of live/fetch.py): a real copy, the live fetch appends to it in place;
- silver and gold Parquet: a real copy, the live steps rewrite them;
- silver/_jev_cache: a hard link per file: a cache file is written once (os.replace) and never changed, and a new live
  answer is a new file in DIR only.
A second init only adds what is missing. The research dirs are only read."""
import os
import shutil
import sys
from pathlib import Path

from ..paths import ROOT
from .fetch import CHANNELS

RESEARCH = ROOT / "data"


def copy(src, dst):
    """A real copy through a temporary file, so a cut init leaves no half file. False if dst is already there."""
    if dst.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)
    return True


def init(dest):
    dest = ROOT / dest
    frozen = [RESEARCH] + [RESEARCH / d for d in ("bronze", "silver", "gold")]
    if dest.resolve() == RESEARCH.resolve() or any(dest.resolve().is_relative_to(d.resolve()) for d in frozen[1:]):
        sys.exit(f"{dest} is research data: choose another dir, e.g. data/live")
    n = {"copied": 0, "linked": 0, "kept": 0}
    files = [RESEARCH / "bronze" / "telegram" / f"{ch}.jsonl" for ch in CHANNELS]
    files += sorted((RESEARCH / "silver").glob("*.parquet")) + sorted((RESEARCH / "gold").glob("*.parquet"))
    for src in files:
        n["copied" if copy(src, dest / src.relative_to(RESEARCH)) else "kept"] += 1
    for d, _, names in os.walk(RESEARCH / "silver" / "_jev_cache"):
        out = dest / Path(d).relative_to(RESEARCH)
        out.mkdir(parents=True, exist_ok=True)
        for name in names:
            if name.endswith(".tmp"):
                continue  # a cut write, not an answer
            if (out / name).exists():
                n["kept"] += 1
            else:
                os.link(Path(d) / name, out / name)  # same filesystem as data/, a cross-device dir fails here
                n["linked"] += 1
    print(f"{dest}: {n['copied']} files copied, {n['linked']} Jev cache files hard linked, {n['kept']} already there")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "init":
        sys.exit(__doc__)
    init(sys.argv[2])
