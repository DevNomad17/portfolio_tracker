"""Yearly summary export (Markdown) for the family newsletter."""
import os
from datetime import date
from . import abspath
from .engine import yearly_summary, lot_rows
from .build import eur, eur2, pct, sk

def yearly_markdown(cfg, portfolios, prices, year):
    lines = [f"# Rodinné portfóliá – zhrnutie roku {year}", ""]
    lines.append("| Kto | Hodnota 1.1. | Vklady v roku | Hodnota 31.12. | Zisk/strata v roku | Výnos (TWR) | Vklady celkom | Hodnota celkom | Celkové zhodnotenie |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for pid, p in portfolios.items():
        ys = [y for y in yearly_summary(p) if y["year"] == year]
        if not ys: continue
        y = ys[0]
        lines.append(f"| {p.name} | {eur(y['start'])} | {eur(y['deposits'])} | {eur(y['end'])} | {eur(y['gain'])} | {pct(y['twr_pct'])} | {eur(p.total_deposits)} | {eur(p.value)} | {pct(p.gain_pct)} |")
    lines.append("")
    for pid, p in portfolios.items():
        deps = [r for r in lot_rows(p, prices) if r["date"].year == year]
        if not deps: continue
        lines.append(f"## {p.name} – vklady v roku {year}")
        for r in deps:
            lines.append(f"- {sk(r['date'])} — {r['note'] or 'vklad'}: {eur2(r['amount'])} (dnes {eur2(r['value'])}, {pct(r['gain_pct'])})")
        lines.append("")
    end = min(date(year, 12, 31), min(p.as_of for p in portfolios.values()))
    lines.append(f"_Stav k {sk(end)}. Kľúč: " + " / ".join(f"{t} {w*100:.0f} %" for t, w in cfg["key"].items()) + ", bez poplatkov, okamžitá investícia._")
    return "\n".join(lines)

def write_yearly(cfg, portfolios, prices, year):
    d = abspath(cfg, cfg["exports_dir"]); os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"zhrnutie_{year}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(yearly_markdown(cfg, portfolios, prices, year))
    return path
