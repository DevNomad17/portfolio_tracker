import unittest
from datetime import date, timedelta
from tracker.prices import PriceSeries
from tracker.ledger import Deposit
from tracker import engine

def series(t, start, closes):
    rows = []; d = start
    for c in closes:
        if d.weekday() < 5: rows.append((d, c))
        d += timedelta(days=1)
    return PriceSeries(t, rows)

class EngineTest(unittest.TestCase):
    def setUp(self):
        self.key = {"A": 0.6, "B": 0.4}
        s = date(2024, 1, 1)  # Monday
        self.prices = {"A": series("A", s, [10]*10 + [20]*20), "B": series("B", s, [5]*10 + [4]*20)}

    def test_units_and_value(self):
        deps = [Deposit(date(2024, 1, 6), "sat", 100.0)]  # Saturday -> buys Monday 8 Jan
        p = engine.compute("x", "X", deps, self.key, self.prices)
        lot = p.lots[0]
        self.assertEqual(lot.trade_date, date(2024, 1, 8))
        self.assertAlmostEqual(lot.units["A"], 6.0); self.assertAlmostEqual(lot.units["B"], 8.0)
        self.assertAlmostEqual(p.value, 6*20 + 8*4)   # 152
        self.assertAlmostEqual(p.gain, 52.0); self.assertAlmostEqual(p.gain_pct, 0.52)
        self.assertAlmostEqual(p.values[0], 100.0)     # invested at cost on trade day
        self.assertEqual(p.dates[0], date(2024, 1, 8))

    def test_price_before_first_raises(self):
        with self.assertRaises(LookupError):
            self.prices["A"].on_or_before(date(2023, 12, 1))

    def test_yearly_summary(self):
        deps = [Deposit(date(2024, 1, 1), "", 100.0), Deposit(date(2024, 1, 20), "", 50.0)]
        p = engine.compute("x", "X", deps, self.key, self.prices)
        ys = engine.yearly_summary(p)
        self.assertEqual(len(ys), 1); y = ys[0]
        self.assertAlmostEqual(y["deposits"], 150.0)
        self.assertAlmostEqual(y["end"], p.value)
        self.assertAlmostEqual(y["gain"], p.value - 150.0)
        # TWR: first lot 100 -> 152 (+52%), second lot bought at flat prices -> 0%
        self.assertAlmostEqual(y["twr_pct"], 0.52, places=6)

    def test_holdings_weights_sum_to_one(self):
        deps = [Deposit(date(2024, 1, 1), "", 100.0)]
        p = engine.compute("x", "X", deps, self.key, self.prices)
        h = p.holdings(self.prices)
        self.assertAlmostEqual(sum(v[2] for v in h.values()), 1.0)

if __name__ == "__main__":
    unittest.main()
