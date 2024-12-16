from datetime import datetime, timedelta

import streamlit as st

from dashboards.utils.data import export_data
from dashboards.utils.charts import chart_lines, chart_many_bars


@st.cache_data(ttl="30m")
def fetch_data(start_date, end_date, resolution):
    """
    Fetches data from the database using the API based on the provided filters.

    Args:
        start_date (datetime.date): The start date for data retrieval.
        end_date (datetime.date): The end date for data retrieval.
        resolution (str): The resolution for data aggregation ('daily' or 'hourly').

    Returns:
        dict: A dictionary containing fetched dataframes.
    """
    api = st.session_state.api

    df_integrator_stats_agg = api._run_query(
        f"""
        SELECT
            ts,
            CASE WHEN tracking_code IN (NULL, '', '`') THEN 'No tracking code' ELSE tracking_code END AS tracking_code,
            exchange_fees,
            exchange_fees_share,
            volume,
            volume_share,
            trades,
            trades_share,
            traders,
            cumulative_exchange_fees,
            cumulative_volume,
            cumulative_trades
        FROM {api.environment}_optimism_mainnet.fct_v2_integrator_{resolution}_optimism_mainnet
        WHERE ts >= '{start_date}' AND ts <= '{end_date}'
        ORDER BY ts
        """
    )

    return {
        "integrator_stats_agg": df_integrator_stats_agg,
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
    df = data["integrator_stats_agg"]
    return {
        "volume": chart_many_bars(
            df,
            "ts",
            ["volume"],
            "Volume",
            "tracking_code",
        ),
        "volume_pct": chart_many_bars(
            df,
            "ts",
            ["volume_share"],
            "Volume %",
            "tracking_code",
            y_format="%",
        ),
        "exchange_fees": chart_many_bars(
            df,
            "ts",
            ["exchange_fees"],
            "Exchange Fees",
            "tracking_code",
        ),
        "exchange_fees_pct": chart_many_bars(
            df,
            "ts",
            ["exchange_fees_share"],
            "Exchange Fees %",
            "tracking_code",
            y_format="%",
        ),
        "trades": chart_many_bars(
            df,
            "ts",
            ["trades"],
            "Trades",
            "tracking_code",
            y_format="#",
        ),
        "trades_pct": chart_many_bars(
            df,
            "ts",
            ["trades_share"],
            "Trades %",
            "tracking_code",
            y_format="%",
        ),
        "traders": chart_many_bars(
            df,
            "ts",
            ["traders"],
            "Traders",
            "tracking_code",
            y_format="#",
        ),
        "cumulative_volume": chart_lines(
            df,
            "ts",
            "cumulative_volume",
            "Cumulative Volume",
            "tracking_code",
            unified_hover=False,
        ),
        "cumulative_exchange_fees": chart_lines(
            df,
            "ts",
            "cumulative_exchange_fees",
            "Cumulative Exchange Fees",
            "tracking_code",
            unified_hover=False,
        ),
        "cumulative_trades": chart_lines(
            df,
            "ts",
            "cumulative_trades",
            "Cumulative Trades",
            "tracking_code",
            unified_hover=False,
            y_format="#",
            no_decimals=True,
        ),
    }


def main():
    """
    The main function that sets up the Streamlit dashboard.
    """
    st.markdown("## Perps V2: Integrators")

    # Initialize session state for filters if not already set
    if "resolution" not in st.session_state:
        st.session_state.resolution = "daily"
    if "start_date" not in st.session_state:
        st.session_state.start_date = datetime.today().date() - timedelta(days=14)
    if "end_date" not in st.session_state:
        st.session_state.end_date = datetime.today().date()

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
        st.plotly_chart(charts["traders"], use_container_width=True)
        st.plotly_chart(charts["cumulative_volume"], use_container_width=True)

    with col2:
        st.plotly_chart(charts["volume_pct"], use_container_width=True)
        st.plotly_chart(charts["exchange_fees_pct"], use_container_width=True)
        st.plotly_chart(charts["trades_pct"], use_container_width=True)
        st.plotly_chart(charts["cumulative_exchange_fees"], use_container_width=True)
        st.plotly_chart(charts["cumulative_trades"], use_container_width=True)

    # Export data section
    exports = [{"title": export, "df": data[export]} for export in data.keys()]
    with st.expander("Exports"):
        for export in exports:
            export_data(title=export["title"], df=export["df"])
