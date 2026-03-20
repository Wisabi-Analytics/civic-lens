"""
civic_lens.metrics
==================
Six party-agnostic electoral volatility metrics, frozen at Phase 2.

Definitions are locked in:
    docs/DATA_DICTIONARY.md  — Metric Definitions (Frozen)
    docs/SCENARIO_DEFINITIONS.md

Formula reference
-----------------
Vote Share Swing      Δ%  = VS_t − VS_(t−1)          per party
Turnout Delta         ΔT  = T_t − T_(t−1)             percentage points
Fragmentation Index   FI  = 1 / Σ(VS_i²)              VS as proportions (0–1)
Seat Change           ΔS  = Seats_t − Seats_(t−1)      integer, historical only
Volatility Score      VOL = 0.5 × Σ|swing_i| + 0.5 × ΔFI
Swing Concentration   SC  = max(|swing_i|) / mean(|swing_i|)

Notation
--------
VS  = vote share (proportion 0–1 inside formulae)
VOL = volatility score  (abbreviations do not collide)

All vote share inputs to public functions are expected as **percentages (0–100)**,
matching the `vote_share` field in clean_election_results.csv.  Internally, FI
converts to proportions before squaring.

Input conventions
-----------------
vote_shares    : dict[str, float]  — {party_standardised: vote_share_pct}
                 Parties absent from one period are treated as 0 vote share.
                 NaN values are dropped before computation.
                 Shares need not sum exactly to 100 — the FI function normalises
                 to handle rounding, but callers should supply clean data.
turnout        : float | None      — percentage (0–100)
seats          : int | None
"""

from __future__ import annotations

from typing import Optional
import math


# ---------------------------------------------------------------------------
# 1. Vote Share Swing
# ---------------------------------------------------------------------------

def vote_share_swing(
    shares_t: dict[str, float],
    shares_t1: dict[str, float],
) -> dict[str, float]:
    """Compute per-party vote share swing between two periods.

    Formula
    -------
    Δ%_i = VS_t_i − VS_(t−1)_i

    Parameters
    ----------
    shares_t  : {party: vote_share_pct} for the current period.
    shares_t1 : {party: vote_share_pct} for the prior period.

    Returns
    -------
    dict[str, float]
        Swing in percentage points per party.  Positive = gain, negative = loss.
        Parties present in one period but absent in the other are treated as
        having 0 vote share in the missing period.

    Edge cases
    ----------
    - Empty inputs on both sides → empty dict returned.
    - Party present in t only  → swing = +VS_t   (new entrant).
    - Party present in t−1 only → swing = −VS_(t−1) (party exited).
    - NaN values are dropped before computation; a party whose share is NaN in
      *both* periods is excluded from the result.
    - No clamping is applied: swings outside [−100, +100] are returned as-is
      and should be caught by Phase 8 QA assertions.
    """
    # Gather clean values, treating NaN / missing as 0
    def _clean(d: dict[str, float]) -> dict[str, float]:
        return {
            k: float(v)
            for k, v in d.items()
            if v is not None and not (isinstance(v, float) and math.isnan(v))
        }

    clean_t  = _clean(shares_t)
    clean_t1 = _clean(shares_t1)

    all_parties = set(clean_t) | set(clean_t1)
    if not all_parties:
        return {}

    return {
        party: clean_t.get(party, 0.0) - clean_t1.get(party, 0.0)
        for party in sorted(all_parties)
    }


# ---------------------------------------------------------------------------
# 2. Turnout Delta
# ---------------------------------------------------------------------------

def turnout_delta(
    turnout_t: Optional[float],
    turnout_t1: Optional[float],
) -> Optional[float]:
    """Compute change in per-elector turnout between two periods.

    Formula
    -------
    ΔT = T_t − T_(t−1)

    Parameters
    ----------
    turnout_t  : Turnout percentage (0–100) for the current period.
    turnout_t1 : Turnout percentage (0–100) for the prior period.
                 Both must use the **corrected** turnout_pct field from
                 clean_election_results.csv — i.e. already divided by
                 seats_contested for multi-member wards.

    Returns
    -------
    float | None
        Delta in percentage points. None if either input is None.

    Edge cases
    ----------
    - Either input None → return None (do not impute).
    - Negative delta is valid (turnout fell).
    - No clamping: outputs outside [−100, +100] flagged in Phase 8 QA.
    """
    if turnout_t is None or turnout_t1 is None:
        return None
    return float(turnout_t) - float(turnout_t1)


# ---------------------------------------------------------------------------
# 3. Fragmentation Index
# ---------------------------------------------------------------------------

def fragmentation_index(shares: dict[str, float]) -> float:
    """Compute the Fragmentation Index (effective number of parties, HHI variant).

    Formula
    -------
    FI = 1 / Σ(VS_i²)    where VS_i are proportions (0–1), not percentages.

    Parameters
    ----------
    shares : {party: vote_share_pct}
        Vote share as **percentages (0–100)**.  The function converts to
        proportions internally.
        Must be derived from `votes / total_valid_votes * 100` in the
        canonical schema — never from the raw DCLEAPIL `vote_share` column.
        ILP and IND parties are treated as distinct entries (not pooled).

    Returns
    -------
    float
        FI ≥ 1.0.  Returns 1.0 for a single-party result (complete dominance).

    Raises
    ------
    ValueError
        If `shares` is empty or all values reduce to zero after cleaning.

    Edge cases
    ----------
    - NaN / None values are dropped before computation.
    - Zero-share parties are dropped (they contribute nothing to the sum).
    - Shares are normalised before squaring to absorb rounding error
      (e.g. shares summing to 99.8 instead of 100 due to float precision).
    - Single party with 100 share → FI = 1.0.
    - N equal parties → FI = N.
    """
    # Drop NaN and None; keep only positive shares
    clean = {
        k: float(v)
        for k, v in shares.items()
        if v is not None
        and not (isinstance(v, float) and math.isnan(v))
        and float(v) > 0
    }

    if not clean:
        raise ValueError(
            "fragmentation_index requires at least one party with a positive "
            "vote share. Received: {!r}".format(shares)
        )

    # Convert percentages → proportions, then normalise
    total = sum(clean.values())
    proportions = [v / total for v in clean.values()]  # normalised proportions

    sum_sq = sum(p ** 2 for p in proportions)
    return 1.0 / sum_sq


# ---------------------------------------------------------------------------
# 4. Seat Change
# ---------------------------------------------------------------------------

def seat_change(
    seats_t: Optional[int],
    seats_t1: Optional[int],
) -> Optional[int]:
    """Compute change in seats won between two periods.

    Formula
    -------
    ΔS = Seats_t − Seats_(t−1)

    Parameters
    ----------
    seats_t  : Seats won in current period.
    seats_t1 : Seats won in prior period.

    Returns
    -------
    int | None
        Signed integer. None if either input is None.
        HISTORICAL DATA ONLY — this function is never called from the scenario
        simulation engine.  Scenario outputs do not include seat projections.

    Edge cases
    ----------
    - Either input None → return None.
    - Negative result is valid (lost seats).
    - Zero change is valid.
    """
    if seats_t is None or seats_t1 is None:
        return None
    return int(seats_t) - int(seats_t1)


# ---------------------------------------------------------------------------
# 5. Volatility Score
# ---------------------------------------------------------------------------

def volatility_score(
    swings: dict[str, float],
    fi_t: Optional[float],
    fi_t1: Optional[float],
) -> Optional[float]:
    """Compute the composite Volatility Score (VOL).

    Formula
    -------
    VOL = (0.5 × Σ|swing_i|) + (0.5 × ΔFI)

    where ΔFI = FI_t − FI_(t−1)

    Equal-weight Pedersen-index variant.  Swing component uses absolute values
    summed over all parties; FI component is the first-difference of FI.

    Parameters
    ----------
    swings : {party: swing_pct}
        Per-party vote share swings in percentage points, as returned by
        `vote_share_swing()`.  Absolute values are taken internally.
    fi_t   : Fragmentation Index for the current period.
    fi_t1  : Fragmentation Index for the prior period.

    Returns
    -------
    float | None
        VOL.  None if either FI value is None.
        VOL can be negative when ΔFI is sufficiently negative
        (fragmentation fell sharply while swings were small).
        This is mathematically correct per the frozen formula — do not clamp.

    Edge cases
    ----------
    - Empty swings dict → swing component = 0; VOL driven by ΔFI only.
    - Either FI is None → return None (cannot compute ΔFI).
    - NaN swings are dropped before summing.
    """
    if fi_t is None or fi_t1 is None:
        return None

    swing_component = sum(
        abs(v)
        for v in swings.values()
        if v is not None and not (isinstance(v, float) and math.isnan(v))
    )

    delta_fi = float(fi_t) - float(fi_t1)

    return (0.5 * swing_component) + (0.5 * delta_fi)


# ---------------------------------------------------------------------------
# 6. Swing Concentration
# ---------------------------------------------------------------------------

def swing_concentration(swings: dict[str, float]) -> float:
    """Compute the Swing Concentration ratio (SC).

    Formula
    -------
    SC = max(|swing_i|) / mean(|swing_i|)

    Parameters
    ----------
    swings : {party: swing_pct}
        Per-party vote share swings in percentage points, as returned by
        `vote_share_swing()`.

    Returns
    -------
    float
        SC ≥ 1.0.  SC = 1.0 indicates perfectly even concentration across
        all parties.  High SC = one party driving all volatility.

    Raises
    ------
    ValueError
        If `swings` is empty (no parties to measure concentration over).

    Edge cases
    ----------
    - **All swings = 0 → return 1.0.**  (Frozen rule, DATA_DICTIONARY.md.)
      Undefined mathematically (0/0) but defined by project convention.
    - Single party → max == mean → SC = 1.0.
    - NaN swings are dropped before computation.
    - The ratio is always ≥ 1 by definition (max ≥ mean for non-negative values).
    """
    # Drop NaN
    abs_swings = [
        abs(float(v))
        for v in swings.values()
        if v is not None and not (isinstance(v, float) and math.isnan(v))
    ]

    if not abs_swings:
        raise ValueError(
            "swing_concentration requires at least one party swing. "
            "Received: {!r}".format(swings)
        )

    # Frozen edge case: all swings = 0 → return 1.0
    if all(s == 0.0 for s in abs_swings):
        return 1.0

    return max(abs_swings) / (sum(abs_swings) / len(abs_swings))