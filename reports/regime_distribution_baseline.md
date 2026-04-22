# Regime Distribution Baseline

- generated_at: `2026-04-22T02:02:25Z`
- data source: `Binance ccxt`
- timeframe: `15m`
- windows: `TRENDING_UP` (2023-10-01 -> 2024-03-31), `RANGING` (2024-12-31 -> 2025-03-31), `MIXED` (2025-02-01 -> 2025-08-31)

### BTC/USDT - TRENDING_UP

| metric | value |
| --- | --- |
| total_bars | 17473 |
| valid_bars | 17460 |
| adx < 20 | 6400 (36.66%) |
| 20 <= adx < 25 | 3401 (19.48%) |
| 25 <= adx < 30 | 2376 (13.61%) |
| adx >= 30 | 5283 (30.26%) |
| adx < 25 (RANGING band) | 9801 (56.13%) |
| adx >= 25 (TRENDING band) | 7659 (43.87%) |
| p25 / p50 / p75 / p90 | 17.4697 / 23.3596 / 32.2828 / 43.5707 |

### BTC/USDT - RANGING

| metric | value |
| --- | --- |
| total_bars | 8641 |
| valid_bars | 8628 |
| adx < 20 | 2875 (33.32%) |
| 20 <= adx < 25 | 1675 (19.41%) |
| 25 <= adx < 30 | 1419 (16.45%) |
| adx >= 30 | 2659 (30.82%) |
| adx < 25 (RANGING band) | 4550 (52.74%) |
| adx >= 25 (TRENDING band) | 4078 (47.26%) |
| p25 / p50 / p75 / p90 | 18.1398 / 24.2896 / 32.2084 / 41.6432 |

### BTC/USDT - MIXED

| metric | value |
| --- | --- |
| total_bars | 20257 |
| valid_bars | 20244 |
| adx < 20 | 7699 (38.03%) |
| 20 <= adx < 25 | 4050 (20.01%) |
| 25 <= adx < 30 | 3015 (14.89%) |
| adx >= 30 | 5480 (27.07%) |
| adx < 25 (RANGING band) | 11749 (58.04%) |
| adx >= 25 (TRENDING band) | 8495 (41.96%) |
| p25 / p50 / p75 / p90 | 17.1301 / 22.8850 / 30.7817 / 39.9688 |

### ETH/USDT - TRENDING_UP

| metric | value |
| --- | --- |
| total_bars | 17473 |
| valid_bars | 17460 |
| adx < 20 | 5261 (30.13%) |
| 20 <= adx < 25 | 3545 (20.30%) |
| 25 <= adx < 30 | 2742 (15.70%) |
| adx >= 30 | 5912 (33.86%) |
| adx < 25 (RANGING band) | 8806 (50.44%) |
| adx >= 25 (TRENDING band) | 8654 (49.56%) |
| p25 / p50 / p75 / p90 | 18.7796 / 24.8740 / 33.3969 / 42.7887 |

### ETH/USDT - RANGING

| metric | value |
| --- | --- |
| total_bars | 8641 |
| valid_bars | 8628 |
| adx < 20 | 2531 (29.33%) |
| 20 <= adx < 25 | 1801 (20.87%) |
| 25 <= adx < 30 | 1346 (15.60%) |
| adx >= 30 | 2950 (34.19%) |
| adx < 25 (RANGING band) | 4332 (50.21%) |
| adx >= 25 (TRENDING band) | 4296 (49.79%) |
| p25 / p50 / p75 / p90 | 18.9921 / 24.9734 / 33.8600 / 45.2515 |

### ETH/USDT - MIXED

| metric | value |
| --- | --- |
| total_bars | 20257 |
| valid_bars | 20244 |
| adx < 20 | 6003 (29.65%) |
| 20 <= adx < 25 | 4355 (21.51%) |
| 25 <= adx < 30 | 3279 (16.20%) |
| adx >= 30 | 6607 (32.64%) |
| adx < 25 (RANGING band) | 10358 (51.17%) |
| adx >= 25 (TRENDING band) | 9886 (48.83%) |
| p25 / p50 / p75 / p90 | 18.8283 / 24.7312 / 33.0569 / 42.8339 |

## Combined Summary

| window | valid_bars | adx < 25 count | adx < 25 pct |
| --- | ---: | ---: | ---: |
| TRENDING_UP | 34920 | 18607 | 53.28% |
| RANGING | 17256 | 8882 | 51.47% |
| MIXED | 40488 | 22107 | 54.60% |

## Plain-Language Readout

BTC/USDT uses `adx < 25` on 15m for TRENDING_UP 56.13%, RANGING 52.74%, and MIXED 58.04% of valid bars.
ETH/USDT uses `adx < 25` on 15m for TRENDING_UP 50.44%, RANGING 50.21%, and MIXED 51.17% of valid bars.
