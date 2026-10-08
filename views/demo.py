"""
RIO: Circular Asset Handover — Live Demo View
Sidebar controls, 4 interactive tabs, and full simulation flows.
"""

from __future__ import annotations

import hashlib
from typing import Any

import streamlit as st
import pandas as pd

from rio.engine import (
    CATEGORIES, RENT_RATES, dutch_price, effective_status, urgency_badge,
    hours_remaining, watchers_count, can_claim, validate_listing,
    can_rent_departing, rental_cost, rental_deposit, rent_to_own_price,
    aggregate_impact, unresolved_items, DECAY_END_BEFORE_DEPARTURE,
    STAFF_CUTOFF_BEFORE_DEPARTURE,
)
from rio.ui import (
    fmt_inr, sim_hour_display, badge_html, location_badge,
    render_item_card, render_qr_code, render_summary_strip,
    chart_co2_by_category, chart_utilization, chart_status_breakdown,
    chart_cumulative_co2,
)


# ── Convenience accessors ─────────────────────────────────────────────────

def get_items() -> list[dict]:
    return st.session_state["items"]

def get_users() -> dict[str, dict]:
    return st.session_state["users"]

def get_txns() -> list[dict]:
    return st.session_state["transactions"]

def get_rents() -> list[dict]:
    return st.session_state["rentals"]

def get_current_user() -> str:
    return st.session_state["current_user"]

def get_sim_hour() -> int:
    return st.session_state["sim_hour"]

def get_alpha() -> float:
    return st.session_state["alpha"]

def get_user_obj() -> dict:
    return get_users()[get_current_user()]

def is_warden() -> bool:
    return get_current_user() == "Warden"

def student_names() -> list[str]:
    return [u for u, d in get_users().items() if d["role"] == "student"]


# ── Sidebar (Demo Controls only) ──────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🛠️ Demo Controls")
    st.caption("RIO live simulation environment")

    # Viewing as
    viewer_options = student_names() + ["Warden"]
    cu = get_current_user()
    viewer_idx = viewer_options.index(cu) if cu in viewer_options else 0
    selected_viewer = st.selectbox(
        "👤 Viewing as",
        viewer_options,
        index=viewer_idx,
        key="viewer_select",
    )
    if selected_viewer != get_current_user():
        st.session_state["current_user"] = selected_viewer

    st.divider()

    # Simulated clock
    sim_h = st.slider(
        "⏰ Simulated time (hours since listing)",
        min_value=0, max_value=336, step=1,
        value=get_sim_hour(),
        key="sim_slider",
    )
    st.session_state["sim_hour"] = sim_h
    st.caption(f"🕐 {sim_hour_display(sim_h)}")

    # Demo mode expander
    with st.expander("🎬 Demo quick-jumps"):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Just listed (0h)", use_container_width=True):
                st.session_state["sim_hour"] = 0
                st.rerun()
            if st.button("Final 24h", use_container_width=True):
                st.session_state["sim_hour"] = 144
                st.rerun()
        with col2:
            if st.button("Mid-auction", use_container_width=True):
                st.session_state["sim_hour"] = 84
                st.rerun()
            if st.button("Past staff cutoff", use_container_width=True):
                st.session_state["sim_hour"] = 167
                st.rerun()

        st.markdown("##### 2-Minute Demo Script")
        st.checkbox("1. Show marketplace at t=0", key="_demo1")
        st.checkbox("2. Slide time → see prices drop", key="_demo2")
        st.checkbox("3. Claim an item → check wallet", key="_demo3")
        st.checkbox("4. Rent an item → return it", key="_demo4")
        st.checkbox("5. Rent-to-own conversion", key="_demo5")
        st.checkbox("6. Slide to final hour → staff pool", key="_demo6")
        st.checkbox("7. Show Warden dashboard", key="_demo7")
        st.checkbox("8. List a new item", key="_demo8")

    # Advanced settings
    with st.expander("⚙️ Advanced settings"):
        st.session_state["alpha"] = st.slider(
            "α (decay curve exponent)",
            min_value=1.0, max_value=2.5, step=0.1,
            value=get_alpha(),
            key="alpha_slider",
        )
        st.session_state["substitution_rate"] = st.slider(
            "Rental substitution rate",
            min_value=0.0, max_value=1.0, step=0.05,
            value=st.session_state["substitution_rate"],
            key="sub_rate_slider",
            help="Share of rentals that replace buying new (for CO₂ estimates)",
        )

    st.divider()

    # Wallet display for students
    if not is_warden():
        uo = get_user_obj()
        st.metric("💰 Wallet", fmt_inr(uo["wallet"]))
        if uo.get("departure_hour"):
            hr = hours_remaining(uo["departure_hour"], get_sim_hour())
            if hr is not None:
                st.caption(f"🚪 Departing in {hr:.0f}h ({sim_hour_display(uo['departure_hour'])})")

    # Reset
    if st.button("🔄 Reset demo", use_container_width=True, type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ── Header ─────────────────────────────────────────────────────────────────
st.markdown("# 🛠️ RIO Live Prototype Demo")
st.markdown("*Experience in-situ transfers, time-decay Dutch auctions, and rental lifecycles live.*")
render_summary_strip(get_items(), get_rents(), st.session_state["substitution_rate"])


# ── Tabs ───────────────────────────────────────────────────────────────────
tab_market, tab_rent, tab_activity, tab_dashboard = st.tabs(
    ["🛒 Marketplace", "🔑 Rent", "📋 My Activity", "📊 Dashboard"]
)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 1: MARKETPLACE
# ═══════════════════════════════════════════════════════════════════════════

with tab_market:
    sh = get_sim_hour()
    al = get_alpha()
    cu = get_current_user()

    # Count staff-reserve items for banner
    staff_pool_count = sum(
        1 for it in get_items()
        if effective_status(it, sh) == "STAFF_RESERVE"
    )
    if staff_pool_count > 0:
        st.info(
            f"🛡️ **{staff_pool_count} item(s) entered the staff welfare pool.** "
            f"Vulture-proof by design — these items support campus housekeeping staff.",
            icon="🛡️",
        )

    # Filters
    fcol1, fcol2, fcol3 = st.columns([2, 2, 2])
    with fcol1:
        cat_filter = st.selectbox(
            "Category", ["All"] + list(CATEGORIES.keys()), key="mkt_cat"
        )
    with fcol2:
        blocks = sorted(set(it["block"] for it in get_items()))
        block_filter = st.selectbox("Location", ["All"] + blocks, key="mkt_block")
    with fcol3:
        sort_by = st.selectbox("Sort by", ["Price (low→high)", "Time remaining"], key="mkt_sort")

    # Filter items
    available = []
    for it in get_items():
        eff = effective_status(it, sh)
        if eff not in ("ACTIVE",):
            continue
        if it["owner"] == cu:
            continue
        if it.get("departure_hour") is None:
            continue  # keeper items shown in Rent tab
        if cat_filter != "All" and it["category"] != cat_filter:
            continue
        if block_filter != "All" and it["block"] != block_filter:
            continue
        available.append(it)

    # Sort
    def sort_key(it: dict) -> Any:
        p = dutch_price(it["start_price"], it["floor_price"],
                        it["listed_hour"], it["departure_hour"], sh, al)
        hr = hours_remaining(it["departure_hour"], sh)
        if sort_by == "Price (low→high)":
            return p
        return hr if hr is not None else 9999

    available.sort(key=sort_key)

    if not available:
        st.markdown(
            "### 🍃 No items available right now\n"
            "Check back later or list your own items in **My Activity**!"
        )
    else:
        # Render in 2-column grid
        cols = st.columns(2)
        for idx, it in enumerate(available):
            with cols[idx % 2]:
                render_item_card(it, sh, al)
                price = dutch_price(
                    it["start_price"], it["floor_price"],
                    it["listed_hour"], it["departure_hour"], sh, al,
                )

                # If rented, show first-refusal message
                if it["status"] == "RENTED":
                    st.warning("🔒 Rented — renter has right of first refusal.")
                elif not is_warden():
                    if st.button(
                        f"🤝 Claim in-situ · {fmt_inr(price)}",
                        key=f"claim_{it['id']}",
                        use_container_width=True,
                        type="primary",
                    ):
                        ok, msg = can_claim(cu, it, get_items(), get_user_obj()["wallet"], price)
                        if not ok:
                            st.error(msg)
                        else:
                            # Execute claim
                            it["status"] = "CLAIMED_ESCROW"
                            it["buyer"] = cu
                            it["settled_price"] = price
                            get_user_obj()["wallet"] -= price
                            get_txns().append({
                                "hour": sh, "type": "ESCROW_HOLD",
                                "user": cu, "amount": -price,
                                "note": f"Escrow for '{it['title']}'",
                                "item_id": it["id"],
                            })
                            st.toast(f"✅ Claimed '{it['title']}' for {fmt_inr(price)}!")
                            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2: RENT
# ═══════════════════════════════════════════════════════════════════════════

with tab_rent:
    sh = get_sim_hour()
    al = get_alpha()
    cu = get_current_user()

    st.markdown("### 🔑 Available for Rent")
    st.caption("Rent items all year. Rent-to-own credit available on departing items.")

    # Rentable items (ACTIVE + rentable, not owned by current user)
    rentable = []
    for it in get_items():
        eff = effective_status(it, sh)
        if eff not in ("ACTIVE",):
            continue
        if not it.get("rentable"):
            continue
        if it["owner"] == cu:
            continue
        rentable.append(it)

    # Also show RENTED items (to show first-refusal)
    rented_items = []
    for it in get_items():
        eff = effective_status(it, sh)
        if eff == "RENTED" and it.get("renter") != cu and it["owner"] != cu:
            rented_items.append(it)

    # Show currently rented by this user
    my_rentals = []
    for it in get_items():
        if it["status"] == "RENTED" and it.get("renter") == cu:
            my_rentals.append(it)

    if my_rentals:
        st.markdown("#### 📦 Items You're Renting")
        for it in my_rentals:
            with st.container(border=True):
                cat_info = CATEGORIES.get(it["category"], {})
                emoji = cat_info.get("emoji", "📦")
                st.markdown(f"**{emoji} {it['title']}**")
                st.markdown(
                    location_badge(it["block"], it["room"]),
                    unsafe_allow_html=True,
                )

                # Find rental record
                rental_rec = None
                for r in get_rents():
                    if (r["item_id"] == it["id"] and r["renter"] == cu
                            and not r.get("completed")):
                        rental_rec = r
                        break

                bcol1, bcol2, bcol3 = st.columns(3)
                with bcol1:
                    if st.button("↩️ Return item", key=f"return_{it['id']}",
                                 use_container_width=True):
                        # Refund deposit
                        if rental_rec:
                            get_user_obj()["wallet"] += rental_rec["deposit"]
                            get_txns().append({
                                "hour": sh, "type": "DEPOSIT_REFUND",
                                "user": cu, "amount": rental_rec["deposit"],
                                "note": f"Deposit refund for '{it['title']}'",
                                "item_id": it["id"],
                            })
                            rental_rec["completed"] = True
                        it["status"] = "ACTIVE"
                        it["renter"] = None
                        st.toast(f"✅ Returned '{it['title']}'. Deposit refunded!")
                        st.rerun()
                with bcol2:
                    if st.button("⚠️ Return w/ damage", key=f"damage_{it['id']}",
                                 use_container_width=True):
                        if rental_rec:
                            deduction = round(rental_rec["deposit"] * 0.25)
                            refund = rental_rec["deposit"] - deduction
                            get_user_obj()["wallet"] += refund
                            # Credit owner
                            get_users()[it["owner"]]["wallet"] += deduction
                            get_txns().append({
                                "hour": sh, "type": "DEPOSIT_PARTIAL_REFUND",
                                "user": cu, "amount": refund,
                                "note": f"Partial deposit (damage) for '{it['title']}'",
                                "item_id": it["id"],
                            })
                            get_txns().append({
                                "hour": sh, "type": "DAMAGE_CREDIT",
                                "user": it["owner"], "amount": deduction,
                                "note": f"Damage deduction from {cu}",
                                "item_id": it["id"],
                            })
                            rental_rec["completed"] = True
                        it["status"] = "ACTIVE"
                        it["renter"] = None
                        st.toast(f"⚠️ Returned with damage. 25% deposit deducted.")
                        st.rerun()
                with bcol3:
                    # Rent-to-own (only for departing items)
                    if it.get("departure_hour") is not None:
                        total_rent = sum(
                            r["rent_paid"] for r in get_rents()
                            if r["item_id"] == it["id"] and r["renter"] == cu
                        )
                        curr_price = dutch_price(
                            it["start_price"], it["floor_price"],
                            it["listed_hour"], it["departure_hour"], sh, al,
                        )
                        buy_p, credit, _ = rent_to_own_price(
                            curr_price, it["floor_price"], total_rent,
                        )
                        st.caption(
                            f"Price {fmt_inr(curr_price)} − credit {fmt_inr(credit)} = "
                            f"**{fmt_inr(buy_p)}** (floor {fmt_inr(it['floor_price'])})"
                        )
                        if st.button(
                            f"🏠 Convert to buy · {fmt_inr(buy_p)}",
                            key=f"rto_{it['id']}",
                            use_container_width=True,
                            type="primary",
                        ):
                            if get_user_obj()["wallet"] < buy_p:
                                st.error(f"Insufficient balance. Need {fmt_inr(buy_p)}.")
                            else:
                                # Refund deposit first
                                if rental_rec:
                                    get_user_obj()["wallet"] += rental_rec["deposit"]
                                    rental_rec["completed"] = True
                                # Then charge buy price
                                get_user_obj()["wallet"] -= buy_p
                                get_users()[it["owner"]]["wallet"] += buy_p
                                it["status"] = "SETTLED"
                                it["buyer"] = cu
                                it["renter"] = None
                                it["settled_price"] = buy_p
                                get_txns().append({
                                    "hour": sh, "type": "RENT_TO_OWN",
                                    "user": cu, "amount": -buy_p,
                                    "note": f"Rent-to-own '{it['title']}' (credit {fmt_inr(credit)})",
                                    "item_id": it["id"],
                                })
                                get_txns().append({
                                    "hour": sh, "type": "SALE",
                                    "user": it["owner"], "amount": buy_p,
                                    "note": f"Rent-to-own sale to {cu}",
                                    "item_id": it["id"],
                                })
                                st.toast(f"🏠 Converted to purchase! Deposit refunded, paid {fmt_inr(buy_p)}.")
                                st.rerun()

        st.divider()

    # Available for rent
    if not rentable and not rented_items:
        st.markdown("### 🍃 No items available for rent right now.")
    else:
        cols = st.columns(2)
        all_rent_display = rentable + rented_items
        for idx, it in enumerate(all_rent_display):
            with cols[idx % 2]:
                render_item_card(it, sh, al)

                if it["status"] == "RENTED":
                    renter_name = it.get("renter", "someone")
                    st.warning(f"🔒 Rented by {renter_name} — renter has first refusal.")
                elif not is_warden():
                    with st.expander("📋 Rental options"):
                        for period, info in RENT_RATES.items():
                            cost = rental_cost(it["start_price"], period)
                            dep = rental_deposit(it["start_price"])
                            can, reason = can_rent_departing(
                                it.get("departure_hour"), sh, period,
                            )

                            label = f"{period}: {fmt_inr(cost)} + {fmt_inr(dep)} deposit"
                            if st.button(
                                label,
                                key=f"rent_{it['id']}_{period}",
                                disabled=not can,
                                help=reason if not can else None,
                                use_container_width=True,
                            ):
                                total_charge = cost + dep
                                if get_user_obj()["wallet"] < total_charge:
                                    st.error(
                                        f"Insufficient balance. Need {fmt_inr(total_charge)}, "
                                        f"have {fmt_inr(get_user_obj()['wallet'])}."
                                    )
                                else:
                                    # Execute rental
                                    get_user_obj()["wallet"] -= total_charge
                                    get_users()[it["owner"]]["wallet"] += cost
                                    it["status"] = "RENTED"
                                    it["renter"] = cu
                                    rid = f"rental_{st.session_state['next_rental_id']:03d}"
                                    st.session_state["next_rental_id"] += 1
                                    get_rents().append({
                                        "id": rid,
                                        "item_id": it["id"],
                                        "renter": cu,
                                        "owner": it["owner"],
                                        "period": period,
                                        "rent_paid": cost,
                                        "deposit": dep,
                                        "start_hour": sh,
                                        "completed": False,
                                        "category": it["category"],
                                    })
                                    get_txns().append({
                                        "hour": sh, "type": "RENTAL",
                                        "user": cu, "amount": -total_charge,
                                        "note": f"Rented '{it['title']}' ({period}) + deposit",
                                        "item_id": it["id"],
                                    })
                                    get_txns().append({
                                        "hour": sh, "type": "RENTAL_INCOME",
                                        "user": it["owner"], "amount": cost,
                                        "note": f"Rental income from {cu} ({period})",
                                        "item_id": it["id"],
                                    })
                                    st.toast(f"🔑 Rented '{it['title']}' for {period}!")
                                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3: MY ACTIVITY
# ═══════════════════════════════════════════════════════════════════════════

with tab_activity:
    sh = get_sim_hour()
    al = get_alpha()
    cu = get_current_user()

    if is_warden():
        st.info("Switch to a student view to see personal activity.")
    else:
        uo = get_user_obj()
        # Header metrics
        mcol1, mcol2, mcol3 = st.columns(3)
        with mcol1:
            st.metric("💰 Wallet Balance", fmt_inr(uo["wallet"]))
        with mcol2:
            earnings = sum(
                t["amount"] for t in get_txns()
                if t["user"] == cu and t["type"] in ("SALE", "RENTAL_INCOME", "DAMAGE_CREDIT")
            )
            st.metric("📈 Total Earnings", fmt_inr(earnings))
        with mcol3:
            from rio.engine import impact_sale_or_transfer as _ist
            my_co2 = 0.0
            for it in get_items():
                if it["owner"] == cu and it["status"] in ("SETTLED", "STAFF_ROUTED"):
                    imp = _ist(it["category"])
                    my_co2 += imp["co2_avoided_kg"]
            st.metric("🌱 CO₂ Avoided", f"{my_co2:.1f} kg")

        # Ledger
        st.markdown("#### 📒 Transaction Ledger")
        my_txns = [t for t in get_txns() if t["user"] == cu]
        if my_txns:
            df = pd.DataFrame(my_txns)
            df["time"] = df["hour"].apply(sim_hour_display)
            df["amount_fmt"] = df["amount"].apply(fmt_inr)
            st.dataframe(
                df[["time", "type", "amount_fmt", "note"]].rename(
                    columns={"time": "Time", "type": "Type",
                             "amount_fmt": "Amount", "note": "Note"}
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No transactions yet.")

        st.divider()

        # Items I listed
        st.markdown("#### 📦 Items I Listed")
        my_items = [it for it in get_items() if it["owner"] == cu]
        if not my_items:
            st.caption("You haven't listed any items yet.")
        else:
            for it in my_items:
                eff = effective_status(it, sh)
                with st.container(border=True):
                    cat_info = CATEGORIES.get(it["category"], {})
                    emoji = cat_info.get("emoji", "📦")
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{emoji} {it['title']}**")
                        st.markdown(
                            badge_html(eff) + " " + location_badge(it["block"], it["room"]),
                            unsafe_allow_html=True,
                        )
                        if it.get("departure_hour") and it["status"] == "ACTIVE":
                            p = dutch_price(it["start_price"], it["floor_price"],
                                            it["listed_hour"], it["departure_hour"], sh, al)
                            st.caption(f"Current price: {fmt_inr(p)}")
                    with col2:
                        if it.get("buyer"):
                            st.caption(f"Buyer: {it['buyer']}")
                        if it.get("renter"):
                            st.caption(f"Renter: {it['renter']}")
                        if it.get("settled_price"):
                            st.caption(f"Settled: {fmt_inr(it['settled_price'])}")

        st.divider()

        # Items I claimed / rented
        st.markdown("#### 🛍️ Items I Claimed / Rented")
        claimed = [it for it in get_items() if it.get("buyer") == cu and it["status"] == "CLAIMED_ESCROW"]
        settled_bought = [it for it in get_items() if it.get("buyer") == cu and it["status"] == "SETTLED"]

        for it in claimed:
            with st.container(border=True):
                cat_info = CATEGORIES.get(it["category"], {})
                emoji = cat_info.get("emoji", "📦")
                st.markdown(f"**{emoji} {it['title']}** — *In Escrow*")
                st.markdown(
                    badge_html("CLAIMED_ESCROW") + " " + location_badge(it["block"], it["room"]),
                    unsafe_allow_html=True,
                )
                st.caption(f"Price: {fmt_inr(it.get('settled_price', 0))}")

                # QR code
                qr_data = f"RIO|{it['id']}|{cu}|{it.get('settled_price', 0)}"
                render_qr_code(qr_data)

                bcol1, bcol2 = st.columns(2)
                with bcol1:
                    if st.button(
                        "✅ Simulate QR scan at check-in",
                        key=f"qr_{it['id']}",
                        use_container_width=True,
                        type="primary",
                    ):
                        # Release escrow to seller
                        price = it.get("settled_price", 0)
                        get_users()[it["owner"]]["wallet"] += price
                        it["status"] = "SETTLED"
                        get_txns().append({
                            "hour": sh, "type": "ESCROW_RELEASE",
                            "user": it["owner"], "amount": price,
                            "note": f"Escrow released for '{it['title']}' from {cu}",
                            "item_id": it["id"],
                        })
                        get_txns().append({
                            "hour": sh, "type": "PURCHASE",
                            "user": cu, "amount": -price,
                            "note": f"Purchase settled: '{it['title']}'",
                            "item_id": it["id"],
                        })
                        st.toast(f"✅ Escrow released! '{it['title']}' is now yours.")
                        st.rerun()
                with bcol2:
                    if st.button(
                        "🚩 Report defect",
                        key=f"dispute_{it['id']}",
                        use_container_width=True,
                    ):
                        it["status"] = "DISPUTED"
                        get_txns().append({
                            "hour": sh, "type": "DISPUTE",
                            "user": cu, "amount": 0,
                            "note": f"Dispute raised for '{it['title']}'",
                            "item_id": it["id"],
                        })
                        st.toast(f"🚩 Dispute raised for '{it['title']}'. Warden will review.")
                        st.rerun()

        for it in settled_bought:
            with st.container(border=True):
                cat_info = CATEGORIES.get(it["category"], {})
                emoji = cat_info.get("emoji", "📦")
                st.markdown(f"**{emoji} {it['title']}** — ✅ Settled")
                st.caption(f"Paid: {fmt_inr(it.get('settled_price', 0))}")

        if not claimed and not settled_bought:
            st.caption("No claims yet.")

        st.divider()

        # List a new item
        st.markdown("#### ➕ List a New Item")
        with st.form("new_item_form", clear_on_submit=True):
            ncol1, ncol2 = st.columns(2)
            with ncol1:
                new_cat = st.selectbox("Category", list(CATEGORIES.keys()), key="new_cat")
                new_title = st.text_input("Title", placeholder="e.g., Symphony 35L Air Cooler")
            with ncol2:
                cat_defaults = CATEGORIES[new_cat]
                new_start = st.number_input(
                    "Start price (₹)", min_value=10,
                    value=int(cat_defaults["default_start"]), step=50,
                )
                new_floor = st.number_input(
                    "Floor price (₹)", min_value=1,
                    value=int(cat_defaults["default_floor"]), step=50,
                )

            ncol3, ncol4 = st.columns(2)
            with ncol3:
                dep_day = st.selectbox(
                    "Departure day",
                    ["Keeper (no departure)", "Day 7", "Day 10", "Day 12", "Day 14"],
                    key="new_dep",
                )
            with ncol4:
                new_rentable = st.checkbox("Available for rent", value=True)

            # Mock proof video upload
            proof = st.file_uploader(
                "🎥 Record 5-second proof video (optional)",
                type=["mp4", "mov", "avi"],
                key="proof_upload",
            )

            submitted = st.form_submit_button("📝 List item", type="primary",
                                               use_container_width=True)
            if submitted:
                if not new_title.strip():
                    st.error("Please enter a title.")
                else:
                    ok, msg = validate_listing(new_start, new_floor)
                    if not ok:
                        st.error(msg)
                    else:
                        dep_map = {
                            "Keeper (no departure)": None,
                            "Day 7": 168, "Day 10": 240,
                            "Day 12": 288, "Day 14": 336,
                        }
                        dep_h = dep_map.get(dep_day)
                        new_id = f"item_{st.session_state['next_item_id']:02d}"
                        st.session_state["next_item_id"] += 1
                        new_item = {
                            "id": new_id, "owner": cu,
                            "title": new_title.strip(),
                            "category": new_cat,
                            "block": uo["block"], "room": uo["room"],
                            "start_price": new_start, "floor_price": new_floor,
                            "listed_hour": sh, "departure_hour": dep_h,
                            "rentable": new_rentable, "status": "ACTIVE",
                            "buyer": None, "renter": None, "settled_price": None,
                        }
                        get_items().append(new_item)
                        get_txns().append({
                            "hour": sh, "type": "LISTING",
                            "user": cu, "amount": 0,
                            "note": f"Listed '{new_title.strip()}'",
                            "item_id": new_id,
                        })

                        if proof:
                            proof_hash = hashlib.sha256(proof.read()).hexdigest()[:16]
                            st.toast(f"📝 Listed! Proof SHA-256: {proof_hash}")
                        else:
                            st.toast(f"📝 '{new_title.strip()}' is now live on the marketplace!")
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# TAB 4: DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

with tab_dashboard:
    sh = get_sim_hour()
    al = get_alpha()
    cu = get_current_user()

    impact = aggregate_impact(get_items(), get_txns(), get_rents(), st.session_state["substitution_rate"])

    if not is_warden():
        st.caption("📊 Read-only impact view. Switch to Warden for full dashboard.")

    # Metrics row
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.metric("♻️ Items diverted", impact["items_diverted"])
    with m2:
        st.metric("⚖️ Waste diverted", f"{impact['waste_diverted_kg']:.1f} kg")
    with m3:
        st.metric("🌱 CO₂e avoided", f"{impact['co2_avoided_kg']:.1f} kg")
    with m4:
        st.metric("💰 Rupees saved", fmt_inr(impact["rupees_saved"]))
    with m5:
        st.metric("📈 Rental income", fmt_inr(impact["rental_income"]))
    with m6:
        st.metric("🔄 Rentals done", impact["rentals_completed"])

    st.caption(
        "⚠️ *Estimates based on approximate embodied carbon ranges; "
        "assumptions adjustable in the sidebar.*"
    )

    # Charts
    ch1, ch2 = st.columns(2)
    with ch1:
        st.plotly_chart(
            chart_co2_by_category(get_items(), get_rents(), st.session_state["substitution_rate"]),
            use_container_width=True,
        )
    with ch2:
        st.plotly_chart(
            chart_utilization(get_items(), get_rents()),
            use_container_width=True,
        )

    ch3, ch4 = st.columns(2)
    with ch3:
        st.plotly_chart(
            chart_status_breakdown(get_items(), sh),
            use_container_width=True,
        )
    with ch4:
        st.plotly_chart(
            chart_cumulative_co2(get_txns(), get_items(), get_rents(), st.session_state["substitution_rate"]),
            use_container_width=True,
        )

    # ── Warden-only sections ──
    if is_warden():
        st.divider()
        st.markdown("### 🏥 Staff Welfare Queue")

        staff_items = [
            it for it in get_items()
            if effective_status(it, sh) == "STAFF_RESERVE"
        ]
        if not staff_items:
            st.success("No items in the staff welfare pool at this time.")
        else:
            for it in staff_items:
                with st.container(border=True):
                    cat_info = CATEGORIES.get(it["category"], {})
                    emoji = cat_info.get("emoji", "📦")
                    st.markdown(
                        f"**{emoji} {it['title']}** — {it['owner']}'s item"
                    )
                    st.markdown(
                        badge_html("STAFF_RESERVE") + " " +
                        location_badge(it["block"], it["room"]),
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "✅ Confirm custody transfer to housekeeping",
                        key=f"staff_{it['id']}",
                        use_container_width=True,
                    ):
                        it["status"] = "STAFF_ROUTED"
                        get_txns().append({
                            "hour": sh, "type": "STAFF_TRANSFER",
                            "user": "Warden", "amount": 0,
                            "note": f"'{it['title']}' transferred to staff",
                            "item_id": it["id"],
                        })
                        st.toast(f"✅ '{it['title']}' transferred to housekeeping staff.")
                        st.rerun()

        st.divider()

        # Disputes queue
        st.markdown("### ⚖️ Disputes Queue")
        disputed = [it for it in get_items() if it["status"] == "DISPUTED"]
        if not disputed:
            st.success("No active disputes.")
        else:
            for it in disputed:
                with st.container(border=True):
                    cat_info = CATEGORIES.get(it["category"], {})
                    emoji = cat_info.get("emoji", "📦")
                    st.markdown(
                        f"**{emoji} {it['title']}** — Buyer: {it.get('buyer', '?')}, "
                        f"Seller: {it['owner']}"
                    )
                    dcol1, dcol2 = st.columns(2)
                    with dcol1:
                        if st.button(
                            "💸 Refund buyer",
                            key=f"refund_{it['id']}",
                            use_container_width=True,
                        ):
                            price = it.get("settled_price", 0)
                            buyer = it.get("buyer")
                            if buyer:
                                get_users()[buyer]["wallet"] += price
                                get_txns().append({
                                    "hour": sh, "type": "DISPUTE_REFUND",
                                    "user": buyer, "amount": price,
                                    "note": f"Refund for '{it['title']}'",
                                    "item_id": it["id"],
                                })
                            it["status"] = "ACTIVE"
                            it["buyer"] = None
                            it["settled_price"] = None
                            st.toast(f"💸 Buyer refunded for '{it['title']}'.")
                            st.rerun()
                    with dcol2:
                        if st.button(
                            "✅ Release to seller",
                            key=f"release_{it['id']}",
                            use_container_width=True,
                        ):
                            price = it.get("settled_price", 0)
                            get_users()[it["owner"]]["wallet"] += price
                            get_txns().append({
                                "hour": sh, "type": "ESCROW_RELEASE",
                                "user": it["owner"], "amount": price,
                                "note": f"Dispute resolved: escrow to {it['owner']}",
                                "item_id": it["id"],
                            })
                            it["status"] = "SETTLED"
                            st.toast(f"✅ Escrow released to {it['owner']}.")
                            st.rerun()

        st.divider()

        # No-Dues panel
        st.markdown("### 📋 No-Dues Clearance Panel")
        st.caption(
            "🏗️ *Proposed integration with the hostel office (pilot) — NOT an existing API.*"
        )

        for sname in student_names():
            suser = get_users()[sname]
            if suser.get("departure_hour") is None:
                continue
            unresolved = unresolved_items(sname, get_items(), sh)
            with st.container(border=True):
                nc1, nc2 = st.columns([3, 1])
                with nc1:
                    st.markdown(f"**{sname}** — {suser['block']} Room {suser['room']}")
                    my_all = [it for it in get_items() if it["owner"] == sname]
                    settled_count = sum(1 for it in my_all if it["status"] in ("SETTLED",))
                    routed_count = sum(1 for it in my_all if it["status"] == "STAFF_ROUTED")
                    rented_count = sum(1 for it in my_all if it["status"] == "RENTED")
                    st.caption(
                        f"Registered: {len(my_all)} · "
                        f"Settled: {settled_count} · "
                        f"Rented out: {rented_count} · "
                        f"Staff-routed: {routed_count} · "
                        f"⚠️ Unresolved: {len(unresolved)}"
                    )
                with nc2:
                    can_approve = len(unresolved) == 0
                    approved = st.session_state["no_dues"].get(sname, False)
                    if st.checkbox(
                        "Approve no-dues",
                        value=approved,
                        key=f"noDues_{sname}",
                        disabled=not can_approve,
                        help="Cannot approve while unresolved items exist" if not can_approve else None,
                    ):
                        st.session_state["no_dues"][sname] = True
                    else:
                        st.session_state["no_dues"][sname] = False


# ── Page Navigation ────────────────────────────────────────────────────────
st.divider()
st.markdown("#### 🧭 Quick Navigation")
nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    st.page_link("views/landing.py", label="← Back to Home", icon="🏠", use_container_width=True)
with nav_col2:
    st.page_link("views/how_it_works.py", label="See How It Works →", icon="📈", use_container_width=True)
with nav_col3:
    st.page_link("views/team.py", label="Team & Roadmap →", icon="👥", use_container_width=True)


# ── Footer ─────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="proto-footer">'
    '🔬 <strong>Prototype: simulated data and payments</strong> · '
    'Built for RIO Hackathon Demo'
    '</div>',
    unsafe_allow_html=True,
)
