from datetime import datetime, timedelta

import streamlit as st

from dashboards.utils.data import export_data
from dashboards.utils.charts import chart_area, chart_lines


@st.cache_data(ttl="30m")
def fetch_data(start_date, end_date, resolution):
    api = st.session_state.api

    df_collateral = api._run_query(
        f"""
        SELECT 
            ts,
            CONCAT(coalesce(tk.token_symbol, collateral_type), ' (Arbitrum)') as label,
            collateral_value,
            debt,
            hourly_pnl,
            rewards_usd,
            hourly_issuance,
            cumulative_issuance,
            cumulative_pnl,
            apr_{resolution} + apr_{resolution}_underlying as apr,
            apr_{resolution}_pnl as apr_pnl,
            apr_{resolution}_rewards as apr_rewards
        FROM {api.environment}_arbitrum_mainnet.fct_core_apr_arbitrum_mainnet apr
        LEFT JOIN {api.environment}_seeds.arbitrum_mainnet_tokens tk on lower(apr.collateral_type) = lower(tk.token_address)
        WHERE ts >= '{start_date}' and ts <= '{end_date}'
        
        UNION ALL
        
        SELECT 
            ts,
            CONCAT(coalesce(tk.token_symbol, collateral_type), ' (Base)') as label,
            collateral_value,
            debt,
            hourly_pnl,
            rewards_usd,
            hourly_issuance,
            cumulative_issuance,
            cumulative_pnl,
            apr_{resolution} + apr_{resolution}_underlying as apr,
            apr_{resolution}_pnl as apr_pnl,
            apr_{resolution}_rewards as apr_rewards
        FROM {api.environment}_base_mainnet.fct_core_apr_base_mainnet apr
        LEFT JOIN {api.environment}_seeds.base_mainnet_tokens tk on lower(apr.collateral_type) = lower(tk.token_address)
        WHERE ts >= '{start_date}' and ts <= '{end_date}'

        UNION ALL
        
        SELECT 
            ts,
            CONCAT(coalesce(tk.token_symbol, collateral_type), ' (Ethereum)') as label,
            collateral_value,
            debt,
            hourly_pnl,
            rewards_usd,
            hourly_issuance,
            cumulative_issuance,
            cumulative_pnl,
            apr_{resolution} + apr_{resolution}_underlying as apr,
            apr_{resolution}_pnl as apr_pnl,
            apr_{resolution}_rewards as apr_rewards
        FROM {api.environment}_eth_mainnet.fct_core_apr_eth_mainnet apr
        LEFT JOIN {api.environment}_seeds.eth_mainnet_tokens tk on lower(apr.collateral_type) = lower(tk.token_address)
        WHERE ts >= '{start_date}' and ts <= '{end_date}'
        
        ORDER BY ts
    """
    )

    df_chain = api._run_query(
        f"""
        with arbitrum as (
        select
            ts,
            label,
            sum(collateral_value) as collateral_value,
            sum(cumulative_pnl) as cumulative_pnl
        from (
            SELECT 
                ts,
                'Arbitrum' as label,
                collateral_value,
                cumulative_pnl
            FROM {api.environment}_arbitrum_mainnet.fct_core_apr_arbitrum_mainnet apr
            LEFT JOIN {api.environment}_seeds.arbitrum_mainnet_tokens tk on lower(apr.collateral_type) = lower(tk.token_address)
            WHERE ts >= '{start_date}' and ts <= '{end_date}'
        ) as a
        group by ts, label
        ),
        base as (
        select
            ts,
            label,
            sum(collateral_value) as collateral_value,
            sum(cumulative_pnl) as cumulative_pnl
        from (
            SELECT 
                ts,
                'Base' as label,
                collateral_value,
                cumulative_pnl
            FROM {api.environment}_base_mainnet.fct_core_apr_base_mainnet apr
            LEFT JOIN {api.environment}_seeds.base_mainnet_tokens tk on lower(apr.collateral_type) = lower(tk.token_address)
            WHERE ts >= '{start_date}' and ts <= '{end_date}'
        ) as b
        group by ts, label
        ),
        eth as (
        select
            ts,
            label,
            sum(collateral_value) as collateral_value,
            sum(cumulative_pnl) as cumulative_pnl
        from (
            SELECT 
                ts,
                'Ethereum' as label,
                collateral_value,
                cumulative_pnl
            FROM {api.environment}_eth_mainnet.fct_core_apr_eth_mainnet apr
            LEFT JOIN {api.environment}_seeds.eth_mainnet_tokens tk on lower(apr.collateral_type) = lower(tk.token_address)
            WHERE ts >= '{start_date}' and ts <= '{end_date}'
        ) as b
        group by ts, label
        )
    
        select * from eth
        union all
        select * from arbitrum
        union all
        select * from base
        ORDER BY ts
    """
    )

    return {
        "collateral": df_collateral,
        "chain": df_chain,
    }


@st.cache_data(ttl="30m")
def make_charts(data):
    return {
        "tvl_collateral": chart_area(
            data["collateral"],
            x_col="ts",
            y_cols="collateral_value",
            title="TVL by Collateral",
            color_by="label",
            custom_agg=dict(field="collateral_value", name="Total", agg="sum"),
        ),
        "pnl_collateral": chart_lines(
            data["collateral"],
            x_col="ts",
            y_cols="cumulative_pnl",
            title="Cumulative Pnl by Collateral",
            color_by="label",
            custom_agg=dict(field="cumulative_pnl", name="Total", agg="sum"),
        ),
        "tvl_chain": chart_area(
            data["chain"],
            x_col="ts",
            y_cols="collateral_value",
            title="TVL by Chain",
            color_by="label",
            custom_agg=dict(field="collateral_value", name="Total", agg="sum"),
        ),
        "pnl_chain": chart_lines(
            data["chain"],
            x_col="ts",
            y_cols="cumulative_pnl",
            title="Cumulative Pnl by Chain",
            color_by="label",
            custom_agg=dict(field="cumulative_pnl", name="Total", agg="sum"),
        ),
        "apr": chart_lines(
            data["collateral"],
            x_col="ts",
            y_cols="apr",
            title=f"APR - {st.session_state.resolution} average",
            y_format="%",
            color_by="label",
            sort_ascending=True,
        ),
    }


def main():
    ## title
    st.markdown("# Liquidity Pools")

    ## inputs
    with st.expander("Filters"):
        st.radio(
            "Resolution",
            ["28d", "7d", "24h"],
            index=1,
            key="resolution",
        )

        filt_col1, filt_col2 = st.columns(2)
        with filt_col1:
            start_date = datetime.today().date() - timedelta(days=14)
            st.date_input(
                "Start",
                key="start_date",
                value=start_date,
            )

        with filt_col2:
            end_date = datetime.today().date() + timedelta(days=1)
            st.date_input(
                "End",
                key="end_date",
                value=end_date,
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
    st.plotly_chart(charts["apr"], use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(charts["tvl_chain"], use_container_width=True)
        st.plotly_chart(charts["tvl_collateral"], use_container_width=True)

    with col2:
        st.plotly_chart(charts["pnl_chain"], use_container_width=True)
        st.plotly_chart(charts["pnl_collateral"], use_container_width=True)

    ## export
    exports = [{"title": export, "df": data[export]} for export in data.keys()]
    with st.expander("Exports"):
        for export in exports:
            export_data(export["title"], export["df"])
