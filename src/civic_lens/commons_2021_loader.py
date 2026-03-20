from __future__ import annotations

from pathlib import Path
import pandas as pd

RAW_PATH = Path('data/raw/ec/local_elections_2021.xlsx')
INTERIM_PATH = Path('data/interim')
INTERIM_PATH.mkdir(exist_ok=True)

NON_PARTY_COLS = {
    'COUNTYNAME', 'County code', 'County name',
    'Local authority code', 'Local authority name',
    'Ward/ED code', 'Ward/ED name',
    'Vacancies', 'Type', 'Electorate', 'Turnout (%)',
}
ACCIDENTAL_COLS = {'GREEN ACCIDENTAL CANDIDATE', 'LAB ACCIDENTAL CANDIDATE'}


def _load_sheet(name: str) -> pd.DataFrame:
    return pd.read_excel(RAW_PATH, sheet_name=name, header=1)


def load_commons_2021() -> tuple[pd.DataFrame, pd.DataFrame]:
    df_cand = _load_sheet('Candidates-results')
    df_ward = _load_sheet('Wards-results')

    df_cand = df_cand.rename(columns={'Inumbent': 'incumbent'})
    df_cand = df_cand.rename(columns={
        'Local authority code': 'authority_code',
        'Local authority name': 'authority_name_raw',
        'Ward/ED code': 'ward_code',
        'Ward/ED name': 'ward_name_raw',
        'Type': 'authority_type_raw',
        'Vacancies': 'seats_contested',
        'Candidate name': 'candidate_name',
        'Votes': 'votes',
        'Elected': 'elected_raw',
        'Party ID': 'party_id',
        'Party name': 'party_raw',
        'Party group': 'party_group_raw',
        'Total valid votes': 'total_valid_votes',
    })
    df_cand['vote_share'] = df_cand['votes'] / df_cand['total_valid_votes'] * 100
    df_cand['election_year'] = 2021
    df_cand['election_date'] = pd.to_datetime('2021-05-06')
    df_cand['source_dataset'] = 'commons_2021'
    df_cand['pipeline_status'] = 'COMPLETENESS_ONLY_NOT_IN_CALIBRATION_CHAIN'
    df_cand['data_source_era'] = 'dc_leap'
    df_cand['ward_code_vintage'] = 'WD22CD'

    df_ward = df_ward.drop(columns=[c for c in ACCIDENTAL_COLS if c in df_ward.columns])
    party_cols = [c for c in df_ward.columns if c not in NON_PARTY_COLS]
    df_ward_long = df_ward.melt(
        id_vars=[
            'Local authority code', 'Local authority name',
            'Ward/ED code', 'Ward/ED name', 'Type', 'Vacancies',
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
        'Ward/ED code': 'ward_code',
        'Ward/ED name': 'ward_name_raw',
        'Type': 'authority_type_raw',
        'Vacancies': 'seats_contested',
        'Electorate': 'electorate',
        'Turnout (%)': 'turnout_pct',
    })
    df_ward_long['election_year'] = 2021
    df_ward_long['election_date'] = pd.to_datetime('2021-05-06')
    df_ward_long['source_dataset'] = 'commons_2021'
    df_ward_long['pipeline_status'] = 'COMPLETENESS_ONLY_NOT_IN_CALIBRATION_CHAIN'
    df_ward_long['data_source_era'] = 'dc_leap'
    df_ward_long['ward_code_vintage'] = 'WD22CD'

    df_cand.to_parquet(INTERIM_PATH / 'commons_2021_candidates.parquet', index=False)
    df_ward_long.to_parquet(INTERIM_PATH / 'commons_2021_wards.parquet', index=False)
    return df_cand, df_ward_long


if __name__ == '__main__':
    load_commons_2021()
