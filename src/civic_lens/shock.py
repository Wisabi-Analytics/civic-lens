from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")

from civic_lens.party_normalise import challenger_party_family

PROCESSED_DIR = Path("data/processed")
INTERIM_DIR = Path("data/interim")
ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dim = pd.read_csv(PROCESSED_DIR / "authority_dimension.csv")
    psb = pd.read_csv(PROCESSED_DIR / "party_swings_backtest.csv")
    tm = pd.read_csv(PROCESSED_DIR / "training_metrics.csv")
    ba = pd.read_csv(PROCESSED_DIR / "backtest_actuals_2022.csv")
    clean = pd.read_csv(
        PROCESSED_DIR / "clean_election_results.csv",
        usecols=["party_standardised", "party_group"],
        low_memory=False,
    )
    imd = pd.read_parquet(INTERIM_DIR / "imd_2019.parquet")
    return dim, psb, tm, ba, clean, imd


def derive_s5_cap(tm: pd.DataFrame, ba: pd.DataFrame) -> float | None:
    tm_boro = tm[
        (tm["computation_level"] == "borough")
        & (tm["tier"] == 2)
        & (tm["authority_code"] != "E09000001")
    ].copy()
    ba_boro = ba[
        (ba["computation_level"] == "borough")
        & (ba["tier"] == 2)
        & (ba["authority_code"] != "E09000001")
    ].copy()
    pool = pd.concat(
        [tm_boro["volatility_score"].dropna(), ba_boro["volatility_score"].dropna()],
        ignore_index=True,
    )
    if len(pool) < 20:
        content = "\n".join(
            [
                "S5_REMOVED",
                f"Reason: only {len(pool)} Tier-2 observations available (threshold: 20)",
            ]
        )
        (ARTIFACTS_DIR / "london_vi_cap.txt").write_text(content + "\n", encoding="utf-8")
        return None
    cap = float(np.percentile(pool, 90))
    lines = [
        f"{cap:.6f}",
        f"# London VI 90th percentile from {len(pool)} observations",
        f"# {len(tm_boro['volatility_score'].dropna())} training + {len(ba_boro['volatility_score'].dropna())} backtest",
    ]
    (ARTIFACTS_DIR / "london_vi_cap.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return cap


def _party_group_lookup(clean: pd.DataFrame) -> pd.DataFrame:
    return (
        clean[["party_standardised", "party_group"]]
        .dropna()
        .drop_duplicates()
        .groupby("party_standardised", as_index=False)["party_group"]
        .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else s.iloc[0])
    )


def identify_challengers(psb: pd.DataFrame, clean: pd.DataFrame | None = None) -> pd.DataFrame:
    psb_boro = psb[psb["computation_level"] == "borough"].copy()
    party_col = "metric_party_family" if "metric_party_family" in psb_boro.columns else "party_standardised"
    if "party_group" not in psb_boro.columns and clean is not None:
        psb_boro = psb_boro.merge(_party_group_lookup(clean), on="party_standardised", how="left")
    if "party_group" not in psb_boro.columns:
        psb_boro["party_group"] = None
    psb_boro["party_bucket"] = psb_boro.apply(
        lambda row: challenger_party_family(row[party_col], row["party_group"]),
        axis=1,
    )
    grouped = (
        psb_boro.groupby(["authority_code", "party_bucket"], dropna=False)
        .agg(
            swing_pp=("swing_pp", "sum"),
            vote_share_2022=("vote_share_2022", "sum"),
        )
        .reset_index()
    )
    rows: list[dict] = []
    for auth, grp in grouped.groupby("authority_code"):
        cand = grp[grp["swing_pp"] > 0].copy()
        if cand.empty:
            cand = grp.copy()
        cand = cand.sort_values(["swing_pp", "vote_share_2022"], ascending=[False, False])
        top = cand.iloc[0]
        rows.append(
            {
                "authority_code": auth,
                "challenger_party": top["party_bucket"],
                "challenger_swing_2018_2022": float(top["swing_pp"]),
                "challenger_share_2022": float(top["vote_share_2022"]),
            }
        )
    return pd.DataFrame(rows)


def _imd_lookup(imd: pd.DataFrame) -> pd.DataFrame:
    lad_col = "Local Authority District code (2019)"
    if lad_col not in imd.columns or "imd_decile" not in imd.columns:
        raise KeyError("IMD file missing required columns for LAD join")
    return imd[[lad_col, "imd_decile"]].rename(columns={lad_col: "authority_code"})


def build_shock_metrics(
    dim: pd.DataFrame,
    challengers: pd.DataFrame,
    imd: pd.DataFrame,
    london_vi_cap: float | None,
) -> pd.DataFrame:
    scenarios = {
        "S0": {"challenger_shock": 0.0, "established_shock": 0.0, "turnout": 0.0},
        "S1": {"challenger_shock": 2.0, "established_shock": -2.0, "turnout": None},
        "S2": {"challenger_shock": -1.5, "established_shock": 1.5, "turnout": None},
        "S3": {"challenger_shock": 4.0, "established_shock": -4.0, "turnout": None},
        "S4": {"challenger_shock": None, "established_shock": None, "turnout": "imd"},
    }
    if london_vi_cap is not None:
        scenarios["S5"] = {"challenger_shock": None, "established_shock": None, "turnout": None}

    auth = dim.merge(challengers, on="authority_code", how="left")
    auth = auth.merge(_imd_lookup(imd), on="authority_code", how="left")

    records: list[dict] = []
    for _, row in auth.iterrows():
        for sid, conf in scenarios.items():
            rec = {
                "authority_code": row["authority_code"],
                "authority_name": row["authority_name"],
                "tier": row["tier"],
                "election_active_2026": row["election_active_2026"],
                "scenario_id": sid,
                "challenger_party": None,
                "challenger_swing_pp": None,
                "established_swing_pp": None,
                "turnout_shock_pp": None,
                "imd_decile": int(row["imd_decile"]) if pd.notna(row["imd_decile"]) else None,
                "vi_cap": None,
                "notes": None,
            }
            if sid in {"S1", "S2", "S3"}:
                if pd.notna(row.get("challenger_party")):
                    rec["challenger_party"] = row["challenger_party"]
                    rec["challenger_swing_pp"] = conf["challenger_shock"]
                    rec["established_swing_pp"] = conf["established_shock"]
                else:
                    rec["notes"] = "no_challenger_identified"
            elif sid == "S0":
                rec["challenger_swing_pp"] = 0.0
                rec["established_swing_pp"] = 0.0
                rec["turnout_shock_pp"] = 0.0
            elif sid == "S4":
                if pd.notna(row.get("imd_decile")) and int(row["imd_decile"]) <= 3:
                    rec["turnout_shock_pp"] = 3.0
                else:
                    rec["turnout_shock_pp"] = 0.0
                    if pd.isna(row.get("imd_decile")):
                        rec["notes"] = "imd_decile_null_no_shock_applied"
            elif sid == "S5":
                if int(row["tier"]) == 2:
                    rec["vi_cap"] = float(london_vi_cap)
                else:
                    rec["notes"] = "S5_london_only"
            records.append(rec)

    out = pd.DataFrame(records)
    out.to_csv(PROCESSED_DIR / "shock_metrics.csv", index=False)
    return out


def main() -> None:
    dim, psb, tm, ba, clean, imd = load_inputs()
    cap = derive_s5_cap(tm, ba)
    challengers = identify_challengers(psb, clean)
    shock = build_shock_metrics(dim, challengers, imd, cap)
    print(f"Wrote {ARTIFACTS_DIR / 'london_vi_cap.txt'}")
    print(f"Wrote {PROCESSED_DIR / 'shock_metrics.csv'} ({len(shock)} rows)")


if __name__ == "__main__":
    main()
