from datetime import datetime, timedelta

import streamlit as st
import pandas as pd

from dashboards.utils.data import export_data
from dashboards.utils.charts import chart_bars, chart_lines


@st.cache_data(ttl="30m")
def fetch_data(chain, account_id, start_date, end_date):
    """
    Fetches data from the database using the API based on the provided filters.

    Args:
        chain (str): The blockchain chain name.
        account_id (str): The account ID.
        start_date (datetime.date): The start date for data retrieval.
        end_date (datetime.date): The end date for data retrieval.

    Returns:
        dict: A dictionary containing fetched dataframes.
    """
    api = st.session_state.api

    # Query for accounts
    df_accounts = api._run_query(
        f"""
        SELECT DISTINCT account_id, sender FROM {api.environment}_{chain}.fct_perp_orders_{chain}
        """
    )

    # Query for expired orders
    df_order_expired = api._run_query(
        f"""
        SELECT
            block_timestamp,
            CAST(account_id AS TEXT) AS account_id,
            market_id,
            acceptable_price,
            commitment_time
        FROM {api.environment}_{chain}.fct_perp_previous_order_expired_{chain}
        WHERE account_id = {account_id if account_id else 'NULL'}
            AND DATE(block_timestamp) >= '{start_date}' AND DATE(block_timestamp) <= '{end_date}'
        """
    )

    # Query for trades
    df_trade = api._run_query(
        f"""
        SELECT
            ts,
            CAST(account_id AS TEXT) AS account_id,
            market_id,
            market_symbol,
            position_size,
            notional_position_size,
            trade_size,
            notional_trade_size,
            fill_price,
            total_fees,
            accrued_funding,
            tracking_code,
            transaction_hash
        FROM {api.environment}_{chain}.fct_perp_trades_{chain}
        WHERE account_id = '{account_id}'
            AND ts >= '{start_date}' AND ts <= '{end_date}'
        """
    )

    # Query for transfers
    df_transfer = api._run_query(
        f"""
        SELECT
            block_timestamp,
            CAST(account_id AS TEXT) AS account_id,
            synth_symbol,
            amount_delta
        FROM {api.environment}_{chain}.fct_perp_collateral_modified_{chain}
        WHERE account_id = {account_id if account_id else 'NULL'}
            AND DATE(block_timestamp) >= '{start_date}' AND DATE(block_timestamp) <= '{end_date}'
        """
    )

    # Query for interest
    df_interest = api._run_query(
        f"""
        SELECT
            block_timestamp,
            transaction_hash,
            CAST(account_id AS TEXT) AS account_id,
            interest
        FROM {api.environment}_{chain}.fct_perp_interest_charged_{chain}
        WHERE account_id = {account_id if account_id else 'NULL'}
            AND DATE(block_timestamp) >= '{start_date}' AND DATE(block_timestamp) <= '{end_date}'
        """
    )

    # Query for account liquidations
    df_account_liq = api._run_query(
        f"""
        SELECT
            ts,
            account_id,
            total_reward
        FROM {api.environment}_{chain}.fct_perp_liq_account_{chain}
        WHERE account_id = '{account_id}'
            AND ts >= '{start_date}' AND ts <= '{end_date}'
        """
    )

    # Query for hourly data
    df_hourly = api._run_query(
        f"""
        SELECT
            ts,
            cumulative_volume,
            cumulative_fees
        FROM {api.environment}_{chain}.fct_perp_account_stats_hourly_{chain}
        WHERE account_id = '{account_id}'
            AND ts >= '{start_date}' AND ts <= '{end_date}'
        ORDER BY ts
        """
    )

    # Query for collateral balances
    df_collateral = (
        api._run_query(
            f"""
        SELECT
            ts,
            synth_symbol,
            event_type,
            amount_delta,
            account_balance,
            account_balance_usd,
            transaction_hash
        FROM {api.environment}_{chain}.fct_perp_collateral_balances_{chain}
        WHERE ts >= '{start_date}' and ts <= '{end_date}'
            AND account_id = '{account_id}'
        ORDER BY ts
        """
        )
        if st.session_state.chain.startswith("arbitrum")
        else pd.DataFrame()
    )

    # Adjust data
    df_accounts = df_accounts[["account_id", "sender"]].drop_duplicates()
    df_accounts.columns = ["id", "owner"]

    return {
        "accounts": df_accounts,
        "order_expired": df_order_expired,
        "interest": df_interest,
        "trade": df_trade,
        "transfer": df_transfer,
        "account_liq": df_account_liq,
        "hourly": df_hourly,
        "collateral": df_collateral,
    }


@st.cache_data(ttl="30m")
def make_charts(data):
    collateral_chart = (
        None
        if data["collateral"].empty
        else chart_lines(
            data["collateral"],
            x_col="ts",
            y_cols="account_balance_usd",
            title="Collateral Balances",
            color_by="synth_symbol",
        )
    )

    return {
        "cumulative_volume": chart_lines(
            data["hourly"],
            x_col="ts",
            y_cols="cumulative_volume",
            title="Cumulative Volume",
        ),
        "cumulative_fees": chart_lines(
            data["hourly"],
            x_col="ts",
            y_cols="cumulative_fees",
            title="Cumulative Fees",
            custom_agg=dict(field="cumulative_fees", name="Total", agg="sum"),
        ),
        "collateral": collateral_chart,
    }


def main():
    st.markdown("## Perps: Account Summary")

    # Initialize session state for filters if not already set
    if "account_id" not in st.session_state:
        st.session_state.account_id = None
    if "start_date" not in st.session_state:
        st.session_state.start_date = datetime.today().date() - timedelta(days=14)
    if "end_date" not in st.session_state:
        st.session_state.end_date = datetime.today().date() + timedelta(days=1)

    # Date filter
    with st.expander("Date Filter"):
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

    # Fetch initial data
    data = fetch_data(
        chain=st.session_state.chain,
        account_id=st.session_state.account_id,
        start_date=st.session_state.start_date,
        end_date=st.session_state.end_date,
    )

    # Account lookup
    with st.expander("Look up accounts by address"):
        address = st.text_input("Enter an address to look up associated accounts")

        df_accounts = data["accounts"]
        account_numbers = df_accounts[df_accounts["owner"] == address]["id"].unique()

        if len(account_numbers) > 0:
            st.dataframe(account_numbers, hide_index=True)

    # Account selection
    accounts = data["accounts"]["id"].unique()
    accounts = sorted([int(acc) for acc in accounts])
    st.selectbox(
        "Select account",
        accounts,
        index=(
            accounts.index(st.session_state.account_id)
            if st.session_state.account_id in accounts
            else 0
        ),
        key="account_id",
    )

    # Fetch data based on selected account
    data = fetch_data(
        chain=st.session_state.chain,
        account_id=st.session_state.account_id,
        start_date=st.session_state.start_date,
        end_date=st.session_state.end_date,
    )

    # Process data for open positions
    df_open_positions = (
        data["trade"]
        .sort_values("ts")
        .groupby(["account_id", "market_id"])
        .last()
        .reset_index()
    )
    df_open_positions = df_open_positions[df_open_positions["position_size"].abs() > 0]

    df_open_account = df_open_positions[
        df_open_positions["account_id"] == st.session_state.account_id
    ]

    last_liq = (
        data["account_liq"]
        .loc[data["account_liq"]["account_id"] == st.session_state.account_id, "ts"]
        .max()
    )

    # Handle cases with no liquidations
    last_liq = last_liq if pd.notna(last_liq) else "2023-01-01 00:00:00+00:00"

    df_open_account = df_open_account.loc[
        df_open_account["ts"] > last_liq,
        ["account_id", "market_symbol", "position_size", "notional_position_size"],
    ]

    # Display open positions
    st.markdown("### Open Positions")
    if len(df_open_account) > 0:
        st.dataframe(df_open_account, use_container_width=True)
    else:
        st.markdown("No open positions")

    # Create charts
    charts = make_charts(data)

    # Display charts
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(charts["cumulative_volume"], use_container_width=True)

    with col2:
        st.plotly_chart(charts["cumulative_fees"], use_container_width=True)

    # display collateral chart if not None
    if charts["collateral"]:
        st.plotly_chart(charts["collateral"], use_container_width=True)

    # Display recent trades
    st.markdown("### Recent Trades")
    st.dataframe(
        data["trade"].sort_values("ts", ascending=False).head(50),
        use_container_width=True,
        hide_index=True,
    )

    # Display recent transfers
    st.markdown("### Recent Transfers")
    st.dataframe(
        data["transfer"].sort_values("block_timestamp", ascending=False).head(50),
        use_container_width=True,
        hide_index=True,
    )

    # Display account liquidations
    st.markdown("### Liquidations")
    st.dataframe(
        data["account_liq"].sort_values("ts", ascending=False).head(25),
        use_container_width=True,
        hide_index=True,
    )

    # Display expired orders
    st.markdown("### Expired Orders")
    st.dataframe(
        data["order_expired"],
        use_container_width=True,
        hide_index=True,
    )

    # Display interest charged
    st.markdown("### Interest Charged")
    st.dataframe(
        data["interest"],
        use_container_width=True,
        hide_index=True,
    )

    # Export data section
    exports = [{"title": export, "df": data[export]} for export in data.keys()]
    with st.expander("Exports"):
        for export in exports:
            export_data(title=export["title"], df=export["df"])
