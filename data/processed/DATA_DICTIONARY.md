# Civic Lens — Data Dictionary

**Version:** Phase 2 (March 2026)  
**Status:** Frozen — no field changes after Phase 2 exit without a DECISIONS_LOG entry  
**Applies to:** `data/processed/clean_election_results.csv`

---

## Canonical Schema — `clean_election_results.csv`

One row per candidate per ward per election year. All sources (DCLEAPIL 2014–2022, Commons Library 2022) are mapped to this schema before any metric computation begins.

---

### Identity Fields

| Field | Type | Nullable | Description |
|---|---|---|---|
| `election_year` | int | No | Year of election. In-scope values: 2014, 2015, 2016, 2018, 2022. |
| `election_date` | date (ISO 8601) | No | Exact polling date. e.g. `2022-05-05`. Derived from year where source provides year only. |
| `source_dataset` | str | No | Which source file this row originated from. Values: `dcleapil_2014`, `dcleapil_2015`, `dcleapil_2016`, `dcleapil_2018`, `dcleapil_2022`, `commons_2022`. Where both DCLEAPIL and Commons 2022 cover the same ward-party-year, `commons_2022` is the canonical row and the DCLEAPIL row is flagged `notes = 'superseded_by_commons_2022'`. |
| `data_source_era` | str | No | Coverage quality flag. `leap_only`: 2014/2015 — LEAP-sourced only, materially degraded electorate/turnout coverage. `dc_leap`: 2016+ — Democracy Club and LEAP merged, improved coverage. Derived from `election_year` (≤2015 → `leap_only`; ≥2016 → `dc_leap`). |

---

### Authority Fields

| Field | Type | Nullable | Description |
|---|---|---|---|
| `authority_code` | str | No | ONS LAD code. Format: `E08xxxxxx` (metro borough), `E09xxxxxx` (London borough), `E08000032–036` (West Yorkshire). Primary join key for authority-level aggregation. |
| `authority_name` | str | No | Standardised council name aligned to ONS LAD23 name. Source names (e.g. DCLEAPIL `council` field) are mapped to ONS canonical form. |
| `authority_type` | str | No | `metropolitan_borough` (Tier 1), `london_borough` (Tier 2), `west_yorkshire_mb` (Tier 3). Derived from `authority_code` prefix — never from DCLEAPIL `type` field. |
| `region` | str | No | ONS region name. Joined from `lad_region_lookup_apr2023.csv` via `authority_code`. |
| `tier` | int | No | 1 (metro boroughs), 2 (London boroughs), 3 (West Yorkshire). |

---

### Ward Fields

| Field | Type | Nullable | Description |
|---|---|---|---|
| `ward_name_raw` | str | No | Ward name exactly as it appears in the source file. Preserved for audit trail. Never used as a join key. |
| `ward_name_clean` | str | No | Standardised ward name. Rules: strip leading/trailing whitespace, normalise `&` vs `and` variants, normalise apostrophes, title case. Used for name-based concordance matching in Phase 7. |
| `ward_code` | str | Yes | ONS ward code. Source: DCLEAPIL `GSS` field. Null in ~0.2% of 2016 rows. DCLEAPIL assigns the most recent available code regardless of election year — codes reflect Dec 2018-era boundaries for most pre-2018 rows. **Concordance chain consequence of null `ward_code`:** any row where `ward_code` is null cannot be matched in the three-vintage concordance table (Phase 7) and must be assigned `harmonisation_status = fallback` and `analysis_level = borough_only`. The ~0.2% null rate in 2016 is small enough to treat as borough fallback without material effect on metric coverage. |
| `ward_code_vintage` | str | Yes | ONS vintage of the ward code. Values: `WD18CD` (for most training window rows — DCLEAPIL assigns modern codes), `WD22CD` (2022 data). Null where `ward_code` is null. Required for three-vintage concordance table (Phase 7). |

---

### Candidate Fields

| Field | Type | Nullable | Description |
|---|---|---|---|
| `candidate_name` | str | No | Full name. Concatenated from `first_name` + `surname` (DCLEAPIL) or `Candidate name` (Commons Library). |
| `party_raw` | str | No | Party label exactly as it appears in the source. Never modified. |
| `party_id` | str | Yes | EC registration code. Source: DCLEAPIL `party_id` (format `PPnnn`). Null for Commons Library rows where party_id not supplied. |
| `party_standardised` | str | No | Canonical party label for metric computation. Derived from `party_id` → `EC_Ref1` join to `DCLEAPIL_v1_0_Party_coding.csv`. For Commons Library rows: derived from `Party ID` column. Three unmatched DCLEAPIL values: `NR_Ind` and `NR_IndLR` → `IND`; `joint-party:15-64` → `IND_LOCAL`. |
| `party_group` | str | No | Simplified grouping for scenario engine. Source: `Type2` field from party coding. Values: `Major`, `Minor`, `ILP`, `Independent`. |
| `is_ilp` | bool | No | True if the candidate's party is an Independent Local Party. Source: `ILP` field from party coding. Required for challenger identification in S1/S3 scenarios. |

---

### Result Fields

| Field | Type | Nullable | Description |
|---|---|---|---|
| `votes` | int | Yes | Votes cast for this candidate. Null only for uncontested wards (single candidate, no formal count). Source: DCLEAPIL `votes_cast` (after comma-strip and numeric cast); Commons Library `Votes`. |
| `vote_share` | float | Yes | Candidate's share of total valid votes in the ward, expressed as a percentage (0–100). **Always derived as `(votes / total_valid_votes_in_ward) * 100` — never taken directly from DCLEAPIL `vote_share` field**, which is null for non-top-vote candidates in multi-member wards. Null only for uncontested wards. |
| `total_valid_votes` | int | Yes | Total valid votes cast in the ward across all candidates. Source: DCLEAPIL `turnout_valid`; Commons Library `Total valid votes`. Used as denominator for `vote_share` derivation. |
| `elected` | bool | No | True if the candidate was elected. Source: DCLEAPIL `elected` field (`t`/`f`); Commons Library `Elected` column. |
| `seats_contested` | int | No | Number of seats up for election in this ward. Source: DCLEAPIL `seats_contested_calc`; Commons Library `Vacancies` (2022). Values: 1, 2, or 3. **`seats_contested_calc = 0` rows (4 rows, Tewkesbury 2014, Lower Tier) are out of scope and dropped at Phase 4.** |
| `seats_won` | int | No | 1 if elected, 0 otherwise. Derived from `elected`. Not the same as seats_won per party (which is a ward-level aggregate computed at Phase 9). |

---

### Turnout and Electorate Fields

| Field | Type | Nullable | Description |
|---|---|---|---|
| `electorate` | int | Yes | Registered electorate for the ward. Nullable — higher null rate in `leap_only` years (2014: 4.1%, 2015: 6.5%). Source: DCLEAPIL `electorate`; Commons Library `Electorate`. |
| `turnout_pct` | float | Yes | **Per-elector turnout percentage (0–100), corrected for multi-member wards.** Derivation: `(total_valid_votes / seats_contested) / electorate * 100`. This correction is necessary because DCLEAPIL `turnout_valid` = total votes cast (all candidates), which exceeds electorate in multi-member wards. Commons Library `Turnout (%)` is already per-elector — no correction needed. Null where `electorate` is null. After correction, assert `turnout_pct <= 100` and `turnout_pct >= 1`. Rows outside this range are flagged in `notes` and reviewed in Phase 8 QA. |

---

### Analysis and Harmonisation Fields

| Field | Type | Nullable | Description |
|---|---|---|---|
| `analysis_level` | str | No | Effective granularity of analysis for this row. Values and precedence: `ward` (full ward-level comparison defensible), `borough_fallback` (ward boundary changes prevent direct comparison — borough aggregate used), `borough_only` (ward comparison structurally not possible: uncontested, all-out LGBCE election, or major boundary change), `descriptive_only` (authority included for narrative context only — not in metric computation). Set definitively at Phase 7 concordance. Provisional values set at Phase 5. **LGBCE all-out elections (2026):** 13 of the 32 Tier 1 metro boroughs hold all-out elections in May 2026 due to LGBCE boundary reviews (listed in `docs/DECISIONS_LOG.md`). Every row belonging to one of those 13 authorities must be assigned `analysis_level = borough_only` and `concordance_change_type = all_out_lgbce` during Phase 7, regardless of whether a matching ward code exists in the concordance table. The same rule applies to any Tier 3 authority that undergoes an all-out review. This assignment is set in Phase 7 from the scope-lock list — it is not derived from the data. |
| `harmonisation_status` | str | No | Concordance outcome for this ward across the calibration chain. Values: `matched` (exact ONS code match across cycles), `name_matched` (cleaned name match within same LAD), `reviewed` (manual fallback, documented), `fallback` (borough-level fallback applied). Set at Phase 7. |
| `concordance_change_type` | str | Yes | Boundary change classification from Phase 7. Values: `stable`, `split`, `merge`, `all_out_lgbce`, `unmatched`. Null for rows not in the concordance window. |

---

### Audit Fields

| Field | Type | Nullable | Description |
|---|---|---|---|
| `notes` | str | Yes | Free-text anomaly or caveat flag. Multiple flags separated by ` | `. Expected values: `uncontested`, `multi_member`, `vote_share_derived`, `turnout_corrected`, `superseded_by_commons_2022`, `boundary_fallback`, `electorate_missing`, `turnout_missing`. |

---

## Edge Case Handling Rules

These rules are non-negotiable. Any deviation requires a DECISIONS_LOG entry.

### 1. Multi-member wards (seats_contested > 1)

Present in all years. 37,308 rows in training data (49% of total).

- `vote_share` is **always derived** from `votes / total_valid_votes * 100`. Never use DCLEAPIL `vote_share` directly — it is null for all candidates except the highest-vote party candidate in multi-member wards.
- `turnout_pct` is **always corrected** as `(total_valid_votes / seats_contested) / electorate * 100`.
- `seats_won` = 1 if `elected = True`, else 0 (per candidate row).
- Ward-level `seats_won` by party = sum of `seats_won` per `party_standardised` per ward per year. Computed at Phase 9, not stored in the canonical schema.
- Flag all multi-member rows with `notes = 'multi_member'`.

### 2. Uncontested wards (single candidate, no formal count)

157 rows in training data (predominantly 2015: 143 rows).

- `votes` may be present (declared uncontested with count) or null (no count held).
- `vote_share` = null (cannot be meaningfully computed).
- `analysis_level` = `borough_only`.
- `notes` = `'uncontested'`.
- Do not exclude from the dataset — include with these flags. Borough-level metrics remain valid.

### 3. Source conflict: DCLEAPIL vs Commons Library 2022

Where both sources cover the same ward-party-year:

- **Commons Library 2022 is canonical.** Use it as the primary row.
- DCLEAPIL 2022 row is retained as `notes = 'superseded_by_commons_2022'` and excluded from metric computation (flagged `analysis_level = descriptive_only`).
- Log all material discrepancies (vote count differences > 1%) in Phase 8 QA.

### 4. Turnout > 100% after correction

If `turnout_pct > 100` after the multi-member correction, the ward has data quality issues (likely incorrect `electorate` field). Flag `notes = 'turnout_over_100_post_correction'` and set `analysis_level = borough_only`. Do not exclude — the borough-level aggregate may still be usable.

### 5. Independents and ILP candidates

All candidates have a `party_id` — no null values observed. Standardisation path:

- `NR_Ind`, `NR_IndLR` → `party_standardised = 'IND'`, `party_group = 'Independent'`, `is_ilp = False`
- `joint-party:15-64` → `party_standardised = 'IND_LOCAL'`, `party_group = 'ILP'`, `is_ilp = True`
- All `Type2 = ILP` parties → `is_ilp = True`

For Fragmentation Index: all ILP and Independent candidates are treated as separate parties (not pooled) unless they share an identical `party_standardised` label within the same ward-year.

### 6. Turnout source inconsistency between DCLEAPIL and Commons Library 2022

DCLEAPIL `turnout_percentage` = `turnout_valid / electorate * 100` (total votes / electorate, may exceed 100% in multi-member wards).

Commons Library 2022 `Turnout (%)` = valid votes / (electorate × seats) effectively — already per-elector, never exceeds 100%.

**Pipeline always uses the corrected derivation:** `turnout_pct = (total_valid_votes / seats_contested) / electorate * 100`. This produces consistent values from both sources.

### 7. Commons Library 2021 accidental candidate columns

The `Wards-results` sheet in `local_elections_2021.xlsx` contains two columns that are not genuine party vote columns: `GREEN ACCIDENTAL CANDIDATE` and `LAB ACCIDENTAL CANDIDATE`. Both are nearly entirely zero (3,862 of 3,863 rows are 0) but are structurally present. The Phase 4 loader **must explicitly drop these two columns before the wide-to-long party pivot** — if left in, the pivot will create spurious `GREEN ACCIDENTAL CANDIDATE` and `LAB ACCIDENTAL CANDIDATE` party entries in the canonical schema, polluting `party_raw` and `party_standardised` downstream.

Drop rule: before pivoting `Wards-results`, apply a column exclusion list: `['GREEN ACCIDENTAL CANDIDATE', 'LAB ACCIDENTAL CANDIDATE']`. These are 2021-specific — no equivalent columns exist in the 2022 ward sheet. Note that 2021 is not in the calibration chain (completeness/contextual only), so this edge case affects only any code that processes the 2021 file.

---

## Metric Definitions (Frozen)

| Metric | Symbol | Formula | Notes |
|---|---|---|---|
| Vote Share Swing | — | `Δ% = VS_t − VS_(t-1)` | Per party, per ward or borough. Positive = gain, negative = loss. |
| Turnout Delta | — | `ΔT = T_t − T_(t-1)` | In percentage points. Uses corrected `turnout_pct`. |
| Fragmentation Index | `FI` | `FI = 1 / Σ(VS_i²)` | VS expressed as proportions (0–1), not percentages. Computed from independently derived `vote_share`. ILP and IND treated as distinct parties. Min value = 1 (one-party ward). |
| Seat Change | — | `ΔS = Seats_t − Seats_(t-1)` | Historical data only. Never simulated. |
| Volatility Score | **`VOL`** | `VOL = (0.5 × Σ\|swing_i\|) + (0.5 × ΔFI)` | The Pedersen index variant. Swing summed over all parties. ΔFI is first-difference of FI. |
| Swing Concentration | `SC` | `SC = max(\|swing_i\|) / mean(\|swing_i\|)` | High SC = one party driving volatility. Low SC = broad-based shift. Undefined where all swings = 0 — set `SC = 1.0` in that case. |

`VS` = vote share (proportion, 0–1 in formulas). `VOL` = volatility score. These abbreviations do not overlap.

**FI computation note:** FI is computed from `votes / total_valid_votes` (i.e. re-derived from raw vote counts), not from the stored `vote_share` field. This ensures consistency in multi-member wards where `vote_share` may be null for some candidates.

---

## Source-to-Schema Field Mapping

| Canonical field | DCLEAPIL source field | Commons Library 2022 source field |
|---|---|---|
| `election_year` | `year` | Derived from sheet / `Year` column |
| `authority_code` | Derived via GSS → ward-LAD lookup | `Local authority code` |
| `authority_name` | `council` (standardised) | `Local authority name` (standardised) |
| `ward_name_raw` | `ward` | `Ward name` |
| `ward_code` | `GSS` | `Ward code` |
| `candidate_name` | `first_name` + `surname` | `Candidate name` |
| `party_raw` | `party_name` | `Party name` |
| `party_id` | `party_id` | `Party ID` |
| `votes` | `votes_cast` (after comma-strip and int cast) | `Votes` |
| `vote_share` | **Derived** from `votes_cast / turnout_valid * 100` | **Derived** from `Votes / Total valid votes * 100` |
| `total_valid_votes` | `turnout_valid` | `Total valid votes` |
| `elected` | `elected` (`t`/`f` → True/False) | `Elected` |
| `seats_contested` | `seats_contested_calc` | `Vacancies` |
| `electorate` | `electorate` | `Electorate` (from Wards-results sheet) |
| `turnout_pct` | **Derived**: `(turnout_valid / seats_contested) / electorate * 100` | `Turnout (%)` (already per-elector — no correction) |
| `data_source_era` | Derived from `year` (≤2015 → `leap_only`) | Always `dc_leap` |
| `source_dataset` | `dcleapil_{year}` | `commons_2022` |