# Rodinné portfóliá – tracker

Static tracker for the family ETF mirror portfolios. Source of truth stays `rodina_portfolia.xlsm`
(one sheet per portfolio: `Trade Date` YYYYMMDD, date, note, EUR amount). People sharing a sheet
(tana_nina, filip_riso) each get an identical portfolio.

## Daily / whenever you add a deposit

    cd ~/Documents/portfolio_tracker
    python3 -m tracker all        # fetch new prices (Yahoo, Stooq fallback) + rebuild site/

Other commands:

    python3 -m tracker update     # only refresh data/prices/*.csv
    python3 -m tracker build      # only rebuild site/ from cached prices
    python3 -m tracker status     # cache coverage + deposits per person
    python3 -m tracker summary 2025   # exports/zhrnutie_2025.md for the newsletter
    python3 -m unittest discover tests

## Layout

- `config.json` – distribution key (40/10/15/5/30), tickers, people + their secret URL tokens
- `tracker/ledger.py` – reads the workbook (validates dates/amounts, refuses bad rows)
- `tracker/prices.py` – price cache (`data/prices/<T>.csv`) and updater
- `tracker/engine.py` – virtual-units calculation, daily value series, yearly summary (TWR)
- `tracker/build.py` – one self-contained HTML page per person → `site/<token>/index.html`
- `tracker/export.py` – yearly Markdown summary
- `tests/` – unit tests with synthetic prices

## Model assumptions (stated on every page)

Static key, zero fees, each deposit invested at the close of the first trading day on/after the
deposit date. Values are an approximation of the real Degiro portfolio.

## Publishing

`site/` is the whole deliverable — upload it anywhere static (GitHub Pages, Cloudflare Pages,
Netlify). Root page is blank; each person gets `https://<host>/<token>/`.
