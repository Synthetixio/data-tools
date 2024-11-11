import streamlit as st
import base64
from pathlib import Path
import urllib.parse
from streamlit_card import card


def sidebar_logo():
    LOGO_URL = "dashboards/static/logo.svg"
    HEIGHT = 28

    # Read SVG and convert to base64
    svg = Path(LOGO_URL).read_text()
    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")

    # Create the URL format for background-image
    logo = f"url(data:image/svg+xml;base64,{b64})"

    st.html(
        f"""
        <style>
            [data-testid="stSidebarHeader"] {{
                background-image: {logo};
                background-repeat: no-repeat;
                padding-top: {HEIGHT - 10}px;
                background-position: 20px 20px;
                background-size: auto {HEIGHT}px;
            }}
        </style>
        """,
    )


def sidebar_icon():
    burger_svg = """%3Csvg%20width%3D%2718%27%20height%3D%2715%27%20viewBox%3D%270%200%2018%2015%27%20fill%3D%27none%27%20xmlns%3D%27http%3A//www.w3.org/2000/svg%27%3E%20%3Cpath%20d%3D%27M0.512695%201.31128C0.512695%200.897066%200.848482%200.561279%201.2627%200.561279H16.2627C16.6769%200.561279%2017.0127%200.897066%2017.0127%201.31128C17.0127%201.72549%2016.6769%202.06128%2016.2627%202.06128H1.2627C0.848482%202.06128%200.512695%201.72549%200.512695%201.31128Z%27%20fill%3D%27white%27/%3E%20%3Cpath%20d%3D%27M0.512695%207.31128C0.512695%206.89707%200.848482%206.56128%201.2627%206.56128H16.2627C16.6769%206.56128%2017.0127%206.89707%2017.0127%207.31128C17.0127%207.72549%2016.6769%208.06128%2016.2627%208.06128H1.2627C0.848482%208.06128%200.512695%207.72549%200.512695%207.31128Z%27%20fill%3D%27white%27/%3E%20%3Cpath%20d%3D%27M1.2627%2012.5613C0.848482%2012.5613%200.512695%2012.8971%200.512695%2013.3113C0.512695%2013.7255%200.848482%2014.0613%201.2627%2014.0613H16.2627C16.6769%2014.0613%2017.0127%2013.7255%2017.0127%2013.3113C17.0127%2012.8971%2016.6769%2012.5613%2016.2627%2012.5613H1.2627Z%27%20fill%3D%27white%27/%3E%20%3C/svg%3E%20%20%20%20%20"""
    custom_css = f"""
    <style>
        [data-testid="stSidebarCollapseButton"] button svg {{
            display: none;
        }}
        
        [data-testid="stSidebarCollapseButton"] button::after {{
            content: '';
            display: block;
            width: 24px;
            height: 24px;
            background-image: url("data:image/svg+xml,{burger_svg}");
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center center;
        }}

        [data-testid="stSidebarCollapsedControl"] button svg {{
            display: none;
        }}
        
        [data-testid="stSidebarCollapsedControl"] button::after {{
            content: '';
            display: block;
            width: 24px;
            height: 24px;
            background-image: url("data:image/svg+xml,{burger_svg}");
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center center;
        }}
        
    </style>
    """
    st.html(custom_css)


def display_cards(card_configs, width=3):
    """Display a list of cards in a grid layout, with a specified width."""
    cols = st.columns(width)
    for i, card_config in enumerate(card_configs):
        with cols[i % width]:
            card(
                **card_config,
                styles={
                    "card": {
                        "width": "100%",
                        "margin": "0px",
                        "background-color": "#1A1A5A",
                    }
                },
            )
