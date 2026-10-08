"""
RIO — Team & Roadmap Page
Team members, honest 3-phase development roadmap, FAQ, and pilot proposal.
"""

from __future__ import annotations

import streamlit as st
from rio.ui import credit_block_html

# Optional roles dictionary — team can fill in specific roles later
ROLES: dict[str, str] = {
    # "Raj": "Fullstack / Logic",
    # "Siddhanth": "Product & Research",
    # "Charu": "Design & UI",
    # "Varun": "Operations",
    # "Siya": "Outreach",
}

st.markdown('<div class="rio-content-container">', unsafe_allow_html=True)

# ── 6.1 Team RIO ───────────────────────────────────────────────────────────
st.markdown("# 👥 Team & Roadmap")
st.markdown("### Team RIO &middot; Sharda University")
st.caption("Undergraduate engineering team tackling hyper-local hostel sustainability.")

team_members = ["Raj", "Siddhanth", "Charu", "Varun", "Siya"]
cols = st.columns(len(team_members))

for idx, member in enumerate(team_members):
    with cols[idx]:
        with st.container(border=True):
            st.markdown(f"#### 🎓 {member}")
            role = ROLES.get(member)
            if role:
                st.caption(role)
            st.markdown("<small style='color: #6B7280;'>Sharda University</small>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ── 6.4 Pilot Ask Highlight ────────────────────────────────────────────────
with st.container(border=True):
    p_col1, p_col2 = st.columns([1.2, 2.5])
    with p_col1:
        st.markdown("### 🎯 Pilot Ask")
        st.markdown(
            "<span style='display:inline-block; padding: 4px 12px; background: #FFEDD5; "
            "color: #C2410C; border-radius: 9999px; font-weight: 700; font-size: 0.9rem;'>"
            "One Hostel Block · One Month"
            "</span>",
            unsafe_allow_html=True,
        )
    with p_col2:
        st.markdown(
            "We are requesting approval from hostel administration to run a 30-day trial in "
            "a single residential block during end-of-semester checkout to measure item diversion, "
            "room clearance speed, and staff welfare benefits."
        )

st.markdown("<br>", unsafe_allow_html=True)


# ── 6.2 Honest Roadmap ─────────────────────────────────────────────────────
st.markdown("### 🗺️ Product Roadmap")

r_col1, r_col2, r_col3 = st.columns(3)

with r_col1:
    with st.container(border=True):
        st.markdown("#### 🟢 Prototype (Today)")
        st.markdown(
            """
            - **Simulated Clock**: Interactive time slider with quick jumps.
            - **In-Memory Wallets**: Instant simulation of escrow holds and refunds.
            - **Pure Business Engine**: Isolated Dutch auction and clearance logic.
            - **Warden Dashboard**: Staff queue approval and no-dues tracking.
            """
        )

with r_col2:
    with st.container(border=True):
        st.markdown("#### 🟡 Pilot (Next Step)")
        st.markdown(
            """
            - **Hostel Trial**: 1-month trial run in one hostel block.
            - **Proposed No-Dues**: Student room clearance integrated with hostel office checkout *(proposed)*.
            - **Physical QR Posters**: Pre-printed QR stickers affixed to room doors and bulky furniture.
            - **Staff Handover Protocol**: Direct coordination with housekeeping head.
            """
        )

with r_col3:
    with st.container(border=True):
        st.markdown("#### 🔵 Production (Future)")
        st.markdown(
            """
            - **Real Payments**: UPI/Escrow integration via payment gateway.
            - **Production Backend**: FastAPI service + PostgreSQL persistence.
            - **Video Inspection**: Handover proof recording with hash verification.
            - **Campus Alerts**: Instant WhatsApp and Telegram listing notifications.
            """
        )

st.markdown("<br>", unsafe_allow_html=True)


# ── 6.3 Frequently Asked Questions ─────────────────────────────────────────
st.markdown("### ❓ Frequently Asked Questions")

with st.expander("Why not just OLX or a WhatsApp group?"):
    st.markdown(
        "WhatsApp groups suffer from endless spam, manual haggling, and the fundamental issue that "
        "buyers must haul bulky coolers or mattresses across campus or up flights of stairs. "
        "RIO items **never leave their room**: ownership transfers in-situ, prices decay automatically without haggling, "
        "and unsold assets are guaranteed to support housekeeping staff instead of ending up in junkyards."
    )

with st.expander("What if the item is damaged?"):
    st.markdown(
        "During rentals, a 20% refundable deposit protects the owner (with partial 25% deductions for reported damage). "
        "For sales, buyers inspect the item and scan its QR code before escrow is released to the seller. "
        "Mandatory 5-second video recording and photo timestamping at handover and return are planned for phase 2."
    )

with st.expander("What stops buyers from waiting for the price to drop to the absolute floor?"):
    st.markdown(
        "Two safeguards prevent vulture behavior:\n"
        "1. **Floor Lock**: The Dutch auction hits its floor price 2 hours before the owner departs.\n"
        "2. **Staff Cutoff**: 1 hour before departure, the item vanishes from student search and enters the "
        "exclusive Housekeeping Staff Welfare Pool.\n"
        "3. **Competition**: Live watcher counters inform buyers that other students are watching the same item, "
        "creating urgency to claim before someone else snaps it up."
    )

with st.expander("What if nobody adopts it?"):
    st.markdown(
        "Hostel checkout already mandates a physical room inspection for the 'No-Dues' clearance certificate. "
        "Our pilot proposal integrates RIO into this existing mandatory checkpoint: students cannot get clearance "
        "until bulky items are either claimed, rented, or signed over to the staff welfare pool."
    )

with st.expander("Is the CO₂ data real?"):
    st.markdown(
        "The environmental figures are approximate engineering estimates based on embodied carbon "
        "coefficients for steel, polypropylene, and foam manufacturing, plus avoided transport logistics. "
        "All assumptions (such as the rental substitution factor) are transparent and adjustable in the demo."
    )

with st.expander("Is this using real payments?"):
    st.markdown(
        "No. This prototype uses 100% simulated in-memory balances and ledger transactions. "
        "No real bank accounts, credit cards, or UPI IDs are connected."
    )

st.markdown("<br>", unsafe_allow_html=True)

st.markdown(credit_block_html(), unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
