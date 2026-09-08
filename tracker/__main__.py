"""CLI:  python3 -m tracker update | build | all | summary YEAR | status"""
import sys
from datetime import date
from . import load_config
from . import prices as pr, ledger, engine, build, export

def compute_all(cfg, prices):
    deps = ledger.read_all(cfg)
    return {pid: engine.compute(pid, cfg["people"][pid]["name"], deps[pid], cfg["key"], prices)
            for pid in cfg["people"]}

def main(argv):
    cfg = load_config()
    cmd = argv[0] if argv else "all"
    if cmd == "update":
        print("Updating prices…"); pr.update(cfg); return
    prices = pr.load_all(cfg)
    missing = [t for t, s in prices.items() if len(s) == 0]
    if cmd == "status":
        for t, s in prices.items():
            print(f"{t}: {len(s)} rows {s.first}..{s.last}")
        deps = ledger.read_all(cfg)
        for pid, ds in deps.items():
            print(f"{pid}: {len(ds)} deposits, {sum(d.amount for d in ds):.0f} EUR")
        return
    if cmd == "all":
        print("Updating prices…"); pr.update(cfg); prices = pr.load_all(cfg)
        missing = [t for t, s in prices.items() if len(s) == 0]
    if missing:
        sys.exit(f"no price data for {missing} — run: python3 -m tracker update")
    ports = compute_all(cfg, prices)
    if cmd in ("build", "all"):
        as_of = engine.common_as_of(prices)
        if (date.today() - as_of).days > 7:
            print(f"WARNING: prices are stale (last {as_of})", file=sys.stderr)
        urls = build.build_site(cfg, ports, prices)
        for pid, p in ports.items():
            print(f"{p.name:6} vklady {p.total_deposits:8.0f}  hodnota {p.value:8.0f}  {p.gain_pct*100:+6.1f} %   -> site/{urls[pid]}")
        print(f"Site built in {cfg['site_dir']}/ (as of {as_of})")
    elif cmd == "summary":
        year = int(argv[1]) if len(argv) > 1 else date.today().year
        print("written:", export.write_yearly(cfg, ports, prices, year))
    else:
        sys.exit(__doc__)

if __name__ == "__main__":
    main(sys.argv[1:])
