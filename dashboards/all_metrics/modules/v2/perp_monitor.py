from datetime import datetime, timedelta

import streamlit as st

from dashboards.utils.data import export_data
from dashboards.utils.charts import chart_many_bars


@st.cache_data(ttl="30m")
def fetch_data(chain, start_date, end_date, resolution):
    """
    Fetches data from the database using the API based on the provided filters.

    Args:
        chain (str): The blockchain network (e.g., 'optimism_mainnet').
        start_date (datetime.date): The start date for data retrieval.
        end_date (datetime.date): The end date for data retrieval.
        resolution (str): The resolution for data aggregation (e.g., 'hourly', 'daily').

    Returns:
        dict: A dictionary containing fetched dataframes.
    """
    api = st.session_state.api

    df_market_stats_agg = api._run_query(
        f"""
        SELECT
            ts,
            market,
            exchange_fees,
            liquidation_fees,
            volume,
            amount_liquidated,
            trades,
            liquidations,
            cumulative_volume,
            cumulative_exchange_fees,
            cumulative_liquidation_fees,
            cumulative_amount_liquidated,
            long_oi_usd,
            short_oi_usd,
            total_oi_usd
        FROM {api.environment}_{chain}.fct_v2_market_{resolution}_{chain}
        WHERE ts >= '{start_date}'
            AND ts <= '{end_date}'
        ORDER BY ts
        """
    )

    return {
        "market_stats_agg": df_market_stats_agg,
    }


@st.cache_data(ttl="30m")
def make_charts(data):
    """
    Creates charts based on the fetched data.

    Args:
        data (dict): A dictionary containing fetched dataframes.

    Returns:
        dict: A dictionary containing Plotly chart objects.
    """
    df = data["market_stats_agg"]

    return {
        "volume": chart_many_bars(
            df,
            "ts",
            ["volume"],
            "Volume",
            "market",
        ),
        "exchange_fees": chart_many_bars(
            df,
            "ts",
            ["exchange_fees"],
            "Exchange Fees",
            "market",
        ),
        "liquidation_fees": chart_many_bars(
            df,
            "ts",
            ["liquidation_fees"],
            "Liquidation Fees",
            "market",
        ),
        "amount_liquidated": chart_many_bars(
            df,
            "ts",
            ["amount_liquidated"],
            "Amount Liquidated",
            "market",
        ),
        "trades": chart_many_bars(
            df,
            "ts",
            ["trades"],
            "Trades",
            "market",
            y_format="#",
        ),
        "liquidations": chart_many_bars(
            df,
            "ts",
            ["liquidations"],
            "Liquidations",
            "market",
            y_format="#",
        ),
    }


def main():
    """
    The main function that sets up the Streamlit dashboard.
    """
    # Initialize session state for filters if not already set
    if "resolution" not in st.session_state:
        st.session_state.resolution = "hourly"
    if "start_date" not in st.session_state:
        st.session_state.start_date = datetime.today().date() - timedelta(days=3)
    if "end_date" not in st.session_state:
        st.session_state.end_date = datetime.today().date()

    st.markdown("## Perps V2: Activity Monitor")

    # Filters section
    with st.expander("Filters"):
        st.radio(
            "Resolution",
            options=["hourly", "daily"],
            index=1,
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
    charts = make_charts(data)

    # Display charts
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(charts["volume"], use_container_width=True)
        st.plotly_chart(charts["exchange_fees"], use_container_width=True)
        st.plotly_chart(charts["trades"], use_container_width=True)

    with col2:
        st.plotly_chart(charts["amount_liquidated"], use_container_width=True)
        st.plotly_chart(charts["liquidation_fees"], use_container_width=True)
        st.plotly_chart(charts["liquidations"], use_container_width=True)

    # Export data section
    exports = [{"title": export, "df": data[export]} for export in data.keys()]
    with st.expander("Exports"):
        for export in exports:
            export_data(title=export["title"], df=export["df"])
