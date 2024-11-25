import streamlit as st
from dashboards.all_metrics.modules.v3 import (
    chain_core_stats,
)

st.session_state.chain = "eth_mainnet"

modules = {
    "LP": chain_core_stats.main,
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
