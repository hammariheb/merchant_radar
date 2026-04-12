# builtwith_domain_collector/

Scrapes the BuiltWith French top eCommerce rankings and exports the domain list
as a CSV for dbt seed ingestion.

This module is a **domain list collector** — it does not touch BigQuery directly.
Its output feeds `dbt seed` which loads it into `analytics.leads_builtwith_fr`,
which the `scraper/` then uses as its FR domain list.

## Flow

```
builtwith.com/top-sites/France/eCommerce
    ↓
builtwith_domain_collector (HTTP scrape)
    ↓
leads_builtwith_fr.csv
    ↓
dbt seed → analytics.leads_builtwith_fr (BigQuery)
    ↓
scraper --source fr
```

## Usage

```bash
# Default — 20 pages (~1,000 domains)
python -m builtwith_domain_collector.main

# Custom page count
python -m builtwith_domain_collector.main --pages 5

# Custom output path
python -m builtwith_domain_collector.main --output my_leads.csv

# Skip dbt seed CSV (output CSV only)
python -m builtwith_domain_collector.main --no-seed
```

## Files

| File | Purpose |
|---|---|
| `config.py` | Constants — URL, page count, delays, User-Agent rotation, seed column order |
| `scraper.py` | HTTP fetch + HTML parse + pagination — all in one file. Handles rate limiting (429/403 with exponential backoff), domain cleaning, deduplication |
| `main.py` | CLI entry point — argument parsing, CSV export, dbt seed CSV export |

## Output columns

| Column | Description |
|---|---|
| `rank` | BuiltWith rank (1 = most popular) |
| `domain` | Cleaned domain (e.g. `sezane.com`) |
| `sales_revenue` | Estimated revenue tier from BuiltWith |
| `tech_spend` | Estimated tech spend tier |
| `social_followers` | Social follower count tier |
| `traffic_tier` | Traffic tier (High / Medium / Low) |
| `country` | Always `FR` |
| `source` | Always `builtwith_top_ecommerce_fr` |

## Rate limiting

BuiltWith aggressively rate-limits scrapers. The module handles this with:
- Random User-Agent rotation on every request
- Polite delay of 2–4 seconds between pages
- Exponential backoff (30s → 60s → 120s) on 429/403 responses
- Max 3 retries per page before giving up
