from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import pandas as pd
try:
    from scipy.stats import pearsonr as _scipy_pearsonr
except ImportError:  # pragma: no cover - optional dependency fallback
    _scipy_pearsonr = None

PROCESSED = Path("data/processed")
REPORTS = Path("reports/tableau_data")
REPORTS.mkdir(parents=True, exist_ok=True)

CITY_OF_LONDON = "E09000001"


def _pearson_with_p(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    """Return (r, p). If scipy is unavailable, return (r, nan)."""
    if len(x) < 3 or len(y) < 3:
        return np.nan, np.nan
    if _scipy_pearsonr is not None:
        r, p = _scipy_pearsonr(x, y)
        return float(r), float(p)
    return float(x.corr(y)), np.nan


def _fragmentation_index(shares: dict[str, float]) -> float:
    clean = [float(v) for v in shares.values() if pd.notna(v) and float(v) > 0]
    if not clean:
        return np.nan
    total = sum(clean)
    if total <= 0:
        return np.nan
    proportions = [v / total for v in clean]
    return 1.0 / sum(p * p for p in proportions)


def _tier_label(tier: int) -> str:
    return {
        1: "Metropolitan Borough",
        2: "London Borough",
        3: "West Yorkshire",
    }.get(int(tier), "Unknown")


def _normalize_party_label(name: str) -> str:
    s = str(name).strip().lower()
    if "labour" in s:
        return "LAB"
    if "conservative" in s:
        return "CON"
    if "liberal democrats" in s or s == "lib dem":
        return "LD"
    if "green party" in s or s == "green":
        return "GREEN"
    if "reform" in s or "uk independence" in s or "ukip" in s:
        return "REFORM"
    if "yorkshire party" in s:
        return "YORKS"
    if s.startswith("ind") or "independent" in s:
        return "IND"
    return "OTHER"


def _party_color(label: str) -> str:
    return {
        "LAB": "#E4003B",
        "CON": "#0087DC",
        "LD": "#FAA61A",
        "GREEN": "#02A95B",
        "REFORM": "#6B2FBE",
        "IND": "#6B7280",
        "YORKS": "#228B22",
        "OTHER": "#9CA3AF",
    }.get(label, "#9CA3AF")


def _borough_turnout(clean: pd.DataFrame, year: int) -> pd.DataFrame:
    df = clean[clean["election_year"] == year].copy()
    ward = df[
        ["authority_code", "ward_code", "turnout_pct", "electorate"]
    ].drop_duplicates(subset=["authority_code", "ward_code"])
    rows = []
    for auth, grp in ward.groupby("authority_code", dropna=False):
        g = grp[grp["turnout_pct"].notna()].copy()
        if g.empty:
            rows.append({"authority_code": auth, "turnout_pct_year": np.nan})
            continue
        w = g["electorate"].notna() & (g["electorate"] > 0)
        if w.mean() >= 0.5 and g.loc[w, "electorate"].sum() > 0:
            t = (g.loc[w, "turnout_pct"] * g.loc[w, "electorate"]).sum() / g.loc[w, "electorate"].sum()
        else:
            t = g["turnout_pct"].mean()
        rows.append({"authority_code": auth, "turnout_pct_year": float(t)})
    return pd.DataFrame(rows)


def _borough_fi(clean: pd.DataFrame, year: int) -> pd.DataFrame:
    df = clean[clean["election_year"] == year].copy()
    grouped = (
        df.groupby(["authority_code", "party_standardised"], dropna=False)["votes"]
        .sum()
        .reset_index()
    )
    rows = []
    for auth, grp in grouped.groupby("authority_code", dropna=False):
        total_votes = grp["votes"].sum()
        if pd.isna(total_votes) or total_votes <= 0:
            rows.append({"authority_code": auth, "fi_value": np.nan, "n_parties": 0})
            continue
        shares = {
            str(r["party_standardised"]): (float(r["votes"]) / float(total_votes) * 100.0)
            for _, r in grp.iterrows()
            if pd.notna(r["votes"]) and r["votes"] > 0
        }
        if not shares:
            rows.append({"authority_code": auth, "fi_value": np.nan, "n_parties": 0})
            continue
        rows.append(
            {
                "authority_code": auth,
                "fi_value": float(_fragmentation_index(shares)),
                "n_parties": int(len(shares)),
            }
        )
    return pd.DataFrame(rows)


def _load_centroids(dim: pd.DataFrame) -> pd.DataFrame:
    path = REPORTS / "authority_centroids.csv"
    if path.exists():
        c = pd.read_csv(path)
        required = {"authority_code", "lat", "lon"}
        if required.issubset(c.columns):
            return c[["authority_code", "lat", "lon"]]
    # Prepare a template for manual fill if absent.
    template = dim[["authority_code", "authority_name"]].copy()
    template["lat"] = np.nan
    template["lon"] = np.nan
    template.to_csv(path, index=False)
    return template[["authority_code", "lat", "lon"]]


def build_tableau_authority_metrics(
    dim: pd.DataFrame, clean: pd.DataFrame, tm: pd.DataFrame, ba: pd.DataFrame
) -> pd.DataFrame:
    tm_b = tm[tm["computation_level"] == "borough"].copy()
    ba_b = ba[ba["computation_level"] == "borough"].copy()

    fi_2018 = _borough_fi(clean, 2018).rename(columns={"fi_value": "fi_2018_calc", "n_parties": "n_parties_2018"})
    fi_2022 = _borough_fi(clean, 2022).rename(columns={"fi_value": "fi_2022_calc", "n_parties": "n_parties_2022"})

    start_year_by_auth = (
        clean[clean["election_year"].isin([2014, 2015, 2016])]
        .groupby("authority_code")["election_year"]
        .max()
        .reset_index()
        .rename(columns={"election_year": "fi_start_year"})
    )
    fi_start_rows = []
    for _, r in start_year_by_auth.iterrows():
        auth = r["authority_code"]
        year = int(r["fi_start_year"])
        fi = _borough_fi(clean[clean["authority_code"] == auth], year)
        val = fi["fi_value"].iloc[0] if not fi.empty else np.nan
        fi_start_rows.append({"authority_code": auth, "fi_start_year": year, "fi_start": val})
    fi_start = pd.DataFrame(fi_start_rows)

    turn_start_rows = []
    for _, r in start_year_by_auth.iterrows():
        auth = r["authority_code"]
        year = int(r["fi_start_year"])
        t = _borough_turnout(clean[clean["authority_code"] == auth], year)
        val = t["turnout_pct_year"].iloc[0] if not t.empty else np.nan
        turn_start_rows.append({"authority_code": auth, "turnout_start_year": year, "turnout_start": val})
    turn_start = pd.DataFrame(turn_start_rows)
    turn_2018 = _borough_turnout(clean, 2018).rename(columns={"turnout_pct_year": "turnout_2018_calc"})
    turn_2022 = _borough_turnout(clean, 2022).rename(columns={"turnout_pct_year": "turnout_2022_calc"})

    base = dim.merge(fi_start, on="authority_code", how="left")
    base = base.merge(fi_2018[["authority_code", "fi_2018_calc"]], on="authority_code", how="left")
    base = base.merge(fi_2022[["authority_code", "fi_2022_calc"]], on="authority_code", how="left")
    base = base.merge(turn_start, on="authority_code", how="left")
    base = base.merge(turn_2018, on="authority_code", how="left")
    base = base.merge(turn_2022, on="authority_code", how="left")
    base = base.merge(tm_b[["authority_code", "volatility_score", "swing_concentration", "turnout_delta"]], on="authority_code", how="left")
    base = base.rename(
        columns={
            "volatility_score": "vol_2014_2018",
            "swing_concentration": "sc_2014_2018",
            "turnout_delta": "turnout_delta_2014_2018",
        }
    )
    base = base.merge(ba_b[["authority_code", "volatility_score", "swing_concentration", "turnout_delta"]], on="authority_code", how="left")
    base = base.rename(
        columns={
            "volatility_score": "vol_2018_2022",
            "swing_concentration": "sc_2018_2022",
            "turnout_delta": "turnout_delta_2018_2022",
        }
    )
    base["vol_change"] = base["vol_2018_2022"] - base["vol_2014_2018"]

    rows = []
    for _, r in base.iterrows():
        common = {
            "authority_code": r["authority_code"],
            "authority_name": r["authority_name"],
            "tier": r["tier"],
            "tier_label": _tier_label(r["tier"]),
            "region": r["region"],
            "election_active_2026": r["election_active_2026"],
            "all_out_2026": r["all_out_2026"],
            "vol_change": r["vol_change"],
        }
        rows.append(
            {
                **common,
                "window": "2014→2018",
                "fi_start": r["fi_start"],
                "fi_end": r["fi_2018_calc"],
                "delta_fi": (r["fi_2018_calc"] - r["fi_start"]) if pd.notna(r["fi_2018_calc"]) and pd.notna(r["fi_start"]) else np.nan,
                "volatility_score": r["vol_2014_2018"],
                "turnout_start": r["turnout_start"],
                "turnout_end": r["turnout_2018_calc"],
                "turnout_delta": r["turnout_delta_2014_2018"],
                "swing_concentration": r["sc_2014_2018"],
                "metric_available": bool(pd.notna(r["vol_2014_2018"])),
            }
        )
        rows.append(
            {
                **common,
                "window": "2018→2022",
                "fi_start": r["fi_2018_calc"],
                "fi_end": r["fi_2022_calc"],
                "delta_fi": (r["fi_2022_calc"] - r["fi_2018_calc"]) if pd.notna(r["fi_2022_calc"]) and pd.notna(r["fi_2018_calc"]) else np.nan,
                "volatility_score": r["vol_2018_2022"],
                "turnout_start": r["turnout_2018_calc"],
                "turnout_end": r["turnout_2022_calc"],
                "turnout_delta": r["turnout_delta_2018_2022"],
                "swing_concentration": r["sc_2018_2022"],
                "metric_available": bool(pd.notna(r["vol_2018_2022"])),
            }
        )
    out = pd.DataFrame(rows)
    out = out[out["authority_code"] != CITY_OF_LONDON].copy()
    out["vol_rank_in_tier"] = (
        out.groupby(["window", "tier"])["volatility_score"]
        .rank(method="min", ascending=False)
    )
    # Historical-only classification is scope-based (2026 election status), not metric availability.
    # Rotherham is historical-only even though it has null comparable metrics in 2018→2022.
    out["display_group"] = np.where(
        out["election_active_2026"] == False,
        "Historical only (no 2026 election)",
        out["tier_label"],
    )
    out["vol_quartile"] = (
        out.groupby("window")["volatility_score"]
        .transform(lambda s: pd.qcut(s.rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"]))
    )
    centroids = _load_centroids(dim[dim["authority_code"] != CITY_OF_LONDON].copy())
    out = out.merge(centroids, on="authority_code", how="left")
    return out


def build_tableau_party_swings(
    dim: pd.DataFrame, clean: pd.DataFrame, psb: pd.DataFrame, shock: pd.DataFrame
) -> pd.DataFrame:
    df = psb[psb["computation_level"] == "borough"].copy()
    df = df.merge(dim[["authority_code", "authority_name", "tier", "region"]], on="authority_code", how="left")
    df["tier_label"] = df["tier"].map(_tier_label)
    df = df[df["authority_code"] != CITY_OF_LONDON].copy()

    lookup = (
        clean[["party_standardised", "party_group"]]
        .dropna()
        .drop_duplicates()
        .groupby("party_standardised", as_index=False)["party_group"]
        .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else s.iloc[0])
    )
    df = df.merge(lookup, on="party_standardised", how="left")

    challengers = shock[shock["scenario_id"] == "S1"][["authority_code", "challenger_party"]].drop_duplicates()
    df = df.merge(challengers, on="authority_code", how="left")
    df["is_challenger"] = df["party_standardised"] == df["challenger_party"]
    df["swing_abs_rank"] = (
        df.groupby("authority_code")["swing_pp"]
        .transform(lambda s: s.abs().rank(method="min", ascending=False))
    )
    df["party_label_norm"] = df["party_standardised"].map(_normalize_party_label)
    df["party_colour_hex"] = df["party_label_norm"].map(_party_color)
    return df[
        [
            "authority_code",
            "authority_name",
            "tier",
            "tier_label",
            "region",
            "party_standardised",
            "party_group",
            "vote_share_2018",
            "vote_share_2022",
            "swing_pp",
            "is_challenger",
            "swing_abs_rank",
            "party_label_norm",
            "party_colour_hex",
        ]
    ]


def build_tableau_fi_timeseries(dim: pd.DataFrame, clean: pd.DataFrame) -> pd.DataFrame:
    target_years = [2014, 2015, 2016, 2018, 2022]
    clean = clean[clean["election_year"].isin(target_years)].copy()
    clean = clean[clean["authority_code"] != CITY_OF_LONDON].copy()

    rows = []
    for (auth, year), grp in clean.groupby(["authority_code", "election_year"], dropna=False):
        votes = grp.groupby("party_standardised", dropna=False)["votes"].sum()
        total = votes.sum()
        if pd.isna(total) or total <= 0:
            fi = np.nan
            n_parties = 0
        else:
            shares = {str(k): float(v) / float(total) * 100.0 for k, v in votes.items() if pd.notna(v) and v > 0}
            fi = float(_fragmentation_index(shares)) if shares else np.nan
            n_parties = len(shares)
        wards = grp[["ward_code", "turnout_pct", "electorate"]].drop_duplicates(subset=["ward_code"])
        wards = wards[wards["turnout_pct"].notna()]
        if wards.empty:
            turnout = np.nan
        else:
            w = wards["electorate"].notna() & (wards["electorate"] > 0)
            if w.mean() >= 0.5 and wards.loc[w, "electorate"].sum() > 0:
                turnout = float((wards.loc[w, "turnout_pct"] * wards.loc[w, "electorate"]).sum() / wards.loc[w, "electorate"].sum())
            else:
                turnout = float(wards["turnout_pct"].mean())
        rows.append(
            {
                "authority_code": auth,
                "election_year": int(year),
                "fi_value": fi,
                "n_parties": n_parties,
                "turnout_pct": turnout,
                "n_wards_observed": int(grp["ward_code"].nunique()),
            }
        )
    out = pd.DataFrame(rows).merge(
        dim[["authority_code", "authority_name", "tier", "region"]],
        on="authority_code",
        how="left",
    )
    out["tier_label"] = out["tier"].map(_tier_label)

    max_wards = out.groupby("authority_code")["n_wards_observed"].max().rename("max_wards")
    out = out.merge(max_wards, on="authority_code", how="left")
    out["is_whole_council"] = out["n_wards_observed"] >= (0.9 * out["max_wards"])
    out = out.drop(columns=["max_wards"])
    return out[
        [
            "authority_code",
            "authority_name",
            "tier",
            "tier_label",
            "region",
            "election_year",
            "fi_value",
            "n_parties",
            "turnout_pct",
            "is_whole_council",
            "n_wards_observed",
        ]
    ]


def build_volatility_distribution(authority_metrics: pd.DataFrame) -> pd.DataFrame:
    df = authority_metrics[["tier_label", "window", "volatility_score"]].dropna().copy()
    if df.empty:
        return pd.DataFrame(columns=["tier_label", "window", "vol_bin_midpoint", "count", "pct_of_tier"])
    df["vol_bin_midpoint"] = np.floor(df["volatility_score"]).astype(float) + 0.5
    out = (
        df.groupby(["tier_label", "window", "vol_bin_midpoint"], dropna=False)
        .size()
        .reset_index(name="count")
    )
    totals = out.groupby(["tier_label", "window"])["count"].transform("sum")
    out["pct_of_tier"] = out["count"] / totals * 100
    return out


def build_tableau_kpis(authority_metrics: pd.DataFrame) -> pd.DataFrame:
    base = authority_metrics.copy()
    train = base[base["window"] == "2014→2018"].copy()
    back = base[base["window"] == "2018→2022"].copy()

    # By construction authority_metrics excludes City of London.
    n_scope = int(back["authority_code"].nunique())
    comparable_fi = back["fi_start"].notna() & back["fi_end"].notna()
    n_comparable = int(back.loc[comparable_fi, "authority_code"].nunique())
    n_fi_increased = int((back.loc[comparable_fi, "delta_fi"] > 0).sum())

    pearson_subset = back[
        back["turnout_delta"].notna() & back["volatility_score"].notna()
    ].copy()
    pearson_n = int(len(pearson_subset))
    pearson_r, pearson_p = _pearson_with_p(
        pearson_subset["turnout_delta"], pearson_subset["volatility_score"]
    )
    active_subset = back[
        (back["election_active_2026"] == True)
        & back["turnout_delta"].notna()
        & back["volatility_score"].notna()
    ].copy()
    pearson_active_n = int(len(active_subset))
    pearson_active_r, pearson_active_p = _pearson_with_p(
        active_subset["turnout_delta"], active_subset["volatility_score"]
    )

    kpi = {
        "median_vol_2014_2018": float(train["volatility_score"].median()),
        "median_vol_2018_2022": float(back["volatility_score"].median()),
        "median_delta_fi_2014_2018": float(train["delta_fi"].median()),
        "median_delta_fi_2018_2022": float(back["delta_fi"].median()),
        "n_fi_increased": n_fi_increased,
        "n_comparable": n_comparable,
        "n_scope": n_scope,
        "n_all_with_metrics": int(back["volatility_score"].notna().sum()),
        "n_active_2026": int(back.loc[back["election_active_2026"] == True, "authority_code"].nunique()),
        "n_historical_only_2026": int(back.loc[back["election_active_2026"] == False, "authority_code"].nunique()),
        "n_metro_active": int(back.loc[back["tier"] == 1, "authority_code"].nunique()),
        "n_london_active": int(back.loc[back["tier"] == 2, "authority_code"].nunique()),
        "n_wy_active": int(back.loc[back["tier"] == 3, "authority_code"].nunique()),
        "pearson_r_2018_2022": float(round(pearson_r, 4)) if pd.notna(pearson_r) else np.nan,
        "pearson_p_2018_2022": float(round(pearson_p, 4)) if pd.notna(pearson_p) else np.nan,
        "pearson_n": pearson_n,
        "pearson_active_r_2018_2022": float(round(pearson_active_r, 4)) if pd.notna(pearson_active_r) else np.nan,
        "pearson_active_p_2018_2022": float(round(pearson_active_p, 4)) if pd.notna(pearson_active_p) else np.nan,
        "pearson_active_n": pearson_active_n,
        "kpi_pearson_label": (
            f"Pearson r = {pearson_r:.2f}  (n = {pearson_n}, p = {pearson_p:.2f})"
            if pd.notna(pearson_r) and pd.notna(pearson_p)
            else f"Pearson r = {pearson_r:.2f}  (n = {pearson_n})"
            if pd.notna(pearson_r)
            else "Pearson r unavailable"
        ),
        "kpi_pearson_subset": (
            f"Active-only sub-scope (n = {pearson_active_n}): r = {pearson_active_r:.2f}, p = {pearson_active_p:.2f}. Both scopes are statistically null."
            if pd.notna(pearson_active_r) and pd.notna(pearson_active_p)
            else f"Active-only sub-scope (n = {pearson_active_n}): r = {pearson_active_r:.2f}."
            if pd.notna(pearson_active_r)
            else "Active-only sub-scope unavailable."
        ),
        "pearson_subset_note": (
            "window=2018→2022; City of London excluded; turnout_delta and volatility_score non-null only"
        ),
    }
    return pd.DataFrame([kpi])


def main() -> None:
    clean = pd.read_csv(PROCESSED / "clean_election_results.csv", low_memory=False)
    tm = pd.read_csv(PROCESSED / "training_metrics.csv")
    ba = pd.read_csv(PROCESSED / "backtest_actuals_2022.csv")
    psb = pd.read_csv(PROCESSED / "party_swings_backtest.csv")
    dim = pd.read_csv(PROCESSED / "authority_dimension.csv")
    shock = pd.read_csv(PROCESSED / "shock_metrics.csv")

    authority_metrics = build_tableau_authority_metrics(dim, clean, tm, ba)
    party_swings = build_tableau_party_swings(dim, clean, psb, shock)
    fi_series = build_tableau_fi_timeseries(dim, clean)
    vol_dist = build_volatility_distribution(authority_metrics)
    kpis = build_tableau_kpis(authority_metrics)

    authority_metrics.to_csv(REPORTS / "tableau_authority_metrics.csv", index=False)
    party_swings.to_csv(REPORTS / "tableau_party_swings.csv", index=False)
    fi_series.to_csv(REPORTS / "tableau_fi_timeseries.csv", index=False)
    vol_dist.to_csv(REPORTS / "tableau_volatility_distribution.csv", index=False)
    kpis.to_csv(REPORTS / "tableau_kpis.csv", index=False)

    print(f"Wrote {REPORTS / 'tableau_authority_metrics.csv'} ({len(authority_metrics)} rows)")
    print(f"Wrote {REPORTS / 'tableau_party_swings.csv'} ({len(party_swings)} rows)")
    print(f"Wrote {REPORTS / 'tableau_fi_timeseries.csv'} ({len(fi_series)} rows)")
    print(f"Wrote {REPORTS / 'tableau_volatility_distribution.csv'} ({len(vol_dist)} rows)")
    print(f"Wrote {REPORTS / 'tableau_kpis.csv'} ({len(kpis)} rows)")
    print(f"Centroid file: {REPORTS / 'authority_centroids.csv'}")


if __name__ == "__main__":
    main()
