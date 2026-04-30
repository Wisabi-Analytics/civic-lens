import sys

sys.path.insert(0, "src")

from civic_lens.party_normalise import (
    challenger_party_family,
    display_party_label,
    metric_party_family,
)


def test_labour_variants_map_to_lab_for_metrics():
    assert metric_party_family("Labour Party", "Major") == "LAB"
    assert metric_party_family("Labour And Cooperative Party", "Major") == "LAB"
    assert metric_party_family("Labour and Co-operative Party", "Major") == "LAB"


def test_reform_ukip_variants_map_to_reform_for_metrics():
    assert metric_party_family("Reform Uk", "Minor") == "REFORM"
    assert metric_party_family("UK Independence Party (Ukip)", "Minor") == "REFORM"
    assert metric_party_family("Brexit Party", "Minor") == "REFORM"


def test_metric_party_family_preserves_distinct_local_parties():
    assert (
        metric_party_family("Garforth And Swillington Independents Party", "ILP")
        == "Garforth And Swillington Independents Party"
    )
    assert metric_party_family("Independent Labour Group", "Minor") == "Independent Labour Group"
    assert metric_party_family("Some Local Residents Group", "Minor") == "Some Local Residents Group"


def test_challenger_party_family_pools_independent_and_ilp_by_group():
    assert challenger_party_family("Jane Smith", "Independent") == "IND"
    assert challenger_party_family("Garforth And Swillington Independents Party", "ILP") == "ILP"
    assert challenger_party_family("Rainham Independent Residents Association", "ILP") == "ILP"


def test_challenger_party_family_is_case_and_whitespace_robust():
    assert challenger_party_family("Local Candidate", " independent ") == "IND"
    assert challenger_party_family("Local Party", " ilp ") == "ILP"


def test_unknown_minor_party_preserved_for_metric_and_challenger():
    assert metric_party_family("Shared Ground", "Minor") == "Shared Ground"
    assert challenger_party_family("Shared Ground", "Minor") == "Shared Ground"


def test_display_party_label_is_broad_and_not_for_metrics():
    assert display_party_label("Garforth And Swillington Independents Party", "ILP") == "IND"
    assert display_party_label("Independent Labour Group", "Minor") == "IND"
    assert metric_party_family("Independent Labour Group", "Minor") == "Independent Labour Group"
