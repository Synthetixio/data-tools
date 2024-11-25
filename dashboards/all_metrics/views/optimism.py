import streamlit as st
from dashboards.all_metrics.modules.v2 import (
    perp_stats,
    perp_monitor,
    perp_markets,
    perp_integrators,
)

st.session_state.chain = "optimism_mainnet"

modules = {
    "Perps V2": perp_stats.main,
    "Perps V2 Monitor": perp_monitor.main,
    "Perps V2 Markets": perp_markets.main,
    "Perps V2 Integrators": perp_integrators.main,
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
