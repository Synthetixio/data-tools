import streamlit as st
from dashboards.utils.display import sidebar_logo, sidebar_icon
from api.internal_api import SynthetixAPI, get_db_config

st.set_page_config(
    page_title="Synthetix Stats",
    page_icon=f"dashboards/static/favicon.ico",
    layout="wide",
)
sidebar_logo()
sidebar_icon()

hide_footer = """
    <style>
        footer {visibility: hidden;}

        div[class^="_stateContainer"] > * {
            display: none !important;
        }
        div[class^="_stateContainer"] iframe {
            display: block !important;
        }
    </style>
"""
st.markdown(hide_footer, unsafe_allow_html=True)


# set the API
@st.cache_resource
def load_api():
    return SynthetixAPI(db_config=get_db_config(streamlit=True))


st.session_state.api = load_api()

# pages
cross_chain = st.Page("views/cross_chain.py", title="Synthetix Test")
lp = st.Page("views/lp.py", title="Liquidity Providers")
perps = st.Page("views/perps.py", title="Perps")
token = st.Page("views/token.py", title="SNX Token")
v2 = st.Page("views/v2.py", title="Synthetix V2")
accounts = st.Page("views/accounts.py", title="Accounts Activity")
links = st.Page("views/links.py", title="Links")

# navigation
pages = {
    "": [cross_chain, lp, perps, token, v2, links],
}
nav = st.navigation(pages)
nav.run()
