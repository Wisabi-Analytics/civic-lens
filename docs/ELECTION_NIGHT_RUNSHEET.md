# Election Night Runsheet

**Date:** 7 May 2026  
**Status:** Template — populate after L2 pipeline test (Task L2, 2 May)

---

## Pre-Night Checklist (by 10pm May 7th)

- [ ] `artifacts/scenario_outputs.csv` frozen and committed
- [ ] `artifacts/model_lock.txt` committed with SHA hash
- [ ] `src/audit/audit_results.py` tested against 2025 mock data
- [ ] `reports/part3_template.md` pre-written with placeholders
- [ ] Fallback snapshots script tested: `python export_snapshots.py --test`
- [ ] Google Analytics and Tableau tabs open
- [ ] `docs/ELECTION_NIGHT_RUNSHEET.md` (this file) open

---

## Live Update Protocol (from ~11pm)

*(Populate from live_test_log.md after Task L2 test run)*

**Step 1 — Ingest batch results**
```bash
python src/calibration/run_backtest.py --live [path/to/results.csv]
```

**Step 2 — Refresh Tableau**
- Publish updated data source to Tableau Public
- Wait max 15 mins — if longer, activate fallback

**Fallback:**
```bash
python export_snapshots.py --timestamp $(date +%Y-%m-%d_%H-%M)
# Upload PNG to wisabianalytics.com/live
# Post URL to LinkedIn
```

**Step 3 — Screenshot Tableau analytics**
- 11pm — screenshot concurrent viewers
- 1am — screenshot
- 3am — screenshot
- Final count — screenshot
- Save all to `artifacts/election_night/snapshots/`

---

## Post-Night (9 May — within 48hrs)

```bash
python src/audit/audit_results.py artifacts/scenario_outputs.csv [actual_results.csv]
# Fill in reports/part3_template.md with outputs
# Publish Part 3 to wisabianalytics.com
# Email journalists who covered May 7th results
```
