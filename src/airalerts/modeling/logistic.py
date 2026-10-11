"""Ridge logistic regression with time since the last strike (an idea from hazard models, not a full hazard model).

p(strike in [t, t + 3 h)) = 1 / (1 + exp(-(b0 + sum w_j z_j))), where z_j are the features standardized on the fit rows:
hour of day as sin and cos of HARMONICS harmonics, alert_active, a flag "an attack is going on" (hours_since_strike < 3)
and a flag "the pause after an attack" (3 <= hours_since_strike < 24), plus the EXTRA columns. The weights minimize the
weighted log loss plus LAMBDA / 2 * sum w_j^2 (the intercept b0 is not penalized) by Newton steps whose largest component
is cut to MAX_STEP. Each fit row weighs 0.5 ** (age / HALF_LIFE_DAYS), the age counted back from the newest fit row, so
recent weeks count more. Settings were chosen on the development folds only (docs/models/logistic.md).

    .venv/bin/python -I -m airalerts.modeling.logistic    write data/predictions/logistic.parquet
"""
import math
import sys
from datetime import datetime

from ..gold.kyiv_hourly import LABEL

NAME = "logistic"
DESCRIPTION = "ridge logistic regression on hour of day, alert, attack and pause flags from time since the last strike"

HARMONICS = 2           # sin and cos of the hour of day, 1 and 2 cycles per day
LAMBDA = 10.0           # ridge penalty on the standardized weights (variant lambda_10, chosen on the development folds)
HALF_LIFE_DAYS = 28.0   # None: every fit row weighs the same
EXTRA = ()              # more columns, used as numbers (bool -> 0/1)
START = None            # ISO time in UTC: fit rows before it are dropped; None keeps all
MAX_STEP = 3.0          # largest Newton step on any weight (keeps exp from overflowing on separable data)
MAX_ITER = 100
TOL = 1e-9
ATTACK_H, PAUSE_H = 3.0, 24.0
NO_STRIKE_H = 336.0     # the ceiling of hours_since_strike in gold


def num(v, empty=0.0):
    return empty if v is None else float(v)


def raw_features(rows, harmonics, extra):
    """Feature names and one list of raw values per row."""
    names = []
    for k in range(1, harmonics + 1):
        names += [f"hour_sin{k}", f"hour_cos{k}"]
    names += ["alert_active", "attack_on", "pause_3_24h"] + list(extra)
    hour = rows.column("hour_kyiv").to_pylist()
    alert = rows.column("alert_active").to_pylist()
    since = rows.column("hours_since_strike").to_pylist()
    more = [rows.column(c).to_pylist() for c in extra]
    out = []
    for i, h in enumerate(hour):
        x = []
        for k in range(1, harmonics + 1):
            a = 2 * math.pi * k * h / 24
            x += [math.sin(a), math.cos(a)]
        s = num(since[i], NO_STRIKE_H)
        x += [num(alert[i]), float(s < ATTACK_H), float(ATTACK_H <= s < PAUSE_H)]
        x += [num(m[i]) for m in more]
        out.append(x)
    return names, out


def sigmoid(z):
    return 1 / (1 + math.exp(-max(-35.0, min(35.0, z))))


def solve(a, b):
    """x with a x = b, Gauss elimination with partial pivoting."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        piv = max(range(c, n), key=lambda i: abs(m[i][c]))
        m[c], m[piv] = m[piv], m[c]
        for i in range(n):
            if i != c and m[i][c]:
                f = m[i][c] / m[c][c]
                for j in range(c, n + 1):
                    m[i][j] -= f * m[c][j]
    return [m[i][n] / m[i][i] for i in range(n)]


def newton(z, y, wt, lam, max_step=MAX_STEP):
    """Weights [b0, w1..] minimizing sum wt * logloss + lam / 2 * |w|^2 (b0 free); z rows without the intercept."""
    d = len(z[0]) + 1 if z else 1
    pos = sum(w for w, v in zip(wt, y) if v)
    w = [math.log((pos + 0.5) / (sum(wt) - pos + 0.5))] + [0.0] * (d - 1)
    for _ in range(MAX_ITER):
        g = [0.0] * d
        hess = [[0.0] * d for _ in range(d)]
        for x, v, q in zip(z, y, wt):
            xi = [1.0] + x
            p = sigmoid(sum(a * b for a, b in zip(w, xi)))
            r, s = q * (p - v), q * p * (1 - p)
            for i in range(d):
                g[i] += r * xi[i]
                si = s * xi[i]
                row = hess[i]
                for j in range(i, d):
                    row[j] += si * xi[j]
        for i in range(d):
            for j in range(i):
                hess[i][j] = hess[j][i]
            if i:
                hess[i][i] += lam
                g[i] += lam * w[i]
        step = solve(hess, g)
        big = max(abs(v) for v in step)
        if big > max_step:
            step = [v * max_step / big for v in step]
        w = [a - b for a, b in zip(w, step)]
        if big < TOL:
            break
    return w


def fit(rows, harmonics=HARMONICS, lam=LAMBDA, half_life=HALF_LIFE_DAYS, extra=EXTRA, start=START):
    times = rows.column("t_utc").to_pylist()
    y = [int(bool(v)) for v in rows.column(LABEL).to_pylist()]
    names, x = raw_features(rows, harmonics, tuple(extra))
    if start is not None:
        cut = datetime.fromisoformat(start).replace(tzinfo=times[0].tzinfo)
        keep = [i for i, t in enumerate(times) if t >= cut]
        times, y, x = [times[i] for i in keep], [y[i] for i in keep], [x[i] for i in keep]
    newest = max(times)
    if half_life is None:
        wt = [1.0] * len(y)
    else:
        wt = [0.5 ** ((newest - t).total_seconds() / 86400 / half_life) for t in times]
    n = len(x)
    mean = [sum(r[j] for r in x) / n for j in range(len(names))]
    sd = [math.sqrt(sum((r[j] - mean[j]) ** 2 for r in x) / n) or 1.0 for j in range(len(names))]
    z = [[(r[j] - mean[j]) / sd[j] for j in range(len(names))] for r in x]
    w = newton(z, y, wt, lam)
    return {"names": names, "mean": mean, "sd": sd, "b0": w[0], "w": w[1:], "harmonics": harmonics,
            "extra": tuple(extra)}


def predict(model, rows):
    _, x = raw_features(rows, model["harmonics"], model["extra"])
    out = []
    for r in x:
        lin = model["b0"] + sum(w * (v - m) / s for w, v, m, s in zip(model["w"], r, model["mean"], model["sd"]))
        out.append(float(sigmoid(lin)))
    return out


def odds_multipliers(model):
    """exp(weight per raw unit): how many times the odds grow when the raw feature grows by 1 (a flag from 0 to 1)."""
    return {n: math.exp(w / s) for n, w, s in zip(model["names"], model["w"], model["sd"])}


def main():
    from . import runner
    runner.run(sys.modules[__name__])


if __name__ == "__main__":
    main()
