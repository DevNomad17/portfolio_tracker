"""Render one self-contained HTML page per person into site/<token>/index.html."""
import html, json, os, shutil
from datetime import date
from . import abspath
from .engine import lot_rows, yearly_summary

def eur(x):  return f"{x:,.0f} €".replace(",", " ")
def eur2(x): return f"{x:,.2f} €".replace(",", " ")
def pct(x):  return f"{x*100:+.1f} %"
def sk(d):   return f"{d.day}. {d.month}. {d.year}"
def cls(x):  return "pos" if x >= 0 else "neg"

CSS = """
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1d1b;--mute:#6b6b66;--line:#e4e2dc;--pos:#1d7a4d;--neg:#b3362b;--acc:#2b5ea8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 -apple-system,system-ui,Segoe UI,Roboto,sans-serif}
main{max-width:920px;margin:0 auto;padding:24px 16px 48px}h1{font-size:28px;margin:0 0 4px}.sub{color:var(--mute);margin:0 0 20px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:24px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}.card .l{font-size:13px;color:var(--mute)}.card .v{font-size:24px;font-weight:600;margin-top:2px}
.pos{color:var(--pos)}.neg{color:var(--neg)}section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:16px}
h2{font-size:17px;margin:0 0 12px}table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child,th.t,td.t{text-align:left;white-space:normal}th{color:var(--mute);font-weight:500}tfoot td{font-weight:600}
.wrap{overflow-x:auto}svg{width:100%;height:auto;display:block}.legend{font-size:13px;color:var(--mute);display:flex;gap:16px;margin-top:6px}
.legend i{display:inline-block;width:12px;height:3px;vertical-align:middle;margin-right:5px}.note{font-size:13px;color:var(--mute)}
.tip{position:absolute;pointer-events:none;background:#1d1d1b;color:#fff;font-size:12px;padding:4px 8px;border-radius:5px;display:none}
"""

JS = r"""
(function(){
const D=window.__data;const svg=document.getElementById('chart');const W=900,H=320,L=56,R=12,T=12,B=28;
const n=D.dates.length;const xs=i=>L+(W-L-R)*i/Math.max(1,n-1);
const mx=Math.max(...D.values,...D.invested)*1.05;const ys=v=>T+(H-T-B)*(1-v/mx);
let s='';const step=Math.max(1,Math.round(mx/5/100))*100;
for(let v=0;v<=mx;v+=step){const y=ys(v);s+=`<line x1="${L}" x2="${W-R}" y1="${y}" y2="${y}" stroke="#e4e2dc"/><text x="${L-6}" y="${y+4}" font-size="11" text-anchor="end" fill="#6b6b66">${v.toLocaleString('sk')}</text>`;}
const yrs={};D.dates.forEach((d,i)=>{const y=d.slice(0,4);if(!(y in yrs))yrs[y]=i;});
const yk=Object.keys(yrs);yk.forEach((y,k)=>{const x=xs(yrs[y]);const nx=k+1<yk.length?xs(yrs[yk[k+1]]):W;s+=`<line x1="${x}" x2="${x}" y1="${T}" y2="${H-B}" stroke="#eee"/>`;if(nx-x>40)s+=`<text x="${x+3}" y="${H-8}" font-size="11" fill="#6b6b66">${y}</text>`;});
const path=(a)=>a.map((v,i)=>(i?'L':'M')+xs(i).toFixed(1)+' '+ys(v).toFixed(1)).join(' ');
s+=`<path d="${path(D.invested)}" fill="none" stroke="#9a9a94" stroke-width="1.5" stroke-dasharray="4 3"/>`;
s+=`<path d="${path(D.values)}" fill="none" stroke="#2b5ea8" stroke-width="2"/>`;
s+=`<line id="cur" x1="0" x2="0" y1="${T}" y2="${H-B}" stroke="#2b5ea8" stroke-width="1" style="display:none"/>`;
svg.innerHTML=s;const tip=document.getElementById('tip');const cur=document.getElementById('cur');
svg.addEventListener('mousemove',e=>{const r=svg.getBoundingClientRect();const x=(e.clientX-r.left)*W/r.width;let i=Math.round((x-L)/(W-L-R)*(n-1));i=Math.max(0,Math.min(n-1,i));
cur.setAttribute('x1',xs(i));cur.setAttribute('x2',xs(i));cur.style.display='';const g=D.values[i]-D.invested[i];
tip.style.display='block';tip.style.left=(e.pageX+12)+'px';tip.style.top=(e.pageY-30)+'px';
tip.innerHTML=`${D.dates[i]}<br>hodnota ${D.values[i].toFixed(0)} € · vklady ${D.invested[i].toFixed(0)} € · ${g>=0?'+':''}${g.toFixed(0)} €`;});
svg.addEventListener('mouseleave',()=>{tip.style.display='none';cur.style.display='none';});
})();
"""

def render(cfg, p, prices, deposits_note=None):
    rows = lot_rows(p, prices)
    ys = yearly_summary(p)
    hold = p.holdings(prices)
    # chart data: weekly sampling keeps the page small
    step = 7 if len(p.dates) > 400 else 1
    idx = list(range(0, len(p.dates), step))
    if idx[-1] != len(p.dates) - 1: idx.append(len(p.dates) - 1)
    data = {"dates": [p.dates[i].isoformat() for i in idx],
            "values": [round(p.values[i], 2) for i in idx],
            "invested": [round(p.invested[i], 2) for i in idx]}
    key_txt = " / ".join(f"{t} {w*100:.0f} %" for t, w in cfg["key"].items())
    h = []
    h.append(f"<!doctype html><html lang='sk'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
             f"<meta name='robots' content='noindex,nofollow'><title>Portfólio – {html.escape(p.name)}</title><style>{CSS}</style></head><body><main>")
    h.append(f"<h1>Portfólio – {html.escape(p.name)}</h1><p class='sub'>Stav k {sk(p.as_of)} · ceny na konci obchodného dňa</p>")
    h.append("<div class='cards'>"
             f"<div class='card'><div class='l'>Vklady spolu</div><div class='v'>{eur(p.total_deposits)}</div></div>"
             f"<div class='card'><div class='l'>Aktuálna hodnota</div><div class='v'>{eur(p.value)}</div></div>"
             f"<div class='card'><div class='l'>Zisk / strata</div><div class='v {cls(p.gain)}'>{'+' if p.gain>=0 else ''}{eur(p.gain)}</div></div>"
             f"<div class='card'><div class='l'>Zhodnotenie</div><div class='v {cls(p.gain)}'>{pct(p.gain_pct)}</div></div></div>")
    h.append("<section><h2>Vývoj hodnoty</h2><svg id='chart' viewBox='0 0 900 320'></svg><div id='tip' class='tip'></div>"
             "<div class='legend'><span><i style='background:#2b5ea8'></i>hodnota portfólia</span><span><i style='background:#9a9a94'></i>vložené peniaze</span></div></section>")
    h.append("<section><h2>Jednotlivé vklady</h2><div class='wrap'><table><thead><tr><th>Dátum</th><th class='t'>Od koho</th><th>Vklad</th><th>Hodnota dnes</th><th>Zisk / strata</th><th>%</th></tr></thead><tbody>")
    for r in rows:
        h.append(f"<tr><td>{sk(r['date'])}</td><td class='t'>{html.escape(r['note'])}</td><td>{eur2(r['amount'])}</td><td>{eur2(r['value'])}</td>"
                 f"<td class='{cls(r['gain'])}'>{'+' if r['gain']>=0 else ''}{eur2(r['gain'])}</td><td class='{cls(r['gain'])}'>{pct(r['gain_pct'])}</td></tr>")
    h.append(f"</tbody><tfoot><tr><td colspan='2'>Spolu ({len(rows)} vkladov)</td><td>{eur2(p.total_deposits)}</td><td>{eur2(p.value)}</td>"
             f"<td class='{cls(p.gain)}'>{'+' if p.gain>=0 else ''}{eur2(p.gain)}</td><td class='{cls(p.gain)}'>{pct(p.gain_pct)}</td></tr></tfoot></table></div></section>")
    h.append("<section><h2>Po rokoch</h2><div class='wrap'><table><thead><tr><th>Rok</th><th>Hodnota na začiatku</th><th>Vklady v roku</th><th>Hodnota na konci</th><th>Zisk / strata</th><th>Výnos (TWR)</th></tr></thead><tbody>")
    for y in ys:
        lab = f"{y['year']}{' (do ' + sk(p.as_of) + ')' if y['partial'] else ''}"
        h.append(f"<tr><td>{lab}</td><td>{eur(y['start'])}</td><td>{eur(y['deposits'])}</td><td>{eur(y['end'])}</td>"
                 f"<td class='{cls(y['gain'])}'>{'+' if y['gain']>=0 else ''}{eur(y['gain'])}</td><td class='{cls(y['twr_pct'])}'>{pct(y['twr_pct'])}</td></tr>")
    h.append("</tbody></table></div><p class='note'>Výnos (TWR) = časovo vážený výnos, t. j. výkonnosť samotného portfólia bez vplyvu toho, kedy prišli vklady.</p></section>")
    h.append("<section><h2>Zloženie portfólia</h2><div class='wrap'><table><thead><tr><th class='t'>ETF</th><th>Kľúč</th><th>Podiel dnes</th><th>Hodnota</th></tr></thead><tbody>")
    for t, w in cfg["key"].items():
        u, v, wt = hold.get(t, (0, 0, 0))
        h.append(f"<tr><td class='t'>{html.escape(cfg['tickers'][t]['name'])} <span class='note'>({t})</span></td><td>{w*100:.0f} %</td><td>{wt*100:.1f} %</td><td>{eur(v)}</td></tr>")
    h.append("</tbody></table></div></section>")
    h.append(f"<p class='note'>Zjednodušenia: každý vklad sa počíta ako okamžite investovaný podľa kľúča {key_txt} za záverečnú cenu prvého obchodného dňa, bez poplatkov. "
             "Skutočné portfólio sa preto môže mierne líšiť. Ceny: Borsa Italiana (EUR), zdroj Yahoo Finance.</p>")
    h.append(f"<script>window.__data={json.dumps(data)};</script><script>{JS}</script></main></body></html>")
    return "".join(h)

def build_site(cfg, portfolios, prices):
    site = abspath(cfg, cfg["site_dir"])
    os.makedirs(site, exist_ok=True)
    # blank landing page so the site root reveals nothing
    with open(os.path.join(site, "index.html"), "w", encoding="utf-8") as f:
        f.write("<!doctype html><meta charset='utf-8'><meta name='robots' content='noindex'><title>Portfólio</title>")
    out = {}
    for pid, p in portfolios.items():
        tok = cfg["people"][pid]["token"]
        d = os.path.join(site, tok); os.makedirs(d, exist_ok=True)
        path = os.path.join(d, "index.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(render(cfg, p, prices))
        out[pid] = f"{tok}/"
    return out
