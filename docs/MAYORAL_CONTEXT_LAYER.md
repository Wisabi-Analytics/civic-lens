# Mayoral Context Layer

**Status:** Active — separate descriptive pipeline, excluded from volatility system.  
**File:** `docs/MAYORAL_CONTEXT_LAYER.md`

---

## Why Mayoral Elections Are Excluded from the Volatility System

All 10 combined authority mayoral elections on 7 May 2026 are **newly-established roles**. No prior election exists for any of them.

The Civic Lens volatility system requires a minimum of two election cycles to compute:
- Vote share swing (Δ% = VS_t − VS_(t-1)) — undefined with one cycle
- Turnout delta (ΔT = T_t − T_(t-1)) — undefined with one cycle
- Fragmentation delta (ΔFI) — undefined with one cycle
- Volatility Score (VOL) — depends on all of the above
- Backtest calibration — requires training on one cycle, predicting another

Running the volatility pipeline against a single data point would produce undefined outputs. Fabricating a reference baseline would violate the project's transparency principles. The exclusion is therefore methodological, not editorial.

**This is a strength, not a gap.** A system disciplined enough to exclude high-profile elections when methodological requirements are not met is more credible than one that forces outputs regardless of data conditions.

---

## What Is Published Instead

Mayoral elections are included as a **separate descriptive context layer**. This layer produces:

| Output | Description | Claim |
|---|---|---|
| Vote share distribution | % per candidate per authority | Descriptive — single cycle |
| Turnout | Turnout % per authority | Descriptive — no delta possible |
| Candidate field fragmentation | FI = 1/Σ(VS²) per authority | Descriptive — no trend possible |
| Cross-authority patterns | Comparative table across all 10 | Descriptive — no longitudinal |

All outputs are clearly labelled **"descriptive only — single election cycle"**. No volatility claims are made. No scenario simulation is run.

Published in: `reports/mayoral_context.md`  
Data source: `data/processed/mayoral_context.csv`

---

## The 10 Combined Authority Mayors (2026)

All are newly-established roles — no prior election baseline exists for any.

*(Exact list confirmed during Phase A data acquisition from Electoral Commission)*

---

## Data Pipeline

Mayoral data flows through a **separate, simpler pipeline** than the main volatility system:

```
data/raw/ec/mayors_2026.csv
    ↓
src/metrics/mayoral_descriptive.py
    ↓
data/processed/mayoral_context.csv
    ↓
reports/mayoral_context.md
```

`mayoral_descriptive.py` computes:
- Vote share per candidate
- Turnout per authority
- Single-cycle Fragmentation Index (descriptive)

It does **not** call:
- `vote_share_swing()`
- `turnout_delta()`
- `volatility_score()`
- `scenario_model.py`
- `audit_results.py`

Any function call from the volatility pipeline on mayoral data should raise a `ValueError` with the message: `"Mayoral elections excluded from volatility system — see docs/MAYORAL_CONTEXT_LAYER.md"`

---

## Public Statement

The following language is used in all publications referencing mayoral elections:

> *"Civic Lens excludes mayoral elections from its volatility measurement framework. All 10 combined authority mayoral roles on the May 2026 ballot are newly established — no prior election exists from which to compute swing, turnout delta, or calibrated uncertainty. A system that cannot be calibrated should not produce volatility outputs. Mayoral results are published separately as single-cycle descriptive analysis."*

---

## Tech Nation Positioning

The decision to exclude mayoral elections — despite their political prominence — demonstrates:

- **Statistical prerequisites enforced.** The system applies its own rules even when exceptions would be convenient.
- **Transparency over coverage.** Narrower, honest scope is more credible than broad, uncalibrated outputs.
- **Engineering maturity.** The pipeline is structured to make the exclusion explicit and testable, not silently omitted.

This exclusion is cited in `docs/DECISIONS_LOG.md` with full rationale.
