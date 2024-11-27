from datetime import datetime, timedelta

import streamlit as st
import pandas as pd

from dashboards.utils.data import export_data
from dashboards.utils.charts import chart_bars, chart_lines, chart_many_bars


@st.cache_data(ttl="30m")
def fetch_data(chain, start_date, end_date, resolution):
    """
    Fetches data from the database using the API based on the provided filters.

    Args:
        chain (str): The blockchain network to query.
        start_date (datetime.date): The start date for data retrieval.
        end_date (datetime.date): The end date for data retrieval.
        resolution (str): The resolution for data aggregation ('daily' or 'hourly').

    Returns:
        dict: A dictionary containing fetched dataframes.
    """
    api = st.session_state.api

    df_order_expired = api._run_query(
        f"""
        SELECT
            block_number,
            block_timestamp,
            cast(account_id as text) as account_id,
            market_id,
            acceptable_price,
            commitment_time,
            tracking_code
        FROM {api.environment}_{chain}.fct_perp_previous_order_expired_{chain}
        WHERE date(block_timestamp) >= '{start_date}' and date(block_timestamp) <= '{end_date}'
        ORDER BY block_timestamp
        """
    )

    df_trade = api._run_query(
        f"""
        SELECT
            ts,
            account_id,
            market_symbol,
            position_size,
            trade_size,
            notional_trade_size,
            fill_price,
            total_fees,
            accrued_funding,
            tracking_code,
            transaction_hash
        FROM {api.environment}_{chain}.fct_perp_trades_{chain}
        WHERE ts >= '{start_date}' and ts <= '{end_date}'
        ORDER BY ts
        """
    )

    df_account_liq = api._run_query(
        f"""
        SELECT
            ts,
            account_id,
            total_reward
        FROM {api.environment}_{chain}.fct_perp_liq_account_{chain}
        WHERE ts >= '{start_date}' and ts <= '{end_date}'
        ORDER BY ts
        """
    )

    df_skew = api._run_query(
        f"""
        SELECT
            ts,
            market_symbol,
            skew,
            skew * price as skew_usd
        FROM {api.environment}_{chain}.fct_perp_market_history_{chain}
        WHERE ts >= '{start_date}' and ts <= '{end_date}'
        ORDER BY ts
        """
    )

    df_market = api._run_query(
        f"""
        SELECT
            ts,
            market_symbol,
            volume,
            trades,
            exchange_fees,
            liquidations
        FROM {api.environment}_{chain}.fct_perp_market_stats_{resolution}_{chain}
        WHERE ts >= '{start_date}' and ts <= '{end_date}'
        """
    )

    df_stats = api._run_query(
        f"""
        SELECT
            ts,
            liquidated_accounts,
            liquidation_rewards
        FROM {api.environment}_{chain}.fct_perp_stats_{resolution}_{chain}
        WHERE ts >= '{start_date}' and ts <= '{end_date}'
        """
    )

    current_skew = (
        df_skew.groupby("market_symbol")
        .tail(1)
        .sort_values("skew_usd", ascending=False)
    )
    current_skew["side"] = current_skew["skew"].apply(
        lambda x: "Long" if x > 0 else ("Short" if x < 0 else "Neutral")
    )

    return {
        "order_expired": df_order_expired,
        "trade": df_trade,
        "account_liq": df_account_liq,
        "market": df_market,
        "stats": df_stats,
        "skew": df_skew,
        "current_skew": current_skew,
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
        "volume": chart_bars(
            data["market"],
            "ts",
            "volume",
            "Volume",
            "market_symbol",
            unified_hover=False,
        ),
        "exchange_fees": chart_bars(
            data["market"],
            "ts",
            "exchange_fees",
            "Exchange Fees",
            "market_symbol",
            unified_hover=False,
        ),
        "trades": chart_bars(
            data["market"],
            "ts",
            "trades",
            "Trades",
            "market_symbol",
            unified_hover=False,
            y_format="#",
            no_decimals=True,
        ),
        "position_liquidations": chart_bars(
            data["market"],
            "ts",
            "liquidations",
            "Position Liquidations",
            "market_symbol",
            y_format="#",
            unified_hover=False,
            no_decimals=True,
        ),
        "account_liquidations": chart_bars(
            data["stats"],
            x_col="ts",
            y_cols="liquidated_accounts",
            title="Account Liquidations",
            y_format="#",
            no_decimals=True,
        ),
        "liquidation_rewards": chart_bars(
            data["stats"],
            x_col="ts",
            y_cols="liquidation_rewards",
            title="Liquidation Rewards",
        ),
        "skew": chart_lines(
            data["skew"],
            x_col="ts",
            y_cols="skew_usd",
            title="Market Skew",
            color_by="market_symbol",
        ),
        "current_skew": chart_many_bars(
            data["current_skew"],
            x_col="skew_usd",
            y_cols="side",
            title="Current Market Skew",
            color="market_symbol",
            x_format="$",
            y_format="#",
        ),
    }


def main():
    """
    The main function that sets up the Streamlit dashboard.
    """
    st.markdown("## Perps: Activity Monitor")

    # Initialize session state for filters if not already set
    if "resolution" not in st.session_state:
        st.session_state.resolution = "daily"
    if "start_date" not in st.session_state:
        st.session_state.start_date = datetime.today().date() - timedelta(days=14)
    if "end_date" not in st.session_state:
        st.session_state.end_date = datetime.today().date() + timedelta(days=1)

    ## inputs
    with st.expander("Filters"):
        # resolution
        st.radio(
            "Resolution",
            options=["daily", "hourly"],
            index=0,
            key="resolution",
        )

        # date filter
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

    ## fetch data
    data = fetch_data(
        chain=st.session_state.chain,
        start_date=st.session_state.start_date,
        end_date=st.session_state.end_date,
        resolution=st.session_state.resolution,
    )

    ## make the charts
    charts = make_charts(data)

    ## display
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(charts["volume"], use_container_width=True)
        st.plotly_chart(charts["exchange_fees"], use_container_width=True)
        st.plotly_chart(charts["account_liquidations"], use_container_width=True)

    with col2:
        st.plotly_chart(charts["trades"], use_container_width=True)
        st.plotly_chart(charts["position_liquidations"], use_container_width=True)
        st.plotly_chart(charts["liquidation_rewards"], use_container_width=True)

    st.plotly_chart(charts["current_skew"], use_container_width=True)
    st.plotly_chart(charts["skew"], use_container_width=True)

    # Recent trades
    st.markdown("### Recent Trades")
    st.dataframe(
        data["trade"].sort_values("ts", ascending=False).head(50),
        use_container_width=True,
        hide_index=True,
    )

    # Account liquidations table
    st.markdown("### Accounts Liquidated")
    st.dataframe(
        data["account_liq"].sort_values("ts", ascending=False).head(25),
        use_container_width=True,
        hide_index=True,
    )

    # Expired orders table
    st.markdown("### Expired Orders")
    st.dataframe(
        data["order_expired"].sort_values("block_timestamp", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    ## export
    exports = [{"title": export, "df": data[export]} for export in data.keys()]
    with st.expander("Exports"):
        for export in exports:
            export_data(title=export["title"], df=export["df"])
