import os
import streamlit as st


# constants
ALCHEMY_KEY = st.secrets.settings.WEB3_ALCHEMY_API_KEY

ALCHEMY_NETWORK_SLUGS = {
    1: "eth-mainnet",
    10: "optimism-mainnet",
    8453: "base-mainnet",
    42161: "arb-mainnet",
    11155111: "eth-sepolia",
    84532: "base-sepolia",
    421614: "arb-sepolia",
}


def get_provider_url(network_id):
    # first check if the network_id has an environment variable named like NETWORK_{network_id}_RPC
    env_var = f"NETWORK_{network_id}_RPC"
    if env_var in st.secrets.rpcs:
        print(f"Getting {network_id} RPC from secrets")
        return st.secrets.rpcs[env_var]
    else:
        # make an alchemy url
        print(f"Getting {network_id} RPC from alchemy")
        if network_id not in ALCHEMY_NETWORK_SLUGS:
            raise ValueError(f"Network {network_id} not supported")
        return f"https://{ALCHEMY_NETWORK_SLUGS[network_id]}.g.alchemy.com/v2/{ALCHEMY_KEY}"
