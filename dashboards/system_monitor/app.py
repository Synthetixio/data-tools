from dotenv import load_dotenv
import streamlit as st
from api.internal_api import SynthetixAPI, get_db_config

load_dotenv()

if "network_id" not in st.session_state:
    st.session_state.network_id = 1


st.set_page_config(
    page_title="Synthetix System Monitor",
    page_icon="dashboards/static/favicon.ico",
    layout="wide",
)

hide_footer = """
    <style>
        footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_footer, unsafe_allow_html=True)


# set the API
@st.cache_resource
def load_api():
    return SynthetixAPI(db_config=get_db_config(streamlit=True))


st.session_state.api = load_api()

# pages
core = st.Page("views/core.py", title="Core System")
perps = st.Page("views/perps.py", title="Perps Markets")
performance = st.Page("views/performance.py", title="Query Performance")
depth = st.Page("views/depth.py", title="Market Depth")

# navigation
pages = {
    "": [core, perps, performance, depth],
}
nav = st.navigation(pages)
nav.run()
