"""The frozen hourly models judged per night (docs/adr/0010-night-question.md): alarm at any hour against bedtime
(21..23), against the rule "go to the corridor at any night alert", night-level ROC AUC at bedtime and a stricter
threshold chosen on development nights. Descriptive only, run after `evaluate final`.

    .venv/bin/python -I scripts/analysis/strikes_by_night.py    (from the project root)
"""
import duckdb
from collections import defaultdict
from datetime import timedelta
from airalerts.evaluation import split
from airalerts.strikes import score as ev

h = ev.Hours(split.load())
models, _ = ev.load_models(h.at)
names = ("share_table", "logistic", "lgbm", "naive_7d")
dev = [i for i, k in enumerate(h.test) if not k]
thr = {m: ev.best_threshold([h.y[i] for i in dev], [models[m][i] for i in dev]) for m in names}
con = duckdb.connect()
strikes = {r[0] for r in con.execute("SELECT hour_utc FROM 'data/silver/kyiv_threat_hourly.parquet' WHERE missile_strike").fetchall()}
alerts = [r[0] for r in con.execute("SELECT start_utc FROM 'data/silver/kyiv_alerts.parquet'").fetchall()]

def night_of(x):
    k = x + timedelta(hours=3)
    if k.hour >= 20: return k.date()
    if k.hour < 8: return k.date() - timedelta(days=1)
    return None

nights = defaultdict(list)
for i, x in enumerate(h.at):
    d = night_of(x)
    if d: nights[d].append(i)
nights = {d: ix for d, ix in nights.items() if len(ix) == 12}       # only complete nights
first_strike = {}
for s in sorted(strikes):
    d = night_of(s)
    if d in nights and d not in first_strike: first_strike[d] = s
alert_nights = {night_of(a) for a in alerts}

def table(sel, label):
    n_att = sum(d in first_strike for d in sel)
    print(f"\n{label}: {len(sel)} nights, {n_att} with a missile attack, {len(sel) - n_att} quiet")
    print(f"  {'rule':34s} caught  missed  false nights  quiet nights right  precision")
    def row(name, flag, caught):
        tp = sum(1 for d in sel if d in first_strike and caught(d)); fn = n_att - tp
        fp = sum(1 for d in sel if d not in first_strike and flag(d)); tn = len(sel) - n_att - fp
        prec = tp / (tp + fp) if tp + fp else float('nan')
        print(f"  {name:34s} {tp:3d}/{n_att:<3d} {fn:5d}   {fp:5d}         {tn:5d}             {prec:.2f}")
    row("alert rule: any alert at night", lambda d: d in alert_nights, lambda d: any(night_of(a) == d and a <= first_strike[d] + timedelta(hours=1) for a in alerts))
    for m in names:
        p, t = models[m], thr[m]
        row(f"{m} wake-up (any hour)", lambda d: any(p[i] >= t for i in nights[d]),
            lambda d: any(p[i] >= t and h.at[i] <= first_strike[d] for i in nights[d]))
    for m in names:
        p, t = models[m], thr[m]
        bed = lambda d: max(p[i] for i in nights[d] if (h.at[i] + timedelta(hours=3)).hour in (21, 22, 23)) >= t
        row(f"{m} bedtime (21..23)", bed, bed)

table([d for d in nights if h.at[nights[d][0]] < split.TEST_START], "DEVELOPMENT 07-04..08-28")
table([d for d in nights if h.at[nights[d][0]] >= split.TEST_START], "TEST 08-29..10-09")

print("\nnight-level ROC AUC of the bedtime score (max p 21..23), threshold-free; 0.5 = no better than chance")
for label, sel in (("development", [d for d in nights if h.at[nights[d][0]] < split.TEST_START]),
                   ("test", [d for d in nights if h.at[nights[d][0]] >= split.TEST_START])):
    y = [int(d in first_strike) for d in sel]
    cells = []
    for m in names:
        s = [max(models[m][i] for i in nights[d] if (h.at[i] + timedelta(hours=3)).hour in (21, 22, 23)) for d in sel]
        cells.append(f"{m} {ev.roc_auc(y, s):.2f}")
    print(f"  {label:12s} " + "  ".join(cells))

print("\nwake-up mode with a stricter threshold chosen on development: the highest threshold that still catches >= 13 of 16 dev attack nights")
devn = [d for d in nights if h.at[nights[d][0]] < split.TEST_START]
testn = [d for d in nights if h.at[nights[d][0]] >= split.TEST_START]
def counts(m, t, sel):
    p = models[m]
    tp = sum(1 for d in sel if d in first_strike and any(p[i] >= t and h.at[i] <= first_strike[d] for i in nights[d]))
    fp = sum(1 for d in sel if d not in first_strike and any(p[i] >= t for i in nights[d]))
    return tp, sum(d in first_strike for d in sel), fp, sum(d not in first_strike for d in sel)
for m in ("share_table", "logistic", "lgbm"):
    cand = sorted({models[m][i] for d in devn for i in nights[d]}, reverse=True)
    t = next(v for v in cand if counts(m, v, devn)[0] >= 13)
    a, b, c, e = counts(m, t, devn); a2, b2, c2, e2 = counts(m, t, testn)
    print(f"  {m:12s} threshold {t:.3f} | dev caught {a}/{b}, false nights {c}/{e} | test caught {a2}/{b2}, false nights {c2}/{e2}")
