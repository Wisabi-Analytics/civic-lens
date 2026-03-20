from __future__ import annotations

from pathlib import Path
import pandas as pd

RAW_PATH = Path('data/raw/ec/DCLEAPIL_v1_0_Party_coding.csv')
INTERIM_PATH = Path('data/interim')
INTERIM_PATH.mkdir(exist_ok=True)

MANUAL_PARTY_MAP = {
    'NR_Ind': {'party_standardised': 'IND', 'party_group': 'Independent', 'is_ilp': False},
    'NR_IndLR': {'party_standardised': 'IND', 'party_group': 'Independent', 'is_ilp': False},
    'joint-party:15-64': {'party_standardised': 'IND_LOCAL', 'party_group': 'ILP', 'is_ilp': True},
}


def _normalize_name(name: str) -> str:
    return name.strip().title()


def load_party_coding() -> pd.DataFrame:
    df = pd.read_csv(RAW_PATH)
    df = df.rename(columns=str.strip)

    lookup_rows = []
    for _, row in df.iterrows():
        entry = {
            'party_standardised': _normalize_name(row.get('Party Name', '')),
            'party_group': row.get('Type2', '').strip() or 'Minor',
            'is_ilp': str(row.get('ILP', '')).strip().lower() == 'yes',
        }
        ec_ref1 = row.get('EC_Ref1')
        ec_ref2 = row.get('EC_Ref2')
        if pd.notna(ec_ref1):
            lookup_rows.append({'party_id_key': ec_ref1, **entry})
        if pd.notna(ec_ref2):
            lookup_rows.append({'party_id_key': ec_ref2, **entry})

    manual = [{
        'party_id_key': k,
        **v,
    } for k, v in MANUAL_PARTY_MAP.items()]

    lookup_df = pd.DataFrame(lookup_rows + manual)

    lookup_df = lookup_df.drop_duplicates(subset=['party_id_key'], keep='last')

    lookup_df.to_parquet(INTERIM_PATH / 'party_coding.parquet', index=False)
    return lookup_df

if __name__ == '__main__':
    load_party_coding()
