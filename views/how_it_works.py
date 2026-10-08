"""
RIO — How It Works
Deep dive into Dutch auction mechanics, circular lifecycles, and impact math.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from rio.engine import CATEGORIES, RENT_RATES
from rio.ui import auction_curve_figure, fmt_inr, credit_block_html

st.markdown('<div class="rio-content-container">', unsafe_allow_html=True)

# ── Title & Intro ──────────────────────────────────────────────────────────
st.markdown("# 📈 How RIO Works")
st.markdown(
    "RIO solves the end-of-semester bulky asset abandonment crisis by replacing haulage "
    "with room-bound in-situ transfers and manual haggling with automated time-decay Dutch auctions."
)

st.divider()


# ── Full Auction Curve ─────────────────────────────────────────────────────
st.markdown("### 1. The Time-Decay Dutch Auction Formula")
st.markdown(
    "Unlike traditional auctions where bids rise, a Dutch auction begins at the seller's asking price "
    "and decays smoothly toward a floor price as their departure hour approaches. "
    "The first buyer to accept the current price wins instantly."
)

# Interactive alpha slider
col_curve1, col_curve2 = st.columns([1, 2.5])
with col_curve1:
    with st.container(border=True):
        st.markdown("##### 🎛️ Tune Curve Curvature")
        alpha_val = st.slider(
            "α (Decay Exponent)",
            min_value=1.0, max_value=2.5, step=0.1,
            value=float(st.session_state.get("alpha", 1.0)),
            help="1.0 = linear decay; >1.0 = convex curve (holds price longer, drops faster near end)",
        )
        st.caption(
            "$$\\text{Price}(t) = \\text{Floor} + (\\text{Start} - \\text{Floor}) \\cdot (1 - \\tau)^\\alpha$$\n\n"
            "where $\\tau = \\frac{t}{T - 2\\text{h}}$ is normalized elapsed time."
        )

with col_curve2:
    fig = auction_curve_figure(alpha=alpha_val, height=420)
    st.plotly_chart(fig, use_container_width=True)

st.markdown(
    """
    **Key Auction Milestones:**
    - **t = 0h**: Item listed at Start Price (e.g., ₹1,800).
    - **Departure − 2h**: Price decay finishes and locks at the Floor Price (e.g., ₹500).
    - **Departure − 1h**: If still unclaimed, student search ends and item transfers to the **Housekeeping Staff Welfare Pool**.
    """
)

st.divider()


# ── Lifecycle Diagram ──────────────────────────────────────────────────────
st.markdown("### 2. Asset Lifecycle & Handover Pathways")
st.markdown(
    "Items stay bound to their physical Room ID throughout all transitions, eliminating moving trucks, "
    "stairway haulage, and storage locker fees."
)

st.html(
    """<div style="background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;">
    <h4 style="color: #1F2937; margin-top: 0; font-size: 1.15rem; font-weight: 700;">Pathway A: Year-Round Rental Loop</h4>
    <div style="font-family: monospace; font-size: 0.95rem; color: #1E40AF; background: #EFF6FF; padding: 0.75rem 1rem; border-radius: 8px; border-left: 4px solid #3B82F6; margin-bottom: 0.5rem;">
        [Listed in Room] &rarr; [Rented by Peer] &rarr; [Returned with Inspection] &rarr; [Active in Room]
    </div>
    <p style="color: #4B5563; font-size: 0.9rem; margin: 0.5rem 0 1.25rem 0;">
        Students living in the same or nearby rooms rent coolers, tables, and kettles for days, weeks, or months with a 20% refundable deposit.
    </p>

    <h4 style="color: #1F2937; font-size: 1.15rem; font-weight: 700;">Pathway B: In-Situ Ownership Transfer (Escrow & QR)</h4>
    <div style="font-family: monospace; font-size: 0.95rem; color: #9A3412; background: #FFF7ED; padding: 0.75rem 1rem; border-radius: 8px; border-left: 4px solid #F97316; margin-bottom: 0.5rem;">
        [Listed in Room] &rarr; [Claimed & Held in Escrow] &rarr; [Incoming Student QR Scan] &rarr; [Escrow Released to Seller]
    </div>
    <p style="color: #4B5563; font-size: 0.9rem; margin: 0.5rem 0 1.25rem 0;">
        The buyer claims the item at the Dutch price. Funds are secured in escrow until the incoming occupant enters the room and scans the item's QR code.
    </p>

    <h4 style="color: #1F2937; font-size: 1.15rem; font-weight: 700;">Pathway C: Guaranteed Liquidation (Zero Landfill)</h4>
    <div style="font-family: monospace; font-size: 0.95rem; color: #065F46; background: #ECFDF5; padding: 0.75rem 1rem; border-radius: 8px; border-left: 4px solid #10B981; margin-bottom: 0.5rem;">
        [Unsold at Departure &minus; 1h] &rarr; [Staff Welfare Pool] &rarr; [Warden Custody Approval] &rarr; [Housekeeping Staff Gift]
    </div>
    <p style="color: #4B5563; font-size: 0.9rem; margin: 0.5rem 0 0 0;">
        Zero items end up in municipal landfills or hostel junkyards. Campus support staff receive working appliances for their quarters.
    </p>
</div>"""
)

st.divider()


# ── Rental Pricing Rules ───────────────────────────────────────────────────
st.markdown("### 3. Rental Pricing & Rent-to-Own Structure")

rent_col1, rent_col2 = st.columns([1.2, 1])

with rent_col1:
    rental_table = [
        {"Rental Period": "Day (24h)", "Rate (% of Start Price)": "2%", "Example (₹1,800 Cooler)": "₹36"},
        {"Rental Period": "Week (7 days)", "Rate (% of Start Price)": "10%", "Example (₹1,800 Cooler)": "₹180"},
        {"Rental Period": "Month (30 days)", "Rate (% of Start Price)": "25%", "Example (₹1,800 Cooler)": "₹450"},
    ]
    st.table(pd.DataFrame(rental_table).set_index("Rental Period"))

with rent_col2:
    with st.container(border=True):
        st.markdown("##### 🔒 Deposit & Conversion Terms")
        st.markdown(
            """
            - **Refundable Deposit**: Fixed at **20% of start price**, refunded upon non-damaged return.
            - **50% Rent-to-Own Credit**: Half of all cumulative rent paid is credited toward purchase.
            - **Floor Protection**: The converted purchase price is clamped so the seller always receives at least the item's **floor price**.
            """
        )

st.divider()


# ── Impact Math Expander ───────────────────────────────────────────────────
with st.expander("🌱 Impact Math & Carbon Methodology (Click to expand)", expanded=False):
    st.markdown(
        """
        #### CO₂e Avoidance Formulas
        - **Permanent Transfer / Sale**:
          $$\\text{CO}_2\\text{e Avoided (kg)} = \\text{Embodied CO}_2\\text{e} + 2.2\\text{ kg}$$
          *(Embodied footprint of avoiding brand-new manufacture + 2.2 kg avoided delivery vehicle logistics).*
        - **Rental Handover**:
          $$\\text{CO}_2\\text{e Avoided (kg)} = \\text{Embodied CO}_2\\text{e} \\times \\text{Substitution Factor}$$
          *(Default substitution factor is 50%, representing the probability that the student would otherwise have purchased new).*
        """
    )

    st.markdown("#### Category Coefficients Reference Table")
    cat_rows = []
    for cat_name, props in CATEGORIES.items():
        cat_rows.append({
            "Category": cat_name,
            "Tare Weight (kg)": f"{props['tare_kg']} kg",
            "Embodied CO₂e (kg)": f"{props['embodied_co2e']} kg",
            "Default Start Price": fmt_inr(props["default_start"]),
            "Default Floor Price": fmt_inr(props["default_floor"]),
        })
    st.table(pd.DataFrame(cat_rows).set_index("Category"))

    st.caption("All environmental figures are conservative estimates modeled on typical Indian appliance lifecycles.")

st.markdown("<br>", unsafe_allow_html=True)


# ── Page Navigation ────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("#### 🧭 Quick Navigation")
nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    st.page_link("views/landing.py", label="← Back to Home", icon="🏠", use_container_width=True)
with nav_col2:
    st.page_link("views/demo.py", label="Test Live in Demo →", icon="🛠️", use_container_width=True)
with nav_col3:
    st.page_link("views/team.py", label="Team & Roadmap →", icon="👥", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(credit_block_html(), unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
