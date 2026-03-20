from __future__ import annotations

from pathlib import Path
import pandas as pd

RAW_PATH = Path('data/raw/ec/dcleapil_2006_2024.csv')
INTERIM_PATH = Path('data/interim')
INTERIM_PATH.mkdir(exist_ok=True)

INSCOPE_YEARS = {2014, 2015, 2016, 2018, 2022}
EXPECTED_ROWS = {
    2014: 17038,
    2015: 30729,
    2016: 10957,
    2018: 17005,
    2022: 21932,
}


def _era(year: int) -> str:
    return 'leap_only' if year <= 2015 else 'dc_leap'


def _ward_code_vintage(year: int) -> str:
    return 'WD22CD' if year == 2022 else 'WD18CD'


def load_dcleapil() -> pd.DataFrame:
    df = pd.read_csv(RAW_PATH, encoding='utf-8-sig', low_memory=False)

    df = df[df['year'].notna()].copy()
    df['year'] = df['year'].astype(int)
    df = df[df['year'].isin(INSCOPE_YEARS)].copy()
    df = df[df['seats_contested_calc'] != 0].copy()

    for year, expected in EXPECTED_ROWS.items():
        actual = int((df['year'] == year).sum())
        if abs(actual - expected) > 50:
            raise AssertionError(
                f'Year {year}: expected approx {expected} rows, got {actual}'
            )

    df['votes_cast'] = (
        df['votes_cast'].astype(str)
        .str.replace(',', '', regex=False)
        .str.strip()
    )
    df['votes_cast'] = pd.to_numeric(df['votes_cast'], errors='coerce')
    df['turnout_valid'] = pd.to_numeric(df['turnout_valid'], errors='coerce')
    df['electorate'] = pd.to_numeric(df['electorate'], errors='coerce')

    if (df['votes_cast'].dropna() < 0).any():
        raise AssertionError('Negative votes_cast found in DCLEAPIL data')

    df['turnout_pct'] = (
        df['turnout_valid']
        / df['seats_contested_calc']
        / df['electorate']
        * 100
    )

    valid_turnout = df['turnout_pct'].dropna()
    too_high = valid_turnout[valid_turnout > 200]
    if len(too_high) > 0:
        print(
            f'WARNING: {len(too_high)} rows with turnout_pct > 200 after correction'
        )

    df['data_source_era'] = df['year'].map(_era)
    df['source_dataset'] = df['year'].map(lambda y: f'dcleapil_{y}')
    df['ward_code_vintage'] = df['year'].map(_ward_code_vintage)

    df['candidate_name'] = (
        df['first_name'].fillna('')
        + ' '
        + df['surname'].fillna('')
    ).str.strip()

    column_map = {
        'year': 'election_year',
        'council': 'authority_name_raw',
        'ward': 'ward_name_raw',
        'GSS': 'ward_code',
        'party_id': 'party_id',
        'party_name': 'party_raw',
        'votes_cast': 'votes',
        'turnout_valid': 'total_valid_votes',
        'elected': 'elected_raw',
        'seats_contested_calc': 'seats_contested',
        'electorate': 'electorate',
    }

    df = df.rename(columns=column_map)
    df['votes'] = pd.to_numeric(df['votes'], errors='coerce').astype('Int64')
    df['vote_share'] = (
        df['votes'] / df['total_valid_votes'] * 100
    ).clip(0, 100)
    df = df.assign(election_date=pd.to_datetime('2022-05-05'))

    retain = [
        'election_year',
        'election_date',
        'source_dataset',
        'data_source_era',
        'authority_name_raw',
        'ward_name_raw',
        'ward_code',
        'ward_code_vintage',
        'candidate_name',
        'party_raw',
        'party_id',
        'votes',
        'vote_share',
        'total_valid_votes',
        'turnout_pct',
        'seats_contested',
        'electorate',
        'elected_raw',
        'DC_ballot_paper_id',
        'merge_ballot_paper',
        'merge_candidate',
        'DC_person_id',
        'region',
        'tier',
        'dataset',
        'ENP',
    ]

    missing = [c for c in retain if c not in df.columns]
    if missing:
        raise KeyError(f'Missing requested columns: {missing}')

    df = df[retain]
    df.to_parquet(INTERIM_PATH / 'dcleapil_interim.parquet', index=False)
    return df


if __name__ == '__main__':
    load_dcleapil()
