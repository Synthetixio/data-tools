from datetime import datetime, timedelta

import streamlit as st

from dashboards.utils.data import export_data
from dashboards.utils.charts import chart_bars


@st.cache_data(ttl="30m")
def fetch_data(chain, start_date, end_date, resolution):
    """
    Fetches data from the database using the API based on the provided filters.

    Args:
        chain (str): The blockchain network (e.g., 'base_mainnet').
        start_date (datetime.date): The start date for data retrieval.
        end_date (datetime.date): The end date for data retrieval.
        resolution (str): The resolution for data retrieval (e.g., 'daily', 'hourly').

    Returns:
        dict: A dictionary containing fetched dataframes.
    """
    api = st.session_state.api

    # Query for stats data
    df_stats = api._run_query(
        f"""
        SELECT
            ts,
            CASE
                WHEN tracking_code = '' then 'No tracking code'
                ELSE COALESCE(tracking_code, 'No tracking code')
            END AS tracking_code,
            accounts,
            volume,
            volume_share,
            trades,
            trades_share,
            exchange_fees,
            exchange_fees_share,
            referral_fees,
            referral_fees_share
        FROM {api.environment}_{chain}.fct_perp_tracking_stats_{resolution}_{chain}
        WHERE ts >= '{start_date}' AND ts <= '{end_date}'
        """
    )

    return {
        "stats": df_stats,
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
    return {
        "accounts": chart_bars(
            df=data["stats"],
            x_col="ts",
            y_cols="accounts",
            title="Accounts",
            color_by="tracking_code",
            y_format="#",
            no_decimals=True,
        ),
        "volume": chart_bars(
            df=data["stats"],
            x_col="ts",
            y_cols="volume",
            title="Volume",
            color_by="tracking_code",
        ),
        "volume_pct": chart_bars(
            df=data["stats"],
            x_col="ts",
            y_cols="volume_share",
            title="Volume %",
            color_by="tracking_code",
            y_format="%",
        ),
        "trades": chart_bars(
            df=data["stats"],
            x_col="ts",
            y_cols="trades",
            title="Trades",
            color_by="tracking_code",
            y_format="#",
            no_decimals=True,
        ),
        "trades_pct": chart_bars(
            df=data["stats"],
            x_col="ts",
            y_cols="trades_share",
            title="Trades %",
            color_by="tracking_code",
            y_format="%",
        ),
        "exchange_fees": chart_bars(
            df=data["stats"],
            x_col="ts",
            y_cols="exchange_fees",
            title="Exchange Fees",
            color_by="tracking_code",
        ),
        "exchange_fees_pct": chart_bars(
            df=data["stats"],
            x_col="ts",
            y_cols="exchange_fees_share",
            title="Exchange Fees %",
            color_by="tracking_code",
            y_format="%",
        ),
        "referral_fees": chart_bars(
            df=data["stats"],
            x_col="ts",
            y_cols="referral_fees",
            title="Referral Fees",
            color_by="tracking_code",
        ),
        "referral_fees_pct": chart_bars(
            df=data["stats"],
            x_col="ts",
            y_cols="referral_fees_share",
            title="Referral Fees %",
            color_by="tracking_code",
            y_format="%",
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
        st.session_state.start_date = datetime.today().date() - timedelta(days=14)
    if "end_date" not in st.session_state:
        st.session_state.end_date = datetime.today().date() + timedelta(days=1)
    if "chain" not in st.session_state:
        st.session_state.chain = (
            "base_mainnet"  # Set a default chain or retrieve dynamically
        )

    # Title
    st.markdown("## Perps: Integrators")

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
        resolution=st.session_state.resolution,
    )

    # Create charts based on fetched data
    charts = make_charts(data)

    # Display charts in two columns
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(charts["volume"], use_container_width=True)
        st.plotly_chart(charts["trades"], use_container_width=True)
        st.plotly_chart(charts["exchange_fees"], use_container_width=True)
        st.plotly_chart(charts["referral_fees"], use_container_width=True)
        st.plotly_chart(charts["accounts"], use_container_width=True)

    with col2:
        st.plotly_chart(charts["volume_pct"], use_container_width=True)
        st.plotly_chart(charts["trades_pct"], use_container_width=True)
        st.plotly_chart(charts["exchange_fees_pct"], use_container_width=True)
        st.plotly_chart(charts["referral_fees_pct"], use_container_width=True)

    # Export data section
    exports = [{"title": export, "df": data[export]} for export in data.keys()]
    with st.expander("Exports"):
        for export in exports:
            export_data(title=export["title"], df=export["df"])
