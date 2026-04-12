# R2 V54-in-RANGING 22 Trades Deep Dive

Generated: 2026-04-12

Scope: P0.6 deduped completed trades where `entry_regime == RANGING`, across `TRENDING_UP`, `TRENDING_DOWN`, `RANGING`, and `MIXED` windows.

Status: report only. No runtime code changed.

## Recommendation

**R3 = SKIP for now.**

V54 should remain the RANGING fallback executor until a later dataset shows a clearer gap. The current 22-trade sample does not justify adding a new range strategy yet.

## Baseline Metrics

| metric | value |
|---|---:|
| Unique completed trades | 22 |
| Profit factor | 2.1685 |
| Win rate | 54.5% |
| PnL | +169.31 USDT |
| Avg realized R | +0.3005R |
| Best realized R | +5.34R |
| Worst realized R | -1.21R |
| Max `max_r_reached` | 6.3625R |
| Max adverse excursion estimate | 1.21R |

Symbol mix:

| symbol | trades |
|---|---:|
| ETH/USDT | 8 |
| SOL/USDT | 4 |
| BTC/USDT | 4 |
| XRP/USDT | 3 |
| DOGE/USDT | 2 |
| BNB/USDT | 1 |

Exit mix:

| exit_reason | trades |
|---|---:|
| `sl_hit` | 11 |
| `stage1_timeout` | 9 |
| `v54_structure_break` | 2 |

## Trade Table

| entry_time | symbol | side | R | MaxR | capture | MAE R est. | hold h | exit | BTC ADX | BTC BBW pct50 | BTC BBW ratio | BTC ATR% |
|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| 2023-11-07 18:00 | XRP | LONG | 0.12 | 0.18 | 0.69 | 0.22 | 24 | stage1_timeout | 13.02 | 16 | 0.699 | 1.16 |
| 2023-11-25 01:00 | SOL | LONG | -0.17 | 0.20 | -0.84 | 0.23 | 24 | stage1_timeout | 21.50 | 78 | 1.195 | 1.28 |
| 2024-03-10 15:00 | ETH | LONG | -0.94 | 0.45 | -2.12 | 0.94 | 7 | sl_hit | 22.18 | 22 | 0.555 | 1.58 |
| 2024-03-11 00:00 | BTC | LONG | 0.48 | 0.48 | 1.00 | 0.00 | 1 | sl_hit | 20.23 | 16 | 0.529 | 1.67 |
| 2024-03-12 16:00 | ETH | LONG | 0.84 | 0.84 | 1.00 | 0.00 | 1 | sl_hit | 21.44 | 40 | 0.914 | 1.99 |
| 2024-03-12 16:00 | BTC | LONG | 0.77 | 0.77 | 1.00 | 0.00 | 1 | sl_hit | 21.44 | 40 | 0.914 | 1.99 |
| 2024-03-12 19:00 | BTC | LONG | 0.90 | 0.94 | 0.96 | 0.23 | 24 | stage1_timeout | 21.44 | 40 | 0.914 | 1.99 |
| 2024-03-12 19:00 | ETH | LONG | 0.16 | 0.68 | 0.24 | 0.32 | 24 | stage1_timeout | 21.44 | 40 | 0.914 | 1.99 |
| 2025-03-07 14:00 | SOL | SHORT | 1.44 | 1.94 | 0.74 | 0.64 | 39 | sl_hit | 16.81 | 12 | 0.728 | 2.96 |
| 2025-03-07 14:00 | ETH | SHORT | 0.63 | 1.86 | 0.34 | 0.00 | 23 | sl_hit | 16.81 | 12 | 0.728 | 2.96 |
| 2025-03-09 10:00 | SOL | SHORT | 1.02 | 1.67 | 0.62 | 0.05 | 25 | sl_hit | 19.56 | 12 | 0.685 | 2.03 |
| 2025-03-19 06:00 | SOL | SHORT | -1.21 | 0.23 | -5.30 | 1.21 | 5 | sl_hit | 13.61 | 12 | 0.526 | 1.35 |
| 2025-05-28 11:00 | ETH | LONG | 0.71 | 1.38 | 0.52 | 0.48 | 24 | stage1_timeout | 15.20 | 0 | 0.605 | 1.07 |
| 2025-07-22 02:00 | ETH | LONG | -0.41 | 0.00 | n/a | 0.74 | 4 | v54_structure_break | 13.55 | 6 | 0.494 | 1.09 |
| 2025-07-22 02:00 | XRP | LONG | -0.40 | 0.00 | n/a | 0.73 | 4 | v54_structure_break | 13.55 | 6 | 0.494 | 1.09 |
| 2025-07-22 10:00 | ETH | LONG | -0.21 | 0.31 | -0.68 | 0.32 | 24 | stage1_timeout | 12.73 | 12 | 0.550 | 1.15 |
| 2025-11-30 15:00 | DOGE | SHORT | 5.34 | 6.36 | 0.84 | 0.35 | 30 | sl_hit | 17.70 | 4 | 0.248 | 1.03 |
| 2025-12-28 16:00 | DOGE | SHORT | -1.03 | 0.60 | -1.70 | 1.03 | 9 | sl_hit | 9.32 | 6 | 0.673 | 0.69 |
| 2026-02-20 11:00 | ETH | SHORT | -0.61 | 0.18 | -3.35 | 0.61 | 24 | stage1_timeout | 13.46 | 0 | 0.567 | 1.45 |
| 2026-02-20 11:00 | BTC | SHORT | -0.48 | 0.32 | -1.50 | 0.56 | 24 | stage1_timeout | 13.46 | 0 | 0.567 | 1.45 |
| 2026-02-20 11:00 | BNB | SHORT | -1.21 | 0.34 | -3.59 | 1.21 | 6 | sl_hit | 13.46 | 0 | 0.567 | 1.45 |
| 2026-02-23 14:00 | XRP | SHORT | 0.87 | 1.04 | 0.84 | 0.00 | 24 | stage1_timeout | 19.27 | 84 | 1.190 | 1.46 |

Notes:

- `MAE R est.` is estimated from `abs(mae_pct) * entry_notional / initial_r`.
- BTC BBW/ATR features are read from the BTCUSDT 4H cache at `entry_regime_candle_time`.

## Capture Gap Check

Winning trades: 12.

| criterion | result |
|---|---:|
| Winning trades with `capture_ratio < 0.4` | 2 / 12 = 16.7% |
| All trades with `capture_ratio < 0.4` | 10 / 22 = 45.5% |
| R2 threshold for R3 GO | `> 30%` of winners |
| Verdict | FAIL |

The two low-capture winners are:

| entry_time | symbol | R | MaxR | capture | exit |
|---|---|---:|---:|---:|---|
| 2024-03-12 19:00 | ETH | 0.16 | 0.68 | 0.24 | stage1_timeout |
| 2025-03-07 14:00 | ETH | 0.63 | 1.86 | 0.34 | sl_hit |

This is not enough to claim V54 has a broad RANGING capture failure.

## Missed Setup Check

I mapped `signal_entries.csv` and `signal_rejects.csv` to BTC 4H regime using `btc_trend_log.csv` timestamps, then deduped by timestamp / symbol / side / signal type.

| audit bucket | count |
|---|---:|
| A-tier 2B signal entries mapped to RANGING | 24 |
| Completed RANGING trades among those entries | 22 |
| A-tier RANGING entries not completed | 2 |
| A-tier 2B post-filter rejects mapped to RANGING | 3 |
| Strict A-tier missed setup ceiling | 5 |
| R2 threshold for R3 GO | `>= 20` |
| Verdict | FAIL |

The 2 passed-entry rows without completed RANGING trades:

| timestamp | window | symbol | side | note |
|---|---|---|---|---|
| 2024-03-12 18:00 | TRENDING_UP | BNB | LONG | audited A-tier entry, no completed trade row |
| 2025-07-22 02:00 | MIXED | DOGE | LONG | audited A-tier entry, no completed trade row |

The 3 A-tier post-filter rejects:

| timestamp | window | symbol | side | reject_reason |
|---|---|---|---|---|
| 2025-02-10 15:00 | RANGING | ETH | SHORT | `btc_trend_ranging` |
| 2025-02-20 15:00 | RANGING | SOL | SHORT | `btc_trend_ranging` |
| 2025-08-29 10:00 | MIXED | SOL | LONG | `btc_trend_ranging` |

There were 176 deduped 2B rejects mapped to RANGING, but almost all were lower-tier or non-A setups: 66 `C` tier and 9 `B` tier `tier_filter` rejects dominate the post-filter set. That does not satisfy the A-tier missed-setup criterion.

## Risk Gap Check

| criterion | result |
|---|---:|
| Worst realized R | -1.21R |
| Max estimated single-trade adverse excursion | 1.21R |
| R2 threshold for R3 GO | `> 2R` |
| Verdict | FAIL |

The largest adverse cases were:

| entry_time | symbol | realized R | MAE R est. | exit |
|---|---|---:|---:|---|
| 2025-03-19 06:00 | SOL | -1.21 | 1.21 | sl_hit |
| 2026-02-20 11:00 | BNB | -1.21 | 1.21 | sl_hit |
| 2025-12-28 16:00 | DOGE | -1.03 | 1.03 | sl_hit |

No single-trade RANGING risk shape exceeded the 2R danger line.

## Read

V54-in-RANGING is not perfect, but this sample does not expose a large enough gap to justify a new RANGING strategy right now.

The most important clue is that the completed-trade baseline is already profitable while the missed-A-tier ceiling is small. If we write a new range strategy here, it must beat PF 2.82 later under the R3 gate, and this report does not show the thesis needed to make that worth the added router complexity.

## Decision

**Recommended Decision Log entry: `R3 = SKIP for now; keep V54 as RANGING fallback executor; proceed to R4 transition stress test after review.`**

This leaves the door open to revisit range strategy work if R4 or future forward data shows a cleaner gap.
