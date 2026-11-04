# Market Intelligence – Data API

A compact FastAPI + Supabase data-ingestion service for Indian equities. It fetches daily OHLCV and fundamentals with yfinance, stores each trading session as one row in Supabase, maintains one CSV per stock, and ingests news/announcements.

## Quick start

```bash
make bootstrap          # venv, deps, .env from .env.example, verify_setup
# Edit .env with real Supabase URL, service role key, and API_KEY
# Run in Supabase SQL Editor: schema.sql → migrations/001 → seed.sql
make run                # API on :8000
make smoke              # health + list stocks + sample price update (API must be running)
```

Railway: connect repo, set env vars from `.env.example`, deploy (`railway.toml` included). Schedule `scripts/cron_update.sh` with `BASE_URL` + `API_KEY`.

## Architecture

```text
market_intelligence/
├── main.py                         # FastAPI entry point
├── data_manager/
│   ├── scripts/                    # CLI scheduled jobs
│   ├── services/                   # price, Supabase, CSV, news, announcement logic
│   └── data/historical_prices/      # one CSV per stock_id
├── services/                        # your existing custom fetcher modules
│   ├── news_fetcher.py              # you provide fetch_news(stock_id)
│   └── ann_fetcher.py               # you provide fetch_corp_ann(stock_id)
└── database/schema.sql              # create Supabase tables
```

## 1. Supabase setup

Run `database/schema.sql` in Supabase SQL Editor. Existing projects should also run `database/migrations/001_bse_scrip_code.sql`. Optional: `database/read_policies.sql` for authenticated read access; create a Storage bucket per `database/storage_setup.sql` for CSV mirroring.

This version uses four tables: `stock_list`, `stock_prices`, `news`, `announcements`. `stock_list.bse_scrip_code` supports BSE corporate announcements (e.g. `500325` for Reliance).

Add stocks to `stock_list`, for example:

```sql
insert into public.stock_list (stock_id, symbol, yfinance_symbol, company_name, exchange) values
('STK001', 'RELIANCE', 'RELIANCE.NS', 'Reliance Industries', 'NSE'),
('STK002', 'TCS', 'TCS.NS', 'Tata Consultancy Services', 'NSE');
```

For BSE tickers use the Yahoo Finance suffix where supported (commonly `.BO`). Always verify the ticker resolves before bulk ingestion.

## 2. Local setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and a strong `API_KEY` in `.env`. Never expose the service-role key in frontend code. The Supabase Python client uses the Data API; ensure the tables are available to that API. See [Supabase Python setup](https://supabase.com/docs/reference/python/installing).

## 3. Run API

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check (API key config + Supabase connectivity) |
| POST | `/update/stocks` | Update all stocks; includes prices, fundamentals, news and announcements |
| POST | `/update/prices` | Update prices only (optional JSON body with `backfill_from`) |
| POST | `/backfill/prices` | Historical price load; requires `backfill_from` in JSON body |
| POST | `/update/news` | Update news only |
| POST | `/update/announcements` | Update announcements only |
| GET | `/stocks` | List stocks (API key) |
| GET | `/stocks/{stock_id}` | Stock metadata + fundamentals + latest prediction |
| GET | `/stocks/{stock_id}/prices` | Recent OHLCV rows (`limit` query param) |
| GET | `/stocks/{stock_id}/news` | Recent news rows |
| GET | `/admin/stocks` | List all stocks including inactive |
| POST | `/admin/stocks` | Create a stock (no SQL required) |
| PATCH | `/admin/stocks/{stock_id}` | Update symbols, `active`, `bse_scrip_code`, etc. |

Write/update jobs attach an `alert` object when failures occur (Slack webhook and/or SMTP email — see `.env.example`).

```bash
curl -X POST http://localhost:8000/update/stocks \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{"include_fundamentals": true, "include_news": true, "include_announcements": true}'
```

Single stock:

```bash
curl -X POST 'http://localhost:8000/update/stocks' \
  -H 'Content-Type: application/json' -H 'x-api-key: YOUR_API_KEY' \
  -d '{"stock_id":"STK001"}'
```

Backfill prices from a date (inclusive):

```bash
curl -X POST 'http://localhost:8000/backfill/prices' \
  -H 'Content-Type: application/json' -H 'x-api-key: YOUR_API_KEY' \
  -d '{"stock_id":"STK001","backfill_from":"2020-01-01","include_fundamentals":true}'
```

CLI backfill (same logic):

```bash
python -m data_manager.scripts.backfill_prices --from 2020-01-01 --stock-id STK001
```

## 4. Daily update behavior

- Reads active stocks from `stock_list`.
- Reads the latest stored `trade_date` for each stock from `stock_prices`.
- Fetches from that date onward (inclusive) so it can add missing trading sessions and refresh a provider correction for the latest stored date. On a stock's first run, it fetches `PRICE_INITIAL_LOOKBACK_DAYS` (default **365**) when `stock_prices` is empty.
- Upserts every fetched OHLCV session into `stock_prices` using `(stock_id, trade_date)`; no duplicate daily rows.
- There is no rolling 31-day price cache, no `recent_prices` JSON field, and no job that maintains a last-31-days dataset. The full OHLCV history is kept as dated rows in `stock_prices` and in the per-stock CSV.
- Merges the same rows into `data_manager/data/historical_prices/STK001.csv`, sorted by date and deduplicated.
- Updates the fundamentals JSONB snapshot on `stock_list`.
- Calls the optional prediction function only if configured.
- Processes each stock independently so one failure does not stop the entire batch.

The updater is incremental: it starts at the latest stored trading date, inclusive, so it can catch up missed sessions since that date without maintaining a separate rolling price window. For a stock with no stored prices, it uses a short initial fetch window; load older history separately if required. yfinance may revise adjusted data and may not publish final prices immediately after market close; trigger the update after the NSE/BSE close and validate results.

## 5. News ingestion

The built-in provider searches Google News RSS for each company name/ticker. It is free and requires no API key. It stores headline, summary, publisher, source URL and publication time. It does not scrape full article text. Google RSS is an unofficial feed and can change; treat it as best-effort.

Your custom `services/news_fetcher.py` is also called when `NEWS_PROVIDERS` includes `custom` (default: `google_rss,custom`). It must define:

```python
def fetch_news(stock_id: str) -> list[dict]:
    return [{
        "headline": "Company announces ...",
        "content": "Short summary",
        "source": "Publisher",
        "source_url": "https://publisher.example/article",
        "published_at": "2026-11-02T10:00:00+05:30",
    }]
```

Duplicate `(stock_id, source_url)` records are ignored. **`services/ann_fetcher.py`** is included for NSE-listed symbols (`exchange = NSE`, `symbol` = NSE ticker such as `RELIANCE`). It calls the NSE corporate announcements API. For BSE-only names, add your own fetcher logic or extend `ann_fetcher.py`. Custom modules should expose `fetch_corp_ann(stock_id)` and return dictionaries with `title`, `source_url`, optional `category`, `description`, and `published_at`.

## 6. Optional prediction hook

An example SMA crossover model ships in `prediction/predict.py`. Default in `.env.example`:

```env
PREDICTION_FUNCTION=prediction.predict:predict_stock
```

Keep production models outside `data_manager` if you prefer. The function is called as:

```python
predict_stock(stock=stock_metadata, prices=list_of_ohlcv_rows)
```

It should return a JSON-serializable dictionary. If your existing function has a different signature, change only `_run_prediction()` in `data_manager/services/stock_updater.py`.

## 7. Railway deployment

Deploy this repository as a Railway service from GitHub and set the environment variables in Railway. Start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Use Railway Cron (or another scheduler) to call `POST /update/stocks` after market data is published. Keep the API key secret. Set `APP_ENV=production` on Railway and use a separate Supabase project for local `APP_ENV=development` if possible.

**Important CSV note:** Railway's local filesystem is not durable across all redeploy/restart scenarios. Supabase `stock_prices` is the durable source of truth. When `SUPABASE_STORAGE_BUCKET` is set, each CSV merge is upserted to Storage under `historical_prices/{stock_id}.csv`.

## 8. Tests and CI

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```

GitHub Actions runs the same tests on push (`.github/workflows/ci.yml`).

## Notes

- yfinance is unofficial and intended for research/personal use; review Yahoo Finance terms before commercial/public use.
- This starter fetches OHLCV incrementally from the latest date already stored (inclusive) and appends/upserts the dated rows. It does not maintain a last-31-days cache and does not claim that Yahoo data is exchange-grade or real-time.
- Fundamentals from `Ticker.info` can be incomplete, delayed or inconsistent across companies; treat missing values as unavailable, not zero.
- Use only the Supabase service-role key on the backend. Add read policies separately if your frontend needs direct access.
