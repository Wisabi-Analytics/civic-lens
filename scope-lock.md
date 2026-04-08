# Scope Lock

**Status:** LOCKED — committed March 2026  
**Locked by:** Max Obi / Wisabi Analytics  
**Lock date:** March 2026  
**Version:** 1.1 (calibration chain updated from 2018→2022→2025 to 2014→2018→2022)

Once committed, this document governs all project decisions. Changes require a new commit with explicit rationale.

---

## Geographic Tiers

| Tier | Scope | Councils | Granularity | Status |
|---|---|---|---|---|
| Tier 1 — Primary | 32 Metropolitan Boroughs (election-active only) | See exclusions below | Borough-level only | LOCKED |
| Tier 2 — Contrast | 32 London Boroughs | All 32 | Borough-level only — NO ward analysis | LOCKED |
| Tier 3 — Deep Dive | 5 Yorkshire councils (selected) | Leeds, Bradford, Calderdale, Kirklees, Wakefield | Ward-level where harmonised, borough fallback | LOCKED |
| Mayoral Context Layer | 10 Combined Authority Mayors | All 10 | **Descriptive only — EXCLUDED from volatility system** | LOCKED |

---

## Metropolitan Borough Scope (Tier 1) — Detail

England has **36 metropolitan boroughs** in total. Only **32 hold elections in May 2026**.

**Four excluded — no 2026 election:**

| Council | Reason |
|---|---|
| Doncaster | No election in 2026 |
| Liverpool | No election in 2026 |
| Wirral | No election in 2026 |
| Rotherham | No election in 2026 |

These councils are excluded solely because no election occurs. They are not excluded on data quality grounds.

---

## All-Out Election Flag (Confirmed 2026)

**Six in-scope authorities are flagged `all_out_2026` in 2026** (full council elected, not the usual staggered cycle):
- Barnsley (`E08000016`)
- Birmingham (`E08000025`)
- St Helens (`E08000013`)
- Coventry (`E08000026`)
- Calderdale (`E08000033`)
- Kirklees (`E08000034`)

For all six authorities:
- `analysis_level = borough_only` in `clean_election_results.csv`
- Ward-level longitudinal comparisons are NOT attempted
- Concordance table includes boundary change type = `all_out_lgbce`
- Listed in `docs/DECISIONS_LOG.md`

---

## Mayoral Context Layer — Explicit Exclusion from Volatility System

All 10 combined authority mayoral elections in 2026 are **newly-established roles**. No prior election exists.

**Therefore:**
- ❌ No volatility metrics computed
- ❌ No backtest calibration
- ❌ No Monte Carlo scenarios
- ❌ Not included in composite system outputs

**Instead (descriptive only — separate pipeline):**
- ✅ Vote share distribution per candidate
- ✅ Turnout levels
- ✅ Candidate field fragmentation (descriptive FI, not calibrated)
- ✅ Cross-authority comparative patterns
- ✅ Published in `reports/` as standalone contextual analysis

**Statement for all public outputs:** *"Mayoral elections are excluded from the volatility measurement system due to the absence of a historical baseline. They are included as contextual civic analysis only."*

See: `docs/MAYORAL_CONTEXT_LAYER.md`

---

**All other exclusions:** Scottish Parliament, Welsh Senedd, all ward-level analysis outside Yorkshire, cross-UK expansion.

---

## Data Years

| Year | Purpose | Status |
|---|---|---|
| 2014 | Training window — by-thirds cohort year | REQUIRED |
| 2015 | Training window — by-thirds cohort year | REQUIRED |
| 2016 | Training window — by-thirds cohort year | REQUIRED |
| 2018 | Backtest origin (training endpoint) | REQUIRED |
| 2021 | Completeness only — excluded from chain | NOT IN PIPELINE |
| 2022 | Backtest target and prediction baseline | REQUIRED |
| 2025 | Not used — no in-scope boroughs held elections | NOT IN PIPELINE |
| 2026 | Live ingestion (election night) | LIVE PIPELINE |

**Calibration chain:** 2014→2018 (train) / 2018→2022 (backtest, measure error) / 2022→2026 (predict). 2021 falls between backtest origin and target — excluded by chain design. 2025 not used: county council fallow year for by-thirds metro districts.

---

## Six Metrics — LOCKED

1. **Vote Share Swing** — `Δ% = VS_t − VS_(t-1)`
2. **Turnout Delta** — `ΔT = T_t − T_(t-1)`
3. **Fragmentation Index** — `FI = 1 / Σ(VS²)` (HHI)
4. **Seat Change** — `ΔS = Seats_t − Seats_(t-1)`
5. **Volatility Score** — `VOL = (0.5 × Σ|swing_i|) + (0.5 × ΔFI)` — equal weight, not normalised (VOL to avoid VS collision)
6. **Swing Concentration** — `SC = max(|swing|) / mean(|swing|)`

**Rule:** No additional metrics are added after this commit.

---

## Six Scenarios — LOCKED after Phase B commit

| ID | Name | Definition |
|---|---|---|
| S0 | Baseline | Uniform swing = 0pp — all parties hold their 2022 vote shares |
| S1 | High volatility continuation | Challenger +2pp; established −2pp |
| S2 | Partial recovery | Established +1.5pp; challenger −1.5pp |
| S3 | Challenger surge | Challenger +4pp; established −4pp |
| S4 | Deprivation turnout shift | ΔT +3pp in IMD deciles 1–3, vote share unchanged |
| S5 | Stability reversion | VI capped at empirical London 90th pctile — or REMOVED |

**Challenger definition:** Party with highest absolute VS swing gain in the **2018→2022** transition in that borough.  
**Tie-break:** Higher 2022 absolute vote share.  
**Independents:** Pooled as `IND`. Treated as challenger if they meet the swing criterion.

**Rule:** No scenarios added after Phase B freeze commit.

---

## Explicit Exclusions

- ❌ Scottish Parliament / Welsh Senedd elections
- ❌ National polling data integration
- ❌ Social media sentiment
- ❌ Economic indicator overlays
- ❌ ML / deep learning modelling
- ❌ Demographic regression (IMD is descriptive overlay only)
- ❌ Ward-level analysis outside Yorkshire Tier 3
- ❌ Cross-borough swing correlation in Monte Carlo
- ❌ More than 6 scenarios
- ❌ More than 12 total dashboard charts (4 per publication)

---

## Publication Dates

| Output | Target Date | Hard Constraint |
|---|---|---|
| Part 1 — Historical Baseline | 25 March 2026 | Shifts to 1 April if Phase A misses 8 Mar gate |
| Part 2 — Scenarios & Uncertainty | 14 April 2026 | Fixed |
| Model Lock | 30 April 2026 | Absolute. No exceptions. |
| Part 3 — Accuracy Report | 9 May 2026 (within 48hrs) | Absolute. Never moves. |

---

## Pre-Authorised Fallback Triggers

| Date | Condition | Action |
|---|---|---|
| Phase 7 | >40% of in-scope wards unmatched in concordance table | Borough-only fallback applied across all affected authorities — ward-level analysis abandoned |
| Phase 8 | QA failures exceed 5% of in-scope rows | Hold pipeline; investigate before proceeding to Phase 9 |
| Phase B | London VI 90th pctile not derivable | S5 removed entirely |
| Phase B | Any scenario interval P10>P50 or P50>P90 | Reduce to 4 scenarios (drop S3 + S5) |
| Phase A (ongoing) | EC files schema mismatch or missing fields | Activate EC_PLAN_B_PROTOCOL.md |

---

## Model Parameters

- Monte Carlo iterations: **2,000 per scenario per borough**
- Uncertainty bands: set from **measured backtest RMSE** — not assumed
- Output format: **P10/P50/P90** — single-point estimates never published

---

## Signed Off

- [x] Tiers confirmed
- [x] Councils listed by name
- [x] Metrics defined with formulas
- [x] Scenarios named and locked
- [x] Exclusions listed
- [x] Publication dates confirmed
- [x] Committed to GitHub
