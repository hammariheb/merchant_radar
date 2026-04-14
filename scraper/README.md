# scraper/

Scrapes Trustpilot reviews for two domain sources and writes them to BigQuery.

## Sources

| `--source` | Domain list | Target table |
|---|---|---|
| `default` | `leads.leads_raw` (Target prospecting list) | `reviews.reviews_raw` |
| `fr` | `analytics.leads_builtwith_fr` (BuiltWith FR seed) | `reviews.reviews_raw_fr` |

## Usage

```bash
# Full scrape — all domains
python -m scraper.main --source default
python -m scraper.main --source fr

# Incremental — only reviews newer than last ingestion date
python -m scraper.main --source default --incremental
python -m scraper.main --source fr --incremental

# Limited run for testing
python -m scraper.main --source default --limit 5

# Resume from a specific domain (after interruption)
python -m scraper.main --source default --start-from gymshark.com
```

## Incremental mode

`--incremental` reads `MAX(date_published)` per domain from the target BigQuery
table via `get_last_scraped_dates()`. The scraper stops pagination for a domain
when it hits a review older than or equal to that date.

New domains (not yet in BigQuery) always get a full scrape regardless of the flag.

This makes the scraper safe to run weekly without re-ingesting existing data.

## Files

| File | Purpose |
|---|---|
| `config.py` | All constants — BQ project, dataset names, table names, delays. Uses `override=False` so Docker env vars always win over `.env` |
| `bq_client.py` | BigQuery operations — connect, create table, load domains, get last scraped dates, upload reviews |
| `scraper.py` | Trustpilot HTTP scraping — fetches review pages for a single domain |
| `main.py` | CLI entry point — argument parsing, orchestration, progress bar, summary |

## BigQuery schema

```
reviews_raw / reviews_raw_fr
├── domain           STRING
├── trustpilot_slug  STRING
├── review_id        STRING
├── review_text      STRING
├── review_title     STRING
├── star_rating      INTEGER
├── date_published   DATE
├── reviewer_name    STRING
├── company_replied  BOOLEAN
├── language         STRING
└── ingested_at      TIMESTAMP  (partition key)
```

Table is partitioned by `ingested_at` (day) and clustered by `domain` for
cost-efficient queries.
