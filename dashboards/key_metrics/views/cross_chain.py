from datetime import datetime, timedelta

import streamlit as st
import pandas as pd

from dashboards.utils.charts import chart_area, chart_lines, chart_bars
from dashboards.utils.date_utils import get_start_date
from dashboards.key_metrics.constants import (
    SUPPORTED_CHAINS_CORE,
    SUPPORTED_CHAINS_PERPS,
)

st.markdown("# Synthetix V3 - Overview")

APR_RESOLUTION = "7d"
PERPS_RESOLUTION = "daily"

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
        if current_chain in SUPPORTED_CHAINS_CORE
    ]
    core_stats = [
        st.session_state.api.get_core_stats(
            start_date=start_date.date(),
            end_date=end_date.date(),
            chain=current_chain,
        )
        for current_chain in chains_to_fetch
        if current_chain in SUPPORTED_CHAINS_CORE
    ]
    perps_stats = [
        st.session_state.api.get_perps_stats(
            start_date=start_date.date(),
            end_date=end_date.date(),
            chain=current_chain,
            resolution=PERPS_RESOLUTION,
        )
        for current_chain in chains_to_fetch
        if current_chain in SUPPORTED_CHAINS_PERPS
    ]
    core_account_activity_daily = [
        st.session_state.api.get_core_account_activity(
            start_date=start_date.date(),
            end_date=end_date.date(),
            chain=current_chain,
            resolution="day",
        )
        for current_chain in chains_to_fetch
        if current_chain in SUPPORTED_CHAINS_CORE
    ]
    perps_account_activity_daily = [
        st.session_state.api.get_perps_account_activity(
            start_date=start_date.date(),
            end_date=end_date.date(),
            chain=current_chain,
            resolution="day",
        )
        for current_chain in chains_to_fetch
        if current_chain in SUPPORTED_CHAINS_PERPS
    ]

    return {
        "core_stats_by_collateral": (
            pd.concat(core_stats_by_collateral, ignore_index=True)
            if core_stats_by_collateral
            else pd.DataFrame()
        ),
        "core_stats": (
            pd.concat(core_stats, ignore_index=True) if core_stats else pd.DataFrame()
        ),
        "perps_stats": (
            pd.concat(perps_stats, ignore_index=True) if perps_stats else pd.DataFrame()
        ),
        "core_account_activity_daily": (
            pd.concat(core_account_activity_daily, ignore_index=True)
            if core_account_activity_daily
            else pd.DataFrame()
        ),
        "perps_account_activity_daily": (
            pd.concat(perps_account_activity_daily, ignore_index=True)
            if perps_account_activity_daily
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

chart_core_tvl_by_chain = chart_area(
    data["core_stats"],
    x_col="ts",
    y_cols="collateral_value",
    title="TVL",
    color="chain",
)
chart_core_account_activity_daily = chart_lines(
    data["core_account_activity_daily"]
    .groupby(["date", "action"])
    .nof_accounts.sum()
    .reset_index(),
    x_col="date",
    y_cols="nof_accounts",
    title="LP Accounts Activity",
    color="action",
    y_format="#",
    help_text="Number of daily active accounts per action (Delegate, Withdraw, Claim)",
)
chart_core_tvl_by_collateral = chart_area(
    data["core_stats_by_collateral"],
    x_col="ts",
    y_cols="collateral_value",
    title="TVL by Collateral",
    color="label",
)
chart_core_apr_by_collateral = chart_lines(
    data["core_stats_by_collateral"],
    x_col="ts",
    y_cols=f"apr_{APR_RESOLUTION}",
    title="APR by Collateral (7d average)",
    color="label",
    y_format="%",
)

core_chart_col1, core_chart_col2 = st.columns(2)
with core_chart_col1:
    st.plotly_chart(chart_core_tvl_by_chain, use_container_width=True)
    st.plotly_chart(chart_core_apr_by_collateral, use_container_width=True)
with core_chart_col2:
    st.plotly_chart(chart_core_account_activity_daily, use_container_width=True)
    st.plotly_chart(chart_core_tvl_by_collateral, use_container_width=True)

if st.session_state.chain in [*SUPPORTED_CHAINS_PERPS, "all"]:
    chart_perps_volume_by_chain = chart_bars(
        data["perps_stats"],
        x_col="ts",
        y_cols="volume",
        title="Perps Volume",
        color="chain",
    )
    chart_perps_account_activity_daily = chart_bars(
        data["perps_account_activity_daily"],
        x_col="date",
        y_cols="nof_accounts",
        title="Perps Accounts Activity",
        color="chain",
        y_format="#",
        help_text="Number of daily unique accounts that have at least one settled order",
    )
    chart_perps_fees_by_chain = chart_bars(
        data["perps_stats"],
        x_col="ts",
        y_cols="exchange_fees",
        title="Perps Fees",
        color="chain",
    )

    perps_chart_col1, perps_chart_col2 = st.columns(2)
    with perps_chart_col1:
        st.plotly_chart(chart_perps_volume_by_chain, use_container_width=True)
        st.plotly_chart(chart_perps_fees_by_chain, use_container_width=True)
    with perps_chart_col2:
        st.plotly_chart(chart_perps_account_activity_daily, use_container_width=True)
