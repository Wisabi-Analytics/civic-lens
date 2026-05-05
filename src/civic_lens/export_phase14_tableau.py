from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import re
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
TABLEAU = REPORTS / "tableau_data"

SCENARIO_OUTPUTS = ARTIFACTS / "scenario_outputs.csv"
SCENARIO_LOG = ARTIFACTS / "scenario_run_log.csv"
MODEL_LOCK = ARTIFACTS / "model_lock.txt"
LONDON_VI_CAP = ARTIFACTS / "london_vi_cap.txt"
SCENARIO_DEFINITIONS = ROOT / "docs" / "SCENARIO_DEFINITIONS.md"
AUTHORITY_DIMENSION = PROCESSED / "authority_dimension.csv"
AUTHORITY_CENTROIDS = TABLEAU / "authority_centroids.csv"
AUDIT_PATH = REPORTS / "phase14_scenario_audit.md"

LOCKED_SCENARIO_OUTPUTS_SHA256 = (
    "522fd6bdc5f38ff70392c5975e209af46d258018b25e4b98d71b958e9586fe0d"
)
LOCKED_SCENARIO_DEFINITIONS_SHA = "b862faf8eab6b7f235c707241db7078de846f8ca"
EXPECTED_ROWS = 1536
EXPECTED_AUTHORITIES = 64

SCENARIO_LABELS = {
    "S0": "Baseline: no new swing",
    "S1": "Volatility continuation",
    "S2": "Partial establishment recovery",
    "S3": "Challenger surge",
    "S4": "Deprivation turnout shift",
    "S5": "London stability reversion",
}
METRIC_LABELS = {
    "turnout_delta": "Turnout change (pp)",
    "delta_fi": "Change in effective parties",
    "volatility_score": "Volatility score",
    "swing_concentration": "Swing concentration",
}
TIER_LABELS = {
    1: "Metropolitan Borough",
    2: "London Borough",
    3: "West Yorkshire",
}
SCENARIO_ORDER = {scenario_id: i for i, scenario_id in enumerate(SCENARIO_LABELS, start=1)}
METRIC_ORDER = {metric: i for i, metric in enumerate(METRIC_LABELS, start=1)}
BLOCKING_EVENTS = {
    "validation_failure",
    "interval_ordering_violated",
    "tier_pool_too_small",
    "no_base_shares",
}


@dataclass(frozen=True)
class LockMetadata:
    status: str
    model_version_sha: str
    scenario_definitions_sha: str
    freeze_timestamp_utc: str
    rng_seed: str


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_hash_object(path: Path) -> str:
    result = subprocess.run(
        ["git", "hash-object", str(path.relative_to(ROOT))],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def parse_model_lock(path: Path = MODEL_LOCK) -> LockMetadata:
    text = path.read_text(encoding="utf-8")

    def extract(pattern: str, field: str) -> str:
        match = re.search(pattern, text, flags=re.MULTILINE)
        if not match:
            raise ValueError(f"Missing {field} in {path}")
        return match.group(1).strip()

    return LockMetadata(
        status=extract(r"^Status:\s*(\S+)\s*$", "status"),
        model_version_sha=extract(r"model_version_sha:\s*([0-9a-f]{40})", "model_version_sha"),
        scenario_definitions_sha=extract(
            r"scenario_definitions_sha:\s*([0-9a-f]{40})", "scenario_definitions_sha"
        ),
        freeze_timestamp_utc=extract(
            r"freeze_timestamp_utc:\s*([0-9T:\-]+Z)", "freeze_timestamp_utc"
        ),
        rng_seed=extract(r"rng_seed:\s*(\d+)", "rng_seed"),
    )


def read_london_vi_cap(path: Path = LONDON_VI_CAP) -> float:
    first_line = path.read_text(encoding="utf-8").splitlines()[0].strip()
    if first_line == "S5_REMOVED":
        raise ValueError("Phase 14 expects S5 to be present; london_vi_cap is S5_REMOVED")
    return float(first_line)


def _is_true(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().casefold() == "true"
    return bool(value)


def load_validated_sources() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, LockMetadata, float, str]:
    lock = parse_model_lock()
    outputs_sha = sha256_file(SCENARIO_OUTPUTS)
    scenario_definitions_sha = git_hash_object(SCENARIO_DEFINITIONS)

    if lock.status != "LOCKED":
        raise ValueError(f"Model lock status must be LOCKED, found {lock.status!r}")
    if lock.scenario_definitions_sha != LOCKED_SCENARIO_DEFINITIONS_SHA:
        raise ValueError("Model lock scenario_definitions_sha does not match Phase 13 lock")
    if scenario_definitions_sha != LOCKED_SCENARIO_DEFINITIONS_SHA:
        raise ValueError(
            "docs/SCENARIO_DEFINITIONS.md hash mismatch: "
            f"{scenario_definitions_sha} != {LOCKED_SCENARIO_DEFINITIONS_SHA}"
        )
    if outputs_sha != LOCKED_SCENARIO_OUTPUTS_SHA256:
        raise ValueError(
            "artifacts/scenario_outputs.csv SHA256 mismatch: "
            f"{outputs_sha} != {LOCKED_SCENARIO_OUTPUTS_SHA256}"
        )

    outputs = pd.read_csv(SCENARIO_OUTPUTS)
    logs = pd.read_csv(SCENARIO_LOG)
    dim = pd.read_csv(AUTHORITY_DIMENSION)
    centroids = pd.read_csv(AUTHORITY_CENTROIDS)
    london_vi_cap = read_london_vi_cap()

    if len(outputs) != EXPECTED_ROWS:
        raise ValueError(f"Expected {EXPECTED_ROWS} scenario rows, found {len(outputs)}")
    if outputs["authority_code"].nunique() != EXPECTED_AUTHORITIES:
        raise ValueError(
            f"Expected {EXPECTED_AUTHORITIES} active authorities, "
            f"found {outputs['authority_code'].nunique()}"
        )
    if set(outputs["scenario_id"]) != set(SCENARIO_LABELS):
        raise ValueError("Scenario outputs do not contain the expected S0-S5 set")
    if set(outputs["metric"]) != set(METRIC_LABELS):
        raise ValueError("Scenario outputs do not contain the expected metric set")
    if not ((outputs["P10"] <= outputs["P50"]) & (outputs["P50"] <= outputs["P90"])).all():
        raise ValueError("Scenario outputs contain interval ordering violations")
    if outputs[["point_estimate", "P10", "P50", "P90"]].isna().any().any():
        raise ValueError("Scenario outputs contain null estimate or interval values")

    event_types = set(logs.get("event_type", pd.Series(dtype=str)).dropna())
    bad_events = sorted(BLOCKING_EVENTS & event_types)
    if bad_events:
        raise ValueError(f"Blocking scenario log events present: {bad_events}")

    return outputs, logs, dim, centroids, lock, london_vi_cap, outputs_sha


def build_scenario_outputs_export(
    outputs: pd.DataFrame,
    logs: pd.DataFrame,
    dim: pd.DataFrame,
    centroids: pd.DataFrame,
    lock: LockMetadata,
    london_vi_cap: float,
    outputs_sha: str,
) -> pd.DataFrame:
    active_dim = dim[dim["election_active_2026"].map(_is_true)].copy()
    active_dim = active_dim[active_dim["authority_code"] != "E09000001"].copy()
    dim_cols = [
        "authority_code",
        "authority_type",
        "region",
        "all_out_2026",
    ]
    centroids = centroids[["authority_code", "lat", "lon"]].drop_duplicates("authority_code")
    if centroids["authority_code"].duplicated().any():
        raise ValueError("Authority centroids must have one row per authority")

    export = outputs.merge(active_dim[dim_cols], on="authority_code", how="left")
    export = export.merge(centroids, on="authority_code", how="left")
    if export[["region", "authority_type", "lat", "lon"]].isna().any().any():
        missing = export.loc[
            export[["region", "authority_type", "lat", "lon"]].isna().any(axis=1),
            "authority_code",
        ].drop_duplicates()
        raise ValueError(f"Missing dimension or coordinate data for {sorted(missing)}")

    cap_events = logs[logs["event_type"] == "s5_vi_capped"].copy()
    cap_keys = set(zip(cap_events["scenario_id"], cap_events["authority_code"], cap_events["metric"]))

    export["scenario_label"] = export["scenario_id"].map(SCENARIO_LABELS)
    export["scenario_order"] = export["scenario_id"].map(SCENARIO_ORDER)
    export["tier_label"] = export["tier"].map(TIER_LABELS)
    export["metric_label"] = export["metric"].map(METRIC_LABELS)
    export["metric_order"] = export["metric"].map(METRIC_ORDER)
    export["interval_width"] = export["P90"] - export["P10"]
    export["uncertainty_asymmetry"] = (export["P90"] - export["P50"]) - (
        export["P50"] - export["P10"]
    )
    export["is_london"] = export["tier"].astype(int).eq(2)
    export["is_copied_from_s0"] = export["notes"].fillna("").eq("copied_from_s0")
    export["is_s5_copy"] = export["scenario_id"].eq("S5") & export["is_copied_from_s0"]
    export["is_turnout_only_s4"] = export["scenario_id"].eq("S4") & export["metric"].eq(
        "turnout_delta"
    )
    export["is_s5_london_cap_applicable"] = (
        export["scenario_id"].eq("S5")
        & export["is_london"]
        & export["metric"].eq("volatility_score")
    )
    export["is_s5_london_cap_binding"] = [
        (scenario_id, authority_code, metric) in cap_keys
        for scenario_id, authority_code, metric in zip(
            export["scenario_id"], export["authority_code"], export["metric"]
        )
    ]
    export["source_artifact_sha256"] = outputs_sha
    export["model_version_sha"] = lock.model_version_sha
    export["scenario_definitions_sha"] = lock.scenario_definitions_sha
    export["freeze_timestamp_utc"] = lock.freeze_timestamp_utc
    export["london_vi_cap"] = london_vi_cap

    columns = [
        "scenario_id",
        "scenario_label",
        "scenario_order",
        "authority_code",
        "authority_name",
        "tier",
        "tier_label",
        "region",
        "authority_type",
        "election_active_2026",
        "all_out_2026",
        "metric",
        "metric_label",
        "metric_order",
        "P10",
        "P50",
        "P90",
        "interval_width",
        "uncertainty_asymmetry",
        "point_estimate",
        "notes",
        "lat",
        "lon",
        "is_london",
        "is_s5_copy",
        "is_copied_from_s0",
        "is_turnout_only_s4",
        "is_s5_london_cap_applicable",
        "is_s5_london_cap_binding",
        "london_vi_cap",
        "source_artifact_sha256",
        "model_version_sha",
        "scenario_definitions_sha",
        "freeze_timestamp_utc",
    ]
    export = export[columns].sort_values(
        ["scenario_order", "authority_code", "metric_order"]
    ).reset_index(drop=True)
    return export


def build_kpis(export: pd.DataFrame, logs: pd.DataFrame, london_vi_cap: float, outputs_sha: str) -> pd.DataFrame:
    event_counts = logs["event_type"].value_counts()
    s3_vol = export[
        (export["scenario_id"] == "S3") & (export["metric"] == "volatility_score")
    ]
    s5_london_vol = export[
        (export["scenario_id"] == "S5")
        & (export["metric"] == "volatility_score")
        & (export["is_london"])
    ]
    first = export.iloc[0]
    return pd.DataFrame(
        [
            {
                "model_version_sha": first["model_version_sha"],
                "scenario_definitions_sha": first["scenario_definitions_sha"],
                "freeze_timestamp_utc": first["freeze_timestamp_utc"],
                "n_rows": len(export),
                "n_authorities": export["authority_code"].nunique(),
                "n_scenarios": export["scenario_id"].nunique(),
                "n_metrics": export["metric"].nunique(),
                "scenario_outputs_sha256": outputs_sha,
                "s5_cap": london_vi_cap,
                "s5_cap_binding_events": int(event_counts.get("s5_vi_capped", 0)),
                "s3_median_vol_point_estimate": float(s3_vol["point_estimate"].median()),
                "max_s5_london_vol_p90": float(s5_london_vol["P90"].max()),
                "n_validation_failures": int(event_counts.get("validation_failure", 0)),
                "n_interval_ordering_violations": int(
                    event_counts.get("interval_ordering_violated", 0)
                ),
                "n_tier_pool_too_small": int(event_counts.get("tier_pool_too_small", 0)),
            }
        ]
    )


def build_rankings(export: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    vol = export[export["metric"] == "volatility_score"].copy()
    for scenario_id in ["S1", "S2", "S3"]:
        rows.append(
            vol[vol["scenario_id"] == scenario_id]
            .sort_values("P50", ascending=False)
            .head(15)
            .assign(ranking_type="top_volatility_p50", rank_metric="P50")
        )
    rows.append(
        vol.sort_values("interval_width", ascending=False)
        .head(15)
        .assign(ranking_type="widest_volatility_interval", rank_metric="interval_width")
    )
    rows.append(
        vol[vol["scenario_id"] == "S3"]
        .sort_values("point_estimate", ascending=False)
        .head(15)
        .assign(ranking_type="s3_top_volatility_point_estimate", rank_metric="point_estimate")
    )

    s0 = vol[vol["scenario_id"] == "S0"][
        ["authority_code", "P50", "P90", "point_estimate"]
    ].rename(
        columns={
            "P50": "s0_P50",
            "P90": "s0_P90",
            "point_estimate": "s0_point_estimate",
        }
    )
    s5_london = vol[(vol["scenario_id"] == "S5") & (vol["is_london"])].merge(
        s0, on="authority_code", how="left"
    )
    s5_london["s5_minus_s0_P50"] = s5_london["P50"] - s5_london["s0_P50"]
    s5_london["s5_minus_s0_P90"] = s5_london["P90"] - s5_london["s0_P90"]
    rows.append(
        s5_london.sort_values("P90", ascending=False)
        .assign(ranking_type="s5_london_vs_s0", rank_metric="P90")
    )

    out = pd.concat(rows, ignore_index=True, sort=False)
    out["rank"] = out.groupby("ranking_type").cumcount() + 1
    return out


def build_intervals(export: pd.DataFrame) -> pd.DataFrame:
    return export.sort_values(
        ["metric_order", "scenario_order", "interval_width"], ascending=[True, True, False]
    ).reset_index(drop=True)


def build_log_summary(logs: pd.DataFrame) -> pd.DataFrame:
    if logs.empty:
        return pd.DataFrame(columns=["event_type", "n_events", "n_authorities", "n_scenarios"])
    summary = (
        logs.groupby("event_type", dropna=False)
        .agg(
            n_events=("event_type", "size"),
            n_authorities=("authority_code", "nunique"),
            n_scenarios=("scenario_id", "nunique"),
        )
        .reset_index()
        .sort_values(["n_events", "event_type"], ascending=[False, True])
    )
    summary["is_blocking"] = summary["event_type"].isin(BLOCKING_EVENTS)
    return summary


def _markdown_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    if df.empty:
        return "_No rows._"
    display = df.copy()
    display = display.fillna("")
    headers = [str(col) for col in display.columns]
    rows = [[str(value) for value in row] for row in display.to_numpy()]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def build_audit_markdown(
    export: pd.DataFrame,
    kpis: pd.DataFrame,
    rankings: pd.DataFrame,
    log_summary: pd.DataFrame,
) -> str:
    medians = (
        export.groupby(["scenario_id", "scenario_label", "metric"], as_index=False)[
            ["point_estimate", "P50", "P10", "P90", "interval_width"]
        ]
        .median()
        .round(3)
        .sort_values(["scenario_id", "metric"])
    )
    vol = export[export["metric"] == "volatility_score"].copy()
    top_s3_point = rankings[
        rankings["ranking_type"] == "s3_top_volatility_point_estimate"
    ][["rank", "authority_name", "region", "point_estimate", "P10", "P50", "P90"]].round(3)
    widest = rankings[rankings["ranking_type"] == "widest_volatility_interval"][
        ["rank", "scenario_id", "authority_name", "region", "P10", "P50", "P90", "interval_width"]
    ].round(3)
    s5_status = kpis.iloc[0]
    s5_note = (
        "binding"
        if int(s5_status["s5_cap_binding_events"]) > 0
        else "non-binding in the frozen output"
    )
    s5_london = vol[(vol["scenario_id"] == "S5") & (vol["is_london"])][
        ["authority_name", "P10", "P50", "P90", "point_estimate", "is_s5_london_cap_binding"]
    ].sort_values("P90", ascending=False).head(10).round(3)

    return "\n\n".join(
        [
            "# Phase 14 Scenario Audit",
            "Generated from locked `artifacts/scenario_outputs.csv`. This audit is "
            "a dashboard QA artifact, not a model artifact.",
            "## Coverage",
            _markdown_table(kpis.T.reset_index().rename(columns={"index": "field", 0: "value"})),
            "## Scenario Medians",
            _markdown_table(medians),
            "## S3 Volatility Point-Estimate Ranking",
            _markdown_table(top_s3_point),
            "## Widest Volatility Intervals",
            _markdown_table(widest),
            "## S5 London Cap Check",
            f"The S5 London VOL cap is {s5_note}. Dashboard copy must not imply "
            "the cap changed outputs unless cap-binding events are present.",
            _markdown_table(s5_london),
            "## Scenario Log Summary",
            _markdown_table(log_summary),
            "## Narrative Guardrails",
            "- This is scenario analysis, not a forecast.",
            "- Use `point_estimate` for scenario shock magnitude.",
            "- Use P10/P50/P90 for calibrated uncertainty.",
            "- `delta_fi` is also part of `volatility_score`; do not treat them as independent signals.",
            "- Negative `volatility_score` interval values are composite uncertainty, not negative electoral churn.",
        ]
    ) + "\n"


def write_exports() -> dict[str, Path]:
    outputs, logs, dim, centroids, lock, london_vi_cap, outputs_sha = load_validated_sources()
    export = build_scenario_outputs_export(outputs, logs, dim, centroids, lock, london_vi_cap, outputs_sha)
    kpis = build_kpis(export, logs, london_vi_cap, outputs_sha)
    rankings = build_rankings(export)
    intervals = build_intervals(export)
    log_summary = build_log_summary(logs)

    TABLEAU.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    paths = {
        "outputs": TABLEAU / "tableau_scenario_outputs.csv",
        "kpis": TABLEAU / "tableau_scenario_kpis.csv",
        "rankings": TABLEAU / "tableau_scenario_rankings.csv",
        "intervals": TABLEAU / "tableau_scenario_intervals.csv",
        "log_summary": TABLEAU / "tableau_scenario_log_summary.csv",
        "audit": AUDIT_PATH,
    }
    export.to_csv(paths["outputs"], index=False)
    kpis.to_csv(paths["kpis"], index=False)
    rankings.to_csv(paths["rankings"], index=False)
    intervals.to_csv(paths["intervals"], index=False)
    log_summary.to_csv(paths["log_summary"], index=False)
    paths["audit"].write_text(build_audit_markdown(export, kpis, rankings, log_summary), encoding="utf-8")
    return paths


def main() -> None:
    paths = write_exports()
    for label, path in paths.items():
        print(f"Wrote {label}: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
