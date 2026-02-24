"""
civic-lens: Mayoral Context Layer — descriptive analysis only.

ALL combined authority mayoral elections in 2026 are newly-established roles.
No prior election exists. Therefore:

  - NO volatility metrics computed here
  - NO swing, turnout delta, or fragmentation delta
  - NO scenario simulation
  - NO backtest calibration

This module produces single-cycle DESCRIPTIVE outputs only:
  - Vote share per candidate
  - Turnout per authority
  - Single-cycle Fragmentation Index (FI, not ΔFI)
  - Cross-authority comparison table

Output: data/processed/mayoral_context.csv
        reports/mayoral_context.md

See: docs/MAYORAL_CONTEXT_LAYER.md
"""

import pandas as pd
import numpy as np

MAYORAL_EXCLUSION_MSG = (
    "Mayoral elections excluded from volatility system — "
    "see docs/MAYORAL_CONTEXT_LAYER.md"
)


def guard_against_volatility_pipeline(func_name: str) -> None:
    """
    Raise ValueError if any volatility function is accidentally called
    with mayoral data.
    """
    raise ValueError(
        f"Attempted to call '{func_name}' on mayoral data. "
        f"{MAYORAL_EXCLUSION_MSG}"
    )


def load_mayoral_results(raw_path: str) -> pd.DataFrame:
    """
    Load and validate raw mayoral results from EC download.

    Required columns: combined_authority, candidate, party, votes, turnout
    Returns cleaned DataFrame ready for descriptive analysis.
    """
    # TODO: implement
    raise NotImplementedError


def mayoral_vote_shares(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute vote share per candidate per combined authority.

    Single cycle only — no delta, no swing.
    Returns DataFrame: combined_authority, candidate, party, votes, vote_share
    """
    # TODO: implement
    raise NotImplementedError


def mayoral_fragmentation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute single-cycle Fragmentation Index per combined authority.

    FI = 1 / Σ(VS²)

    NOTE: This is a DESCRIPTIVE single-cycle FI only.
    ΔFI (change in FI) is not computed — no prior baseline exists.
    This value is NOT used in VOL (Volatility Score) calculation.

    Returns DataFrame: combined_authority, fragmentation_index, n_candidates
    """
    # TODO: implement
    raise NotImplementedError


def mayoral_cross_authority_table(vote_shares: pd.DataFrame,
                                    fi_df: pd.DataFrame,
                                    df: pd.DataFrame) -> pd.DataFrame:
    """
    Produce cross-authority summary table for publication.

    Columns: combined_authority, winner, winner_party, winner_vs,
             turnout, fragmentation_index, n_candidates

    All values descriptive only — no longitudinal comparisons.
    """
    # TODO: implement
    raise NotImplementedError


def generate_mayoral_report(raw_path: str,
                             processed_path: str = "data/processed/mayoral_context.csv",
                             report_path: str = "reports/mayoral_context.md") -> None:
    """
    Run full mayoral descriptive pipeline. Write CSV and markdown report.

    Includes the exclusion statement verbatim at the top of every output.
    """
    # TODO: implement
    raise NotImplementedError


if __name__ == "__main__":
    generate_mayoral_report("data/raw/ec/mayors_2026.csv")
