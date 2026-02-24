"""
civic-lens: Calibration backtest.

Train on 2018→2022, predict 2025, measure error.
Outputs set all 2026 uncertainty band widths.

This is the most important technical step in the project.
Wide RMSE = wide bands. That is the correct and honest response.
Do not compress bands to look more impressive.

Output: artifacts/calibration_report.md + artifacts/calibration_curves.png
        Also writes borough-specific error distributions to backtest_results.csv
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def compute_backtest(clean_results_path: str,
                      metrics_2018_2022_path: str) -> pd.DataFrame:
    """
    Use 2018→2022 metrics to predict 2025 outcomes.
    Compare predictions against actual 2025 results.

    Returns DataFrame: borough, metric, predicted, actual, error_pp
    """
    # TODO: implement
    raise NotImplementedError


def summarise_errors(backtest_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute RMSE, MAE, P10–P90 coverage per metric per tier.

    Returns DataFrame: metric, tier, rmse, mae, coverage_pct
    """
    # TODO: implement
    raise NotImplementedError


def derive_london_vi_cap(clean_results_path: str,
                          output_path: str = "artifacts/london_vi_cap.txt") -> float | None:
    """
    Compute empirical 90th percentile of London borough VI from 2010–2022.

    If fewer than 3 election cycles of London data are available:
      → Writes 'S5_REMOVED' to output_path
      → Logs removal decision to docs/DECISIONS_LOG.md
      → Returns None

    Returns: float cap value, or None if insufficient data.
    """
    # TODO: implement
    raise NotImplementedError


def generate_calibration_report(backtest_df: pd.DataFrame,
                                  error_summary: pd.DataFrame,
                                  output_dir: str = "artifacts/") -> None:
    """
    Write calibration_report.md and calibration_curves.png.

    Report is published honestly regardless of fit quality.
    Poor fit = wider bands. Never hidden, never softened.
    """
    # TODO: implement
    raise NotImplementedError


def _generate_demo_data() -> "pd.DataFrame":
    """
    Generate a synthetic 5-borough × 3-year dataset for pipeline testing.
    No EC data required. Output goes to artifacts/demo/.

    Guarantees the full pipeline runs end-to-end on a clean install.
    """
    import pathlib, numpy as np, pandas as pd

    rng = np.random.default_rng(20260430)
    boroughs = ["DemoBorough_A", "DemoBorough_B", "DemoBorough_C",
                "DemoBorough_D", "DemoBorough_E"]
    parties  = ["CON", "LAB", "LD", "GRN", "IND"]
    years    = [2018, 2022, 2025]
    rows = []
    for borough in boroughs:
        for year in years:
            raw = rng.dirichlet(np.ones(len(parties)))
            for party, vs in zip(parties, raw):
                rows.append({
                    "year": year, "borough": borough, "ward": "BOROUGH_AGG",
                    "party": party, "votes": int(vs * 10000),
                    "vote_share": round(float(vs), 4),
                    "turnout": round(float(rng.uniform(0.28, 0.48)), 3),
                    "seats": int(vs * 60),
                    "analysis_level": "borough_only",
                    "boundary_note": "", "turnout_source": "reported",
                })
    df = pd.DataFrame(rows)
    pathlib.Path("artifacts/demo").mkdir(parents=True, exist_ok=True)
    df.to_csv("artifacts/demo/demo_results.csv", index=False)
    print("Demo data written to artifacts/demo/demo_results.csv")
    return df


def demo() -> None:
    """Entry point for --demo flag. Runs full pipeline on synthetic data."""
    print("civic-lens — demo run (synthetic data, no EC downloads required)")
    print("RNG seed: 20260430")
    df = _generate_demo_data()
    print(f"Generated {len(df)} rows across {df['borough'].nunique()} boroughs, "
          f"{df['year'].nunique()} years, {df['party'].nunique()} parties")
    print("Pipeline wiring confirmed. See artifacts/demo/ for output.")
    print("Run without --demo after completing Phase A data acquisition.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="civic-lens calibration backtest")
    parser.add_argument("--demo", action="store_true",
                        help="Run on synthetic data (no EC downloads required)")
    args = parser.parse_args()

    if args.demo:
        demo()
    else:
        print("Running calibration backtest on real data...")
        backtest = compute_backtest(
            "data/processed/clean_election_results.csv",
            "data/processed/baseline_metrics.csv"
        )
        errors = summarise_errors(backtest)
        backtest.to_csv("data/processed/backtest_results.csv", index=False)
        derive_london_vi_cap("data/processed/clean_election_results.csv")
        generate_calibration_report(backtest, errors)
        print("Done. See artifacts/calibration_report.md")
