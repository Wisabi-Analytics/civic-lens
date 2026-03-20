"""Tests validating Phase 8 QA outputs."""
import os

import pandas as pd
import pytest

QA_REPORT = "data/processed/qa_report.csv"
CSV = "data/processed/clean_election_results.csv"


@pytest.fixture(scope="module")
def qa():
    return pd.read_csv(QA_REPORT)


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(CSV, low_memory=False)


def test_qa_report_exists(qa):
    assert len(qa) > 0


def test_no_hard_failures(qa):
    failures = qa[qa["status"] == "FAIL"]
    assert len(failures) == 0, (
        f"{len(failures)} hard QA failures:\n"
        + failures[["check_id", "description", "n_affected"]].to_string()
    )


def test_scope_lock_trigger_not_breached(qa):
    trigger = qa[qa["check_id"] == "T01"]
    assert len(trigger) == 1
    assert trigger.iloc[0]["status"] != "FAIL", \
        f"Scope-lock trigger breached: {trigger.iloc[0]['n_affected']:,} failing rows"


def test_vote_share_derivation_correct(df):
    derivable = df[
        df["votes"].notna() &
        df["total_valid_votes"].notna() &
        df["vote_share"].notna() &
        (df["analysis_level"] != "descriptive_only")
    ].copy()
    diff = (derivable["vote_share"] -
            derivable["votes"] / derivable["total_valid_votes"] * 100).abs()
    bad = (diff > 0.01).sum()
    assert bad == 0, f"{bad} rows with vote_share != votes/total_valid_votes"


def test_no_negative_votes(df):
    bad = (df["votes"] < 0).sum()
    assert bad == 0


def test_turnout_over_100_always_flagged(df):
    over_100 = df[df["turnout_pct"].notna() & (df["turnout_pct"] > 100)]
    unflagged = over_100[~over_100["notes"].str.contains("turnout_over_100", na=False)]
    assert len(unflagged) == 0, \
        f"{len(unflagged)} rows with turnout_pct > 100 not flagged in notes"


def test_seats_won_consistent_with_elected(df):
    bad = ((df["elected"] == True) & (df["seats_won"] != 1)).sum() + \
          ((df["elected"] == False) & (df["seats_won"] != 0)).sum()
    assert bad == 0, f"{bad} rows where seats_won doesn't match elected"


def test_no_active_duplicates(df):
    active = df[df["analysis_level"].isin(["ward", "borough_fallback"])]
    key = ["election_year", "authority_code", "ward_code",
           "party_standardised", "candidate_name"]
    dupes = active[active.duplicated(subset=key, keep=False)]
    assert len(dupes) == 0, f"{len(dupes)} duplicate active rows"


def test_conflict_log_columns(tmp_path):
    path = "data/processed/phase8_conflict_log.csv"
    if os.path.exists(path):
        log = pd.read_csv(path)
        required = {"authority_code", "ward_name_clean", "party_standardised",
                    "votes", "dcl_votes", "pct_diff"}
        assert required.issubset(set(log.columns))


def test_electorate_null_rates_within_ceiling(df):
    ceilings = {2014: 0.10, 2015: 0.12, 2016: 0.12, 2018: 0.12, 2022: 0.10}
    for yr, ceiling in ceilings.items():
        sub = df[df["election_year"] == yr]
        rate = sub["electorate"].isna().mean()
        assert rate <= ceiling, \
            f"Year {yr}: electorate null rate {rate:.1%} exceeds ceiling {ceiling:.0%}"
