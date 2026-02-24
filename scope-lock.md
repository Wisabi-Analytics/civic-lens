# Scope Lock

**Status:** DRAFT — fill in and commit before Phase A data acquisition begins.  
**Locked by:** [Your name]  
**Lock date:** [Date]  
**Version:** 1.0

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

## All-Out Election Flag (Tier 1)

**13 of the 32 election-active metropolitan boroughs hold all-out elections in 2026** due to LGBCE boundary reviews (full council elected, not the usual one-third).

For all 13 councils:
- `analysis_level = borough_only` in `clean_election_results.csv`
- Ward-level longitudinal comparisons are NOT attempted
- Concordance table includes boundary change type = `all_out_lgbce`
- Listed in `docs/DECISIONS_LOG.md`

*(Exact list of 13 councils to be confirmed during Phase A data acquisition)*

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
| 2018 | Baseline (pre-disruption baseline — clean) | REQUIRED |
| 2021 | Context only if needed | LOW PRIORITY |
| 2022 | Mid-point transition | REQUIRED |
| 2025 | Shock measurement | REQUIRED |
| 2026 | Live ingestion (election night) | LIVE PIPELINE |

**Baseline:** 2018→2022 transition. 2021 excluded from baseline — pandemic election with structurally suppressed turnout.

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
| S0 | Baseline | Uniform swing = 0pp from 2025 |
| S1 | High volatility continuation | Challenger +2pp; established −2pp |
| S2 | Partial recovery | Established +1.5pp; challenger −1.5pp |
| S3 | Challenger surge | Challenger +4pp; established −4pp |
| S4 | Deprivation turnout shift | ΔT +3pp in IMD deciles 1–3, vote share unchanged |
| S5 | Stability reversion | VI capped at empirical London 90th pctile — or REMOVED |

**Challenger definition:** Party with highest absolute VS swing gain in 2025 in that borough.  
**Tie-break:** Higher 2025 absolute vote share.  
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
| 3 March | <50% Yorkshire councils harmonised | London Tier 2 drops to contextual only |
| 8 March | Phase A not complete | Reduce Tier 1 to 10-borough sample |
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

- [ ] Tiers confirmed
- [ ] Councils listed by name
- [ ] Metrics defined with formulas
- [ ] Scenarios named (locked after Phase B)
- [ ] Exclusions listed
- [ ] Publication dates confirmed
- [ ] Committed to GitHub
