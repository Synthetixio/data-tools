from datetime import datetime, timedelta

import streamlit as st
import pandas as pd

from dashboards.utils.charts import chart_area, chart_lines, chart_bars
from dashboards.utils.date_utils import get_start_date
from dashboards.dash_key_metrics.constants import SUPPORTED_CHAINS_CORE

st.markdown("# Liquidity Providers")

APR_RESOLUTION = "7d"

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

    chains_to_fetch = [*SUPPORTED_CHAINS_CORE] if chain == "All" else [chain]

    core_stats_by_collateral = [
        st.session_state.api.get_core_stats_by_collateral(
            start_date=start_date.date(),
            end_date=end_date.date(),
            chain=current_chain,
            resolution=APR_RESOLUTION,
        )
        for current_chain in chains_to_fetch
    ]

    return {
        "core_stats_by_collateral": (
            pd.concat(core_stats_by_collateral, ignore_index=True)
            if core_stats_by_collateral
            else pd.DataFrame()
        ),
    }


data = fetch_data(st.session_state.date_range, st.session_state.chain)

filter_col1, filter_col2 = st.columns(2)

with filter_col1:
    st.radio(
        "Select date range",
        ["30d", "90d", "1y", "all"],
        index=0,
        key="date_range",
    )
with filter_col2:
    st.radio(
        "Select chain",
        ["All", *SUPPORTED_CHAINS_CORE],
        index=0,
        format_func=lambda x: "All" if x == "All" else SUPPORTED_CHAINS_CORE[x],
        key="chain",
    )

chart_core_tvl_by_collateral = chart_area(
    data["core_stats_by_collateral"],
    x_col="ts",
    y_cols="collateral_value",
    title="TVL",
    color="label",
)
chart_core_apr_by_collateral = chart_lines(
    data["core_stats_by_collateral"],
    x_col="ts",
    y_cols=f"apr_{APR_RESOLUTION}",
    title=f"APR ({APR_RESOLUTION} average)",
    color="label",
)
chart_core_apr_rewards_by_collateral = chart_lines(
    data["core_stats_by_collateral"],
    x_col="ts",
    y_cols=f"apr_{APR_RESOLUTION}_rewards",
    title=f"APR (Rewards {APR_RESOLUTION} average)",
    color="label",
)
chart_core_debt_by_collateral = chart_area(
    data["core_stats_by_collateral"],
    x_col="ts",
    y_cols="debt",
    title="Debt",
    color="label",
)
chart_core_rewards_usd_by_collateral = chart_bars(
    data["core_stats_by_collateral"],
    x_col="ts",
    y_cols="rewards_usd",
    title="Rewards (USD)",
    color="label",
)


st.plotly_chart(chart_core_tvl_by_collateral, use_container_width=True)
chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    st.plotly_chart(chart_core_apr_by_collateral, use_container_width=True)
    st.plotly_chart(chart_core_debt_by_collateral, use_container_width=True)
with chart_col2:
    st.plotly_chart(chart_core_apr_rewards_by_collateral, use_container_width=True)
    st.plotly_chart(chart_core_rewards_usd_by_collateral, use_container_width=True)
