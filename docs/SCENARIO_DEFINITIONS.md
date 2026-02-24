# Scenario Definitions

**Status:** FROZEN after Phase B commit. No modifications after freeze date.  
**Freeze recorded in:** `artifacts/model_lock.txt`

---

## Global Simulation Rules

**Borough independence:** Boroughs are simulated independently. No cross-borough swing correlation is modelled. Local elections are driven by borough-specific dynamics — candidate quality, local issues, council composition — that make national correlation assumptions unjustified at this geography. This is a deliberate, stated simplification.

**Bootstrap source:** Swing distributions are bootstrapped from **borough-specific historical error distributions** derived from the calibration backtest (2018→2022→predict 2025). Each borough's uncertainty reflects its own historical volatility. Boroughs with fewer than 2 complete election cycles fall back to the tier-level pooled distribution.

**Metric outputs only:** Scenario simulation produces P10/P50/P90 distributions of **volatility metrics only**. Seat projections are NOT generated. Seat Change (ΔS) is computed from realised historical data — it is never an output of scenario simulation.

**Iteration count:** 2,000 per scenario per borough. Frozen. Do not increase.

**Single-point outputs prohibited:** All published outputs show P10/P50/P90. Never P50 alone.

---

## Challenger Definition

> Challenger = the party with the highest absolute vote share swing gain in 2025 in that borough.

Rules applied mechanically — no editorial discretion:

- **Tie-break:** Higher 2025 absolute vote share wins.
- **Independents:** Pooled as `IND`. Treated as challenger if they meet the swing criterion.
- **No overall control outcomes:** Recorded in the Seat Change historical metric only. Does not affect scenario vote share logic.
- **No manual overrides** of challenger classification after Phase B commit.

---

## S0 — Baseline

`Swing = 0pp from 2025 across all parties.`

No-change assumption. Used as reference point for all other scenarios.

## S1 — High Volatility Continuation

`Challenger VS +2pp; Established VS −2pp`

Challenger defined per borough (see above). The −2pp is redistributed proportionally among established parties.

## S2 — Partial Recovery

`Established VS +1.5pp; Challenger VS −1.5pp`

Reverse of S1. Redistributed proportionally.

## S3 — Challenger Surge

`Challenger VS +4pp; Established VS −4pp`

High-end continuation. If this scenario fails interval validation → dropped first (see fallback rule below).

## S4 — Deprivation Turnout Shift

`ΔT = +3pp in wards with IMD deciles 1–3. Vote share unchanged.`

IMD used only to identify which wards receive the structural turnout adjustment. IMD does not infer, adjust, or predict vote share.

## S5 — Stability Reversion (London Cap)

`Borough VI capped at empirical 90th percentile of London VI 2010–2022.`

**Empirical derivation required.** If insufficient London data is available to derive the 90th percentile empirically, S5 is removed:
- `artifacts/london_vi_cap.txt` will contain `S5_REMOVED`
- Removal decision logged in `docs/DECISIONS_LOG.md` with full rationale, before model lock
- No substitute scenario is created

If S5 is removed, this is a disciplined scope decision — not a failure.

---

## Fallback: Scenario Count Reduction

If scenario output validation fails (any P10 > P50, P50 > P90, or interval narrower than calibration RMSE):

1. Drop S3 (Challenger Surge) — highest uncertainty, most likely to produce unstable intervals
2. Drop S5 (Stability Reversion) — empirically dependent, second highest uncertainty
3. Rerun validation on remaining 4 scenarios
4. Log decision in `docs/DECISIONS_LOG.md` before model lock

---

*Freeze hash: [populated at Phase B commit]*
