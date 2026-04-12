# airflow/

Weekly pipeline orchestration using Apache Airflow running in Docker.

## DAG: `merchantradar_weekly`

Runs every Monday at 06:00 UTC. Orchestrates the full MerchantRadar pipeline
from domain collection through to dbt mart rebuild.

```
scrape_builtwith
      ↓
seed_and_stage
      ↓
scrape_reviews ──────┐
scrape_reviews_fr ───┤  (parallel)
      ↓              ↓
enrich_reviews ──────┐
enrich_reviews_fr ───┤  (parallel)
      ↓              ↓
    dbt_build
      ↓
notify_success
```

## Task descriptions

| Task | Command | Description |
|---|---|---|
| `scrape_builtwith` | `python -m builtwith_domain_collector.main --pages 100` | Refresh FR domain list from BuiltWith |
| `seed_and_stage` | `dbt seed && dbt run --select stg_domains` | Load new CSV into BQ, rebuild domain staging |
| `scrape_reviews` | `python -m scraper.main --source default --incremental` | Scrape new Target lead reviews only |
| `scrape_reviews_fr` | `python -m scraper.main --source fr --incremental` | Scrape new FR brand reviews only |
| `enrich_reviews` | `python -m ai_enrichment.main --source default` | AI-enrich new Target reviews |
| `enrich_reviews_fr` | `python -m ai_enrichment.main --source fr` | AI-enrich new FR reviews |
| `dbt_build` | `dbt build --no-partial-parse` | Rebuild all models staging → marts |
| `notify_success` | Python callback | Log completion summary |

## Starting Airflow

```bash
# Copy GCP credentials to project root
cp /path/to/gcp-key.json ./gcp_credentials.json

# First-time setup
docker-compose up airflow-init

# Start
docker-compose up -d airflow-webserver airflow-scheduler

# Open UI
open http://localhost:8080
# username: airflow / password: airflow
```

## Environment variables (docker-compose)

| Variable | Where set | Value |
|---|---|---|
| `BQ_PROJECT` | `.env` | `xxxxxxxxx` |
| `OPENAI_API_KEY` | `.env` | OpenAI key |
| `GOOGLE_APPLICATION_CREDENTIALS` | `docker-compose.yml` | `/opt/airflow/credentials/gcp_merchantradar_credentials.json` |
| `DBT_PROFILES_DIR` | `docker-compose.yml` | `/opt/airflow/projects/merchant_radar/dbt_transformation` |

## Testing individual tasks

```bash
# Test a single task without running the full DAG
docker-compose exec airflow-scheduler \
  airflow tasks test merchantradar_weekly <task_id> 2025-01-01
```

## Incremental logic

Both scraping tasks run with `--incremental`:
- `bq_client.get_last_scraped_dates()` queries `MAX(date_published)` per domain
- The scraper stops paginating when it hits reviews older than that date
- New domains always get a full scrape
- Both tasks are idempotent — safe to retry on failure
