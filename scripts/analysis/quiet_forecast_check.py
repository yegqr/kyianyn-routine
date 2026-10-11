"""How the person's forecast (src/airalerts/quiet/forecast.py) did, refitted every hour on what is known at that
hour, over the development weeks (where its scale was set) and the test weeks (never used to set anything).
Descriptive only; about 2 minutes.

    .venv/bin/python -I scripts/analysis/quiet_forecast_check.py    (from the project root)
"""
from airalerts.evaluation import split, walkforward as tasks
from airalerts.quiet import forecast, score as quiet

both = forecast.tables()
labelled = both[0]
at = tasks.scored(quiet.SPEC, labelled)
out = {"dev": [], "test": []}
for x in at:
    f = forecast.forecast(x, both)
    out["test" if x >= split.TEST_START else "dev"].append((f["quiet_now"], f["verdict"], f["actual"]))
for part, rows in out.items():
    for name, keep in (("quiet now", lambda r: r[0]), ("all hours", lambda r: True)):
        sel = [r for r in rows if keep(r)]
        quiet_calls = [r for r in sel if r[1][0] == "тихо"]
        busy = [r for r in sel if r[2]]
        caught = [r for r in busy if r[1][0] != "тихо"]
        cells = []
        for risk in ("швидше тихо", "середній ризик", "високий ризик"):
            g = [r for r in sel if r[1][1] == risk]
            cells.append(f"{risk} {len(g)} h, busy {sum(r[2] for r in g) / max(1, len(g)):.0%}")
        print(f"{part:4s} {name:9s}: {len(sel)} h, busy {len(busy) / len(sel):.0%}; said quiet {len(quiet_calls)} "
              f"({len(quiet_calls) / len(sel):.0%}), really quiet {sum(not r[2] for r in quiet_calls) / max(1, len(quiet_calls)):.0%}; "
              f"busy windows warned {len(caught)}/{len(busy)} ({len(caught) / max(1, len(busy)):.0%}) | " + " | ".join(cells))
