from pathlib import Path
import pandas as pd

INTERIM = Path('data/interim')


def test_dcleapil_interim_exists():
    path = INTERIM / 'dcleapil_interim.parquet'
    assert path.exists()
    df = pd.read_parquet(path)
    counts = df['election_year'].value_counts()
    for year, expected in [(2014, 17038), (2015, 30729), (2016, 10957), (2018, 17005), (2022, 21932)]:
        assert abs(counts.get(year, 0) - expected) <= 50
    assert df['votes'].dtype.kind in 'iu'
    valid_vote_share = df['vote_share'].dropna()
    assert valid_vote_share.between(0, 100).all()


def test_commons_2022_outputs():
    cand = pd.read_parquet(INTERIM / 'commons_2022_candidates.parquet')
    ward = pd.read_parquet(INTERIM / 'commons_2022_wards.parquet')
    assert abs(len(cand) - 18481) <= 20
    assert len(ward) > 0
    assert 'COUNTYCODE' not in cand.columns
    assert 'COUNTYNAME' not in cand.columns


def test_commons_2021_outputs():
    path = INTERIM / 'commons_2021_candidates.parquet'
    assert path.exists()
    cand = pd.read_parquet(path)
    assert 'pipeline_status' in cand.columns
    assert (cand['pipeline_status'] == 'COMPLETENESS_ONLY_NOT_IN_CALIBRATION_CHAIN').all()
    assert 'Inumbent' not in cand.columns


def test_lookup_files_exist():
    required = [
        'ward_lad_dec2011.parquet', 'ward_lad_dec2016.parquet',
        'ward_lad_dec2018.parquet', 'ward_lad_may2022.parquet',
        'ward_lad_dec2022.parquet', 'lad_region_apr2023.parquet',
        'imd_2019.parquet', 'party_coding.parquet'
    ]
    for filename in required:
        assert (INTERIM / filename).exists(), f'{filename} missing'
