# bb_fade_squeeze_1h Gate Attribution

Date: 2026-04-25  
Status: `PHASE_5_CLOSEOUT_PARKED`

Closeout update (2026-05-05): this attribution closes Phase 5. The squeeze
definition is the bottleneck, but the lane is parked until a trigger review
proves a real Slot B ranging/frequency gap.

## Scope

- Candidate: `bb_fade_squeeze_1h`
- Windows: standard `DEFAULT_WINDOWS` from `extensions/Backtesting/plugin_candidate_review.py`
- Symbols: `BTC/USDT`, `ETH/USDT`
- Method: closed-bar shifted 1h cursor after the same 100-bar warmup used by candidate review.
- CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\bb_fade_squeeze_1h\gate_attribution.csv`

## Single Gate Pass Rates

| window | valid bars | RSI < 30 | close <= BB lower | BBW pctrank < 20 | 4h ADX < 20 | all gates | post-cooldown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| TRENDING_UP | 8500 | 231 (2.72%) | 414 (4.87%) | 2187 (25.73%) | 2156 (25.36%) | 1 (0.01%) | 1 |
| RANGING | 4084 | 287 (7.03%) | 301 (7.37%) | 902 (22.09%) | 1640 (40.16%) | 0 (0.00%) | 0 |
| MIXED | 9892 | 407 (4.11%) | 529 (5.35%) | 2316 (23.41%) | 3332 (33.68%) | 0 (0.00%) | 0 |
| TOTAL | 22476 | 925 (4.12%) | 1244 (5.53%) | 5405 (24.05%) | 7128 (31.71%) | 1 (0.00%) | 1 |

## Cumulative Survival

| window | valid bars | after RSI | + lower touch | + BBW squeeze | + 4h ADX |
| --- | ---: | ---: | ---: | ---: | ---: |
| TRENDING_UP | 8500 | 231 (2.72%) | 133 (1.56%) | 1 (0.01%) | 1 (0.01%) |
| RANGING | 4084 | 287 (7.03%) | 127 (3.11%) | 0 (0.00%) | 0 (0.00%) |
| MIXED | 9892 | 407 (4.11%) | 180 (1.82%) | 1 (0.01%) | 0 (0.00%) |
| TOTAL | 22476 | 925 (4.12%) | 440 (1.96%) | 2 (0.01%) | 1 (0.00%) |

## Near Misses

A near miss fails exactly one of the four gates while passing the other three.

| window | fail only RSI | fail only lower touch | fail only BBW squeeze | fail only 4h ADX |
| --- | ---: | ---: | ---: | ---: |
| TRENDING_UP | 17 | 0 | 38 | 0 |
| RANGING | 28 | 0 | 31 | 0 |
| MIXED | 43 | 0 | 37 | 1 |
| TOTAL | 88 | 0 | 106 | 1 |

## First Failing Gate

First-fail attribution uses entry order: RSI -> lower-band touch -> BBW squeeze -> 4h ADX.

| window | first fail RSI | first fail lower touch | first fail BBW squeeze | first fail 4h ADX | pass all |
| --- | ---: | ---: | ---: | ---: | ---: |
| TRENDING_UP | 8269 | 98 | 132 | 0 | 1 |
| RANGING | 3797 | 160 | 127 | 0 | 0 |
| MIXED | 9485 | 227 | 179 | 1 | 0 |
| TOTAL | 21551 | 485 | 438 | 1 | 1 |

## Read

- Total valid evaluated bars: `22476`.
- Fully qualified all-gate bars: `1`.
- Post-cooldown candidate signals: `1`.
- The main conditional bottleneck is `BBW pctrank < 20`: `RSI + lower touch`
  leaves `440` bars, but adding the BBW squeeze gate collapses that to `2`.
- The 4h ADX gate is not the first thing to loosen: it blocks only `1` of the
  `2` bars that survive RSI, lower touch, and BBW squeeze.
- Lower-band touch is not the final bottleneck once the other three gates pass:
  there are `0` near misses where only lower touch fails.
- If this lane gets a rescue pass, attribution points to the squeeze definition
  first, not to the HTF ADX regime guard.
- This is diagnostic evidence only; it does not modify runtime defaults or promote the candidate.
