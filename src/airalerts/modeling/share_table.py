"""Smoothed share table (docs/models/share_table.md). Not a learned tree: the cells are fixed by hand, the model only
counts. p of a cell = (true + m * p of its parent) / (rows + m), level by level from the root (the share of true in the
fit rows) through hour_kyiv, then (hour_kyiv, alert_active), then (hour_kyiv, alert_active, pause), where pause means
3 <= hours_since_strike < 24. Optional settings: recency weights of the fit rows (half-life in days counted back from
the newest fit row) and a first fit hour. predict reads only the three feature columns; t_utc only weights fit rows.

    .venv/bin/python -I -m airalerts.modeling.share_table    write data/predictions/share_table.parquet
"""
import sys

from ..gold.kyiv_hourly import LABEL
from . import runner

NAME = "share_table"
DESCRIPTION = ("share of true windows per cell hour_kyiv x alert_active x pause 3..24 h after a strike, each cell "
               "pulled to its parent with weight m = 24 rows (a hand-made table, not a learned tree)")
M = 24  # weight of the parent p, in fit rows
HALF_LIFE_DAYS = None  # recency weight of a fit row halves every this many days back from the newest fit row; None: equal
START = None  # fit rows before this UTC hour are dropped; None: keep all
PAUSE = (3, 24)  # hours_since_strike in [3, 24): the pause after an attack
COLUMNS = ("hour_kyiv", "alert_active", "hours_since_strike")


def cell_keys(hour, alert, since):
    """Keys of the cells of one row, from the root to the leaf."""
    pause = since is not None and PAUSE[0] <= since < PAUSE[1]
    return ((), (hour,), (hour, alert), (hour, alert, pause))


def fit(rows, m=M, half_life_days=HALF_LIFE_DAYS, start=START):
    """The table: cell key -> (weighted true, weighted rows, smoothed p), parents smoothed before their children."""
    ts = rows["t_utc"].to_pylist()
    newest = max(ts)
    sums = {}
    for x, y, *f in zip(ts, rows[LABEL].to_pylist(), *(rows[c].to_pylist() for c in COLUMNS)):
        if start is not None and x < start:
            continue
        w = 1.0 if half_life_days is None else 0.5 ** ((newest - x).total_seconds() / 86400 / half_life_days)
        for k in cell_keys(*f):
            s = sums.setdefault(k, [0.0, 0.0])
            s[0] += w * y
            s[1] += w
    cells = {}
    for k in sorted(sums, key=len):  # stable: every parent comes before its children
        wy, w = sums[k]
        cells[k] = (wy, w, wy / w if not k else (wy + m * cells[k[:-1]][2]) / (w + m))
    return cells


def predict(model, rows):
    """p of the deepest cell of each row seen in the fit rows: an unseen cell has 0 rows, so its p equals its parent's."""
    out = []
    for f in zip(*(rows[c].to_pylist() for c in COLUMNS)):
        p = None
        for k in cell_keys(*f):
            if k not in model:
                break
            p = model[k][2]
        out.append(float(p))
    return out


def main():
    runner.run(sys.modules[__name__])


if __name__ == "__main__":
    main()
