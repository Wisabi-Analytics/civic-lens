from __future__ import annotations

from datetime import date
from pathlib import Path
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")

CALIBRATED_METRICS = [
    "volatility_score",
    "delta_fi",
    "turnout_delta",
    "swing_concentration",
]
RNG_SEED = 20260430
N_ITERATIONS = 2000

PROCESSED_DIR = Path("data/processed")
INTERIM_DIR = Path("data/interim")
ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)


def _metric_error_columns(metric: str) -> tuple[str, str, str, str]:
    tr = f"{metric}_training"
    bt = f"{metric}_backtest"
    err = f"{metric}_error"
    abs_err = f"{metric}_abs_error"
    return tr, bt, err, abs_err


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tm = pd.read_csv(PROCESSED_DIR / "training_metrics.csv")
    ba = pd.read_csv(PROCESSED_DIR / "backtest_actuals_2022.csv")
    dim = pd.read_csv(PROCESSED_DIR / "authority_dimension.csv")
    if not (INTERIM_DIR / "imd_2019.parquet").exists():
        raise FileNotFoundError("Missing data/interim/imd_2019.parquet")
    return tm, ba, dim, pd.read_parquet(INTERIM_DIR / "imd_2019.parquet")


def build_backtest_results(tm: pd.DataFrame, ba: pd.DataFrame, dim: pd.DataFrame) -> pd.DataFrame:
    tm_boro = tm[tm["computation_level"] == "borough"].copy()
    ba_boro = ba[ba["computation_level"] == "borough"].copy()

    base_cols = [
        "authority_code",
        "authority_name",
        "tier",
        "election_active_2026",
        "all_out_2026",
    ]
    errors = dim[base_cols].copy()

    tm_keep = tm_boro[["authority_code"] + CALIBRATED_METRICS].copy()
    ba_keep = ba_boro[["authority_code"] + CALIBRATED_METRICS].copy()
    tm_keep = tm_keep.rename(columns={m: f"{m}_training" for m in CALIBRATED_METRICS})
    ba_keep = ba_keep.rename(columns={m: f"{m}_backtest" for m in CALIBRATED_METRICS})

    errors = errors.merge(tm_keep, on="authority_code", how="left")
    errors = errors.merge(ba_keep, on="authority_code", how="left")

    for metric in CALIBRATED_METRICS:
        tr, bt, err, abs_err = _metric_error_columns(metric)
        errors[err] = errors[bt] - errors[tr]
        errors[abs_err] = errors[err].abs()

    missing_tm = errors[[f"{m}_training" for m in CALIBRATED_METRICS]].isna().any(axis=1)
    missing_ba = errors[[f"{m}_backtest" for m in CALIBRATED_METRICS]].isna().any(axis=1)
    errors["fallback_reason"] = np.select(
        [
            missing_tm & missing_ba,
            missing_tm,
            missing_ba,
            errors["all_out_2026"].fillna(False),
        ],
        [
            "missing_training_and_backtest_metrics",
            "missing_training_metrics",
            "missing_backtest_metrics",
            "all_out_2026_lgbce_review",
        ],
        default=None,
    )

    errors.to_csv(ARTIFACTS_DIR / "backtest_results.csv", index=False)
    return errors


def calibration_stats(errors: pd.DataFrame, metric: str, tier: int | None = None) -> dict:
    subset = errors if tier is None else errors[errors["tier"] == tier]
    vals = subset[f"{metric}_error"].dropna()
    if len(vals) == 0:
        return {
            "n": 0,
            "rmse": None,
            "mae": None,
            "mean_error": None,
            "std_error": None,
            "pct_positive": None,
            "p10": None,
            "p90": None,
        }
    return {
        "n": int(len(vals)),
        "rmse": float(np.sqrt(np.mean(vals**2))),
        "mae": float(np.mean(np.abs(vals))),
        "mean_error": float(np.mean(vals)),
        "std_error": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0,
        "pct_positive": float(np.mean(vals > 0) * 100),
        "p10": float(np.percentile(vals, 10)),
        "p90": float(np.percentile(vals, 90)),
    }


def build_error_distributions(errors: pd.DataFrame, tm: pd.DataFrame) -> dict:
    tier_pools: dict[int, dict[str, list[float]]] = {1: {}, 2: {}, 3: {}}
    for tier in [1, 2, 3]:
        subset = errors[errors["tier"] == tier]
        for metric in CALIBRATED_METRICS:
            vals = subset[f"{metric}_error"].dropna().tolist()
            tier_pools[tier][metric] = [float(v) for v in vals]

    borough_errors: dict[str, dict[str, float | None]] = {}
    fallback_authorities: dict[str, str] = {}
    for _, row in errors.iterrows():
        auth = row["authority_code"]
        borough_errors[auth] = {}
        has_null = False
        for metric in CALIBRATED_METRICS:
            val = row[f"{metric}_error"]
            if pd.isna(val):
                has_null = True
                borough_errors[auth][metric] = None
            else:
                borough_errors[auth][metric] = float(val)
        if has_null:
            fallback_authorities[auth] = str(row.get("fallback_reason") or "null_error_one_or_more_metrics")
        elif bool(row.get("all_out_2026", False)):
            fallback_authorities[auth] = "all_out_2026_lgbce_review"

    tm_ward = tm[tm["computation_level"] == "ward"].copy()
    if tm_ward.empty:
        leap_only_rmse_ratio = 1.0
    else:
        ward_counts = (
            tm_ward.assign(is_leap=tm_ward["training_year"].isin([2014, 2015]))
            .groupby("authority_code", dropna=False)["is_leap"]
            .agg(["mean", "count"])
            .rename(columns={"mean": "leap_exposure_share", "count": "ward_rows"})
            .reset_index()
        )
        joined = errors.merge(ward_counts, on="authority_code", how="left")
        high = joined[joined["leap_exposure_share"].fillna(0) >= 0.5]["volatility_score_error"].dropna()
        low = joined[joined["leap_exposure_share"].fillna(0) < 0.5]["volatility_score_error"].dropna()
        rmse_high = float(np.sqrt(np.mean(high**2))) if len(high) else np.nan
        rmse_low = float(np.sqrt(np.mean(low**2))) if len(low) else np.nan
        leap_only_rmse_ratio = 1.0
        if pd.notna(rmse_high) and pd.notna(rmse_low) and rmse_low > 0:
            leap_only_rmse_ratio = float(rmse_high / rmse_low)

    payload = {
        "tier_pools": tier_pools,
        "borough_errors": borough_errors,
        "fallback_authorities": fallback_authorities,
        "leap_only_rmse_ratio": float(leap_only_rmse_ratio),
        "calibrated_metrics": CALIBRATED_METRICS,
        "rng_seed": RNG_SEED,
        "n_iterations": N_ITERATIONS,
    }
    with open(ARTIFACTS_DIR / "error_distributions.pkl", "wb") as fh:
        pickle.dump(payload, fh)
    return payload


def _fmt(value: float | int | None, ndigits: int = 4) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "NA"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    return f"{float(value):.{ndigits}f}"


def write_calibration_report(errors: pd.DataFrame, payload: dict) -> None:
    stats_rows: list[dict] = []
    for metric in CALIBRATED_METRICS:
        for tier in [1, 2, 3]:
            s = calibration_stats(errors, metric, tier=tier)
            stats_rows.append({"metric": metric, "tier": tier, **s})

    outliers: list[str] = []
    vol_stats_by_tier = {
        tier: calibration_stats(errors, "volatility_score", tier=tier) for tier in [1, 2, 3]
    }
    for _, row in errors.iterrows():
        tier = int(row["tier"])
        rmse = vol_stats_by_tier[tier]["rmse"]
        val = row["volatility_score_error"]
        if rmse and pd.notna(val) and abs(float(val)) > 2 * float(rmse):
            outliers.append(
                f"- {row['authority_name']} ({row['authority_code']}): "
                f"volatility_score_error={_fmt(val)} (> 2x tier {tier} RMSE {_fmt(rmse)})"
            )

    fallback_lines = []
    for auth, reason in payload["fallback_authorities"].items():
        row = errors[errors["authority_code"] == auth]
        name = row["authority_name"].iloc[0] if not row.empty else auth
        fallback_lines.append(f"- {name} ({auth}): {reason}")

    city_row = errors[errors["authority_code"] == "E09000001"]
    city_note = "No special handling applied."
    if not city_row.empty:
        city_note = (
            f"Training VOL={_fmt(city_row['volatility_score_training'].iloc[0])}, "
            f"Backtest VOL={_fmt(city_row['volatility_score_backtest'].iloc[0])}; "
            "this creates a null error and routes City of London to tier fallback."
        )

    lines: list[str] = []
    lines.append("# Civic Lens - Calibration Report")
    lines.append("")
    lines.append(f"**Generated:** {date.today().isoformat()}  ")
    lines.append("**Calibration chain:** 2014->2018 (training) / 2018->2022 (backtest) / 2022->2026 (prediction)  ")
    lines.append(f"**Authorities calibrated:** {len(errors)} borough-level rows  ")
    lines.append("**Ward-level backtest:** Not available under current concordance artifact")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Summary Statistics by Metric and Tier")
    lines.append("")
    lines.append("| metric | tier | n | RMSE | MAE | mean_error | std_error | pct_positive | p10 | p90 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in stats_rows:
        lines.append(
            f"| {r['metric']} | {r['tier']} | {_fmt(r['n'],0)} | {_fmt(r['rmse'])} | {_fmt(r['mae'])} | "
            f"{_fmt(r['mean_error'])} | {_fmt(r['std_error'])} | {_fmt(r['pct_positive'])} | "
            f"{_fmt(r['p10'])} | {_fmt(r['p90'])} |"
        )
    lines.append("")
    lines.append("## 2. Fit Quality Assessment")
    lines.append("")
    for metric in CALIBRATED_METRICS:
        overall = calibration_stats(errors, metric, tier=None)
        lines.append(
            f"- {metric}: n={overall['n']}, RMSE={_fmt(overall['rmse'])}, MAE={_fmt(overall['mae'])}, "
            f"mean_error={_fmt(overall['mean_error'])}."
        )
    lines.append("")
    lines.append("## 3. Systematic Biases")
    lines.append("")
    vol_overall = calibration_stats(errors, "volatility_score", tier=None)
    bias_direction = "underestimation" if (vol_overall["mean_error"] or 0) > 0 else "overestimation"
    lines.append("### 3.1 Brexit-era training window")
    lines.append(
        f"VOL mean_error is {_fmt(vol_overall['mean_error'])}; this implies net {bias_direction} in 2018->2022 versus training baseline."
    )
    lines.append("")
    lines.append("### 3.2 LEAP-only era (2014/2015) training exposure")
    lines.append(
        f"Estimated RMSE ratio (high leap-only exposure / low exposure) = {_fmt(payload['leap_only_rmse_ratio'])}."
    )
    lines.append("")
    lines.append("## 4. Individual Borough Outliers")
    lines.append("")
    lines.extend(outliers if outliers else ["- None above 2x tier RMSE for volatility_score."])
    lines.append("")
    lines.append("## 5. Fallback Authorities")
    lines.append("")
    lines.extend(fallback_lines if fallback_lines else ["- None."])
    lines.append("")
    lines.append("## 6. Calibration Limitations")
    lines.append("")
    lines.append("- No ward-level backtest available under current concordance artifact.")
    lines.append("- Single observed backtest cycle per borough; uncertainty is pooled by tier.")
    lines.append(f"- City of London handling note: {city_note}")
    lines.append("- 2018->2022 includes COVID-era disruption and may not represent a stationary regime.")
    lines.append("")
    lines.append("## 7. Disclosure Statement")
    lines.append("")
    lines.append(
        '> "Uncertainty bands are calibrated from borough-specific forecast errors measured across the 2014->2022 window '
        '(training: 2014->2018; backtest: 2018->2022). The training period predates the 2025 Reform surge. '
        'Uncertainty bands may understate right-wing volatility in areas of high recent Reform support. '
        'This is a stated assumption, not an observed measurement."'
    )
    lines.append("")

    (ARTIFACTS_DIR / "calibration_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    tm, ba, dim, _imd = load_inputs()
    errors = build_backtest_results(tm, ba, dim)
    payload = build_error_distributions(errors, tm)
    write_calibration_report(errors, payload)
    print(f"Wrote {ARTIFACTS_DIR / 'backtest_results.csv'} ({len(errors)} rows)")
    print(f"Wrote {ARTIFACTS_DIR / 'error_distributions.pkl'}")
    print(f"Wrote {ARTIFACTS_DIR / 'calibration_report.md'}")


if __name__ == "__main__":
    main()
