# Raw Data Audit Summary — Phase 1

## Immediate usability
- **Election history** – `ec/dcleapil_2006_2024.csv` is ready to feed the baseline/backtest pipeline once ward names are mapped via the ONS lookups; the file already carries the GSS ward codes, party IDs, DC identifiers, and tier tags the model needs.
- **Commons Library sheets** – 2022 candidates/wards can slot straight into the calibration chain once the redundant uppercase vs descriptive column pairs are aligned and the party columns in the ward sheet are pivoted; 2025 (“Tier 3”) candidate and ward tabs contain clean longitudinal columns such as `ONS ward code`, `Upper tier authority`, `Votes cast`, `Seats contested`, and the ward-level `Turnout (EC method)`/`Valid vote turnout (HoC method)` measures.
- **Geography references** – the 2018/2022 ward‑to‑LAD CSVs, the May 2022 provisional Excel lookup, and the December 2022 LAD→region CSV all provide the code/figure references required to assign authorities, regions, and `authority_type` tags to every election row; the 2021 and 2022 BGC shapefiles supplement visualisations once they are joined to the lookup tables.

## Special parsing requirements
- **Excel headers** – every Commons Library workbook has text in row 1 (“Local election results by …”) and the true field names begin at row 2, so ingestion scripts must skip row 1 before reading column names. The ward sheets also mix uppercase codes and descriptive labels (e.g., `COUNTYNAME` + `County name`), so de‑duplication or column selection is required.
- **Wide-party ward sheets** – the 2021/2022 ward tabs list tens of party columns (including ad-hoc columns such as `LAB ACCIDENTAL CANDIDATE` and `YORKS`), meaning a reshape (longer party table with party code + votes) is the only practical normalisation step.
- **DCLEAPIL numeric cleanup** – `votes_cast` is stored as comma-delimited strings (e.g., `"1,251"` for Sunderland/Pallion 2018) and `vote_share` values are percentages on a 0–100 scale; about 30.8% of 2018 rows (Manchester 182, Leeds 175, Newcastle upon Tyne 168 missing, etc.) leave `vote_share` blank, so commas must be stripped before casting and missing percentages should be derived as `(votes_cast / turnout_valid) * 100`.
- **2025 schema shift** – the 2025 workbook uses new headers such as `Ward/ County Electoral District name`, trims party coverage to the top five parties plus `REF/IND/Other`, and drops county codes (only names remain) and vacancy counts; scripts must map these columns to the existing schema before joining to earlier years.
- **Boundary/geography joins** – the shapefiles lack authority-type metadata (especially the 2021 file, which holds only ward codes and lat/long), so every spatial join needs to go through the ONS ward→LAD lookups before a final `authority_type` mapping via `lad_region_lookup_dec2022.csv`.
- **IMD workbook** – the English Indices data is spread across separate sheets (IMD, Income, Employment, etc.) that each repeat the same LAD code/ name columns; ingestors must pick the relevant sheet (or unwind them all) and merge internally because there is no single sheet containing all domains.

## Known schema mismatches
- **2021 vs 2022 column naming** – 2021 sheets use descriptive names (`County code`, `Ward/ED code`), while 2022 sheets duplicate the county/local authority pair in uppercase and descriptive forms (`COUNTYCODE`/`County code`, `COUNTYNAME`/`County name`, etc.); the ward code column remains `Ward code` in both, so focus deduplication on the county-level duplicates.
- **2025 schema drift** – the 2025 sheets rename fields (`EC ward code`, `Seats`, `Ballots` instead of `Vacancies`/`Electorate`), reduce the party list, and split candidate names into `First names`/`Last names`; pipelines expecting the 2018/2022 structure must remap field names and backfill any missing identifiers.
- **Ward lookup vintages** – the December 2018 and December 2022 CSVs use different field names (`WD18*` vs `WD22*`), so code that maps wards to authorities must be parameterised by vintage. The May 2022 Excel file is labelled provisional but duplicates the 2022 codes, so treat it as a 2022 backup rather than a new schema.
- **Boundary shapefile vintage names** – the 2021 shapefile is labelled `dec2021` even though we use it as a proxy for 2018 geography, so any visual logic that references the file must document that it is a near‑approximation rather than an exact 2018 boundary.

## Known field gaps
- **Lacking 2025 metro/London returns** – Commons 2025 data only covers 23 county/unitary councils; Tier 1 (metro) and Tier 2 (London) 2025 results must continue to come from `DCLEAPIL` (see inventory note), meaning Tier 3 is the only tier with a full Commons 2025 workbook.
- **Vote_share gaps in 2018** – 30.8% of the 2018 DCLEAPIL rows lack `vote_share`, with Manchester (182 rows), Leeds (175), and Newcastle upon Tyne (168) among the most affected Tier 1 authorities; the loader needs to compute these percentages from `(votes_cast / turnout_valid) * 100` once the numeric cleanup above is complete.
- **No ward-level IMD** – IMD 2019 data is only at the Local Authority District level, lacks a decile column, and still uses 2019 LAD codes, so the pipeline must derive deciles from the rank fields (e.g., `IMD - Rank of average rank`) via `pd.qcut` before rolling them down to wards through the lookup tables.
- **Shapefile authority attributes** – the 2021 shapefile lacks any LAD code, so ward→LAD joins for visualisations must rely on the 2018 lookup file; the 2022 shapefile adds `LAD22` fields but still needs the LAD→region CSV to infer `authority_type`.

## Known election-cycle caveats
- **2025 Tier gaps** – metropolitan and London borough councils held no local elections in 2025, so no ward-level data exists for Tier 1 or Tier 2 in the Commons 2025 workbook; DCLEAPIL remains the source for their 2018 baseline data, but the Tier 3 2025 dataset that underpins the 2022→2025 backtest (and therefore Tier 3 uncertainty) is still to be acquired.
- **Tier-specific uncertainty** – because only the Yorkshire Tier 3 councils produce a complete 2025 dataset, their forecast errors drive the uncertainty bands for all tiers (as documented in `docs/METHODOLOGY.md`). The audit above confirms the absence of direct Tier 1/2 2025 data rather than an oversight.
- **2021 pandemic election** – the 2021 Commons dataset is structurally different and subject to pandemic turnout distortion, so it remains excluded from calibrations and is retained solely for completeness checks (see DECISIONS_LOG). Don’t merge it into the baseline without explicit filtering.

## Deliverables
- `data/raw/data_inventory.csv` (this file catalogues every raw file, its shape, keys, and known issues).
- `docs/RAW_DATA_AUDIT_SUMMARY.md` (current document, which records usability, parsing notes, schema gaps, and election caveats).

**Phase 1 exit criteria:** all raw files listed above have been inspected and documented; no cleaning has been attempted yet.
