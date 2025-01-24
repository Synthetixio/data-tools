from datetime import datetime, timedelta

import streamlit as st

from dashboards.utils.data import export_data
from dashboards.utils.charts import chart_bars, chart_lines


@st.cache_data(ttl="30m")
def fetch_data(chain, start_date, end_date, resolution):
    """
    Fetches data from the database using the API based on the provided filters.

    Args:
        start_date (datetime.date): The start date for data retrieval.
        end_date (datetime.date): The end date for data retrieval.
        resolution (str): The resolution for APR calculations (e.g., '24h').

    Returns:
        dict: A dictionary containing fetched dataframes.
    """
    api = st.session_state.api

    # Query for account delegation data
    df_account_delegation = api._run_query(
        f"""
        SELECT 
            *
        FROM {api.environment}_{chain}.fct_core_account_delegation_{chain}
        WHERE ts >= '{start_date}' AND ts <= '{end_date}'
        """
    )

    # Query for APR data
    df_apr = api._run_query(
        f"""
        SELECT 
            ts,
            COALESCE(tk.token_symbol, collateral_type) AS collateral_type,
            collateral_value,
            debt,
            hourly_pnl,
            rewards_usd,
            hourly_issuance,
            cumulative_issuance,
            cumulative_pnl,
            apr_{resolution} + apr_{resolution}_underlying AS apr,
            apr_{resolution}_underlying as apr_underlying,
            apr_{resolution}_pnl AS apr_pnl,
            apr_{resolution}_rewards AS apr_rewards
        FROM {api.environment}_{chain}.fct_core_apr_{chain} apr
        LEFT JOIN {api.environment}_seeds.{chain}_tokens tk 
            ON LOWER(apr.collateral_type) = LOWER(tk.token_address)
        WHERE ts >= '{start_date}' AND ts <= '{end_date}'
            AND pool_id = 1
        ORDER BY ts
        """
    )

    # Query for APR token data
    df_apr_token = api._run_query(
        f"""
        SELECT 
            ts,
            COALESCE(tk.token_symbol, collateral_type) AS collateral_type,
            apr.reward_token,
            CONCAT(COALESCE(tk.token_symbol, collateral_type), ' : ', apr.reward_token) AS token_pair,
            collateral_value,
            rewards_usd,
            apr_{resolution}_rewards AS apr_rewards
        FROM {api.environment}_{chain}.fct_core_apr_rewards_{chain} apr
        LEFT JOIN {api.environment}_seeds.{chain}_tokens tk 
            ON LOWER(apr.collateral_type) = LOWER(tk.token_address)
        WHERE ts >= '{start_date}' AND ts <= '{end_date}'
            AND pool_id = 1
            AND apr.reward_token IS NOT NULL
        ORDER BY ts
        """
    )

    return {
        "account_delegation": df_account_delegation,
        "apr": df_apr,
        "apr_token": df_apr_token,
    }


@st.cache_data(ttl="30m")
def make_charts(data, resolution):
    """
    Creates charts based on the fetched data.

    Args:
        data (dict): A dictionary containing fetched dataframes.
        resolution (str): The resolution for APR calculations.

    Returns:
        dict: A dictionary containing Plotly chart objects.
    """
    native_yield_tokens = data["apr"][data["apr"]["apr_underlying"] != 0][
        "collateral_type"
    ].unique()
    return {
        "tvl": chart_lines(
            df=data["apr"],
            x_col="ts",
            y_cols="collateral_value",
            title="TVL",
            color_by="collateral_type",
            custom_agg=dict(field="collateral_value", name="Total", agg="sum"),
        ),
        "debt": chart_lines(
            df=data["apr"],
            x_col="ts",
            y_cols="debt",
            title="Debt",
            color_by="collateral_type",
            custom_agg=dict(field="debt", name="Total", agg="sum"),
        ),
        "hourly_issuance": chart_bars(
            df=data["apr"],
            x_col="ts",
            y_cols="hourly_issuance",
            title="Hourly Issuance",
            color_by="collateral_type",
            custom_agg=dict(field="hourly_issuance", name="Total", agg="sum"),
        ),
        "issuance": chart_lines(
            df=data["apr"],
            x_col="ts",
            y_cols="cumulative_issuance",
            title="Issuance",
            color_by="collateral_type",
            custom_agg=dict(field="cumulative_issuance", name="Total", agg="sum"),
        ),
        "pnl": chart_lines(
            df=data["apr"],
            x_col="ts",
            y_cols="cumulative_pnl",
            title="Pnl",
            color_by="collateral_type",
            custom_agg=dict(field="cumulative_pnl", name="Total", agg="sum"),
        ),
        "hourly_pnl": chart_bars(
            df=data["apr"],
            x_col="ts",
            y_cols="hourly_pnl",
            title="Hourly Pnl",
            color_by="collateral_type",
            custom_agg=dict(field="hourly_pnl", name="Total", agg="sum"),
        ),
        "hourly_rewards": chart_bars(
            df=data["apr"],
            x_col="ts",
            y_cols="rewards_usd",
            title="Hourly Rewards",
            color_by="collateral_type",
            custom_agg=dict(field="rewards_usd", name="Total", agg="sum"),
        ),
        "hourly_rewards_token": chart_bars(
            df=data["apr_token"],
            x_col="ts",
            y_cols="rewards_usd",
            title="Hourly Rewards (Collateral : Reward)",
            color_by="token_pair",
            custom_agg=dict(field="rewards_usd", name="Total", agg="sum"),
        ),
        "apr": chart_lines(
            df=data["apr"],
            x_col="ts",
            y_cols="apr",
            title=f"APR - {resolution} average",
            y_format="%",
            color_by="collateral_type",
            help_text="APR includes pool performance and yields from underlying Aave deposits over the specified timeframe.",
        ),
        "apr_token": chart_lines(
            df=data["apr_token"],
            x_col="ts",
            y_cols="apr_rewards",
            title=f"Reward APR by Token - {resolution} average",
            y_format="%",
            color_by="token_pair",
        ),
        "apr_underlying": chart_lines(
            df=data["apr"][data["apr"]["collateral_type"].isin(native_yield_tokens)],
            x_col="ts",
            y_cols="apr_underlying",
            title=f"Native APR by Token - {resolution} average",
            y_format="%",
            color_by="collateral_type",
        ),
    }


def main():
    """
    The main function that sets up the Streamlit dashboard.
    """
    st.markdown("## Liquidity Pools")

    # Initialize session state for filters if not already set
    if "resolution" not in st.session_state:
        st.session_state.resolution = "28d"
    if "start_date" not in st.session_state:
        st.session_state.start_date = datetime.today().date() - timedelta(days=14)
    if "end_date" not in st.session_state:
        st.session_state.end_date = datetime.today().date() + timedelta(days=1)

    # Filters section
    with st.expander("Filters"):
        # Resolution selection
        st.radio(
            "Resolution",
            options=["28d", "7d", "24h"],
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
    charts = make_charts(
        data=data,
        resolution=st.session_state.resolution,
    )

    # Display the APR chart
    st.plotly_chart(charts["apr"], use_container_width=True)

    # Create two columns for displaying multiple charts
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(charts["tvl"], use_container_width=True)
        st.plotly_chart(charts["hourly_pnl"], use_container_width=True)
        st.plotly_chart(charts["hourly_issuance"], use_container_width=True)

    with col2:
        st.plotly_chart(charts["debt"], use_container_width=True)
        st.plotly_chart(charts["pnl"], use_container_width=True)
        st.plotly_chart(charts["issuance"], use_container_width=True)

    # make these charts full width
    st.plotly_chart(charts["hourly_rewards"], use_container_width=True)
    st.plotly_chart(charts["apr_token"], use_container_width=True)
    st.plotly_chart(charts["hourly_rewards_token"], use_container_width=True)
    st.plotly_chart(charts["apr_underlying"], use_container_width=True)

    # Display Top Delegators table
    st.markdown("## Top Delegators")
    st.dataframe(
        data["account_delegation"]
        .sort_values("amount_delegated", ascending=False)
        .head(25)
        .reset_index(drop=True),
        use_container_width=True,
    )

    # Export data section
    exports = [{"title": export, "df": data[export]} for export in data.keys()]
    with st.expander("Exports"):
        for export in exports:
            export_data(title=export["title"], df=export["df"])
