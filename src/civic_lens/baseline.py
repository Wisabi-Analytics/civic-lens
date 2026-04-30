from __future__ import annotations

from pathlib import Path
import logging
import sys

import pandas as pd

sys.path.insert(0, "src")

from civic_lens.metrics import (
    fragmentation_index,
    seat_change,
    swing_concentration,
    turnout_delta,
    volatility_score,
    vote_share_swing,
)
from civic_lens.party_normalise import metric_party_family

LOGGER = logging.getLogger(__name__)

PROCESSED_DIR = Path("data/processed")
TRAINING_YEARS = frozenset({2014, 2015, 2016})
BACKTEST_YEAR = 2018
TARGET_YEAR = 2022
WARD_MATCH_METHODS = {"exact_code", "name_matched"}


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    clean = pd.read_csv(PROCESSED_DIR / "clean_election_results.csv", low_memory=False)
    conc = pd.read_csv(PROCESSED_DIR / "concordance_table.csv")
    dim = pd.read_csv(PROCESSED_DIR / "authority_dimension.csv")
    active = clean[clean["analysis_level"] != "descriptive_only"].copy()
    return active, conc, dim


def build_ward_shares(active: pd.DataFrame, year: int) -> pd.DataFrame:
    sub = active[active["election_year"] == year].copy()
    sub["metric_party_family"] = sub.apply(
        lambda row: metric_party_family(row["party_standardised"], row["party_group"]),
        axis=1,
    )
    grouped = (
        sub.groupby(
            [
                "authority_code",
                "authority_name",
                "tier",
                "ward_code",
                "ward_name_clean",
                "metric_party_family",
            ],
            dropna=False,
        )
        .agg(
            party_standardised=("party_standardised", "first"),
            party_group=("party_group", "first"),
            votes=("votes", "sum"),
            total_valid_votes=("total_valid_votes", "first"),
            seats_won_party=("seats_won", "sum"),
            seats_contested=("seats_contested", "first"),
            electorate=("electorate", "first"),
        )
        .reset_index()
    )
    grouped["ward_vote_pool"] = grouped.groupby(
        ["authority_code", "ward_code"], dropna=False
    )["votes"].transform("sum")
    grouped["vote_share_pct"] = grouped.apply(
        lambda row: (row["votes"] / row["ward_vote_pool"] * 100)
        if pd.notna(row["ward_vote_pool"]) and row["ward_vote_pool"] > 0
        else None,
        axis=1,
    )
    return grouped


def build_ward_turnout(active: pd.DataFrame, year: int) -> pd.DataFrame:
    return (
        active[active["election_year"] == year][
            ["authority_code", "ward_code", "turnout_pct", "electorate"]
        ]
        .drop_duplicates(subset=["authority_code", "ward_code"])
        .copy()
    )


def ward_shares_dict(wp: pd.DataFrame, auth: str, ward_code: str) -> dict[str, float]:
    rows = wp[(wp["authority_code"] == auth) & (wp["ward_code"] == ward_code)]
    return {
        row["metric_party_family"]: float(row["vote_share_pct"])
        for _, row in rows.iterrows()
        if pd.notna(row["vote_share_pct"])
    }


def borough_shares_dict(wp: pd.DataFrame, auth: str) -> dict[str, float]:
    rows = wp[wp["authority_code"] == auth]
    if rows.empty:
        return {}
    borough_vote_pool = rows["votes"].sum()
    if pd.isna(borough_vote_pool) or borough_vote_pool <= 0:
        return {}
    party_votes = rows.groupby("metric_party_family")["votes"].sum()
    return {
        party: float(votes) / float(borough_vote_pool) * 100
        for party, votes in party_votes.items()
        if pd.notna(votes)
    }


def ward_turnout_val(turnout_df: pd.DataFrame, auth: str, ward_code: str) -> float | None:
    row = turnout_df[
        (turnout_df["authority_code"] == auth) & (turnout_df["ward_code"] == ward_code)
    ]
    if row.empty or pd.isna(row["turnout_pct"].iloc[0]):
        return None
    return float(row["turnout_pct"].iloc[0])


def borough_turnout_val(turnout_df: pd.DataFrame, auth: str) -> tuple[float | None, str | None]:
    rows = turnout_df[
        (turnout_df["authority_code"] == auth) & turnout_df["turnout_pct"].notna()
    ]
    if rows.empty:
        return None, "turnout_missing_all_wards"

    has_electorate = rows["electorate"].notna() & (rows["electorate"] > 0)
    if has_electorate.mean() >= 0.5:
        weighted = rows.loc[has_electorate, ["turnout_pct", "electorate"]]
        value = float((weighted["turnout_pct"] * weighted["electorate"]).sum() / weighted["electorate"].sum())
        return value, None

    return float(rows["turnout_pct"].mean()), "turnout_plain_mean_fallback"


def compose_notes(*parts: str | None) -> str | None:
    filtered = [part for part in parts if part]
    return " | ".join(filtered) if filtered else None


def max_swing(swings: dict[str, float]) -> tuple[str | None, float | None]:
    if not swings:
        return None, None
    party = max(swings, key=lambda key: abs(swings[key]))
    return party, swings[party]


def training_ward_pairs(conc: pd.DataFrame) -> pd.DataFrame:
    return conc[
        (conc["analysis_level"] == "ward")
        & (conc["match_method"].isin(WARD_MATCH_METHODS))
        & conc["ward_code_training"].notna()
        & conc["ward_code_2018"].notna()
    ].copy()


def backtest_ward_pairs(conc: pd.DataFrame) -> pd.DataFrame:
    return conc[
        (conc["analysis_level"] == "ward")
        & (conc["match_method"].isin(WARD_MATCH_METHODS))
        & conc["ward_code_2018"].notna()
        & conc["ward_code_2022"].notna()
    ].copy()


def compute_training_metrics(
    active: pd.DataFrame, conc: pd.DataFrame, dim: pd.DataFrame
) -> tuple[list[dict], list[dict]]:
    metric_records: list[dict] = []
    swing_records: list[dict] = []
    shares = {
        year: build_ward_shares(active, year)
        for year in sorted(TRAINING_YEARS | {BACKTEST_YEAR})
    }
    turnout = {
        year: build_ward_turnout(active, year)
        for year in sorted(TRAINING_YEARS | {BACKTEST_YEAR})
    }
    activity = dict(zip(dim["authority_code"], dim["election_active_2026"]))
    ward_pairs = training_ward_pairs(conc)

    LOGGER.info("Training ward pairs available: %s", len(ward_pairs))

    for _, row in ward_pairs.iterrows():
        auth = row["authority_code"]
        ward_training = row["ward_code_training"]
        ward_2018 = row["ward_code_2018"]
        years_present = set(
            active[
                (active["authority_code"] == auth)
                & (active["ward_code"] == ward_training)
                & (active["analysis_level"] == "ward")
                & (active["election_year"].isin(TRAINING_YEARS))
            ]["election_year"].unique()
        )
        if not years_present:
            continue
        training_year = max(years_present)
        shares_training = ward_shares_dict(shares[training_year], auth, ward_training)
        shares_2018 = ward_shares_dict(shares[BACKTEST_YEAR], auth, ward_2018)
        if not shares_training or not shares_2018:
            continue

        try:
            swings = vote_share_swing(shares_2018, shares_training)
            fi_training = fragmentation_index(shares_training)
            fi_2018 = fragmentation_index(shares_2018)
            vol = volatility_score(swings, fi_t=fi_2018, fi_t1=fi_training)
            sc = swing_concentration(swings)
        except (ValueError, ZeroDivisionError) as exc:
            LOGGER.warning("Training ward metric skipped for %s/%s: %s", auth, ward_training, exc)
            continue

        turnout_training = ward_turnout_val(turnout[training_year], auth, ward_training)
        turnout_2018 = ward_turnout_val(turnout[BACKTEST_YEAR], auth, ward_2018)
        turnout_change = turnout_delta(turnout_2018, turnout_training)

        seats_training_rows = shares[training_year][
            (shares[training_year]["authority_code"] == auth)
            & (shares[training_year]["ward_code"] == ward_training)
        ]
        seats_2018_rows = shares[BACKTEST_YEAR][
            (shares[BACKTEST_YEAR]["authority_code"] == auth)
            & (shares[BACKTEST_YEAR]["ward_code"] == ward_2018)
        ]
        seats_delta = seat_change(
            int(seats_2018_rows["seats_won_party"].sum()),
            int(seats_training_rows["seats_won_party"].sum()),
        )

        meta = shares[BACKTEST_YEAR][
            (shares[BACKTEST_YEAR]["authority_code"] == auth)
            & (shares[BACKTEST_YEAR]["ward_code"] == ward_2018)
        ]
        if meta.empty:
            continue
        meta_row = meta.iloc[0]
        max_party, max_swing_pp = max_swing(swings)

        metric_records.append(
            {
                "authority_code": auth,
                "authority_name": meta_row["authority_name"],
                "tier": meta_row["tier"],
                "election_active_2026": bool(activity.get(auth, False)),
                "ward_code": ward_2018,
                "ward_name_clean": meta_row["ward_name_clean"],
                "computation_level": "ward",
                "training_year": training_year,
                "fi_training": round(fi_training, 6),
                "fi_2018": round(fi_2018, 6),
                "delta_fi": round(fi_2018 - fi_training, 6),
                "turnout_training": round(turnout_training, 4) if turnout_training is not None else None,
                "turnout_2018": round(turnout_2018, 4) if turnout_2018 is not None else None,
                "turnout_delta": round(turnout_change, 4) if turnout_change is not None else None,
                "volatility_score": round(vol, 6) if vol is not None else None,
                "swing_concentration": round(sc, 6),
                "seat_change": seats_delta,
                "max_swing_party": max_party,
                "max_swing_pp": round(max_swing_pp, 4) if max_swing_pp is not None else None,
                "n_parties_training": len(shares_training),
                "n_parties_2018": len(shares_2018),
                "notes": None,
            }
        )

        for party, swing_pp in swings.items():
            swing_records.append(
                {
                    "authority_code": auth,
                    "ward_code": ward_2018,
                    "computation_level": "ward",
                    "training_year": training_year,
                    "party_standardised": party,
                    "metric_party_family": party,
                    "vote_share_training": shares_training.get(party, 0.0),
                    "vote_share_2018": shares_2018.get(party, 0.0),
                    "swing_pp": round(swing_pp, 6),
                }
            )

    for _, dim_row in dim.iterrows():
        auth = dim_row["authority_code"]
        auth_training = active[
            (active["authority_code"] == auth) & (active["election_year"].isin(TRAINING_YEARS))
        ].copy()
        auth_2018 = active[
            (active["authority_code"] == auth) & (active["election_year"] == BACKTEST_YEAR)
        ].copy()

        note_parts: list[str | None] = ["ward_composite_training_baseline"]
        shares_training_borough: dict[str, float] = {}
        shares_2018_borough: dict[str, float] = {}
        fi_training = fi_2018 = vol = sc = max_swing_pp = None
        max_party = None
        turnout_training = turnout_2018 = turnout_change = None

        if auth_training.empty:
            note_parts.append("missing_training_data")
        else:
            latest_year = auth_training.groupby("ward_code")["election_year"].max().reset_index(name="latest_year")
            auth_training = auth_training.merge(latest_year, on="ward_code", how="left")
            composite = auth_training[auth_training["election_year"] == auth_training["latest_year"]].copy()

            composite["metric_party_family"] = composite.apply(
                lambda row: metric_party_family(row["party_standardised"], row["party_group"]),
                axis=1,
            )
            party_votes_training = composite.groupby("metric_party_family")["votes"].sum()
            training_vote_pool = composite["votes"].sum()
            if pd.notna(training_vote_pool) and training_vote_pool > 0:
                shares_training_borough = {
                    party: float(votes) / float(training_vote_pool) * 100
                    for party, votes in party_votes_training.items()
                    if pd.notna(votes)
                }
                ward_turnout_rows = composite.drop_duplicates("ward_code")[
                    ["authority_code", "ward_code", "turnout_pct", "electorate"]
                ]
                turnout_training, turnout_note = borough_turnout_val(ward_turnout_rows, auth)
                note_parts.append(turnout_note)
            else:
                note_parts.append("missing_training_vote_pool")

        if auth_2018.empty:
            note_parts.append("missing_2018_data")
        else:
            shares_2018_borough = borough_shares_dict(shares[BACKTEST_YEAR], auth)
            turnout_2018, turnout_note_2018 = borough_turnout_val(turnout[BACKTEST_YEAR], auth)
            note_parts.append(turnout_note_2018)
            if not shares_2018_borough:
                note_parts.append("missing_2018_total_valid_votes")

        if shares_training_borough and shares_2018_borough:
            try:
                swings = vote_share_swing(shares_2018_borough, shares_training_borough)
                fi_training = fragmentation_index(shares_training_borough)
                fi_2018 = fragmentation_index(shares_2018_borough)
                vol = volatility_score(swings, fi_t=fi_2018, fi_t1=fi_training)
                sc = swing_concentration(swings)
                max_party, max_swing_pp = max_swing(swings)
                turnout_change = turnout_delta(turnout_2018, turnout_training)
                for party, swing_pp in swings.items():
                    swing_records.append(
                        {
                            "authority_code": auth,
                            "ward_code": None,
                            "computation_level": "borough",
                            "training_year": None,
                            "party_standardised": party,
                            "metric_party_family": party,
                            "vote_share_training": shares_training_borough.get(party, 0.0),
                            "vote_share_2018": shares_2018_borough.get(party, 0.0),
                            "swing_pp": round(swing_pp, 6),
                        }
                    )
            except (ValueError, ZeroDivisionError) as exc:
                note_parts.append("metric_computation_failed")
                LOGGER.warning("Training borough metric skipped for %s: %s", auth, exc)

        metric_records.append(
            {
                "authority_code": auth,
                "authority_name": dim_row["authority_name"],
                "tier": dim_row["tier"],
                "election_active_2026": bool(dim_row["election_active_2026"]),
                "ward_code": None,
                "ward_name_clean": None,
                "computation_level": "borough",
                "training_year": None,
                "fi_training": round(fi_training, 6) if fi_training is not None else None,
                "fi_2018": round(fi_2018, 6) if fi_2018 is not None else None,
                "delta_fi": round(fi_2018 - fi_training, 6)
                if fi_training is not None and fi_2018 is not None
                else None,
                "turnout_training": round(turnout_training, 4) if turnout_training is not None else None,
                "turnout_2018": round(turnout_2018, 4) if turnout_2018 is not None else None,
                "turnout_delta": round(turnout_change, 4) if turnout_change is not None else None,
                "volatility_score": round(vol, 6) if vol is not None else None,
                "swing_concentration": round(sc, 6) if sc is not None else None,
                "seat_change": None,
                "max_swing_party": max_party,
                "max_swing_pp": round(max_swing_pp, 4) if max_swing_pp is not None else None,
                "n_parties_training": len(shares_training_borough) if shares_training_borough else None,
                "n_parties_2018": len(shares_2018_borough) if shares_2018_borough else None,
                "notes": compose_notes(*note_parts),
            }
        )

    return metric_records, swing_records


def compute_backtest_actuals(
    active: pd.DataFrame, conc: pd.DataFrame, dim: pd.DataFrame
) -> tuple[list[dict], list[dict]]:
    metric_records: list[dict] = []
    swing_records: list[dict] = []
    shares_2018 = build_ward_shares(active, BACKTEST_YEAR)
    shares_2022 = build_ward_shares(active, TARGET_YEAR)
    turnout_2018 = build_ward_turnout(active, BACKTEST_YEAR)
    turnout_2022 = build_ward_turnout(active, TARGET_YEAR)

    ward_pairs = backtest_ward_pairs(conc)
    LOGGER.info("Backtest ward pairs available: %s", len(ward_pairs))

    for _, row in ward_pairs.iterrows():
        auth = row["authority_code"]
        ward_2018 = row["ward_code_2018"]
        ward_2022 = row["ward_code_2022"]
        shares_18 = ward_shares_dict(shares_2018, auth, ward_2018)
        shares_22 = ward_shares_dict(shares_2022, auth, ward_2022)
        if not shares_18 or not shares_22:
            continue

        try:
            swings = vote_share_swing(shares_22, shares_18)
            fi_18 = fragmentation_index(shares_18)
            fi_22 = fragmentation_index(shares_22)
            vol = volatility_score(swings, fi_t=fi_22, fi_t1=fi_18)
            sc = swing_concentration(swings)
        except (ValueError, ZeroDivisionError) as exc:
            LOGGER.warning("Backtest ward metric skipped for %s/%s: %s", auth, ward_2018, exc)
            continue

        turnout_18 = ward_turnout_val(turnout_2018, auth, ward_2018)
        turnout_22 = ward_turnout_val(turnout_2022, auth, ward_2022)
        turnout_change = turnout_delta(turnout_22, turnout_18)
        seats_18 = shares_2018[
            (shares_2018["authority_code"] == auth) & (shares_2018["ward_code"] == ward_2018)
        ]
        seats_22 = shares_2022[
            (shares_2022["authority_code"] == auth) & (shares_2022["ward_code"] == ward_2022)
        ]
        seats_delta = seat_change(
            int(seats_22["seats_won_party"].sum()),
            int(seats_18["seats_won_party"].sum()),
        )
        meta = shares_2022[
            (shares_2022["authority_code"] == auth) & (shares_2022["ward_code"] == ward_2022)
        ]
        if meta.empty:
            continue
        meta_row = meta.iloc[0]
        max_party, max_swing_pp = max_swing(swings)

        metric_records.append(
            {
                "authority_code": auth,
                "authority_name": meta_row["authority_name"],
                "tier": meta_row["tier"],
                "election_active_2026": bool(dim.loc[dim["authority_code"] == auth, "election_active_2026"].iloc[0]),
                "ward_code_2018": ward_2018,
                "ward_code_2022": ward_2022,
                "ward_name_clean": row["ward_name_clean"],
                "computation_level": "ward",
                "match_method": row["match_method"],
                "fi_2018": round(fi_18, 6),
                "fi_2022": round(fi_22, 6),
                "delta_fi": round(fi_22 - fi_18, 6),
                "turnout_2018": round(turnout_18, 4) if turnout_18 is not None else None,
                "turnout_2022": round(turnout_22, 4) if turnout_22 is not None else None,
                "turnout_delta": round(turnout_change, 4) if turnout_change is not None else None,
                "volatility_score": round(vol, 6) if vol is not None else None,
                "swing_concentration": round(sc, 6),
                "seat_change": seats_delta,
                "max_swing_party": max_party,
                "max_swing_pp": round(max_swing_pp, 4) if max_swing_pp is not None else None,
                "n_parties_2018": len(shares_18),
                "n_parties_2022": len(shares_22),
                "notes": None,
            }
        )
        for party, swing_pp in swings.items():
            swing_records.append(
                {
                    "authority_code": auth,
                    "ward_code_2018": ward_2018,
                    "ward_code_2022": ward_2022,
                    "computation_level": "ward",
                    "party_standardised": party,
                    "metric_party_family": party,
                    "vote_share_2018": shares_18.get(party, 0.0),
                    "vote_share_2022": shares_22.get(party, 0.0),
                    "swing_pp": round(swing_pp, 6),
                }
            )

    for _, dim_row in dim.iterrows():
        auth = dim_row["authority_code"]
        shares_18_borough = borough_shares_dict(shares_2018, auth)
        shares_22_borough = borough_shares_dict(shares_2022, auth)
        turnout_18, turnout_note_18 = borough_turnout_val(turnout_2018, auth)
        turnout_22, turnout_note_22 = borough_turnout_val(turnout_2022, auth)

        note_parts: list[str | None] = []
        if len(ward_pairs) == 0:
            note_parts.append("borough_only_backtest_no_2018_2022_ward_pairs")
        note_parts.extend([turnout_note_18, turnout_note_22])
        if not shares_18_borough:
            note_parts.append("missing_2018_data")
        if not shares_22_borough:
            note_parts.append("missing_2022_data")

        fi_18 = fi_22 = vol = sc = max_swing_pp = None
        max_party = None
        turnout_change = None

        if shares_18_borough and shares_22_borough:
            try:
                swings = vote_share_swing(shares_22_borough, shares_18_borough)
                fi_18 = fragmentation_index(shares_18_borough)
                fi_22 = fragmentation_index(shares_22_borough)
                vol = volatility_score(swings, fi_t=fi_22, fi_t1=fi_18)
                sc = swing_concentration(swings)
                turnout_change = turnout_delta(turnout_22, turnout_18)
                max_party, max_swing_pp = max_swing(swings)
                for party, swing_pp in swings.items():
                    swing_records.append(
                        {
                            "authority_code": auth,
                            "ward_code_2018": None,
                            "ward_code_2022": None,
                            "computation_level": "borough",
                            "party_standardised": party,
                            "metric_party_family": party,
                            "vote_share_2018": shares_18_borough.get(party, 0.0),
                            "vote_share_2022": shares_22_borough.get(party, 0.0),
                            "swing_pp": round(swing_pp, 6),
                        }
                    )
            except (ValueError, ZeroDivisionError) as exc:
                note_parts.append("metric_computation_failed")
                LOGGER.warning("Backtest borough metric skipped for %s: %s", auth, exc)

        metric_records.append(
            {
                "authority_code": auth,
                "authority_name": dim_row["authority_name"],
                "tier": dim_row["tier"],
                "election_active_2026": bool(dim_row["election_active_2026"]),
                "ward_code_2018": None,
                "ward_code_2022": None,
                "ward_name_clean": None,
                "computation_level": "borough",
                "match_method": "borough_aggregate",
                "fi_2018": round(fi_18, 6) if fi_18 is not None else None,
                "fi_2022": round(fi_22, 6) if fi_22 is not None else None,
                "delta_fi": round(fi_22 - fi_18, 6) if fi_18 is not None and fi_22 is not None else None,
                "turnout_2018": round(turnout_18, 4) if turnout_18 is not None else None,
                "turnout_2022": round(turnout_22, 4) if turnout_22 is not None else None,
                "turnout_delta": round(turnout_change, 4) if turnout_change is not None else None,
                "volatility_score": round(vol, 6) if vol is not None else None,
                "swing_concentration": round(sc, 6) if sc is not None else None,
                "seat_change": None,
                "max_swing_party": max_party,
                "max_swing_pp": round(max_swing_pp, 4) if max_swing_pp is not None else None,
                "n_parties_2018": len(shares_18_borough) if shares_18_borough else None,
                "n_parties_2022": len(shares_22_borough) if shares_22_borough else None,
                "notes": compose_notes(*note_parts),
            }
        )

    return metric_records, swing_records


def write_outputs(
    training_records: list[dict],
    training_swings: list[dict],
    backtest_records: list[dict],
    backtest_swings: list[dict],
) -> None:
    pd.DataFrame(training_records).to_csv(PROCESSED_DIR / "training_metrics.csv", index=False)
    pd.DataFrame(training_swings).to_csv(PROCESSED_DIR / "party_swings_training.csv", index=False)
    pd.DataFrame(backtest_records).to_csv(PROCESSED_DIR / "backtest_actuals_2022.csv", index=False)
    pd.DataFrame(backtest_swings).to_csv(PROCESSED_DIR / "party_swings_backtest.csv", index=False)


def run_plausibility_checks(dim: pd.DataFrame) -> None:
    training = pd.read_csv(PROCESSED_DIR / "training_metrics.csv")
    backtest = pd.read_csv(PROCESSED_DIR / "backtest_actuals_2022.csv")
    training_swings = pd.read_csv(PROCESSED_DIR / "party_swings_training.csv")
    backtest_swings = pd.read_csv(PROCESSED_DIR / "party_swings_backtest.csv")

    issues: list[str] = []
    all_auths = set(dim["authority_code"])

    for label, frame in [("training", training), ("backtest", backtest)]:
        borough_auths = set(frame.loc[frame["computation_level"] == "borough", "authority_code"])
        missing = sorted(all_auths - borough_auths)
        if missing:
            issues.append(f"{label}: missing borough rows for {missing}")
        for col in [column for column in frame.columns if column.startswith("fi_")]:
            if (frame[col].dropna() < 0.99).any():
                issues.append(f"{label}: {col} contains values below 1.0")
        if "swing_concentration" in frame.columns and (frame["swing_concentration"].dropna() < 0.99).any():
            issues.append(f"{label}: swing_concentration below 1.0")

    for label, frame in [("training", training_swings), ("backtest", backtest_swings)]:
        share_columns = [column for column in frame.columns if "vote_share" in column]
        for column in share_columns:
            values = frame[column].dropna()
            if not ((values >= 0).all() and (values <= 100).all()):
                issues.append(f"{label}: {column} outside [0,100]")

    if issues:
        raise AssertionError("\n".join(issues))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    active, conc, dim = load_inputs()
    LOGGER.info("Phase 9 baseline starting")
    training_records, training_swings = compute_training_metrics(active, conc, dim)
    backtest_records, backtest_swings = compute_backtest_actuals(active, conc, dim)
    write_outputs(training_records, training_swings, backtest_records, backtest_swings)
    run_plausibility_checks(dim)
    LOGGER.info(
        "Phase 9 baseline complete: %s training rows, %s backtest rows",
        len(training_records),
        len(backtest_records),
    )


if __name__ == "__main__":
    main()
