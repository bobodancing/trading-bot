# Slot A SHORT Snapback Guard Experiment

Date: 2026-05-07
Status: `RESEARCH_ONLY_REPAIR_EXPERIMENT_SECOND_PASS`

## Scope

- Goal: falsify or validate the late-breakdown / snapback guard direction from Slot A SHORT failure attribution.
- This is not a promotion review and does not change runtime defaults.
- The baseline row reuses existing Slot A SHORT overlay artifacts when present; guard rows run disabled research plugins.
- The full `classic_rollercoaster_2021_2022` guard backtest timed out before writing artifacts, so this first pass uses targeted failure-month diagnostics plus one positive-control window.
- Summary artifact: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_bidirectional\slot_a_short_snapback_guard\slot_a_short_snapback_guard_summary.json`

## Verdict

Verdict: `V2_EXHAUSTION_GUARD_MATCHES_V1_ON_DIAGNOSTICS_NOT_PROMOTION_READY`.

V1 materially improves the known failure-month signature but is blunt. The first vote-only V2 was too permissive, so the current V2 requires follow-through votes plus no overextension exhaustion. On the targeted diagnostics it matches V1's defensive result; this validates the exhaustion guard direction but still does not prove that V2 preserves profitable late bearish continuation.

## Results

| variant | window | portfolio_trades | portfolio_net_pnl | max_dd_pct | slot_a_short_trades | slot_a_short_net_pnl | slot_a_short_win_rate | slot_a_short_pf | slot_a_short_avg_r | slot_a_short_avg_mfe_pct | slot_a_short_avg_mae_pct | slot_a_short_sl_hits | slot_a_short_zero_h_sl_hits | run_errors |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `slot_a_short_overlay_baseline` | `stress_2022_01` | 5 | 17.2559 | 6.0989 | 2 | -276.9231 | 0.0000 | 0.0000 | -0.8400 | 0.0000 | -4.9317 | 2 | 1 | 0 |
| `slot_a_short_overlay_baseline` | `stress_2022_02` | 9 | -51.8563 | 3.1211 | 5 | -591.2605 | 0.2000 | 0.0073 | -0.7320 | 0.3919 | -3.7196 | 3 | 2 | 0 |
| `slot_a_short_overlay_baseline` | `stress_2022_09` | 4 | -402.6481 | 4.5986 | 4 | -402.6481 | 0.0000 | 0.0000 | -0.7825 | 0.7186 | -2.8562 | 3 | 1 | 0 |
| `slot_a_short_overlay_baseline` | `bull_recovery_2026` | 4 | 601.7713 | 3.8584 | 4 | 601.7713 | 0.5000 | 5.2358 | 1.4600 | 7.2988 | -1.5727 | 2 | 1 | 0 |
| `slot_a_short_snapback_guard_overlay` | `stress_2022_01` | 3 | 294.1790 | 2.1054 | 0 | 0.0000 | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| `slot_a_short_snapback_guard_overlay` | `stress_2022_02` | 4 | 539.4043 | 0.0000 | 0 | 0.0000 | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| `slot_a_short_snapback_guard_overlay` | `stress_2022_09` | 1 | -64.1542 | 1.3288 | 1 | -64.1542 | 0.0000 | 0.0000 | -0.5500 | 0.5646 | -2.4748 | 1 | 0 | 0 |
| `slot_a_short_snapback_guard_overlay` | `bull_recovery_2026` | 2 | 743.8405 | 3.8068 | 2 | 743.8405 | 1.0000 | n/a | 4.0050 | 14.5976 | -1.5352 | 0 | 0 | 0 |
| `slot_a_short_followthrough_guard_overlay` | `stress_2022_01` | 3 | 294.1790 | 2.1054 | 0 | 0.0000 | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| `slot_a_short_followthrough_guard_overlay` | `stress_2022_02` | 4 | 539.4043 | 0.0000 | 0 | 0.0000 | 0.0000 | n/a | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 0 |
| `slot_a_short_followthrough_guard_overlay` | `stress_2022_09` | 1 | -64.1542 | 1.3288 | 1 | -64.1542 | 0.0000 | 0.0000 | -0.5500 | 0.5646 | -2.4748 | 1 | 0 | 0 |
| `slot_a_short_followthrough_guard_overlay` | `bull_recovery_2026` | 2 | 743.8405 | 3.8068 | 2 | 743.8405 | 1.0000 | n/a | 4.0050 | 14.5976 | -1.5352 | 0 | 0 | 0 |

## Delta Vs Baseline

| variant | window | portfolio_net_pnl_delta | max_dd_pct_delta | slot_a_short_trade_delta | slot_a_short_net_pnl_delta | zero_h_sl_hit_delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `slot_a_short_snapback_guard_overlay` | `stress_2022_01` | 276.9231 | -3.9935 | -2 | 276.9231 | -1 |
| `slot_a_short_snapback_guard_overlay` | `stress_2022_02` | 591.2606 | -3.1211 | -5 | 591.2605 | -2 |
| `slot_a_short_snapback_guard_overlay` | `stress_2022_09` | 338.4939 | -3.2698 | -3 | 338.4939 | -1 |
| `slot_a_short_snapback_guard_overlay` | `bull_recovery_2026` | 142.0692 | -0.0516 | -2 | 142.0692 | -1 |
| `slot_a_short_followthrough_guard_overlay` | `stress_2022_01` | 276.9231 | -3.9935 | -2 | 276.9231 | -1 |
| `slot_a_short_followthrough_guard_overlay` | `stress_2022_02` | 591.2606 | -3.1211 | -5 | 591.2605 | -2 |
| `slot_a_short_followthrough_guard_overlay` | `stress_2022_09` | 338.4939 | -3.2698 | -3 | 338.4939 | -1 |
| `slot_a_short_followthrough_guard_overlay` | `bull_recovery_2026` | 142.0692 | -0.0516 | -2 | 142.0692 | -1 |

## Read

- V1 answers whether late-breakdown blocking can remove the failure signature; these diagnostics say yes.
- V2 now blocks late breakdowns unless follow-through is confirmed and the breakdown is not overextended by close-through, downside move, or entry extension.
- In this diagnostic matrix V2 matches V1, so the repair is defensive but not yet differentiated from the blunt guard.
- The follow-up dry classifier completed and found V2 is not meaningfully differentiated from V1; a full `classic_rollercoaster_2021_2022` run is not recommended while this remains true.
- Any positive result here is repair-direction evidence only; it is not promotion evidence.
