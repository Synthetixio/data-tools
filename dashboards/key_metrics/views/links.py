import streamlit as st
from dashboards.utils.display import display_cards

BASE_URL = "https://stats.synthetix.io"

# card configs
perps_cards = [
    {
        "title": "Base Perps",
        "text": "Synthetix V3 Perps on Base",
        "url": f"{BASE_URL}/all?page=base&module=Perps",
    },
    {
        "title": "Arbitrum Perps",
        "text": "Synthetix V3 Perps on Arbitrum",
        "url": f"{BASE_URL}/all?page=arbitrum&module=Perps",
    },
    {
        "title": "V2 Perps",
        "text": "Synthetix V2 Perps on Optimism",
        "url": f"{BASE_URL}/all?page=optimism&module=Perps%20V2",
    },
]

lp_cards = [
    {
        "title": "Base LP",
        "text": "Synthetix V3 liquidity pools on Base",
        "url": f"{BASE_URL}/all?page=base&module=LP",
    },
    {
        "title": "Arbitrum LP",
        "text": "Synthetix V3 liquidity pools on Arbitrum",
        "url": f"{BASE_URL}/all?page=arbitrum&module=LP",
    },
    {
        "title": "Ethereum LP",
        "text": "Synthetix V3 liquidity pools on Ethereum",
        "url": f"{BASE_URL}/all?page=ethereum&module=LP",
    },
]

community_cards = [
    {
        "title": "Watcher",
        "text": "Real-time dashboard monitoring Synthetix Perps",
        "url": "https://dune.com/synthetix_community/synthetix-stats",
    },
    {
        "title": "Dune",
        "text": "Dune dashboards maintained by the community",
        "url": "https://dune.com/synthetix_community/synthetix-stats",
    },
]

st.markdown("# Perps")
display_cards(perps_cards)

st.markdown("# LPs")
display_cards(lp_cards)

st.markdown("# Community")
display_cards(community_cards)
