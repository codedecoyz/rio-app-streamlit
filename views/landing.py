"""
RIO — Landing Page (Home View)
Clean, confident landing page explaining RIO in under 30 seconds.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from rio.engine import aggregate_impact
from rio.ui import (
    fmt_inr, hero_card_html, step_card, lifecycle_chain_html,
    credit_block_html, auction_curve_figure,
)

# ── Problem statistic constant ─────────────────────────────────────────────
REAL_BASELINE = None  # TODO: replace with the warden's real number, e.g. 120 items dumped per hostel per year


# ── 4.1 Hero Section ───────────────────────────────────────────────────────
st.markdown('<div class="rio-content-container">', unsafe_allow_html=True)

hero_col1, hero_col2 = st.columns([1.15, 0.85], gap="large")

with hero_col1:
    st.markdown('<div class="rio-eyebrow">♻️ Circular economy for hostels and PGs</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="rio-hero-title">Nothing moves.<br>Nothing gets dumped.</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="rio-hero-subtitle">'
        'RIO transfers bulky items like coolers, mattresses and study tables between '
        'students in place, with prices that fall automatically and a guaranteed home '
        'for everything unsold.'
        '</p>',
        unsafe_allow_html=True,
    )

    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        st.page_link("views/demo.py", label="Try the live demo →", icon="🚀", use_container_width=True)
    with btn_col2:
        st.page_link("views/how_it_works.py", label="See how it works", icon="📈", use_container_width=True)

with hero_col2:
    st.markdown(hero_card_html(), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ── 4.2 The Problem in One Number ──────────────────────────────────────────
with st.container(border=True):
    if REAL_BASELINE is not None:
        st.markdown(
            f"### 🚪 {REAL_BASELINE} bulky items are dumped from one hostel every year."
        )
        st.caption("When moving out, haulage costs exceed asset value. RIO keeps the value in place.")
    else:
        st.markdown(
            "### 🚪 Every semester end, coolers, mattresses and tables are left behind because moving them costs more than they are worth."
        )
        st.caption("Abandonment is a logistics failure, not a lack of student demand.")


st.markdown("<br>", unsafe_allow_html=True)


# ── 4.3 Three-step "How it works" ──────────────────────────────────────────
st.markdown("### ⚡ Three Steps to Zero Hostel Waste")
scol1, scol2, scol3 = st.columns(3)

with scol1:
    st.markdown(
        step_card(
            "📍",
            "1. List in place",
            "Owners list an item once. It stays in its room with zero haulage — the next occupant simply scans in.",
        ),
        unsafe_allow_html=True,
    )

with scol2:
    st.markdown(
        step_card(
            "📉",
            "2. Price falls on its own",
            "A Dutch auction lowers the price smoothly toward a floor as departure nears. Zero awkward haggling.",
        ),
        unsafe_allow_html=True,
    )

with scol3:
    st.markdown(
        step_card(
            "🛡️",
            "3. Nothing is dumped",
            "Unsold items transfer free to campus support staff one hour before departure. Vulture-proof by design.",
        ),
        unsafe_allow_html=True,
    )


st.markdown("<br>", unsafe_allow_html=True)


# ── 4.4 Rent, Then Own (Retention Feature) ─────────────────────────────────
st.markdown("### 🔑 Year-Round Circularity")
st.markdown(lifecycle_chain_html(), unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; color: #4B5563; font-weight: 500; font-size: 0.95rem;'>"
    "Students use RIO all year, not only at move-out."
    "</p>",
    unsafe_allow_html=True,
)


st.markdown("<br>", unsafe_allow_html=True)


# ── 4.5 Live Impact Counters ───────────────────────────────────────────────
st.markdown("### 📊 Live Campus Impact")

items = st.session_state.get("items", [])
txns = st.session_state.get("transactions", [])
rents = st.session_state.get("rentals", [])
sub_rate = st.session_state.get("substitution_rate", 0.5)

impact = aggregate_impact(items, txns, rents, sub_rate)

mcol1, mcol2, mcol3, mcol4 = st.columns(4)
with mcol1:
    st.metric("♻️ Items kept from landfill", impact["items_diverted"])
with mcol2:
    st.metric("⚖️ Waste diverted", f"{impact['waste_diverted_kg']:.1f} kg")
with mcol3:
    st.metric("🌱 CO₂e avoided", f"{impact['co2_avoided_kg']:.1f} kg")
with mcol4:
    st.metric("💰 Rental income earned", fmt_inr(impact["rental_income"]))

st.caption(
    "⚠️ *Estimates based on approximate embodied carbon ranges; assumptions adjustable in the demo.*"
)


st.markdown("<br>", unsafe_allow_html=True)


# ── 4.6 Mini Auction Curve Preview ─────────────────────────────────────────
st.markdown("### 📉 The Time-Decay Dutch Auction")
st.caption(
    "Automatic price discovery eliminates back-and-forth haggling. "
    "The floor is hit 2 hours before departure; unsold items route to staff 1 hour before departure."
)

fig = auction_curve_figure(alpha=st.session_state.get("alpha", 1.0), height=320)
st.plotly_chart(fig, use_container_width=True)


st.markdown("<br>", unsafe_allow_html=True)


# ── 4.7 Why not OLX or WhatsApp? ───────────────────────────────────────────
st.markdown("### ⚖️ Why Not OLX or WhatsApp Groups?")

comp_data = {
    "Dimension": ["Asset Location", "Pricing Mechanism", "Unsold Items"],
    "OLX / WhatsApp Groups": [
        "Buyer must physically haul bulky item across campus",
        "Awkward manual haggling; buyers stall until the last minute",
        "Abandoned in hallway or dumped in hostel junkyard",
    ],
    "RIO (Circular Handover)": [
        "In-situ transfer: item stays bound to Room ID, zero moving",
        "Deterministic Dutch auction: price decays automatically toward floor",
        "Guaranteed handover: automatically routed to campus housekeeping staff",
    ],
}
df_comp = pd.DataFrame(comp_data)
st.dataframe(
    df_comp.set_index("Dimension"),
    use_container_width=True,
)


st.markdown("<br><br>", unsafe_allow_html=True)


# ── 4.8 Closing Call to Action & Credit Footer ─────────────────────────────
st.markdown(
    "<div style='text-align: center; margin-bottom: 1rem;'>"
    "<h3 style='margin-bottom: 0.25rem;'>Ready to explore?</h3>"
    "<p style='color: #6B7280; font-size: 0.95rem;'>Experience the live simulation, review the auction mechanics, or meet the team.</p>"
    "</div>",
    unsafe_allow_html=True,
)

nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    st.page_link("views/demo.py", label="Try the Live Demo →", icon="🛠️", use_container_width=True)
with nav_col2:
    st.page_link("views/how_it_works.py", label="How It Works →", icon="📈", use_container_width=True)
with nav_col3:
    st.page_link("views/team.py", label="Team & Roadmap →", icon="👥", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(credit_block_html(), unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
