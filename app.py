"""
RIO: Circular Asset Handover — Multipage Router
Configures page metadata, initializes state once, and routes pages via st.navigation.
"""

import streamlit as st
from rio.data import init_state
from rio.ui import inject_css

st.set_page_config(
    page_title="RIO | Nothing moves. Nothing gets dumped.",
    page_icon="♻️",
    layout="wide",
)

init_state()
inject_css()

pages = [
    st.Page("views/landing.py", title="Home", icon="🏠", default=True),
    st.Page("views/demo.py", title="Live demo", icon="🛠️"),
    st.Page("views/how_it_works.py", title="How it works", icon="📈"),
    st.Page("views/team.py", title="Team & roadmap", icon="👥"),
]

st.navigation(pages).run()
