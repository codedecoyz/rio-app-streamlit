"""
RIO Engine — Pure business logic (no Streamlit imports).

Dutch auction pricing, status derivation, impact math, rental calculations,
and validation rules. All functions are deterministic and unit-testable.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Optional

# ── Category coefficients ──────────────────────────────────────────────────
# Estimated from published embodied-carbon ranges; NOT measured facts.
CATEGORIES: dict[str, dict[str, float]] = {
    "Air cooler": {
        "tare_kg": 14.5, "volume_m3": 0.28, "embodied_co2e": 62.0,
        "default_start": 1800, "default_floor": 500, "emoji": "❄️",
    },
    "Foam mattress": {
        "tare_kg": 11.2, "volume_m3": 0.35, "embodied_co2e": 44.0,
        "default_start": 1200, "default_floor": 300, "emoji": "🛏️",
    },
    "Kettle/immersion": {
        "tare_kg": 1.2, "volume_m3": 0.01, "embodied_co2e": 15.5,
        "default_start": 500, "default_floor": 150, "emoji": "🫖",
    },
    "Drafter+board": {
        "tare_kg": 1.8, "volume_m3": 0.04, "embodied_co2e": 8.2,
        "default_start": 450, "default_floor": 150, "emoji": "📐",
    },
    "Study table+chair": {
        "tare_kg": 18.0, "volume_m3": 0.42, "embodied_co2e": 52.0,
        "default_start": 1500, "default_floor": 400, "emoji": "🪑",
    },
}

# Logistics avoided per in-situ transfer
LOGISTICS_CO2_PER_TRANSFER: float = 8.0 * 0.275  # 8 km × 0.275 kgCO2e/km = 2.2

# ── Constants (defaults; overridable via sidebar) ──────────────────────────
DECAY_END_BEFORE_DEPARTURE: int = 2   # hours
STAFF_CUTOFF_BEFORE_DEPARTURE: int = 1  # hours
DEFAULT_ALPHA: float = 1.0

# Rental rates (fraction of start_price)
RENT_RATES: dict[str, dict[str, Any]] = {
    "Day":   {"fraction": 0.02, "hours": 24},
    "Week":  {"fraction": 0.10, "hours": 168},
    "Month": {"fraction": 0.25, "hours": 720},
}

DEPOSIT_FRACTION: float = 0.20
RENT_TO_OWN_CREDIT_FRACTION: float = 0.50
DAMAGE_DEDUCTION_FRACTION: float = 0.25


# ── Pricing ────────────────────────────────────────────────────────────────

def dutch_price(
    start_price: float,
    floor_price: float,
    listed_hour: int,
    departure_hour: int,
    sim_hour: int,
    alpha: float = DEFAULT_ALPHA,
) -> float:
    """Compute the time-decay Dutch auction price.

    The price decays from start_price to floor_price over the window
    [listed_hour, departure_hour - DECAY_END_BEFORE_DEPARTURE] using a
    power curve controlled by alpha.
    Returns the price rounded to the nearest ₹5.
    """
    decay_end = departure_hour - DECAY_END_BEFORE_DEPARTURE
    span = decay_end - listed_hour
    if span <= 0:
        return _round5(floor_price)
    frac = max(0.0, min(1.0, (sim_hour - listed_hour) / span))
    price = max(floor_price, start_price - (frac ** alpha) * (start_price - floor_price))
    return _round5(price)


def _round5(value: float) -> float:
    """Round to the nearest multiple of 5."""
    return round(value / 5) * 5


# ── Status derivation ─────────────────────────────────────────────────────

def hours_remaining(departure_hour: Optional[int], sim_hour: int) -> Optional[float]:
    """Hours left until departure. None for keeper items."""
    if departure_hour is None:
        return None
    return max(0, departure_hour - sim_hour)


def effective_status(item: dict, sim_hour: int) -> str:
    """Derive the display status from stored status + simulated time.

    Derived statuses (not stored):
      STAFF_RESERVE — ACTIVE item within 1 hour of departure
      RETURN_DUE    — RENTED item within 1 hour of departure
    """
    stored = item["status"]
    dep = item.get("departure_hour")
    if dep is None:
        return stored
    hr = hours_remaining(dep, sim_hour)
    if hr is not None and hr <= STAFF_CUTOFF_BEFORE_DEPARTURE:
        if stored == "ACTIVE":
            return "STAFF_RESERVE"
        if stored == "RENTED":
            return "RETURN_DUE"
    return stored


def urgency_badge(departure_hour: Optional[int], sim_hour: int) -> str:
    """Return an urgency label for display."""
    hr = hours_remaining(departure_hour, sim_hour)
    if hr is None:
        return "KEEPER"
    if hr > 48:
        return "FRESH"
    if hr > 3:
        return "DROPPING"
    return "CRITICAL"


def watchers_count(item_id: str, sim_hour: int, departure_hour: Optional[int],
                   start_price: float, floor_price: float,
                   listed_hour: int) -> int:
    """Deterministic pseudo-random watcher count that rises as price falls.

    Seeded by item_id for stability between reruns.
    """
    seed = int(hashlib.md5(item_id.encode()).hexdigest()[:8], 16)
    base = (seed % 5) + 2  # 2–6 base watchers
    if departure_hour is not None and departure_hour > listed_hour:
        decay_end = departure_hour - DECAY_END_BEFORE_DEPARTURE
        span = max(1, decay_end - listed_hour)
        frac = max(0.0, min(1.0, (sim_hour - listed_hour) / span))
        extra = int(frac * 12)
    else:
        extra = 0
    return base + extra


# ── Impact math ────────────────────────────────────────────────────────────

def impact_sale_or_transfer(category: str) -> dict[str, float]:
    """Impact of a sale or staff transfer (item stays in-situ)."""
    cat = CATEGORIES[category]
    return {
        "co2_avoided_kg": cat["embodied_co2e"] + LOGISTICS_CO2_PER_TRANSFER,
        "waste_diverted_kg": cat["tare_kg"],
        "volume_diverted_m3": cat["volume_m3"],
    }


def impact_rental(category: str, substitution_rate: float = 0.5) -> dict[str, float]:
    """Impact of a completed rental."""
    cat = CATEGORIES[category]
    return {
        "co2_avoided_kg": cat["embodied_co2e"] * substitution_rate,
        "waste_diverted_kg": 0.0,
        "volume_diverted_m3": 0.0,
    }


def aggregate_impact(
    items: list[dict],
    transactions: list[dict],
    rentals: list[dict],
    substitution_rate: float = 0.5,
) -> dict[str, float]:
    """Aggregate impact across all settled/routed sales and completed rentals."""
    totals = {
        "co2_avoided_kg": 0.0,
        "waste_diverted_kg": 0.0,
        "volume_diverted_m3": 0.0,
        "rupees_saved": 0.0,
        "rental_income": 0.0,
        "items_diverted": 0,
        "rentals_completed": 0,
    }

    for item in items:
        if item["status"] in ("SETTLED", "STAFF_ROUTED"):
            imp = impact_sale_or_transfer(item["category"])
            totals["co2_avoided_kg"] += imp["co2_avoided_kg"]
            totals["waste_diverted_kg"] += imp["waste_diverted_kg"]
            totals["volume_diverted_m3"] += imp["volume_diverted_m3"]
            totals["items_diverted"] += 1
            # Rupees saved = difference between start and settled price
            settled_price = item.get("settled_price", 0)
            totals["rupees_saved"] += item["start_price"] - settled_price

    for rental in rentals:
        if rental.get("completed"):
            imp = impact_rental(rental["category"], substitution_rate)
            totals["co2_avoided_kg"] += imp["co2_avoided_kg"]
            totals["rentals_completed"] += 1
            totals["rental_income"] += rental.get("rent_paid", 0)

    return totals


# ── Rental calculations ───────────────────────────────────────────────────

def rental_cost(start_price: float, period: str) -> float:
    """Rental cost for a given period, rounded to ₹1."""
    rate = RENT_RATES[period]["fraction"]
    return round(start_price * rate)


def rental_deposit(start_price: float) -> float:
    """Deposit amount for a rental."""
    return round(start_price * DEPOSIT_FRACTION)


def can_rent_departing(
    departure_hour: Optional[int],
    sim_hour: int,
    period: str,
) -> tuple[bool, str]:
    """Check if a departing item can be rented for the given period.

    Rule: hours_remaining >= duration_hours + 24
    Returns (allowed, reason).
    """
    if departure_hour is None:
        return True, ""
    hr = hours_remaining(departure_hour, sim_hour)
    if hr is None:
        return True, ""
    duration = RENT_RATES[period]["hours"]
    needed = duration + 24
    if hr >= needed:
        return True, ""
    return False, (
        f"Rental ends too close to owner's departure. "
        f"Need {needed}h remaining, only {hr:.0f}h left."
    )


def rent_to_own_price(
    current_dutch_price: float,
    floor_price: float,
    total_rent_paid: float,
) -> tuple[float, float, float]:
    """Compute the rent-to-own conversion price.

    Returns (buy_price, credit, current_dutch_price).
    """
    credit = total_rent_paid * RENT_TO_OWN_CREDIT_FRACTION
    buy_price = max(floor_price, current_dutch_price - credit)
    return buy_price, credit, current_dutch_price


# ── Validation ─────────────────────────────────────────────────────────────

def validate_listing(
    start_price: float,
    floor_price: float,
) -> tuple[bool, str]:
    """Validate a new item listing.

    Rules: floor > 0, floor < start.
    """
    if floor_price <= 0:
        return False, "Floor price must be greater than ₹0."
    if floor_price >= start_price:
        return False, "Floor price must be less than the starting price."
    return True, ""


def can_claim(
    buyer: str,
    item: dict,
    items: list[dict],
    wallet: float,
    price: float,
) -> tuple[bool, str]:
    """Check if a student can claim an item.

    Rules:
      - Cannot claim own item
      - Max 1 item per category per student (anti-hoarding)
      - Sufficient wallet balance
    """
    if buyer == item["owner"]:
        return False, "You cannot claim your own item."

    # Anti-hoarding: check for existing claims in same category
    cat = item["category"]
    for it in items:
        if (it["id"] != item["id"]
                and it.get("buyer") == buyer
                and it["category"] == cat
                and it["status"] in ("CLAIMED_ESCROW", "SETTLED")):
            return False, f"Anti-hoarding: you already have a {cat} claimed or purchased."

    if wallet < price:
        return False, f"Insufficient balance. Need ₹{price:.0f}, have ₹{wallet:.0f}."

    return True, ""


# ── No-dues check ──────────────────────────────────────────────────────────

def unresolved_items(owner: str, items: list[dict], sim_hour: int) -> list[dict]:
    """Items owned by this student that are not yet settled, routed, or keeper."""
    result = []
    for it in items:
        if it["owner"] != owner:
            continue
        if it.get("departure_hour") is None:
            continue  # keeper items don't block no-dues
        status = effective_status(it, sim_hour)
        if status not in ("SETTLED", "STAFF_ROUTED"):
            result.append(it)
    return result
