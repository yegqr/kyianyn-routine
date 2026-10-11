"""Small checks of the night rule models on toy nights (docs/models/night_rules.md)."""
import unittest
from datetime import date, timedelta

import pyarrow as pa

from airalerts.modeling.night_models import rules


def toy(ys, first=date(2026, 5, 13)):
    """Labelled nights from first with the history columns computed from ys, as the nightly table does."""
    rows, last = [], None
    for i, y in enumerate(ys):
        d = first + timedelta(days=i)
        rows.append({"night_date": d, "y_night": bool(y), "attack_last_night": bool(i and ys[i - 1]),
                     "attack_nights_28": sum(ys[max(0, i - 28):i]), "nights_since_attack": 30 if last is None else i - last})
        last = i if y else last
    return pa.Table.from_pylist(rows)


YS = [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0] * 3


class RulesTest(unittest.TestCase):
    def test_clim_recent_is_the_pulled_28_night_share(self):
        t = toy(YS)
        m = rules.fit_clim(t)
        base = sum(YS) / len(YS)
        self.assertAlmostEqual(m["base"], base)
        self.assertEqual(rules.predict_clim(m, t), [(10 * base + a) / 38 for a in t["attack_nights_28"].to_pylist()])

    def test_after_an_attack_is_jeffreys_never_zero(self):
        t = toy(YS)
        after = [y for y, a in zip(YS, t["attack_last_night"].to_pylist()) if a]
        want = (sum(after) + 0.5) / (len(after) + 1)
        self.assertEqual(sum(after), 0)
        for fit, predict in ((rules.fit_refractory, rules.predict_refractory), (rules.fit_hazard, rules.predict_hazard),
                             (rules.fit_renewal, rules.predict_renewal)):
            p = predict(fit(t), t)
            self.assertTrue(all(abs(v - want) < 1e-12 for v, a in zip(p, t["attack_last_night"].to_pylist()) if a))
            self.assertTrue(all(0 < v < 1 for v in p))

    def test_window_42_adds_the_nights_before_d_minus_28(self):
        t = toy(YS)
        m = rules.fit_clim(t, window=42)
        ys = t["y_night"].to_pylist()
        self.assertEqual(rules._recent(m, t), [sum(ys[max(0, i - 42):i]) for i in range(len(ys))])

    def test_renewal_hazard_matches_the_gap_distribution(self):
        m = rules.fit_renewal(toy(YS), last=0)
        surv, total = 1.0, 0.0
        for k in range(2, 200):  # P(gap = k) from the hazards; they must add up to 1
            h = rules._hazard(m, k)
            total += surv * h
            surv *= 1 - h
        self.assertAlmostEqual(total, 1.0, places=6)
        days = [i for i, y in enumerate(YS) if y]
        gaps = [b - a for a, b in zip(days, days[1:])]
        self.assertAlmostEqual(m["mu"], sum(gaps) / len(gaps) - 2)  # last=0: the mean of all gaps


if __name__ == "__main__":
    unittest.main(verbosity=2)
