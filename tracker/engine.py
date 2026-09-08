"""Virtual-units calculation.

Each deposit D on date t is split by the static key into per-ETF EUR amounts; each buys
amount*weight/close(t') virtual units, t' = first trading day >= t.  Value on day d =
sum(units * close(d)).  Zero fees, instant investment (accepted simplifications).
"""
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List

@dataclass
class Lot:
    deposit: "Deposit"
    trade_date: date
    units: Dict[str, float]           # ticker -> virtual units
    buy_prices: Dict[str, float]

    def value_on(self, prices, d):
        v = 0.0
        for t, u in self.units.items():
            _, c = prices[t].on_or_before(d)
            v += u * c
        return v

@dataclass
class Portfolio:
    person_id: str
    name: str
    lots: List[Lot]
    as_of: date                       # last date with prices for all tickers
    dates: List[date] = field(default_factory=list)      # daily valuation dates (calendar days)
    values: List[float] = field(default_factory=list)    # value on each date
    invested: List[float] = field(default_factory=list)  # cumulative deposits on each date

    # --- headline numbers ---
    @property
    def total_deposits(self): return sum(l.deposit.amount for l in self.lots)
    @property
    def value(self): return self.values[-1] if self.values else 0.0
    @property
    def gain(self): return self.value - self.total_deposits
    @property
    def gain_pct(self): return self.gain / self.total_deposits if self.total_deposits else 0.0

    def holdings(self, prices):
        """ticker -> (units, value, weight)"""
        out = {}
        for l in self.lots:
            for t, u in l.units.items():
                out[t] = out.get(t, 0.0) + u
        tot = 0.0; res = {}
        for t, u in out.items():
            _, c = prices[t].on_or_before(self.as_of)
            res[t] = [u, u * c]; tot += u * c
        for t in res:
            res[t].append(res[t][1] / tot if tot else 0.0)
        return res

def common_as_of(prices):
    return min(s.last for s in prices.values())

def build_lots(deposits, key, prices):
    lots = []
    for dep in deposits:
        units, bp = {}, {}
        td = None
        for t, w in key.items():
            d_, c = prices[t].on_or_after(dep.date)
            td = max(td, d_) if td else d_
            units[t] = dep.amount * w / c
            bp[t] = c
        lots.append(Lot(dep, td, units, bp))
    return lots

def compute(person_id, name, deposits, key, prices, as_of=None):
    as_of = as_of or common_as_of(prices)
    lots = build_lots(deposits, key, prices)
    p = Portfolio(person_id, name, lots, as_of)
    if not lots:
        return p
    d = lots[0].trade_date
    # per-ticker cumulative units by date is cheaper than per-lot loops
    lots_sorted = sorted(lots, key=lambda l: l.trade_date)
    i = 0; units = {t: 0.0 for t in key}; inv = 0.0
    while d <= as_of:
        while i < len(lots_sorted) and lots_sorted[i].trade_date <= d:
            for t, u in lots_sorted[i].units.items():
                units[t] += u
            inv += lots_sorted[i].deposit.amount
            i += 1
        v = 0.0
        for t, u in units.items():
            _, c = prices[t].on_or_before(d)
            v += u * c
        p.dates.append(d); p.values.append(v); p.invested.append(inv)
        d += timedelta(days=1)
    return p

def lot_rows(p, prices):
    """Per-deposit table: date, note, amount, value now, gain, gain %."""
    rows = []
    for l in p.lots:
        v = l.value_on(prices, p.as_of)
        rows.append({"date": l.deposit.date, "trade_date": l.trade_date, "note": l.deposit.note,
                     "amount": l.deposit.amount, "value": v, "gain": v - l.deposit.amount,
                     "gain_pct": (v / l.deposit.amount - 1) if l.deposit.amount else 0.0})
    return rows

def value_on(p, d):
    """Portfolio value at calendar date d (0 before first lot)."""
    if not p.dates or d < p.dates[0]:
        return 0.0
    if d > p.dates[-1]:
        return p.values[-1]
    return p.values[(d - p.dates[0]).days]

def yearly_summary(p):
    """Per calendar year: start value, deposits, end value, gain, simple return and TWR."""
    if not p.lots: return []
    years = range(p.dates[0].year, p.as_of.year + 1)
    out = []
    idx = {d: i for i, d in enumerate(p.dates)}
    for y in years:
        start = value_on(p, date(y - 1, 12, 31))
        end_d = min(date(y, 12, 31), p.as_of)
        end = value_on(p, end_d)
        deps = sum(l.deposit.amount for l in p.lots if l.trade_date.year == y)
        gain = end - start - deps
        base = start + deps
        # time-weighted return: chain daily returns, deposits enter at cost on their trade date
        twr = 1.0
        d = max(date(y, 1, 1), p.dates[0])
        prev = value_on(p, d - timedelta(days=1))
        flows = {}
        for l in p.lots:
            flows[l.trade_date] = flows.get(l.trade_date, 0.0) + l.deposit.amount
        while d <= end_d:
            v = value_on(p, d); f = flows.get(d, 0.0)
            if prev > 0:
                twr *= (v - f) / prev
            prev = v
            d += timedelta(days=1)
        out.append({"year": y, "start": start, "deposits": deps, "end": end, "gain": gain,
                    "simple_pct": gain / base if base else 0.0, "twr_pct": twr - 1 if prev else 0.0,
                    "partial": end_d < date(y, 12, 31)})
    return out
