"""
RIO UI — card renderers, CSS injection, badge helpers, chart builders, fmt_inr().
"""

from __future__ import annotations

import io
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

    /* Hide Streamlit menu & footer */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* Rounded cards */
    div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] {
        gap: 0.75rem;
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
