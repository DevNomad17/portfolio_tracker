"""Daily close cache (data/prices/<TICKER>.csv: date,close) with Yahoo primary / Stooq fallback updater."""
import csv, json, os, sys, time, urllib.request, urllib.error
from datetime import date, datetime, timedelta
from bisect import bisect_left
from . import abspath

UA = {"User-Agent": "Mozilla/5.0 (family-portfolio-tracker)"}

class PriceSeries:
    def __init__(self, ticker, rows):
        self.ticker = ticker
        rows = sorted(set(rows))
        self.dates = [d for d, _ in rows]
        self.closes = [c for _, c in rows]

    def __len__(self): return len(self.dates)
    @property
    def first(self): return self.dates[0] if self.dates else None
    @property
    def last(self): return self.dates[-1] if self.dates else None

    def on_or_after(self, d):
        """(trading_date, close) for the first trading day >= d (buy at close of that day)."""
        i = bisect_left(self.dates, d)
        if i >= len(self.dates):
            raise LookupError(f"{self.ticker}: no price on/after {d} (last {self.last})")
        return self.dates[i], self.closes[i]

    def on_or_before(self, d):
        """(trading_date, close) for the last trading day <= d (valuation)."""
        i = bisect_left(self.dates, d)
        if i < len(self.dates) and self.dates[i] == d:
            return d, self.closes[i]
        if i == 0:
            raise LookupError(f"{self.ticker}: no price on/before {d} (first {self.first})")
        return self.dates[i-1], self.closes[i-1]

def _csv_path(cfg, ticker):
    return os.path.join(abspath(cfg, cfg["price_cache_dir"]), f"{ticker}.csv")

def load(cfg, ticker):
    p = _csv_path(cfg, ticker)
    rows = []
    if os.path.exists(p):
        with open(p, newline="") as f:
            for r in csv.reader(f):
                if not r or r[0] == "date": continue
                rows.append((date.fromisoformat(r[0]), float(r[1])))
    return PriceSeries(ticker, rows)

def save(cfg, series):
    p = _csv_path(cfg, series.ticker)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "close"])
        for d, c in zip(series.dates, series.closes):
            w.writerow([d.isoformat(), f"{c:.4f}"])
    os.replace(tmp, p)

def load_all(cfg):
    return {t: load(cfg, t) for t in cfg["key"]}

# ---------- fetching ----------
def _get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def fetch_yahoo(symbol, start, end=None):
    end = end or date.today() + timedelta(days=1)
    p1 = int(datetime(start.year, start.month, start.day).timestamp())
    p2 = int(datetime(end.year, end.month, end.day).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?period1={p1}&period2={p2}&interval=1d&events=splits")
    j = json.loads(_get(url))
    res = j.get("chart", {}).get("result")
    if not res:
        raise RuntimeError(f"yahoo {symbol}: {j.get('chart',{}).get('error')}")
    r = res[0]
    ts = r.get("timestamp") or []
    cl = r["indicators"]["quote"][0].get("close") or []
    tz = r["meta"].get("gmtoffset", 0)
    out = []
    for t, c in zip(ts, cl):
        if c is None: continue
        d = (datetime.utcfromtimestamp(t + tz)).date()
        out.append((d, float(c)))
    if r.get("events", {}).get("splits"):
        print(f"WARNING {symbol}: split events present, check cache", file=sys.stderr)
    return out

def fetch_stooq(symbol, start):
    url = f"https://stooq.com/q/d/l/?s={symbol}&d1={start:%Y%m%d}&d2={date.today():%Y%m%d}&i=d"
    txt = _get(url)
    out = []
    for r in csv.DictReader(txt.splitlines()):
        if r.get("Close") in (None, "", "-"): continue
        out.append((date.fromisoformat(r["Date"]), float(r["Close"])))
    if not out:
        raise RuntimeError(f"stooq {symbol}: empty response")
    return out

def update(cfg, tickers=None, overlap_days=10, verbose=True):
    """Fetch new closes for every ticker (from last cached date - overlap). Returns {ticker: n_new}."""
    start_all = date.fromisoformat(cfg.get("history_start", "2020-12-01"))
    result = {}
    for t in (tickers or list(cfg["key"])):
        s = load(cfg, t)
        start = (s.last - timedelta(days=overlap_days)) if s.last else start_all
        meta = cfg["tickers"][t]
        rows, src = None, None
        for name, fn in (("yahoo", lambda: fetch_yahoo(meta["yahoo"], start)),
                         ("stooq", lambda: fetch_stooq(meta["stooq"], start))):
            try:
                rows = fn(); src = name; break
            except Exception as e:
                if verbose: print(f"  {t}: {name} failed: {e}", file=sys.stderr)
        if rows is None:
            result[t] = None
            continue
        before = len(s)
        merged = {d: c for d, c in zip(s.dates, s.closes)}
        for d, c in rows:
            merged[d] = c
        s = PriceSeries(t, list(merged.items()))
        save(cfg, s)
        result[t] = len(s) - before
        if verbose:
            print(f"  {t}: +{len(s)-before} rows from {src}, now {len(s)} rows {s.first}..{s.last}")
        time.sleep(0.5)
    return result
