from __future__ import annotations

from pathlib import Path
import pandas as pd

INTERIM_PATH = Path('data/interim')
INTERIM_PATH.mkdir(exist_ok=True)

LOOKUPS = [
    ('data/raw/ons/ward_lad_lookup_dec2011.csv', 'ward_lad_dec2011.parquet', 'WD11CD', 'LAD11CD'),
    ('data/raw/ons/ward_lad_lookup_dec2016.csv', 'ward_lad_dec2016.parquet', 'WD16CD', 'LAD16CD'),
    ('data/raw/ons/ward_lad_lookup_dec2018.csv', 'ward_lad_dec2018.parquet', 'WD18CD', 'LAD18CD'),
    ('data/raw/ons/ward_lad_lookup_may2022.xlsx', 'ward_lad_may2022.parquet', 'WD22CD', 'LAD22CD'),
    ('data/raw/ons/ward_lad_lookup_dec2022.csv', 'ward_lad_dec2022.parquet', 'WD22CD', 'LAD22CD'),
]


def _filter_england(df: pd.DataFrame, ward_col: str) -> pd.DataFrame:
    return df[df[ward_col].astype(str).str.startswith('E')].copy()


def _load_lookup(path: str, ward_col: str, lad_col: str) -> pd.DataFrame:
    if path.endswith('.xlsx'):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
    df = df.drop(columns=[c for c in df.columns if c.lower() in {'fid', 'objectid'}], errors='ignore')
    df = _filter_england(df, ward_col)
    if df[[ward_col, lad_col]].isnull().any(axis=None):
        raise AssertionError(f'Null ward/LAD codes in {path}')
    return df


def load_all_lookups() -> dict[str, pd.DataFrame]:
    results = {}
    for path, outfile, ward_col, lad_col in LOOKUPS:
        df = _load_lookup(path, ward_col, lad_col)
        df.to_parquet(INTERIM_PATH / outfile, index=False)
        results[outfile] = df

    lad_region = pd.read_csv('data/raw/ons/lad_region_lookup_apr2023.csv')
    if len(lad_region) != 296:
        raise AssertionError('LAD-region lookup row count mismatch')
    if lad_region.isnull().any().any():
        raise AssertionError('Nulls found in lad_region_lookup_apr2023.csv')
    lad_region.to_parquet(INTERIM_PATH / 'lad_region_apr2023.parquet', index=False)
    results['lad_region_apr2023.parquet'] = lad_region

    imd = pd.read_excel('data/raw/imd/imd_2019_lad_summary.xlsx', sheet_name='IMD')
    imd.columns = [c.strip() for c in imd.columns]
    imd['imd_decile'] = pd.qcut(imd['IMD - Rank of average score'], 10, labels=range(1, 11)).astype(int)
    if not imd['imd_decile'].between(1, 10).all():
        raise AssertionError('IMD deciles out of range')
    imd.to_parquet(INTERIM_PATH / 'imd_2019.parquet', index=False)
    results['imd_2019.parquet'] = imd

    return results

if __name__ == '__main__':
    load_all_lookups()
