# Regime Distribution Baseline

- generated_at: `2026-04-22T05:50:10Z`
- data source: `Binance ccxt`
- timeframe: `1h`
- windows: `TRENDING_UP` (2023-10-01 -> 2024-03-31), `RANGING` (2024-12-31 -> 2025-03-31), `MIXED` (2025-02-01 -> 2025-08-31)

### BTC/USDT - TRENDING_UP

| metric | value |
| --- | --- |
| total_bars | 4369 |
| valid_bars | 4356 |
| adx < 20 | 1428 (32.78%) |
| 20 <= adx < 25 | 684 (15.70%) |
| 25 <= adx < 30 | 682 (15.66%) |
| adx >= 30 | 1562 (35.86%) |
| adx < 25 (RANGING band) | 2112 (48.48%) |
| adx >= 25 (TRENDING band) | 2244 (51.52%) |
| p25 / p50 / p75 / p90 | 17.5495 / 25.4697 / 34.8535 / 44.2114 |

### BTC/USDT - RANGING

| metric | value |
| --- | --- |
| total_bars | 2161 |
| valid_bars | 2148 |
| adx < 20 | 758 (35.29%) |
| 20 <= adx < 25 | 360 (16.76%) |
| 25 <= adx < 30 | 312 (14.53%) |
| adx >= 30 | 718 (33.43%) |
| adx < 25 (RANGING band) | 1118 (52.05%) |
| adx >= 25 (TRENDING band) | 1030 (47.95%) |
| p25 / p50 / p75 / p90 | 17.4319 / 24.4379 / 33.6932 / 44.9217 |

### BTC/USDT - MIXED

| metric | value |
| --- | --- |
| total_bars | 5065 |
| valid_bars | 5052 |
| adx < 20 | 1764 (34.92%) |
| 20 <= adx < 25 | 1003 (19.85%) |
| 25 <= adx < 30 | 785 (15.54%) |
| adx >= 30 | 1500 (29.69%) |
| adx < 25 (RANGING band) | 2767 (54.77%) |
| adx >= 25 (TRENDING band) | 2285 (45.23%) |
| p25 / p50 / p75 / p90 | 17.9832 / 23.6885 / 31.9649 / 42.1766 |

### ETH/USDT - TRENDING_UP

| metric | value |
| --- | --- |
| total_bars | 4369 |
| valid_bars | 4356 |
| adx < 20 | 1295 (29.73%) |
| 20 <= adx < 25 | 928 (21.30%) |
| 25 <= adx < 30 | 642 (14.74%) |
| adx >= 30 | 1491 (34.23%) |
| adx < 25 (RANGING band) | 2223 (51.03%) |
| adx >= 25 (TRENDING band) | 2133 (48.97%) |
| p25 / p50 / p75 / p90 | 18.9970 / 24.6646 / 34.1345 / 44.4395 |

### ETH/USDT - RANGING

| metric | value |
| --- | --- |
| total_bars | 2161 |
| valid_bars | 2148 |
| adx < 20 | 711 (33.10%) |
| 20 <= adx < 25 | 488 (22.72%) |
| 25 <= adx < 30 | 327 (15.22%) |
| adx >= 30 | 622 (28.96%) |
| adx < 25 (RANGING band) | 1199 (55.82%) |
| adx >= 25 (TRENDING band) | 949 (44.18%) |
| p25 / p50 / p75 / p90 | 18.3559 / 23.6108 / 31.8492 / 43.8730 |

### ETH/USDT - MIXED

| metric | value |
| --- | --- |
| total_bars | 5065 |
| valid_bars | 5052 |
| adx < 20 | 1600 (31.67%) |
| 20 <= adx < 25 | 1012 (20.03%) |
| 25 <= adx < 30 | 791 (15.66%) |
| adx >= 30 | 1649 (32.64%) |
| adx < 25 (RANGING band) | 2612 (51.70%) |
| adx >= 25 (TRENDING band) | 2440 (48.30%) |
| p25 / p50 / p75 / p90 | 18.7107 / 24.5569 / 33.4524 / 44.9953 |

## Combined Summary

| window | valid_bars | adx < 25 count | adx < 25 pct |
| --- | ---: | ---: | ---: |
| TRENDING_UP | 8712 | 4335 | 49.76% |
| RANGING | 4296 | 2317 | 53.93% |
| MIXED | 10104 | 5379 | 53.24% |

## Plain-Language Readout

BTC/USDT uses `adx < 25` on 1h for TRENDING_UP 48.48%, RANGING 52.05%, and MIXED 54.77% of valid bars.
ETH/USDT uses `adx < 25` on 1h for TRENDING_UP 51.03%, RANGING 55.82%, and MIXED 51.70% of valid bars.
