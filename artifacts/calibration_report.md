# Civic Lens - Calibration Report

**Generated:** 2026-04-30  
**Calibration chain:** 2014->2018 (training) / 2018->2022 (backtest) / 2022->2026 (prediction)  
**Authorities calibrated:** 69 borough-level rows  
**Ward-level backtest:** Not available under current concordance artifact

---

## 1. Summary Statistics by Metric and Tier

| metric | tier | n | RMSE | MAE | mean_error | std_error | pct_positive | p10 | p90 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| volatility_score | 1 | 30 | 17.4158 | 11.8654 | 8.9256 | 15.2103 | 66.6667 | -4.8929 | 25.3354 |
| volatility_score | 2 | 32 | 19.4946 | 16.4828 | 14.4957 | 13.2437 | 87.5000 | 0.0266 | 29.9472 |
| volatility_score | 3 | 5 | 16.2356 | 13.3039 | 13.3039 | 10.4044 | 100.0000 | 3.2776 | 24.3821 |
| delta_fi | 1 | 30 | 0.8321 | 0.6856 | 0.1932 | 0.8232 | 63.3333 | -0.8283 | 1.0808 |
| delta_fi | 2 | 32 | 0.5120 | 0.4395 | 0.0080 | 0.5201 | 53.1250 | -0.7543 | 0.6994 |
| delta_fi | 3 | 5 | 0.4785 | 0.4596 | -0.2100 | 0.4808 | 40.0000 | -0.5687 | 0.3297 |
| turnout_delta | 1 | 30 | 12.8065 | 7.8854 | 5.2243 | 11.8923 | 70.0000 | -5.8819 | 11.8256 |
| turnout_delta | 2 | 32 | 15.0612 | 14.4154 | 14.4154 | 4.4326 | 100.0000 | 9.8428 | 19.4257 |
| turnout_delta | 3 | 5 | 18.5106 | 11.6028 | 8.1400 | 18.5871 | 80.0000 | -5.1086 | 27.0291 |
| swing_concentration | 1 | 30 | 1.1913 | 0.9146 | 0.5628 | 1.0680 | 73.3333 | -0.6046 | 1.9111 |
| swing_concentration | 2 | 32 | 1.6707 | 1.4244 | 1.0259 | 1.3397 | 81.2500 | -0.9023 | 2.7301 |
| swing_concentration | 3 | 5 | 1.5707 | 1.1499 | 0.9707 | 1.3805 | 80.0000 | -0.2309 | 2.4187 |

## 2. Fit Quality Assessment

- volatility_score: n=67, RMSE=18.3574, MAE=14.1781, mean_error=11.9127.
- delta_fi: n=67, RMSE=0.6725, MAE=0.5512, mean_error=0.0747.
- turnout_delta: n=67, RMSE=14.3995, MAE=11.2816, mean_error=9.8317.
- swing_concentration: n=67, RMSE=1.4672, MAE=1.1757, mean_error=0.8144.

## 3. Systematic Biases

### 3.1 Brexit-era training window
VOL mean_error is 11.9127; this implies net underestimation in 2018->2022 versus training baseline.

### 3.2 LEAP-only era (2014/2015) training exposure
Estimated RMSE ratio (high leap-only exposure / low exposure) = 1.1168.

## 4. Individual Borough Outliers

- Solihull (E08000029): volatility_score_error=61.5217 (> 2x tier 1 RMSE 17.4158)

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
