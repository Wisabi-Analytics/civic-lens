# Phase 1 — Raw Data Audit Note

**Date:** 12–20 March 2026  
**Status:** Complete — all 17 sources inspected and documented. All acquisition tasks closed.  
**Auditor:** Max Obi / Wisabi Analytics  
**Files inspected:** 17 of 17  
**Phase 2:** Complete — schema, metrics, and scenarios frozen.

---

## Summary Verdict

All 17 sources are structurally understood. No open acquisition tasks remain. No cleaning has begun. Phase 2 (canonical schema and metric contract) is complete — see `data/processed/DATA_DICTIONARY.md` and `docs/SCENARIO_DEFINITIONS.md`.

The calibration chain runs 2014→2018→2022. No 2025 data is used. Commons Library 2025 is retained for provenance only.

---

## 1. Immediately Usable

### `lad_region_lookup_apr2023.csv`
Clean. England-only (296 rows). Columns `LAD23CD`, `LAD23NM`, `RGN23CD`, `RGN23NM`, zero nulls. All 9 English regions represented. All in-scope metro boroughs, London boroughs, and Yorkshire councils confirmed present.

### `ward_lad_lookup_dec2022.csv`
Clean. 8,483 rows. `WD22CD` and `LAD22CD` fully populated, zero nulls. UK-wide — filter to England. Canonical 2022 ward lookup.

### `ward_lad_lookup_may2022.xlsx`
Identical ward codes to dec2022 CSV. Redundant — retain for provenance, dec2022 CSV is the active lookup.

### `ward_lad_lookup_dec2016.csv`
9,130 rows; 7,463 England rows. `WD16CD`, `WD16NM`, `LAD16CD`, `LAD16NM`, `FID`. Zero nulls. **Role: boundary concordance reference only — not a GSS join key.** DCLEAPIL retroactively assigns modern GSS codes to all election years, so this lookup matches only 60–72% of training year GSS codes. The Dec 2018 lookup (already in project) is the correct GSS join for 2014–2016 DCLEAPIL data. This file confirms which wards existed in 2014–2016 for Phase 7 concordance decisions.

### `ward_lad_lookup_dec2011.csv`
Columns: `WD11CD`, `WD11NM`, `LAD11CD`, `LAD11NM`, `WD22CD`, `WD22NM`, `LAD22CD`, `LAD22NM`. Maps 2011 ward codes to their 2022 equivalents — covers splits and merges across the full window. Covers all in-scope metro/London boroughs and all 5 West Yorkshire councils. Essential for Phase 7 split/merge tracking. **Row counts and merge/split statistics not yet verified from this checkout — validate shape before Phase 7.** Not used as a DCLEAPIL GSS join key.

### `imd_2019_lad_summary.xlsx`
IMD sheet: 317 rows, clean, zero nulls on key fields. All in-scope authorities present. 28 pre-reorganisation district codes (E07xxxxx) entirely out of scope. **No decile column** — derive via `pd.qcut` on `IMD - Rank of average score` (10 bins) in Phase 4 loader. Only the `IMD` sheet needed for Scenario S4; nine additional domain sheets available for future extension.

### `local_elections_2022.xlsx`
18,481 candidate rows; 3,611 ward rows. `Type` column (`MB`, `LB`, `UAT`, `UAA`, `SDT`, `SDA`) enables scope filtering. 33 MB authorities present — Liverpool, Doncaster, Rotherham absent (no 2022 elections — expected). Parse `Candidates-results` with `header=1`. Electorate and turnout join from `Wards-results` via `Ward code`.

---

## 2. Usable With Specific Parsing Requirements

### `dcleapil_2006_2024.csv`

**One file. All years 2006–2024.** Uploads used in this audit were filtered slices cut for size only. Pipeline reads the full file once, drops null-year rows, and filters to `{2014, 2015, 2016, 2018, 2022}`.

**Encoding: UTF-8-BOM.** Load with `encoding='utf-8-sig'`. Standard `utf-8` prepends `\ufeff` to the first column name causing silent join failures.

**Null-year rows: drop on load.** The full file contains null-year padding rows.

**In-scope rows after filter:**

| Year | Rows | Dataset source | `data_source_era` |
|---|---|---|---|
| 2014 | 17,038 | LEAP only | `leap_only` |
| 2015 | 30,729 | LEAP only | `leap_only` |
| 2016 | 10,957 | DC-LEAP | `dc_leap` |
| 2018 | 17,005 | DC (949) + DC-LEAP (16,056) | `dc_leap` |
| 2022 | 21,932 | DC-LEAP | `dc_leap` |

`data_source_era` boundary is **2016**, not 2019. 2014/2015 are pure LEAP; 2016 is the first DC-LEAP merge year.

**Null rates by year:**

| Field | 2014 | 2015 | 2016 | 2018 | 2022 |
|---|---|---|---|---|---|
| `vote_share` | 25.4% | 25.8% | 14.4% | 30.8% | ~30% |
| `electorate` | 4.1% | 6.5% | 8.6% | 5.5% | 2.6% |
| `turnout_percentage` | 4.1% | 7.3% | 7.8% | 2.7% | — |
| `GSS` | 0.0% | 0.0% | 0.2% | 0.0% | ~0% |

**Key field notes:**

- `type` — **party type** (Major / Minor / Independent / Localist etc.), never authority type. Never use as authority filter.
- `vote_share` — **CRITICAL: in multi-member wards, only populated for the candidate with the most votes within each party.** FI must derive from `votes_cast / turnout_valid` for all candidates.
- `ENP` — pre-computed `1/Σ(VS²)`. Identical to our FI formula. Use as Phase 8 QA cross-check only.
- `votes_cast` — string type. One comma-formatted value: `"1,251"` (Sunderland/Pallion, 2018). Strip commas before cast.
- `turnout_valid` — total valid votes in ward. Denominator for FI derivation and turnout correction.
- `turnout_percentage` — **MULTI-MEMBER CORRECTION REQUIRED.** In multi-member wards, `turnout_valid` = total votes cast across all seats, exceeding electorate. 490 rows exceed 100%. Correct as `(turnout_valid / seats_contested) / electorate * 100`. Apply at Phase 4 load time.
- `GSS` — most recent GSS code assigned retroactively. Dec 2018 lookup is the correct GSS join for all years including 2014–2016.
- `tier` — DCLEAPIL authority tier (Unitary / Lower Tier / Upper Tier). Not civic-lens Tier 1/2/3.
- `party_id` — joins to `EC_Ref1` in `DCLEAPIL_v1_0_Party_coding.csv`. Three unmatched: `NR_Ind`/`NR_IndLR` → `IND`; `joint-party:15-64` → `EC_Ref2` join (Civic ILP).
- `seats_contested_calc = 0` — 4 rows (Tewkesbury, Lower Tier, South West). All out of scope — drop at Phase 4.

**All in-scope authorities confirmed present** for all years. London boroughs in 2014 (all 32, whole council); partial coverage 2015/2016 (by-elections only).

### `ward_lad_lookup_dec2018.csv`
9,114 rows. `WD18CD` and `LAD18CD` fully populated. UK-wide — filter to England. **Primary GSS join key for all DCLEAPIL years including 2014–2016** — DCLEAPIL retroactively assigns modern codes, so Dec 2018 matches far better than Dec 2016.

**Metadata mismatch (logged):** `DATA_SOURCE_METADATA.md` previously stated `CTY18NM` and `RGN18NM` as key fields — **neither is present.** Actual columns: `WD18CD`, `WD18NM`, `WD18NMW`, `LAD18CD`, `LAD18NM`, `FID`. Region lookup is a two-step join: `WD18CD → LAD18CD` (this file), then `LAD18CD → RGN23NM` (Apr 2023 LAD-region lookup). `DATA_SOURCE_METADATA.md` corrected.

### `DCLEAPIL_v1_0_Party_coding.csv`
661 rows, 17 columns. **Join key: `party_id` in main DCLEAPIL file → `EC_Ref1` here.** Not `MergePartyID`.

| Column | Pipeline use |
|---|---|
| `EC_Ref1` | Primary join key — matches `party_id` in main file |
| `EC_Ref2` | Secondary join — use when `EC_Ref1` fails (joint parties) |
| `Type` | Full party type classification |
| `Type2` | Simplified grouping (Major / Minor / ILP / Independent) — canonical `party_group` field |
| `ILP` | Yes/No flag — required for challenger identification in S1/S3 |

**3 unmatched `party_id` values:** `NR_Ind`/`NR_IndLR` → `IND`; `joint-party:15-64` → found via `EC_Ref2` (Civic ILP).

### `DCLEAPIL_v1_0_Variable_descriptions.csv`
30 rows, 2 columns. Reference document — not loaded in pipeline. Pipeline-critical findings:

1. `vote_share` — multi-member caveat: only populated for highest-vote party candidate per party. FI must derive from `votes_cast / turnout_valid`.
2. `ENP` — pre-computed `1/Σ(VS²)`. Use as Phase 8 QA cross-check, not primary input.
3. `GSS` — "most recent GSS code for this ward area" — explains retroactive code assignment.
4. `top_vote` — highest vote in the ward, not this candidate's vote.
5. `turnout_valid` — sum of all `votes_cast` (valid only). Denominator for FI and turnout correction.
6. `electorate` — higher null rate in LEAP-only years (2014/2015).

### `local_elections_2021.xlsx`
18,044 candidate rows; 3,863 ward rows. `Votes (%)` present. No `Type` column — derive authority type from code prefix. Parse with `header=1`. Typo: `Inumbent`. **Not in pipeline — completeness and contextual use only.** Wide-party ward sheet (149 columns, 138 party codes). `GREEN ACCIDENTAL CANDIDATE` and `LAB ACCIDENTAL CANDIDATE` columns must be excluded from party pivot. `YORKS` present.

### `local_elections_2022.xlsx` — ward sheet detail
`Wards-results`: 121 columns including 110 party-code columns. `YORKS` present across all 124 Tier 3 ward rows (25 total votes). No accidental candidate columns. Wide-to-long reshape required. Duplicate column pair in Candidates-results: `COUNTYCODE`/`COUNTYNAME` — drop in loader.

### `local_elections_2025.xlsx`
**NOT IN PIPELINE.** No in-scope metro or London boroughs held elections in May 2025 (county council fallow year for by-thirds metropolitan districts). File retained in `data/raw/` for provenance only. Key characteristics documented for reference:

- 8,141 candidate rows; 1,401 ward rows. Complete schema break vs 2021/2022 — different sheet names, entirely different column names.
- Two turnout measures: `Turnout (EC method)` (Ballots/Electorate, ratio 0–1) and `Valid vote turnout (HoC method)` (valid votes/electorate, ratio 0–1). Diverge by >1pp in 16 wards.
- Party coverage reduced to 6 named parties + `Other parties / candidates` aggregate.
- Does not cover any in-scope metro or London boroughs.

### `wards_dec2021_bgc` (shapefile)
*(stored as `wards_dec2021_bgc.*` — confirmed filename; `DATA_SOURCE_METADATA.md` corrected)*

8,232 features; 7,026 England features. CRS: EPSG:27700. No LAD code — filter to Tier 3 via name-based join. Proxy for 2018-era ward geometry (visualisations only): 71% of DCLEAPIL 2018 GSS codes match `WD21CD`; 847 unmatched fall back to borough rendering. No effect on metric computation.

### `wards_dec2022_bgc` (shapefile)
8,483 features; 6,904 England features. CRS: EPSG:27700. `LAD22CD` embedded — direct Tier 3 filter possible. 124 Tier 3 ward features confirmed present.

---

## 3. Schema Mismatches (Carried into Phase 2)

Phase 2 produced `DATA_DICTIONARY.md` with definitive resolution for every mismatch below.

| Field | DCLEAPIL (all in-scope years) | Commons Library 2021 | Commons Library 2022 | Commons Library 2025 |
|---|---|---|---|---|
| Vote share | `vote_share` (%, derived — multi-member caveat) | `Votes (%)` (present) | Not present — derive | Not present — derive |
| Votes column | `votes_cast` (string — comma-strip + cast) | `Votes` (int) | `Votes` (int) | `Votes cast` (int) |
| Authority type | `type` = PARTY TYPE — never use | Derive from code | `Type` = authority type | `Local authority type` |
| Ward code | `GSS` (ONS E05xxxxx) | `Ward/ED code` | `Ward code` | `ONS ward code` |
| Total valid votes | `turnout_valid` (count) | `Total valid votes` | `Total valid votes` | Not present — aggregate |
| Electorate | `electorate` (partial — higher null in 2014/2015) | In candidates sheet | In Wards-results sheet | In Ward results sheet |
| Turnout % | `turnout_percentage` (**multi-member correction required**) | `Turnout (%)` | `Turnout (%)` (per-elector, no correction) | Not in pipeline |
| Incumbent | `top_vote` ≠ incumbent | `Inumbent` [sic] | `Incumbent` | Not in pipeline |
| Candidate ID | `DC_person_id` / `merge_candidate` | `Candidate number` | `Candidate number` | Not in pipeline |
| Seats contested | `seats_contested_calc` | `Votes effective` proxy | `Vacancies` | Not in pipeline |

---

## 4. Anomalies and Resolutions

| Anomaly | Resolution |
|---|---|
| `ward_lad_lookup_dec2018.csv` missing `CTY18NM`/`RGN18NM` | `DATA_SOURCE_METADATA.md` corrected; region join is two-step |
| `ward_lad_lookup_may2022.xlsx` redundant vs dec2022 CSV | Use dec2022 as canonical; retain for provenance |
| `wards_dec2021_bgc` filename vs `wards_2021_bgc` in metadata | `DATA_SOURCE_METADATA.md` corrected |
| `wards_dec2021_bgc` no LAD code embedded | Filter via name-based join to ward-LAD lookup |
| 847 DCLEAPIL 2018 GSS codes unmatched in dec2021 shapefile | Borough-level fallback for visualisations only |
| DCLEAPIL `type` = party type, not authority type | Derive authority type from GSS/LAD join only |
| DCLEAPIL `vote_share` null in multi-member wards | Derive as `votes_cast / turnout_valid * 100` for all candidates |
| DCLEAPIL `turnout_percentage` >100% in multi-member wards (490 rows) | Correct: `(turnout_valid / seats_contested) / electorate * 100` — applied at Phase 4 load |
| DCLEAPIL `votes_cast` string with comma (`"1,251"` — Sunderland/Pallion 2018) | Strip commas, cast to int in Phase 4 loader |
| DCLEAPIL `seats_contested_calc = 0` (4 rows, Tewkesbury) | Drop at Phase 4 — out of scope (Lower Tier) |
| DCLEAPIL ward names differ from Commons Library in punctuation | Standardise in Phase 5 — do not join on raw strings |
| DCLEAPIL null-year padding rows in full file | Drop rows where `year is null` at load time |
| DCLEAPIL `data_source_era` boundary is 2016, not 2019 | 2014/2015 = `leap_only`; 2016+ = `dc_leap` |
| DCLEAPIL Dec 2016 lookup matches only 60–72% of training GSS | Use Dec 2018 lookup for GSS join; Dec 2016 for boundary concordance only |
| 2022: Liverpool, Doncaster, Rotherham absent from Commons Library | Expected — no 2022 elections held |
| 2022: 70 uncontested wards | `votes=NULL`, `analysis_level=borough_only` |
| 2022: duplicate county columns (`COUNTYCODE`/`COUNTYNAME`) | Drop in loader |
| 2021/2022 ward sheets: wide party format (100+ columns) | Wide-to-long reshape; exclude accidental candidate columns |
| 2021: `GREEN ACCIDENTAL CANDIDATE`/`LAB ACCIDENTAL CANDIDATE` columns | Exclude from party pivot |
| 2022: `YORKS` party (25 votes in Tier 3) | Include in pivot — negligible metric impact |
| 2025: not in pipeline | Retained for provenance; not loaded |
| IMD: no decile column | Derive via `pd.qcut` in Phase 4 loader |
| IMD: 28 pre-reorganisation LAD codes | Out of scope — documented for auditability |

---

## 5. Phase 2 Schema Validation Findings

Schema was validated against real data in Phase 2. These findings are documented in full in `data/processed/DATA_DICTIONARY.md` and are not action items for Phase 1 — recorded here for audit continuity.

- **490 DCLEAPIL rows with `turnout_percentage > 100%`** — multi-member artefact (not a data error). Corrected by `(turnout_valid / seats_contested) / electorate * 100`.
- **157 uncontested wards** in training data (2015: 143). `analysis_level = borough_only`, `notes = 'uncontested'`.
- **`vote_share` always derived** from `votes_cast / turnout_valid` — DCLEAPIL source field unreliable in multi-member wards.
- **`data_source_era` boundary confirmed as 2015/2016** — not pre-2019.
- **4 rows with `seats_contested_calc = 0`** (Tewkesbury, Lower Tier) — dropped at Phase 4.

---

## 6. Data Quality Action Plan

Items still outstanding (forward-looking). Completed items removed.

### Completeness

| Action | Phase | Blocks |
|---|---|---|
| Assert all 36 metro boroughs and all 32 London boroughs present in DCLEAPIL for all five in-scope years (2014/2015/2016 sample-verified; 2018/2022 confirmed) | Phase 4 | Phase 9 |
| Document which 2022 wards have null electorate (Wards-results join required) | Phase 5 | Nullable — document only |

### Accuracy

| Action | Phase | Blocks |
|---|---|---|
| Cross-validate DCLEAPIL 2022 vs Commons Library 2022 for all overlapping MB and LB authorities | Phase 8 (QA) | Phase 9 |
| Validate `votes_cast` comma strip: confirm Sunderland/Pallion = `1251` after cleaning | Phase 4 | Phase 5 |
| Validate derived `vote_share` for Manchester, Newcastle, Leeds 2018 — spot-check 10 wards each | Phase 5 | Phase 9 |
| Assert ward count consistency: candidates sheet count per ward = Wards-results row count | Phase 5 | Phase 8 QA |

### Consistency

| Action | Phase | Blocks |
|---|---|---|
| Define ward name standardisation rules in `src/civic_lens/ward_name_utils.py` | Phase 5 | Cross-source join |
| Define party standardisation lookup: `party_id` → `EC_Ref1` → `Type2`/`ILP` (party coding file inspected — join key confirmed) | Phase 5 | Phase 9 |
| Decide `YORKS` party handling in Tier 3 (include in pivot — 25 votes, negligible impact) | Phase 5 | Phase 7 |

### Validity

| Action | Phase | Blocks |
|---|---|---|
| Assert `vote_share` in range 0–100 after derivation | Phase 5 | Phase 8 QA |
| Assert `votes_cast` ≥ 0 after numeric cast | Phase 4 | Phase 5 |
| Assert `seats_won` ≤ `seats_contested` per row | Phase 5 | Phase 8 QA |
| Assert `turnout_pct` in range 0–100 after multi-member correction | Phase 4/5 | Phase 8 QA |
| Assert all 32+32+5 in-scope authorities present; 4 excluded boroughs absent | Phase 6 | Phase 9 |
| Assert no duplicate ward-party-year rows after cleaning | Phase 5 | Phase 8 QA |
| Assert `year` in `{2014, 2015, 2016, 2018, 2022}` in DCLEAPIL interim output | Phase 4 | Phase 5 |

### Timeliness

| Action | Phase | Blocks |
|---|---|---|
| Confirm no post-2019 IMD vintage has been published | Phase 9 | METHODOLOGY.md accuracy |

### Uniqueness

| Action | Phase | Blocks |
|---|---|---|
| Drop `COUNTYCODE`/`COUNTYNAME` duplicate columns in 2022 loader | Phase 4 | Phase 5 |
| Exclude `GREEN ACCIDENTAL CANDIDATE`/`LAB ACCIDENTAL CANDIDATE` from 2021 party pivot | Phase 4 | Phase 5 |
| Flag duplicate ward name entries within same authority and year after standardisation | Phase 5 | Phase 7 |

---

## 7. Acquisition Tasks — All Closed

| Task | Status | Resolution |
|---|---|---|
| Tier 3 2025 data acquisition | **CLOSED — never required** | Calibration chain revised to 2014→2018→2022. No 2025 data used at any stage. Calderdale-only 2025 result insufficient for generalisable error distribution regardless. |
| DCLEAPIL 2014/2015/2016 extract | **CLOSED — never required** | DCLEAPIL is one file (2006–2024). Training years already present. Filter `{2014, 2015, 2016, 2018, 2022}` at load time. |
| Ward-LAD lookup for training window | **CLOSED** | Dec 2018 lookup (GSS join), Dec 2016 lookup (boundary reference), 2011→2022 crosswalk (split/merge concordance) — all in hand. |
| Inspect party coding and variable descriptions | **CLOSED** | Both files inspected. Join key: `party_id → EC_Ref1`. `Type2` and `ILP` flag confirmed as pipeline-relevant fields. |

---

## Exit Status

**Phase 1 exit criteria: met.** All 17 sources structurally understood. All acquisition tasks closed. Data quality action plan in place. No cleaning has begun.

**Phase 2 status: complete.** Canonical schema frozen (`DATA_DICTIONARY.md`). All six metrics frozen. All six scenarios frozen (`SCENARIO_DEFINITIONS.md`). Schema validated against real data — all edge cases documented.

**Next: Phase 3 — Metric Engine Foundation.**