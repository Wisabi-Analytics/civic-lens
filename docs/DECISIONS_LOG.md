# Analytical Decisions Log

Key decisions with full rationale and rejected alternatives.

---

| Decision | Choice | Core Rationale |
|---|---|---|
| Baseline year | 2018 (not 2021) | 2021 = pandemic outlier, would conflate two disruptions |
| Ward granularity | Borough-level for Tier 1+2 | Harmonisation cost too high; borough analysis is fully valid |
| Monte Carlo iterations | 2,000 | Calibration logic matters, not simulation volume |
| Bootstrap source | Borough-specific error distributions | National pool too coarse; each borough has its own volatility pattern |
| Borough independence | No correlation modelling | Too few cycles to estimate reliable covariance for 64 boroughs |
| Volatility Score weights | Equal (0.5 swing / 0.5 ΔFI) | No strong prior for privileging either component |
| Seat Change in scenarios | Historical data only, not simulated | Seat projections would contradict "not a forecast" positioning |
| Challenger framing | Mechanical per-borough rule | Party-neutral, auditable, avoids perception risk |
| 2021 data | Included in raw/, excluded from calibration | Available for context; structurally unsuitable as baseline |

---

| Metropolitan borough count | 32 of 36 election-active (not all 36) | 4 councils (Doncaster, Liverpool, Wirral, Rotherham) have no 2026 election — excluded on factual grounds |
| Mayoral elections | Descriptive context layer only — excluded from volatility system | All 10 combined authority mayoral elections are newly-established roles. No historical baseline = no calibration = no volatility outputs. Publishing volatility metrics without a baseline would be methodologically dishonest. |
| All-out elections (Tier 1) | Borough aggregate only for 13 affected metropolitan boroughs | 13 of 32 Tier 1 boroughs hold all-out elections due to LGBCE reviews. Ward-level longitudinal comparisons impossible without concordance. Borough aggregate preserves analytical validity. |

*(Full entries including rejected alternatives maintained in WarBoard v3 Decisions Log tab)*

---

## S5 Removal Log

*(Populated if S5 removed during Phase B — logged before model lock)*

| Date | Decision | Rationale | Alternative Considered |
|---|---|---|---|
| [TBD] | [S5 kept / S5_REMOVED] | [Empirical cap derived / insufficient data] | [N/A or substitute considered and rejected] |

---

## All-Out Election Boroughs (Tier 1 — Confirmed During Phase A)

13 metropolitan boroughs hold all-out elections in 2026 due to LGBCE boundary reviews.

*(Full list confirmed during Phase A data acquisition — add names here)*

For each:
- `analysis_level = borough_only`
- `boundary_note = "All-out election 2026 — LGBCE boundary review. No ward-level longitudinal analysis."`
- Concordance table entry: `change_type = all_out_lgbce`

---

## Mayoral Context Layer — Exclusion Rationale

**Decision date:** Confirmed at scope lock  
**Decision:** All 10 combined authority mayoral elections excluded from volatility measurement system.

**Reason:** All 2026 combined authority mayoral elections are newly-established roles (confirmed: Wikipedia, 2026 United Kingdom local elections). No prior election exists from which to compute swing, turnout delta, fragmentation trend, or any time-series metric. Running the volatility pipeline against a single data point would produce undefined or meaningless outputs.

**Alternative considered:** Include mayors in the volatility system with a single-cycle "baseline" using invented reference values. Rejected — this would require fabricating a baseline, violating the project's transparency principles.

**What is published instead:** A separate descriptive analysis (`reports/mayoral_context.md`) covering vote share distribution, turnout, and candidate field fragmentation for each of the 10 mayors. These outputs are clearly labelled as descriptive-only with no volatility claims.

**Public statement:** *"Civic Lens excludes mayoral elections from its volatility framework because all 10 roles are newly established with no prior election baseline. A system that cannot be calibrated should not produce volatility outputs. Mayoral results are included as contextual civic analysis only."*
