import logging
import time

from google.cloud import bigquery

from .config import (
    BQ_PROJECT,
    BQ_LOCATION,
    BQ_BATCH_SIZE,
    LEADS_DATASET,
    LEADS_TABLE,
    FR_LEADS_DATASET,
    FR_LEADS_TABLE,
    REVIEWS_DATASET,
    REVIEWS_TABLE,
    REVIEWS_TABLE_FR,
)

log = logging.getLogger(__name__)

BQ_SCHEMA = [
    bigquery.SchemaField("domain",          "STRING"),
    bigquery.SchemaField("trustpilot_slug", "STRING"),
    bigquery.SchemaField("review_id",       "STRING"),
    bigquery.SchemaField("review_text",     "STRING"),
    bigquery.SchemaField("review_title",    "STRING"),
    bigquery.SchemaField("star_rating",     "INTEGER"),
    bigquery.SchemaField("date_published",  "DATE"),
    bigquery.SchemaField("reviewer_name",   "STRING"),
    bigquery.SchemaField("company_replied", "BOOLEAN"),
    bigquery.SchemaField("language",        "STRING"),
    bigquery.SchemaField("ingested_at",     "TIMESTAMP"),
]


def get_client() -> bigquery.Client:
    client = bigquery.Client(project=BQ_PROJECT)
    log.info(f"✅ BigQuery connected — {BQ_PROJECT}")
    return client


def _source_table(source: str) -> tuple[str, str, str]:
    """Returns (leads_dataset, leads_table, reviews_table) for the given source."""
    if source == "fr":
        return FR_LEADS_DATASET, FR_LEADS_TABLE, REVIEWS_TABLE_FR
    return LEADS_DATASET, LEADS_TABLE, REVIEWS_TABLE


def ensure_reviews_table(client: bigquery.Client, source: str = "default") -> None:
    _, _, reviews_table = _source_table(source)

    ds          = bigquery.Dataset(f"{BQ_PROJECT}.{REVIEWS_DATASET}")
    ds.location = BQ_LOCATION
    client.create_dataset(ds, exists_ok=True)

    table_id                = f"{BQ_PROJECT}.{REVIEWS_DATASET}.{reviews_table}"
    table                   = bigquery.Table(table_id, schema=BQ_SCHEMA)
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="ingested_at",
    )
    table.clustering_fields = ["domain"]
    client.create_table(table, exists_ok=True)
    log.info(f"✅ Table ready: {table_id}")
    time.sleep(3)


def load_domains(
    client:     bigquery.Client,
    source:     str        = "default",
    limit:      int | None = None,
    start_from: str | None = None,
) -> list[str]:
    leads_dataset, leads_table, _ = _source_table(source)

    start_clause = f"AND LOWER(TRIM(domain)) >= '{start_from.lower()}'" if start_from else ""
    limit_clause = f"LIMIT {limit}" if limit else ""

    query = f"""
        SELECT DISTINCT LOWER(TRIM(domain)) AS domain
        FROM `{BQ_PROJECT}.{leads_dataset}.{leads_table}`
        WHERE domain IS NOT NULL
          AND TRIM(domain) != ''
          {start_clause}
        ORDER BY domain
        {limit_clause}
    """
    domains = [row["domain"] for row in client.query(query, location=BQ_LOCATION).result()]
    log.info(f"✅ {len(domains)} domains loaded from {leads_dataset}.{leads_table}")
    return domains


def get_last_scraped_dates(
    client: bigquery.Client,
    source: str = "default",
) -> dict[str, str]:
    """
    Returns a dict mapping domain → last review date already in BigQuery.
    Used for incremental scraping: the scraper stops when it hits a review
    older than or equal to this date.

    Example return:
        {
            "gymshark.com":  "2025-03-15",
            "sezane.com":    "2025-03-10",
        }

    Domains not yet scraped are not included in the dict — the scraper
    treats missing entries as "scrape everything" (full scrape for new domains).
    """
    _, _, reviews_table = _source_table(source)

    query = f"""
        SELECT
            domain,
            CAST(MAX(date_published) AS STRING) AS last_date
        FROM `{BQ_PROJECT}.{REVIEWS_DATASET}.{reviews_table}`
        WHERE date_published IS NOT NULL
        GROUP BY domain
    """
    try:
        result = client.query(query, location=BQ_LOCATION).result()
        dates  = {row["domain"]: row["last_date"] for row in result}
        log.info(f"✅ {len(dates)} domains with existing reviews loaded")
        return dates
    except Exception as e:
        log.warning(f"  Could not load last scraped dates: {e} — full scrape will run")
        return {}


def upload_reviews(
    client: bigquery.Client,
    rows:   list[dict],
    source: str = "default",
) -> None:
    if not rows:
        return

    _, _, reviews_table = _source_table(source)
    table_id            = f"{BQ_PROJECT}.{REVIEWS_DATASET}.{reviews_table}"

    for i in range(0, len(rows), BQ_BATCH_SIZE):
        batch  = rows[i:i + BQ_BATCH_SIZE]
        errors = client.insert_rows_json(table_id, batch)
        if errors:
            log.error(f"❌ BQ insert errors: {errors[:2]}")
        else:
            log.info(f"⬆  {len(batch)} rows → {table_id}")