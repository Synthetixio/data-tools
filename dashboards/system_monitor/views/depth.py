import streamlit as st
import pandas as pd

from synthetix import Synthetix
from synthetix.utils.multicall import multicall_erc7412, call_erc7412
from synthetix.utils import ether_to_wei, wei_to_ether
from api.internal_api import SynthetixAPI, get_db_config
from dashboards.system_monitor.modules.settings import settings
from dashboards.utils.charts import chart_lines, chart_bars


PERPS_NETWORKS = [
    8453,
    84532,
    42161,
    421614,
]

ALL_USD_POSITION_SIZES = [-10000, -1000, -100, 100, 1000, 10000] + list(
    range(-10000000, 10000000, 50000)
)

DISPLAY_USD_POSITION_SIZES = [
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


def plot_impact(df):
    """Create a price impact analysis chart.

    Args:
        df (pd.DataFrame): DataFrame containing the data for the chart.

    Returns:
        plotly.graph_objs._figure.Figure: The generated chart.
    """
    fig = chart_lines(
        df,
        x_col="order_size_usd",
        y_cols="price_impact_pct",
        title="Price Impact",
        x_format="$",
        y_format="%",
        smooth=True,
    )
    # add axis labels
    fig.update_xaxes(title_text="Order Size")
    fig.update_yaxes(title_text="Price Impact %")
    return fig


def plot_depth(df):
    """Create a depth analysis chart.

    Args:
        df (pd.DataFrame): DataFrame containing the data for the chart.

    Returns:
        plotly.graph_objs._figure.Figure: The generated chart.
    """
    fig = chart_lines(
        df,
        x_col="order_size_usd",
        y_cols="fill_price",
        title="Depth",
        x_format="$",
        y_format="$",
        smooth=True,
    )
    fig.update_xaxes(title_text="Order Size")
    fig.update_yaxes(title_text="Fill Price")
    return fig


def get_markets(snx):
    """Retrieve the markets from the Synthetix instance.

    Args:
        snx (Synthetix): The Synthetix instance.

    Returns:
        dict: A dictionary of markets by name.
    """
    return snx.perps.markets_by_name


def get_market_info(snx, market_name):
    """Retrieve market information for a specific market.

    Args:
        snx (Synthetix): The Synthetix instance.
        market_name (str): The name of the market.

    Returns:
        pd.DataFrame: DataFrame containing the market information.
    """
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

    # max leverage
    liquidation_parameters = call_erc7412(
        snx,
        snx.perps.market_proxy,
        "getLiquidationParameters",
        (market_info["market_id"]),
    )
    min_initial_margin_ratio = wei_to_ether(liquidation_parameters[1])
    max_leverage = 1 / min_initial_margin_ratio

    pct_cols = ["current_funding_rate", "maker_fee", "taker_fee"]
    df_market_info[pct_cols] = df_market_info[pct_cols].applymap(lambda x: f"{x:.4%}")

    val_cols = ["size", "skew", "skew_scale", "max_open_interest"]
    df_market_info[val_cols] = df_market_info[val_cols].applymap(lambda x: f"{x:.2f}")

    df_market_info["skew_usd"] = df_market_info["skew_usd"].apply(
        lambda x: f"${x:,.2f}"
    )
    df_market_info["max_leverage"] = f"{max_leverage:.2g}x"
    return df_market_info.transpose()


@st.cache_data(ttl=600, hash_funcs={Synthetix: lambda x: x.network_id})
def get_depth(snx, market_name):
    """Retrieve the depth information for a specific market.

    Args:
        snx (Synthetix): The Synthetix instance.
        market_name (str): The name of the market.

    Returns:
        pd.DataFrame: DataFrame containing the depth information.
    """
    market_info = snx.perps.markets_by_name[market_name]
    price = market_info["index_price"]
    skew = market_info["skew"]
    skew_usd = skew * price
    funding_rate_24h = market_info["current_funding_rate"]
    funding_rate_1h = funding_rate_24h / 24

    # check the market depth at various sizes
    position_sizes_usd = ALL_USD_POSITION_SIZES + [-skew_usd]
    position_sizes_usd.sort(reverse=True)
    position_sizes = [size / price for size in position_sizes_usd]

    order_fees_result = multicall_erc7412(
        snx,
        snx.perps.market_proxy,
        "computeOrderFeesWithPrice",
        [
            (market_info["market_id"], ether_to_wei(size), ether_to_wei(price))
            for size in position_sizes
        ],
    )

    settlement_reward_cost = call_erc7412(
        snx,
        snx.perps.market_proxy,
        "getSettlementRewardCost",
        (market_info["market_id"], 0),
    )
    settlement_reward_cost = wei_to_ether(settlement_reward_cost)

    depths = {}
    for size_usd, size, fee_result in zip(
        position_sizes_usd, position_sizes, order_fees_result
    ):
        order_fees = wei_to_ether(fee_result[0])
        fill_price = wei_to_ether(fee_result[1])

        depths[size_usd] = {
            "order_size_usd": size_usd,
            "order_size": size,
            "order_fees": order_fees,
            "fill_price": fill_price,
            "index_price": price,
            "settlement_reward_cost": settlement_reward_cost,
        }

    df = pd.DataFrame().from_dict(depths, orient="index")
    df = df.reset_index()

    # add columns
    df["total_fee_usd"] = df["order_fees"] + df["settlement_reward_cost"]
    df["premium_discount_pct"] = (df["fill_price"] - df["index_price"]) / df[
        "index_price"
    ]
    df["price_impact_pct"] = (
        abs(df["fill_price"] - df["index_price"]) / df["index_price"]
    )
    df["order_fee_pct"] = abs(df["order_fees"] / df["order_size_usd"])
    df["settlement_fee_pct"] = df["settlement_reward_cost"] / df["order_size_usd"]
    df["total_fee_pct"] = df["total_fee_usd"] / df["order_size_usd"]
    df["funding_per_hour_usd"] = funding_rate_1h * df["order_size_usd"]

    cols = [
        "order_size_usd",
        "index_price",
        "fill_price",
        "premium_discount_pct",
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


def format_depth(df):
    """Format the depth DataFrame for display.

    Args:
        df (pd.DataFrame): DataFrame containing the depth information.

    Returns:
        pd.DataFrame: Formatted DataFrame.
    """
    df = df.copy()
    pct_cols = [c for c in df.columns if c.endswith("_pct")]
    df[pct_cols] = df[pct_cols].applymap(lambda x: f"{x:.3%}")

    usd_cols = [
        c
        for c in df.columns
        if c.endswith("_usd") or c.endswith("_fees") or c.endswith("_price")
    ]
    df[usd_cols] = df[usd_cols].applymap(lambda x: f"${x:,.2f}")
    return df


# add the settings dropdown
settings(enabled_markets=PERPS_NETWORKS)

markets = get_markets(st.session_state.snx)

st.selectbox("Market", list(markets.keys()), key="market_name")

st.markdown("## Market Depth")
df_depth = get_depth(st.session_state.snx, st.session_state.market_name)

st.dataframe(
    format_depth(df_depth[df_depth["order_size_usd"].isin(DISPLAY_USD_POSITION_SIZES)]),
    use_container_width=True,
)

st.markdown("#### Max Maker Order")
st.dataframe(
    format_depth(df_depth[~df_depth["order_size_usd"].isin(ALL_USD_POSITION_SIZES)]),
    use_container_width=True,
)

df_market_info = get_market_info(st.session_state.snx, st.session_state.market_name)
st.dataframe(df_market_info)

# charts
col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(plot_impact(df_depth), use_container_width=True)

with col2:
    st.plotly_chart(plot_depth(df_depth), use_container_width=True)
