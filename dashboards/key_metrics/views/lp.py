from datetime import datetime

import streamlit as st
import pandas as pd

from dashboards.utils.charts import chart_area, chart_lines
from dashboards.utils.date_utils import get_start_date
from dashboards.key_metrics.constants import SUPPORTED_CHAINS_CORE

st.markdown("# Liquidity Providers")

APR_RESOLUTION = "28d"

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

    chains_to_fetch = [*SUPPORTED_CHAINS_CORE] if chain == "all" else [chain]

    core_stats_by_collateral = [
        st.session_state.api.get_core_stats_by_collateral(
            start_date=start_date.date(),
            end_date=end_date.date(),
            chain=current_chain,
            resolution=APR_RESOLUTION,
        )
        for current_chain in chains_to_fetch
    ]
    core_account_activity_daily = [
        st.session_state.api.get_core_account_activity(
            start_date=start_date.date(),
            end_date=end_date.date(),
            chain=current_chain,
            resolution="day",
        )
        for current_chain in chains_to_fetch
    ]

    return {
        "core_stats_by_collateral": (
            pd.concat(core_stats_by_collateral, ignore_index=True)
            if core_stats_by_collateral
            else pd.DataFrame()
        ),
        "core_account_activity_daily": (
            pd.concat(core_account_activity_daily, ignore_index=True)
            .groupby(["date", "action"])
            .nof_accounts.sum()
            .reset_index()
            if core_account_activity_daily
            else pd.DataFrame()
        ),
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
        ["all", *SUPPORTED_CHAINS_CORE],
        index=0,
        format_func=lambda x: "All" if x == "all" else SUPPORTED_CHAINS_CORE[x],
        key="chain",
    )

chart_core_tvl_by_collateral = chart_area(
    data["core_stats_by_collateral"][
        ~data["core_stats_by_collateral"].label.str.contains("0x")
    ],
    x_col="ts",
    y_cols="collateral_value",
    title="TVL",
    color_by="label",
    y_format="$",
    custom_agg=dict(field="collateral_value", name="Total", agg="sum"),
)
chart_core_apr_by_collateral = chart_lines(
    data["core_stats_by_collateral"][
        ~data["core_stats_by_collateral"].label.str.contains("0x")
    ],
    x_col="ts",
    y_cols=f"apr_{APR_RESOLUTION}",
    title=f"Total APR ({APR_RESOLUTION} average)",
    color_by="label",
    y_format="%",
    sort_ascending=True,
    help_text="APR includes pool performance and yields from underlying Aave deposits over the specified timeframe.",
)
chart_core_apr_rewards_by_collateral = chart_lines(
    data["core_stats_by_collateral"][
        ~data["core_stats_by_collateral"].label.str.contains("0x")
    ],
    x_col="ts",
    y_cols=f"apr_{APR_RESOLUTION}_rewards",
    title=f"Rewards APR ({APR_RESOLUTION} average)",
    color_by="label",
    y_format="%",
    sort_ascending=True,
    help_text="Rewards APR includes the USD value of all assets distributed to a pool during the specified timeframe.",
)

st.plotly_chart(chart_core_tvl_by_collateral, use_container_width=True)

chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    st.plotly_chart(chart_core_apr_rewards_by_collateral, use_container_width=True)
with chart_col2:
    st.plotly_chart(chart_core_apr_by_collateral, use_container_width=True)
