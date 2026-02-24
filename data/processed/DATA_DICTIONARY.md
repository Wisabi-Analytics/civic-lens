# Data Dictionary

**Status:** Populated during Phase A (Task A9). Do not edit manually.

Every field in `clean_election_results.csv` is documented here.
Every harmonisation assumption is stated here.
Every boundary change decision is recorded here.

Boundary change rule:
> Councils with all-out elections or LGBCE boundary changes are handled at borough aggregate only.
> No ward-to-ward comparisons are claimed for these councils.

---

## clean_election_results.csv

| Field | Type | Description | Notes |
|---|---|---|---|
| `year` | int | Election year | 2018, 2022, 2025, 2026 |
| `borough` | str | Local authority name | Standardised from EC |
| `ward` | str | Ward name or `BOROUGH_AGG` | `BOROUGH_AGG` if borough-level only |
| `party` | str | Party label | Standardised: CON, LAB, LD, GRN, REF, IND, OTHER |
| `votes` | int | Raw vote count | From EC results |
| `vote_share` | float | Votes / total valid votes | Computed |
| `turnout` | float | Turnout % | Reported or computed from votes/electorate |
| `seats` | int | Seats won in ward/borough | From EC results |
| `analysis_level` | str | `ward`, `borough_only`, `borough_fallback`, `descriptive_only` | Set by harmonisation pipeline. `descriptive_only` = mayoral context layer |
| `boundary_note` | str | Empty string or explanation | Populated for: all-out election boroughs, mid-cycle boundary changes, ward fallback councils |
| `turnout_source` | str | `reported`, `computed`, `missing` | Audit trail |

---

*(Populated during Phase A)*

---

## All-Out Election Boroughs (Tier 1)

13 of 32 election-active metropolitan boroughs hold all-out elections in 2026 due to LGBCE boundary reviews. These are flagged as follows in `clean_election_results.csv`:

```
analysis_level  = borough_only
boundary_note   = "All-out election 2026 — LGBCE boundary review. No ward-level longitudinal analysis."
```

Concordance table (`concordance_table.csv`) entries for these councils:
```
change_type = all_out_lgbce
```

*(Exact list of 13 councils confirmed during Phase A data acquisition)*

---

## Excluded Metropolitan Boroughs (No 2026 Election)

The following four metropolitan boroughs are excluded from `clean_election_results.csv` entirely — no election occurs in 2026:

| Council | Reason |
|---|---|
| Doncaster | No election in 2026 |
| Liverpool | No election in 2026 |
| Wirral | No election in 2026 |
| Rotherham | No election in 2026 |

If 2022 or prior results for these councils are present in raw EC files, they are **not loaded** into the processed dataset. Their exclusion is documented here, not handled silently.

---

## Mayoral Context Layer

Mayoral elections have `analysis_level = descriptive_only`. They are stored in a **separate file**:

```
data/processed/mayoral_context.csv
```

Schema:

| Field | Type | Description |
|---|---|---|
| `year` | int | Election year (2026) |
| `combined_authority` | str | Combined authority name |
| `candidate` | str | Candidate name |
| `party` | str | Party label |
| `votes` | int | Raw vote count |
| `vote_share` | float | Votes / total valid votes |
| `turnout` | float | Turnout % |
| `result` | str | `elected` / `not_elected` |

**Not present:**
- `swing_pp` — no prior baseline
- `volatility_score` — not computed
- `fragmentation_delta` — not computed (single-cycle FI only)

Any attempt to join `mayoral_context.csv` with `clean_election_results.csv` on time-series metrics should be treated as a data error.
