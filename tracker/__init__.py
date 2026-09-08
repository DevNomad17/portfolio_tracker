"""Family ETF portfolio tracker."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_config(path=None):
    path = path or os.path.join(ROOT, "config.json")
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    s = sum(cfg["key"].values())
    if abs(s - 1.0) > 1e-9:
        raise ValueError(f"distribution key sums to {s}, not 1.0")
    for t in cfg["key"]:
        if t not in cfg["tickers"]:
            raise ValueError(f"key ticker {t} missing in tickers")
    cfg["_root"] = ROOT
    return cfg

def abspath(cfg, rel):
    return rel if os.path.isabs(rel) else os.path.join(cfg["_root"], rel)
