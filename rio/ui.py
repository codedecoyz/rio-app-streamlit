"""
RIO UI — card renderers, CSS injection, badge helpers, chart builders, fmt_inr().
"""

from __future__ import annotations

import io
import textwrap
from typing import Any, Optional

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from rio.engine import (
    CATEGORIES, dutch_price, effective_status, urgency_badge,
    watchers_count, hours_remaining, impact_sale_or_transfer,
    impact_rental,
)

# ── QR code (graceful fallback) ────────────────────────────────────────────
try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False


# ── CSS Injection ──────────────────────────────────────────────────────────

CUSTOM_CSS = """
<style>
    /* Tighter top padding */
    .block-container { padding-top: 1.5rem !important; }

    /* Hide Streamlit default menu & footer, but allow custom blocks */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* Rounded cards */
    div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] {
        gap: 0.75rem;
    }

    /* Container max-width constraint for readable reading width */
    .rio-content-container {
        max-width: 1100px;
        margin: 0 auto;
    }

    /* Interactive hover lift */
    div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"] {
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(249, 115, 22, 0.08);
    }

    /* Badge pills */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        margin-right: 4px;
    }
    .badge-fresh       { background: #FFEDD5; color: #C2410C; }
    .badge-dropping    { background: #FEF3C7; color: #92400E; }
    .badge-critical    { background: #FEE2E2; color: #991B1B; }
    .badge-staff       { background: #E5E7EB; color: #374151; }
    .badge-rented      { background: #DBEAFE; color: #1E40AF; }
    .badge-settled     { background: #FFEDD5; color: #C2410C; }
    .badge-disputed    { background: #FEE2E2; color: #991B1B; }
    .badge-keeper      { background: #E0E7FF; color: #3730A3; }
    .badge-location    { background: #F3F4F6; color: #374151; border: 1px solid #D1D5DB; }

    /* Price styling */
    .price-current { font-size: 1.5rem; font-weight: 700; color: #F97316; }
    .price-original { font-size: 0.9rem; color: #9CA3AF; text-decoration: line-through; }

    /* Impact line */
    .impact-line { font-size: 0.78rem; color: #6B7280; margin-top: 4px; }

    /* Footer note */
    .proto-footer {
        text-align: center; padding: 1rem; margin-top: 2rem;
        font-size: 0.8rem; color: #9CA3AF; border-top: 1px solid #E5E7EB;
    }

    /* Summary strip */
    .summary-strip {
        display: flex; gap: 2rem; justify-content: center;
        padding: 0.5rem 1rem; background: #FFF7ED; border-radius: 8px;
        margin-bottom: 1rem; flex-wrap: wrap;
    }
    .summary-item {
        font-size: 0.85rem; color: #431407;
    }
    .summary-value { font-weight: 700; color: #F97316; }

    /* Mock hero card */
    .hero-mock-card {
        background: #FFFFFF;
        border: 1px solid #FED7AA;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 10px 25px -5px rgba(249, 115, 22, 0.12), 0 8px 10px -6px rgba(249, 115, 22, 0.08);
        transition: transform 0.2s ease;
    }
    .hero-mock-card:hover {
        transform: translateY(-3px);
    }
    .mock-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
    }
    .mock-category-tag {
        font-size: 0.8rem;
        font-weight: 600;
        color: #C2410C;
        background: #FFEDD5;
        padding: 3px 8px;
        border-radius: 6px;
    }
    .mock-card-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1F2937;
        margin-bottom: 0.25rem;
    }
    .mock-card-location {
        font-size: 0.85rem;
        color: #4B5563;
        margin-bottom: 1rem;
    }
    .mock-card-pricing {
        display: flex;
        align-items: baseline;
        gap: 0.75rem;
        margin-bottom: 0.5rem;
    }
    .mock-price-current {
        font-size: 2rem;
        font-weight: 800;
        color: #EA580C;
    }
    .mock-price-original {
        font-size: 1.1rem;
        color: #9CA3AF;
        text-decoration: line-through;
    }
    .mock-floor-tag {
        font-size: 0.8rem;
        color: #047857;
        background: #DEF7EC;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 600;
    }
    .mock-decay-bar {
        background: #F3F4F6;
        height: 8px;
        border-radius: 9999px;
        overflow: hidden;
        margin-bottom: 0.75rem;
    }
    .mock-decay-fill {
        background: linear-gradient(90deg, #F97316, #EA580C);
        height: 100%;
        border-radius: 9999px;
    }
    .mock-card-footer {
        display: flex;
        justify-content: space-between;
        font-size: 0.82rem;
        color: #6B7280;
        margin-bottom: 0.75rem;
    }
    .mock-card-note {
        font-size: 0.8rem;
        color: #9A3412;
        background: #FFF7ED;
        padding: 6px 10px;
        border-radius: 8px;
        border: 1px dashed #FDBA74;
        text-align: center;
    }

    /* 3-step cards */
    .rio-step-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 1.25rem;
        height: 100%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .rio-step-card:hover {
        transform: translateY(-2px);
        border-color: #FDBA74;
    }
    .rio-step-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    .rio-step-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1F2937;
        margin-bottom: 0.35rem;
    }
    .rio-step-text {
        font-size: 0.9rem;
        color: #4B5563;
        line-height: 1.45;
    }

    /* Lifecycle chain */
    .lifecycle-chain-container {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: center;
        gap: 0.6rem;
        padding: 1rem;
        background: #FFF7ED;
        border: 1px solid #FED7AA;
        border-radius: 12px;
        margin: 1rem 0;
    }
    .lifecycle-step {
        display: flex;
        align-items: center;
    }
    .lifecycle-pill {
        background: #FFFFFF;
        color: #9A3412;
        border: 1px solid #FDBA74;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    .lifecycle-pill .subtext {
        font-size: 0.78rem;
        color: #C2410C;
        font-weight: 500;
    }
    .lifecycle-arrow {
        color: #EA580C;
        font-size: 1.2rem;
        font-weight: 700;
    }

    /* Credit block */
    .rio-credit-card {
        background: #FFFFFF;
        border: 1px solid #FED7AA;
        border-radius: 16px;
        padding: 1.75rem;
        text-align: center;
        margin: 2.5rem auto 1.5rem auto;
        max-width: 650px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .rio-credit-heart {
        font-size: 1.75rem;
        margin-bottom: 0.25rem;
    }
    .rio-credit-heading {
        font-size: 1.2rem;
        font-weight: 700;
        color: #1F2937;
        margin-bottom: 0.35rem;
    }
    .rio-credit-sub {
        font-size: 0.95rem;
        color: #4B5563;
        margin-bottom: 0.6rem;
    }
    .rio-credit-names {
        font-size: 0.95rem;
        font-weight: 600;
        color: #EA580C;
        margin-bottom: 0.75rem;
    }
    .rio-credit-names span {
        padding: 0 4px;
    }
    .rio-credit-note {
        font-size: 0.78rem;
        color: #9CA3AF;
        border-top: 1px solid #F3F4F6;
        padding-top: 0.5rem;
        margin-top: 0.5rem;
    }
</style>
"""


def inject_css() -> None:
    """Inject custom CSS into the Streamlit app."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ── Formatting helpers ─────────────────────────────────────────────────────

def fmt_inr(amount: float) -> str:
    """Format a number as ₹ with Indian grouping (e.g., ₹1,800)."""
    amount = int(round(amount))
    negative = amount < 0
    amount = abs(amount)
    s = str(amount)
    if len(s) <= 3:
        formatted = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.append(rest)
        parts.reverse()
        formatted = ",".join(parts) + "," + last3
    prefix = "-" if negative else ""
    return f"₹{prefix}{formatted}"


def sim_hour_display(sim_hour: int) -> str:
    """Convert simulated hour to human-readable 'Day X, HH:00'."""
    day = sim_hour // 24 + 1
    hour = sim_hour % 24
    return f"Day {day}, {hour:02d}:00"


# ── Badge rendering ───────────────────────────────────────────────────────

BADGE_CLASSES = {
    "FRESH": "badge-fresh",
    "DROPPING": "badge-dropping",
    "CRITICAL": "badge-critical",
    "STAFF_RESERVE": "badge-staff",
    "RETURN_DUE": "badge-staff",
    "RENTED": "badge-rented",
    "SETTLED": "badge-settled",
    "STAFF_ROUTED": "badge-staff",
    "DISPUTED": "badge-disputed",
    "KEEPER": "badge-keeper",
    "CLAIMED_ESCROW": "badge-dropping",
    "ACTIVE": "badge-fresh",
}


def badge_html(label: str) -> str:
    """Render a coloured pill badge."""
    css_class = BADGE_CLASSES.get(label, "badge-fresh")
    return f'<span class="badge {css_class}">{label}</span>'


def location_badge(block: str, room: str) -> str:
    """Render a location pill."""
    return f'<span class="badge badge-location">📍 {block} - Room {room}</span>'


# ── Item card renderer ─────────────────────────────────────────────────────

def render_item_card(
    item: dict,
    sim_hour: int,
    alpha: float,
    show_actions: bool = False,
    action_context: str = "marketplace",
    current_user: str = "",
) -> None:
    """Render a single item card inside a container."""
    cat_info = CATEGORIES.get(item["category"], {})
    emoji = cat_info.get("emoji", "📦")
    eff_status = effective_status(item, sim_hour)

    with st.container(border=True):
        # Title row
        st.markdown(
            f"### {emoji} {item['title']}",
        )

        # Badges
        urg = urgency_badge(item.get("departure_hour"), sim_hour)
        badges = badge_html(urg)
        if eff_status not in ("ACTIVE",):
            badges += " " + badge_html(eff_status)
        badges += " " + location_badge(item["block"], item["room"])
        st.markdown(badges, unsafe_allow_html=True)

        # Price section (for departing items)
        if item.get("departure_hour") is not None:
            current_p = dutch_price(
                item["start_price"], item["floor_price"],
                item["listed_hour"], item["departure_hour"],
                sim_hour, alpha,
            )
            hr = hours_remaining(item["departure_hour"], sim_hour)

            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(
                    f'<span class="price-current">{fmt_inr(current_p)}</span> '
                    f'<span class="price-original">{fmt_inr(item["start_price"])}</span>',
                    unsafe_allow_html=True,
                )
                # Price decay progress bar
                if item["start_price"] > item["floor_price"]:
                    decay_pct = 1.0 - (current_p - item["floor_price"]) / (item["start_price"] - item["floor_price"])
                    st.progress(min(1.0, max(0.0, decay_pct)), text=f"Price decay: {decay_pct*100:.0f}%")
            with col2:
                if hr is not None:
                    st.metric("⏱ Time left", f"{hr:.0f}h")
                wc = watchers_count(
                    item["id"], sim_hour, item.get("departure_hour"),
                    item["start_price"], item["floor_price"], item["listed_hour"],
                )
                st.caption(f"👀 {wc} watchers")
        else:
            # Keeper item — no price decay, rent only
            st.markdown(
                f'<span class="price-current">{fmt_inr(item["start_price"])}</span> '
                f'<span class="impact-line">Keeper item · Rent only</span>',
                unsafe_allow_html=True,
            )

        # Impact line
        co2 = cat_info.get("embodied_co2e", 0)
        weight = cat_info.get("tare_kg", 0)
        st.markdown(
            f'<span class="impact-line">🌱 Saves {co2 + 2.2:.1f} kgCO₂e · '
            f'Diverts {weight} kg from landfill</span>',
            unsafe_allow_html=True,
        )


# ── QR code helper ─────────────────────────────────────────────────────────

def render_qr_code(data: str) -> None:
    """Render a QR code image or a styled placeholder if qrcode is not installed."""
    if HAS_QRCODE:
        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#F97316", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        st.image(buf.getvalue(), width=150, caption="Scan at check-in")
    else:
        st.info(f"📱 **QR Code Placeholder**\n\n`{data}`\n\n*(Install `qrcode[pil]` for real QR)*")


# ── Charts ─────────────────────────────────────────────────────────────────

RIO_COLORS = ["#F97316", "#FB923C", "#FDBA74", "#FED7AA", "#FFEDD5",
              "#EA580C", "#C2410C", "#9A3412", "#7C2D12"]


def chart_co2_by_category(items: list[dict], rentals: list[dict],
                          substitution_rate: float) -> go.Figure:
    """Bar chart of CO2 avoided by category."""
    data: dict[str, float] = {}
    for item in items:
        if item["status"] in ("SETTLED", "STAFF_ROUTED"):
            imp = impact_sale_or_transfer(item["category"])
            data[item["category"]] = data.get(item["category"], 0) + imp["co2_avoided_kg"]
    for r in rentals:
        if r.get("completed"):
            imp = impact_rental(r["category"], substitution_rate)
            data[r["category"]] = data.get(r["category"], 0) + imp["co2_avoided_kg"]

    if not data:
        return _empty_chart("No data yet")

    df = pd.DataFrame({"Category": list(data.keys()), "CO₂ avoided (kg)": list(data.values())})
    fig = px.bar(df, x="Category", y="CO₂ avoided (kg)",
                 color_discrete_sequence=RIO_COLORS,
                 title="CO₂ Avoided by Category")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    return fig


def chart_utilization(items: list[dict], rentals: list[dict]) -> go.Figure:
    """Bar chart of uses (rentals + sale) per item, top 10."""
    uses: dict[str, int] = {}
    titles: dict[str, str] = {}
    for item in items:
        iid = item["id"]
        titles[iid] = item["title"][:25]
        uses[iid] = uses.get(iid, 0)
        if item["status"] in ("SETTLED", "STAFF_ROUTED"):
            uses[iid] += 1
    for r in rentals:
        iid = r["item_id"]
        uses[iid] = uses.get(iid, 0) + 1

    # Top 10
    sorted_items = sorted(uses.items(), key=lambda x: x[1], reverse=True)[:10]
    if not sorted_items or all(v == 0 for _, v in sorted_items):
        return _empty_chart("No utilization data yet")

    df = pd.DataFrame({
        "Item": [titles.get(k, k) for k, _ in sorted_items],
        "Uses": [v for _, v in sorted_items],
    })
    fig = px.bar(df, x="Uses", y="Item", orientation="h",
                 color_discrete_sequence=RIO_COLORS,
                 title="Top 10 Items by Utilization")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      yaxis=dict(autorange="reversed"))
    return fig


def chart_status_breakdown(items: list[dict], sim_hour: int) -> go.Figure:
    """Donut chart of item status breakdown."""
    counts: dict[str, int] = {}
    for item in items:
        s = effective_status(item, sim_hour)
        counts[s] = counts.get(s, 0) + 1
    if not counts:
        return _empty_chart("No items")

    status_colors = {
        "ACTIVE": "#F97316", "RENTED": "#3B82F6", "CLAIMED_ESCROW": "#F59E0B",
        "SETTLED": "#C2410C", "STAFF_RESERVE": "#6B7280", "STAFF_ROUTED": "#9CA3AF",
        "DISPUTED": "#EF4444", "RETURN_DUE": "#8B5CF6",
    }
    labels = list(counts.keys())
    values = list(counts.values())
    colors = [status_colors.get(s, "#D1D5DB") for s in labels]

    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values,
        hole=0.45, marker=dict(colors=colors),
    )])
    fig.update_layout(title="Item Status Breakdown",
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    return fig


def chart_cumulative_co2(transactions: list[dict], items: list[dict],
                         rentals: list[dict], substitution_rate: float) -> go.Figure:
    """Line chart of cumulative CO2 avoided over simulated time."""
    events: list[tuple[int, float]] = []
    for item in items:
        if item["status"] in ("SETTLED", "STAFF_ROUTED"):
            # Find the transaction hour
            hour = 0
            for t in transactions:
                if t.get("item_id") == item["id"] and t["type"] in ("PURCHASE", "SALE"):
                    hour = t["hour"]
                    break
            imp = impact_sale_or_transfer(item["category"])
            events.append((hour, imp["co2_avoided_kg"]))
    for r in rentals:
        if r.get("completed"):
            imp = impact_rental(r["category"], substitution_rate)
            events.append((r.get("start_hour", 0), imp["co2_avoided_kg"]))

    if not events:
        return _empty_chart("No CO₂ data yet")

    events.sort(key=lambda x: x[0])
    hours = []
    cumulative = []
    total = 0.0
    for h, co2 in events:
        total += co2
        hours.append(h)
        cumulative.append(total)

    df = pd.DataFrame({"Hour": hours, "Cumulative CO₂ avoided (kg)": cumulative})
    fig = px.area(df, x="Hour", y="Cumulative CO₂ avoided (kg)",
                  color_discrete_sequence=RIO_COLORS,
                  title="Cumulative CO₂ Avoided Over Time")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    return fig


def _empty_chart(msg: str) -> go.Figure:
    """Return an empty chart with a message."""
    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False, font=dict(size=16, color="#9CA3AF"))
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(visible=False), yaxis=dict(visible=False), height=200)
    return fig


# ── Summary strip ──────────────────────────────────────────────────────────

def render_summary_strip(items: list[dict], rentals: list[dict],
                         substitution_rate: float) -> None:
    """Render the live summary strip at the top."""
    from rio.engine import aggregate_impact
    impact = aggregate_impact(items, [], rentals, substitution_rate)

    active_count = sum(1 for it in items if it["status"] == "ACTIVE")

    html = f"""
    <div class="summary-strip">
        <span class="summary-item">📦 <span class="summary-value">{active_count}</span> items listed</span>
        <span class="summary-item">🌱 <span class="summary-value">{impact['co2_avoided_kg']:.1f}</span> kgCO₂e avoided</span>
        <span class="summary-item">♻️ <span class="summary-value">{impact['waste_diverted_kg']:.1f}</span> kg diverted</span>
        <span class="summary-item">🔄 <span class="summary-value">{impact['rentals_completed']}</span> rentals done</span>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ── Landing & Multipage Shared Helpers ─────────────────────────────────────

PILL_STYLES = {
    "green": ("#DEF7EC", "#03543F", "#BCF0DA"),
    "amber": ("#FEF3C7", "#92400E", "#FDE68A"),
    "orange": ("#FFEDD5", "#C2410C", "#FED7AA"),
    "red": ("#FEE2E2", "#991B1B", "#FECACA"),
    "grey": ("#F3F4F6", "#374151", "#E5E7EB"),
    "blue": ("#DBEAFE", "#1E40AF", "#BFDBFE"),
}


def pill(text: str, kind: str = "green") -> str:
    """Render a colored pill badge (green, amber, red, grey, blue, orange)."""
    bg, fg, border = PILL_STYLES.get(kind, PILL_STYLES["green"])
    return (
        f'<span style="display:inline-block; padding:3px 10px; border-radius:9999px; '
        f'font-size:0.75rem; font-weight:600; background:{bg}; color:{fg}; '
        f'border:1px solid {border}; margin:2px 4px 2px 0;">{text}</span>'
    )


def hero_card_html() -> str:
    """Mock item card for landing page hero visual."""
    return textwrap.dedent("""
    <div class="hero-mock-card">
        <div class="mock-card-header">
            <span class="mock-category-tag">🌬️ Air cooler</span>
            <span class="badge badge-dropping">DROPPING</span>
        </div>
        <div class="mock-card-title">Symphony 35L Desert Air Cooler</div>
        <div class="mock-card-location">📍 Hostel Block B &middot; Room 304</div>
        <div class="mock-card-pricing">
            <span class="mock-price-current">₹645</span>
            <span class="mock-price-original">₹1,800</span>
            <span class="mock-floor-tag">Floor: ₹500</span>
        </div>
        <div class="mock-decay-bar">
            <div class="mock-decay-fill" style="width: 88%;"></div>
        </div>
        <div class="mock-card-footer">
            <span>⏱ 18h to departure</span>
            <span>👀 7 watching</span>
        </div>
        <div class="mock-card-note">
            🛡️ In-situ handover &middot; Stays in room &middot; Zero haulage
        </div>
    </div>
    """).strip()


def step_card(icon: str, title: str, text: str) -> str:
    """Render a 3-step feature card HTML."""
    return textwrap.dedent(f"""
    <div class="rio-step-card">
        <div class="rio-step-icon">{icon}</div>
        <div class="rio-step-title">{title}</div>
        <div class="rio-step-text">{text}</div>
    </div>
    """).strip()


def lifecycle_chain_html() -> str:
    """Render the rent-to-own visual lifecycle chain."""
    return textwrap.dedent("""
    <div class="lifecycle-chain-container">
        <div class="lifecycle-step">
            <span class="lifecycle-pill">🔑 Rent</span>
        </div>
        <div class="lifecycle-arrow">&rarr;</div>
        <div class="lifecycle-step">
            <span class="lifecycle-pill">🏠 Convert to buy <span class="subtext">(50% rent credit)</span></span>
        </div>
        <div class="lifecycle-arrow">&rarr;</div>
        <div class="lifecycle-step">
            <span class="lifecycle-pill">📉 Dutch Auction</span>
        </div>
        <div class="lifecycle-arrow">&rarr;</div>
        <div class="lifecycle-step">
            <span class="lifecycle-pill">🛡️ Staff Welfare</span>
        </div>
    </div>
    """).strip()


def credit_block_html() -> str:
    """Render the thank-you and team credit block required in section 7."""
    return textwrap.dedent("""
    <div class="rio-credit-card">
        <div class="rio-credit-heart">♻️</div>
        <div class="rio-credit-heading">Thank you for reviewing RIO.</div>
        <div class="rio-credit-sub">
            Built with care by <strong>Team RIO</strong> &middot; <strong>Sharda University</strong>
        </div>
        <div class="rio-credit-names">
            <span>Raj</span> &middot;
            <span>Siddhanth</span> &middot;
            <span>Charu</span> &middot;
            <span>Varun</span> &middot;
            <span>Siya</span>
        </div>
        <div class="rio-credit-note">Prototype: simulated data and payments.</div>
    </div>
    """).strip()


def auction_curve_figure(
    item: dict | None = None,
    alpha: float = 1.0,
    height: int = 380,
) -> go.Figure:
    """Generate a Plotly line chart of the Dutch auction decay curve for an item.

    Defaults to the sample cooler (start ₹1,800, floor ₹500, departure 168h).
    Marks floor line, floor-reached point (departure - 2h), and staff cutoff (departure - 1h).
    """
    if item is None:
        start_p = 1800.0
        floor_p = 500.0
        listed_h = 0
        dep_h = 168
        title_str = "Dutch Auction Price Decay (Sample 35L Cooler)"
    else:
        start_p = float(item["start_price"])
        floor_p = float(item["floor_price"])
        listed_h = int(item.get("listed_hour", 0))
        dep_h = int(item.get("departure_hour", 168))
        title_str = f"Auction Price Decay: {item.get('title', 'Item')}"

    hours = list(range(listed_h, dep_h + 1))
    prices = [
        dutch_price(start_p, floor_p, listed_h, dep_h, h, alpha)
        for h in hours
    ]

    fig = go.Figure()

    # Main decay curve
    fig.add_trace(go.Scatter(
        x=hours,
        y=prices,
        mode="lines",
        name="Price (₹)",
        line=dict(color="#F97316", width=3),
        hovertemplate="Hour %{x}<br>Price: ₹%{y:,.0f}<extra></extra>",
    ))

    # Floor line (horizontal)
    fig.add_hline(
        y=floor_p,
        line_dash="dot",
        line_color="#10B981",
        line_width=1.5,
        annotation_text=f"Floor: {fmt_inr(floor_p)}",
        annotation_position="bottom right",
        annotation_font=dict(size=11, color="#047857"),
    )

    # Floor reached line (dep_h - 2)
    floor_reach_h = dep_h - 2
    if floor_reach_h >= listed_h:
        fig.add_vline(
            x=floor_reach_h,
            line_dash="dash",
            line_color="#6B7280",
            line_width=1.2,
            annotation_text=f"Hits floor ({floor_reach_h}h)",
            annotation_position="top left",
            annotation_font=dict(size=10, color="#4B5563"),
        )

    # Staff cutoff line (dep_h - 1)
    staff_cutoff_h = dep_h - 1
    if staff_cutoff_h >= listed_h:
        fig.add_vline(
            x=staff_cutoff_h,
            line_dash="dash",
            line_color="#EF4444",
            line_width=1.5,
            annotation_text=f"Staff cutoff ({staff_cutoff_h}h)",
            annotation_position="bottom left",
            annotation_font=dict(size=10, color="#DC2626"),
        )

    fig.update_layout(
        title=dict(text=title_str, font=dict(size=14, color="#431407")),
        xaxis=dict(
            title="Hours since listing",
            gridcolor="#F3F4F6",
            zeroline=False,
        ),
        yaxis=dict(
            title="Price (₹)",
            gridcolor="#F3F4F6",
            zeroline=False,
        ),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=40, r=40, t=50, b=40),
        hovermode="x unified",
    )
    return fig

