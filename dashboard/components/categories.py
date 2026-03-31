import streamlit as st
import pandas as pd
import plotly.express as px


def render(df_domains: pd.DataFrame, df_categories: pd.DataFrame) -> None:
    st.header("Category Breakdown")

    all_domains = df_domains["domain"].tolist()
    if not all_domains:
        st.info("No domains in the current filter selection.")
        return

    selected = st.selectbox("Select a domain", all_domains, key="cat_select")

    # Si not_found → message et stop, pas de graphique
    row = df_domains[df_domains["domain"] == selected].iloc[0]
    if row["trustpilot_status"] == "not_found":
        st.info(f"**{selected}** is not listed on Trustpilot — no review category data available.")
        return

    domain_cats = df_categories[df_categories["domain"] == selected].copy()
    if domain_cats.empty:
        st.info(f"No category data available for {selected}.")
        return

    domain_cats = domain_cats.sort_values("review_count", ascending=True)

    c1, c2 = st.columns([2, 1])
    with c1:
        fig = px.bar(domain_cats, x="review_count", y="category", orientation="h",
                     color="avg_rating",
                     color_continuous_scale=["#E24B4A", "#EF9F27", "#639922"],
                     range_color=[1, 5],
                     title=f"Review categories — {selected}",
                     labels={"review_count": "Number of reviews", "category": "Category", "avg_rating": "Avg ⭐"})
        st.plotly_chart(fig, width="stretch")
    with c2:
        st.subheader("Details")
        for _, row in domain_cats.sort_values("review_count", ascending=False).iterrows():
            st.metric(label=row["category"],
                      value=f"{int(row['review_count'])} reviews",
                      delta=f"{row.get('pct_of_domain', 0):.1f}% of total")