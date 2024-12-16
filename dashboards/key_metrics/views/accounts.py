from datetime import datetime

import streamlit as st
import pandas as pd

from dashboards.utils.charts import chart_bars, chart_lines, chart_area
from dashboards.utils.date_utils import get_start_date
from dashboards.key_metrics.constants import (
    SUPPORTED_CHAINS_CORE,
    SUPPORTED_CHAINS_PERPS,
)

st.markdown("# Accounts Activity")

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
    core_account_activity_monthly = [
        st.session_state.api.get_core_account_activity(
            start_date=start_date.date(),
            end_date=end_date.date(),
            chain=current_chain,
            resolution="month",
        )
        for current_chain in chains_to_fetch
        if current_chain in SUPPORTED_CHAINS_CORE
    ]
    core_nof_stakers = [
        st.session_state.api.get_core_nof_stakers(
            start_date=start_date.date(),
            end_date=end_date.date(),
            chain=current_chain,
        )
        for current_chain in chains_to_fetch
        if current_chain in SUPPORTED_CHAINS_CORE
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
        "core_account_activity_daily": (
            pd.concat(core_account_activity_daily, ignore_index=True)
            .groupby(["date", "action"])
            .nof_accounts.sum()
            .reset_index()
            if core_account_activity_daily
            else pd.DataFrame()
        ),
        "core_account_activity_monthly": (
            pd.concat(core_account_activity_monthly, ignore_index=True)
            .groupby(["date", "action"])
            .nof_accounts.sum()
            .reset_index()
            if core_account_activity_monthly
            else pd.DataFrame()
        ),
        "core_nof_stakers": (
            pd.concat(core_nof_stakers, ignore_index=True)
            if core_nof_stakers
            else pd.DataFrame()
        ),
        "perps_account_activity": (
            pd.concat(perps_account_activity, ignore_index=True)
            if perps_account_activity
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

chart_core_account_activity_daily = chart_lines(
    data["core_account_activity_daily"],
    x_col="date",
    y_cols="nof_accounts",
    title="Accounts Activity (Daily)",
    color="action",
    y_format="#",
    help_text="Number of daily active accounts per action (Delegate, Withdraw, Claim)",
    no_decimals=True,
)
chart_core_account_activity_monthly = chart_bars(
    data["core_account_activity_monthly"],
    x_col="date",
    y_cols="nof_accounts",
    title="Accounts Activity (Monthly)",
    color="action",
    y_format="#",
    barmode="group",
    help_text="Number of monthly active accounts per action (Delegate, Withdraw, Claim)",
    no_decimals=True,
)
chart_core_nof_stakers = chart_bars(
    data["core_nof_stakers"],
    x_col="ts",
    y_cols="nof_stakers",
    title="Number of Stakers",
    color="chain",
    y_format="#",
    help_text="Number of unique accounts that have at least one staked position",
    no_decimals=True,
)


st.markdown("## Liquidity Providers")
lp_chart_col1, lp_chart_col2 = st.columns(2)
with lp_chart_col1:
    st.plotly_chart(chart_core_account_activity_daily, use_container_width=True)
    st.plotly_chart(chart_core_nof_stakers, use_container_width=True)
with lp_chart_col2:
    st.plotly_chart(chart_core_account_activity_monthly, use_container_width=True)

if st.session_state.chain in [*SUPPORTED_CHAINS_PERPS, "all"]:
    st.markdown("## Perps")
    chart_perps_account_activity_daily = chart_bars(
        data["perps_account_activity"],
        x_col="date",
        y_cols="dau",
        title="Accounts Activity (Daily)",
        color="chain",
        y_format="#",
        help_text="Number of daily unique accounts that have at least one settled order",
        no_decimals=True,
    )
    chart_perps_account_activity_monthly = chart_area(
        data["perps_account_activity"],
        x_col="date",
        y_cols="mau",
        title="Accounts Activity (Monthly)",
        color="chain",
        y_format="#",
        help_text="Number of monthly unique accounts that have at least one settled order",
        no_decimals=True,
    )

    perps_chart_col1, perps_chart_col2 = st.columns(2)
    with perps_chart_col1:
        st.plotly_chart(chart_perps_account_activity_daily, use_container_width=True)
    with perps_chart_col2:
        st.plotly_chart(chart_perps_account_activity_monthly, use_container_width=True)
