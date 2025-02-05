import os
import streamlit as st
from synthetix import Synthetix
from api.internal_api import SynthetixAPI, get_db_config
from dashboards.utils.providers import get_provider_url

# constants
ALCHEMY_KEY = st.secrets.settings.WEB3_ALCHEMY_API_KEY

NETWORK_CONFIGS = {
    1: {
        "network_id": 1,
        "network_name": "Ethereum Mainnet",
        "provider_rpc": get_provider_url(1),
    },
    10: {
        "network_id": 10,
        "network_name": "Optimism Mainnet",
        "provider_rpc": get_provider_url(10),
    },
    8453: {
        "network_id": 8453,
        "network_name": "Base Mainnet",
        "provider_rpc": get_provider_url(8453),
    },
    42161: {
        "network_id": 42161,
        "network_name": "Arbitrum Mainnet",
        "provider_rpc": get_provider_url(42161),
    },
    11155111: {
        "network_id": 11155111,
        "network_name": "Ethereum Sepolia",
        "provider_rpc": get_provider_url(11155111),
    },
    84532: {
        "network_id": 84532,
        "network_name": "Base Sepolia",
        "provider_rpc": get_provider_url(84532),
    },
    421614: {
        "network_id": 421614,
        "network_name": "Arbitrum Sepolia",
        "provider_rpc": get_provider_url(421614),
    },
}


# set the API
@st.cache_resource
def load_api():
    return SynthetixAPI(db_config=get_db_config(streamlit=True))


@st.cache_resource(ttl=3600)
def load_snx(network_id=8453):
    provider_rpc = NETWORK_CONFIGS[network_id]["provider_rpc"]
    return Synthetix(
        provider_rpc=provider_rpc,
    )


def settings(enabled_markets=NETWORK_CONFIGS.keys()):
    networks = list(NETWORK_CONFIGS.keys())
    networks = [network for network in networks if network in enabled_markets]

    # select the network
    network_id = st.selectbox(
        "Network",
        options=networks,
        format_func=lambda x: NETWORK_CONFIGS[x]["network_name"],
    )

    # save the network
    st.session_state.network_id = network_id

    # initialize the values
    st.session_state.api = load_api()
    st.session_state.snx = load_snx(st.session_state.network_id)
