"""The numbers of the methodology scene "Наскільки можна вірити моделі": site/data/trust.json, one block per question,
each with its "source" (a file or a command). Always the research data under data/: AIRALERTS_DATA is ignored.

- split: how the hours of gold kyiv_quiet were split (airalerts.evaluation.split, docs/adr/0008-time-split.md);
- evaluation: BSS and ROC AUC with 95% bootstrap intervals on quiet-now hours, of the finalist and the reference
  models, recomputed from data/predictions/quiet by walkforward.bootstrap; every cell must equal
  reports/quiet_leaderboard.md;
- replay: what the site would have said hour by hour: airalerts.live.model.replay() with its default cadence (read back
  from the retrain moments of the call), scored on quiet-now hours with a known target; y_alert_3h as the live features
  define it (features.alert_ahead on data/silver/kyiv_alerts.parquet); docs_weekly: the same questions for the weekly
  refit, read from docs/quiet/forecast.md;
- obvious_rules: the comparisons of docs/quiet/forecast.md, read from the doc and held equal to the leaderboard;
- examples: four test hours of the replay, picked by RULE.

Prints every cross-check; when one fails, exits 1 and writes nothing.

    .venv/bin/python -I scripts/site/trust.py    (from the project root)

Shape. Times are Kyiv "YYYY-MM-DD HH:MM", a "to" is the hour after the last one; shares are 0..1 and metrics are
rounded to 3 places, p to 4; null means no hours. "quiet_now" counts quiet-now hours with a known target.
{"schema": 1, "source": the command,
 "split": {"source", "hours", "labelled", "first", "last", "folds_from", "test_start", "test_weeks",
   "parts": [{"key": history|development|purged|test|unlabelled, "name", "from", "to", "rows", "busy_share_all",
              "quiet_now", "busy", "busy_share"}],
   "dev_folds", "test_folds": [{"origin", "fit_rows", "rows", "quiet_now", "busy", "busy_share"}]},
 "evaluation": {"source", "hours": "quiet_now", "n_boot", "ci": 0.95,
   "parts": {"development"|"test": {"hours", "busy", "busy_share"}},
   "models": [{"name", "role": finalist|reference|rule, "label",
               "development"|"test": {"bss", "bss_ci": [low, high], "roc_auc", "roc_auc_ci",
                                      "d_bss", "d_bss_ci", "verdict"}}]},     d_bss: BSS minus naive_7d's, null for it
 "replay": {"source", "model", "busy_at", "high_at", "tier_names": {"low"|"medium"|"high": words},
   "cadence": {"words", "retrains", "every_hours", "kyiv_hours", "defaults": {parameter: value}, "about"},
   "development"|"test": {"from", "to", "hours", "busy", "busy_share",
     "table": {"quiet_quiet", "quiet_busy", "busy_quiet", "busy_busy"},   said_happened; said quiet is p < busy_at
     "accuracy", "always_busy_accuracy", "always_quiet_accuracy", "busy_precision", "busy_recall",
     "quiet_truth" (said quiet and was quiet, of said quiet), "quiet_found" (the same, of was quiet),
     "alert_hours" (y_alert_3h known), "alert_share",
     "tiers": {"low"|"medium"|"high": {"hours", "share_of_hours", "busy_share", "alert_share", "missile_share"}},
     "calibration": [{"from", "to", "n", "p_mean", "busy_share"}] (10 bins of p)},
   "docs_weekly": {"source", "development"|"test": {"said_quiet_share", "quiet_truth", "busy_recall",
     "medium_busy_share", "high_busy_share", "accuracy", "quiet_found", "alert_share", "low_alert_share",
     "medium_alert_share", "high_alert_share"}}},
 "obvious_rules": {"source", "model": {"test_bss", "test_roc_auc"},
   "rules": [{"name", "label", "test_bss", "d_bss_ci", "test_roc_auc", "d_roc_auc_ci"}],     d: the model minus the rule
   "alert_copy": {"label", "roc_auc_all_hours", "model_all_hours", "model_quiet_now": {"development", "test"}}},
 "examples": {"source", "rule", "items": [{"kind": right_quiet|miss|right_high|false_alarm, "label", "t", "window",
   "p", "tier", "said", "busy", "drones", "missiles", "alert", "happened"}]}}
"""
import inspect
import os
import re
import statistics
import sys
from datetime import timedelta
from zoneinfo import ZoneInfo

os.environ.pop("AIRALERTS_DATA", None)  # the research data: paths.DATA is read at import

from airalerts import paths  # noqa: E402
from airalerts.evaluation import split, walkforward  # noqa: E402
from airalerts.live import features, model, publish  # noqa: E402
from airalerts.quiet import score as quiet  # noqa: E402

OUT = paths.ROOT / "site" / "data" / "trust.json"
BOARD = quiet.REPORT
DOC = paths.ROOT / "docs" / "quiet" / "forecast.md"
ALERTS = paths.SILVER / "kyiv_alerts.parquet"
COMMAND = ".venv/bin/python -I scripts/site/trust.py"
TARGET, DRONE, MISSILE, H = model.TARGET, model.DRONE, model.MISSILE, model.H
HOUR = timedelta(hours=1)
UTC, KYIV = ZoneInfo("UTC"), ZoneInfo("Europe/Kyiv")
WEEKDAYS = ("у понеділок", "у вівторок", "у середу", "у четвер", "у п'ятницю", "у суботу", "у неділю")
MODELS = {  # the models of the scene: role and plain words
    model.NAME: ("finalist", "наша модель: година, давність атаки і сигнали моніторів про дрони"),
    quiet.REFERENCE: ("reference", "частка неспокійних вікон за останні 7 днів"),
    "clim_hour": ("rule", "лише година доби"),
    "recency_table": ("rule", "нещодавно була атака, отже буде ще"),
    "hour_recency_nb": ("rule", "година доби і давність атаки"),
}
TIERS = {"low": "швидше тихо", "medium": "середній ризик", "high": "високий ризик"}
EXPECT = {"hours": 3909, "development": (1067, 31), "test": (412, 71)}  # README, Епоха 3: quiet-now hours, % busy
DOC_RULES = {"recency_table": 0.206, "hour_recency_nb": 0.178}  # their test BSS in docs/quiet/forecast.md
DOC_COPY = (0.632, 0.625)  # ROC AUC of the alert copy on all hours, development and test, the same doc
BOARD_PARTS = {"Розробка, години «зараз тихо»": "development", "Тест, години «зараз тихо»": "test",
               "Розробка, усі години": "development_all", "Тест, усі години": "test_all"}
RULE = ("test hours of the replay, the most confident of each kind: the lowest p among the 'швидше тихо' hours that "
        "stayed quiet and among those that got busy, the highest p among the 'високий ризик' hours that got busy and "
        "among those that stayed quiet; a tie goes to the earlier hour")
KINDS = (("right_quiet", "правильне «швидше тихо»", "low", False),
         ("miss", "пропуск: модель казала «швидше тихо», а стало неспокійно", "low", True),
         ("right_high", "правильний «високий ризик»", "high", True),
         ("false_alarm", "хибна тривога: модель казала «високий ризик», а було тихо", "high", False))
FAILED = []
share = publish.share


def check(name, ok, got):
    """Print one cross-check; a failure is remembered and stops the script before it writes."""
    print(f"{'OK  ' if ok else 'FAIL'} {name}: {got}")
    if not ok:
        FAILED.append(name)


def r3(v):
    return None if v is None else round(v, 3)


def counts(rows):
    """Rows, the busy share of the labelled ones, quiet-now hours with a known target and how many got busy."""
    known = [r for r in rows if r[TARGET] is not None]
    q = [r for r in known if r["quiet_now"]]
    busy = sum(1 for r in q if r[TARGET])
    return {"rows": len(rows), "busy_share_all": share(sum(1 for r in known if r[TARGET]), len(known)),
            "quiet_now": len(q), "busy": busy, "busy_share": share(busy, len(q))}


def folds_info(folds):
    return [{"origin": split.kyiv(o), "fit_rows": fit.num_rows,
             **{k: v for k, v in counts(ev.to_pylist()).items() if k != "busy_share_all"}} for o, fit, ev in folds]


def split_block(every, labelled):
    """every: all hours of gold kyiv_quiet as dicts; labelled: the hours with a known target (quiet.load())."""
    first, last = every[0]["t_utc"], every[-1]["t_utc"]
    end = max(r["t_utc"] for r in every if r[TARGET] is not None) + HOUR
    start, cut = split.TEST_START - split.DEV_FOLDS * split.WEEK, split.TEST_START - (H - 1) * HOUR
    bounds = (("history", "розробка: лише навчання, перевірок ще немає", first, start),
              ("development", f"розробка: {split.DEV_FOLDS} тижневих перевірок, тут обирали модель і межі", start, cut),
              ("purged", "викинуто: їхні 3 години заходять у тест", cut, split.TEST_START),
              ("test", "тест: відкрито один раз, лише звіт", split.TEST_START, end),
              ("unlabelled", "останні години: їхні 3 години ще не минули", end, last + HOUR))
    parts = [{"key": k, "name": n, "from": split.kyiv(lo), "to": split.kyiv(hi),
              **counts([r for r in every if lo <= r["t_utc"] < hi])} for k, n, lo, hi in bounds]
    test_folds = quiet.test_folds(labelled)
    out = {"source": "data/gold/kyiv_quiet.parquet split by airalerts.evaluation.split (docs/adr/0008-time-split.md)",
           "hours": len(every), "labelled": labelled.num_rows, "first": split.kyiv(first), "last": split.kyiv(last),
           "folds_from": split.kyiv(start), "test_start": split.kyiv(split.TEST_START),
           "test_weeks": sum(1 for _, _, ev in test_folds if ev.num_rows == 7 * 24), "parts": parts,
           "dev_folds": folds_info(quiet.dev_folds(labelled)), "test_folds": folds_info(test_folds)}
    print(f"split: {out['hours']} hours {out['first']}..{out['last']} Kyiv, folds from {out['folds_from']}, "
          f"test from {out['test_start']} ({out['test_weeks']} full weeks, {len(test_folds)} folds)")
    for p in parts:
        print(f"  {p['key']:<11} {p['from']}..{p['to']}: {p['rows']} rows, quiet-now {p['quiet_now']}, "
              f"busy {p['busy_share']}")
    check("gold kyiv_quiet hours", out["hours"] == EXPECT["hours"] == sum(p["rows"] for p in parts),
          f"{out['hours']} from {out['first']}, parts sum {sum(p['rows'] for p in parts)}")
    for key in ("development", "test"):
        p = next(p for p in parts if p["key"] == key)
        got = (p["quiet_now"], round(100 * p["busy"] / p["quiet_now"]) if p["quiet_now"] else None)
        check(f"{key}: quiet-now hours and busy %", got == EXPECT[key], f"{got[0]} hours, {got[1]}% busy")
    return out


def leaderboard():
    """{(part, model): {column: cell}} and {part: (hours, busy windows)} of the tables of the leaderboard."""
    cells, heads, part, head = {}, {}, None, None
    for line in BOARD.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            title, _, rest = line[3:].partition(": ")
            part, head = BOARD_PARTS.get(title), None
            m = re.match(r"(\d+) годин, неспокійних 3-годинних вікон (\d+)", rest)
            if part and m:
                heads[part] = (int(m[1]), int(m[2]))
        elif part and line.startswith("|") and not set(line.strip()) <= set("|-"):
            row = [c.strip() for c in line.strip().strip("|").split("|")]
            if head is None:
                head = row
            else:
                cells[(part, row[0].strip("`"))] = dict(zip(head, row))
    return cells, heads


def evaluation_block(labelled, cells, heads):
    at = walkforward.scored(quiet.SPEC, labelled)
    preds, _ = walkforward.load_predictions(quiet.SPEC, at, set(MODELS))
    folds = quiet.dev_folds(labelled) + quiet.test_folds(labelled)
    rows = [r for _, _, ev in folds for r in ev.select([TARGET, "quiet_now"]).to_pylist()]
    y = [int(r[TARGET]) for r in rows]
    clim = walkforward.climatology(quiet.SPEC, folds)
    out = {"source": f"{BOARD.relative_to(paths.ROOT)} (.venv/bin/python -I -m airalerts.quiet.score final), "
                     "recomputed from data/predictions/quiet by airalerts.evaluation.walkforward.bootstrap",
           "hours": "quiet_now", "n_boot": walkforward.N_BOOT, "ci": 0.95, "parts": {}, "models": []}
    per = {m: {"name": m, "role": role, "label": label} for m, (role, label) in MODELS.items()}
    for part, keep in (("development", lambda x: x < split.TEST_START), ("test", lambda x: x >= split.TEST_START)):
        idx = [i for i, x in enumerate(at) if keep(x) and rows[i]["quiet_now"]]
        yy, cc = [y[i] for i in idx], [clim[i] for i in idx]
        box = walkforward.bootstrap(quiet.days(idx, at), y, clim, preds, quiet.REFERENCE)
        point = {m: walkforward.scores(yy, [p[i] for i in idx], cc) for m, p in preds.items()}
        out["parts"][part] = {"hours": len(idx), "busy": sum(yy), "busy_share": share(sum(yy), len(idx))}
        check(f"leaderboard {part}: hours and busy windows", heads.get(part) == (len(idx), sum(yy)),
              f"{len(idx)}, {sum(yy)}")
        bad = []
        for m in MODELS:
            s, d = point[m], None if m == quiet.REFERENCE else point[m]["bss"] - point[quiet.REFERENCE]["bss"]
            lo, hi = box[(m, "d")]
            verdict = "опорна" if d is None else "краще" if lo > 0 else "гірше" if hi < 0 else "не розрізнити"
            mine = {"BSS": walkforward.ci(s["bss"], box[(m, "bss")]),
                    "ROC AUC": walkforward.ci(s["roc_auc"], box[(m, "roc_auc")]),
                    f"ΔBSS з {quiet.REFERENCE}": "" if d is None else walkforward.ci(d, (lo, hi)), "вердикт": verdict}
            got = cells.get((part, m), {})
            bad += [f"{m} {k}" for k, v in mine.items() if got.get(k) != v]
            if m == model.NAME:
                check(f"{m} {part}: BSS and ROC AUC = {BOARD.name}",
                      all(got.get(k) == mine[k] for k in ("BSS", "ROC AUC")),
                      f"BSS {mine['BSS']}, ROC AUC {mine['ROC AUC']}")
            per[m][part] = {"bss": r3(s["bss"]), "bss_ci": [r3(v) for v in box[(m, "bss")]],
                            "roc_auc": r3(s["roc_auc"]), "roc_auc_ci": [r3(v) for v in box[(m, "roc_auc")]],
                            "d_bss": r3(d), "d_bss_ci": None if d is None else [r3(lo), r3(hi)], "verdict": verdict}
        check(f"{part}: every cell of the {len(MODELS)} models = {BOARD.name}", not bad,
              ", ".join(bad) or "BSS, ROC AUC, ΔBSS, вердикт")
    out["models"] = list(per.values())
    return out


def cadence(moments):
    """The retrain schedule replay() used: read from its retrain moments, its defaults and its docstring."""
    sig = inspect.signature(model.replay)
    defaults = {k: str(v.default) for k, v in sig.parameters.items() if v.default is not inspect.Parameter.empty}
    gaps = [(b - a) / HOUR for a, b in zip(moments, moments[1:])]
    every = statistics.median(gaps) if gaps else None
    every = int(every) if every and every == int(every) else every
    local = [m.replace(tzinfo=UTC).astimezone(KYIV) for m in moments]
    at, days = sorted({x.hour for x in local}), sorted({x.weekday() for x in local})
    clock = ", ".join(f"{h:02d}:00" for h in at) + " за Києвом"
    if every == 1:
        words = "щогодини"
    elif every == 24 and len(at) == 1:
        words = f"щодня о {clock}"
    elif every == 168 and len(at) == 1 and len(days) == 1:
        words = f"щотижня {WEEKDAYS[days[0]]} о {clock}"
    else:
        words = (f"кожні {every:g} год" + (f" (о {clock})" if len(at) <= 6 else "")) if every else "невідомо"
    about = (inspect.getdoc(model.replay) or "").split(". ")[0].replace("\n", " ")
    return {"words": words, "retrains": len(moments), "every_hours": every, "kyiv_hours": at, "defaults": defaults,
            "about": about}


def judged(xs):
    """Said quiet (tier low) or busy against what happened, the metrics of the scene, the tiers and calibration."""
    n, table = len(xs), dict.fromkeys(("quiet_quiet", "quiet_busy", "busy_quiet", "busy_busy"), 0)
    for x in xs:
        table[("quiet_" if x["tier"] == "low" else "busy_") + ("busy" if x["row"][TARGET] else "quiet")] += 1
    qq, qb, bq, bb = table.values()
    busy, alerts = qb + bb, [x["row"].get("y_alert_3h") for x in xs]
    tiers = {}
    for k in TIERS:
        sub = [x for x in xs if x["tier"] == k]
        s = publish.summary(sub)
        tiers[k] = {"hours": len(sub), "share_of_hours": share(len(sub), n),
                    **{key: s[key] for key in ("busy_share", "alert_share", "missile_share")}}
    return {"hours": n, "busy": busy, "busy_share": share(busy, n), "table": table, "accuracy": share(qq + bb, n),
            "always_busy_accuracy": share(busy, n), "always_quiet_accuracy": share(n - busy, n),
            "busy_precision": share(bb, bb + bq), "busy_recall": share(bb, busy), "quiet_truth": share(qq, qq + qb),
            "quiet_found": share(qq, qq + bq), "alert_hours": sum(a is not None for a in alerts),
            "alert_share": publish.summary(xs)["alert_share"], "tiers": tiers, "calibration": publish.calibration(xs)}


def replay_block(gold, every):
    """replay() with its defaults, each retrain moment noted; scored like the site, by part."""
    moments, real = [], model.fitted

    def spy(*a, **k):
        at = a[1] if len(a) > 1 else k.get("at")
        if at is not None:
            moments.append(model.utc(at))
        return real(*a, **k)

    model.fitted = spy
    try:
        rep = model.replay(gold)
    finally:
        model.fitted = real
    al, until = features.read_alerts(ALERTS)
    for r, a in zip(every, features.alert_ahead([r["t_utc"] for r in every], al, until)):
        r["y_alert_3h"] = a
    scored = model.scored(rep, {r["t_utc"]: r for r in every})
    out = {"source": "airalerts.live.model.replay() with its defaults on data/gold/kyiv_quiet.parquet "
                     "(model.load(gold=True)), quiet-now hours with a known target (model.scored); tiers and "
                     "calibration by airalerts.live.publish.summary and calibration; y_alert_3h by "
                     "airalerts.live.features.alert_ahead on data/silver/kyiv_alerts.parquet",
           "model": model.NAME, "busy_at": model.BUSY_AT, "high_at": model.HIGH_AT, "tier_names": TIERS,
           "cadence": cadence(moments)}
    c = out["cadence"]
    print(f"replay: {len(rep)} hours, retrained {c['words']} ({c['retrains']} times, every {c['every_hours']} h), "
          f"defaults {c['defaults']}")
    start, last = split.TEST_START - split.DEV_FOLDS * split.WEEK, every[-1]["t_utc"] + HOUR
    for part, lo, hi in (("development", start, split.TEST_START - (H - 1) * HOUR), ("test", split.TEST_START, last)):
        j = judged([x for x in scored if lo <= x["t"] < hi])
        want = sum(1 for r in every if lo <= r["t_utc"] < hi and r["quiet_now"] and r[TARGET] is not None)
        out[part] = {"from": split.kyiv(lo), "to": split.kyiv(hi), **j}
        t, tiers = j["table"], j["tiers"]
        print(f"  {part}: {j['hours']} hours, busy {j['busy_share']}; said/happened {t}")
        print(f"    accuracy {j['accuracy']} (always busy {j['always_busy_accuracy']}, always quiet "
              f"{j['always_quiet_accuracy']}), busy precision {j['busy_precision']}, recall {j['busy_recall']}, "
              f"'швидше тихо' true {j['quiet_truth']}, quiet found {j['quiet_found']}, alert {j['alert_share']} "
              f"of {j['alert_hours']}")
        print("    tiers: " + "; ".join(f"{k} {v['hours']} h busy {v['busy_share']} alert {v['alert_share']}"
                                       for k, v in tiers.items()))
        check(f"replay {part}: the said/happened table sums to the quiet-now hours with a known target",
              sum(t.values()) == want and want > 0, f"{sum(t.values())} of {want}")
    return scored, out


def doc_line(text, start):
    """The numbers of the first line of the doc that starts with `start`; the minus sign reads as -."""
    line = next(x for x in text.splitlines() if x.startswith(start))
    return [float(v) for v in re.findall(r"[+-]?\d+(?:\.\d+)?", line.replace("−", "-"))]


def docs_weekly(text):
    pct = {"said_quiet_share": "| каже «швидше тихо» |", "quiet_truth": "| коли каже «тихо», справді тихо |",
           "busy_recall": "| попередив про неспокійні вікна |",
           "medium_busy_share": "| «середній ризик»: стало неспокійно |",
           "high_busy_share": "| «високий ризик»: стало неспокійно |", "accuracy": "**Accuracy**",
           "quiet_found": "- з тихих вікон названо тихими", "alert_share": "| усі тихі години |",
           "low_alert_share": "| «швидше тихо» |", "medium_alert_share": "| «середній ризик» |",
           "high_alert_share": "| «високий ризик» |"}
    got = {k: [round(v / 100, 2) for v in doc_line(text, start)[:2]] for k, start in pct.items()}
    out = {"source": f"{DOC.relative_to(paths.ROOT)}: the weekly refit (scripts/analysis/quiet_forecast_check.py and "
                     "quiet_forecast_value.py)", **{p: {k: v[i] for k, v in got.items()}
                                                   for i, p in enumerate(("development", "test"))}}
    print(f"docs weekly: development {out['development']}")
    print(f"             test {out['test']}")
    return out


def rules_block(text, cells):
    out = {"source": f"{DOC.relative_to(paths.ROOT)}, «Чи хороша модель» (scripts/analysis/quiet_forecast_value.py); "
                     f"the BSS and ROC AUC also in {BOARD.relative_to(paths.ROOT)}", "rules": []}
    for name, start in (("recency_table", "| «нещодавно була атака"), ("hour_recency_nb", "| «година доби і давність")):
        bss, rule_bss, dlo, dhi, auc, rule_auc, alo, ahi = doc_line(text, start)[:8]
        board = cells.get(("test", name), {})
        check(f"{DOC.name} {name}: test BSS {DOC_RULES[name]}, BSS and ROC AUC = {BOARD.name}",
              rule_bss == DOC_RULES[name] and [f"{rule_bss:.3f}", f"{rule_auc:.3f}"] == [
                  board.get(k, "").split(" [")[0] for k in ("BSS", "ROC AUC")], f"BSS {rule_bss}, ROC AUC {rule_auc}")
        out["model"] = {"test_bss": bss, "test_roc_auc": auc}
        out["rules"].append({"name": name, "label": MODELS[name][1], "test_bss": rule_bss, "d_bss_ci": [dlo, dhi],
                             "test_roc_auc": rule_auc, "d_roc_auc_ci": [alo, ahi]})
    mine = cells.get(("test", model.NAME), {})
    check(f"{DOC.name}: the model's test BSS and ROC AUC = {BOARD.name}",
          [f"{out['model']['test_bss']:.3f}", f"{out['model']['test_roc_auc']:.3f}"] == [
              mine.get(k, "").split(" [")[0] for k in ("BSS", "ROC AUC")], out["model"])
    m = re.search(r"копія (\d\.\d+) на розробці і (\d\.\d+) на тесті, модель (\d\.\d+) і (\d\.\d+)\. Коли зараз "
                  r"тихо, копії нема чого копіювати, а модель має (\d\.\d+) і (\d\.\d+)", text)
    v = tuple(float(x) for x in m.groups()) if m else (None,) * 6
    board = [cells.get((p, model.NAME), {}).get("ROC AUC", "").split(" [")[0]
             for p in ("development_all", "test_all", "development", "test")]
    check(f"{DOC.name}: alert copy ROC AUC {DOC_COPY[0]} and {DOC_COPY[1]}, the model's = {BOARD.name}",
          v[:2] == DOC_COPY and [f"{x:.3f}" for x in v[2:]] == board, f"copy {v[:2]}, model {v[2:]}")
    out["alert_copy"] = {"label": "копія «зараз тривога»: знає лише, тихо зараз чи ні",
                         "roc_auc_all_hours": {"development": v[0], "test": v[1]},
                         "model_all_hours": {"development": v[2], "test": v[3]},
                         "model_quiet_now": {"development": v[4], "test": v[5]}}
    return out


def examples(scored):
    test, items = [x for x in scored if x["t"] >= split.TEST_START], []
    for kind, label, tier, busy in KINDS:
        cands = [x for x in test if x["tier"] == tier and bool(x["row"][TARGET]) == busy]
        if not cands:
            items.append({"kind": kind, "label": label, "t": None})
            continue
        x = min(cands, key=lambda x: (x["p"] if tier == "low" else -x["p"], x["t"]))
        r, alert = x["row"], x["row"].get("y_alert_3h")
        what = ("неспокійно: " + ", ".join(w for w, f in (("дрони", r[DRONE]), ("ракети", r[MISSILE])) if f)
                if r[TARGET] else "тихо")
        if alert is not None:
            what += ", офіційна тривога була" if alert else ", офіційної тривоги не було"
        items.append({"kind": kind, "label": label, "t": split.kyiv(x["t"]),
                      "window": f"{split.kyiv(x['t'])[11:]}..{split.kyiv(x['t'] + H * HOUR)[11:]}",
                      "p": round(x["p"], 4), "tier": x["tier"], "said": TIERS[x["tier"]], "busy": bool(r[TARGET]),
                      "drones": bool(r[DRONE]), "missiles": bool(r[MISSILE]), "alert": alert, "happened": what})
        print(f"  example {kind}: {items[-1]['t']} p {items[-1]['p']} {items[-1]['said']}: {what}")
    return {"source": "the replay above, test part", "rule": RULE, "items": items}


def main():
    gold, _ = model.load(gold=True)
    every, labelled = gold.to_pylist(), quiet.load()
    cells, heads = leaderboard()
    text = DOC.read_text(encoding="utf-8")
    data = {"schema": 1, "source": COMMAND, "split": split_block(every, labelled),
            "evaluation": evaluation_block(labelled, cells, heads)}
    scored, data["replay"] = replay_block(gold, every)
    data["replay"]["docs_weekly"] = docs_weekly(text)
    data["obvious_rules"] = rules_block(text, cells)
    data["examples"] = examples(scored)
    if FAILED:
        sys.exit(f"FAIL: {len(FAILED)} cross-checks failed, {OUT.relative_to(paths.ROOT)} not written")
    model.write_json(OUT, data)
    print(f"all cross-checks OK; written {OUT.relative_to(paths.ROOT)}: {OUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
