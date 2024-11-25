import streamlit as st
from dashboards.all_metrics.modules.v3 import (
    chain_core_stats,
    chain_perp_stats,
    chain_perp_markets,
    chain_perp_monitor,
    chain_perp_integrators,
    chain_perp_keepers,
    chain_perp_account,
    chain_spot_markets,
)

st.session_state.chain = "base_mainnet"

modules = {
    "LP": chain_core_stats.main,
    "Perps": chain_perp_stats.main,
    "Perps Markets": chain_perp_markets.main,
    "Perps Monitor": chain_perp_monitor.main,
    "Perps Integrators": chain_perp_integrators.main,
    "Perps Keepers": chain_perp_keepers.main,
    "Perps Account": chain_perp_account.main,
    "Spot": chain_spot_markets.main,
}

module_query = st.query_params["module"] if "module" in st.query_params else None
state_module = st.sidebar.radio(
    "All Chains",
    tuple(modules.keys()),
    index=(
        tuple(modules.keys()).index(module_query)
        if module_query and module_query in modules.keys()
        else 0
    ),
)
modules[state_module]()
