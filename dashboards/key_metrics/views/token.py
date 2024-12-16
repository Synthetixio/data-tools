from datetime import datetime

import streamlit as st

from dashboards.utils.charts import chart_area, chart_bars
from dashboards.utils.date_utils import get_start_date

st.markdown("# SNX Token")

APR_RESOLUTION = "7d"

if "date_range" not in st.session_state:
    st.session_state.date_range = st.query_params.get("date_range", "30d")

st.query_params.date_range = st.session_state.date_range


@st.cache_data(ttl="30m")
def fetch_data(date_range):
    end_date = datetime.now()
    start_date = get_start_date(date_range)

    core_stats_by_collateral = st.session_state.api.get_core_stats_by_collateral(
        start_date=start_date.date(),
        end_date=end_date.date(),
        chain="eth_mainnet",
        resolution=APR_RESOLUTION,
    )

    snx_token_buyback = st.session_state.api.get_snx_token_buyback(
        start_date=start_date.date(),
        end_date=end_date.date(),
        chain="base_mainnet",
    )

    return {
        "core_stats_by_collateral": core_stats_by_collateral,
        "snx_token_buyback": snx_token_buyback,
    }


data = fetch_data(st.session_state.date_range)

st.radio(
    "Select date range",
    ["30d", "90d", "1y", "All"],
    index=0,
    key="date_range",
)

chart_core_tvl_by_collateral = chart_area(
    data["core_stats_by_collateral"],
    x_col="ts",
    y_cols="collateral_value",
    title="SNX Token TVL",
    color_by="chain",
)

chart_snx_token_buyback = chart_bars(
    data["snx_token_buyback"],
    x_col="ts",
    y_cols="usd_amount",
    title="SNX Token Buyback (Base)",
    color_by="chain",
)

col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(chart_core_tvl_by_collateral, use_container_width=True)
with col2:
    st.plotly_chart(chart_snx_token_buyback, use_container_width=True)
