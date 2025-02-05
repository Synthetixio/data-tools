from datetime import datetime, timedelta

import streamlit as st

from dashboards.utils.data import export_data
from dashboards.utils.charts import chart_lines, chart_bars, chart_oi


@st.cache_data(ttl="30m")
def fetch_data(chain, start_date, end_date):
    """
    Fetches data from the database using the API based on the provided filters.

    Args:
        chain (str): The blockchain network.
        start_date (datetime.date): The start date for data retrieval.
        end_date (datetime.date): The end date for data retrieval.

    Returns:
        dict: A dictionary containing fetched dataframes.
    """
    api = st.session_state.api

    # Query for market history data
    df_market_history = api._run_query(
        f"""
        SELECT
            ts,
            market_id,
            market_symbol,
            funding_rate,
            interest_rate,
            funding_rate_apr,
            long_rate_apr,
            short_rate_apr,
            price,
            skew,
            market_oi_usd,
            short_oi_pct,
            long_oi_pct
        FROM {api.environment}_{chain}.fct_perp_market_history_{chain}
        WHERE ts >= '{start_date}' AND ts <= '{end_date}'
        ORDER BY ts
        """
    )

    # Query for market stats data
    df_stats = api._run_query(
        f"""
        SELECT
            ts,
            market_symbol,
            volume,
            trades,
            exchange_fees,
            liquidations
        FROM {api.environment}_{chain}.fct_perp_market_stats_daily_{chain}
        WHERE ts >= '{start_date}' AND ts <= '{end_date}'
        """
    )

    return {
        "market_history": df_market_history,
        "stats": df_stats,
    }


@st.cache_data(ttl="30m")
def make_charts(data, asset):
    """
    Creates charts based on the fetched data for a specific asset.

    Args:
        data (dict): A dictionary containing fetched dataframes.
        asset (str): The selected asset symbol.

    Returns:
        dict: A dictionary containing Plotly chart objects.
    """
    df_market = data["market_history"][data["market_history"]["market_symbol"] == asset]
    df_stats = data["stats"][data["stats"]["market_symbol"] == asset]

    return {
        "rates": chart_lines(
            df_market,
            x_col="ts",
            y_cols=[
                "funding_rate_apr",
                "interest_rate",
                "long_rate_apr",
                "short_rate_apr",
            ],
            title="Rates",
            smooth=True,
            y_format="%",
        ),
        "price": chart_lines(
            df_market,
            x_col="ts",
            y_cols="price",
            title="Price",
            smooth=True,
        ),
        "volume": chart_bars(
            df_stats,
            x_col="ts",
            y_cols="volume",
            title="Volume",
        ),
        "exchange_fees": chart_bars(
            df_stats,
            x_col="ts",
            y_cols="exchange_fees",
            title="Exchange Fees",
        ),
        "skew": chart_lines(
            df_market,
            x_col="ts",
            y_cols="skew",
            title="Market Skew",
            y_format="#",
        ),
        "oi": chart_lines(
            df_market,
            x_col="ts",
            y_cols="market_oi_usd",
            title="Market Open Interest",
        ),
        "oi_pct": chart_oi(
            df_market,
            x_col="ts",
            title="Open Interest: Long vs Short",
        ),
    }


def main():
    """
    The main function that sets up the Streamlit dashboard.
    """
    # Initialize session state for filters if not already set
    if "start_date" not in st.session_state:
        st.session_state.start_date = datetime.today().date() - timedelta(days=14)
    if "end_date" not in st.session_state:
        st.session_state.end_date = datetime.today().date() + timedelta(days=1)

    # Title
    st.markdown("## Perps: Market Overview")

    # Filters section
    with st.expander("Filters"):
        # Date range selection
        filt_col1, filt_col2 = st.columns(2)
        with filt_col1:
            st.date_input(
                "Start Date",
                key="start_date",
                value=st.session_state.start_date,
                min_value=datetime(2000, 1, 1),
                max_value=datetime.today().date(),
            )

        with filt_col2:
            st.date_input(
                "End Date",
                key="end_date",
                value=st.session_state.end_date,
                min_value=st.session_state.start_date,
                max_value=datetime.today().date() + timedelta(days=30),
            )

    # Fetch data based on filters
    data = fetch_data(
        chain=st.session_state.chain,
        start_date=st.session_state.start_date,
        end_date=st.session_state.end_date,
    )

    # Market filter
    assets = sorted(
        data["market_history"]["market_symbol"].unique(),
        key=lambda x: (x != "ETH", x != "BTC", x),
    )
    asset = st.selectbox("Select asset", assets, index=0)

    # Create charts based on fetched data and selected asset
    charts = make_charts(data, asset)

    # Display the price chart
    st.plotly_chart(charts["price"], use_container_width=True)

    # Create two columns for displaying multiple charts
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(charts["volume"], use_container_width=True)
        st.plotly_chart(charts["oi"], use_container_width=True)
        st.plotly_chart(charts["skew"], use_container_width=True)

    with col2:
        st.plotly_chart(charts["exchange_fees"], use_container_width=True)
        st.plotly_chart(charts["oi_pct"], use_container_width=True)
        st.plotly_chart(charts["rates"], use_container_width=True)

    # Export data section
    exports = [{"title": export, "df": data[export]} for export in data.keys()]
    with st.expander("Exports"):
        for export in exports:
            export_data(title=export["title"], df=export["df"])
