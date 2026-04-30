# Civic Lens — Scenario Definitions

**Status:** FROZEN at Phase 2. No scenario definition may be altered after this point without a `docs/DECISIONS_LOG.md` entry and a corresponding commit. The scenario engine (Phase 12) must implement these definitions exactly.

---

## Challenger Party Definition (Frozen)

**Challenger:** the party with the highest absolute vote share swing gain in the **2018→2022** transition per borough.

Computation:
1. Compute `swing_2018_2022 = vote_share_2022 − vote_share_2018` per party per borough (borough-level aggregate, not ward-level).
2. Challenger = `argmax(swing_2018_2022)` per borough.
3. **Tie-break:** higher 2022 absolute vote share.
4. **IND pooling:** all `party_group = 'Independent'` candidates are pooled as a single `IND` entry before challenger identification. ILP candidates are pooled separately as `ILP`.
5. **Established parties:** all parties that are not the challenger.

This definition uses 2018→2022 because it is the most recent complete observed cycle available across all tiers. No 2025 data is used in the pipeline.

**Critical implementation note — use derived vote shares only:** `vote_share_2022` and `vote_share_2018` must be taken from the `vote_share` field in `clean_election_results.csv`, which is always derived as `votes / total_valid_votes * 100`. The raw `vote_share` column in the DCLEAPIL source file is null for lower-ranked candidates in multi-member wards and must never be used directly. All swing calculations — in the challenger definition and in S0–S3 scenario shifts — operate on borough-level aggregates of the canonical derived percentages.

**Phase 10.5 party-family note:** Challenger and metric calculations use explicit analytical party-family keys. Labour and Labour Co-operative labels are one `LAB` family. UKIP, Brexit Party, and Reform UK labels are one `REFORM` family. For metric computation, distinct local and independent party labels remain separate unless their cleaned labels are identical. For challenger identification only, `party_group = 'Independent'` is pooled as `IND`, and `party_group = 'ILP'` is pooled separately as `ILP`.

---

## Frozen Simulation Parameters

| Parameter | Value |
|---|---|
| `RNG_SEED` | `20260430` |
| `N_ITERATIONS` | `2000` |
| Borough independence | Boroughs simulated independently. No cross-borough correlation. |
| Interval constraint | `P10 ≤ P50 ≤ P90` enforced. Invalid ordering fails validation. |
| Minimum interval width | No interval narrower than calibration RMSE permits. |
| Scenario removal order | If a scenario fails validation: remove S3 first, then S5. Log in DECISIONS_LOG. Do not patch. |

---

## Six Scenarios

### S0 — Baseline (0pp swing)

**Definition:** No swing applied. All parties hold their 2022 vote shares. Uncertainty bands from calibration only.

**What this represents:** Electoral stasis — the null hypothesis.

**Falsified by:** Any material party movement on election night.

---

### S1 — High Volatility Continuation

**Definition:** Challenger +2pp; all Established parties −2pp (distributed proportionally to their 2022 vote share).

**What this represents:** The 2018→2022 volatility pattern continues at the same rate into 2026.

**Challenger identification:** per borough, per the frozen definition above.

**Falsified by:** Challenger underperforms relative to 2022 trend, or Established parties recover.

---

### S2 — Partial Establishment Recovery

**Definition:** Established parties collectively +1.5pp; Challenger −1.5pp.

**What this represents:** A mean-reversion scenario — volatility partially unwinds as the challenger peak passes.

**Falsified by:** Challenger holds or extends 2022 gains.

---

### S3 — Challenger Surge

**Definition:** Challenger +4pp; all Established parties −4pp (distributed proportionally).

**What this represents:** An accelerated version of S1 — a larger swing than historically observed.

**Removal candidate:** S3 is the first scenario removed if validation fails (it produces the most extreme outputs and is most likely to violate interval constraints).

**Falsified by:** Challenger fails to exceed 2022 gains materially.

---

### S4 — Deprivation Turnout Shift

**Definition:** Turnout delta of +3pp applied to all wards in IMD deciles 1–3 (most deprived). Vote shares adjusted proportionally within those wards.

**IMD source:** `imd_2019_lad_summary.xlsx` — LAD-level IMD scores. Deciles derived via `pd.qcut` on rank field. IMD is a **descriptive overlay only** — it does not infer, adjust, or predict vote shares directly.

**Ward assignment:** Wards assigned to IMD deciles via their parent LAD's decile. Where a LAD spans decile boundaries, all wards in that LAD receive the same LAD-level decile assignment.

**Implementation note — ward→LAD join required:** Because the IMD source is LAD-level, applying the +3pp shock requires joining every ward row in `clean_election_results.csv` to its parent LAD via `authority_code` before the decile filter can be applied. The join path is: `ward → authority_code` (already on every row) → `pd.qcut`-derived decile on `imd_2019_lad_summary.xlsx`. The turnout adjustment is then applied as a delta on the canonical `turnout_pct` field (which is already corrected for multi-member wards).

**Phase 12 implementation caveat:** Phase 12 scenario outputs are borough-level. Until a ward-level scenario output layer exists, S4 is implemented as a turnout-only borough shock: `turnout_delta = +3pp` for authorities in IMD deciles 1-3, while vote-share-derived metrics copy S0 exactly.

**Falsified by:** No material turnout increase in high-deprivation wards, or turnout increase does not translate to vote share change.

---

### S5 — London Stability Reversion

**Definition:** London borough Volatility Index capped at the empirical 90th percentile derived from two historical cycles (2014→2018 and 2018→2022).

**Derivation:** Computed at Phase 10 from `training_metrics.csv` and `backtest_actuals_2022.csv`.

**Condition for inclusion:**
- If derivable from ≥ 20 London boroughs contributing to the distribution → write numeric cap to `artifacts/london_vi_cap.txt` and include S5.
- If not derivable → write `S5_REMOVED` to `artifacts/london_vi_cap.txt`, log removal in `docs/DECISIONS_LOG.md`, and remove S5 before Phase 12.

**Why the ≥ 20 threshold may not be met:** All 32 London boroughs are present in the raw election sources, making the threshold realistic in normal operation. However, Phase 8 QA may downgrade boroughs to `analysis_level = borough_only` for reasons other than missing data — specifically, LGBCE all-out elections or widespread uncontested seats in a given borough. A borough downgraded to `borough_only` can still contribute to the S5 VI cap distribution because the cap is computed at borough level, not ward level. The threshold failure scenario is therefore limited to cases where 13 or more London boroughs are entirely excluded from the processed dataset, which would represent a catastrophic data quality failure flagged well before Phase 10. If Phase 8 QA passes with all 32 London boroughs present at any `analysis_level`, S5 derivation will succeed.

**Removal candidate:** S5 is the second scenario removed if validation fails after S3 is already removed.

**Falsified by:** London boroughs exceed the historical 90th percentile cap on election night.

---

## Scenario Output Format

For each scenario × borough × metric combination, the simulation outputs:

| Field | Description |
|---|---|
| `scenario_id` | `S0` through `S5` |
| `authority_code` | ONS LAD code |
| `metric` | Phase 12 emits `turnout_delta`, `delta_fi`, `volatility_score`, `swing_concentration` (Seat Change is historical only — not simulated) |
| `P10` | 10th percentile of simulated distribution |
| `P50` | 50th percentile (median) |
| `P90` | 90th percentile |

Seat projections are not produced under any scenario.

**Phase 12 output caveat:** `vote_share_swing` is omitted because there is no calibrated error distribution for that metric. `fragmentation_index` is not emitted as an absolute level; Phase 12 emits `delta_fi` because the calibrated backtest pool is `delta_fi_error`. `delta_fi` is also one component of `volatility_score`, so these fields should not be treated as independent evidence in publication analysis.
