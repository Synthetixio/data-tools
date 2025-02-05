import streamlit as st
import pandas as pd
from synthetix import Synthetix
from synthetix.utils import wei_to_ether
from synthetix.utils.multicall import multicall_erc7412
from eth_utils import encode_hex

from dashboards.system_monitor.modules.settings import settings

st.markdown("# Synthetix V3: Core")


# add the settings dropdown
settings()


# get the core configuration
@st.cache_data(ttl=300, hash_funcs={Synthetix: lambda x: x.network_id})
def get_configs(snx):
    raw_configs = snx.core.core_proxy.functions.getCollateralConfigurations(
        False
    ).call()

    configs = {}
    for config in raw_configs:
        (
            enabled,
            issuance_ratio,
            liquidation_ratio,
            liquidation_reward,
            oracle_node_id,
            token_address,
            min_delegation,
        ) = config

        token = snx.web3.eth.contract(
            address=token_address, abi=snx.contracts["common"]["ERC20"]["abi"]
        )
        try:
            # get the token name if its ERC20 compliant
            token_name = token.functions.name().call()
            token_symbol = token.functions.symbol().call()
            token_description = f"{token_name} ({token_symbol})"
        except:
            # if not an ERC20 token, use a default name
            token_name = "Unknown Token"
            token_description = f"{token_name}"

        configs[token_address] = {
            "token": token_description,
            "enabled": enabled,
            "min_delegation": wei_to_ether(min_delegation),
            "issuance_ratio": wei_to_ether(issuance_ratio),
            "liquidation_ratio": wei_to_ether(liquidation_ratio),
            "liquidation_reward": wei_to_ether(liquidation_reward),
            "token_address": token_address,
            "oracle_node_id": encode_hex(oracle_node_id),
        }

    # create a dataframe and clean it
    df = pd.DataFrame.from_dict(configs, orient="index")

    # replace all values over 1e59 with "Infinity"
    df = df.applymap(lambda x: "Infinity" if type(x) is float and x > 1e59 else x)

    # change some types to percentages
    df["issuance_ratio"] = df["issuance_ratio"].astype(float).map("{:.2%}".format)
    df["liquidation_ratio"] = df["liquidation_ratio"].astype(float).map("{:.2%}".format)
    return df


@st.cache_data(ttl=300, hash_funcs={Synthetix: lambda x: x.network_id})
def get_vaults(snx, configs):
    collaterals = configs.index.tolist()
    function_inputs = [(1, collateral) for collateral in collaterals]

    # get calls
    if "markets_by_id" in dir(snx.perps):
        calls, _ = snx.perps._prepare_oracle_call()
    else:
        calls = []

    # get all vault collaterals
    collateral_calls = multicall_erc7412(
        snx, snx.core.core_proxy, "getVaultCollateral", function_inputs, calls=calls
    )
    is_vault_liquidatables = multicall_erc7412(
        snx, snx.core.core_proxy, "isVaultLiquidatable", function_inputs, calls=calls
    )
    vault_collateral_ratios = multicall_erc7412(
        snx,
        snx.core.core_proxy,
        "getVaultCollateralRatio",
        function_inputs,
        calls=calls,
    )
    vault_debts = multicall_erc7412(
        snx, snx.core.core_proxy, "getVaultDebt", function_inputs, calls=calls
    )

    collateral_results = {
        collateral: {
            "token": configs.loc[collateral, "token"],
            "collateral_amount": wei_to_ether(result[0]),
            "collateral_value": wei_to_ether(result[1]),
            "vault_debt": wei_to_ether(vault_debt),
            "vault_collateral_ratio": wei_to_ether(vault_collateral_ratio),
            "is_vault_liquidatable": is_vault_liquidatable,
        }
        for collateral, result, is_vault_liquidatable, vault_debt, vault_collateral_ratio in zip(
            collaterals,
            collateral_calls,
            is_vault_liquidatables,
            vault_debts,
            vault_collateral_ratios,
        )
    }
    df = pd.DataFrame.from_dict(collateral_results, orient="index")
    return df


def get_market_type(snx, market_address):
    # get the type of perps market that is enabled
    perps_type = str(type(snx.perps))
    perps_type = perps_type.split(".")[-1][:-2]

    if (
        "market_proxy" in dir(snx.perps)
        and market_address == snx.perps.market_proxy.address
    ):
        return perps_type
    elif (
        "market_proxy" in dir(snx.spot)
        and market_address == snx.spot.market_proxy.address
    ):
        return "Spot"
    else:
        return "Unknown"


@st.cache_data(ttl=300, hash_funcs={Synthetix: lambda x: x.network_id})
def get_markets(snx, configs):
    market_ids = range(1, 26)

    # fetch all market addresses
    market_addresses = multicall_erc7412(
        snx,
        snx.core.core_proxy,
        "getMarketAddress",
        [(market,) for market in market_ids],
    )

    market_addresses = [snx.web3.to_checksum_address(addr) for addr in market_addresses]
    markets = {
        market_id: {
            "market_id": market_id,
            "market_address": address,
            "market_type": get_market_type(snx, address),
        }
        for market_id, address in zip(market_ids, market_addresses)
    }

    # filter perps and spot
    perps = pd.DataFrame.from_dict(
        {
            market_id: market
            for market_id, market in markets.items()
            if market["market_type"] in ["PerpsV3", "BfPerps"]
        },
        orient="index",
    )
    spot = pd.DataFrame.from_dict(
        {
            market_id: market
            for market_id, market in markets.items()
            if market["market_type"] == "Spot"
        },
        orient="index",
    )
    if spot.shape[0] > 0:
        spot = get_market_details(
            snx,
            configs,
            spot,
            snx.spot.market_proxy,
        )
    if perps.shape[0] > 0:
        perps = get_market_details(
            snx,
            configs,
            perps,
            snx.perps.market_proxy,
        )
    return perps, spot


@st.cache_data(ttl=300, hash_funcs={Synthetix: lambda x: x.network_id})
def get_market_details(snx, configs, markets, _contract):
    market_ids = [(market_id,) for market_id in markets["market_id"].tolist()]

    # get calls
    if "markets_by_id" in dir(snx.perps):
        calls, _ = snx.perps._prepare_oracle_call()
    else:
        calls = []

    market_names = multicall_erc7412(snx, _contract, "name", market_ids, calls=calls)
    is_capacity_lockeds = multicall_erc7412(
        snx,
        snx.core.core_proxy,
        "isMarketCapacityLocked",
        market_ids,
        calls=calls,
    )
    withdrawable_margin_usds = multicall_erc7412(
        snx,
        snx.core.core_proxy,
        "getWithdrawableMarketUsd",
        market_ids,
        calls=calls,
    )
    market_reported_debts = multicall_erc7412(
        snx,
        snx.core.core_proxy,
        "getMarketReportedDebt",
        market_ids,
        calls=calls,
    )
    market_total_debts = multicall_erc7412(
        snx,
        snx.core.core_proxy,
        "getMarketTotalDebt",
        market_ids,
        calls=calls,
    )

    # make a copy and add data
    market_details = markets.copy()
    market_details["market_name"] = market_names
    market_details["is_capacity_locked"] = is_capacity_lockeds
    market_details["withdrawable_margin_usd"] = [
        wei_to_ether(withdrawable_margin_usd)
        for withdrawable_margin_usd in withdrawable_margin_usds
    ]
    market_details["market_reported_debt"] = [
        wei_to_ether(market_reported_debt)
        for market_reported_debt in market_reported_debts
    ]
    market_details["market_total_debt"] = [
        wei_to_ether(market_total_debts) for market_total_debts in market_total_debts
    ]
    return market_details


@st.cache_data(ttl=300, hash_funcs={Synthetix: lambda x: x.network_id})
def get_market_collateral_details(snx, configs, markets):
    market_collaterals = [
        (market_id, collateral)
        for market_id in markets["market_id"]
        for collateral in configs["token_address"]
    ]

    max_collaterals = multicall_erc7412(
        snx,
        snx.core.core_proxy,
        "getMaximumMarketCollateral",
        market_collaterals,
    )
    collateral_amounts = multicall_erc7412(
        snx,
        snx.core.core_proxy,
        "getMarketCollateralAmount",
        market_collaterals,
    )

    # create the dataframe and filter
    market_details = pd.DataFrame.from_dict(
        {
            market_collateral: {
                "market_id": market_collateral[0],
                "market_name": markets.loc[market_collateral[0], "market_name"],
                "collateral_name": configs.loc[market_collateral[1], "token"],
                "collateral_amount": wei_to_ether(collateral_amount),
                "max_collateral": wei_to_ether(max_collateral),
                "cap_used": (
                    wei_to_ether(collateral_amount) / wei_to_ether(max_collateral)
                    if max_collateral > 0
                    else 0
                ),
            }
            for market_collateral, max_collateral, collateral_amount in zip(
                market_collaterals,
                max_collaterals,
                collateral_amounts,
            )
        },
        orient="index",
    )
    market_details = market_details[market_details["max_collateral"] > 0]

    # change some types to percentages
    market_details["cap_used"] = market_details["cap_used"].map("{:.2%}".format)
    return market_details


# format the configurations
configs = get_configs(st.session_state.snx)

collateral_addresses = configs["token_address"].tolist()
vaults = get_vaults(st.session_state.snx, configs)

perps, spot = get_markets(st.session_state.snx, configs)


# display
st.markdown("### Collateral Configurations")
st.dataframe(configs, hide_index=True)

st.markdown("### Vault Information")
st.dataframe(vaults, hide_index=True)

st.markdown("### Markets")

st.markdown("#### Perps")
st.dataframe(perps, hide_index=True)

if perps.shape[0] > 0:
    st.markdown("#### Perps Market Collateral Details")
    perps_market_details = get_market_collateral_details(
        st.session_state.snx, configs, perps
    )
    st.dataframe(perps_market_details, hide_index=True)


st.markdown("#### Spot")
st.dataframe(spot, hide_index=True)

if spot.shape[0] > 0:
    st.markdown("#### Spot Market Collateral Details")
    spot_market_details = get_market_collateral_details(
        st.session_state.snx, configs, spot
    )
    st.dataframe(spot_market_details, hide_index=True, use_container_width=True)
