# Project Principles

civic-lens is built on five principles. These govern every analytical decision, every public-facing output, and every piece of methodology documentation. They are committed on Day 1 and do not change.

---

## 1. Neutrality

This project has no political affiliation, no preferred electoral outcome, and no persuasion intent.

All metrics are party-agnostic. No party is named in scenario logic — scenarios are defined in terms of "challenger" and "established" parties, with challenger defined mechanically per borough as the party with the highest absolute vote share swing gain in 2025. This produces different party labels in different geographies, which is analytically correct.

We do not publish commentary that frames any electoral outcome as good or bad. We measure volatility. We do not endorse it.

---

## 2. Uncertainty-First

Every output from this system includes explicit uncertainty quantification.

All scenario outputs show P10/P50/P90 distribution bands. Single-point estimates are never published without intervals. Wide uncertainty bands are honest — they are not a weakness of the model, and they will not be narrowed to appear more impressive.

The width of our uncertainty bands is set by the measured error from the calibration backtest, not by assumption.

---

## 3. Transparent Limitations

Every methodological limitation is disclosed in public-facing documentation before it could be discovered by a critic.

This includes:
- Baseline year choice (2018, not 2021 — rationale in `docs/DECISIONS_LOG.md`)
- Borough-level fallback for councils with LGBCE boundary changes
- Ward harmonisation limited to Yorkshire Tier 3 only
- Borough independence assumption in Monte Carlo simulation
- Any scenario removed due to missing empirical inputs (e.g. S5 if London VI cap is not derivable)

Silence on a limitation is not acceptable. Transparency about constraints is a strength, not a weakness.

---

## 4. No Predictive Claims

Scenario outputs are exploratory under stated algebraic assumptions. They are not seat predictions, vote share forecasts, or electoral projections.

The phrase "this model predicts" does not appear in any public-facing material produced by this project. Scenarios are presented as: *"Under assumption X, our model produces output Y with uncertainty band Z."*

---

## 5. Open Audit

The model is frozen on 30 April 2026. No parameters, scenario definitions, or uncertainty bands are modified after that date.

A post-election accuracy report is published within 48 hours of May 7th results. This report is honest: it shows where the model was wrong, decomposes the error by tier and metric, and does not attribute failures to external factors without evidence.

The full audit infrastructure — `audit_results.py`, calibration curves, scenario performance comparison — is built *before* election night, not after results are known.

---

*civic-lens is also a case study in how responsible civic data systems should be designed: transparent assumptions, pre-authorised fallback triggers, calibration-first modelling, and post-hoc accountability built in from the start.*
