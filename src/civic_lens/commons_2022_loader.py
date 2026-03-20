from __future__ import annotations

from pathlib import Path
import pandas as pd

RAW_PATH = Path('data/raw/ec/local_elections_2022.xlsx')
INTERIM_PATH = Path('data/interim')
INTERIM_PATH.mkdir(exist_ok=True)

CANDIDATE_EXPECTED = 18482
WARD_EXPECTED = 3536
NON_PARTY_COLS = {
    'COUNTYNAME', 'County code', 'County name',
    'Local authority code', 'Local authority name',
    'Ward code', 'Ward name',
    'Vacancies', 'Type', 'Electorate', 'Turnout (%)',
    'Total votes'
}


def _load_sheet(name: str) -> pd.DataFrame:
    return pd.read_excel(RAW_PATH, sheet_name=name, header=1)


def load_commons_2022() -> tuple[pd.DataFrame, pd.DataFrame]:
    df_cand = _load_sheet('Candidates-results')
    df_ward = _load_sheet('Wards-results')

    assert abs(len(df_cand) - CANDIDATE_EXPECTED) <= 20
    assert abs(len(df_ward) - WARD_EXPECTED) <= 20

    df_cand = df_cand.drop(columns=['COUNTYCODE', 'COUNTYNAME'], errors='ignore')
    df_cand = df_cand.rename(columns={
        'Local authority code': 'authority_code',
        'Local authority name': 'authority_name_raw',
        'Ward code': 'ward_code',
        'Ward name': 'ward_name_raw',
        'Type': 'authority_type_raw',
        'Vacancies': 'seats_contested',
        'Candidate name': 'candidate_name',
        'Incumbent': 'incumbent',
        'Votes': 'votes',
        'Elected': 'elected_raw',
        'Party ID': 'party_id',
        'Party name': 'party_raw',
        'Party group': 'party_group_raw',
        'Total valid votes': 'total_valid_votes',
        'Candidate number': 'candidate_number',
    })

    df_cand['vote_share'] = df_cand['votes'] / df_cand['total_valid_votes'] * 100
    df_cand['election_year'] = 2022
    df_cand['election_date'] = pd.to_datetime('2022-05-05')
    df_cand['source_dataset'] = 'commons_2022'
    df_cand['data_source_era'] = 'dc_leap'
    df_cand['ward_code_vintage'] = 'WD22CD'

    party_cols = [c for c in df_ward.columns if c not in NON_PARTY_COLS]
    df_ward_long = df_ward.melt(
        id_vars=[
            'Local authority code', 'Local authority name',
            'Ward code', 'Ward name', 'Type', 'Vacancies',
            'Electorate', 'Turnout (%)'
        ],
        value_vars=party_cols,
        var_name='party_code',
        value_name='party_ward_votes'
    )
    df_ward_long = df_ward_long[df_ward_long['party_ward_votes'].notna()]
    df_ward_long = df_ward_long[df_ward_long['party_ward_votes'] > 0]

    df_ward_long = df_ward_long.rename(columns={
        'Local authority code': 'authority_code',
        'Local authority name': 'authority_name_raw',
        'Ward code': 'ward_code',
        'Ward name': 'ward_name_raw',
        'Type': 'authority_type_raw',
        'Vacancies': 'seats_contested',
        'Electorate': 'electorate',
        'Turnout (%)': 'turnout_pct',
    })
    df_ward_long['election_year'] = 2022
    df_ward_long['election_date'] = pd.to_datetime('2022-05-05')
    df_ward_long['source_dataset'] = 'commons_2022'
    df_ward_long['data_source_era'] = 'dc_leap'
    df_ward_long['ward_code_vintage'] = 'WD22CD'

    df_cand.to_parquet(INTERIM_PATH / 'commons_2022_candidates.parquet', index=False)
    df_ward_long.to_parquet(INTERIM_PATH / 'commons_2022_wards.parquet', index=False)
    return df_cand, df_ward_long


if __name__ == '__main__':
    load_commons_2022()
