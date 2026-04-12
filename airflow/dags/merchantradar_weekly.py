
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

# ── Default args ──────────────────────────────────────────────
default_args = {
    "owner":            "merchantradar",
    "depends_on_past":  False,
    "retries":          2,
    "retry_delay":      timedelta(minutes=10),
}

# ── Project path ──────────────────────────────────────────────
PROJECT_DIR  = "/opt/airflow/projects/merchant_radar"
DBT_DIR      = f"{PROJECT_DIR}/dbt_transformation"
VENV         = "python"
# Prepend project root to PYTHONPATH so python -m finds your modules
PYTHON_CMD   = f"PYTHONPATH={PROJECT_DIR} python"


def _notify_success(**context):
    """Called at the end of a successful run — logs a summary."""
    run_date = context["ds"]
    print(f"✅ MerchantRadar pipeline completed successfully for week of {run_date}")


def _notify_failure(context):
    """Called on any task failure — can be extended to send Slack/email."""
    task_id  = context["task_instance"].task_id
    run_date = context["ds"]
    print(f"❌ Task {task_id} failed for run date {run_date}")


# ── DAG definition ────────────────────────────────────────────
with DAG(
    dag_id="merchantradar_weekly",
    description="Weekly MerchantRadar pipeline — scraping, enrichment, dbt, dashboard refresh",
    schedule="0 6 * * 1",          # Every Monday at 06:00 UTC
    start_date=datetime(2025, 1, 1),
    catchup=False,                  # Don't backfill missed runs
    max_active_runs=1,              # Never run two pipelines simultaneously
    default_args=default_args,
    tags=["merchantradar", "weekly", "production"],
    on_failure_callback=_notify_failure,
) as dag:

    # ── Step 1: Scrape BuiltWith ──────────────────────────────
    scrape_builtwith = BashOperator(
        task_id="scrape_builtwith",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"{VENV} -m builtwith_domain_collector.main --pages 100 "
            f"--output leads_builtwith_fr.csv"
        ),
        doc_md="""
        Scrapes builtwith.com/top-sites/France/eCommerce.
        Saves CSV to leads_builtwith_fr.csv and dbt seed path.
        Runs up to 100 pages (~1,928 domains).
        """,
    )

    # ── Step 2: dbt seed + stg_leads_builtwith_fr ────────────
    seed_and_stage = BashOperator(
        task_id="seed_and_stage",
        bash_command=(
            f"cd {DBT_DIR} && "
            f"dbt seed --select leads_builtwith_fr &&"
            f"dbt run --select stg_domains"
        ),
        doc_md="""
        Loads the BuiltWith CSV into BigQuery via dbt seed.
        Then rebuilds stg_domains to include the fresh FR domains.
        """,
    )

    # ── Step 3: Incremental Trustpilot scraping — Gorgias ────
    scrape_reviews = BashOperator(
        task_id="scrape_reviews",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"{VENV} -m scraper.main --source default --incremental"
        ),
        doc_md="""
        Scrapes new Trustpilot reviews for Target leads.
        --incremental: only fetches reviews newer than the last ingestion date.
        Writes to reviews.reviews_raw.
        """,
        execution_timeout=timedelta(hours=3),
    )

    # ── Step 4: Incremental Trustpilot scraping — FR brands ──
    scrape_reviews_fr = BashOperator(
        task_id="scrape_reviews_fr",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"{VENV} -m scraper.main --source fr --incremental"
        ),
        doc_md="""
        Scrapes new Trustpilot reviews for French top eCommerce brands.
        --incremental: only fetches reviews newer than the last ingestion date.
        Writes to reviews.reviews_raw_fr.
        """,
        execution_timeout=timedelta(hours=4),
    )

    # ── Step 5: AI enrichment — Gorgias reviews ──────────────
    enrich_reviews = BashOperator(
        task_id="enrich_reviews",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"{VENV} -m ai_enrichment.main --source default"
        ),
        doc_md="""
        Enriches new Gorgias reviews with AI (sentiment, category, pain_point).
        LEFT JOIN ensures only unenriched reviews are processed.
        Writes to reviews.reviews_enriched.
        """,
        execution_timeout=timedelta(hours=1),
    )

    # ── Step 6: AI enrichment — FR reviews ───────────────────
    enrich_reviews_fr = BashOperator(
        task_id="enrich_reviews_fr",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"{VENV} -m ai_enrichment.main --source fr"
        ),
        doc_md="""
        Enriches new French reference reviews with AI.
        Writes to reviews.reviews_enriched_fr.
        """,
        execution_timeout=timedelta(hours=2),
    )

    # ── Step 7: dbt full build ────────────────────────────────
    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {DBT_DIR} && "
            f"dbt build --no-partial-parse --exclude stg_domains"
            # stg_domains already rebuilt in step 2
        ),
        doc_md="""
        Runs the full dbt pipeline:
          stg_reviews → stg_reviews_enriched
          int_reviews_agg → int_category_agg → int_benchmark_scores
          int_trend_analysis
          mart_domain_insights → mart_reviews_detail
        Includes all tests (dbt build = dbt run + dbt test).
        """,
        execution_timeout=timedelta(minutes=30),
    )

    # ── Step 8: Success notification ─────────────────────────
    notify_success = PythonOperator(
        task_id="notify_success",
        python_callable=_notify_success,
        trigger_rule=TriggerRule.ALL_SUCCESS,
        doc_md="Logs pipeline completion. Extend to send Slack message.",
    )

    # ── Dependencies ──────────────────────────────────────────
    # scrape_builtwith → seed_and_stage → scrape_reviews (parallel with scrape_reviews_fr)
    #                                   → scrape_reviews_fr
    #                 → enrich_reviews (after scrape_reviews)
    #                 → enrich_reviews_fr (after scrape_reviews_fr)
    #                 → dbt_build (after both enrichments)
    #                 → notify_success

    scrape_builtwith >> seed_and_stage

    seed_and_stage >> [scrape_reviews, scrape_reviews_fr]

    scrape_reviews    >> enrich_reviews
    scrape_reviews_fr >> enrich_reviews_fr

    [enrich_reviews, enrich_reviews_fr] >> dbt_build

    dbt_build >> notify_success