"""
Unit tests for civic-lens core metrics.
Run with: pytest tests/test_metrics.py -v

Tests use hand-calculated known inputs/outputs.
A function without a passing test is NOT DONE — see Definition of Done.
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'models'))

from metrics import (vote_share_swing, turnout_delta, fragmentation_index,
                     seat_change, volatility_score, swing_concentration)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def simple_two_party():
    """Two-party borough, two years. Known swing = +5pp for Party A."""
    return pd.DataFrame([
        {"borough": "TestBorough", "party": "A", "vote_share": 0.40, "year": 2022, "seats": 20, "turnout": 0.35},
        {"borough": "TestBorough", "party": "B", "vote_share": 0.60, "year": 2022, "seats": 30, "turnout": 0.35},
        {"borough": "TestBorough", "party": "A", "vote_share": 0.45, "year": 2025, "seats": 25, "turnout": 0.38},
        {"borough": "TestBorough", "party": "B", "vote_share": 0.55, "year": 2025, "seats": 25, "turnout": 0.38},
    ])

@pytest.fixture
def equal_three_party():
    """Three parties with equal vote share — FI should equal 3.0."""
    return pd.DataFrame([
        {"borough": "TestBorough", "party": p, "vote_share": 1/3, "year": 2022}
        for p in ["A", "B", "C"]
    ])

@pytest.fixture
def monopoly_party():
    """One party with 100% vote share — FI should equal 1.0."""
    return pd.DataFrame([
        {"borough": "TestBorough", "party": "A", "vote_share": 1.0, "year": 2022}
    ])


# ── vote_share_swing ──────────────────────────────────────────────────────────

class TestVoteShareSwing:
    def test_positive_swing(self, simple_two_party):
        result = vote_share_swing(simple_two_party)
        a_swing = result[(result["party"] == "A")]["swing_pp"].values[0]
        assert abs(a_swing - 5.0) < 0.01, f"Expected +5pp, got {a_swing}"

    def test_negative_swing(self, simple_two_party):
        result = vote_share_swing(simple_two_party)
        b_swing = result[(result["party"] == "B")]["swing_pp"].values[0]
        assert abs(b_swing - (-5.0)) < 0.01, f"Expected -5pp, got {b_swing}"

    def test_swings_sum_to_zero(self, simple_two_party):
        result = vote_share_swing(simple_two_party)
        assert abs(result["swing_pp"].sum()) < 0.01, "Swings must sum to 0"

    def test_output_columns(self, simple_two_party):
        result = vote_share_swing(simple_two_party)
        assert {"party", "swing_pp"}.issubset(result.columns)


# ── turnout_delta ─────────────────────────────────────────────────────────────

class TestTurnoutDelta:
    def test_positive_delta(self, simple_two_party):
        result = turnout_delta(simple_two_party)
        delta = result[result["area"] == "TestBorough"]["turnout_delta_pp"].values[0]
        assert abs(delta - 3.0) < 0.01, f"Expected +3pp, got {delta}"

    def test_output_columns(self, simple_two_party):
        result = turnout_delta(simple_two_party)
        assert {"area", "turnout_delta_pp"}.issubset(result.columns)


# ── fragmentation_index ───────────────────────────────────────────────────────

class TestFragmentationIndex:
    def test_equal_three_party(self, equal_three_party):
        result = fragmentation_index(equal_three_party)
        fi = result[result["area"] == "TestBorough"]["fragmentation_index"].values[0]
        assert abs(fi - 3.0) < 0.01, f"Expected FI=3.0 for equal three-party, got {fi}"

    def test_monopoly(self, monopoly_party):
        result = fragmentation_index(monopoly_party)
        fi = result[result["area"] == "TestBorough"]["fragmentation_index"].values[0]
        assert abs(fi - 1.0) < 0.01, f"Expected FI=1.0 for monopoly, got {fi}"

    def test_fi_always_positive(self, simple_two_party):
        result = fragmentation_index(simple_two_party)
        assert (result["fragmentation_index"] > 0).all()


# ── seat_change ───────────────────────────────────────────────────────────────

class TestSeatChange:
    def test_seat_gain(self, simple_two_party):
        result = seat_change(simple_two_party)
        a_change = result[(result["party"] == "A")]["seat_change"].values[0]
        assert a_change == 5, f"Expected +5 seats, got {a_change}"

    def test_seat_loss(self, simple_two_party):
        result = seat_change(simple_two_party)
        b_change = result[(result["party"] == "B")]["seat_change"].values[0]
        assert b_change == -5, f"Expected -5 seats, got {b_change}"


# ── swing_concentration ───────────────────────────────────────────────────────

class TestSwingConcentration:
    def test_equal_swing_equals_one(self):
        """If all parties have equal absolute swing, SC = 1."""
        df = pd.DataFrame([
            {"borough": "Test", "party": p, "vote_share": vs_t0, "year": 2022}
            for p, vs_t0 in [("A", 0.5), ("B", 0.5)]
        ] + [
            {"borough": "Test", "party": p, "vote_share": vs_t1, "year": 2025}
            for p, vs_t1 in [("A", 0.6), ("B", 0.4)]
        ])
        swing_df = vote_share_swing(df)
        result = swing_concentration(swing_df)
        sc = result["swing_concentration"].values[0]
        assert abs(sc - 1.0) < 0.01, f"Expected SC=1.0 for equal swing, got {sc}"

    def test_concentrated_swing_above_one(self):
        """Swing dominated by one party should produce SC > 1."""
        df = pd.DataFrame([
            {"borough": "Test", "party": "A", "vote_share": 0.10, "year": 2022},
            {"borough": "Test", "party": "B", "vote_share": 0.45, "year": 2022},
            {"borough": "Test", "party": "C", "vote_share": 0.45, "year": 2022},
            {"borough": "Test", "party": "A", "vote_share": 0.40, "year": 2025},
            {"borough": "Test", "party": "B", "vote_share": 0.35, "year": 2025},
            {"borough": "Test", "party": "C", "vote_share": 0.25, "year": 2025},
        ])
        swing_df = vote_share_swing(df)
        result = swing_concentration(swing_df)
        sc = result["swing_concentration"].values[0]
        assert sc > 1.0, f"Expected SC > 1.0 for concentrated swing, got {sc}"
