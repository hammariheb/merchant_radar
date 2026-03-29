# dashboard/bigquery_client.py

import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

BQ_PROJECT  = st.secrets["BQ_PROJECT"]
BQ_LOCATION = "EU"
BQ_DATASET  = "analytics"


@st.cache_resource
def get_bq_client() -> bigquery.Client:
    """
    BQ client using service account from Streamlit secrets.
    Required on Streamlit Cloud — gcloud ADC is not available there.
    """
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return bigquery.Client(
        project=BQ_PROJECT,
        credentials=credentials,
        location=BQ_LOCATION,
    )


@st.cache_data(ttl=600)
def load_domain_insights() -> pd.DataFrame:
    """Load mart_domain_insights — one row per domain."""
    query = f"""
        SELECT *
        FROM `{BQ_PROJECT}.{BQ_DATASET}.mart_domain_insights`
        ORDER BY
            CASE outreach_signal
                WHEN 'priority_lead'          THEN 1
                WHEN 'warm_lead'              THEN 2
                WHEN 'no_stack_prospect'      THEN 3
                WHEN 'inbox_upgrade_prospect' THEN 4
                WHEN 'competitor_prospect'    THEN 5
                WHEN 'lightweight_prospect'   THEN 6
                WHEN 'low_priority'           THEN 7
                ELSE 8
            END,
            review_count DESC
    """
    return get_bq_client().query(query, location=BQ_LOCATION).to_dataframe()


@st.cache_data(ttl=600)
def load_category_agg() -> pd.DataFrame:
    """Load int_category_agg — review counts by domain and category."""
    query = f"""
        SELECT *
        FROM `{BQ_PROJECT}.{BQ_DATASET}.int_category_agg`
        ORDER BY domain, review_count DESC
    """
    return get_bq_client().query(query, location=BQ_LOCATION).to_dataframe()


@st.cache_data(ttl=600)
def load_reviews_for_domain(domain: str) -> pd.DataFrame:
    """Load individual reviews for a domain — negatives first."""
    query = f"""
        SELECT *
        FROM `{BQ_PROJECT}.{BQ_DATASET}.mart_reviews_detail`
        WHERE domain = '{domain}'
        ORDER BY
            CASE sentiment
                WHEN 'negative' THEN 1
                WHEN 'neutral'  THEN 2
                ELSE 3
            END,
            star_rating ASC
    """
    return get_bq_client().query(query, location=BQ_LOCATION).to_dataframe()