# Portfolio A+B Promotion Review

Date: 2026-04-29
Status: `RUEI_APPROVED_RUNTIME_PROMOTED`

## Verdict

- Decision: `FIRST_PROMOTION_CANDIDATE_QUALIFIED_AND_RUEI_APPROVED`
- Ruei approved runtime promotion on 2026-04-29.
- Promotion landed through `5dee878` (catalog enablement) and `1933e65` (Config runtime defaults).
- Recovery backlog scheduling landed through `827b5a7`; no backlog alpha research starts during post-promotion control.
- BTC trend filter enforcement remains report-only for plugin entries in current StrategyRuntime.

## Gate Snapshot

| gate | value | threshold | result |
| --- | --- | --- | --- |
| portfolio max_dd_pct | 5.1770 | 8.0000 | PASS |
| max same-symbol same-candle A+B emits | 0 | 5 | PASS |
| Slot A aggregate router block rate | 0.1946 | 0.5000 | PASS |
| Slot B aggregate router block rate | 0.2222 | 0.5000 | PASS |

## Matrix Totals

| matrix | trades | net_pnl | max_dd_pct | run_errors | max_overlap |
| --- | --- | --- | --- | --- | --- |
| default | 59 | 2249.7027 | 4.3144 | 0 | 0 |
| supplemental | 156 | 7515.9710 | 5.1770 | 0 | 0 |

## Drawdown Concentration

| matrix | window | trades | net_pnl | max_dd_pct | overlap |
| --- | --- | --- | --- | --- | --- |
| supplemental | classic_rollercoaster_2021_2022 | 50 | 2797.7194 | 5.1770 | 0 |
| default | TRENDING_UP | 32 | 1757.4222 | 4.3144 | 0 |
| supplemental | recovery_2023_2024 | 65 | 3281.2602 | 4.1090 | 0 |
| supplemental | bull_strong_up_1 | 11 | 754.3417 | 2.4695 | 0 |
| default | MIXED | 24 | 404.8474 | 2.3435 | 0 |

## Slot Attribution

Validation windows overlap; this is attribution across the validation pack, not a live expectancy estimate.

| slot | trades | win_rate | net_pnl | profit_factor | avg_r | avg_mae_pct |
| --- | --- | --- | --- | --- | --- | --- |
| Slot A | 139 | 0.4532 | 6476.5332 | 2.5789 | 0.5604 | -1.2356 |
| Slot B | 76 | 0.8158 | 3289.1404 | 4.5344 | 0.3930 | -0.3209 |

## Symbol Attribution

| symbol | trades | win_rate | net_pnl | profit_factor | avg_r |
| --- | --- | --- | --- | --- | --- |
| BTC/USDT | 187 | 0.5561 | 8588.0987 | 2.9700 | 0.5253 |
| ETH/USDT | 28 | 0.7500 | 1177.5749 | 2.7498 | 0.3404 |

## Reject Totals

| slot | entries | rejects | router_block_rate | position_slot_occupied | strategy_router_blocked | cooldown | central_risk_blocked |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Slot A | 139 | 457 | 0.1946 | 320 | 116 | 21 | 0 |
| Slot B | 76 | 212 | 0.2222 | 88 | 64 | 52 | 8 |

## Top Losing Trades

| matrix | window | symbol | slot | entry_time | pnl_usdt | realized_r | mae_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| supplemental | classic_rollercoaster_2021_2022 | BTC/USDT | Slot A | 2021-04-30T13:00:00+00:00 | -194.3672 | -1.2500 | -4.4146 |
| supplemental | classic_rollercoaster_2021_2022 | ETH/USDT | Slot B | 2021-12-09T21:00:00+00:00 | -187.1377 | -1.1000 | -5.0589 |
| default | TRENDING_UP | BTC/USDT | Slot A | 2024-03-11T05:00:00+00:00 | -153.7519 | -1.2900 | -3.4918 |
| supplemental | recovery_2023_2024 | BTC/USDT | Slot A | 2024-03-11T05:00:00+00:00 | -153.7519 | -1.2900 | -3.4918 |
| supplemental | classic_rollercoaster_2021_2022 | ETH/USDT | Slot B | 2021-03-22T17:00:00+00:00 | -153.1048 | -1.1400 | -3.4974 |
| supplemental | classic_rollercoaster_2021_2022 | ETH/USDT | Slot B | 2022-04-22T13:00:00+00:00 | -137.9823 | -1.0500 | -3.1524 |
| default | TRENDING_UP | BTC/USDT | Slot A | 2024-02-26T13:00:00+00:00 | -133.5055 | -1.9500 | -3.0440 |
| supplemental | recovery_2023_2024 | BTC/USDT | Slot A | 2024-02-26T13:00:00+00:00 | -133.5055 | -1.9500 | -3.0440 |
| supplemental | classic_rollercoaster_2021_2022 | BTC/USDT | Slot A | 2021-02-06T01:00:00+00:00 | -117.8925 | -0.6900 | -2.7212 |
| supplemental | recovery_2023_2024 | BTC/USDT | Slot A | 2024-05-27T13:00:00+00:00 | -110.4031 | -1.3900 | -2.4902 |

## Read

- Main drawdown concentration is in long stress windows, not in same-candle A/B collisions.
- Slot B has visible `central_risk_blocked` only in the 2021-2022 stress pack, which is expected under Config default `MAX_TOTAL_RISK=0.0642` and should remain monitored.
- Risk sensitivity completed separately and kept approved sizing at `RISK_PER_TRADE=0.017`.
- Runtime promotion is complete; post-promotion control verifies default parity and smoke wiring in `reports/portfolio_ab_post_promotion_control.md`.
