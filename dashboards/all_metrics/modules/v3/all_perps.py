from datetime import datetime, timedelta

import streamlit as st

from dashboards.utils.data import export_data
from dashboards.utils.charts import chart_bars


@st.cache_data(ttl="30m")
def fetch_data(start_date, end_date, resolution):
    api = st.session_state.api

    df_stats = api._run_query(
        f"""
        WITH base AS (
            SELECT
                ts,
                'Base (V3)' AS label,
                volume,
                trades,
                exchange_fees AS fees,
                liquidated_accounts AS liquidations
            FROM {api.environment}_base_mainnet.fct_perp_stats_{resolution}_base_mainnet
            WHERE ts >= '{start_date}' AND ts <= '{end_date}'
        ),
        optimism AS (
            SELECT
                ts,
                'Optimism (V2)' AS label,
                volume,
                trades,
                exchange_fees + liquidation_fees AS fees,
                liquidations
            FROM {api.environment}_optimism_mainnet.fct_v2_stats_{resolution}_optimism_mainnet
            WHERE ts >= '{start_date}' AND ts <= '{end_date}'
        ),
        arbitrum AS (
            SELECT
                ts,
                'Arbitrum (V3)' AS label,
                volume,
                trades,
                exchange_fees AS fees,
                liquidated_accounts AS liquidations
            FROM {api.environment}_arbitrum_mainnet.fct_perp_stats_{resolution}_arbitrum_mainnet
            WHERE ts >= '{start_date}' AND ts <= '{end_date}'
        )
        SELECT * FROM base
        UNION ALL
        SELECT * FROM optimism
        UNION ALL
        SELECT * FROM arbitrum
        ORDER BY ts
        """
    )

    return {
        "stats": df_stats,
    }


@st.cache_data(ttl="30m")
def make_charts(data):
    return {
        "volume": chart_bars(
            data["stats"],
            x_col="ts",
            y_cols="volume",
            title="Volume",
            color_by="label",
        ),
        "fees": chart_bars(
            data["stats"],
            x_col="ts",
            y_cols="fees",
            title="Exchange Fees",
            color_by="label",
        ),
        "trades": chart_bars(
            data["stats"],
            x_col="ts",
            y_cols="trades",
            title="Trades",
            color_by="label",
            y_format="#",
            no_decimals=True,
        ),
        "liquidations": chart_bars(
            data["stats"],
            x_col="ts",
            y_cols="liquidations",
            title="Liquidations",
            color_by="label",
            y_format="#",
            no_decimals=True,
        ),
    }


def main():
    ## title
    st.markdown("# Perps")

    ## inputs
    with st.expander("Filters"):
        st.radio(
            "Resolution",
            ["daily", "hourly"],
            key="resolution",
        )

        filt_col1, filt_col2 = st.columns(2)
        with filt_col1:
            start_date_default = datetime.today().date() - timedelta(days=14)
            st.date_input(
                "Start",
                key="start_date",
                value=start_date_default,
            )

        with filt_col2:
            end_date_default = datetime.today().date() + timedelta(days=1)
            st.date_input(
                "End",
                key="end_date",
                value=end_date_default,
            )

    ## fetch data
    data = fetch_data(
        st.session_state.start_date,
        st.session_state.end_date,
        st.session_state.resolution,
    )

    ## charts
    charts = make_charts(data)

    ## display
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(charts["volume"], use_container_width=True)
        st.plotly_chart(charts["trades"], use_container_width=True)

    with col2:
        st.plotly_chart(charts["fees"], use_container_width=True)
        st.plotly_chart(charts["liquidations"], use_container_width=True)

    ## Export
    exports = [{"title": key, "df": data[key]} for key in data]
    with st.expander("Exports"):
        for export in exports:
            export_data(export["title"], export["df"])
