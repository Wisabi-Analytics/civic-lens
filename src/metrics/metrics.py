"""
civic-lens: Core metric functions.

Six metrics — party-agnostic, frozen at Phase B commit.
Formula locked: see artifacts/model_lock.txt

IMPORTANT — Seat Change:
  seat_change() operates on REALISED HISTORICAL DATA ONLY.
  It is not used to project seats in scenario simulation.
  Scenario outputs are distributions of volatility metrics, not seat forecasts.

Run tests: pytest tests/test_metrics.py -v

IMPORTANT — MAYORAL DATA GUARD:
  Never call these functions on mayoral election data.
  Mayoral elections are excluded from the volatility system.
  Use src/metrics/mayoral_descriptive.py for mayoral context layer.
  See docs/MAYORAL_CONTEXT_LAYER.md
"""

import pandas as pd
import numpy as np


def vote_share_swing(df: pd.DataFrame,
                     party_col: str = "party",
                     vs_col: str = "vote_share",
                     year_col: str = "year",
                     area_col: str = "borough") -> pd.DataFrame:
    """
    Vote Share Swing: Δ% = VS_t − VS_(t-1)

    Returns DataFrame with columns: area, party, year_from, year_to, swing_pp
    Positive = gained vote share. Negative = lost.
    Swings sum to 0 within each area-year pair.
    """
    # TODO: implement
    raise NotImplementedError


def turnout_delta(df: pd.DataFrame,
                  turnout_col: str = "turnout",
                  year_col: str = "year",
                  area_col: str = "borough") -> pd.DataFrame:
    """
    Turnout Delta: ΔT = T_t − T_(t-1)

    Returns DataFrame with columns: area, year_from, year_to, turnout_delta_pp
    """
    # TODO: implement
    raise NotImplementedError


def fragmentation_index(df: pd.DataFrame,
                         vs_col: str = "vote_share",
                         area_col: str = "borough",
                         year_col: str = "year") -> pd.DataFrame:
    """
    Fragmentation Index: FI = 1 / Σ(VS²)   [Herfindahl-Hirschman Index inverse]

    Effective number of parties. Higher = more fragmented.
    FI = 1.0 for a single-party monopoly.
    FI = N for N parties with equal vote share.

    Returns DataFrame with columns: area, year, fragmentation_index
    """
    # TODO: implement
    raise NotImplementedError


def seat_change(df: pd.DataFrame,
                seats_col: str = "seats",
                party_col: str = "party",
                area_col: str = "borough",
                year_col: str = "year") -> pd.DataFrame:
    """
    Seat Change: ΔS = Seats_t − Seats_(t-1)

    HISTORICAL DATA ONLY. This function operates on realised election results.
    It is NOT used inside scenario simulation — scenarios produce metric
    distributions only, not seat projections.

    Returns DataFrame with columns: area, party, year_from, year_to, seat_change
    """
    # TODO: implement
    raise NotImplementedError


def volatility_score(swing_df: pd.DataFrame,
                      fi_df: pd.DataFrame,
                      area_col: str = "borough") -> pd.DataFrame:
    """
    Volatility Score (VOL): VOL = (0.5 × Σ|swing_i|) + (0.5 × ΔFI)

    FROZEN FORMULA — equal weight, not normalised.
    Symbol: VOL (not VS — VS is reserved for vote share).
    Turnout enters separately via turnout_delta(). Do not include ΔT here.
    Do not modify weighting. See artifacts/model_lock.txt.

    Args:
        swing_df: output of vote_share_swing() — contains swing_pp per party
        fi_df:    output of fragmentation_index() with delta (ΔFI) pre-computed

    Returns DataFrame with columns: area, year_from, year_to, volatility_score
    """
    # TODO: implement
    raise NotImplementedError


def swing_concentration(swing_df: pd.DataFrame,
                         area_col: str = "borough") -> pd.DataFrame:
    """
    Swing Concentration: SC = max(|swing|) / mean(|swing|)

    SC = 1.0: swing distributed evenly across all parties.
    SC > 1.0: swing concentrated in one or few parties.

    Returns DataFrame with columns: area, year_from, year_to, swing_concentration
    """
    # TODO: implement
    raise NotImplementedError
