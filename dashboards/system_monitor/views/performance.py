import streamlit as st
from dashboards.utils import performance

st.markdown("# Query Performance")

if "df_query" not in st.session_state:
    st.session_state.df_query = None


def time_queries():
    results = performance.run_benchmarks(st.session_state.api)

    # create dataframe
    df = performance.create_benchmark_dataframe(results)
    st.session_state.df_query = df


st.button("Run queries", on_click=time_queries)

if st.session_state.df_query is not None:
    st.dataframe(st.session_state.df_query)
