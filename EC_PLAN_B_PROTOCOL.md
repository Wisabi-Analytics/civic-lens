# EC Data Plan B Protocol

**Status:** Active from Day 1. Consult this before any ad hoc data cleaning decision.  
**Rule:** Every data quality issue handled here has a documented response. Nothing is fixed silently.

---

## When to Use This Document

Consult this protocol whenever `data_inventory.csv` flags any of the following:

- Missing columns in EC results files
- Schema differences between years
- Ward names that break joins
- Missing turnout fields
- Unexpected row counts

---

## Response Rules by Issue Type

### 1. Missing turnout field

**Response:**
- Compute from `votes / electorate` where electorate field is present. Flag `turnout_source = computed`.
- If electorate is also missing: set `turnout = null`, flag `turnout_source = missing`.
- Document in `DATA_DICTIONARY.md`. Never impute silently.

### 2. Column schema mismatch between years

**Response:**
- Map columns to the standard schema defined in `DATA_DICTIONARY.md`.
- Document the mapping in `EC_schema_mapping.csv`: `year, original_column_name, mapped_to, notes`.
- If a required field has no mapping: treat as missing (see above).

### 3. Ward names break join

**Response:**
- Apply the concordance table (`concordance_table.csv`) first.
- If name still unresolved after fuzzy match (rapidfuzz score <90): escalate to manual review.
- If manual review fails: set `analysis_level = borough_fallback` for that council-year.
- Add `boundary_note` field: *"Ward join failed for [council] [year]. Borough aggregate only. No ward-to-ward comparisons claimed."*

### 4. Councils with LGBCE boundary changes or all-out elections

**Response:**
- Handled at borough aggregate only.
- `analysis_level = borough_only` in `clean_election_results.csv`.
- `boundary_note` field populated.
- Statement in `DATA_DICTIONARY.md`: *"Councils with all-out elections or LGBCE boundary changes are handled at borough aggregate only. No ward-to-ward comparisons are claimed for these councils."*

### 5. Unexpected row counts (more or fewer rows than expected per council-year)

**Response:**
- Cross-reference against LGBCE boundary records to check ward count changes.
- If explained by boundary change: document and continue.
- If unexplained: flag in `validation_log.md`, do not proceed until resolved.

### 6. Missing results for a council-year entirely

**Response:**
- Check EC website manually for alternative download format.
- If unavailable: remove that council-year from scope. Document in `DATA_DICTIONARY.md`.
- Do not extrapolate or infer missing council-year data.

---

## Standard Schema

All years normalised to:

| Field | Type | Notes |
|---|---|---|
| `year` | int | Election year |
| `borough` | str | Local authority name |
| `ward` | str | Ward name or `BOROUGH_AGG` |
| `party` | str | Standardised party name |
| `votes` | int | Raw vote count |
| `vote_share` | float | Votes / total valid votes |
| `turnout` | float | Turnout % |
| `seats` | int | Seats won |
| `analysis_level` | str | `ward`, `borough_only`, `borough_fallback` |
| `boundary_note` | str | Empty string or explanation |
| `turnout_source` | str | `reported`, `computed`, `missing` |

---

## Party Name Standardisation

Standardise to these labels. Any other label maps to the nearest or to `OTHER`:

```
CON, LAB, LD, GRN, REF, IND, UKIP, OTHER
```

Multi-word independent groups: classify as `IND` unless they hold seats, in which case retain original name and flag for manual review.

---

## Commit Rule

Every fallback decision made under this protocol must be:
1. Recorded in `DATA_DICTIONARY.md`
2. Reflected in the `boundary_note` field of affected rows
3. Committed to GitHub with a message referencing this protocol

No silent fixes.
