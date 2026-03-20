# Methodology

**Status:** Updated March 2026 — calibration chain revised from 2018→2022→2025 to 2014→2018→2022. All affected sections rewritten.

---

## Calibration Chain

The project uses a three-stage empirical calibration chain:

```
TRAINING WINDOW        BACKTEST                PREDICTION
2014 → 2018            2018 → 2022             2022 → 2026
(compute metrics)  →   (measure forecast  →    (apply calibrated
                        error vs actuals)        uncertainty bands)
```

**Training window (2014–2018):** The three by-thirds election years immediately preceding the 2018 endpoint (2014, 2015, 2016) form the training window. Because metro and London boroughs elect by thirds, each ward is contested once every three years — its training data point is its most recent result from the {2014, 2015, 2016} cohort, as assigned by the concordance table.

**Backtest (2018→2022):** The trained model's predictions for the 2018→2022 transition are compared against the actual 2022 results. Forecast error (RMSE, MAE, P10–P90 empirical coverage) is measured borough by borough across all in-scope Tier 1, Tier 2, and Tier 3 authorities. This produces an empirically grounded, borough-specific error distribution.

**Prediction (2022→2026):** The calibrated error distributions are used to generate uncertainty bands for 2026 via bootstrap sampling (N = 2,000 iterations, RNG seed = 20260430).

**All three tiers are calibrated from the same backtest.** No cross-tier proxy transfer is required. No 2025 data is used at any stage of the chain.

---

## Year Inclusion and Exclusion

**2014, 2015, 2016** — included as training window. Pre-2019 data is sourced from LEAP only (Democracy Club data does not begin until 2019). Electorate and turnout coverage is degraded relative to post-2019 data. By-election coverage is incomplete pre-2016. These limitations are stated explicitly and do not invalidate the training window — they widen the uncertainty intervals appropriately where data is sparse.

**2018** — training window endpoint and backtest origin. Post-Brexit referendum, pre-Boris Johnson. Both LEAP and early Democracy Club data contribute.

**2021** — excluded entirely. It falls between the backtest origin (2018) and the backtest target (2022) and plays no structural role in the chain. Its exclusion is a consequence of the chain design, not a judgement call. The pandemic distortion is a secondary reason, consistent with the primary one.

**2022** — backtest target. The most recent fully observed election cycle for all in-scope tiers. Primary source: Commons Library Local Elections 2022, cross-checked against DCLEAPIL.

**2025** — not used. No in-scope metro or London boroughs held elections in 2025 (2025 was the county council fallow year for by-thirds metropolitan districts). Calderdale held a 2025 by-thirds election but is not used as a standalone calibration source — a single borough cannot produce a generalisable error distribution. The Commons Library 2025 file is retained in `data/raw/` for provenance but is not loaded in the pipeline.

---

## Metric Definitions

Six metrics — formulas frozen at Phase 0 commit. See `README.md`.

**Critical distinction on Seat Change:**
`seat_change()` is computed from realised historical data only. Scenario simulations do not project seats — they produce distributions of volatility metrics under stated assumptions.

---

## Scenario Definitions

Six scenarios (S0–S5) frozen in `docs/SCENARIO_DEFINITIONS.md`.

**Challenger party definition:** The party with the highest absolute swing gain in the **2018→2022** transition per borough. This is the most recent available cycle. Tie-break: higher 2022 absolute vote share. IND candidates are pooled before challenger identification.

---

## Ward Harmonisation

The concordance table spans three ward code vintages: the 2014/2016 ONS vintage (training window), the Dec 2018 vintage (backtest origin), and the May/Dec 2022 vintage (backtest target). The extended 8–12 year boundary window means more wards fall to borough-only fallback than a 4-year window would produce. This is expected and correct. Borough-level fallback is the safe default; ward-level comparison is the exception that requires explicit justification.

`analysis_level` field in `clean_election_results.csv` records the effective granularity for every row.

Full harmonisation decisions: `data/processed/DATA_DICTIONARY.md`

---

## Monte Carlo Simulation

**Iterations:** 2,000 per scenario per borough (frozen).

**Bootstrap source:** Borough-specific forecast error distributions from the 2014→2018 / 2018→2022 backtest. For boroughs with insufficient history (< 2 usable cycles, e.g. recently reorganised authorities), fall back to tier-level pooled distribution. Every fallback case is documented in `artifacts/calibration_report.md`.

**Independence assumption:** Boroughs simulated independently. No cross-borough correlation modelled.

**Output format:** P10/P50/P90 metric distributions. Seat projections not produced.

---

## Limitations

*Every limitation is disclosed here before it can be discovered externally.*

**1. LEAP-only era training data quality (2014/2015)**

The 2014 and 2015 training years draw on LEAP-only data — Democracy Club data begins contributing in 2016. Electorate and turnout fields have materially higher null rates in 2014/2015 than in 2016+ data. By-election coverage is incomplete pre-2016. Affected rows are flagged `data_source_era = leap_only` in the canonical schema. QA thresholds are set separately for these rows. The consequence is wider uncertainty intervals for boroughs whose training data has significant coverage gaps — this is the appropriate and honest outcome.

**2. Political context: Brexit-era training window**

The training window (2014–2018) straddles the Brexit referendum (June 2016) and the associated realignment of the English political landscape. Party competition patterns in this period — notably the UKIP surge and subsequent collapse, the Labour Corbyn era, and the Lib Dem post-coalition recovery — are structurally different from the Reform/Green/independent surge dynamics observable in 2022–2026. The backtest measures how well 2014→2018 patterns predict 2018→2022, but the 2022→2026 prediction is applied to a political environment with further structural differences that the calibration window does not capture.

**Consequence:** Uncertainty bands may understate right-wing volatility in 2026, particularly in areas with high 2025 Reform support. The direction of this potential bias is stated in advance and tested explicitly in the Part 3 accuracy audit.

**All publications referencing 2026 uncertainty bands must include:**

> *"Uncertainty bands are calibrated from borough-specific forecast errors measured across the 2014→2022 window (training: 2014→2018; backtest: 2018→2022). The training period predates the 2025 Reform surge. Uncertainty bands may understate right-wing volatility in areas of high recent Reform support. This is a stated assumption, not an observed measurement."*

**3. Borough-level fallback rate**

The extended 8–12 year concordance window produces a higher rate of borough-level fallback (where ward boundaries changed materially between 2014 and 2022) than a 4-year window would. Ward-level analysis is more granular; borough-level fallback is honest. The concordance table documents every downgrade decision.

**4. Boroughs with insufficient calibration history**

Authorities that have undergone significant reorganisation or had all-out LGBCE elections within the training window may not have two complete comparable cycles. These fall back to tier-level pooled error distributions, documented in `artifacts/calibration_report.md`.

**5. Calibration quality is what it is**

If the 2014→2018 model produces poor predictions of 2018→2022 outcomes, the calibration report says so. Wide uncertainty bands are the correct response to poor calibration — not model tuning. The bands reported in Part 2 are the direct output of what the data supports, not a target width chosen for presentational reasons.

---

## Required Publication Disclosures

**Part 1 (Historical Baseline):** State that the baseline covers two cycles (2014→2018 and 2018→2022) and that the 2014/2015 training years use LEAP-only data with degraded electorate and turnout coverage.

**Part 2 (Scenarios and Uncertainty):** State the calibration chain explicitly. Include the political context caveat above verbatim. State that all tiers are calibrated from the same empirical backtest with no cross-tier proxy transfer.

**Part 3 (Accuracy Audit):** Include verbatim: *"Model frozen 30 April 2026 to prevent adaptive tuning."* Test the Brexit-era bias hypothesis explicitly. Report honestly regardless of outcome.