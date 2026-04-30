from __future__ import annotations

from pathlib import Path
from typing import Dict

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


def _load_lad_lookup(path: Path, ward_col: str, lad_col: str) -> Dict[str, str]:
    df = pd.read_parquet(path, columns=[ward_col, lad_col])
    df[ward_col] = df[ward_col].astype('string').str.strip()
    df[lad_col] = df[lad_col].astype('string')
    return df.set_index(ward_col)[lad_col].to_dict()


def _filter_scope(df: pd.DataFrame) -> pd.DataFrame:
    wl_18 = _load_lad_lookup(
        Path('data/interim/ward_lad_dec2018.parquet'),
        'WD18CD',
        'LAD18CD',
    )
    wl_22 = _load_lad_lookup(
        Path('data/interim/ward_lad_dec2022.parquet'),
        'WD22CD',
        'LAD22CD',
    )

    df['ward_code'] = df['ward_code'].astype('string').str.strip()
    mask_2022 = df['year'] == 2022
    df['lad_code'] = None
    df.loc[~mask_2022, 'lad_code'] = (
        df.loc[~mask_2022, 'ward_code'].map(wl_18)
    )
    df.loc[mask_2022, 'lad_code'] = (
        df.loc[mask_2022, 'ward_code'].map(wl_22)
    )

    # Fallback for authorities whose retroactive DCLEAPIL ward codes do not
    # appear in current ward lookup vintages: recover LAD from authority name.
    # This is only used when ward-code lookup failed.
    lad_name = pd.read_csv('data/raw/ons/lad_region_lookup_apr2023.csv')[
        ['LAD23CD', 'LAD23NM']
    ].copy()
    name_to_lad = dict(
        zip(
            lad_name['LAD23NM'].astype('string').str.strip().str.lower(),
            lad_name['LAD23CD'].astype('string').str.strip(),
        )
    )
    no_lad = df['lad_code'].isna() & df['council'].notna()
    if no_lad.any():
        fallback_lad = (
            df.loc[no_lad, 'council']
            .astype('string')
            .str.strip()
            .str.lower()
            .map(name_to_lad)
        )
        recovered = int(fallback_lad.notna().sum())
        if recovered > 0:
            print(
                f'INFO: Recovered {recovered} DCLEAPIL rows via council->LAD fallback'
            )
            df.loc[no_lad, 'lad_code'] = fallback_lad

    valid_prefixes = ('E08', 'E09')
    valid = df['lad_code'].str.startswith(valid_prefixes, na=False)
    dropped = (~valid).sum()
    if dropped > 0:
        print(f'INFO: Dropping {dropped} DCLEAPIL rows outside E08/E09 scope')
    df = df[valid].copy()
    df = df.drop(columns=['lad_code'], errors='ignore')
    return df


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

    df['ward_code'] = df['GSS'].astype('string').str.strip()
    df = _filter_scope(df)
    df = df.drop(columns=['GSS'], errors='ignore')

    df['candidate_name'] = (
        df['first_name'].fillna('')
        + ' '
        + df['surname'].fillna('')
    ).str.strip()

    # Deduplicate DCLEAPIL 2018: prefer DC-LEAP rows over DC duplicates
    if 'dataset' in df.columns:
        df_2018 = df[df['year'] == 2018].copy()
        df_other = df[df['year'] != 2018].copy()

        dedup_key = ['year', 'ward_code', 'party_id', 'candidate_name']
        available_key = [col for col in dedup_key if col in df_2018.columns]

        priority = {'DC-LEAP': 0, 'DC': 1, 'LEAP': 2}
        df_2018['_dataset_priority'] = df_2018['dataset'].map(priority).fillna(9)
        df_2018 = df_2018.sort_values('_dataset_priority')
        before = len(df_2018)
        df_2018 = df_2018.drop_duplicates(subset=available_key, keep='first')
        dropped = before - len(df_2018)
        df_2018 = df_2018.drop(columns=['_dataset_priority'])

        if dropped > 0:
            print(
                f'INFO: DCLEAPIL 2018 dedup dropped {dropped} rows superseded by DC-LEAP'
            )
        df = pd.concat([df_other, df_2018], ignore_index=True)
    else:
        print("WARNING: 'dataset' column missing; DCLEAPIL 2018 dedup skipped")

    column_map = {
        'year': 'election_year',
        'council': 'authority_name_raw',
        'ward': 'ward_name_raw',
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
