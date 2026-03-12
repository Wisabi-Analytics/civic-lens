# Methodology

**Status:** Populated during Phase B. Calibration findings added before Part 1 publication.

---

## Baseline Year

**2018** is the historical baseline. The 2018→2022 transition establishes "normal" electoral conditions.

**2021 is excluded from baseline calibration.** The 2021 local election cycle was materially distorted by the COVID-19 pandemic: suppressed turnout in many areas, cancelled contests, and abnormal party performance. Using 2021 as a baseline would conflate pandemic disruption with political realignment, making it impossible to isolate the 2025 shock cleanly.

2021 results are present in `data/raw/ec/` for completeness and are available for contextual analysis. They are not used in the core 2018→2022→2025 calibration chain.

Full rationale: `docs/DECISIONS_LOG.md`

---

## Metric Definitions

Six metrics — see `README.md` for formulas. Locked at Phase B commit.

**Critical distinction on Seat Change:**
`seat_change()` is computed from realised historical data only. It measures what actually happened. Scenario simulations do not project seats — they produce distributions of volatility metrics under stated assumptions. This distinction is deliberate and non-negotiable.

---

## Calibration Approach

1. Compute all six metrics for the 2018→2022 transition → `baseline_metrics.csv`
2. Use those metrics to model the 2022→2025 outcome
3. Compare modelled vs actual 2025 results → `backtest_results.csv`
4. Compute RMSE, MAE, P10–P90 coverage per metric per tier → `calibration_report.md`
5. Use measured borough-specific error to set all 2026 uncertainty bands

**Uncertainty bands are set from measured backtest error — never by assumption.**
Wide bands are honest. A poorly calibrated model produces wide bands. That is the correct and transparent outcome.

---

## Tier-Specific Calibration Limitation

**This is a material methodological constraint. It is disclosed here before it can be discovered externally.**

The three project tiers do not have equivalent calibration data:

| Tier | Last election before 2026 | 2025 data available | Direct backtest possible |
|---|---|---|---|
| Tier 1 — 32 Metropolitan Boroughs | May 2022 | ❌ No | ❌ No |
| Tier 2 — 32 London Boroughs | May 2022 | ❌ No | ❌ No |
| Tier 3 — 5 Yorkshire Councils | May 2025 | ✅ Yes | ✅ Yes |

Metropolitan and London borough councils did not hold elections in 2025. No 2025 ward-level results exist for Tiers 1 or 2 from any source.

**Consequence for uncertainty bands:**

- Tier 3 uncertainty bands are derived from a direct calibration backtest: 2018→2022 baseline used to predict 2022→2025, measured against actuals. The observed forecast errors form a borough-specific distribution, which is then used as the bootstrap source for 2026 uncertainty bands.
- Tier 1 and Tier 2 uncertainty bands **cannot** be derived this way. Instead, the Tier 3 forecast error distribution is used as a proxy uncertainty model for Tiers 1 and 2. The same distribution is bootstrap-sampled to produce their uncertainty bands.
- The logic is: Tier 3 → observed error distribution → bootstrap sampling → uncertainty bands. Tiers 1 & 2 → apply same error distribution → bootstrap sampling → uncertainty bands.
- This is a stated assumption, not an observed measurement. It treats the Yorkshire forecast error distribution as a reasonable proxy for what would have been observed in metro and London boroughs had 2025 data existed.

**This assumption may not hold.** London and metropolitan boroughs have different structural volatility characteristics to Yorkshire councils. The proxy error distribution may be wider or narrower than a direct backtest would have produced.

**Scaling diagnostic:** The Tier 3 error distribution is applied without scaling. Prior to use, diagnostic checks confirmed that baseline volatility levels in metropolitan and London boroughs fall within the same order of magnitude as the Yorkshire councils used for calibration. A gross mismatch in volatility scale would have triggered a documented decision on whether to scale or widen the proxy distribution. No such adjustment was required.

All publications referencing Tier 1 and Tier 2 uncertainty must include the following disclosure:

> *"Uncertainty bands for metropolitan and London boroughs use the Tier 3 (Yorkshire) forecast error distribution as a proxy uncertainty model, applied cross-tier via bootstrap sampling. No direct 2025 backtest is available for these tiers as no elections were held in 2025. This is a stated assumption, not an observed measurement."*

---

## Monte Carlo Simulation

**Iterations:** 2,000 per scenario per borough (frozen — do not increase).

**Bootstrap source:** Borough-specific historical error distributions from the calibration backtest. Each borough's swing distribution reflects its own historical volatility pattern. Boroughs with insufficient history (< 2 complete cycles) fall back to tier-level pooled distributions.

**Independence assumption:** Boroughs are simulated independently. No cross-borough correlation modelled. See `docs/SCENARIO_DEFINITIONS.md` for full rationale.

**Output format:** P10/P50/P90 metric distributions. Seat projections are not produced.

---

## Ward Harmonisation

Ward-level analysis applies only to Tier 3 Yorkshire councils. All other tiers use borough-level aggregation.

For councils with LGBCE boundary changes or all-out elections: borough aggregate only. No ward-to-ward comparisons are claimed. `analysis_level` field in `clean_election_results.csv` records the effective granularity for every row.

Full harmonisation decisions: `data/processed/DATA_DICTIONARY.md`

---

## Limitations

*(Populated during Phase A and B — every limitation disclosed here before it can be discovered externally)*

- Tier 1 and Tier 2 uncertainty bands transferred from Tier 3 calibration error — no direct 2025 backtest available. See Tier-Specific Calibration Limitation above.
- [Borough-level fallback councils to be listed after Phase A audit]
- [Harmonisation decisions to be listed after Phase A]
- [Calibration fit quality to be stated honestly after Phase B]