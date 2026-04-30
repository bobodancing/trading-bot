# Portfolio A+B Risk Sensitivity

Date: 2026-04-29
Status: `RUEI_APPROVED_PROMOTION_SIZING`

## Scope

- Slot A: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- Slot B: `donchian_range_fade_4h_range_width_cv_013`
- Symbols: `BTC/USDT`, `ETH/USDT`
- `MAX_TOTAL_RISK`: Config default `0.0642`; intentionally not overridden.
- Ruei approved promotion sizing at `RISK_PER_TRADE=0.017`.

## Verdict

- Decision: `PASS - risk scaling remains within hard gates across the sensitivity pack; keep 0.017 as the approved runtime promotion sizing.`
- Recommended promotion-review sizing: `0.017`.
- This run did not change runtime defaults by itself; promotion later landed in `5dee878` and `1933e65` after Ruei approval.

## Sensitivity Summary

| risk | default_pnl | supp_pnl | total_pack_pnl | max_dd_pct | overlap | central_risk_blocked | Slot A router | Slot B router | gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.014 | 2242.8312 | 7183.6734 | 9426.5046 | 4.7786 | 0 | 8 | 0.1946 | 0.2222 | PASS |
| 0.017 | 2249.7027 | 7515.9710 | 9765.6737 | 5.1770 | 0 | 8 | 0.1946 | 0.2222 | PASS |
| 0.020 | 2251.3455 | 7719.1366 | 9970.4821 | 5.1162 | 0 | 8 | 0.1946 | 0.2222 | PASS |

## Linearity Vs 0.017

*Validation windows overlap; ratios are stability checks, not expected live scaling.*

| risk | risk_ratio | pnl_ratio | pnl_error | dd_ratio | dd_error | run_errors |
| --- | --- | --- | --- | --- | --- | --- |
| 0.014 | 0.8235 | 0.9653 | 0.1417 | 0.9230 | 0.0995 | 0 |
| 0.017 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 0 |
| 0.020 | 1.1765 | 1.0210 | -0.1555 | 0.9883 | -0.1882 | 0 |

## Read

- The main thing to watch is whether `central_risk_blocked` rises at 0.020 due to the unchanged Config default `MAX_TOTAL_RISK=0.0642`.
- A passing 0.020 result does not automatically justify promotion at 0.020; it only says the portfolio is not fragile around the 0.017 baseline.
- Runtime enablement is complete at the approved 0.017 sizing; 0.020 remains non-promoted evidence only.
