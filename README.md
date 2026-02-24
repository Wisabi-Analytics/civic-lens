# civic-lens

**A transparent, uncertainty-first electoral volatility measurement system for English local elections.**

[![Model Status](https://img.shields.io/badge/model%20status-pre--lock-blue)](artifacts/model_lock.txt)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Data](https://img.shields.io/badge/data-Electoral%20Commission-orange)](https://www.electoralcommission.org.uk)
[![Methodology](https://img.shields.io/badge/docs-methodology-lightgrey)](docs/METHODOLOGY.md)

---

## What This Is

Civic Lens measures **electoral volatility** across English local elections — not to predict winners, but to quantify the scale and structure of political change.

The central question:

> *How do we measure electoral volatility and structural party realignment responsibly — with transparent modelling, explicit uncertainty, and full public audit?*

This project produces three public outputs:

| Publication | Date | What It Does |
|---|---|---|
| [Part 1 — Historical Baseline (2018–2022)](https://wisabianalytics.com) | 25 March 2026 | Establishes what "normal" electoral volatility looks like before the 2025 shock |
| [Part 2 — Scenarios & Uncertainty](https://wisabianalytics.com) | 14 April 2026 | Models six defined scenarios for May 7th using calibrated uncertainty bands |
| [Part 3 — Predictions vs Reality](https://wisabianalytics.com) | 9 May 2026 | Post-election accuracy audit published within 48 hours of results |

**Part 3 is the point.** A system that audits its own accuracy publicly is fundamentally different from a dashboard that publishes predictions and goes quiet.

---

## What This Is Not

This project does not:

- Predict seat counts or electoral outcomes
- Model individual ward-level results nationally
- Use ML or black-box modelling
- Incorporate polling data, social media sentiment, or economic indicators
- Use demographic data to infer or adjust vote share
- Express preference for any party or electoral outcome

**On seat change specifically:** `seat_change` is computed from *realised historical data only* — it measures what actually happened in past elections. Scenario simulations do not generate seat projections. Scenario outputs are distributions of volatility metrics under stated assumptions — not forecasts of seats won or lost.

Scenario outputs are **exploratory under stated algebraic assumptions** — not forecasts.

**On mayoral elections:** All 10 combined authority mayoral elections in 2026 are newly-established roles with no historical baseline. Civic Lens excludes them from the volatility system — a system that cannot be calibrated should not produce volatility outputs. They are included as a descriptive context layer only.

---

## Limitations

Civic Lens is a measurement system, not a prediction engine. Users and reviewers should be aware of four explicit constraints:

- **Local elections heterogeneity.** English local elections vary substantially in electoral system, council type, and incumbency dynamics across boroughs. No single volatility model fully captures this variation. Borough-level aggregation is a deliberate, disclosed simplification.
- **Borough independence assumption.** Boroughs are simulated independently in the Monte Carlo engine. No cross-borough swing correlation is modelled. This is appropriate for local elections where borough-specific dynamics dominate, but it means the model cannot capture nationally coordinated swings. See `docs/SCENARIO_DEFINITIONS.md`.
- **Boundary change and all-out election fallback.** 13 metropolitan boroughs hold all-out elections in 2026 due to LGBCE boundary reviews; these are handled at borough aggregate only. Councils with mid-cycle boundary changes follow the same rule. The full list is documented in `data/processed/DATA_DICTIONARY.md`.
- **No polling or economic inputs.** Civic Lens uses only official Electoral Commission results. Scenarios are defined algebraically — not calibrated to polling aggregates, economic indicators, or demographic regression.

---

## Six Core Metrics

All analysis derives from these six party-agnostic metrics. This count is locked — no metrics are added mid-project.

| Metric | Formula | What It Measures |
|---|---|---|
| Vote Share Swing | `Δ% = VS_t − VS_(t-1)` | Directional party movement |
| Turnout Delta | `ΔT = T_t − T_(t-1)` | Participation change |
| Fragmentation Index | `FI = 1 / Σ(VS²)` | Effective number of parties (HHI) |
| Seat Change | `ΔS = Seats_t − Seats_(t-1)` | Structural electoral outcome (historical data only) |
| Volatility Score | `VOL = (0.5 × Σ\|swing_i\|) + (0.5 × ΔFI)` | Composite party-agnostic signal — equal weight, not normalised |
| Swing Concentration | `SC = max(\|swing\|) / mean(\|swing\|)` | Broad vs ward-clustered swings |

**Terminology note:** Vote share is denoted `VS` throughout. The Volatility Score is denoted `VOL` to avoid collision. Equal weighting of swing and fragmentation delta. Turnout enters separately via ΔT. This formula is **frozen at the Phase B commit** — see [`artifacts/model_lock.txt`](artifacts/model_lock.txt).

---

## Geographic Scope

| Tier | Scope | Granularity | Note |
|---|---|---|---|
| Tier 1 — Primary | 32 Metropolitan Boroughs (election-active) | Borough-level | 36 total; 4 excluded — no 2026 election¹ |
| Tier 2 — Contrast | 32 London Boroughs | Borough-level | All-out elections |
| Tier 3 — Deep Dive | 5 Yorkshire councils (selected) | Ward-level (where harmonised) | Ward harmonisation only here |
| Mayoral Context Layer | 10 Combined Authority Mayors | Descriptive only | **Excluded from volatility system** — see below |

¹ **Excluded metropolitan boroughs (no 2026 election):** Doncaster, Liverpool, Wirral, Rotherham.

**All-out election flag:** 13 of the 32 election-active metropolitan boroughs hold all-out elections in 2026 due to LGBCE boundary reviews. For these councils, ward-level longitudinal comparisons are not attempted — analysis is conducted at borough aggregate only (`analysis_level = borough_only`). These 13 councils are listed in [`data/processed/DATA_DICTIONARY.md`](data/processed/DATA_DICTIONARY.md).

**Mayoral Context Layer:** All 10 combined authority mayoral elections in 2026 are newly-established roles with no prior election baseline. They are therefore **excluded from the volatility measurement system** — no volatility metrics, no backtest calibration, no Monte Carlo scenarios. Mayoral elections are included as a separate descriptive-only layer: vote share distribution, turnout levels, and candidate field fragmentation. This exclusion is a deliberate methodological decision, not an omission. See [`docs/MAYORAL_CONTEXT_LAYER.md`](docs/MAYORAL_CONTEXT_LAYER.md).

---

## Six Scenarios

Scenario definitions are **frozen after the Phase B commit**. No new scenarios are added after this point.

| ID | Name | Definition |
|---|---|---|
| S0 | Baseline | Uniform swing = 0pp from 2025 across all parties |
| S1 | High volatility continuation | Challenger VS +2pp; established VS −2pp (challenger defined per borough) |
| S2 | Partial recovery | Established VS +1.5pp; challenger VS −1.5pp |
| S3 | Challenger surge | Challenger VS +4pp; established VS −4pp |
| S4 | Deprivation turnout shift | ΔT = +3pp in IMD deciles 1–3. Vote share unchanged. |
| S5 | Stability reversion | VI capped at 90th percentile London VI 2010–2022. Empirically derived or removed. |

**Challenger definition:** The party with the highest absolute vote share swing gain in 2025 in that borough. Tie-break: higher 2025 absolute vote share. Independents pooled as `IND`. Full rules in [`docs/SCENARIO_DEFINITIONS.md`](docs/SCENARIO_DEFINITIONS.md).

**Borough independence:** Boroughs are simulated independently. No cross-borough swing correlation is modelled. This is a deliberate, stated simplification — local elections are driven by borough-specific dynamics that make national correlation assumptions unjustified at this geography.

**S5 removal rule:** If the London VI 90th percentile is not empirically derivable from available data, S5 is removed and replaced with `S5_REMOVED.txt`. This decision is logged in `docs/DECISIONS_LOG.md` before model lock, with full rationale. No substitute scenario is created.

---

## Methodology

**Baseline year: 2018.** The 2018→2022 transition is used as the historical baseline. 2021 results are acquired and stored locally under `data/raw/ec/` for completeness but are **excluded from baseline calibration** — the 2021 cycle was a pandemic election with structurally suppressed turnout and cancelled contests in many wards, making it atypical as a baseline for "normal" electoral conditions. Full rationale in [`docs/DECISIONS_LOG.md`](docs/DECISIONS_LOG.md).

**Calibration-first.** The model is trained on 2018→2022 data, used to predict 2025, and the measured error sets all 2026 uncertainty bands. See [`artifacts/calibration_report.md`](artifacts/calibration_report.md).

**Monte Carlo.** 2,000 iterations per scenario per borough. Swing distributions are bootstrapped from **borough-specific historical error distributions** derived from the calibration backtest — not national pooled distributions and not assumed parametric distributions. Each borough's uncertainty reflects its own historical volatility pattern. All simulations use a fixed RNG seed (`20260430`) recorded in `artifacts/model_lock.txt`.

**Uncertainty.** All outputs show P10/P50/P90 bands. Single-point estimates are never published without intervals. Wide bands are honest — they will not be narrowed to appear more impressive.

Full methodology: [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md)

---

## Model Lock

The model is frozen on **30 April 2026** to prevent adaptive tuning. No parameters, scenarios, or uncertainty bands are modified after this date.

```
model_version_sha:        [populated 30 April]
scenario_definitions_sha: [populated 30 April]
volatility_score_formula: VOL = (0.5 × Σ|swing_i|) + (0.5 × ΔFI)
rng_seed:                 20260430
bootstrap_source:         borough-specific historical error distributions
freeze_timestamp_utc:     2026-04-30T[HH:MM:SS]Z
statement:                "Model frozen 30 April 2026 to prevent adaptive tuning.
                           No parameters, scenarios, or uncertainty bands were
                           modified after this timestamp."
```

See [`artifacts/model_lock.txt`](artifacts/model_lock.txt). This statement appears verbatim in the Part 3 accuracy report.

---

## Reproducibility

All scenario outputs are deterministically reproducible given the freeze artefacts committed on 30 April. Determinism is guaranteed by the fixed RNG seed (`20260430`) and pinned dependency versions in `pyproject.toml`.

```bash
# Reproduce a published run exactly
git checkout [model_version_sha]
pip install -e ".[dev]"
python src/calibration/run_backtest.py
python src/simulation/run_scenarios.py --config artifacts/model_lock.txt
```

Outputs should match published artefacts in `artifacts/scenario_outputs.csv` exactly.

The following inputs fully determine all outputs:
- `model_version_sha` — code state at lock
- `scenario_definitions_sha` — scenario algebra at lock
- `rng_seed: 20260430` — fixed seed; guarantees Monte Carlo determinism
- `data/raw/data_inventory.csv` — raw data manifest (hash verified)
- `freeze_timestamp_utc` — confirms no post-lock modifications

If reproduction fails or outputs diverge, open an issue with the SHA and timestamp. Reproducibility failures are treated as bugs.

---

## Quickstart

**Setup:**

```bash
git clone https://github.com/[yourusername]/civic-lens.git
cd civic-lens
pip install -e ".[dev]"         # pinned deps from pyproject.toml
pytest tests/                   # all six metric unit tests must pass before proceeding
```

**Minimal demo run (synthetic data — no EC downloads required):**

```bash
python -m src.calibration.run_backtest --demo
python -m src.simulation.run_scenarios --demo
```

The `--demo` flag runs the full pipeline on a synthetic dataset of 5 boroughs × 3 election years, confirming the pipeline is correctly wired without requiring real EC data. Outputs go to `artifacts/demo/`.

**Full run (after completing Phase A data acquisition):**

```bash
python src/calibration/run_backtest.py
python src/simulation/run_scenarios.py --config artifacts/model_lock.txt
```

---

## Repository Structure

```
civic-lens/
│
├── src/                              # All executable source code
│   ├── metrics/
│   │   └── metrics.py                # Six metric functions with unit tests
│   ├── simulation/
│   │   └── scenario_model.py         # Monte Carlo engine (2,000 iter/scenario/borough)
│   ├── calibration/
│   │   └── run_backtest.py           # Calibration backtest (2018→2022→predict 2025)
│   └── audit/
│       └── audit_results.py          # Post-election accuracy script (pre-built before May 7th)
│
├── data/
│   ├── raw/                          # Source files — never modified after download
│   │   ├── ec/                       # Electoral Commission results CSVs
│   │   ├── ons/                      # ONS ward lookup tables (3 vintages)
│   │   ├── lgbce/                    # LGBCE boundary shapefiles (Yorkshire only)
│   │   └── data_inventory.csv        # Audit log: every file, schema, issues detected
│   └── processed/
│       ├── clean_election_results.csv
│       ├── concordance_table.csv     # Ward harmonisation — standalone open artefact
│       ├── baseline_metrics.csv      # 2018→2022 metric outputs
│       ├── shock_metrics.csv         # 2022→2025 metric outputs
│       └── DATA_DICTIONARY.md        # Every field, every harmonisation assumption
│
├── artifacts/                        # Versioned, immutable outputs
│   ├── model_lock.txt                # SHA hash + freeze timestamp (populated 30 Apr)
│   ├── scenario_outputs.csv          # P10/P50/P90 per scenario per borough
│   ├── calibration_report.md         # Backtest findings — published regardless of fit
│   ├── calibration_curves.png
│   └── election_night/
│       └── snapshots/                # Timestamped PNG fallbacks from election night
│
├── reports/                          # Published articles and dashboards
│   ├── part1_article.md              # Historical baseline
│   ├── part2_article.md              # Scenarios and uncertainty
│   └── part3_template.md             # Accuracy report (pre-built, fills post-election)
│
├── docs/
│   ├── METHODOLOGY.md                # Full technical methodology
│   ├── SCENARIO_DEFINITIONS.md       # Algebraic definitions — frozen at Phase B
│   ├── DECISIONS_LOG.md              # Analytical decisions with rationale
│   └── ELECTION_NIGHT_RUNSHEET.md    # Step-by-step from 10pm May 7th
│
├── notebooks/
│   ├── baseline_volatility.ipynb     # Phase B working analysis
│   └── scenario_exploration.ipynb    # Scenario validation workings
│
├── tests/
│   └── test_metrics.py               # Unit tests for all six metric functions
│
├── PROJECT_PRINCIPLES.md             # Neutrality, uncertainty-first, open audit
├── EC_PLAN_B_PROTOCOL.md             # Data quality fallback procedures
├── scope-lock.md                     # Tiers, councils, metrics, exclusions — locked
├── LICENSE                           # MIT
├── requirements.txt
└── README.md
```

---

## Setup

```bash
git clone https://github.com/[yourusername]/civic-lens.git
cd Civic Lens
pip install -r requirements.txt
pytest tests/                         # All six metric unit tests should pass before proceeding
```

**Requirements:**
```
pandas>=2.0
numpy>=1.24
geopandas>=0.14
rapidfuzz>=3.0
pyarrow>=14.0
matplotlib>=3.7
pytest>=7.0
scipy>=1.11
```

---

## Data Sources

| Dataset | Years | Source | Licence |
|---|---|---|---|
| Electoral results | 2018, 2021, 2022, 2025 | [Electoral Commission](https://www.electoralcommission.org.uk/who-we-are-and-what-we-do/elections-and-referendums/past-elections-and-referendums) | OGL v3 |
| Ward boundary lookups | 2018, 2022, 2025 vintages | [ONS Open Geography](https://geoportal.statistics.gov.uk) | OGL v3 |
| Ward boundary shapefiles | Current | [ONS Open Geography](https://geoportal.statistics.gov.uk) | OGL v3 |
| LGBCE boundary reviews | All cycles | [LGBCE](https://www.lgbce.org.uk/all-reviews) | OGL v3 |
| IMD 2019 (descriptive overlay only) | 2019 | [ONS Nomis](https://www.nomisweb.co.uk) | OGL v3 |

**Note on 2021:** Results are acquired and stored locally under `data/raw/ec/` for completeness and potential contextual use. 2021 is **excluded from baseline calibration** due to pandemic-era distortions. This exclusion is documented in [`docs/DECISIONS_LOG.md`](docs/DECISIONS_LOG.md).

Raw data files are not committed to this repository (see `.gitignore`). Run the Phase A acquisition tasks in `scope-lock.md` to populate `/data/raw/`.

---

## Project Principles

This project is built on five principles. Full statement: [`PROJECT_PRINCIPLES.md`](PROJECT_PRINCIPLES.md).

1. **Neutrality** — party-agnostic metrics, no persuasion intent, no editorial framing of results
2. **Uncertainty-first** — all outputs show P10/P50/P90 bands, never single-point estimates
3. **Transparent limitations** — boundary changes, harmonisation fallbacks, and baseline year choices are all disclosed before they can be discovered externally
4. **No predictive claims** — scenario outputs are exploratory under stated algebraic assumptions only; seat change is measured from historical data, not projected
5. **Open audit** — model frozen 30 April, post-election accuracy published within 48 hours

---

## Licence

MIT — see [LICENSE](LICENSE). All code, concordance tables, metric implementations, and simulation logic are open for replication, audit, and reuse.
