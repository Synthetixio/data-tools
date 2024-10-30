import streamlit as st
import pandas as pd

from synthetix import Synthetix
from api.internal_api import SynthetixAPI, get_db_config
from dashboards.system_monitor.modules.settings import settings

PERPS_NETWORKS = [
    8453,
    84532,
    42161,
    421614,
]

USD_POSITION_SIZES = [
    10000000,
    5000000,
    1000000,
    500000,
    100000,
    10000,
    1000,
    100,
    -100,
    -1000,
    -10000,
    -100000,
    -500000,
    -1000000,
    -5000000,
    -10000000,
]


def get_markets(snx):
    return snx.perps.markets_by_name


def get_market_info(snx, market_name):
    market_info = snx.perps.markets_by_name[market_name]

    df_market_info = pd.DataFrame().from_dict(
        {market_name: market_info}, orient="index"
    )
    df_market_info["skew_usd"] = df_market_info["skew"] * df_market_info["index_price"]
    df_market_info = df_market_info[
        [
            "market_name",
            "size",
            "skew",
            "skew_usd",
            "skew_scale",
            "maker_fee",
            "taker_fee",
            "max_open_interest",
            "current_funding_rate",
        ]
    ]

    pct_cols = ["current_funding_rate", "maker_fee", "taker_fee"]
    df_market_info[pct_cols] = df_market_info[pct_cols].applymap(lambda x: f"{x:.4%}")

    val_cols = ["size", "skew", "skew_scale", "max_open_interest"]
    df_market_info[val_cols] = df_market_info[val_cols].applymap(lambda x: f"{x:.2f}")

    df_market_info["skew_usd"] = df_market_info["skew_usd"].apply(
        lambda x: f"${x:,.2f}"
    )
    return df_market_info.transpose()


@st.cache_data(ttl=600, hash_funcs={Synthetix: lambda x: x.network_id})
def get_depth(snx, market_name):
    market_info = snx.perps.markets_by_name[market_name]
    price = market_info["index_price"]
    skew = market_info["skew"]
    skew_usd = skew * price
    funding_rate_24h = market_info["current_funding_rate"]
    funding_rate_1h = funding_rate_24h / 24

    # check the market depth at various sizes
    position_sizes = USD_POSITION_SIZES + [-skew_usd]
    position_sizes.sort(reverse=True)
    depths = {}
    for size in position_sizes:
        position_size = size / price
        depths[size] = snx.perps.get_quote(position_size, market_name=market_name)

    df = pd.DataFrame().from_dict(depths, orient="index")
    df.index.name = "order_size_usd"
    df = df.reset_index()

    # add columns
    df["total_fee_usd"] = df["order_fees"] + df["settlement_reward_cost"]
    df["price_impact_pct"] = (
        abs(df["fill_price"] - df["index_price"]) / df["index_price"]
    )
    df["order_fee_pct"] = df["order_fees"] / df["order_size_usd"]
    df["settlement_fee_pct"] = df["settlement_reward_cost"] / df["order_size_usd"]
    df["total_fee_pct"] = df["total_fee_usd"] / df["order_size_usd"]
    df["funding_per_hour_usd"] = funding_rate_1h * df["order_size_usd"]

    pct_cols = [c for c in df.columns if c.endswith("_pct")]
    df[pct_cols] = df[pct_cols].applymap(lambda x: f"{x:.3%}")

    usd_cols = [
        c
        for c in df.columns
        if c.endswith("_usd") or c.endswith("_fees") or c.endswith("_price")
    ]
    df[usd_cols] = df[usd_cols].applymap(lambda x: f"${x:,.2f}")

    cols = [
        "order_size_usd",
        "index_price",
        "fill_price",
        "price_impact_pct",
        "total_fee_usd",
        "total_fee_pct",
        "funding_per_hour_usd",
        "order_fees",
        "order_fee_pct",
        "settlement_reward_cost",
        "settlement_fee_pct",
    ]
    return df[cols]


# add the settings dropdown
settings(enabled_markets=PERPS_NETWORKS)

markets = get_markets(st.session_state.snx)

st.selectbox("Market", list(markets.keys()), key="market_name")

st.markdown("## Market Depth")
df_depth = get_depth(st.session_state.snx, st.session_state.market_name)

st.dataframe(df_depth, use_container_width=True)

df_market_info = get_market_info(st.session_state.snx, st.session_state.market_name)
st.dataframe(df_market_info, use_container_width=True)
