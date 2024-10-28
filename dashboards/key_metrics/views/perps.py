from datetime import datetime

import streamlit as st
import pandas as pd

from dashboards.utils.charts import chart_bars, chart_area
from dashboards.utils.date_utils import get_start_date
from dashboards.key_metrics.constants import SUPPORTED_CHAINS_PERPS

st.markdown("# Perps")

if "chain" not in st.session_state:
    st.session_state.chain = st.query_params.get("chain", "all")
if "date_range" not in st.session_state:
    st.session_state.date_range = st.query_params.get("date_range", "30d")

st.query_params.chain = st.session_state.chain
st.query_params.date_range = st.session_state.date_range


@st.cache_data(ttl="30m")
def fetch_data(date_range, chain):
    end_date = datetime.now()
    start_date = get_start_date(date_range)

    chains_to_fetch = [*SUPPORTED_CHAINS_PERPS] if chain == "all" else [chain]

    perps_stats = [
        st.session_state.api.get_perps_stats(
            start_date=start_date.date(),
            end_date=end_date.date(),
            chain=current_chain,
            resolution="daily",
        )
        for current_chain in chains_to_fetch
        if current_chain in SUPPORTED_CHAINS_PERPS
    ]
    perps_account_activity = [
        st.session_state.api.get_perps_account_activity(
            start_date=start_date.date(),
            end_date=end_date.date(),
            chain=current_chain,
        )
        for current_chain in chains_to_fetch
        if current_chain in SUPPORTED_CHAINS_PERPS
    ]

    return {
        "perps_stats": pd.concat(perps_stats, ignore_index=True),
        "perps_account_activity": pd.concat(perps_account_activity, ignore_index=True),
    }


data = fetch_data(st.session_state.date_range, st.session_state.chain)

filter_col1, filter_col2 = st.columns(2)

with filter_col1:
    st.radio(
        "Select date range",
        ["30d", "90d", "1y", "All"],
        index=0,
        key="date_range",
    )
with filter_col2:
    st.radio(
        "Select chain",
        ["all", *SUPPORTED_CHAINS_PERPS],
        index=0,
        format_func=lambda x: "All" if x == "all" else SUPPORTED_CHAINS_PERPS[x],
        key="chain",
    )

chart_perps_volume = chart_bars(
    data["perps_stats"],
    x_col="ts",
    y_cols="volume",
    title="Perps Volume",
    color_by="chain",
    custom_agg=(
        dict(field="volume", name="Total", agg="sum")
        if st.session_state.chain == "all"
        else None
    ),
)
chart_perps_exchange_fees = chart_bars(
    data["perps_stats"],
    x_col="ts",
    y_cols="exchange_fees",
    title="Perps Fees",
    color_by="chain",
    custom_agg=(
        dict(field="exchange_fees", name="Total", agg="sum")
        if st.session_state.chain == "all"
        else None
    ),
)
chart_perps_account_activity_daily = chart_bars(
    data["perps_account_activity"],
    x_col="date",
    y_cols="dau",
    title="Active Accounts (Daily)",
    color_by="chain",
    y_format="#",
    help_text="Number of daily unique accounts that have at least one settled order",
    custom_agg=(
        dict(field="dau", name="Total", agg="sum")
        if st.session_state.chain == "all"
        else None
    ),
)
chart_perps_account_activity_monthly = chart_area(
    data["perps_account_activity"],
    x_col="date",
    y_cols="mau",
    title="Active Accounts (Monthly)",
    color_by="chain",
    y_format="#",
    help_text="Number of unique accounts that have at least one settled order in the past 28 days",
    custom_agg=(
        dict(field="mau", name="Total", agg="sum")
        if st.session_state.chain == "all"
        else None
    ),
)

chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    st.plotly_chart(chart_perps_volume, use_container_width=True)
    st.plotly_chart(chart_perps_account_activity_daily, use_container_width=True)
with chart_col2:
    st.plotly_chart(chart_perps_exchange_fees, use_container_width=True)
    st.plotly_chart(chart_perps_account_activity_monthly, use_container_width=True)
