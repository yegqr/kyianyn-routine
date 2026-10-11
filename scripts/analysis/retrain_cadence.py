"""How often should the live model retrain (docs/adr/0013-retrain-cadence.md): every hour, every 6 hours, every day or
every week, with the model and its thresholds frozen. Prints only, writes nothing.

Rules fixed in ADR-0013 before anything was scored:
- candidates, the CADENCES of airalerts.live.model on the Kyiv clock: every hour; every 6 hours at 04:00, 10:00, 16:00
  and 22:00; every day at 04:00; every week at the fold origins of the development folds (Saturday 12:00);
- frozen: logit_signals with C 0.3 (quiet/linear.py) and the thresholds 0.197 and 0.300 (quiet/forecast.py);
- the forecast of hour t comes from the model of the latest retrain moment r <= t, fitted on every hour whose 3 hours
  ended by r (split.known_by);
- the metric: BSS on the quiet-now hours of the 8 development weeks as reports/quiet_leaderboard.md computes it (the
  same reference: the busy share known at each weekly fold origin), next to ROC AUC and the truth of "швидше тихо";
- the choice: the rarest cadence whose development BSS is at least the best development BSS minus 0.01;
- the test is scored only as a report, never to choose.

    .venv/bin/python -I scripts/analysis/retrain_cadence.py    (from the project root, a minute or two)
"""
import time
from bisect import bisect_right

import pyarrow as pa

from airalerts.evaluation import split, walkforward
from airalerts.live import model as live
from airalerts.quiet import forecast, score as quiet

ORDER = ("hourly", "6h", "daily", "weekly")  # most often first: the rule takes the rarest one good enough
NAMES = {"hourly": "щогодини", "6h": "кожні 6 год", "daily": "щодня о 04:00", "weekly": "щотижня, субота 12:00"}
PARTS = {"development": "розробка", "test": "тест, лише звіт"}
TOL = 0.01
LEADERBOARD_DEV_BSS = 0.094  # reports/quiet_leaderboard.md: logit_signals, development, quiet-now hours
DOCS_TEST_QUIET_TRUE = 0.83  # docs/quiet/forecast.md: on the test, "швидше тихо" was truly quiet


def predictions(t, folds, cadence):
    """p of every evaluation hour of the folds from the model of its latest retrain moment r, fitted on the hours known
    at r; with the retrain moments, the number of fits and the seconds they took."""
    ev = pa.concat_tables([e for _, _, e in folds])
    at = ev["t_utc"].to_pylist()
    moments = live.retrains(at[0], at[-1], cadence)
    which = [bisect_right(moments, x) - 1 for x in at]
    p, fits, a, clock = [], 0, 0, time.perf_counter()
    while a < len(at):
        b = a
        while b < len(at) and which[b] == which[a]:
            b += 1
        m = forecast.MODEL["fit"](split.known_by(t, moments[which[a]], quiet.H))
        p += [float(v) for v in forecast.MODEL["predict"](m, quiet.features_only(ev.slice(a, b - a)))]
        a, fits = b, fits + 1
    return {"p": p, "moments": moments, "fits": fits, "seconds": time.perf_counter() - clock}


def scored(folds, p):
    """Quiet-now hours: BSS, Brier, ROC AUC and PR AUC against the leaderboard's reference, the hours that got
    "швидше тихо" and how many of them stayed quiet, the hours of "високий ризик" and how many of them got busy."""
    rows = [r for _, _, ev in folds for r in ev.select([quiet.LABEL, "quiet_now"]).to_pylist()]
    clim = walkforward.climatology(quiet.SPEC, folds)
    y = [int(r[quiet.LABEL]) for r in rows]
    q = [i for i, r in enumerate(rows) if r["quiet_now"]]
    low = [i for i in q if p[i] < forecast.BUSY_AT]
    high = [i for i in q if p[i] >= forecast.HIGH_AT]
    return {**walkforward.scores([y[i] for i in q], [p[i] for i in q], [clim[i] for i in q]), "hours": len(q),
            "low": len(low), "low_quiet": sum(1 - y[i] for i in low), "high": len(high),
            "high_busy": sum(y[i] for i in high)}


def pct(k, n):
    return f"{k / n:.0%}" if n else "n/a"


def check(ok, text):
    print(f"check: {text}: {'OK' if ok else 'FAIL'}")


def main():
    t = quiet.load()
    folds = {"development": quiet.dev_folds(t), "test": quiet.test_folds(t)}
    got = {}
    for part, fs in folds.items():
        for c in ORDER:
            r = predictions(t, fs, c)
            got[part, c] = {**r, **scored(fs, r["p"])}
    print(f"how often to retrain {live.NAME} (C 0.3, thresholds {forecast.BUSY_AT:.3f} and {forecast.HIGH_AT:.3f} frozen); "
          f"quiet-now hours: development {got['development', 'weekly']['hours']}, test {got['test', 'weekly']['hours']}; "
          "BSS against the busy share known at each weekly fold origin, as in reports/quiet_leaderboard.md")
    print()
    print("| частина | як часто | перенавчань | секунд | BSS | ROC AUC | «швидше тихо»: частка годин | "
          "«швидше тихо»: справді тихо | «високий ризик»: неспокійно |")
    print("|" + "---|" * 9)
    for (part, c), g in got.items():
        print(f"| {PARTS[part]} | `{c}` {NAMES[c]} | {g['fits']} | {g['seconds']:.1f} | {g['bss']:.4f} | "
              f"{g['roc_auc']:.3f} | {pct(g['low'], g['hours'])} | {pct(g['low_quiet'], g['low'])} "
              f"({g['low_quiet']}/{g['low']}) | {pct(g['high_busy'], g['high'])} |")
    print()

    for part, fs in folds.items():
        check(got[part, "weekly"]["moments"] == [o for o, _, _ in fs], f"the weekly retrains of the {part} are its fold origins")
    w = got["development", "weekly"]
    check(round(w["bss"], 3) == LEADERBOARD_DEV_BSS,
          f"weekly development BSS {w['bss']:.4f} is the {LEADERBOARD_DEV_BSS} of reports/quiet_leaderboard.md")
    try:
        saved = walkforward.load_predictions(quiet.SPEC, walkforward.scored(quiet.SPEC, t), {live.NAME})[0][live.NAME]
        mine = w["p"] + got["test", "weekly"]["p"]
        if len(saved) != len(mine):
            raise ValueError("lengths differ")
        print(f"info: weekly p against the saved fold predictions data/predictions/quiet/{live.NAME}.parquet: "
              f"max |diff| {max(abs(a - b) for a, b in zip(saved, mine)):.1e}")
    except (OSError, ValueError, KeyError) as e:
        print(f"info: the saved fold predictions are not comparable ({type(e).__name__})")
    h = got["test", "hourly"]
    check(round(h["low_quiet"] / h["low"], 2) == DOCS_TEST_QUIET_TRUE,
          f"hourly test: \"швидше тихо\" truly quiet {h['low_quiet']}/{h['low']} is the {DOCS_TEST_QUIET_TRUE:.0%} "
          "of docs/quiet/forecast.md")

    dev = {c: got["development", c]["bss"] for c in ORDER}
    best = max(ORDER, key=dev.get)
    choice = [c for c in ORDER if dev[c] >= dev[best] - TOL][-1]
    print(f"choice by ADR-0013: {choice} ({NAMES[choice]}): development BSS {dev[choice]:.4f}, not lower than the best "
          f"{dev[best]:.4f} ({best}) minus {TOL} = {dev[best] - TOL:.4f}; the rarest such cadence")


if __name__ == "__main__":
    main()
