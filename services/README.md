Place your own integration modules here:

- `news_fetcher.py` — optional; exposes `fetch_news(stock_id)`. A stub is included (returns no extra items). Enable with `NEWS_PROVIDERS=custom` or keep default `google_rss,custom`.
- `ann_fetcher.py` — **included**: NSE corporate announcements via `fetch_corp_ann(stock_id)`. Requires `stock_list.symbol` as the NSE ticker (e.g. `RELIANCE`) and `exchange = NSE`.

Accepted keys for custom news: `headline` or `title`, `source_url` or `url`, optional `content`/`summary`, `source`, `published_at`.

For custom announcements, return dictionaries with `title` or `headline`, `source_url` or `url`, optional `category`, `description`, `published_at`.

These modules live outside `data_manager/`; updaters load them dynamically. Google News RSS runs when `NEWS_PROVIDERS` includes `google_rss`.
