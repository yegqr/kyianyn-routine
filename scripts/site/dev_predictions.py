"""The development predictions of the frozen quiet model for the site: the scene "thresholds" of the methodology deck
(site/assets/js/scenes/08-thresholds.js) draws one dot per quiet-now development hour.

Rebuilt exactly as airalerts.quiet.forecast.rules() does it: quiet.dev_folds, walkforward.fold_predictions of the
frozen model logit_signals, then only the quiet_now rows. Stops unless the two thresholds come out as forecast.BUSY_AT
(the highest threshold that still catches 80% of the busy windows) and forecast.HIGH_AT (the upper third).
Writes site/data/dev_predictions.json: [{"p": 0.1234, "busy": 0 or 1}, ...] in time order.

    .venv/bin/python -I scripts/site/dev_predictions.py    (from the project root)
"""
import json
import sys
from pathlib import Path

from airalerts.evaluation import metrics, walkforward
from airalerts.quiet import forecast, score as quiet

OUT = Path(__file__).resolve().parents[2] / "site" / "data" / "dev_predictions.json"


def development():
    """(p, busy) of every quiet-now development hour, in time order, as forecast.rules() builds them."""
    t = quiet.load()
    folds = quiet.dev_folds(t)
    p = walkforward.fold_predictions(quiet.SPEC, forecast.MODEL["fit"], forecast.MODEL["predict"], folds)
    rows = [r for _, _, ev in folds for r in ev.select([quiet.LABEL, "quiet_now"]).to_pylist()]
    return [(p[i], int(r[quiet.LABEL])) for i, r in enumerate(rows) if r["quiet_now"]]


def share(part, whole):
    return f"{len(part) / len(whole):.0%}" if whole else "none"


def main():
    hours = development()
    p, y = [v for v, _ in hours], [b for _, b in hours]
    s = sorted(p)
    busy_at, high_at = metrics.recall_threshold(y, p, forecast.RECALL), s[2 * len(s) // 3]
    busy = [v for v, b in hours if b]
    low = [b for v, b in hours if v < busy_at]
    high = [b for v, b in hours if v >= high_at]
    print(f"rows {len(hours)}, busy {len(busy)} ({share(busy, hours)})")
    print(f"busy_at {busy_at:.3f}: busy windows caught {share([v for v in busy if v >= busy_at], busy)}")
    print(f"high_at {high_at:.3f}: hours at or above it {share([v for v in p if v >= high_at], p)}")
    print(f"tiers: low (p < busy_at) {share(low, hours)} of hours, truly quiet {share([b for b in low if not b], low)}; "
          f"high (p >= high_at) busy {share([b for b in high if b], high)}")
    if (round(busy_at, 3), round(high_at, 3)) != (forecast.BUSY_AT, forecast.HIGH_AT):
        sys.exit(f"the thresholds differ from forecast.py {forecast.BUSY_AT}, {forecast.HIGH_AT}: nothing written")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps([{"p": round(v, 4), "busy": b} for v, b in hours], separators=(",", ":")) + "\n")
    print(f"{len(hours)} rows written to {OUT.relative_to(OUT.parents[2])}")


if __name__ == "__main__":
    main()
