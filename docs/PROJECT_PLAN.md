Final Unified Civic Lens Project Plan

Phase 0 — Governance Lock

Goal: freeze scope, principles, and operating rules before transformation begins.

0.1 Finalise core governance docs

Complete and commit:
	•	README.md
	•	scope-lock.md
	•	PROJECT_PRINCIPLES.md
	•	docs/METHODOLOGY.md
	•	docs/DECISIONS_LOG.md

0.2 Record locked decisions

Document explicitly:
	•	mayoral layer excluded from volatility pipeline, or handled as descriptive-only context
	•	36 metro boroughs exist, but only 32 are election-active in 2026
	•	excluded metro boroughs: Doncaster, Liverpool, Wirral, Rotherham
	•	2021 included in raw storage for completeness but excluded from calibration
	•	Tier 3 ward-level analysis only where harmonisation is defensible
	•	all-out elections and major boundary changes force borough-level fallback
	•	Tiers 1 and 2 have no 2025 backtest; uncertainty borrowed from Tier 3 with explicit caveat

0.3 Freeze repo structure

Ensure structure is final before scripts proliferate:
	•	src/
	•	data/raw/
	•	data/interim/
	•	data/processed/
	•	docs/
	•	artifacts/
	•	reports/
	•	tests/

Exit criteria
	•	No ambiguity remains on scope, exclusions, tiers, or methodology.

⸻

Phase 1 — Raw Data Audit

Goal: understand every file before cleaning or joining anything.

1.1 Audit all raw sources

Inspect every file in:
	•	data/raw/ec/
	•	data/raw/ons/
	•	data/raw/boundaries/
	•	data/raw/imd/

For each file record:
	•	filename
	•	source
	•	download date
	•	file type
	•	sheet names
	•	row count
	•	column names
	•	key identifiers present
	•	missing fields
	•	anomalies
	•	whether it is authoritative or supplementary

1.2 Populate inventory

Complete:
	•	data/raw/data_inventory.csv
	•	validate against data/raw/DATA_SOURCE_METADATA.md

1.3 Produce audit note

Write a short raw audit summary:
	•	what is immediately usable
	•	what needs special parsing
	•	known schema mismatches
	•	known field gaps
	•	known election-cycle caveats

Deliverables
	•	data/raw/data_inventory.csv
	•	raw audit summary

Exit criteria
	•	Every raw file is understood structurally.

⸻

Phase 2 — Canonical Schema and Metric Contract

Goal: define the target data model and freeze metric semantics before processing.

2.1 Define canonical election schema

Create the target schema for clean_election_results.csv.

Core fields:
	•	election_year
	•	election_date
	•	authority_code
	•	authority_name
	•	authority_type
	•	region
	•	tier
	•	ward_name_raw
	•	ward_name_clean
	•	ward_code
	•	candidate_name
	•	party_raw
	•	party_standardised
	•	votes
	•	vote_share
	•	electorate
	•	turnout_pct
	•	seats_contested
	•	seats_won
	•	source_dataset
	•	analysis_level
	•	harmonisation_status
	•	notes

2.2 Freeze metric definitions

Define and confirm the six metrics and their inputs:
	•	vote share swing
	•	turnout delta
	•	fragmentation index
	•	seat change
	•	volatility score
	•	swing concentration

Resolve notation collisions here.
Do not use the same abbreviation for vote share and volatility score.

2.3 Write the data dictionary

Create:
	•	data/processed/DATA_DICTIONARY.md

Deliverables
	•	canonical schema
	•	metric contract
	•	data dictionary draft

Exit criteria
	•	You know exactly what clean outputs and metric inputs must look like.

⸻

Phase 3 — Metric Engine Foundation

Goal: build and test the six metrics before full pipeline execution.

3.1 Implement metric functions

Create:
	•	src/civic_lens/metrics.py

3.2 Write unit tests

Create:
	•	tests/test_metrics.py

Use synthetic known-value cases only:
	•	zero swing
	•	equal party shares
	•	concentrated swing
	•	turnout increase/decrease
	•	seat changes
	•	fragmentation edge cases

3.3 Validate formulas manually

Check a few by hand and record expected results.

Deliverables
	•	working metric engine
	•	passing unit tests

Exit criteria
	•	Metric functions are correct and fully test-passing.

⸻

Phase 4 — Source Ingestion

Goal: load each source into reproducible interim tables without manual spreadsheet work.

4.1 Build source loaders

Create loaders for:
	•	DCLEAPIL
	•	Commons Library 2021
	•	Commons Library 2022
	•	Commons Library 2025
	•	ONS ward/LAD lookups
	•	LAD/region lookup
	•	IMD

4.2 Save standardised interim outputs

Write to data/interim/ with source-specific cleaned column names but no cross-source merge yet.

Deliverables
	•	ingestion scripts
	•	interim source tables

Exit criteria
	•	Every raw source can be reloaded cleanly from code.

⸻

Phase 5 — Election Results Cleaning and Standardisation

Goal: create a single unified election-results table.

5.1 Standardise naming

Standardise:
	•	party labels
	•	ward names
	•	authority names
	•	date fields
	•	candidate-level structure

5.2 Handle edge cases

Define and apply rules for:
	•	missing electorate
	•	missing turnout
	•	independents
	•	uncontested wards
	•	multi-seat wards
	•	source conflicts

5.3 Assign provenance and analysis placeholders

Add:
	•	source_dataset
	•	provisional analysis_level
	•	notes

5.4 Output master table

Create:
	•	data/processed/clean_election_results.csv

Deliverables
	•	unified clean results table

Exit criteria
	•	One canonical results file exists across all relevant years.

⸻

Phase 6 — Geography, Scope, and Authority Metadata

Goal: attach geography cleanly and enforce scope by code, not by name guessing.

6.1 Join LAD metadata

Attach:
	•	region
	•	authority type
	•	Civic Lens tier

6.2 Build authority dimension

Produce a clean dimension table containing:
	•	all in-scope authorities
	•	excluded authorities
	•	election-active flags
	•	borough/London/Yorkshire typing

6.3 Verify scope membership

Assert:
	•	exactly 32 metro boroughs in scope
	•	exactly 32 London boroughs in scope
	•	exactly 5 Yorkshire councils in scope
	•	excluded metro boroughs absent from active 2026 scope

Deliverables
	•	enriched clean results
	•	authority dimension
	•	scope verification script

Exit criteria
	•	Scope lock can be programmatically proven.

⸻

Phase 7 — Concordance and Harmonisation

Goal: make cross-cycle ward comparison defensible and explicit.

7.1 Build concordance logic

Match across vintages using:
	1.	exact code match
	2.	exact cleaned-name match
	3.	reviewed fallback
	4.	borough-only fallback

7.2 Create concordance table

Include fields such as:
	•	prior ward code
	•	current ward code
	•	authority code
	•	match method
	•	confidence
	•	change type
	•	analysis level
	•	fallback reason

7.3 Handle boundary-change and all-out cases

Explicitly flag:
	•	all-out election boroughs
	•	split/merge wards
	•	unmatched wards
	•	borough-only authorities

7.4 Output

Create:
	•	data/processed/concordance_table.csv

Deliverables
	•	concordance table
	•	harmonisation rules documented

Exit criteria
	•	Every ward-level comparison is either defensible or explicitly downgraded.

⸻

Phase 8 — QA and Source Validation

Goal: catch data inconsistencies before metrics are computed.

8.1 Cross-source validation

Compare DCLEAPIL vs Commons Library where overlap exists, especially 2022.

Check:
	•	authority
	•	ward
	•	party
	•	votes
	•	turnout
	•	electorate where available

8.2 Structural QA

Check:
	•	duplicates
	•	null rates
	•	impossible vote shares
	•	turnout > 100
	•	negative values
	•	invalid seat counts

8.3 Log anomalies

Document every material anomaly and resolution in:
	•	docs/DECISIONS_LOG.md

Deliverables
	•	QA scripts
	•	anomaly log
	•	validated processed dataset

Exit criteria
	•	Known inconsistencies are documented and accepted.

⸻

Phase 9 — Baseline Metrics

Goal: compute the historical baseline of “normal” volatility.

9.1 Compute 2018→2022 metrics

For all in-scope tiers, respecting analysis_level.

9.2 Output baseline file

Create:
	•	data/processed/baseline_metrics.csv

9.3 Review outputs

Check whether values are plausible by borough and tier.

Deliverables
	•	baseline metrics dataset
	•	exploratory visuals/notebook

Exit criteria
	•	Part 1 can be written from actual metric outputs.

⸻

Phase 10 — Tier-Specific Calibration and Shock Logic

Goal: calibrate responsibly and document tier differences upfront.

10.1 Tier 3 backtest

Use Tier 3 only:
	•	2018→2022 baseline
	•	compare against actual 2022→2025 outcomes

Output:
	•	artifacts/backtest_results.csv
	•	artifacts/calibration_report.md

Metrics:
	•	RMSE
	•	MAE
	•	P10/P50/P90 coverage

10.2 Document Tier 1 and 2 limitation

State clearly in docs/METHODOLOGY.md:
	•	no 2025 election exists for metro/London boroughs
	•	no direct backtest available
	•	uncertainty bands transferred from Tier 3 backtest
	•	this is a limitation

10.3 Compute Tier 3 shock metrics

Create:
	•	data/processed/shock_metrics.csv

10.4 Derive S5 rule

Compute London VI empirical cap if possible.
If not possible:
	•	create artifacts/london_vi_cap.txt with S5_REMOVED
	•	log the decision

Deliverables
	•	backtest results
	•	calibration report
	•	shock metrics
	•	S5 decision artefact

Exit criteria
	•	Uncertainty logic is empirical where possible and explicit where transferred.

⸻

Phase 11 — Publication 1: Baseline

Goal: publish the historical baseline cleanly and credibly.

11.1 Write baseline narrative

Interpret:
	•	volatility distribution
	•	fragmentation
	•	turnout
	•	stable vs unstable boroughs

11.2 Build dashboard

Charts:
	•	swing distribution
	•	fragmentation trend
	•	turnout trend
	•	borough volatility map

11.3 Publish

Complete:
	•	reports/part1_article.md

Then publish to site and socials.

Deliverables
	•	Part 1 article
	•	dashboard assets
	•	screenshots/archive

Exit criteria
	•	Part 1 is public and archived.

⸻

Phase 12 — Scenario Engine

Goal: encode S0–S5 exactly as locked.

12.1 Implement simulation engine

Create:
	•	src/civic_lens/scenario_model.py

12.2 Hard-code simulation contract
	•	RNG seed locked
	•	2,000 iterations
	•	borough-level independence
	•	no invalid interval ordering
	•	no implausibly narrow bands

12.3 Encode scenario rules

Include:
	•	challenger definition
	•	S5 derivation/removal logic

Deliverables
	•	scenario engine
	•	validation checks

Exit criteria
	•	Scenarios execute exactly as documented.

⸻

Phase 13 — Monte Carlo Runs and Output Validation

Goal: generate and validate publishable scenario outputs.

13.1 Run S0–S5

Create:
	•	artifacts/scenario_outputs.csv

13.2 Validate outputs

Checks:
	•	P10 ≤ P50 ≤ P90
	•	intervals not narrower than calibration logic permits
	•	no impossible values
	•	all in-scope boroughs covered

13.3 Failure handling

If a scenario fails validation:
	•	remove only that scenario if necessary
	•	log reason
	•	rerun cleanly

Deliverables
	•	validated scenario outputs
	•	validation log

Exit criteria
	•	Scenario outputs are stable and defensible.

⸻

Phase 14 — Publication 2: Scenarios and Uncertainty

Goal: publish scenario analysis without drifting into forecast language.

14.1 Write scenario narrative

Explain:
	•	what each scenario means
	•	what would falsify it
	•	why bands are wide
	•	where uncertainty is transferred vs observed

14.2 Build dashboard

Charts:
	•	Tier 3 shock map
	•	scenario selector
	•	P10/P50/P90 bands
	•	battleground borough ranking

14.3 Publish

Complete:
	•	reports/part2_article.md

Deliverables
	•	Part 2 article
	•	scenario dashboard
	•	screenshots/archive

Exit criteria
	•	Part 2 is public and methodologically consistent.

⸻

Phase 15 — Model Lock

Goal: freeze the system before live results.

15.1 Finalise audit script

Complete and test:
	•	src/civic_lens/audit_results.py

Must run end-to-end on mock or historical data before lock.

15.2 Lock the model

Populate:
	•	code SHA
	•	scenario SHA
	•	RNG seed
	•	volatility formula
	•	freeze timestamp

Write:
	•	artifacts/model_lock.txt

15.3 Tag release

Tag Git state and archive lock evidence.

Deliverables
	•	model lock artefact
	•	tagged release

Exit criteria
	•	No post-lock model changes allowed.

⸻

Phase 16 — Election Night Readiness

Goal: be able to operate without improvisation.

16.1 Finalise runsheet

Complete:
	•	docs/ELECTION_NIGHT_RUNSHEET.md

16.2 Rehearse live flow

Test:
	•	result ingestion
	•	schema validation
	•	dashboard refresh
	•	PNG fallback export
	•	audit script dry run

16.3 Define go/no-go thresholds

Examples:
	•	minimum result completeness before publishing
	•	validation error thresholds
	•	fallback publishing rules

Deliverables
	•	runsheet
	•	readiness checklist
	•	dry-run evidence

Exit criteria
	•	Election night can run from checklist alone.

⸻

Phase 17 — Live Result Ingestion

Goal: ingest actual 2026 results and compute realised metrics.

17.1 Ingest live results

Pull from chosen result source into canonical schema.

17.2 Validate

Check:
	•	schema integrity
	•	duplicate wards
	•	missing authorities
	•	turnout/value plausibility

17.3 Compute actuals

Produce actual:
	•	2022→2026 metrics
	•	realised borough outputs

Deliverables
	•	actual 2026 clean results
	•	actual 2022→2026 metrics

Exit criteria
	•	Actual results dataset is valid and complete enough to audit.

⸻

Phase 18 — Accuracy Audit

Goal: test the frozen system publicly against reality.

18.1 Run audit

Feed actual results against frozen scenario outputs.

Measure:
	•	MAE
	•	interval coverage
	•	ranking quality
	•	overconfidence
	•	systematic misses

18.2 Publish Part 3

Complete:
	•	reports/part3_template.md

Include freeze statement verbatim.

18.3 Archive election-night evidence

Store:
	•	screenshots
	•	snapshots
	•	logs
	•	decisions made during live ops

Deliverables
	•	Part 3 accuracy report
	•	archived evidence

Exit criteria
	•	Accuracy report is publicly published within 48 hours.

⸻

Phase 19 — Final Wrap-Up

Goal: leave the repo reusable, credible, and citation-ready.

19.1 Clean and polish

Update:
	•	README
	•	methodology
	•	decisions log
	•	final file references

19.2 Final release

Tag final project version.

19.3 Write retrospective

Summarise:
	•	what worked
	•	what failed
	•	what would improve in Civic Lens v2

Deliverables
	•	final release
	•	final retrospective
	•	fully documented repo

Exit criteria
	•	Project is complete and reusable.

⸻

Hard Gates You Should Not Skip

These are the non-negotiables:
	1.	No cleaning before raw audit is complete
	2.	No scenario modelling before calibration limitation is documented
	3.	No publication before QA passes
	4.	No model lock before audit script is tested
	5.	No live publishing without validation thresholds
	6.	No post-election narrative before running the audit

⸻

Best Working Sequence From Right Now

From your current state, the next phases should be executed in this exact order:
	1.	Phase 0 — Governance Lock
	2.	Phase 1 — Raw Data Audit
	3.	Phase 2 — Canonical Schema and Metric Contract
	4.	Phase 3 — Metric Engine Foundation
	5.	Phase 4 — Source Ingestion
	6.	Phase 5 — Election Results Cleaning and Standardisation
	7.	Phase 6 — Geography, Scope, and Authority Metadata
	8.	Phase 7 — Concordance and Harmonisation
	9.	Phase 8 — QA and Source Validation
	10.	Phase 9 — Baseline Metrics
	11.	Phase 10 — Tier-Specific Calibration and Shock Logic
	12.	Phase 11 — Publication 1
	13.	Phase 12 — Scenario Engine
	14.	Phase 13 — Monte Carlo Runs and Validation
	15.	Phase 14 — Publication 2
	16.	Phase 15 — Model Lock
	17.	Phase 16 — Election Night Readiness
	18.	Phase 17 — Live Result Ingestion
	19.	Phase 18 — Accuracy Audit
	20.	Phase 19 — Final Wrap-Up