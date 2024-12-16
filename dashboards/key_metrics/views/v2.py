from datetime import datetime

import streamlit as st

from dashboards.utils.charts import chart_area, chart_bars
from dashboards.utils.date_utils import get_start_date

st.markdown("# Synthetix V2")

APR_RESOLUTION = "7d"
PERPS_RESOLUTION = "daily"

if "date_range" not in st.session_state:
    st.session_state.date_range = st.query_params.get("date_range", "30d")

st.query_params.date_range = st.session_state.date_range


@st.cache_data(ttl="30m")
def fetch_data(date_range):
    end_date = datetime.now()
    start_date = get_start_date(date_range)

    perps_stats = st.session_state.api.get_perps_v2_stats(
        start_date=start_date.date(),
        end_date=end_date.date(),
        resolution=PERPS_RESOLUTION,
    )

    open_interest = st.session_state.api.get_perps_v2_open_interest(
        start_date=start_date.date(),
        end_date=end_date.date(),
        resolution=PERPS_RESOLUTION,
    )

    return {
        "perps_stats": perps_stats,
        "open_interest": open_interest,
    }


data = fetch_data(st.session_state.date_range)

st.radio(
    "Select date range",
    ["30d", "90d", "1y", "All"],
    index=0,
    key="date_range",
)

chart_perps_volume_by_chain = chart_bars(
    data["perps_stats"],
    x_col="ts",
    y_cols="volume",
    title="Perps Volume",
    color_by="chain",
)
chart_perps_fees_by_chain = chart_bars(
    data["perps_stats"],
    x_col="ts",
    y_cols="exchange_fees",
    title="Perps Fees",
    color_by="chain",
)
chart_perps_oi_by_chain = chart_area(
    data["open_interest"],
    x_col="ts",
    y_cols="total_oi_usd",
    title="Open Interest",
    color_by="chain",
)

perps_chart_col1, perps_chart_col2 = st.columns(2)
with perps_chart_col1:
    st.plotly_chart(chart_perps_volume_by_chain, use_container_width=True)
with perps_chart_col2:
    st.plotly_chart(chart_perps_fees_by_chain, use_container_width=True)

st.plotly_chart(chart_perps_oi_by_chain, use_container_width=True)
