"""Metrics shared by every question: y is a list of 0 and 1, p a list of probabilities (docs/METHODOLOGY.md 4.4).
Each one is checked against counting by brute force in tests/test_strikes.py (MetricsTest)."""


def brier(y, p):
    return sum((a - b) ** 2 for a, b in zip(p, y)) / len(y)


def tie_groups(y, p):
    """(p, true, false) per distinct p, highest p first."""
    out = []
    for v, a in sorted(zip(p, y), reverse=True):
        if out and out[-1][0] == v:
            out[-1][1] += a
            out[-1][2] += 1 - a
        else:
            out.append([v, a, 1 - a])
    return out


def roc_auc(y, p):
    """Chance that a true hour gets a higher p than a false one, ties count half; None without both classes."""
    pos, neg = sum(y), len(y) - sum(y)
    if not pos or not neg:
        return None
    above, s = 0, 0.0  # false hours with a lower p, lowest p first
    for _, tp, fp in reversed(tie_groups(y, p)):
        s += tp * (above + fp / 2)
        above += fp
    return s / (pos * neg)


def pr_auc(y, p):
    """Average precision: the precision at each distinct threshold weighted by the recall it adds; None without a true."""
    pos = sum(y)
    if not pos:
        return None
    tp = fp = 0
    ap = 0.0
    for _, a, b in tie_groups(y, p):
        tp, fp = tp + a, fp + b
        ap += a / pos * tp / (tp + fp)
    return ap


def recall_threshold(y, p, recall):
    """The highest threshold whose alarms (p >= it) still catch at least `recall` of the true rows: missing an event
    is worse than a false warning (docs/METHODOLOGY.md 4.4)."""
    need = recall * sum(y)
    for v in sorted(set(p), reverse=True):
        if sum(1 for a, b in zip(p, y) if b and a >= v) >= need:
            return v
    return min(p)
