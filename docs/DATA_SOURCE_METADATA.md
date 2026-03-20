# Data Source Metadata

All raw data files in `data/raw/`. Licence and provenance recorded here for audit trail.

---

## Election Results

### DCLEAPIL v1.0

| Field | Value |
|---|---|
| **File** | `ec/dcleapil_2006_2024.csv` + `ec/dcleapil_party_coding.csv` + `ec/dcleapil_variable_descriptions.csv` |
| **Source** | Figshare — Jason Leman (2025) |
| **URL** | https://figshare.com/articles/dataset/DCLEAPIL_v1_0_British_local_election_results_dataset_2006-2024/28920872 |
| **Licence** | CC BY-SA 4.0 |
| **Citation** | Leman, Jason (2025) DCLEAPIL_v1.0, Figshare |
| **Download date** | 2026-03-11 |
| **Coverage** | British local government principal authority elections 2006–2024 |
| **Used for** | **Training window (2014, 2015, 2016)** and **2018 backtest origin** — primary source across the full calibration chain; cross-check for 2022 results |
| **Notes** | Draws on Andrew Teale's LEAP dataset (2006–2021) and Democracy Club (2019–2024). `leap_only` era (2014/2015): LEAP-sourced only — materially degraded electorate, turnout, and by-election coverage. `dc_leap` era (2016+): DC-LEAP merged. All required years are present in the full file — no separate extract needed. See READ_ME.txt in same folder. |

---

### DCLEAPIL v1.0 — Party Coding

| Field | Value |
|---|---|
| **File** | `ec/DCLEAPIL_v1_0_Party_coding.csv` |
| **Source** | Figshare — Jason Leman (2025) / DCLEAPIL v1.0 |
| **Licence** | CC BY-SA 4.0 |
| **Download date** | 2026-03-20 |
| **Coverage** | 661 party records; 17 columns |
| **Used for** | Party standardisation in Phase 5. Join `party_id` (main file) → `EC_Ref1` (this file) to get `Type`, `Type2`, `ILP` flag, and canonical `Party Name`. |
| **Notes** | Primary join key is EC_Ref1 (not MergePartyID). 3 unmatched cases require fallback: NR_Ind/NR_IndLR → IND; joint-party:15-64 → EC_Ref2 join. ILP flag (Yes/No) required for challenger identification logic in scenario engine. |

---

### DCLEAPIL v1.0 — Variable Descriptions

| Field | Value |
|---|---|
| **File** | `ec/DCLEAPIL_v1_0_Variable_descriptions.csv` |
| **Source** | Figshare — Jason Leman (2025) / DCLEAPIL v1.0 |
| **Licence** | CC BY-SA 4.0 |
| **Download date** | 2026-03-20 |
| **Coverage** | 30 variable definitions |
| **Used for** | Reference only — not loaded in pipeline |
| **Notes** | Key findings: vote_share multi-member caveat; GSS uses most-recent code; ENP = 1/Σ(VS²) (same as FI); top_vote = ward maximum not candidate vote; turnout_valid = sum of votes_cast excluding invalid ballots. |


---

### Commons Library Local Elections 2021

| Field | Value |
|---|---|
| **File** | `ec/local_elections_2021.xlsx` |
| **Source** | House of Commons Library — Rallings, Thrasher & Bunting (Elections Centre, University of Exeter) |
| **URL** | https://commonslibrary.parliament.uk/data/parliament-elections-data/2021-local-elections-handbook-and-dataset/ |
| **Licence** | Open Parliament Licence v3.0 |
| **Download date** | 2026-03-11 |
| **Coverage** | England local elections, 6 May 2021 — ward-level candidate votes, turnout, vacancies |
| **Used for** | Completeness only — **excluded from baseline calibration**. 2021 was a pandemic election with structurally suppressed turnout and cancelled contests. See `docs/DECISIONS_LOG.md`. |
| **Notes** | Downloaded for potential contextual use and to satisfy audit completeness. Pipeline will not load this file in the main calibration chain. |

---

### Commons Library Local Elections 2022

| Field | Value |
|---|---|
| **File** | `ec/local_elections_2022.xlsx` |
| **Source** | House of Commons Library — Rallings, Thrasher & Bunting (Elections Centre, University of Exeter) |
| **URL** | https://commonslibrary.parliament.uk/data/parliament-elections-data/2022-local-elections-handbook-and-dataset/ |
| **Licence** | Open Parliament Licence v3.0 |
| **Download date** | 2026-03-11 |
| **Coverage** | England local elections, 5 May 2022 — 18,481 candidate rows, 3,611 ward rows |
| **Used for** | **Backtest target** — actual 2022 results against which the 2014→2018 trained model is measured; cross-checked against DCLEAPIL |
| **Notes** | Primary source for Tier 1 (metro boroughs) and Tier 2 (London boroughs). Sourced from local authority websites and direct correspondence. Quality cross-checked against DCLEAPIL. |

---

### Commons Library Local Elections 2025

| Field | Value |
|---|---|
| **File** | `ec/local_elections_2025.xlsx` |
| **Source** | House of Commons Library — Rallings, Thrasher & Bunting (Elections Centre, University of Exeter) |
| **URL** | https://commonslibrary.parliament.uk/2025-local-elections-handbook-and-dataset/ |
| **Licence** | Open Parliament Licence v3.0 |
| **Download date** | 2026-03-11 |
| **Coverage** | England local elections, 1 May 2025 — ward-level candidate votes, turnout, vacancies, seats |
| **Used for** | **NOT IN PIPELINE.** No in-scope metro or London boroughs held elections in 2025. Retained in data/raw/ for provenance only. See DECISIONS_LOG. |
| **Notes** | 2025 elections covered county councils and unitaries only — no in-scope metro or London boroughs are present. Calderdale held a 2025 by-thirds election but is not used as a standalone calibration source. Pipeline does not load this file. |

---

## Geographic Lookups

### ONS Ward to LAD Lookup — December 2018

| Field | Value |
|---|---|
| **File** | `ons/ward_lad_lookup_dec2018.csv` |
| **Source** | ONS Open Geography Portal |
| **URL** | https://geoportal1-ons.opendata.arcgis.com/datasets/0fa948d8a59d4ba6a46dce9aa32f3513_0 |
| **Licence** | OGL v3 |
| **Download date** | 2026-03-11 |
| **Coverage** | All UK wards — December 2018 vintage |
| **Key fields** | `WD18CD`, `WD18NM`, `WD18NMW`, `LAD18CD`, `LAD18NM`, `FID` |
| **Metadata note** | `CTY18NM` and `RGN18NM` previously listed as key fields — **neither is present in the file**. Region lookup requires two-step join: `WD18CD → LAD18CD` (this file) then `LAD18CD → RGN23NM` (Apr 2023 LAD-region lookup). |
| **Used for** | Mapping 2018 ward codes to borough/LAD codes for baseline metric computation |

---

---

### ONS Ward to LAD Lookup — December 2016

| Field | Value |
|---|---|
| **File** | `ons/ward_lad_lookup_dec2016.csv` |
| **Source** | ONS Open Geography Portal |
| **URL** | https://geoportal.statistics.gov.uk (Ward to Local Authority District December 2016 Lookup) |
| **Licence** | OGL v3 |
| **Download date** | 2026-03-20 |
| **Coverage** | All UK wards — December 2016 vintage; 9,130 rows; 7,463 England rows; zero nulls |
| **Key fields** | `WD16CD`, `WD16NM`, `LAD16CD`, `LAD16NM`, `FID` |
| **Used for** | **Boundary concordance reference (Phase 7) — NOT used as GSS join key.** DCLEAPIL retroactively assigns modern GSS codes to 2014–2016 elections, so Dec 2016 matches only 60–72% of training year GSS codes. The Dec 2018 lookup (already in project) is the correct GSS join for training data. This file provides ground-truth of which wards *existed* in 2014–2016 for concordance decisions. |
| **Notes** | No 2014 Ward-LAD lookup exists on ONS geoportal. Dec 2016 is the closest available vintage for 2014–2016 boundary reference. FID column droppable. UK-wide — filter to England. |

---

### ONS Ward to LAD Lookup — May 2022

| Field | Value |
|---|---|
| **File** | `ons/ward_lad_lookup_may2022.csv` |
| **Source** | ONS Open Geography Portal |
| **URL** | https://geoportal.statistics.gov.uk/datasets/ons::ward-to-local-authority-district-may-2022-lookup-in-the-uk |
| **Licence** | OGL v3 |
| **Download date** | 2026-03-11 |
| **Coverage** | All UK wards — May 2022 vintage |
| **Key fields** | `WD22CD`, `WD22NM`, `LAD22CD`, `LAD22NM` |
| **Used for** | Mapping 2022 election ward codes to borough/LAD codes |

---

### ONS Ward to LAD Lookup — December 2022

| Field | Value |
|---|---|
| **File** | `ons/ward_lad_lookup_dec2022.csv` |
| **Source** | ONS Open Geography Portal |
| **URL** | https://geoportal.statistics.gov.uk/datasets/ons::ward-to-local-authority-district-december-2022-lookup-in-the-uk/about |
| **Licence** | OGL v3 |
| **Download date** | 2026-03-11 |
| **Coverage** | All UK wards — December 2022 vintage |
| **Key fields** | `WD22CD`, `WD22NM`, `LAD22CD`, `LAD22NM` |
| **Used for** | Mapping 2022 election ward codes to borough/LAD codes (canonical 2022 ward lookup) |

---

### ONS LAD to Region Lookup — April 2023

| Field | Value |
|---|---|
| **File** | `ons/lad_region_lookup_apr2023.csv` |
| **Source** | ONS Open Geography Portal |
| **URL** | https://geoportal.statistics.gov.uk (search: "Local Authority District to Region April 2023") |
| **Licence** | OGL v3 |
| **Download date** | 2026-03-11 |
| **Coverage** | All English LADs — April 2023 vintage |
| **Key fields** | `LAD23CD`, `LAD23NM`, `RGN23CD`, `RGN23NM` |
| **Used for** | LAD → region mapping; authority_type classification (metropolitan_borough / london_borough / yorkshire_tier3). April 2023 chosen as stable vintage covering all election years without post-2025 reorganisation distortion. |
| **Notes** | `authority_type` column added manually in processing pipeline — not present in raw file. |

---

### ONS Ward to LAD Lookup — December 2011 (2011→2022 Concordance Crosswalk)

| Field | Value |
|---|---|
| **File** | `ons/ward_lad_lookup_dec2011.csv` |
| **Source** | ONS Open Geography Portal |
| **URL** | https://geoportal.statistics.gov.uk (search: Ward and Local Authority District 2011 to 2022 Lookup in EW) |
| **Licence** | OGL v3 |
| **Download date** | 2026-03-20 |
| **Coverage** | England and Wales — row counts to be verified from repo checkout before Phase 7 |
| **Key fields** | `WD11CD`, `WD11NM`, `LAD11CD`, `LAD11NM`, `WD22CD`, `WD22NM`, `LAD22CD`, `LAD22NM` |
| **Used for** | Phase 7 concordance table — maps every 2011 ward to its 2022 equivalent, capturing all splits and merges across the 11-year window. Essential for tracking boundary changes between the training window (2014–2016) and backtest target (2022). |
| **Notes** | Maps every 2011 ward code to its 2022 equivalent — covers all splits and merges across the 11-year window. Covers all in-scope metro/London boroughs and all 5 West Yorkshire councils. **Not used as GSS join key** — DCLEAPIL uses modern retroactive codes; Dec 2018 lookup handles the GSS join. Verify exact row counts and split/merge statistics before Phase 7. `ObjectId` column droppable if present. |

---

## Boundary Shapefiles

### ONS Wards December 2021 BGC

| Field | Value |
|---|---|
| **Files** | `boundaries/wards_dec2021_bgc.*` (`.shp`, `.dbf`, `.prj`, `.shx`, `.cpg`) |
| **Source** | ONS Open Geography Portal |
| **URL** | https://geoportal.statistics.gov.uk (Boundaries → Wards / Electoral Divisions → 2021 Boundaries → BGC) |
| **Licence** | OGL v3 |
| **Download date** | 2026-03-11 |
| **Coverage** | All UK wards — 2021 vintage, generalised 20m, clipped to coastline |
| **Used for** | Map visualisations representing 2018-era ward geography. **No 2018 shapefile is published by ONS** — 2021 is the closest available proxy. Documented in `data/processed/DATA_DICTIONARY.md` as `boundary_vintage = 2021, proxy_for = 2018`. |
| **Notes** | Not used in metric computation — visuals only. Filter to Yorkshire Tier 3 councils in pipeline using `LAD21NM`. |

---

### ONS Wards December 2022 BGC

| Field | Value |
|---|---|
| **Files** | `boundaries/wards_dec2022_bgc.*` (`.shp`, `.dbf`, `.prj`, `.shx`, `.cpg`) |
| **Source** | ONS Open Geography Portal |
| **URL** | https://geoportal.statistics.gov.uk (Boundaries → Wards / Electoral Divisions → 2022 Boundaries → BGC) |
| **Licence** | OGL v3 |
| **Download date** | 2026-03-11 |
| **Coverage** | All UK wards — December 2022 vintage, generalised 20m, clipped to coastline |
| **Used for** | Map visualisations for 2022 and 2025 election results. Filter to scope councils in pipeline using `LAD22NM`. |
| **Notes** | Not used in metric computation — visuals only. BGC (generalised) chosen over BFC (full resolution) — sufficient for analytical maps, significantly smaller file. |

---

## Socioeconomic Overlay

### English Indices of Deprivation 2019

| Field | Value |
|---|---|
| **File** | `imd/imd_2019_lad_summary.xlsx` |
| **Source** | Ministry of Housing, Communities & Local Government via ONS Nomis |
| **URL** | https://www.gov.uk/government/statistics/english-indices-of-deprivation-2019 |
| **Licence** | OGL v3 |
| **Download date** | 2026-03-11 |
| **Coverage** | All English local authority districts — IMD 2019 scores and deciles |
| **Used for** | Scenario S4 only — identifying wards in IMD deciles 1–3 for the deprivation turnout shift scenario (ΔT = +3pp). **Descriptive overlay only — IMD does not infer, adjust, or predict vote share.** |
| **Notes** | File 10 from the full IoD 2019 release: `File_10_-_IoD2019_Local_Authority_District_Summaries_(lower-tier).xlsx`. No newer vintage used — IMD is published infrequently and 2019 is the current standard for this analysis period. |

---

## Licence Summary

| Licence | Applies to |
|---|---|
| CC BY-SA 4.0 | DCLEAPIL (requires attribution and ShareAlike on derivatives) |
| Open Parliament Licence v3.0 | Commons Library datasets |
| OGL v3 | All ONS datasets, IMD |

All licences permit free use, analysis, and publication of derived outputs with attribution. Raw data files are not committed to the repository — see `.gitignore`. Derived outputs in `data/processed/` are committed.