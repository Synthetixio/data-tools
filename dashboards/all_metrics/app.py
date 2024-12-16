import streamlit as st
from dashboards.utils.display import sidebar_logo, sidebar_icon
from api.internal_api import SynthetixAPI, get_db_config

st.set_page_config(
    page_title="Synthetix Stats - All",
    page_icon="dashboards/static/favicon.ico",
    layout="wide",
)
sidebar_logo()
sidebar_icon()

hide_footer = """
    <style>
        footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_footer, unsafe_allow_html=True)


# set the API
@st.cache_resource
def load_api():
    DB_ENV = st.secrets.database.DB_ENV
    return SynthetixAPI(db_config=get_db_config(streamlit=True), environment=DB_ENV)


st.session_state.api = load_api()

# pages
all_chains = st.Page("views/all_chains.py", title="Synthetix V3")
ethereum = st.Page("views/ethereum.py", title="Ethereum")
base = st.Page("views/base.py", title="Base")
arbitrum = st.Page("views/arbitrum.py", title="Arbitrum")
optimism = st.Page("views/optimism.py", title="Optimism")
links = st.Page("../key_metrics/views/links.py", title="Links")


# navigation
pages = {
    "": [all_chains, ethereum, base, arbitrum, optimism, links],
}
nav = st.navigation(pages)
nav.run()
