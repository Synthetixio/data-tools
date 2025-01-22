from datetime import datetime, timedelta

import streamlit as st

from dashboards.utils.data import export_data
from dashboards.utils.charts import chart_bars, chart_lines


@st.cache_data(ttl="30m")
def fetch_data(chain, start_date, end_date, resolution):
    """
    Fetches data from the database using the API based on the provided filters.

    Args:
        chain (str): The blockchain chain to query.
        start_date (datetime.date): The start date for data retrieval.
        end_date (datetime.date): The end date for data retrieval.
        resolution (str): The resolution for data aggregation (e.g., 'daily', 'hourly').

    Returns:
        dict: A dictionary containing fetched dataframes.
    """
    api = st.session_state.api

    df_market_stats_agg = api._run_query(
        f"""
        SELECT
            ts,
            exchange_fees,
            liquidation_fees,
            exchange_fees + liquidation_fees as total_fees,
            volume,
            amount_liquidated,
            cumulative_volume,
            cumulative_exchange_fees,
            cumulative_liquidation_fees,
            cumulative_exchange_fees + cumulative_liquidation_fees as cumulative_total_fees,
            cumulative_amount_liquidated,
            long_oi_usd,
            short_oi_usd,
            total_oi_usd,
            eth_btc_oi_usd,
            alt_oi_usd
        FROM {api.environment}_{chain}.fct_v2_stats_{resolution}_{chain}
        WHERE ts >= '{start_date}' AND ts <= '{end_date}'
        ORDER BY ts
        """
    )

    return {
        "market_stats_agg": df_market_stats_agg,
    }


@st.cache_data(ttl="30m")
def make_charts(data, resolution):
    """
    Creates charts based on the fetched data.

    Args:
        data (dict): A dictionary containing fetched dataframes.
        resolution (str): The resolution for data aggregation.

    Returns:
        dict: A dictionary containing Plotly chart objects.
    """
    return {
        "cumulative_volume": chart_lines(
            data["market_stats_agg"],
            "ts",
            ["cumulative_volume"],
            "Cumulative Volume",
            smooth=True,
        ),
        "daily_volume": chart_bars(
            data["market_stats_agg"],
            "ts",
            ["volume"],
            f"{resolution.capitalize()} Volume",
        ),
        "cumulative_fees": chart_lines(
            data["market_stats_agg"],
            "ts",
            ["cumulative_exchange_fees", "cumulative_liquidation_fees"],
            "Cumulative Fees",
            smooth=True,
            custom_agg=dict(field="cumulative_total_fees", name="Total", agg="sum"),
        ),
        "daily_fees": chart_bars(
            data["market_stats_agg"],
            "ts",
            ["exchange_fees", "liquidation_fees"],
            f"{resolution.capitalize()} Fees",
            custom_agg=dict(field="total_fees", name="Total", agg="sum"),
        ),
        "cumulative_liquidation": chart_lines(
            data["market_stats_agg"],
            "ts",
            ["cumulative_amount_liquidated"],
            "Cumulative Amount Liquidated",
            smooth=True,
        ),
        "daily_liquidation": chart_bars(
            data["market_stats_agg"],
            "ts",
            ["amount_liquidated"],
            f"{resolution.capitalize()} Amount Liquidated",
        ),
        "oi_usd": chart_lines(
            data["market_stats_agg"],
            "ts",
            ["total_oi_usd", "eth_btc_oi_usd", "alt_oi_usd"],
            "Open Interest (USD)",
            smooth=True,
        ),
    }


def main():
    """
    The main function that sets up the Streamlit dashboard.
    """
    # Initialize session state for filters if not already set
    if "resolution" not in st.session_state:
        st.session_state.resolution = "daily"
    if "start_date" not in st.session_state:
        st.session_state.start_date = datetime.today().date() - timedelta(days=30)
    if "end_date" not in st.session_state:
        st.session_state.end_date = datetime.today().date()

    st.markdown("## Perps V2")

    # Filters section
    with st.expander("Filters"):
        # Resolution selection
        st.radio(
            "Resolution",
            options=["daily", "hourly"],
            index=0,
            key="resolution",
        )

        # Date range selection
        filt_col1, filt_col2 = st.columns(2)
        with filt_col1:
            st.date_input(
                "Start Date",
                key="start_date",
                value=st.session_state.start_date,
            )

        with filt_col2:
            st.date_input(
                "End Date",
                key="end_date",
                value=st.session_state.end_date,
            )

    # Fetch data based on filters
    data = fetch_data(
        chain=st.session_state.chain,
        start_date=st.session_state.start_date,
        end_date=st.session_state.end_date,
        resolution=st.session_state.resolution,
    )

    # Create charts based on fetched data
    charts = make_charts(
        data=data,
        resolution=st.session_state.resolution,
    )

    # Display charts
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(charts["daily_volume"], use_container_width=True)
        st.plotly_chart(charts["oi_usd"], use_container_width=True)
        st.plotly_chart(charts["cumulative_volume"], use_container_width=True)
        st.plotly_chart(charts["cumulative_liquidation"], use_container_width=True)

    with col2:
        st.plotly_chart(charts["daily_fees"], use_container_width=True)
        st.plotly_chart(charts["daily_liquidation"], use_container_width=True)
        st.plotly_chart(charts["cumulative_fees"], use_container_width=True)

    # Export data section
    exports = [{"title": export, "df": data[export]} for export in data.keys()]
    with st.expander("Exports"):
        for export in exports:
            export_data(title=export["title"], df=export["df"])
