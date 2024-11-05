from datetime import datetime, timedelta

import streamlit as st
import pandas as pd

from dashboards.utils.data import export_data
from dashboards.utils.charts import chart_bars, chart_lines


@st.cache_data(ttl="30m")
def fetch_data(chain, start_date, end_date, resolution):
    api = st.session_state.api

    df_stats = api._run_query(
        f"""
        SELECT
            ts,
            volume,
            trades,
            exchange_fees,
            liquidated_accounts,
            liquidation_rewards,
            cumulative_exchange_fees,
            cumulative_volume            
        FROM {api.environment}_{chain}.fct_perp_stats_{resolution}_{chain}
        WHERE ts >= '{start_date}' and ts <= '{end_date}'
        """
    )

    df_oi = api._run_query(
        f"""
        SELECT
            ts,
            total_oi_usd
        FROM {api.environment}_{chain}.fct_perp_market_history_{chain}
        WHERE ts >= '{start_date}' and ts <= '{end_date}'
        ORDER BY ts
        """
    )

    df_buyback = (
        api._run_query(
            f"""
        SELECT
            ts,
            snx_amount,
            usd_amount,
            cumulative_snx_amount,
            cumulative_usd_amount
        FROM {api.environment}_{chain}.fct_buyback_{resolution}_{chain}
        WHERE ts >= '{start_date}' and ts <= '{end_date}'
        """
        )
        if st.session_state.chain.startswith("base")
        else pd.DataFrame()
    )

    df_collateral = (
        api._run_query(
            f"""
        SELECT
            ts,
            synth_symbol,
            total_balance,
            total_balance_usd
        FROM {api.environment}_{chain}.fct_perp_collateral_balances_{chain}
        WHERE ts >= '{start_date}' and ts <= '{end_date}'
        """
        )
        if st.session_state.chain.startswith("arbitrum")
        else pd.DataFrame()
    )

    return {
        "stats": df_stats,
        "oi": df_oi,
        "buyback": df_buyback,
        "collateral": df_collateral,
    }


@st.cache_data(ttl="30m")
def make_charts(data):
    return {
        "volume": chart_bars(
            data["stats"],
            x_col="ts",
            y_cols="volume",
            title="Volume",
        ),
        "cumulative_volume": chart_lines(
            data["stats"],
            x_col="ts",
            y_cols="cumulative_volume",
            title="Cumulative Volume",
            smooth=True,
        ),
        "cumulative_fees": chart_lines(
            data["stats"],
            x_col="ts",
            y_cols="cumulative_exchange_fees",
            title="Cumulative Fees",
            smooth=True,
        ),
        "fees": chart_bars(
            data["stats"],
            x_col="ts",
            y_cols="exchange_fees",
            title="Exchange Fees",
        ),
        "trades": chart_bars(
            data["stats"],
            x_col="ts",
            y_cols="trades",
            title="Trades",
            y_format="#",
        ),
        "oi": chart_lines(
            data["oi"],
            x_col="ts",
            y_cols="total_oi_usd",
            title="Open Interest",
            y_format="$",
            smooth=True,
        ),
        "account_liquidations": chart_bars(
            data["stats"],
            x_col="ts",
            y_cols="liquidated_accounts",
            title="Account Liquidations",
            y_format="#",
        ),
        "liquidation_rewards": chart_bars(
            data["stats"],
            x_col="ts",
            y_cols="liquidation_rewards",
            title="Liquidation Rewards",
        ),
        "collateral": (
            chart_lines(
                data["collateral"],
                x_col="ts",
                y_cols="total_balance_usd",
                y_format="$",
                color_by="synth_symbol",
                title="Collateral Balances",
            )
            if st.session_state.chain.startswith("arbitrum")
            else None
        ),
        "buyback": (
            chart_bars(
                data["buyback"],
                x_col="ts",
                y_cols="snx_amount",
                title="SNX Buyback",
                y_format="#",
            )
            if st.session_state.chain.startswith("base")
            else None
        ),
        "cumulative_buyback": (
            chart_lines(
                data["buyback"],
                x_col="ts",
                y_cols="cumulative_snx_amount",
                title="Cumulative SNX Buyback",
                y_format="#",
                smooth=True,
            )
            if st.session_state.chain.startswith("base")
            else None
        ),
    }


def main():
    st.markdown(f"## Perps")

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
        st.plotly_chart(charts["oi"], use_container_width=True)
        st.plotly_chart(charts["account_liquidations"], use_container_width=True)
        st.plotly_chart(charts["cumulative_volume"], use_container_width=True)

    with col2:
        st.plotly_chart(charts["fees"], use_container_width=True)
        st.plotly_chart(charts["trades"], use_container_width=True)
        st.plotly_chart(charts["liquidation_rewards"], use_container_width=True)
        st.plotly_chart(charts["cumulative_fees"], use_container_width=True)

    if st.session_state.chain.startswith("arbitrum"):
        st.plotly_chart(charts["collateral"], use_container_width=True)

    if st.session_state.chain.startswith("base"):
        bb_col1, bb_col2 = st.columns(2)
        with bb_col1:
            st.plotly_chart(charts["cumulative_buyback"], use_container_width=True)

        with bb_col2:
            st.plotly_chart(charts["buyback"], use_container_width=True)

    ## export
    exports = [{"title": export, "df": data[export]} for export in data.keys()]
    with st.expander("Exports"):
        for export in exports:
            export_data(title=export["title"], df=export["df"])
