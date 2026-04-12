# .github/workflows/

GitHub Actions CI/CD pipeline for MerchantRadar.

## Workflows

### `ci.yml` — Continuous Integration

**Triggers:** every pull request to `main`

**Steps:**
1. `ruff check` — lint `scraper/`, `ai_enrichment/`, `builtwith_domain_collector/`
2. `dbt deps` — install dbt packages
3. `dbt compile` — validate SQL syntax and Jinja templating (no BigQuery queries)

CI catches broken SQL and import errors before they reach production.
`dbt compile` is used deliberately over `dbt build` — it validates the entire
project without executing any queries, making CI fast (~2 min) and free.

### `cd.yml` — Continuous Deployment

**Triggers:** push to `main` when pipeline code changes
(`dbt_transformation/`, `scraper/`, `ai_enrichment/`, `builtwith_domain_collector/`)

**Steps:**
1. `dbt deps` — install dbt packages
2. `dbt build --fail-fast` — run all models + tests in production

`--fail-fast` stops immediately on the first test failure rather than
continuing and potentially writing bad data to downstream tables.

The job uses `environment: prod` which requires manual approval in GitHub
before deploying — configurable under repository Settings → Environments.

## Required secrets

Go to: **GitHub repo → Settings → Secrets and variables → Actions**

| Secret | Value |
|---|---|
| `GCP_SERVICE_ACCOUNT_JSON` |
| `BQ_PROJECT` | 

## How credentials work in CI

The workflow writes the GCP service account JSON to a temp file and sets
`GOOGLE_APPLICATION_CREDENTIALS` pointing to it. The dbt `profiles.yml`
reads this via `env_var('GOOGLE_APPLICATION_CREDENTIALS')` — no hardcoded
paths anywhere.
