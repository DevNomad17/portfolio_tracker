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

- `config.json` – distribution key (40/10/15/5/30), tickers, people (URL path = person id)
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
Netlify). Root page is blank; each person gets `https://<host>/<id>/` (tana, nina, filip, riso, pali).

## GitHub Pages setup (one-time)

1. Create an empty **public** repo `portfolio_tracker` on github.com (no README).
2. In Terminal: `cd ~/Documents/portfolio_tracker && git push -u origin main`
   (username = GitHub login, password = a personal access token with `repo` scope, or use SSH).
3. On GitHub: Settings → Pages → Source: **GitHub Actions**. Settings → Actions → General →
   Workflow permissions: **Read and write**.
4. The workflow `.github/workflows/publish.yml` then runs on every push and every weekday at
   17:15 UTC: fetches prices, commits the cache, rebuilds and deploys `site/`.

Pages: `https://devnomad17.github.io/portfolio_tracker/tana/` (nina, filip, riso, pali likewise).
After adding a deposit to the workbook: `git commit -am "vklad" && git push` (or run the workflow manually).
