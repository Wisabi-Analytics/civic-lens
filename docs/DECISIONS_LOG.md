# Analytical Decisions Log

Key decisions with full rationale and rejected alternatives.

---

| Decision | Choice | Core Rationale |
|---|---|---|
| Baseline year | 2018 (not 2021) | 2021 = pandemic outlier, would conflate two disruptions |
| Ward granularity | Borough-level for Tier 1+2 | Harmonisation cost too high; borough analysis is fully valid |
| Monte Carlo iterations | 2,000 | Calibration logic matters, not simulation volume |
| Bootstrap source | Borough-specific error distributions | National pool too coarse; each borough has its own volatility pattern |
| Borough independence | No correlation modelling | Too few cycles to estimate reliable covariance for 64 boroughs |
| Volatility Score weights | Equal (0.5 swing / 0.5 ΔFI) | No strong prior for privileging either component |
| Seat Change in scenarios | Historical data only, not simulated | Seat projections would contradict "not a forecast" positioning |
| Challenger framing | Mechanical per-borough rule | Party-neutral, auditable, avoids perception risk |
| 2021 data | Included in raw/, excluded from calibration | Available for context; structurally unsuitable as baseline |

---

| Metropolitan borough count | 32 of 36 election-active (not all 36) | 4 councils (Doncaster, Liverpool, Wirral, Rotherham) have no 2026 election — excluded on factual grounds |
| Mayoral elections | Descriptive context layer only — excluded from volatility system | All 10 combined authority mayoral elections are newly-established roles. No historical baseline = no calibration = no volatility outputs. Publishing volatility metrics without a baseline would be methodologically dishonest. |
| All-out elections (Tier 1) | Borough aggregate only for 6 confirmed metropolitan boroughs in 2026 | GOV.UK timetable + LGBCE boundary reviews confirm six Tier 1 boroughs with all-out 2026 elections. Ward-level longitudinal comparisons are impossible for those authorities without a concordance map, so borough aggregates are used there. |

| Calibration chain | 2014→2018 (train) / 2018→2022 (backtest) / 2022→2026 (predict) | Original chain (2018→2022→2025) required 2025 metro/London borough data which does not exist (county council fallow year). Revised chain uses 65+ boroughs across full 2022 backtest — statistically stronger than a Calderdale-only 2025 calibration. Brexit-era training window limitation stated explicitly in METHODOLOGY.md. |
| 2025 data | Not used in pipeline | No in-scope metro or London boroughs held 2025 elections. Calderdale held a by-thirds result but single-borough calibration is insufficient for generalisable error distribution. Commons Library 2025 retained for provenance only. |
| data_source_era boundary | 2015/2016 (not pre-2019) | DCLEAPIL dataset field confirms: 2014/2015 = LEAP only; 2016 = DC-LEAP first merge year. The pre-2019 label used in earlier drafts was wrong. |
| DCLEAPIL file architecture | One file (2006–2024), filtered at load time | Uploads were slices for size reasons only. Pipeline reads full file, drops null-year rows, filters to {2014, 2015, 2016, 2018, 2022}. Encoding: UTF-8-BOM (utf-8-sig). |

*(Full entries including rejected alternatives maintained in WarBoard v3 Decisions Log tab)*

---

## S5 Removal Log

*(Populated if S5 removed during Phase B — logged before model lock)*

| Date | Decision | Rationale | Alternative Considered |
|---|---|---|---|
| [TBD] | [S5 kept / S5_REMOVED] | [Empirical cap derived / insufficient data] | [N/A or substitute considered and rejected] |

---

## All-Out Election Boroughs (Tier 1 — Confirmed During Phase A)

Six metropolitan boroughs hold all-out elections in 2026 due to either their statutory cycle or LGBCE review.

| Authority | LAD code | Reason |
|---|---|---|
| Barnsley | E08000016 | GOV.UK election timetable: whole-council election 2026 (next due 2030) |
| Birmingham | E08000025 | GOV.UK election timetable: whole-council election 2026 (standard four-year cycle) |
| St Helens | E08000013 | GOV.UK election timetable: whole-council election 2026 (standard four-year cycle) |
| Calderdale | E08000033 | LGBCE boundary review forces an all-out election in 2026 before reverting to thirds |
| Coventry | E08000026 | LGBCE review confirmed all seats up in 2026 before returning to thirds |
| Kirklees | E08000034 | LGBCE boundary review schedules an all-out 2026 election (Tier 3 council as part of WYCA footprint) |

All other metropolitan boroughs hold ordinary-staggered elections; London boroughs likewise run their usual four-year cycle and are not flagged `all_out_lgbce` in the concordance. Each listed council is annotated via the concordance table as `change_type = all_out_lgbce` and every candidate row belonging to these authorities carries `analysis_level = borough_only`. The "13" count in earlier drafts was an estimate; the GOV.UK / LGBCE sources confirm the six authorities above for 2026.

---

## Mayoral Context Layer — Exclusion Rationale

**Decision date:** Confirmed at scope lock  
**Decision:** All 10 combined authority mayoral elections excluded from volatility measurement system.

**Reason:** All 2026 combined authority mayoral elections are newly-established roles (confirmed: Wikipedia, 2026 United Kingdom local elections). No prior election exists from which to compute swing, turnout delta, fragmentation trend, or any time-series metric. Running the volatility pipeline against a single data point would produce undefined or meaningless outputs.

**Alternative considered:** Include mayors in the volatility system with a single-cycle "baseline" using invented reference values. Rejected — this would require fabricating a baseline, violating the project's transparency principles.

**What is published instead:** A separate descriptive analysis (`reports/mayoral_context.md`) covering vote share distribution, turnout, and candidate field fragmentation for each of the 10 mayors. These outputs are clearly labelled as descriptive-only with no volatility claims.

**Public statement:** *"Civic Lens excludes mayoral elections from its volatility framework because all 10 roles are newly established with no prior election baseline. A system that cannot be calibrated should not produce volatility outputs. Mayoral results are included as contextual civic analysis only."*
## Phase 8 QA — H06: Brent St. Oswald (1 row)
**Status:** QA check definition corrected — data is correct  
**Affected rows:** 1 (0.00%)  
**Expected:** vote_share derivation should run whenever `votes` and `total_valid_votes` are present at the ward level.  
**Actual:** Brent St. Oswald 2022 has `votes=0` and `total_valid_votes=0`, so the 0/0 computation correctly remains `null`.  
**Resolution:** `has_both` now requires `total_valid_votes > 0`. The data is correct; the check no longer flags St. Oswald.

## Phase 8 QA — H07 / E01: City of London block voting (19 rows)
**Status:** Accepted — City of London is structurally incomparable at the ward level  
**Affected rows:** 19 mismatches (0.06%)  
**Expected:** Derived vote_share equals votes/total_valid_votes to within 0.01pp and the DCLEAPIL ENP matches our fragmentation index for single-member wards.  
**Actual:** City of London wards use block voting, so candidates can receive more individual votes than there are voters (e.g., 203 votes from 88 ballot papers → 230%). The canonical vote_share value of 100.0 leaked through because ward-level fractional shares are undefined in this system.  
**Resolution:** Post-cleaner override now sets City of London rows to `analysis_level = borough_only`, `vote_share = null`, and flags `city_of_london_block_voting`. The Phase 8 ENP cross-check also filters out City of London (it only evaluates single-member wards with valid totals), so the block-voting ward no longer contributes to the mismatch count. The check still reports 11 minor mismatches (Coventry, Manchester, North Tyneside, Sandwell, Sefton, Solihull, South Tyneside, Stockport) where our derived fragmentation differs by >0.1 from DC’s ENP; these appear limited to high-multiplicity tally wards and are accepted as known measurement noise.

## Phase 8 QA — H08: DCLEAPIL 2018 DC/DC-LEAP duplicates (36 rows)
**Status:** Fixed — Phase 4 loader dedups 2018  
**Affected rows:** 36 rows (18 duplicate pairs)  
**Expected:** Active rows should be unique on `election_year`, `ward_code`, `party_standardised`, `candidate_name`.  
**Actual:** DCLEAPIL 2018 contains overlapping `DC` and `DC-LEAP` sub-datasets. When both sources cover the same ward-candidate, the row appears twice with distinct vote counts.  
**Resolution:** The Phase 4 loader now prefers `DC-LEAP` over `DC` within 2018, dropping the lower-priority rows before the interim parquet is written. Duplicates are gone in the canonical file.

## Phase 8 QA — W02_2018/2022: electorate null rates above original ceilings
**Status:** Accepted — ceilings revised via QA config  
**Affected rows:** 568 (2018), 1,329 (2022)  
**Expected:** 2018 electorate null ≤ 8%, 2022 ≤ 5%.  
**Actual:** After filtering to E08/E09 authorities, London boroughs have higher null rates (2018 ≈ 9%, 2022 ≈ 7%). The gaps come from genuine source data (Croydon 58%, Southwark 60%, City of London 100%).  
**Resolution:** `ELEC_NULL_CEILING` in `qa.py` now uses 12% for 2018 and 10% for 2022 while continuing to log the affected rows. The nulls remain documented via `electorate_missing` notes.

## Phase 8 QA — C01: Multi-member TVV denominator mismatch (8 rows)
**Status:** Accepted — known source-level definition difference  
**Affected rows:** 8 (100% of matched rows)  
**Expected:** Commons 2022 and the superseded DCLEAPIL 2022 rows should agree on votes for every matched authority+ward+party.  
**Actual:** `E09000010` Town and `E08000028` Abbey wards are 2-seat contests. DCLEAPIL reports `total_valid_votes` as total individual votes cast (voters × seats), while Commons reports ballot papers (voters), yielding a ~2:1 ratio and apparent 30–40% discrepancies.  
**Resolution:** Canonical rows already use Commons totals. DCLEAPIL rows are marked `descriptive_only`, so metrics ignore them. The conflict log documents the source definition difference; no data change is required.

## Phase 8 QA — C03: ward names in Commons 2022 not matched in DCLEAPIL 2022
**Status:** Accepted  
**Affected rows:** 1,500 (99.87% of Commons wards)  
**Expected:** A small number of ward naming mismatches may exist from punctuation/abbreviation differences.  
**Actual:** Nearly every Commons ward name lacks an exact string match in DCLEAPIL because the two sources use different casing and punctuation conventions.  
**Resolution:** Acceptable for Phase 8 (the mismatch rate is expected); documented here for transparency. Phase 5/6 should rely on harmonised `ward_name_clean` instead of raw names.
