import streamlit as st
import pandas as pd

SENTIMENT_BADGE = {"positive": "🟢", "neutral": "🟡", "negative": "🔴"}

SIGNAL_LABEL = {
    "priority_lead":          "🔴 Priority Lead",
    "warm_lead":              "🟠 Warm Lead",
    "no_stack_prospect":      "🟣 No Support Stack",
    "inbox_upgrade_prospect": "🔵 Shopify Inbox → Upgrade",
    "competitor_prospect":    "🟤 On Competitor",
    "lightweight_prospect":   "🟢 Lightweight Tool",
    "low_priority":           "⚪ Low Priority",
    "research_needed":        "❓ Research Needed",
}

PITCH_MAP = {
    "no_stack_prospect":      "No support tool detected — ideal Gorgias candidate, pitch from scratch.",
    "inbox_upgrade_prospect": "Using Shopify Inbox (free/basic) — natural upgrade pitch to Gorgias.",
    "competitor_prospect":    "On a competitor (Zendesk/Intercom) — pitch eCommerce specialization.",
    "lightweight_prospect":   "Using a lightweight tool (Tidio/Chatra/Olark) — pitch full helpdesk upgrade.",
}


def _render_found(row: pd.Series, reviews: pd.DataFrame) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg Rating",  f"{row.get('avg_rating',0):.2f} ⭐")
    c2.metric("Reviews",     int(row.get("review_count",0)))
    c3.metric("% Positive",  f"{row.get('pct_positive',0):.1f}%")
    c4.metric("% Negative",  f"{row.get('pct_negative',0):.1f}%")
    st.markdown(f"**Signal:** {SIGNAL_LABEL.get(row.get('outreach_signal',''),'—')}")
    st.markdown(f"**Reply rate:** {row.get('reply_rate',0):.1f}%")
    st.divider()

    sentiment_filter = st.radio("Filter by sentiment",
                                ["All","negative","neutral","positive"],
                                horizontal=True, key="dd_sentiment")
    filtered = reviews[reviews["sentiment"] == sentiment_filter] if sentiment_filter != "All" else reviews
    st.caption(f"{len(filtered)} reviews")

    for _, rev in filtered.iterrows():
        badge   = SENTIMENT_BADGE.get(rev.get("sentiment"), "⚪")
        stars   = "⭐" * int(rev.get("star_rating", 0))
        title   = rev.get("review_title") or ""
        text    = rev.get("review_text")  or ""
        pain    = rev.get("pain_point")
        insight = rev.get("actionable_insight")
        cat     = rev.get("category", "")
        with st.container(border=True):
            ca, cb = st.columns([1, 4])
            with ca:
                st.markdown(f"### {badge}")
                st.caption(stars)
                st.caption(f"`{cat}`")
            with cb:
                if title:   st.markdown(f"**{title}**")
                if text:    st.markdown(text[:400] + ("..." if len(text) > 400 else ""))
                if pain:    st.error(f"🔸 **Pain point:** {pain}")
                if insight: st.info(f"💡 **Insight:** {insight}")


def _render_not_found(row: pd.Series) -> None:
    st.info("This merchant is not listed on Trustpilot.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Platform",      row.get("ecommerce_platform","—"))
    c2.metric("Helpdesk",      row.get("helpdesk") or "None")
    c3.metric("Tech Maturity", row.get("tech_maturity","—"))
    st.markdown(f"**GMV Band:** {row.get('estimated_gmv_band','—')}")
    st.markdown(f"**Signal:** {SIGNAL_LABEL.get(row.get('outreach_signal',''),'—')}")
    outreach = row.get("outreach_signal","")
    if outreach in PITCH_MAP:
        st.success(f"💬 **Pitch angle:** {PITCH_MAP[outreach]}")


def render(df_domains: pd.DataFrame, load_reviews_fn, domain_search: str = "") -> None:
    st.header("Domain Drill-down")

    domain_list = df_domains["domain"].tolist()
    if domain_search:
        domain_list = [d for d in domain_list if domain_search.lower() in d.lower()]

    if not domain_list:
        st.info("No domains match your search.")
        return

    selected = st.selectbox("Select a domain", domain_list, key="dd_select")

    row    = df_domains[df_domains["domain"] == selected].iloc[0]
    status = row.get("trustpilot_status")

    st.subheader(f"🏪 {selected}")
    st.caption(f"{row.get('ecommerce_platform','')} · {row.get('estimated_gmv_band','')}")

    if status == "found":
        _render_found(row, load_reviews_fn(selected))
    else:
        _render_not_found(row)