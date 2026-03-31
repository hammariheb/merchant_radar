import streamlit as st
import pandas as pd
import plotly.express as px

SIGNAL_CONFIG = {
    "priority_lead":          {"label": "🔴 Priority Lead",          "color": "#E24B4A"},
    "warm_lead":              {"label": "🟠 Warm Lead",              "color": "#EF9F27"},
    "no_stack_prospect":      {"label": "🟣 No Stack Prospect",      "color": "#7F77DD"},
    "inbox_upgrade_prospect": {"label": "🔵 Inbox Upgrade",          "color": "#378ADD"},
    "competitor_prospect":    {"label": "🟤 Competitor Prospect",    "color": "#888780"},
    "lightweight_prospect":   {"label": "🟢 Lightweight Prospect",   "color": "#639922"},
    "low_priority":           {"label": "⚪ Low Priority",           "color": "#B4B2A9"},
    "research_needed":        {"label": "❓ Research Needed",        "color": "#D3D1C7"},
}

BASE_COLUMNS = {
    "domain":             "Domain",
    "ecommerce_platform": "Platform",
    "estimated_gmv_band": "GMV Band",
    "trustpilot_status":  "Trustpilot",
    "review_count":       "Reviews",
    "avg_rating":         "Avg Rating",
    "pct_negative":       "% Negative",
    "outreach_signal":    "Signal",
    "tech_maturity":      "Tech Maturity",
}

OPTIONAL_COLUMNS = {
    "helpdesk":                  "Helpdesk",
    "technologies_app_partners": "Tech Partners",
}


def render(df: pd.DataFrame) -> None:

    # ── KPIs ──────────────────────────────────────────────────
    total     = len(df)
    found     = len(df[df["trustpilot_status"] == "found"])
    not_found = len(df[df["trustpilot_status"] == "not_found"])
    priority  = len(df[df["outreach_signal"] == "priority_lead"])
    no_stack  = len(df[df["outreach_signal"] == "no_stack_prospect"])

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Leads",      total)
    c2.metric("Found",            found,     f"{found/total*100:.0f}%" if total else "")
    c3.metric("Not Found",        not_found, f"{not_found/total*100:.0f}%" if total else "")
    c4.metric("Priority Leads",   priority,  "avg < 3.0 ⭐")
    c5.metric("No Support Stack", no_stack,  "Priority 1")

    st.caption(f"{total} domains displayed")
    st.divider()

    # ── Signal chart ──────────────────────────────────────────
    sc = (df["outreach_signal"].value_counts().reset_index()
          .rename(columns={"outreach_signal": "signal", "count": "count"}))
    sc["label"] = sc["signal"].map(lambda x: SIGNAL_CONFIG.get(x, {}).get("label", x))
    sc["color"] = sc["signal"].map(lambda x: SIGNAL_CONFIG.get(x, {}).get("color", "#888"))
    fig = px.bar(sc, x="count", y="label", orientation="h", color="signal",
                 color_discrete_map={r["signal"]: r["color"] for _, r in sc.iterrows()},
                 title="Outreach signal distribution")
    fig.update_layout(showlegend=False, yaxis_title="", xaxis_title="Number of domains")
    st.plotly_chart(fig, width="stretch")

    st.divider()

    # ── Quick view ────────────────────────────────────────────
    st.subheader("Domain quick view")
    st.caption("Select a domain to see a summary inline")

    domain_options = ["— Select a domain —"] + df["domain"].tolist()

    selected_quick = st.selectbox(
        "Jump to domain",
        domain_options,
        index=0,
        key="overview_quick",
    )

    if selected_quick and selected_quick != "— Select a domain —":
        row    = df[df["domain"] == selected_quick].iloc[0]
        status = row.get("trustpilot_status")
        with st.container(border=True):
            ca, cb, cc = st.columns(3)
            ca.markdown(f"**Platform:** {row.get('ecommerce_platform','—')}")
            cb.markdown(f"**GMV Band:** {row.get('estimated_gmv_band','—')}")
            cc.markdown(f"**Helpdesk:** {row.get('helpdesk') or 'None'}")
            cd, ce, cf = st.columns(3)
            cd.markdown(f"**Trustpilot:** {'✅ Found' if status == 'found' else '❌ Not found'}")
            ce.markdown(f"**Tech Maturity:** {row.get('tech_maturity','—')}")
            cf.markdown(f"**Signal:** {row.get('outreach_signal','—')}")
            if status == "found":
                cg, ch, ci = st.columns(3)
                cg.metric("Avg Rating", f"{row.get('avg_rating',0):.2f} ⭐")
                ch.metric("Reviews",    int(row.get("review_count",0)))
                ci.metric("% Negative", f"{row.get('pct_negative',0):.1f}%")

    st.divider()

    # ── Full table ────────────────────────────────────────────
    st.subheader("All domains")

    selected_optional = st.multiselect("Add columns", options=list(OPTIONAL_COLUMNS.values()),
                                       default=[], placeholder="Select optional columns...")
    reverse_optional  = {v: k for k, v in OPTIONAL_COLUMNS.items()}
    selected_keys     = [reverse_optional[l] for l in selected_optional]

    ordered_keys = []
    for key in BASE_COLUMNS:
        ordered_keys.append(key)
        if key == "ecommerce_platform":
            ordered_keys.extend(selected_keys)

    all_display = {**BASE_COLUMNS, **{k: OPTIONAL_COLUMNS[k] for k in selected_keys}}
    table = df[ordered_keys].copy().rename(columns=all_display)
    table["Avg Rating"] = table["Avg Rating"].round(2)
    table["% Negative"] = table["% Negative"].round(1)

    st.dataframe(table, width="stretch", hide_index=True,
                 column_config={
                     "Avg Rating": st.column_config.NumberColumn(format="%.2f ⭐"),
                     "% Negative": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                 })