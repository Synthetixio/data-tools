from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
from synthetix import Synthetix
from synthetix.utils import wei_to_ether
from synthetix.utils.multicall import call_erc7412, multicall_erc7412
from eth_utils import encode_hex

from dashboards.system_monitor.modules.settings import settings

st.markdown("# Synthetix V3: Perps")

PERPS_NETWORKS = [
    8453,
    84532,
    42161,
    421614,
]

# add the settings dropdown
settings(enabled_markets=PERPS_NETWORKS)


# get the core configuration
@st.cache_data(ttl=300, hash_funcs={Synthetix: lambda x: x.network_id})
def get_configs(snx):
    markets = snx.perps.markets_by_name

    # call other functions
    # - getSupportedCollaterals -> [collateralId1, collateralId2, ...]
    # - getCollateralConfigurationFull(collateralId) -> (maxCollateralAmount, upperLimitDiscount, lowerLimitDiscount, discountScalar)

    # if multicollateral
    if snx.perps.is_multicollateral:
        supported_collaterals = call_erc7412(
            snx, snx.perps.market_proxy, "getSupportedCollaterals", ()
        )
        supported_collaterals = [x for x in supported_collaterals if x != 0]
        collateral_configurations = multicall_erc7412(
            snx,
            snx.perps.market_proxy,
            "getCollateralConfigurationFull",
            [(collateral_id,) for collateral_id in supported_collaterals],
        )
        collateral_configurations = [
            {
                "market_id": idx,
                "market_name": snx.spot.markets_by_id[idx]["market_name"],
                "max_collateral_amount": wei_to_ether(x[0]),
                "upper_limit_discount": wei_to_ether(x[1]),
                "lower_limit_discount": wei_to_ether(x[2]),
                "discount_scalar": wei_to_ether(x[3]),
            }
            for idx, x in zip(supported_collaterals, collateral_configurations)
        ]
        df_collaterals = pd.DataFrame.from_records(collateral_configurations)
    else:
        df_collaterals = pd.DataFrame()

    # create a dataframe and clean it
    df_markets = pd.DataFrame.from_dict(markets, orient="index").sort_values(
        "market_id"
    )
    df_markets["funding_apr"] = df_markets["current_funding_rate"] * 365

    # change some types to percentages
    percent_cols = [
        "maker_fee",
        "taker_fee",
        "current_funding_rate",
        "funding_apr",
        "current_funding_velocity",
        "interest_rate",
    ]
    for col in percent_cols:
        pct_format = "{:.4%}" if "funding" in col else "{:.2%}"
        df_markets[col] = df_markets[col].astype(float).map(pct_format.format)

    return df_markets, df_collaterals


def clean_markets(configs):
    # add OI
    configs["open_interest"] = configs["size"] * configs["index_price"]
    configs["long_oi"] = (
        (configs["size"] + configs["skew"]) / 2 * configs["index_price"]
    )
    configs["short_oi"] = (
        (configs["size"] - configs["skew"]) / 2 * configs["index_price"]
    )
    configs["long_pct"] = configs.apply(
        lambda x: (
            f"{(x['long_oi'] / x['open_interest']) * 100:.2f}%"
            if x["open_interest"] > 0
            else "0%"
        ),
        axis=1,
    )
    configs["short_pct"] = configs.apply(
        lambda x: (
            f"{(x['short_oi'] / x['open_interest']) * 100:.2f}%"
            if x["open_interest"] > 0
            else "0%"
        ),
        axis=1,
    )

    # calculate amount of oi used
    # it is the larger of the size versus max_open_interest OR the size * index_price versus the max_market_value
    configs["oi_used"] = configs.apply(
        lambda x: max(
            x["size"] / x["max_open_interest"] if x["max_open_interest"] > 0 else 0,
            (
                (x["size"] * x["index_price"]) / x["max_market_value"]
                if x["max_market_value"] > 0
                else 0
            ),
        ),
        axis=1,
    )
    configs["oi_used_pct"] = configs["oi_used"].map("{:.2%}".format)
    configs.sort_values("open_interest", ascending=False, inplace=True)
    return configs


# format the configurations
df_markets, df_collaterals = get_configs(st.session_state.snx)
df_markets = clean_markets(df_markets)

# display
st.markdown("### Market Configurations")
settings_cols = [
    "market_id",
    "market_name",
    "max_open_interest",
    "max_market_value",
    "skew_scale",
    "maker_fee",
    "taker_fee",
    "max_funding_velocity",
    "feed_id",
]
st.dataframe(df_markets[settings_cols], hide_index=True, use_container_width=True)

st.markdown("### Market Information")
info_cols = [
    "market_name",
    "size",
    "index_price",
    "open_interest",
    "long_oi",
    "short_oi",
    "long_pct",
    "short_pct",
    "oi_used_pct",
    "funding_apr",
    "interest_rate",
]
st.dataframe(df_markets[info_cols], hide_index=True, use_container_width=True)

st.markdown("### Collateral Configurations")
st.dataframe(df_collaterals, hide_index=True, use_container_width=True)
