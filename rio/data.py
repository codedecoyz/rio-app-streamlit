"""
RIO Seed Data — deterministic, pre-seeded state for the demo.

6 students, 1 warden, 2 support staff, ~14 items, and pre-seeded history.
"""

from __future__ import annotations

import copy
from typing import Any


def build_users() -> dict[str, dict[str, Any]]:
    """Create the 6 students + warden + 2 staff."""
    students = [
        {"name": "Aarav",  "block": "Hostel Block B", "room": "201", "departure_hour": 168},
        {"name": "Priya",  "block": "Hostel Block B", "room": "304", "departure_hour": 240},
        {"name": "Rohan",  "block": "Hostel Block B", "room": "112", "departure_hour": 300},
        {"name": "Sneha",  "block": "Hostel Block B", "room": "215", "departure_hour": 336},
        {"name": "Karan",  "block": "Sai Meadows PG", "room": "12",  "departure_hour": 240},
        {"name": "Meera",  "block": "Hostel Block B", "room": "408", "departure_hour": 168},
    ]
    users: dict[str, dict[str, Any]] = {}
    for s in students:
        users[s["name"]] = {
            **s,
            "role": "student",
            "wallet": 3000.0,
        }
    users["Warden"] = {
        "name": "Warden", "role": "warden", "wallet": 0.0,
        "block": "Hostel Block B", "room": "Office", "departure_hour": None,
    }
    users["Ramesh (Staff)"] = {
        "name": "Ramesh (Staff)", "role": "staff", "wallet": 0.0,
        "block": "Hostel Block B", "room": "Quarters", "departure_hour": None,
    }
    users["Sunita (Staff)"] = {
        "name": "Sunita (Staff)", "role": "staff", "wallet": 0.0,
        "block": "Hostel Block B", "room": "Quarters", "departure_hour": None,
    }
    return users


def build_items() -> list[dict[str, Any]]:
    """Create ~14 seed items mixing categories, departure times, and keeper items."""
    items = [
        # ── Aarav's items (departing day 7 = 168h) ──
        {
            "id": "item_01", "owner": "Aarav",
            "title": "Symphony 35L Desert Air Cooler",
            "category": "Air cooler",
            "block": "Hostel Block B", "room": "201",
            "start_price": 1800, "floor_price": 500,
            "listed_hour": 0, "departure_hour": 168,
            "rentable": True, "status": "ACTIVE",
            "buyer": None, "renter": None, "settled_price": None,
        },
        {
            "id": "item_02", "owner": "Aarav",
            "title": "Sleepwell 4-inch Foam Mattress",
            "category": "Foam mattress",
            "block": "Hostel Block B", "room": "201",
            "start_price": 1200, "floor_price": 300,
            "listed_hour": 0, "departure_hour": 168,
            "rentable": True, "status": "ACTIVE",
            "buyer": None, "renter": None, "settled_price": None,
        },
        # ── Priya's items (departing day 10 = 240h) ──
        {
            "id": "item_03", "owner": "Priya",
            "title": "Bajaj 1.5L Electric Kettle",
            "category": "Kettle/immersion",
            "block": "Hostel Block B", "room": "304",
            "start_price": 500, "floor_price": 150,
            "listed_hour": 0, "departure_hour": 240,
            "rentable": True, "status": "ACTIVE",
            "buyer": None, "renter": None, "settled_price": None,
        },
        {
            "id": "item_04", "owner": "Priya",
            "title": "Nilkamal Study Table + Chair Set",
            "category": "Study table+chair",
            "block": "Hostel Block B", "room": "304",
            "start_price": 1500, "floor_price": 400,
            "listed_hour": 0, "departure_hour": 240,
            "rentable": True, "status": "ACTIVE",
            "buyer": None, "renter": None, "settled_price": None,
        },
        # ── Rohan's items (departing day 12.5 = 300h) ──
        {
            "id": "item_05", "owner": "Rohan",
            "title": "Mini Drafter, barely used",
            "category": "Drafter+board",
            "block": "Hostel Block B", "room": "112",
            "start_price": 450, "floor_price": 150,
            "listed_hour": 0, "departure_hour": 300,
            "rentable": True, "status": "ACTIVE",
            "buyer": None, "renter": None, "settled_price": None,
        },
        {
            "id": "item_06", "owner": "Rohan",
            "title": "Crompton Oasis 27L Air Cooler",
            "category": "Air cooler",
            "block": "Hostel Block B", "room": "112",
            "start_price": 1800, "floor_price": 500,
            "listed_hour": 0, "departure_hour": 300,
            "rentable": True, "status": "ACTIVE",
            "buyer": None, "renter": None, "settled_price": None,
        },
        # ── Sneha's items (departing day 14 = 336h) ──
        {
            "id": "item_07", "owner": "Sneha",
            "title": "Wakefit Memory Foam Mattress 72x36",
            "category": "Foam mattress",
            "block": "Hostel Block B", "room": "215",
            "start_price": 1200, "floor_price": 300,
            "listed_hour": 0, "departure_hour": 336,
            "rentable": True, "status": "ACTIVE",
            "buyer": None, "renter": None, "settled_price": None,
        },
        {
            "id": "item_08", "owner": "Sneha",
            "title": "Portable Immersion Heater (1500W)",
            "category": "Kettle/immersion",
            "block": "Hostel Block B", "room": "215",
            "start_price": 500, "floor_price": 150,
            "listed_hour": 0, "departure_hour": 336,
            "rentable": False, "status": "ACTIVE",
            "buyer": None, "renter": None, "settled_price": None,
        },
        # ── Karan's items (departing day 10 = 240h, from PG) ──
        {
            "id": "item_09", "owner": "Karan",
            "title": "Folding Study Table (Ikea style)",
            "category": "Study table+chair",
            "block": "Sai Meadows PG", "room": "12",
            "start_price": 1500, "floor_price": 400,
            "listed_hour": 0, "departure_hour": 240,
            "rentable": True, "status": "ACTIVE",
            "buyer": None, "renter": None, "settled_price": None,
        },
        {
            "id": "item_10", "owner": "Karan",
            "title": "Drawing Board A2 with Drafter",
            "category": "Drafter+board",
            "block": "Sai Meadows PG", "room": "12",
            "start_price": 450, "floor_price": 150,
            "listed_hour": 0, "departure_hour": 240,
            "rentable": True, "status": "ACTIVE",
            "buyer": None, "renter": None, "settled_price": None,
        },
        # ── Meera's items (departing day 7 = 168h) ──
        {
            "id": "item_11", "owner": "Meera",
            "title": "Havells 1L Kettle (Steel)",
            "category": "Kettle/immersion",
            "block": "Hostel Block B", "room": "408",
            "start_price": 500, "floor_price": 150,
            "listed_hour": 0, "departure_hour": 168,
            "rentable": True, "status": "ACTIVE",
            "buyer": None, "renter": None, "settled_price": None,
        },
        # ── Keeper items (no departure, rent only) ──
        {
            "id": "item_12", "owner": "Rohan",
            "title": "Kenstar 20L Personal Cooler (staying)",
            "category": "Air cooler",
            "block": "Hostel Block B", "room": "112",
            "start_price": 1800, "floor_price": 500,
            "listed_hour": 0, "departure_hour": None,
            "rentable": True, "status": "ACTIVE",
            "buyer": None, "renter": None, "settled_price": None,
        },
        {
            "id": "item_13", "owner": "Sneha",
            "title": "Large Study Desk (not leaving)",
            "category": "Study table+chair",
            "block": "Hostel Block B", "room": "215",
            "start_price": 1500, "floor_price": 400,
            "listed_hour": 0, "departure_hour": None,
            "rentable": True, "status": "ACTIVE",
            "buyer": None, "renter": None, "settled_price": None,
        },
        {
            "id": "item_14", "owner": "Priya",
            "title": "Springtek 5-inch Mattress (staying)",
            "category": "Foam mattress",
            "block": "Hostel Block B", "room": "304",
            "start_price": 1200, "floor_price": 300,
            "listed_hour": 0, "departure_hour": None,
            "rentable": True, "status": "ACTIVE",
            "buyer": None, "renter": None, "settled_price": None,
        },
    ]
    return items


def build_preseed_history(
    items: list[dict[str, Any]],
    users: dict[str, dict[str, Any]],
) -> tuple[list[dict], list[dict]]:
    """Pre-seed 3 SETTLED sales and 5 completed rentals with matching ledger entries.

    Modifies items in-place to mark some as SETTLED, and adjusts wallets.
    Returns (transactions, rentals).
    """
    transactions: list[dict[str, Any]] = []
    rentals: list[dict[str, Any]] = []

    # ── 3 pre-seeded SETTLED sales ──
    # Sale 1: Sneha bought item_11 (Meera's kettle) at ₹350
    _settle_sale(items, users, transactions,
                 item_id="item_11", buyer="Sneha", price=350, hour=48)

    # Sale 2: Aarav bought item_10 (Karan's drafter) at ₹300
    _settle_sale(items, users, transactions,
                 item_id="item_10", buyer="Aarav", price=300, hour=72)

    # Sale 3: Karan bought item_02 (Aarav's mattress) at ₹800
    _settle_sale(items, users, transactions,
                 item_id="item_02", buyer="Karan", price=800, hour=96)

    # ── 5 pre-seeded completed rentals ──
    _complete_rental(items, users, transactions, rentals,
                     item_id="item_12", renter="Priya", period="Week",
                     rent_paid=180, deposit=360, start_hour=10, category="Air cooler")
    _complete_rental(items, users, transactions, rentals,
                     item_id="item_13", renter="Aarav", period="Day",
                     rent_paid=30, deposit=300, start_hour=20, category="Study table+chair")
    _complete_rental(items, users, transactions, rentals,
                     item_id="item_14", renter="Rohan", period="Week",
                     rent_paid=120, deposit=240, start_hour=5, category="Foam mattress")
    _complete_rental(items, users, transactions, rentals,
                     item_id="item_12", renter="Sneha", period="Day",
                     rent_paid=36, deposit=360, start_hour=200, category="Air cooler")
    _complete_rental(items, users, transactions, rentals,
                     item_id="item_13", renter="Meera", period="Day",
                     rent_paid=30, deposit=300, start_hour=180, category="Study table+chair")

    return transactions, rentals


def _settle_sale(
    items: list[dict], users: dict, transactions: list[dict],
    item_id: str, buyer: str, price: float, hour: int,
) -> None:
    """Mark an item as SETTLED and create ledger entries."""
    for it in items:
        if it["id"] == item_id:
            it["status"] = "SETTLED"
            it["buyer"] = buyer
            it["settled_price"] = price
            owner = it["owner"]
            # Adjust wallets
            users[buyer]["wallet"] -= price
            users[owner]["wallet"] += price
            # Ledger
            transactions.append({
                "hour": hour, "type": "PURCHASE",
                "user": buyer, "amount": -price,
                "note": f"Bought '{it['title']}' from {owner}",
                "item_id": item_id,
            })
            transactions.append({
                "hour": hour, "type": "SALE",
                "user": owner, "amount": price,
                "note": f"Sold '{it['title']}' to {buyer}",
                "item_id": item_id,
            })
            break


def _complete_rental(
    items: list[dict], users: dict, transactions: list[dict],
    rentals: list[dict],
    item_id: str, renter: str, period: str,
    rent_paid: float, deposit: float, start_hour: int,
    category: str,
) -> None:
    """Record a completed rental with ledger entries."""
    owner = None
    for it in items:
        if it["id"] == item_id:
            owner = it["owner"]
            break
    if owner is None:
        return

    # Wallet adjustments (rent paid, deposit refunded)
    users[renter]["wallet"] -= rent_paid  # rent cost
    users[owner]["wallet"] += rent_paid   # owner earns

    transactions.append({
        "hour": start_hour, "type": "RENTAL",
        "user": renter, "amount": -rent_paid,
        "note": f"Rented item ({period})",
        "item_id": item_id,
    })
    transactions.append({
        "hour": start_hour, "type": "RENTAL_INCOME",
        "user": owner, "amount": rent_paid,
        "note": f"Rental income ({period})",
        "item_id": item_id,
    })
    rentals.append({
        "id": f"rental_{len(rentals)+1:03d}",
        "item_id": item_id, "renter": renter, "owner": owner,
        "period": period, "rent_paid": rent_paid, "deposit": deposit,
        "start_hour": start_hour, "completed": True,
        "category": category,
    })


def build_initial_state() -> dict[str, Any]:
    """Build the complete initial session state."""
    users = build_users()
    items = build_items()
    transactions, rentals = build_preseed_history(items, users)

    return {
        "initialized": True,
        "sim_hour": 0,
        "current_user": "Aarav",
        "alpha": 1.0,
        "substitution_rate": 0.5,
        "users": users,
        "items": items,
        "transactions": transactions,
        "rentals": rentals,
        "no_dues": {
            "Aarav": False, "Priya": False, "Rohan": False,
            "Sneha": False, "Karan": False, "Meera": False,
        },
        "next_item_id": 15,
        "next_rental_id": len(rentals) + 1,
    }


def init_state() -> None:
    """Initialize session state from seed data. Guarded: runs only once."""
    import streamlit as st
    if "initialized" not in st.session_state:
        state = build_initial_state()
        for k, v in state.items():
            st.session_state[k] = v

