from __future__ import annotations

import re


def _key(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.strip().casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


PARTY_FAMILY_MAP = {
    "labour party": "LAB",
    "labour and cooperative party": "LAB",
    "labour and co operative party": "LAB",
    "co operative party": "LAB",
    "conservative and unionist party": "CON",
    "conservative party": "CON",
    "liberal democrats": "LD",
    "liberal democrat": "LD",
    "green party": "GREEN",
    "green": "GREEN",
    "reform uk": "REFORM",
    "reform uk party": "REFORM",
    "uk independence party ukip": "REFORM",
    "uk independence party": "REFORM",
    "brexit party": "REFORM",
    "yorkshire party": "YORKS",
}


def metric_party_family(party_standardised: object, party_group: object = None) -> str:
    """Party key for FI, VOL, SC, and party-swing metric computation.

    This collapses known ballot-label artifacts while preserving distinct local
    independent parties. Do not use this for chart colors or challenger pooling.
    """
    key = _key(party_standardised)
    if key in PARTY_FAMILY_MAP:
        return PARTY_FAMILY_MAP[key]

    raw = "" if party_standardised is None else str(party_standardised).strip()
    return raw or "UNKNOWN"


def challenger_party_family(party_standardised: object, party_group: object = None) -> str:
    """Party key for challenger identification.

    Challenger logic pools independents and ILPs as required by the frozen
    scenario definition. Metric logic does not.
    """
    group = _key(party_group)
    if group == "independent":
        return "IND"
    if group == "ilp":
        return "ILP"
    return metric_party_family(party_standardised, party_group)


def display_party_label(party_standardised: object, party_group: object = None) -> str:
    """Broad party label for Tableau colors and readable grouped displays."""
    metric_family = metric_party_family(party_standardised, party_group)
    if metric_family in {"LAB", "CON", "LD", "GREEN", "REFORM", "YORKS"}:
        return metric_family

    group = _key(party_group)
    if group in {"independent", "ilp"}:
        return "IND"

    key = _key(party_standardised)
    if key.startswith("ind") or "independent" in key:
        return "IND"
    return "OTHER"
