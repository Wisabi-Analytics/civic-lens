"""tests/test_metrics.py
=====================
Unit tests for all six metric functions in civic_lens.metrics.

ALL test cases use synthetic known-value data only.
No real election data is loaded. Every expected value is hand-verified
in the docstring of the relevant test.

Test inventory
--------------
vote_share_swing
    test_swing_zero                 — identical periods → all swings = 0
    test_swing_simple_gain          — one party gains, one loses
    test_swing_new_party            — party present in t, absent in t−1
    test_swing_party_exits          — party present in t−1, absent in t
    test_swing_multi_party          — three parties, mixed directions
    test_swing_nan_dropped          — NaN shares excluded
    test_swing_both_empty           — both dicts empty → empty result

turnout_delta
    test_turnout_increase           — positive delta
    test_turnout_decrease           — negative delta
    test_turnout_none_t             — current turnout None → None
    test_turnout_none_t1            — prior turnout None → None
    test_turnout_both_none          — both None → None
    test_turnout_zero               — no change → 0.0

fragmentation_index
    test_fi_single_party            — 100% one party → FI = 1.0
    test_fi_two_equal               — 50/50 → FI = 2.0
    test_fi_four_equal              — 25/25/25/25 → FI = 4.0
    test_fi_three_unequal           — known unequal distribution, hand-verified
    test_fi_normalises_rounding     — shares summing to 99.9 → stable result
    test_fi_drops_zero_shares       — zero-share party excluded from sum
    test_fi_drops_nan               — NaN share dropped, rest computed
    test_fi_empty_raises            — empty dict → ValueError
    test_fi_all_zero_raises         — all shares = 0 → ValueError

seat_change
    test_seat_gain                  — seats increase
    test_seat_loss                  — seats decrease
    test_seat_no_change             — no change → 0
    test_seat_none_t                — current None → None
    test_seat_none_t1               — prior None → None
    test_seat_to_zero               — party loses all seats

volatility_score
    test_vol_zero_swing_zero_dfi    — S0 baseline → VOL = 0.0
    test_vol_swing_only             — swing component, ΔFI = 0
    test_vol_dfi_only               — ΔFI component, swings = 0
    test_vol_both_components        — hand-verified combined value
    test_vol_negative               — ΔFI negative and large → VOL < 0
    test_vol_none_fi_t              — fi_t None → None
    test_vol_none_fi_t1             — fi_t1 None → None
    test_vol_empty_swings           — empty swings, valid FIs → VOL = 0.5 × ΔFI
    test_vol_nan_swings_dropped     — NaN swings excluded from sum

swing_concentration
    test_sc_all_zero_swings         — frozen rule → 1.0
    test_sc_single_party            — one party → SC = 1.0
    test_sc_equal_swings            — all equal → SC = 1.0
    test_sc_concentrated            — one party dominates → SC = n
    test_sc_two_parties_unequal     — hand-verified two-party case
    test_sc_five_parties            — hand-verified five-party case
    test_sc_empty_raises            — empty dict → ValueError
    test_sc_nan_dropped             — NaN dropped, rest computed
"""

from __future__ import annotations

import math
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from civic_lens.metrics import (
    vote_share_swing,
    turnout_delta,
    fragmentation_index,
    seat_change,
    volatility_score,
    swing_concentration,
)


# ============================================================================
# Helpers
# ============================================================================

def _approx(a: float, b: float, tol: float = 1e-9) -> bool:
    """Absolute tolerance comparison for floats."""
    return abs(a - b) < tol


def _approx_dict(
    result: dict[str, float],
    expected: dict[str, float],
    tol: float = 1e-9,
) -> bool:
    if set(result) != set(expected):
        return False
    return all(_approx(result[k], expected[k], tol) for k in expected)


# ============================================================================
# 1. vote_share_swing
# ============================================================================

class TestVoteShareSwing:

    def test_swing_zero(self):
        """Identical periods → all swings exactly 0.
        Hand-check: LAB 40−40=0, CON 35−35=0, LD 25−25=0.
        """
        shares = {"LAB": 40.0, "CON": 35.0, "LD": 25.0}
        result = vote_share_swing(shares, shares)
        assert _approx_dict(result, {"LAB": 0.0, "CON": 0.0, "LD": 0.0})

    def test_swing_simple_gain(self):
        """LAB gains 5pp, CON loses 5pp.
        Hand-check: LAB 45−40=+5, CON 30−35=−5, LD 25−25=0.
        """
        t  = {"LAB": 45.0, "CON": 30.0, "LD": 25.0}
        t1 = {"LAB": 40.0, "CON": 35.0, "LD": 25.0}
        result = vote_share_swing(t, t1)
        assert _approx_dict(result, {"LAB": 5.0, "CON": -5.0, "LD": 0.0})

    def test_swing_new_party(self):
        """REFORM enters with 15pp; LAB and CON each lose 7.5pp.
        Hand-check: REFORM 15−0=+15, LAB 32.5−40=−7.5, CON 27.5−35=−7.5, LD 25−25=0.
        """
        t  = {"LAB": 32.5, "CON": 27.5, "LD": 25.0, "REFORM": 15.0}
        t1 = {"LAB": 40.0, "CON": 35.0, "LD": 25.0}
        result = vote_share_swing(t, t1)
        assert _approx_dict(
            result,
            {"LAB": -7.5, "CON": -7.5, "LD": 0.0, "REFORM": 15.0},
        )

    def test_swing_party_exits(self):
        """UKIP present in t−1 (10pp), absent in t.
        Hand-check: UKIP 0−10=−10.
        """
        t  = {"LAB": 45.0, "CON": 35.0, "LD": 20.0}
        t1 = {"LAB": 40.0, "CON": 30.0, "LD": 20.0, "UKIP": 10.0}
        result = vote_share_swing(t, t1)
        assert _approx_dict(
            result,
            {"LAB": 5.0, "CON": 5.0, "LD": 0.0, "UKIP": -10.0},
        )

    def test_swing_multi_party(self):
        """Three parties, mixed swing directions.
        Hand-check: LAB 38−42=−4, GREEN 18−12=+6, CON 44−46=−2.
        """
        t  = {"LAB": 38.0, "GREEN": 18.0, "CON": 44.0}
        t1 = {"LAB": 42.0, "GREEN": 12.0, "CON": 46.0}
        result = vote_share_swing(t, t1)
        assert _approx_dict(result, {"LAB": -4.0, "GREEN": 6.0, "CON": -2.0})

    def test_swing_nan_dropped(self):
        """NaN share treated as absent (not as 0 in either direction).
        IND has NaN in t and 5.0 in t−1 → swing = 0 − 5 = −5.
        """
        t  = {"LAB": 50.0, "CON": 45.0, "IND": float("nan")}
        t1 = {"LAB": 45.0, "CON": 45.0, "IND": 5.0}
        result = vote_share_swing(t, t1)
        # IND NaN in t → treated as 0 in t; IND had 5 in t−1 → swing −5
        assert _approx(result["IND"], -5.0)
        assert _approx(result["LAB"],  5.0)
        assert _approx(result["CON"],  0.0)

    def test_swing_both_empty(self):
        """Both dicts empty → empty result, no exception."""
        assert vote_share_swing({}, {}) == {}


# ============================================================================
# 2. turnout_delta
# ============================================================================

class TestTurnoutDelta:

    def test_turnout_increase(self):
        """55.0 − 48.0 = +7.0 pp."""
        assert _approx(turnout_delta(55.0, 48.0), 7.0)

    def test_turnout_decrease(self):
        """38.5 − 45.0 = −6.5 pp."""
        assert _approx(turnout_delta(38.5, 45.0), -6.5)

    def test_turnout_none_t(self):
        """Current turnout missing → None."""
        assert turnout_delta(None, 50.0) is None

    def test_turnout_none_t1(self):
        """Prior turnout missing → None."""
        assert turnout_delta(50.0, None) is None

    def test_turnout_both_none(self):
        """Both missing → None."""
        assert turnout_delta(None, None) is None

    def test_turnout_zero(self):
        """Identical turnouts → 0.0, not None."""
        result = turnout_delta(42.0, 42.0)
        assert result is not None
        assert _approx(result, 0.0)


# ============================================================================
# 3. fragmentation_index
# ============================================================================

class TestFragmentationIndex:

    def test_fi_single_party(self):
        """Single party with 100% share → FI = 1.0.
        Hand-check: 1 / (1.0²) = 1.0.
        """
        assert _approx(fragmentation_index({"LAB": 100.0}), 1.0)

    def test_fi_two_equal(self):
        """Two parties, 50/50 → FI = 2.0.
        Hand-check: proportions = [0.5, 0.5], Σ(VS²) = 0.25+0.25 = 0.5, FI = 2.0.
        """
        assert _approx(fragmentation_index({"LAB": 50.0, "CON": 50.0}), 2.0)

    def test_fi_four_equal(self):
        """Four parties, 25/25/25/25 → FI = 4.0.
        Hand-check: Σ(0.25²) = 4×0.0625 = 0.25, FI = 4.0.
        """
        shares = {"LAB": 25.0, "CON": 25.0, "LD": 25.0, "GREEN": 25.0}
        assert _approx(fragmentation_index(shares), 4.0)

    def test_fi_three_unequal(self):
        """Unequal three-party: 60/30/10.
        Hand-check:
            proportions = [0.6, 0.3, 0.1]
            Σ(VS²) = 0.36 + 0.09 + 0.01 = 0.46
            FI = 1/0.46 ≈ 2.1739...
        """
        result = fragmentation_index({"A": 60.0, "B": 30.0, "C": 10.0})
        assert abs(result - (1.0 / 0.46)) < 1e-6

    def test_fi_normalises_rounding(self):
        """Shares summing to 99.9 instead of 100 → same FI as 50/50 after normalisation.
        Hand-check: [49.95, 49.95] normalises to [0.5, 0.5] → FI = 2.0.
        """
        result = fragmentation_index({"LAB": 49.95, "CON": 49.95})
        assert _approx(result, 2.0, tol=1e-6)

    def test_fi_drops_zero_shares(self):
        """Zero-share party contributes nothing; result equals two-party case.
        Hand-check: only LAB (50) and CON (50) count → FI = 2.0.
        """
        result = fragmentation_index({"LAB": 50.0, "CON": 50.0, "MRLP": 0.0})
        assert _approx(result, 2.0)

    def test_fi_drops_nan(self):
        """NaN share dropped; remaining two equal shares → FI = 2.0."""
        result = fragmentation_index({
            "LAB": 50.0, "CON": 50.0, "IND": float("nan")
        })
        assert _approx(result, 2.0)

    def test_fi_empty_raises(self):
        """Empty dict → ValueError."""
        with pytest.raises(ValueError):
            fragmentation_index({})

    def test_fi_all_zero_raises(self):
        """All zero shares → ValueError (nothing to compute)."""
        with pytest.raises(ValueError):
            fragmentation_index({"LAB": 0.0, "CON": 0.0})


# ============================================================================
# 4. seat_change
# ============================================================================

class TestSeatChange:

    def test_seat_gain(self):
        """Gained 3 seats: 8 − 5 = +3."""
        assert seat_change(8, 5) == 3

    def test_seat_loss(self):
        """Lost 4 seats: 2 − 6 = −4."""
        assert seat_change(2, 6) == -4

    def test_seat_no_change(self):
        """No change: 5 − 5 = 0."""
        assert seat_change(5, 5) == 0

    def test_seat_none_t(self):
        """Current seats unknown → None."""
        assert seat_change(None, 5) is None

    def test_seat_none_t1(self):
        """Prior seats unknown → None."""
        assert seat_change(5, None) is None

    def test_seat_to_zero(self):
        """Party loses all seats: 0 − 4 = −4."""
        assert seat_change(0, 4) == -4


# ============================================================================
# 5. volatility_score
# ============================================================================

class TestVolatilityScore:

    def test_vol_zero_swing_zero_dfi(self):
        """S0 baseline: no swing, no FI change → VOL = 0.0.
        Hand-check: 0.5×0 + 0.5×0 = 0.0.
        """
        swings = {"LAB": 0.0, "CON": 0.0, "LD": 0.0}
        result = volatility_score(swings, fi_t=2.5, fi_t1=2.5)
        assert _approx(result, 0.0)

    def test_vol_swing_only(self):
        """Swing component only (ΔFI = 0).
        Swings: LAB +4, CON −4, LD 0.
        Hand-check: Σ|swing| = |4| + |−4| + |0| = 8; 0.5×8 + 0.5×0 = 4.0.
        """
        swings = {"LAB": 4.0, "CON": -4.0, "LD": 0.0}
        result = volatility_score(swings, fi_t=2.5, fi_t1=2.5)
        assert _approx(result, 4.0)

    def test_vol_dfi_only(self):
        """FI component only (all swings = 0).
        FI: 3.2 → 2.0, ΔFI = −1.2.
        Hand-check: 0.5×0 + 0.5×(−1.2) = −0.6.
        Note: negative VOL is mathematically valid per the frozen formula.
        """
        swings = {"LAB": 0.0, "CON": 0.0}
        result = volatility_score(swings, fi_t=2.0, fi_t1=3.2)
        assert _approx(result, -0.6)

    def test_vol_both_components(self):
        """Both components non-zero.
        Swings: LAB +6, CON −3, LD −3.  FI: 2.4 → 2.8 (ΔFI = +0.4).
        Hand-check: Σ|swing| = 6+3+3 = 12; 0.5×12 + 0.5×0.4 = 6.0 + 0.2 = 6.2.
        """
        swings = {"LAB": 6.0, "CON": -3.0, "LD": -3.0}
        result = volatility_score(swings, fi_t=2.8, fi_t1=2.4)
        assert _approx(result, 6.2)

    def test_vol_negative(self):
        """Negative VOL: ΔFI very negative, small swings.
        Swings: LAB +1, CON −1.  FI: 1.5 → 4.5 (ΔFI = −3.0).
        Hand-check: Σ|swing| = 2; 0.5×2 + 0.5×(−3.0) = 1.0 − 1.5 = −0.5.
        Negative VOL is valid — do not clamp.
        """
        swings = {"LAB": 1.0, "CON": -1.0}
        result = volatility_score(swings, fi_t=1.5, fi_t1=4.5)
        assert _approx(result, -0.5)

    def test_vol_none_fi_t(self):
        """fi_t is None → return None."""
        assert volatility_score({"LAB": 2.0}, fi_t=None, fi_t1=2.5) is None

    def test_vol_none_fi_t1(self):
        """fi_t1 is None → return None."""
        assert volatility_score({"LAB": 2.0}, fi_t=2.5, fi_t1=None) is None

    def test_vol_empty_swings(self):
        """Empty swings dict, valid FIs → VOL = 0.5 × ΔFI only.
        FI: 3.0 → 2.0, ΔFI = −1.0.
        Hand-check: 0.5×0 + 0.5×(−1.0) = −0.5.
        """
        result = volatility_score({}, fi_t=2.0, fi_t1=3.0)
        assert _approx(result, -0.5)

    def test_vol_nan_swings_dropped(self):
        """NaN swings excluded; only valid swings contribute.
        Valid: LAB +4, CON −4. NaN: IND.
        Hand-check: Σ|swing| = 8; 0.5×8 + 0.5×0 = 4.0.
        """
        swings = {"LAB": 4.0, "CON": -4.0, "IND": float("nan")}
        result = volatility_score(swings, fi_t=2.5, fi_t1=2.5)
        assert _approx(result, 4.0)


# ============================================================================
# 6. swing_concentration
# ============================================================================

class TestSwingConcentration:

    def test_sc_all_zero_swings(self):
        """ALL swings = 0 → SC = 1.0 (frozen rule from DATA_DICTIONARY.md).
        Mathematically undefined (0/0), but convention = 1.0.
        """
        assert swing_concentration({"LAB": 0.0, "CON": 0.0, "LD": 0.0}) == 1.0

    def test_sc_single_party(self):
        """Single party: max == mean → SC = 1.0.
        Hand-check: max(|5|) / mean(|5|) = 5/5 = 1.0.
        """
        assert _approx(swing_concentration({"LAB": 5.0}), 1.0)

    def test_sc_equal_swings(self):
        """All equal absolute swings → SC = 1.0.
        Hand-check: max(3)/mean(3) = 3/3 = 1.0 (signs irrelevant; absolute values used).
        """
        assert _approx(
            swing_concentration({"LAB": 3.0, "CON": -3.0, "LD": 3.0}),
            1.0,
        )

    def test_sc_concentrated(self):
        """One party takes all swing; rest are zero.
        Swings: REFORM +12, LAB 0, CON 0, LD 0.
        But wait — zeros are included in the mean!
        abs_swings = [12, 0, 0, 0]; max = 12, mean = 3.
        SC = 12/3 = 4.0.
        """
        swings = {"REFORM": 12.0, "LAB": 0.0, "CON": 0.0, "LD": 0.0}
        assert _approx(swing_concentration(swings), 4.0)

    def test_sc_two_parties_unequal(self):
        """Two parties with unequal absolute swings.
        Swings: A = +8, B = −2.
        abs_swings = [8, 2]; max = 8, mean = 5.
        SC = 8/5 = 1.6.
        """
        assert _approx(swing_concentration({"A": 8.0, "B": -2.0}), 1.6)

    def test_sc_five_parties(self):
        """Five parties, one dominant.
        Swings: REFORM +10, LAB −4, CON −3, LD −2, GREEN −1.
        abs_swings = [10, 4, 3, 2, 1]; max = 10, mean = 4.0.
        SC = 10/4 = 2.5.
        """
        swings = {
            "REFORM": 10.0, "LAB": -4.0, "CON": -3.0,
            "LD": -2.0, "GREEN": -1.0,
        }
        assert _approx(swing_concentration(swings), 2.5)

    def test_sc_empty_raises(self):
        """Empty dict → ValueError."""
        with pytest.raises(ValueError):
            swing_concentration({})

    def test_sc_nan_dropped(self):
        """NaN swing dropped; remaining parties computed correctly.
        Valid: A = +6, B = −6.  NaN: C.
        abs_swings = [6, 6]; max = 6, mean = 6.
        SC = 1.0.
        """
        result = swing_concentration({"A": 6.0, "B": -6.0, "C": float("nan")})
        assert _approx(result, 1.0)



# ============================================================================
# Dataset-driven edge case regression tests
#
# These tests document the caller contracts imposed by the real dataset.
# They do not load real data — all inputs are synthetic representations of
# conditions found in the actual DCLEAPIL and Commons Library files.
#
# Point 4 from the review (wide-party ward pivot) is a Phase 4 loader
# responsibility, not a metric function responsibility.  Those tests belong
# in tests/test_loaders.py (Phase 4).  They are NOT added here.
# ============================================================================

class TestUncOntestEdWardCallerContract:
    """GAP 1 — Uncontested wards (157 rows in training data).

    Uncontested rows have votes=None, derived vote_share=None, and must be
    assigned analysis_level='borough_only' by the pipeline BEFORE any metric
    function is called.  If an upstream bug lets an uncontested row reach
    fragmentation_index or swing_concentration, the functions raise ValueError
    with a clear message rather than silently returning a meaningless result.

    These tests document that contract explicitly.
    """

    def test_fi_all_none_shares_raises(self):
        """Uncontested ward: all vote_share values are None (not derived).
        fragmentation_index must raise — borough_only rows must be filtered
        upstream before reaching this function.
        Hand-check: all None → clean dict is empty → ValueError.
        """
        with pytest.raises(ValueError, match="at least one party"):
            fragmentation_index({"LAB": None, "CON": None, "LD": None})

    def test_sc_all_none_swings_raises(self):
        """Uncontested ward: all swings resolve to None after dropping NaN/None.
        swing_concentration must raise — no meaningful concentration exists.
        Hand-check: all None dropped → abs_swings list empty → ValueError.
        """
        with pytest.raises(ValueError, match="at least one party"):
            swing_concentration({"LAB": None, "CON": None})

    def test_fi_mixed_none_and_valid_is_not_uncontested(self):
        """Multi-member ward where DCLEAPIL nulls some party vote_shares —
        this is NOT uncontested.  Valid shares are present; None values are
        dropped and remaining shares are normalised.
        LAB=45 (None for second candidate), LD=25; CON and GREEN are None.
        Hand-check: total=70; proportions 45/70, 25/70;
        sum_sq = (2025+625)/4900 = 2650/4900; FI = 4900/2650 ≈ 1.8491.
        This row should reach fragmentation_index (analysis_level='ward').
        """
        result = fragmentation_index({
            "LAB": 45.0, "CON": None, "LD": 25.0, "GREEN": None
        })
        assert abs(result - (4900.0 / 2650.0)) < 1e-9


class TestPartyExitAndEntryScoped:
    """GAP 2 — Party exits or enters scope between election cycles.

    Reflects real dataset patterns:
    - UKIP present in 2018, absent in 2022 in many boroughs
    - Reform UK absent in 2018, present in 2022
    - Scope filtering (Tier 1/2/3) may produce different party sets per cycle

    Key risk called out in review: when a party exits, SC's denominator
    (mean absolute swing) includes the exiting party's swing, which correctly
    dilutes SC rather than exaggerating it.
    """

    def test_sc_with_exited_party_denominator(self):
        """UKIP contests 2018 (10pp) but is absent in 2022.
        Swings: LAB=+5, CON=−2, LD=+2, UKIP=−10.
        abs_swings = [5, 2, 2, 10]; mean = 19/4 = 4.75; max = 10.
        SC = 10 / 4.75 = 40/19 ≈ 2.1053.

        Critical: UKIP's exit swing is included in the denominator.
        SC is NOT inflated by its absence — it is a legitimate swing of −10pp.
        """
        t1 = {"LAB": 40.0, "CON": 35.0, "LD": 15.0, "UKIP": 10.0}
        t  = {"LAB": 45.0, "CON": 33.0, "LD": 17.0}
        swings = vote_share_swing(t, t1)

        # Confirm swing for exited party
        assert _approx(swings["UKIP"], -10.0)
        # Confirm SC uses full 4-party denominator
        sc = swing_concentration(swings)
        assert _approx(sc, 40.0 / 19.0)

    def test_vol_with_exited_party_full_pipeline(self):
        """Full pipeline: party exits between cycles.
        t−1: LAB=40, CON=35, LD=15, UKIP=10  → FI = 1/0.315 ≈ 3.1746
        t:   LAB=45, CON=33, LD=17             → FI = 1/(3403/9025) ≈ 2.6521
        Σ|swings| = |5|+|−2|+|2|+|−10| = 19
        ΔFI ≈ 2.6521 − 3.1746 = −0.5225
        VOL = 0.5×19 + 0.5×(−0.5225) ≈ 9.2388

        This mirrors the Phase 9 flow where DCLEAPIL 2018 has a party that
        Commons 2022 does not cover — vote_share_swing returns its swing as
        the negative of its prior share.
        """
        t1 = {"LAB": 40.0, "CON": 35.0, "LD": 15.0, "UKIP": 10.0}
        t  = {"LAB": 45.0, "CON": 33.0, "LD": 17.0}

        fi_t1 = fragmentation_index(t1)
        fi_t  = fragmentation_index(t)
        swings = vote_share_swing(t, t1)
        vol = volatility_score(swings, fi_t=fi_t, fi_t1=fi_t1)

        assert abs(fi_t1 - (1.0 / 0.315)) < 1e-4
        assert abs(fi_t  - (9025.0 / 3403.0)) < 1e-4
        expected_vol = 0.5 * 19.0 + 0.5 * (fi_t - fi_t1)
        assert _approx(vol, expected_vol)

    def test_sc_with_new_party_entering(self):
        """Reform UK enters in 2022 (15pp); others lose share.
        t−1: LAB=50, CON=40, LD=10
        t:   LAB=42, CON=33, LD=10, REFORM=15
        Swings: LAB=−8, CON=−7, LD=0, REFORM=+15
        abs_swings=[8,7,0,15]; mean=30/4=7.5; max=15.
        SC = 15/7.5 = 2.0.
        """
        t1 = {"LAB": 50.0, "CON": 40.0, "LD": 10.0}
        t  = {"LAB": 42.0, "CON": 33.0, "LD": 10.0, "REFORM": 15.0}
        swings = vote_share_swing(t, t1)

        assert _approx(swings["REFORM"], 15.0)
        assert _approx(swings["LAB"], -8.0)
        sc = swing_concentration(swings)
        assert _approx(sc, 2.0)


class TestRawVsDerivedVoteShare:
    """GAP 3 — DCLEAPIL raw vote_share vs derived vote_share.

    In DCLEAPIL, the raw `vote_share` column is null for lower-ranked
    candidates in multi-member wards (~30% null in 2018; worst in Manchester,
    Newcastle, Leeds).  The canonical schema always derives vote_share from
    votes / total_valid_votes * 100.

    These tests document what happens if upstream code accidentally passes raw
    DCLEAPIL values (with None for nulled candidates) to the metric functions.
    The functions handle them correctly, but these tests make the dependency
    explicit so future schema drift is caught.
    """

    def test_fi_with_raw_dcleapil_none_shares(self):
        """Simulates a Manchester 2018 multi-member ward where DCLEAPIL nulls
        lower-ranked candidates.
        Raw: LAB=45.0 (top candidate only), CON=None, LD=25.0, GREEN=None.
        After None-drop + normalisation: total=70, FI = 4900/2650 ≈ 1.8491.
        Correct behaviour: Nones dropped, remaining normalised, FI computed.
        Pipeline must instead derive all shares from votes/total_valid_votes
        before calling this function, but the function handles None defensively.
        """
        result = fragmentation_index({
            "LAB": 45.0, "CON": None, "LD": 25.0, "GREEN": None
        })
        assert abs(result - (4900.0 / 2650.0)) < 1e-9

    def test_swing_with_raw_null_in_current_period(self):
        """Simulates a ward where DCLEAPIL t has a null vote_share for CON
        (lower-ranked candidate in multi-member ward) but t−1 has it populated.
        This is what happens if raw DCLEAPIL shares are passed instead of derived.
        CON: None in t → treated as 0; swing = 0 − 35 = −35.
        Warning: this overstates CON's loss. Pipeline must use derived shares.
        The function handles it without crashing, but the downstream metric
        will be wrong — this test documents the failure mode.
        """
        t  = {"LAB": 45.0, "CON": None, "LD": 25.0}
        t1 = {"LAB": 40.0, "CON": 35.0, "LD": 25.0}
        swings = vote_share_swing(t, t1)
        # CON None in t → treated as absent → swing = -35 (incorrect; use derived shares)
        assert _approx(swings["CON"], -35.0)
        assert _approx(swings["LAB"], 5.0)

    def test_fi_all_derived_is_correct(self):
        """Confirms that properly derived shares (votes / total_valid_votes * 100)
        produce correct FI.
        Simulates a 3-candidate multi-member ward:
          LAB: 1200 / 3000 = 40.0%
          CON: 1050 / 3000 = 35.0%
          LD:   750 / 3000 = 25.0%
        FI = 1 / (0.4² + 0.35² + 0.25²) = 1 / (0.16 + 0.1225 + 0.0625) = 1/0.345 ≈ 2.8986.
        """
        total_valid = 3000
        raw_votes = {"LAB": 1200, "CON": 1050, "LD": 750}
        derived = {k: (v / total_valid) * 100 for k, v in raw_votes.items()}

        result = fragmentation_index(derived)
        expected = 1.0 / (0.16 + 0.1225 + 0.0625)
        assert abs(result - expected) < 1e-9


class TestTurnoutPrecorrection:
    """GAP 5 — Pre-correction turnout values may exceed 100%.

    DCLEAPIL's turnout_percentage can exceed 100% in multi-member wards
    (490 rows in training data) because turnout_valid = total votes cast
    across all seats.  The canonical schema corrects this with:
        turnout_pct = (total_valid_votes / seats_contested) / electorate * 100

    The metric function turnout_delta receives the CORRECTED turnout_pct and
    simply subtracts.  It does not re-apply the correction.  These tests
    document:
    (a) The function passes through values > 100 without clamping — it is the
        loader's job to correct them before calling turnout_delta.
    (b) A corrected multi-member turnout produces a sensible delta.
    """

    def test_turnout_delta_does_not_clamp_above_100(self):
        """Pre-correction DCLEAPIL value of 201.1% (Stafford/Milwich 2015,
        2-seat ward, electorate 1581, turnout_valid 3179).
        turnout_delta does NOT clamp — it returns the raw difference.
        The loader must pass corrected values; this test confirms no silent
        clamping occurs that would mask loader bugs.
        Hand-check: 201.1 − 190.0 = 11.1 (not 10.0, not clamped to 100−100=0).
        """
        result = turnout_delta(201.1, 190.0)
        assert _approx(result, 11.1, tol=1e-6)

    def test_turnout_delta_with_corrected_multimember(self):
        """Corrected multi-member turnout feeds into turnout_delta correctly.
        Stafford/Milwich 2015: 2-seat ward, 1581 electorate, 3179 valid votes.
        Corrected: (3179 / 2) / 1581 * 100 ≈ 100.47%  (just over 100 — data quality
        issue in electorate field, will be flagged in Phase 8 QA).
        Prior year (1-seat, same ward): 1050/1581*100 ≈ 66.41%.
        Delta ≈ 100.47 − 66.41 = 34.06 pp.  Function returns delta unchanged.
        """
        corrected_t  = (3179 / 2) / 1581 * 100   # ≈ 100.47
        corrected_t1 = 1050 / 1581 * 100          # ≈ 66.41
        result = turnout_delta(corrected_t, corrected_t1)
        expected = corrected_t - corrected_t1
        assert _approx(result, expected)

    def test_turnout_delta_corrected_normal_case(self):
        """Standard corrected turnout, both periods valid.
        3-seat ward: t = (2400/3)/1800*100 = 44.44%; t−1 = 38.0%.
        Delta = 44.44 − 38.0 = 6.44 pp.
        """
        corrected_t  = (2400 / 3) / 1800 * 100
        corrected_t1 = 38.0
        result = turnout_delta(corrected_t, corrected_t1)
        assert _approx(result, corrected_t - corrected_t1)

# ============================================================================
# Integration: VOL computation using FI and swing outputs together
# ============================================================================

class TestVolatilityIntegration:
    """End-to-end test: compute FI from shares, then feed both FIs and swings
    into volatility_score.  Mirrors the Phase 9 pipeline flow."""

    def test_vol_from_fi_and_swing(self):
        """Full pipeline: derive FI for two periods, compute swings, compute VOL.

        Period t−1: LAB=50, CON=30, LD=20  → FI = 1/(0.25+0.09+0.04) = 1/0.38 ≈ 2.6316
        Period t:   LAB=42, CON=30, LD=28  → FI = 1/(0.1764+0.09+0.0784) = 1/0.3448 ≈ 2.8986

        swings: LAB=−8, CON=0, LD=+8
        Σ|swing| = 16
        ΔFI ≈ 2.8986 − 2.6316 ≈ 0.2670

        VOL = 0.5×16 + 0.5×0.2670 ≈ 8.1335
        """
        shares_t1 = {"LAB": 50.0, "CON": 30.0, "LD": 20.0}
        shares_t  = {"LAB": 42.0, "CON": 30.0, "LD": 28.0}

        fi_t1 = fragmentation_index(shares_t1)
        fi_t  = fragmentation_index(shares_t)
        swings = vote_share_swing(shares_t, shares_t1)
        vol = volatility_score(swings, fi_t=fi_t, fi_t1=fi_t1)

        # Hand-verified values
        assert abs(fi_t1 - (1.0 / 0.38)) < 1e-4
        assert abs(fi_t  - (1.0 / 0.3448)) < 1e-3
        assert vol is not None
        expected_vol = (0.5 * 16.0) + (0.5 * (fi_t - fi_t1))
        assert _approx(vol, expected_vol, tol=1e-9)
