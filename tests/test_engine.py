"""
Tests for rio.engine — pricing, impact, rent-to-own, status derivation.
"""

import pytest
from rio.engine import (
    dutch_price, effective_status, urgency_badge, hours_remaining,
    watchers_count, impact_sale_or_transfer, impact_rental,
    aggregate_impact, rental_cost, rental_deposit, can_rent_departing,
    rent_to_own_price, validate_listing, can_claim, unresolved_items,
    CATEGORIES, LOGISTICS_CO2_PER_TRANSFER, DECAY_END_BEFORE_DEPARTURE,
)


# ── Dutch auction pricing ─────────────────────────────────────────────────

class TestDutchPrice:
    """Test dutch_price at key time points."""

    def test_at_t0_equals_start(self):
        """At listing time, price should equal start price (rounded to 5)."""
        p = dutch_price(1800, 500, listed_hour=0, departure_hour=168,
                        sim_hour=0, alpha=1.0)
        assert p == 1800

    def test_at_midpoint(self):
        """At midpoint with alpha=1, price should be halfway between start and floor."""
        # decay_end = 168 - 2 = 166. midpoint = 83
        p = dutch_price(1800, 500, listed_hour=0, departure_hour=168,
                        sim_hour=83, alpha=1.0)
        # frac = 83/166 = 0.5, price = max(500, 1800 - 0.5 * 1300) = 1150
        assert p == 1150

    def test_at_decay_end_equals_floor(self):
        """At departure_hour - 2, price should equal floor."""
        p = dutch_price(1800, 500, listed_hour=0, departure_hour=168,
                        sim_hour=166, alpha=1.0)
        assert p == 500

    def test_at_cutoff_still_floor(self):
        """At departure_hour - 1 (staff cutoff), price should still be floor."""
        p = dutch_price(1800, 500, listed_hour=0, departure_hour=168,
                        sim_hour=167, alpha=1.0)
        assert p == 500

    def test_past_departure_equals_floor(self):
        """Past departure, price remains at floor."""
        p = dutch_price(1800, 500, listed_hour=0, departure_hour=168,
                        sim_hour=200, alpha=1.0)
        assert p == 500

    def test_rounded_to_5(self):
        """Price should be rounded to nearest ₹5."""
        # Choose values that would produce a non-multiple-of-5
        p = dutch_price(1000, 100, listed_hour=0, departure_hour=102,
                        sim_hour=50, alpha=1.0)
        assert p % 5 == 0

    def test_alpha_effect(self):
        """Higher alpha keeps prices higher early on."""
        p_low = dutch_price(1800, 500, 0, 168, sim_hour=40, alpha=1.0)
        p_high = dutch_price(1800, 500, 0, 168, sim_hour=40, alpha=2.0)
        assert p_high >= p_low

    def test_floor_never_breached(self):
        """Price never goes below floor."""
        for t in range(0, 400):
            p = dutch_price(1800, 500, 0, 168, sim_hour=t, alpha=1.5)
            assert p >= 500


# ── Status derivation ─────────────────────────────────────────────────────

class TestEffectiveStatus:
    def _item(self, status="ACTIVE", departure_hour=168):
        return {"status": status, "departure_hour": departure_hour}

    def test_active_well_before_departure(self):
        assert effective_status(self._item(), sim_hour=0) == "ACTIVE"

    def test_active_at_cutoff(self):
        """Within 1 hour of departure, ACTIVE → STAFF_RESERVE."""
        assert effective_status(self._item(), sim_hour=167) == "STAFF_RESERVE"

    def test_active_past_departure(self):
        assert effective_status(self._item(), sim_hour=168) == "STAFF_RESERVE"

    def test_rented_at_cutoff(self):
        """Within 1 hour of departure, RENTED → RETURN_DUE."""
        assert effective_status(self._item("RENTED"), sim_hour=167) == "RETURN_DUE"

    def test_keeper_always_returns_stored(self):
        it = self._item(departure_hour=None)
        assert effective_status(it, sim_hour=999) == "ACTIVE"

    def test_settled_unchanged(self):
        assert effective_status(self._item("SETTLED"), sim_hour=167) == "SETTLED"


# ── Urgency badge ──────────────────────────────────────────────────────────

class TestUrgencyBadge:
    def test_fresh(self):
        assert urgency_badge(168, sim_hour=0) == "FRESH"

    def test_dropping(self):
        # hours_remaining = 168 - 120 = 48; 3 < 48, but not > 48, so DROPPING
        assert urgency_badge(168, sim_hour=120) == "DROPPING"

    def test_critical(self):
        assert urgency_badge(168, sim_hour=166) == "CRITICAL"

    def test_keeper(self):
        assert urgency_badge(None, sim_hour=0) == "KEEPER"


# ── Watchers ───────────────────────────────────────────────────────────────

class TestWatchers:
    def test_deterministic(self):
        """Same inputs produce same output."""
        w1 = watchers_count("item_01", 50, 168, 1800, 500, 0)
        w2 = watchers_count("item_01", 50, 168, 1800, 500, 0)
        assert w1 == w2

    def test_rises_with_time(self):
        """Watchers increase as sim_hour advances."""
        w_early = watchers_count("item_01", 10, 168, 1800, 500, 0)
        w_late = watchers_count("item_01", 160, 168, 1800, 500, 0)
        assert w_late >= w_early


# ── Impact math ────────────────────────────────────────────────────────────

class TestImpact:
    def test_sale_impact(self):
        imp = impact_sale_or_transfer("Air cooler")
        assert imp["co2_avoided_kg"] == pytest.approx(62.0 + 2.2)
        assert imp["waste_diverted_kg"] == pytest.approx(14.5)
        assert imp["volume_diverted_m3"] == pytest.approx(0.28)

    def test_rental_impact(self):
        imp = impact_rental("Air cooler", substitution_rate=0.5)
        assert imp["co2_avoided_kg"] == pytest.approx(62.0 * 0.5)
        assert imp["waste_diverted_kg"] == 0.0

    def test_aggregate_empty(self):
        totals = aggregate_impact([], [], [], 0.5)
        assert totals["co2_avoided_kg"] == 0.0
        assert totals["items_diverted"] == 0

    def test_aggregate_with_data(self):
        items = [
            {"status": "SETTLED", "category": "Air cooler",
             "start_price": 1800, "settled_price": 500},
        ]
        rentals = [
            {"completed": True, "category": "Foam mattress", "rent_paid": 120},
        ]
        totals = aggregate_impact(items, [], rentals, 0.5)
        assert totals["co2_avoided_kg"] == pytest.approx(64.2 + 22.0)
        assert totals["items_diverted"] == 1
        assert totals["rentals_completed"] == 1
        assert totals["rupees_saved"] == pytest.approx(1300)


# ── Rental calculations ───────────────────────────────────────────────────

class TestRentals:
    def test_rental_cost_day(self):
        assert rental_cost(1800, "Day") == 36

    def test_rental_cost_week(self):
        assert rental_cost(1800, "Week") == 180

    def test_rental_cost_month(self):
        assert rental_cost(1800, "Month") == 450

    def test_deposit(self):
        assert rental_deposit(1800) == 360

    def test_can_rent_keeper(self):
        ok, _ = can_rent_departing(None, 0, "Week")
        assert ok

    def test_can_rent_enough_time(self):
        # 168h remaining, week = 168h + 24h buffer = 192h needed. Not enough.
        ok, msg = can_rent_departing(168, 0, "Week")
        assert not ok
        assert "too close" in msg.lower()

    def test_can_rent_day_ok(self):
        # Day = 24h + 24h buffer = 48h needed. 168h remaining. OK.
        ok, _ = can_rent_departing(168, 0, "Day")
        assert ok


# ── Rent-to-own ────────────────────────────────────────────────────────────

class TestRentToOwn:
    def test_credit_applied(self):
        buy_p, credit, _ = rent_to_own_price(1000, 300, total_rent_paid=200)
        # credit = 200 * 0.5 = 100, buy = max(300, 1000 - 100) = 900
        assert credit == pytest.approx(100)
        assert buy_p == pytest.approx(900)

    def test_floor_clamp(self):
        """Rent credit should never push price below floor."""
        buy_p, credit, _ = rent_to_own_price(400, 300, total_rent_paid=500)
        # credit = 250, buy = max(300, 400 - 250) = max(300, 150) = 300
        assert buy_p == 300

    def test_zero_rent(self):
        buy_p, credit, _ = rent_to_own_price(1000, 300, total_rent_paid=0)
        assert credit == 0
        assert buy_p == 1000


# ── Validation ─────────────────────────────────────────────────────────────

class TestValidation:
    def test_valid_listing(self):
        ok, _ = validate_listing(1000, 300)
        assert ok

    def test_floor_equals_start(self):
        ok, msg = validate_listing(1000, 1000)
        assert not ok
        assert "less than" in msg.lower()

    def test_floor_exceeds_start(self):
        ok, msg = validate_listing(1000, 1500)
        assert not ok

    def test_floor_zero(self):
        ok, msg = validate_listing(1000, 0)
        assert not ok
        assert "greater than" in msg.lower()


# ── Can-claim checks ──────────────────────────────────────────────────────

class TestCanClaim:
    def _item(self, cat="Air cooler", owner="Aarav"):
        return {
            "id": "test_item", "owner": owner, "category": cat,
            "status": "ACTIVE", "buyer": None,
        }

    def test_cannot_claim_own(self):
        ok, msg = can_claim("Aarav", self._item(), [], 3000, 500)
        assert not ok
        assert "own item" in msg.lower()

    def test_anti_hoarding(self):
        existing = [{
            "id": "other", "buyer": "Priya", "category": "Air cooler",
            "status": "CLAIMED_ESCROW",
        }]
        ok, msg = can_claim("Priya", self._item(), existing, 3000, 500)
        assert not ok
        assert "anti-hoarding" in msg.lower()

    def test_insufficient_wallet(self):
        ok, msg = can_claim("Priya", self._item(), [], 100, 500)
        assert not ok
        assert "insufficient" in msg.lower()

    def test_valid_claim(self):
        ok, _ = can_claim("Priya", self._item(), [], 3000, 500)
        assert ok


# ── No-dues ────────────────────────────────────────────────────────────────

class TestNoDues:
    def test_unresolved_active_departing(self):
        items = [{"owner": "Aarav", "status": "ACTIVE", "departure_hour": 168}]
        result = unresolved_items("Aarav", items, sim_hour=0)
        assert len(result) == 1

    def test_settled_not_unresolved(self):
        items = [{"owner": "Aarav", "status": "SETTLED", "departure_hour": 168}]
        result = unresolved_items("Aarav", items, sim_hour=0)
        assert len(result) == 0

    def test_keeper_ignored(self):
        items = [{"owner": "Aarav", "status": "ACTIVE", "departure_hour": None}]
        result = unresolved_items("Aarav", items, sim_hour=0)
        assert len(result) == 0
