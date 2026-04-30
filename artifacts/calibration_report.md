# Civic Lens - Calibration Report

**Generated:** 2026-04-11  
**Calibration chain:** 2014->2018 (training) / 2018->2022 (backtest) / 2022->2026 (prediction)  
**Authorities calibrated:** 69 borough-level rows  
**Ward-level backtest:** Not available under current concordance artifact

---

## 1. Summary Statistics by Metric and Tier

| metric | tier | n | RMSE | MAE | mean_error | std_error | pct_positive | p10 | p90 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| volatility_score | 1 | 30 | 29.4077 | 27.1743 | 26.2234 | 13.5370 | 96.6667 | 13.6469 | 37.9515 |
| volatility_score | 2 | 32 | 32.4093 | 31.0779 | 31.0779 | 9.3411 | 100.0000 | 20.7930 | 42.5258 |
| volatility_score | 3 | 5 | 29.6677 | 29.0934 | 29.0934 | 6.4948 | 100.0000 | 24.8155 | 35.6721 |
| delta_fi | 1 | 30 | 1.6916 | 1.5655 | 1.4905 | 0.8137 | 93.3333 | 0.6959 | 2.2958 |
| delta_fi | 2 | 32 | 1.6833 | 1.5628 | 1.5612 | 0.6394 | 96.8750 | 0.8283 | 2.2447 |
| delta_fi | 3 | 5 | 1.6191 | 1.5598 | 1.5598 | 0.4853 | 100.0000 | 1.0988 | 2.0771 |
| turnout_delta | 1 | 30 | 12.8065 | 7.8854 | 5.2243 | 11.8923 | 70.0000 | -5.8819 | 11.8256 |
| turnout_delta | 2 | 32 | 15.0612 | 14.4154 | 14.4154 | 4.4326 | 100.0000 | 9.8428 | 19.4257 |
| turnout_delta | 3 | 5 | 18.5106 | 11.6028 | 8.1400 | 18.5871 | 80.0000 | -5.1086 | 27.0291 |
| swing_concentration | 1 | 30 | 1.7429 | 1.4337 | 1.1743 | 1.3099 | 80.0000 | -0.4300 | 2.7795 |
| swing_concentration | 2 | 32 | 2.0686 | 1.7838 | 1.4972 | 1.4503 | 84.3750 | -0.7314 | 3.1148 |
| swing_concentration | 3 | 5 | 2.4475 | 2.0534 | 2.0534 | 1.4890 | 100.0000 | 1.1379 | 3.5479 |

## 2. Fit Quality Assessment

- volatility_score: n=67, RMSE=30.8963, MAE=29.1819, mean_error=28.7561.
- delta_fi: n=67, RMSE=1.6823, MAE=1.5638, mean_error=1.5294.
- turnout_delta: n=67, RMSE=14.3995, MAE=11.2816, mean_error=9.8317.
- swing_concentration: n=67, RMSE=1.9624, MAE=1.6472, mean_error=1.3941.

## 3. Systematic Biases

### 3.1 Brexit-era training window
VOL mean_error is 28.7561; this implies net underestimation in 2018->2022 versus training baseline.

### 3.2 LEAP-only era (2014/2015) training exposure
Estimated RMSE ratio (high leap-only exposure / low exposure) = 1.0751.

## 4. Individual Borough Outliers

- Solihull (E08000029): volatility_score_error=63.9720 (> 2x tier 1 RMSE 29.4077)

## 5. Fallback Authorities

- Barnsley (E08000016): all_out_2026_lgbce_review
- Birmingham (E08000025): all_out_2026_lgbce_review
- Coventry (E08000026): all_out_2026_lgbce_review
- Rotherham (E08000018): missing_training_and_backtest_metrics
- St. Helens (E08000013): all_out_2026_lgbce_review
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
