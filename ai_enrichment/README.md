# ai_enrichment/

Enriches raw Trustpilot reviews with AI-generated analysis using GPT-4o-mini.
For each review, it produces: sentiment, category, pain point, and an actionable
insight for the sales team.

## Sources

| `--source` | Input table | Output table |
|---|---|---|
| `default` | `reviews.reviews_raw` | `reviews.reviews_enriched` |
| `fr` | `reviews.reviews_raw_fr` | `reviews.reviews_enriched_fr` |

## Usage

```bash
# Enrich all unenriched reviews for Target leads
python -m ai_enrichment.main --source default

# Enrich all unenriched reviews for FR brands
python -m ai_enrichment.main --source fr

# Limit for testing
python -m ai_enrichment.main --source default --limit 20
```

## Idempotence

The enrichment uses a `LEFT JOIN` to skip reviews already in the enriched table.
Re-running the command is safe — only new reviews are processed.

```sql
SELECT r.*
FROM reviews_raw r
LEFT JOIN reviews_enriched e ON r.review_id = e.review_id
WHERE e.review_id IS NULL
```

## AI output schema

| Field | Values | Description |
|---|---|---|
| `sentiment` | `positive` / `neutral` / `negative` | Overall review tone |
| `category` | `shipping` / `support` / `product` / `returns` / `pricing` / `other` | Main complaint or praise category |
| `pain_point` | Free text or `null` | Specific issue (null for positive reviews) |
| `actionable_insight` | Free text | Sales-ready insight — never null |
| `model_used` | `gpt-4o-mini` | LLM model used for traceability |
| `enriched_at` | Timestamp | When enrichment ran |

## Files

| File | Purpose |
|---|---|
| `config.py` | Constants — BQ tables, OpenAI model, batch size. Uses `override=False` for Docker compatibility |
| `bigquery_client.py` | BQ operations — connect, create enriched table, load unenriched reviews, upload results |
| `enricher.py` | Calls GPT-4o-mini in batches, parses JSON response, handles errors |
| `prompts.py` | System and user prompt templates |
| `main.py` | CLI entry point — argument parsing, orchestration, progress tracking |

## Cost

GPT-4o-mini is used deliberately over GPT-4o for cost efficiency.
At ~500 tokens per review (input + output), enriching 10,000 reviews costs
approximately $0.15 at current pricing.
