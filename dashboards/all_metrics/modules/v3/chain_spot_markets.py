from datetime import datetime, timedelta

import streamlit as st

from dashboards.utils.data import export_data
from dashboards.utils.charts import chart_lines


@st.cache_data(ttl="30m")
def fetch_data(chain, start_date, end_date):
    """
    Fetches data from the database using the API based on the provided filters.

    Args:
        chain (str): The blockchain network to query.
        start_date (datetime.date): The start date for data retrieval.
        end_date (datetime.date): The end date for data retrieval.

    Returns:
        dict: A dictionary containing fetched dataframes.
    """
    api = st.session_state.api

    df_wrapper = api._run_query(
        f"""
        SELECT
            ts,
            block_number,
            tx_hash,
            synth_market_id,
            amount_wrapped
        FROM {api.environment}_{chain}.fct_spot_wrapper_{chain}
        WHERE ts >= '{start_date}' AND ts <= '{end_date}'
        """
    )

    df_atomics = api._run_query(
        f"""
        SELECT
            ts,
            block_number,
            tx_hash,
            synth_market_id,
            amount,
            price
        FROM {api.environment}_{chain}.fct_spot_atomics_{chain}
        WHERE ts >= '{start_date}' AND ts <= '{end_date}'
        """
    )

    df_synth_supply = api._run_query(
        f"""
        SELECT
            ts,
            synth_market_id,
            supply
        FROM {api.environment}_{chain}.fct_synth_supply_{chain}
        WHERE ts >= '{start_date}' AND ts <= '{end_date}'
        """
    )

    return {
        "synth_supply": df_synth_supply,
        "wrapper": df_wrapper,
        "atomics": df_atomics,
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
        "supply": chart_lines(
            df=data["synth_supply"],
            x_col="ts",
            y_cols="supply",
            title="Synth Supply",
            color_by="synth_market_id",
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
    st.markdown("## Spot Markets and Wrappers")

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

    # Create charts based on fetched data
    charts = make_charts(data=data)

    # Display the Synth Supply chart
    st.plotly_chart(charts["supply"], use_container_width=True)

    # Wrapper table
    st.markdown("### Wrapper")
    st.dataframe(
        data["wrapper"].sort_values("ts", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    # Atomics table
    st.markdown("### Atomic Transactions")
    st.dataframe(
        data["atomics"].sort_values("ts", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    # Export data section
    exports = [{"title": export, "df": data[export]} for export in data.keys()]
    with st.expander("Exports"):
        for export in exports:
            export_data(title=export["title"], df=export["df"])
