from __future__ import annotations

from pathlib import Path
import hashlib
import pickle
import sys
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, "src")

from civic_lens.metrics import (
    fragmentation_index,
    swing_concentration,
    volatility_score,
    vote_share_swing,
)

RNG_SEED = 20260430
N_ITER = 2000
SIMULATED_METRICS = [
    "turnout_delta",
    "delta_fi",
    "volatility_score",
    "swing_concentration",
]
METRIC_TO_POOL = {
    "turnout_delta": "turnout_delta",
    "delta_fi": "delta_fi",
    "volatility_score": "volatility_score",
    "swing_concentration": "swing_concentration",
}
SCENARIOS_BASE = ["S0", "S1", "S2", "S3", "S4"]

PROCESSED_DIR = Path("data/processed")
ARTIFACTS_DIR = Path("artifacts")
OUTPUT_PATH = ARTIFACTS_DIR / "scenario_outputs.csv"
LOG_PATH = ARTIFACTS_DIR / "scenario_run_log.csv"

FORBIDDEN_RAW_PARTY_LABELS = {
    "Labour Party",
    "Labour And Cooperative Party",
    "Labour and Co-operative Party",
    "Reform Uk",
    "Uk Independence Party (Ukip)",
    "UK Independence Party (Ukip)",
    "Brexit Party",
}


def _is_true(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().casefold() == "true"
    return bool(value)


def _read_london_vi_cap(path: Path = ARTIFACTS_DIR / "london_vi_cap.txt") -> float | None:
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("S5_REMOVED"):
        return None
    first = text.splitlines()[0].strip()
    return float(first)


def load_inputs() -> tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict, float | None
]:
    dim = pd.read_csv(PROCESSED_DIR / "authority_dimension.csv")
    psb = pd.read_csv(PROCESSED_DIR / "party_swings_backtest.csv")
    shocks = pd.read_csv(PROCESSED_DIR / "shock_metrics.csv")
    backtest = pd.read_csv(ARTIFACTS_DIR / "backtest_results.csv")
    with open(ARTIFACTS_DIR / "error_distributions.pkl", "rb") as fh:
        error_distributions = pickle.load(fh)
    london_vi_cap = _read_london_vi_cap()
    return dim, psb, shocks, backtest, error_distributions, london_vi_cap


def active_authorities(dim: pd.DataFrame) -> list[str]:
    auths = sorted(
        dim.loc[
            (dim["election_active_2026"].map(_is_true))
            & (dim["authority_code"] != "E09000001"),
            "authority_code",
        ].dropna()
    )
    if len(auths) != 64:
        raise ValueError(f"Expected 64 active authorities, found {len(auths)}")
    return auths


def scenario_ids(london_vi_cap: float | None) -> list[str]:
    return SCENARIOS_BASE + (["S5"] if london_vi_cap is not None else [])


def party_column(psb: pd.DataFrame) -> str:
    if "metric_party_family" in psb.columns:
        return "metric_party_family"
    if "party_family" in psb.columns:
        return "party_family"
    col = "party_standardised"
    observed = set(psb[col].dropna().unique())
    bad = FORBIDDEN_RAW_PARTY_LABELS & observed
    if bad:
        raise ValueError(
            "party_swings_backtest.csv is not family-normalised. "
            f"Raw labels still present: {sorted(bad)}"
        )
    return col


def base_shares_by_authority(psb: pd.DataFrame) -> dict[str, dict[str, float]]:
    col = party_column(psb)
    rows = psb[psb["computation_level"] == "borough"].copy()
    result: dict[str, dict[str, float]] = {}
    for auth, grp in rows.groupby("authority_code"):
        shares: dict[str, float] = {}
        for _, row in grp.iterrows():
            party = str(row[col])
            share = row["vote_share_2022"]
            if pd.notna(share) and float(share) > 0:
                shares[party] = shares.get(party, 0.0) + float(share)
        total = sum(shares.values())
        result[auth] = {p: v / total * 100.0 for p, v in shares.items()} if total > 0 else {}
    return result


def append_log(
    logs: list[dict[str, Any]],
    scenario_id: str,
    authority_code: str,
    metric: str,
    event_type: str,
    detail: str,
) -> None:
    logs.append(
        {
            "scenario_id": scenario_id,
            "authority_code": authority_code,
            "metric": metric,
            "event_type": event_type,
            "detail": detail,
        }
    )


def clamp_and_renormalise(
    shares: dict[str, float],
    logs: list[dict[str, Any]],
    auth_code: str,
    scenario_id: str,
) -> dict[str, float]:
    shares = dict(shares)
    while True:
        negatives = {p: v for p, v in shares.items() if v < 0}
        if not negatives:
            break
        for party in negatives:
            shares[party] = 0.0
        append_log(
            logs,
            scenario_id,
            auth_code,
            "shares",
            "share_clamped",
            f"Clamped {sorted(negatives)} to zero",
        )
        if sum(v for v in shares.values() if v > 0) <= 0:
            return {}

    total = sum(v for v in shares.values() if v > 0)
    if total <= 0:
        return {}
    return {p: max(0.0, v / total * 100.0) for p, v in shares.items()}


def apply_vote_share_shock(
    base_shares: dict[str, float],
    shock_row: pd.Series,
    scenario_id: str,
    auth_code: str,
    logs: list[dict[str, Any]],
) -> dict[str, float]:
    if scenario_id in {"S0", "S4", "S5"}:
        return dict(base_shares)

    challenger = shock_row.get("challenger_party")
    if pd.isna(challenger) or not challenger:
        append_log(
            logs,
            scenario_id,
            auth_code,
            "shares",
            "no_challenger_identified",
            "Missing challenger_party in shock_metrics.csv",
        )
        return dict(base_shares)

    challenger = str(challenger)
    challenger_swing = float(shock_row["challenger_swing_pp"])
    established_swing = float(shock_row["established_swing_pp"])
    shares = dict(base_shares)
    if challenger not in shares:
        shares[challenger] = 0.0

    established = {p: v for p, v in shares.items() if p != challenger and v > 0}
    established_total = sum(established.values())
    shares[challenger] = shares.get(challenger, 0.0) + challenger_swing
    if established_total > 0:
        for party, value in established.items():
            shares[party] = shares[party] + established_swing * (value / established_total)
    elif established_swing != 0:
        append_log(
            logs,
            scenario_id,
            auth_code,
            "shares",
            "no_base_shares",
            "No established-party vote share available for proportional shock",
        )
    return clamp_and_renormalise(shares, logs, auth_code, scenario_id)


def point_estimates(
    base_shares: dict[str, float],
    shocked_shares: dict[str, float],
    turnout_point: float,
) -> dict[str, float]:
    if not base_shares or not shocked_shares:
        return {metric: np.nan for metric in SIMULATED_METRICS}
    base_fi = fragmentation_index(base_shares)
    shocked_fi = fragmentation_index(shocked_shares)
    swings = vote_share_swing(shocked_shares, base_shares)
    delta_fi = shocked_fi - base_fi
    vol = volatility_score(swings, shocked_fi, base_fi)
    sc = swing_concentration(swings)
    return {
        "turnout_delta": float(turnout_point),
        "delta_fi": float(delta_fi),
        "volatility_score": float(vol),
        "swing_concentration": float(sc),
    }


def tier_pool(error_distributions: dict, tier: int, metric: str) -> np.ndarray:
    try:
        pool = error_distributions["tier_pools"][int(tier)][METRIC_TO_POOL[metric]]
    except KeyError as exc:
        raise KeyError(f"Missing tier pool for tier={tier}, metric={metric}") from exc
    arr = np.array(pool, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) < 2:
        raise ValueError(f"Tier pool too small for tier={tier}, metric={metric}: n={len(arr)}")
    return arr


def rmse(pool: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(pool))))


def widen_to_floor(
    p10: float, p50: float, p90: float, floor: float
) -> tuple[float, float, float, bool]:
    width = p90 - p10
    if not np.isfinite(floor) or floor <= 0 or width >= floor:
        return p10, p50, p90, False
    half = floor / 2.0
    return p50 - half, p50, p50 + half, True


def bootstrap_interval(
    point: float,
    tier: int,
    metric: str,
    scenario_id: str,
    auth_code: str,
    rng: np.random.Generator,
    error_distributions: dict,
    logs: list[dict[str, Any]],
    london_vi_cap: float | None = None,
) -> tuple[float, float, float]:
    pool = tier_pool(error_distributions, tier, metric)
    metric_rmse = rmse(pool)
    centered_pool = pool - float(np.mean(pool))
    samples = point + rng.choice(centered_pool, size=N_ITER, replace=True)
    p10, p50, p90 = [float(v) for v in np.percentile(samples, [10, 50, 90])]

    p10, p50, p90, widened = widen_to_floor(p10, p50, p90, metric_rmse)
    if widened:
        append_log(
            logs,
            scenario_id,
            auth_code,
            metric,
            "interval_widened",
            f"Expanded P90-P10 to RMSE floor {metric_rmse:.6f}",
        )

    if scenario_id == "S5" and metric == "volatility_score" and london_vi_cap is not None:
        old_width = p90 - p10
        uncapped = (p10, p50, p90)
        p90 = min(p90, london_vi_cap)
        if p50 > london_vi_cap:
            p50 = london_vi_cap
        if (p10, p50, p90) != uncapped:
            append_log(
                logs,
                scenario_id,
                auth_code,
                metric,
                "s5_vi_capped",
                f"Applied London VOL cap {london_vi_cap:.6f}",
            )
        if p90 - p10 < metric_rmse and old_width >= metric_rmse:
            append_log(
                logs,
                scenario_id,
                auth_code,
                metric,
                "s5_floor_overridden_by_cap",
                f"London VOL cap narrowed interval below RMSE floor {metric_rmse:.6f}",
            )

    if metric == "swing_concentration":
        before = (p10, p50, p90)
        p10 = max(1.0, p10)
        p50 = max(1.0, p50)
        p90 = max(1.0, p90)
        if before != (p10, p50, p90):
            append_log(
                logs,
                scenario_id,
                auth_code,
                metric,
                "metric_lower_bound_clamped",
                "Applied swing_concentration lower bound 1.0",
            )
        if p90 - p10 < metric_rmse:
            append_log(
                logs,
                scenario_id,
                auth_code,
                metric,
                "metric_lower_bound_overrode_floor",
                f"SC lower bound narrowed interval below RMSE floor {metric_rmse:.6f}",
            )

    if not (p10 <= p50 <= p90):
        append_log(
            logs,
            scenario_id,
            auth_code,
            metric,
            "interval_ordering_violated",
            f"P10={p10:.6f}, P50={p50:.6f}, P90={p90:.6f}",
        )
        raise ValueError(f"Interval ordering violated for {scenario_id}/{auth_code}/{metric}")

    return p10, p50, p90


def _copy_s0_row(
    s0_lookup: dict[tuple[str, str], dict[str, Any]],
    scenario_id: str,
    authority_code: str,
    metric: str,
    notes: str,
) -> dict[str, Any]:
    source = s0_lookup[(authority_code, metric)]
    copied = dict(source)
    copied["scenario_id"] = scenario_id
    copied["notes"] = notes
    return copied


def build_scenario_rows(
    dim: pd.DataFrame,
    psb: pd.DataFrame,
    shocks: pd.DataFrame,
    error_distributions: dict,
    london_vi_cap: float | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(RNG_SEED)
    logs: list[dict[str, Any]] = []
    shares_by_auth = base_shares_by_authority(psb)
    active = active_authorities(dim)
    scenarios = scenario_ids(london_vi_cap)
    dim_idx = dim.set_index("authority_code")
    shock_idx = shocks.set_index(["authority_code", "scenario_id"])
    rows: list[dict[str, Any]] = []
    s0_lookup: dict[tuple[str, str], dict[str, Any]] = {}

    for auth in active:
        auth_meta = dim_idx.loc[auth]
        tier = int(auth_meta["tier"])
        base = shares_by_auth.get(auth, {})
        if not base:
            append_log(logs, "ALL", auth, "shares", "no_base_shares", "No base 2022 shares")

        for scenario_id in scenarios:
            shock_row = shock_idx.loc[(auth, scenario_id)]
            turnout_point = 0.0
            if scenario_id == "S4" and pd.notna(shock_row.get("turnout_shock_pp")):
                turnout_point = float(shock_row["turnout_shock_pp"])
            shocked = apply_vote_share_shock(base, shock_row, scenario_id, auth, logs)
            estimates = point_estimates(base, shocked, turnout_point)

            for metric in SIMULATED_METRICS:
                if scenario_id == "S5":
                    if tier != 2:
                        rows.append(
                            _copy_s0_row(s0_lookup, scenario_id, auth, metric, "copied_from_s0")
                        )
                        continue
                    if metric != "volatility_score":
                        rows.append(
                            _copy_s0_row(s0_lookup, scenario_id, auth, metric, "copied_from_s0")
                        )
                        continue

                if scenario_id == "S4" and metric in {
                    "delta_fi",
                    "volatility_score",
                    "swing_concentration",
                }:
                    rows.append(
                        _copy_s0_row(s0_lookup, scenario_id, auth, metric, "copied_from_s0")
                    )
                    continue

                point = estimates[metric]
                if pd.isna(point):
                    append_log(
                        logs,
                        scenario_id,
                        auth,
                        metric,
                        "validation_failure",
                        "Point estimate is null",
                    )
                    p10 = p50 = p90 = np.nan
                else:
                    cap = london_vi_cap if scenario_id == "S5" and tier == 2 else None
                    p10, p50, p90 = bootstrap_interval(
                        float(point),
                        tier,
                        metric,
                        scenario_id,
                        auth,
                        rng,
                        error_distributions,
                        logs,
                        london_vi_cap=cap,
                    )

                row = {
                    "scenario_id": scenario_id,
                    "authority_code": auth,
                    "authority_name": auth_meta["authority_name"],
                    "tier": tier,
                    "election_active_2026": bool(auth_meta["election_active_2026"]),
                    "metric": metric,
                    "P10": p10,
                    "P50": p50,
                    "P90": p90,
                    "notes": None,
                    "point_estimate": point,
                }
                rows.append(row)
                if scenario_id == "S0":
                    s0_lookup[(auth, metric)] = dict(row)

    out = pd.DataFrame(rows)
    log_df = pd.DataFrame(
        logs,
        columns=["scenario_id", "authority_code", "metric", "event_type", "detail"],
    )
    return out, log_df


def _interval_width_floor_violations(
    outputs: pd.DataFrame,
    error_distributions: dict,
    logs: pd.DataFrame,
) -> list[str]:
    allowed = {
        (r["scenario_id"], r["authority_code"], r["metric"], r["event_type"])
        for _, r in logs.iterrows()
        if r["event_type"] in {"s5_floor_overridden_by_cap", "metric_lower_bound_overrode_floor"}
    }
    failures: list[str] = []
    for _, row in outputs.iterrows():
        if pd.isna(row["P10"]) or pd.isna(row["P90"]):
            continue
        pool = tier_pool(error_distributions, int(row["tier"]), str(row["metric"]))
        floor = rmse(pool)
        width = float(row["P90"]) - float(row["P10"])
        key_cap = (
            row["scenario_id"],
            row["authority_code"],
            row["metric"],
            "s5_floor_overridden_by_cap",
        )
        key_sc = (
            row["scenario_id"],
            row["authority_code"],
            row["metric"],
            "metric_lower_bound_overrode_floor",
        )
        if width + 1e-9 < floor and key_cap not in allowed and key_sc not in allowed:
            failures.append(
                f"{row['scenario_id']}/{row['authority_code']}/{row['metric']} "
                f"width {width:.6f} < RMSE {floor:.6f}"
            )
    return failures


def validate_outputs(
    outputs: pd.DataFrame,
    logs: pd.DataFrame,
    dim: pd.DataFrame,
    shocks: pd.DataFrame,
    error_distributions: dict,
    london_vi_cap: float | None,
) -> None:
    failures: list[str] = []
    scenarios = scenario_ids(london_vi_cap)
    expected_rows = len(scenarios) * 64 * len(SIMULATED_METRICS)
    if len(outputs) != expected_rows:
        failures.append(f"Expected {expected_rows} rows, found {len(outputs)}")
    if london_vi_cap is not None and len(outputs) != 1536:
        failures.append("S5 active output must contain 1536 rows")
    if london_vi_cap is None and len(outputs) != 1280:
        failures.append("S5 removed output must contain 1280 rows")

    active = set(active_authorities(dim))
    if set(outputs["authority_code"]) != active:
        failures.append("Output authority set does not match 64 active authorities")
    if set(outputs["scenario_id"]) != set(scenarios):
        failures.append("Output scenario set is incomplete")
    if set(outputs["metric"]) != set(SIMULATED_METRICS):
        failures.append("Output metric set is incomplete")
    if "vote_share_swing" in set(outputs["metric"]):
        failures.append("vote_share_swing rows are not allowed")
    if "seat_change" in set(outputs["metric"]):
        failures.append("seat_change rows are not allowed")

    bad_order = outputs[
        outputs[["P10", "P50", "P90"]].notna().all(axis=1)
        & ~((outputs["P10"] <= outputs["P50"]) & (outputs["P50"] <= outputs["P90"]))
    ]
    if not bad_order.empty:
        failures.append(f"{len(bad_order)} rows violate P10 <= P50 <= P90")

    s3_vol = outputs[
        (outputs["scenario_id"] == "S3") & (outputs["metric"] == "volatility_score")
    ]["point_estimate"].median()
    if pd.isna(s3_vol) or float(s3_vol) < 2.0:
        failures.append(f"S3 median VOL point_estimate {s3_vol} < 2.0")

    s0 = outputs[outputs["scenario_id"] == "S0"].set_index(["authority_code", "metric"])
    s4 = outputs[outputs["scenario_id"] == "S4"].set_index(["authority_code", "metric"])
    for metric in ["delta_fi", "volatility_score", "swing_concentration"]:
        cols = ["P10", "P50", "P90", "point_estimate"]
        if not s4.xs(metric, level="metric")[cols].equals(s0.xs(metric, level="metric")[cols]):
            failures.append(f"S4 {metric} rows must equal S0 exactly")

    if london_vi_cap is not None:
        s5 = outputs[outputs["scenario_id"] == "S5"]
        non_london = s5[s5["tier"] != 2]
        if not non_london.empty and not (non_london["notes"] == "copied_from_s0").all():
            failures.append("S5 non-London rows must have notes=copied_from_s0")
        for _, row in non_london.iterrows():
            src = s0.loc[(row["authority_code"], row["metric"])]
            for col in ["P10", "P50", "P90", "point_estimate"]:
                if not np.isclose(float(row[col]), float(src[col]), rtol=0, atol=1e-9):
                    failures.append(
                        f"S5 non-London copy mismatch for {row['authority_code']} {row['metric']}"
                    )
                    break
        london_vol = s5[(s5["tier"] == 2) & (s5["metric"] == "volatility_score")]
        if not london_vol.empty and (london_vol["P90"] > london_vi_cap + 1e-9).any():
            failures.append("S5 London VOL P90 exceeds cap")

    failures.extend(_interval_width_floor_violations(outputs, error_distributions, logs))

    sc = outputs[outputs["metric"] == "swing_concentration"]
    if (sc["P10"] < 1.0).any():
        failures.append("swing_concentration P10 must be >= 1.0")
    turnout = outputs[outputs["metric"] == "turnout_delta"]
    if (turnout["P50"].abs() > 30).any():
        failures.append("abs(turnout_delta P50) must be <= 30")

    s1 = shocks[(shocks["scenario_id"] == "S1") & (shocks["election_active_2026"].map(_is_true))]
    observed = set(s1["challenger_party"].dropna())
    raw_bad = FORBIDDEN_RAW_PARTY_LABELS & observed
    if raw_bad:
        failures.append(f"Raw challenger labels remain: {sorted(raw_bad)}")
    lab_share = float((s1["challenger_party"] == "LAB").mean())
    if lab_share >= 0.75:
        failures.append(f"S1 LAB challenger share is near-universal: {lab_share:.1%}")

    null_points = outputs[outputs["point_estimate"].isna()]
    if not null_points.empty:
        failures.append(f"{len(null_points)} rows have null point_estimate")

    if failures:
        raise ValueError("Scenario validation failed:\n- " + "\n- ".join(failures))


def dataframe_hash(df: pd.DataFrame) -> str:
    payload = df.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run_simulation(write: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    dim, psb, shocks, _backtest, error_distributions, london_vi_cap = load_inputs()
    outputs, logs = build_scenario_rows(dim, psb, shocks, error_distributions, london_vi_cap)
    validate_outputs(outputs, logs, dim, shocks, error_distributions, london_vi_cap)
    outputs = outputs.sort_values(["authority_code", "scenario_id", "metric"]).reset_index(
        drop=True
    )
    logs = logs.sort_values(["authority_code", "scenario_id", "metric", "event_type"]).reset_index(
        drop=True
    )
    if write:
        ARTIFACTS_DIR.mkdir(exist_ok=True)
        outputs.to_csv(OUTPUT_PATH, index=False)
        logs.to_csv(LOG_PATH, index=False)
    return outputs, logs


def main() -> None:
    outputs, logs = run_simulation(write=True)
    print(f"Wrote {OUTPUT_PATH} ({len(outputs)} rows, sha256={dataframe_hash(outputs)})")
    print(f"Wrote {LOG_PATH} ({len(logs)} rows)")


if __name__ == "__main__":
    main()
