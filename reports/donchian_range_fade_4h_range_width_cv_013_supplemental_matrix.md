# donchian_range_fade_4h_range_width_cv_013 Supplemental Matrix

Date: 2026-04-29  
Status: `PHASE_2_1_REVALIDATION`

## Scope

- Candidate: `donchian_range_fade_4h_range_width_cv_013`
- Runner:
  `python -m extensions.Backtesting.scripts.run_supplemental_matrix --candidate donchian_range_fade_4h_range_width_cv_013`
- Results root:
  `extensions/Backtesting/results/custom_windows/donchian_range_fade_4h_range_width_cv_013`
- Summary artifact:
  `extensions/Backtesting/results/custom_windows/donchian_range_fade_4h_range_width_cv_013/supplemental_matrix_summary.json`
- Symbol slices keep the full BTC/ETH market universe available and restrict only plugin emission by `strategy_params_override={"symbol": ...}`.

## Headline

| scope | trades | net_pnl | max_window_dd_pct | run_errors |
| --- | ---: | ---: | ---: | ---: |
| combined | 61 | 2722.0087 | 4.5660 | 0 |
| BTC/USDT slices | 37 | 1807.9676 | 2.1908 | 0 |
| ETH/USDT slices | 24 | 914.0412 | 3.5115 | 0 |

## Combined Matrix

| window | start | end | trades | net_pnl | max_dd_pct | run_errors |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `bull_strong_up_1` | 2024-10-01 | 2025-03-31 | 5 | 158.6374 | 0.7039 | 0 |
| `bear_persistent_down` | 2025-04-01 | 2025-08-31 | 7 | 161.5037 | 0.6442 | 0 |
| `range_low_vol` | 2025-09-01 | 2025-12-31 | 2 | 106.4633 | 0.0000 | 0 |
| `bull_recovery_2026` | 2026-01-01 | 2026-02-28 | 0 | 0.0000 | 0.0000 | 0 |
| `ftx_style_crash` | 2022-11-01 | 2022-12-31 | 1 | 30.0738 | 0.6908 | 0 |
| `sideways_transition` | 2023-06-01 | 2023-09-30 | 1 | 43.8883 | 0.6136 | 0 |
| `classic_rollercoaster_2021_2022` | 2021-01-01 | 2022-12-31 | 25 | 1185.6837 | 4.5660 | 0 |
| `recovery_2023_2024` | 2023-01-01 | 2024-12-31 | 20 | 1035.7585 | 2.1275 | 0 |

## Per-Symbol Slices

| window | symbol | trades | net_pnl | max_dd_pct | run_errors |
| --- | --- | ---: | ---: | ---: | ---: |
| `bull_strong_up_1` | BTC/USDT | 2 | 70.0084 | 0.0000 | 0 |
| `bull_strong_up_1` | ETH/USDT | 3 | 88.6290 | 0.7039 | 0 |
| `bear_persistent_down` | BTC/USDT | 7 | 161.5037 | 0.6442 | 0 |
| `bear_persistent_down` | ETH/USDT | 0 | 0.0000 | 0.0000 | 0 |
| `range_low_vol` | BTC/USDT | 2 | 106.4633 | 0.0000 | 0 |
| `range_low_vol` | ETH/USDT | 0 | 0.0000 | 0.0000 | 0 |
| `bull_recovery_2026` | BTC/USDT | 0 | 0.0000 | 0.0000 | 0 |
| `bull_recovery_2026` | ETH/USDT | 0 | 0.0000 | 0.0000 | 0 |
| `ftx_style_crash` | BTC/USDT | 0 | 0.0000 | 0.0000 | 0 |
| `ftx_style_crash` | ETH/USDT | 1 | 30.0738 | 0.6908 | 0 |
| `sideways_transition` | BTC/USDT | 1 | 43.8883 | 0.6136 | 0 |
| `sideways_transition` | ETH/USDT | 0 | 0.0000 | 0.0000 | 0 |
| `classic_rollercoaster_2021_2022` | BTC/USDT | 13 | 940.9117 | 2.0107 | 0 |
| `classic_rollercoaster_2021_2022` | ETH/USDT | 12 | 244.7720 | 3.5115 | 0 |
| `recovery_2023_2024` | BTC/USDT | 12 | 485.1922 | 2.1908 | 0 |
| `recovery_2023_2024` | ETH/USDT | 8 | 550.5664 | 1.1560 | 0 |

## Read

- The candidate remains mechanically clean in supplemental coverage: every non-zero window is positive and `run_errors = 0`.
- The distribution is BTC-heavy: BTC slices contribute 37 of 61 trades and 66.4% of supplemental net PnL.
- ETH is not dead, but it is episodic: it contributes in `bull_strong_up_1`, `ftx_style_crash`, `classic_rollercoaster_2021_2022`, and `recovery_2023_2024`.
- The weak-tape 2025 surface is almost entirely BTC-driven:
  `bear_persistent_down` has 7 BTC trades / 0 ETH trades, and `range_low_vol` has 2 BTC trades / 0 ETH trades.
- `bull_recovery_2026` cleanly emits no trades; that is acceptable discipline, not starvation by itself.
- The long windows dominate the supplemental PnL:
  `classic_rollercoaster_2021_2022` + `recovery_2023_2024` produce 45 of 61 trades and 2221.4422 net PnL.

## Regime Caveat

These supplemental labels are research-window names, not arbiter classifications. The generated report still classifies most 4h bars as BTC `TRENDING` in every window, including `range_low_vol` at 81.5% TRENDING and 18.5% RANGING.

So the right read is not "Donchian is a pure RANGING engine." The stricter read is:

- the cartridge can emit structural range-fade trades inside broader BTC trend-classified windows
- default candidate review already woke the declared `RANGING` surface from 0 to 2 trades
- supplemental per-symbol attribution shows the current live edge is still mostly BTC and long-window dependent

## Decision

Keep `donchian_range_fade_4h_range_width_cv_013` as Slot B `KEEP_RESEARCH_ONLY`.

This matrix supports continuing to Phase 2.2 robustness validation, but it does not justify promotion or another structural child cartridge. The frozen Donchian read still stands unless the `touch_atr_band` sweep exposes parameter fragility.
