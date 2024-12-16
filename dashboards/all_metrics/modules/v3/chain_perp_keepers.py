from datetime import datetime, timedelta

import streamlit as st

from dashboards.utils.data import export_data
from dashboards.utils.charts import chart_bars


@st.cache_data(ttl="30m")
def fetch_data(chain, start_date, end_date, resolution):
    """
    Fetches data from the database using the API based on the provided filters.

    Args:
        chain (str): The blockchain network.
        start_date (datetime.date): The start date for data retrieval.
        end_date (datetime.date): The end date for data retrieval.
        resolution (str): The resolution for data calculations (e.g., 'daily', 'hourly').

    Returns:
        dict: A dictionary containing fetched dataframes.
    """
    api = st.session_state.api

    df_keeper = api._run_query(
        f"""
        SELECT
            ts,
            keeper as keeper_full,
            CONCAT(SUBSTRING(keeper, 1, 6), '...', SUBSTRING(keeper, length(keeper)-3, length(keeper))) as keeper,
            trades,
            trades_pct,
            amount_settled,
            amount_settled_pct,
            settlement_rewards,
            settlement_rewards_pct
        FROM {api.environment}_{chain}.fct_perp_keeper_stats_{resolution}_{chain}
        WHERE ts >= '{start_date}' and ts <= '{end_date}'
        ORDER BY ts
        """
    )

    return {
        "keeper": df_keeper,
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
    df = data["keeper"]

    return {
        "trades": chart_bars(
            df,
            x_col="ts",
            y_cols="trades",
            title="Orders Settled",
            color_by="keeper",
            y_format="#",
            unified_hover=False,
            no_decimals=True,
        ),
        "trades_pct": chart_bars(
            df,
            x_col="ts",
            y_cols="trades_pct",
            title="Orders Settled %",
            color_by="keeper",
            y_format="%",
            unified_hover=False,
        ),
        "amount_settled": chart_bars(
            df,
            x_col="ts",
            y_cols="amount_settled",
            title="Notional Size Settled",
            color_by="keeper",
            unified_hover=False,
        ),
        "amount_settled_pct": chart_bars(
            df,
            x_col="ts",
            y_cols="amount_settled_pct",
            title="Notional Size Settled %",
            color_by="keeper",
            y_format="%",
            unified_hover=False,
        ),
        "settlement_rewards": chart_bars(
            df,
            x_col="ts",
            y_cols="settlement_rewards",
            title="Settlement Rewards",
            color_by="keeper",
            unified_hover=False,
        ),
        "settlement_rewards_pct": chart_bars(
            df,
            x_col="ts",
            y_cols="settlement_rewards_pct",
            title="Settlement Rewards %",
            color_by="keeper",
            y_format="%",
            unified_hover=False,
        ),
    }


def main():
    """
    The main function that sets up the Streamlit dashboard.
    """
    st.markdown("## Perps: Keepers")

    # Initialize session state for filters if not already set
    if "resolution" not in st.session_state:
        st.session_state.resolution = "daily"
    if "start_date" not in st.session_state:
        st.session_state.start_date = datetime.today().date() - timedelta(days=14)
    if "end_date" not in st.session_state:
        st.session_state.end_date = datetime.today().date() + timedelta(days=1)

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

    # Display charts
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(charts["trades"], use_container_width=True)
        st.plotly_chart(charts["amount_settled"], use_container_width=True)
        st.plotly_chart(charts["settlement_rewards"], use_container_width=True)

    with col2:
        st.plotly_chart(charts["trades_pct"], use_container_width=True)
        st.plotly_chart(charts["amount_settled_pct"], use_container_width=True)
        st.plotly_chart(charts["settlement_rewards_pct"], use_container_width=True)

    # Export data section
    exports = [{"title": export, "df": data[export]} for export in data.keys()]
    with st.expander("Exports"):
        for export in exports:
            export_data(title=export["title"], df=export["df"])
