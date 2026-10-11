"""Is the 3 hour forecast any good, on the hours that are quiet now (no alert, no attack in the last hour)? Descriptive,
frozen models, after `quiet final`:
1. against the obvious rules: paired BSS and ROC AUC differences of logit_signals against recency_table ("an attack
   was recent, so more will come") and hour_recency_nb (time of day plus recency), weekly walk-forward predictions,
   95% bootstrap over noon-to-noon days;
2. massive attacks against noise: the forecast's risk level before windows that stayed quiet, had drones only, a missile
   threat, or a missile strike;
3. practice: how often an official air raid alert in Kyiv started within 3 hours after each forecast word.
Parts 2 and 3 use the person's forecast refitted every hour (forecast.py). About 1 minute.

    .venv/bin/python -I scripts/analysis/forecast_value.py    (from the project root)
"""
import random
from datetime import timedelta

import duckdb

from airalerts.modeling import evaluate, forecast, quiet, split, tasks

HOUR = timedelta(hours=1)
t = quiet.load()
at = tasks.scored(quiet.SPEC, t)
folds = quiet.dev_folds(t) + quiet.test_folds(t)
rows = [r for _, _, ev in folds for r in ev.select([quiet.LABEL, "quiet_now"]).to_pylist()]
models = tasks.load_predictions(quiet.SPEC, at)[0]
clim = tasks.climatology(quiet.SPEC, folds)

print("1. Against the obvious rules (quiet-now hours, weekly walk-forward, difference = logit_signals minus the rule)")
for part, keep in (("dev ", lambda x: x < split.TEST_START), ("test", lambda x: x >= split.TEST_START)):
    idx = [i for i, x in enumerate(at) if keep(x) and rows[i]["quiet_now"]]
    groups = quiet.days(idx, at)
    y = [int(rows[i][quiet.LABEL]) for i in range(len(at))]
    for rule in ("recency_table", "hour_recency_nb"):
        rnd, d_bss, d_auc = random.Random(tasks.SEED), [], []
        for _ in range(tasks.N_BOOT):
            b = [i for g in [rnd.choice(groups) for _ in groups] for i in g]
            yy, cc = [y[i] for i in b], [clim[i] for i in b]
            s = {m: tasks.scores(yy, [models[m][i] for i in b], cc) for m in ("logit_signals", rule)}
            d_bss.append(s["logit_signals"]["bss"] - s[rule]["bss"])
            d_auc.append(s["logit_signals"]["roc_auc"] - s[rule]["roc_auc"])
        yy, cc = [y[i] for i in idx], [clim[i] for i in idx]
        s = {m: tasks.scores(yy, [models[m][i] for i in idx], cc) for m in ("logit_signals", rule)}
        ci = lambda v: f"[{sorted(v)[25]:+.3f}, {sorted(v)[974]:+.3f}]"
        print(f"  {part} vs {rule:15s}: BSS {s['logit_signals']['bss']:.3f} vs {s[rule]['bss']:.3f}, difference {ci(d_bss)}; "
              f"ROC AUC {s['logit_signals']['roc_auc']:.3f} vs {s[rule]['roc_auc']:.3f}, difference {ci(d_auc)}")

both = forecast.tables()
flags = {r[0]: r[1:] for r in duckdb.sql("SELECT hour_utc, drone_threat, missile_threat, missile_strike FROM 'data/silver/kyiv_threat_hourly.parquet'").fetchall()}
alerts = duckdb.sql("SELECT start_utc, coalesce(end_utc, start_utc + INTERVAL 1 HOUR) FROM 'data/silver/kyiv_alerts.parquet'").fetchall()
out = {"dev": [], "test": []}
for i, x in enumerate(at):
    if not rows[i]["quiet_now"]:
        continue
    f = forecast.forecast(x, both)
    ahead = [flags.get(x + k * HOUR, (False, False, False)) for k in range(3)]
    kind = ("missile strike" if any(a[2] for a in ahead) else "missile threat" if any(a[1] for a in ahead)
            else "drones only" if any(a[0] for a in ahead) else "quiet")
    alert = any(s < x + 3 * HOUR and e > x for s, e in alerts)
    out["test" if x >= split.TEST_START else "dev"].append((f["verdict"][1], kind, alert))

LEVELS = ("швидше тихо", "середній ризик", "високий ризик")
print("\n2. Risk level the forecast gave before each kind of 3 hours (person's forecast, quiet-now hours)")
for part, r in out.items():
    for kind in ("quiet", "drones only", "missile threat", "missile strike"):
        g = [v for v in r if v[1] == kind]
        if g:
            print(f"  {part} {kind:15s} {len(g):4d} h: " + ", ".join(f"{lv} {sum(v[0] == lv for v in g) / len(g):.0%}" for lv in LEVELS))
print("\n3. An official air raid alert in Kyiv within the next 3 hours, by forecast word (quiet-now hours)")
for part, r in out.items():
    print(f"  {part}: all {len(r)} h, alert within 3 h {sum(v[2] for v in r) / len(r):.0%}; " + "; ".join(
        f"{lv} {sum(v[0] == lv for v in r)} h, alert {sum(v[2] for v in r if v[0] == lv) / max(1, sum(v[0] == lv for v in r)):.0%}" for lv in LEVELS))
    said_quiet = [v for v in r if v[0] == LEVELS[0]]
    print(f"        right answers if 'quiet' = no alert: {sum(not v[2] for v in said_quiet)}/{len(said_quiet)}; "
          f"'always not quiet' rule right on {sum(v[2] for v in r)}/{len(r)} hours")
