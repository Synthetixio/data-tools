from datetime import datetime

import streamlit as st
import pandas as pd

from dashboards.utils.charts import chart_bars, chart_lines, chart_oi
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
    perps_account_activity_monthly = [
        st.session_state.api.get_perps_account_activity(
            start_date=start_date.date(),
            end_date=end_date.date(),
            chain=current_chain,
            resolution="month",
        )
        for current_chain in chains_to_fetch
        if current_chain in SUPPORTED_CHAINS_PERPS
    ]

    return {
        "perps_stats": pd.concat(perps_stats, ignore_index=True),
        "perps_account_activity_daily": (
            pd.concat(perps_account_activity_daily, ignore_index=True)
            if perps_account_activity_daily
            else pd.DataFrame()
        ),
        "perps_account_activity_monthly": (
            pd.concat(perps_account_activity_monthly, ignore_index=True)
            if perps_account_activity_monthly
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
        ["all", *SUPPORTED_CHAINS_PERPS],
        index=0,
        format_func=lambda x: "All" if x == "all" else SUPPORTED_CHAINS_PERPS[x],
        key="chain",
    )

chart_perps_volume = chart_bars(
    data["perps_stats"],
    x_col="ts",
    y_cols="volume",
    title="Volume",
    color="chain",
)
chart_perps_exchange_fees = chart_bars(
    data["perps_stats"],
    x_col="ts",
    y_cols="exchange_fees",
    title="Exchange Fees",
    color="chain",
)
chart_perps_account_activity_daily = chart_bars(
    data["perps_account_activity_daily"],
    x_col="date",
    y_cols="nof_accounts",
    title="Accounts Activity (Daily)",
    color="chain",
    y_format="#",
    help_text="Number of daily unique accounts that have at least one settled order",
)
chart_perps_account_activity_monthly = chart_bars(
    data["perps_account_activity_monthly"],
    x_col="date",
    y_cols="nof_accounts",
    title="Accounts Activity (Monthly)",
    color="chain",
    y_format="#",
    help_text="Number of monthly unique accounts that have at least one settled order",
)

chart_col1, chart_col2 = st.columns(2)
with chart_col1:
    st.plotly_chart(chart_perps_volume, use_container_width=True)
    st.plotly_chart(chart_perps_account_activity_daily, use_container_width=True)
with chart_col2:
    st.plotly_chart(chart_perps_exchange_fees, use_container_width=True)
    st.plotly_chart(chart_perps_account_activity_monthly, use_container_width=True)
