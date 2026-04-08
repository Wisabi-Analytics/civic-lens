# Civic Lens - Calibration Report

**Generated:** 2026-04-08  
**Calibration chain:** 2014->2018 (training) / 2018->2022 (backtest) / 2022->2026 (prediction)  
**Authorities calibrated:** 69 borough-level rows  
**Ward-level backtest:** Not available under current concordance artifact

---

## 1. Summary Statistics by Metric and Tier

| metric | tier | n | RMSE | MAE | mean_error | std_error | pct_positive | p10 | p90 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| volatility_score | 1 | 28 | 33.0970 | 30.8901 | 29.9519 | 14.3402 | 96.4286 | 12.9353 | 45.1320 |
| volatility_score | 2 | 32 | 31.5883 | 29.7711 | 29.7711 | 10.7284 | 100.0000 | 16.5299 | 44.1013 |
| volatility_score | 3 | 5 | 30.0537 | 29.5424 | 29.5424 | 6.1718 | 100.0000 | 25.8106 | 35.6721 |
| delta_fi | 1 | 28 | 1.6057 | 1.4545 | 1.3548 | 0.8776 | 89.2857 | 0.4182 | 2.3544 |
| delta_fi | 2 | 32 | 1.8688 | 1.6384 | 1.5955 | 0.9885 | 90.6250 | 0.6911 | 2.0335 |
| delta_fi | 3 | 5 | 1.7032 | 1.6446 | 1.6446 | 0.4956 | 100.0000 | 1.0988 | 2.0771 |
| turnout_delta | 1 | 28 | 13.3519 | 8.6637 | 4.0671 | 12.9508 | 64.2857 | -8.5450 | 12.1095 |
| turnout_delta | 2 | 32 | 15.9689 | 14.7246 | 14.3075 | 7.2057 | 96.8750 | 8.2227 | 21.8096 |
| turnout_delta | 3 | 5 | 18.6863 | 11.6848 | 8.2220 | 18.7609 | 80.0000 | -5.1086 | 27.2753 |
| swing_concentration | 1 | 28 | 1.8412 | 1.5742 | 1.3030 | 1.3247 | 82.1429 | -0.2793 | 2.5805 |
| swing_concentration | 2 | 32 | 2.0993 | 1.9150 | 1.7792 | 1.1320 | 93.7500 | 0.5444 | 3.1178 |
| swing_concentration | 3 | 5 | 2.4257 | 2.0032 | 2.0032 | 1.5295 | 100.0000 | 1.0017 | 3.5479 |

## 2. Fit Quality Assessment

- volatility_score: n=65, RMSE=32.1339, MAE=30.2356, mean_error=29.8314.
- delta_fi: n=65, RMSE=1.7473, MAE=1.5597, mean_error=1.4956.
- turnout_delta: n=65, RMSE=15.1392, MAE=11.8799, mean_error=9.4281.
- swing_concentration: n=65, RMSE=2.0205, MAE=1.7750, mean_error=1.5913.

## 3. Systematic Biases

### 3.1 Brexit-era training window
VOL mean_error is 29.8314; this implies net underestimation in 2018->2022 versus training baseline.

### 3.2 LEAP-only era (2014/2015) training exposure
Estimated RMSE ratio (high leap-only exposure / low exposure) = 0.9429.

## 4. Individual Borough Outliers

- None above 2x tier RMSE for volatility_score.

## 5. Fallback Authorities

- Barnsley (E08000016): all_out_2026_lgbce_review
- Birmingham (E08000025): all_out_2026_lgbce_review
- Coventry (E08000026): all_out_2026_lgbce_review
- Oldham (E08000004): missing_training_and_backtest_metrics
- Rotherham (E08000018): missing_training_and_backtest_metrics
- St. Helens (E08000013): all_out_2026_lgbce_review
- Tameside (E08000008): missing_training_and_backtest_metrics
- City of London (E09000001): missing_training_and_backtest_metrics
- Calderdale (E08000033): all_out_2026_lgbce_review
- Kirklees (E08000034): all_out_2026_lgbce_review

## 6. Calibration Limitations

- No ward-level backtest available under current concordance artifact.
- Single observed backtest cycle per borough; uncertainty is pooled by tier.
- City of London handling note: Training VOL=NA, Backtest VOL=24.4880; this creates a null error and routes City of London to tier fallback.
- 2018->2022 includes COVID-era disruption and may not represent a stationary regime.

## 7. Disclosure Statement

> "Uncertainty bands are calibrated from borough-specific forecast errors measured across the 2014->2022 window (training: 2014->2018; backtest: 2018->2022). The training period predates the 2025 Reform surge. Uncertainty bands may understate right-wing volatility in areas of high recent Reform support. This is a stated assumption, not an observed measurement."
