# Portfolio A+B+Slot B SHORT Promotion Gate

Date: 2026-05-07
Status: `SLOT_B_SHORT_PROMOTION_GATE_PASS_RUNTIME_PREPARED`
Branch: `codex/post-promotion-control-20260430`

## Decision

Verdict: `PROMOTE_SLOT_B_SHORT_OVERLAY`.

Approved runtime portfolio:

| slot | strategy id | role |
| --- | --- | --- |
| Slot A LONG | `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter` | BTC 4h trend continuation |
| Slot B LONG | `donchian_range_fade_4h_range_width_cv_013` | BTC/ETH 4h lower-bound range fade |
| Slot B SHORT | `donchian_range_fade_4h_range_width_cv_013_short` | BTC/ETH 4h upper-bound range fade |

Rejected for this promotion:

| slot | strategy id | reason |
| --- | --- | --- |
| Slot A SHORT | `macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter` | Stress-window drawdown source; keep research-only |

## Gate Evidence

Source artifact:

- `reports/portfolio_a_b_short_ablation_research.md`
- `extensions/Backtesting/results/portfolio_ab_bidirectional/short_ablation/portfolio_ab_short_ablation_summary.json`

| matrix | variant | trades | long_trades | short_trades | net_pnl | pnl_delta_vs_long_only | max_dd_pct | dd_delta_vs_long_only | Slot B SHORT pnl | run_errors |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default | `slot_b_short_overlay` | 62 | 53 | 9 | 2319.6818 | +69.9791 | 2.7900 | -1.5244 | 483.1704 | 0 |
| supplemental | `slot_b_short_overlay` | 233 | 159 | 74 | 8994.3783 | +1478.4073 | 6.0766 | +0.8996 | 2090.2808 | 0 |
| custom `2026_01_01_2026_04_30` | `slot_b_short_overlay` | 13 | 9 | 4 | 254.9239 | n/a | 2.1778 | n/a | 171.4041 | 0 |

Promotion-style gates:

| gate | value | threshold | result |
| --- | ---: | ---: | --- |
| supplemental max_dd_pct | 6.0766 | 8.0000 | PASS |
| default max_dd_pct | 2.7900 | 8.0000 | PASS |
| custom 2026-01..04 max_dd_pct | 2.1778 | 8.0000 | PASS |
| run_errors | 0 | 0 | PASS |
| entry_stop_violations | 0 | 0 | PASS |
| Slot B SHORT supplemental router block rate | 0.0769 | 0.5000 | PASS |
| Slot B SHORT default router block rate | 0.0909 | 0.5000 | PASS |
| same-symbol same-entry LONG/SHORT collision count | 0 | 0 | PASS |

Critical stress window:

| variant | window | trades | net_pnl | max_dd_pct | Slot A SHORT pnl | Slot B SHORT pnl |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| long-only reference | `classic_rollercoaster_2021_2022` | 50 | 2797.7194 | 5.1770 | 0.0000 | 0.0000 |
| Slot A SHORT overlay | `classic_rollercoaster_2021_2022` | 96 | 141.8197 | 19.4678 | -2508.9498 | 0.0000 |
| Slot B SHORT overlay | `classic_rollercoaster_2021_2022` | 91 | 3961.2237 | 6.0766 | 0.0000 | 1207.6330 |
| all-four reference | `classic_rollercoaster_2021_2022` | 129 | 1585.3271 | 14.3409 | -2226.9271 | 1197.3162 |

Read: Slot B SHORT improves the promoted A+B portfolio while staying near the existing drawdown envelope. Slot A SHORT is the drawdown source and must not be bundled into runtime defaults.

## Runtime Control Prep

Runtime defaults are prepared for the three-leg portfolio:

| Config item | value |
| --- | --- |
| `STRATEGY_RUNTIME_ENABLED` | `True` |
| `STRATEGY_RUNTIME_SIDE_FILTER` | `"both"` |
| `ENABLED_STRATEGIES` | Slot A LONG + Slot B LONG + Slot B SHORT |
| `SYMBOLS` | `["BTC/USDT", "ETH/USDT"]` |
| `USE_SCANNER_SYMBOLS` | `False` |
| `SCANNER_UNIVERSE_ENABLED` | `False` |
| `RISK_PER_TRADE` | `0.017` |
| `MAX_TOTAL_RISK` | `0.0642` |
| `STRATEGY_ROUTER_POLICY` | `"fail_closed"` |

Runtime boundary:

- Slot B SHORT is promoted only through `Config.ENABLED_STRATEGIES`.
- Slot A SHORT remains implemented, tested, and catalog-present for research, but is not runtime-enabled.
- Scanner universe remains observe-only; no scanner activation is included.
- No credentials, router policy, production scanner defaults, or live/testnet service state were changed.

## Caveats

- Validation windows overlap; totals are promotion evidence, not live expectancy guarantees.
- Current `StrategyRuntime` still does not enforce `BTC_TREND_FILTER_ENABLED` as a plugin-entry reject or size-zero multiplier.
- Slot B SHORT has one small negative supplemental cell: `range_low_vol` Slot B SHORT pnl `-11.2717`; this is not promotion-blocking but should remain monitored.
- Slot A SHORT requires a separate failure-attribution lane before any future promotion attempt.

## Next Checks

Before handoff or commit:

```bash
python -c "from trader.config import Config; Config.validate(); print('Config.validate PASS')"
python -m pytest trader/tests extensions/Backtesting/tests -q
```
