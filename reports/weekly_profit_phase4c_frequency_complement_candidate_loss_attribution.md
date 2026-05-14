# Weekly Profit Phase 4C Frequency Complement Candidate Loss Attribution

Date: 2026-05-14
Branch: `codex/post-promotion-control-20260430`
Verdict: `LOSS_ATTRIBUTION_FAIL_CONFIRMED_CANDIDATE_EDGE`

## Executive Read

`btc_recovery_band_trend_breadth_4h` closed 8 trades with net PnL `-681.6736` USDT. The lane still fails the weekly-profit objective unless this loss source is repaired.

Precision match count is `8` matched and `0` unmatched. Phase 4C parity drift is removed; the remaining loss is confirmed candidate-edge evidence.

## Loss Summary

| metric | value |
| --- | ---: |
| trades | 8 |
| wins | 1 |
| losses | 7 |
| net pnl | -681.6736 |
| matched precision trades | 8 |
| unmatched precision trades | 0 |

## Buckets

| bucket | counts | pnl |
| --- | --- | --- |
| exit reason | `{"sl_hit": 7, "unknown": 1}` | `{"sl_hit": -645.7574, "unknown": -35.9162}` |
| entry regime | `{"RANGING": 1, "TRENDING": 7}` | `{"RANGING": -85.2243, "TRENDING": -596.4493}` |
| entry regime direction | `{"LONG": 7, "SHORT": 1}` | `{"LONG": -520.6868, "SHORT": -160.9868}` |

## Candidate Trades

| key | entry | exit | pnl | realized_r | exit_reason | regime | direction | precision_match |
| --- | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| `2026-01-05T00:00:00Z` | `2026-01-05T04:00:00+00:00` | `2026-01-06T18:00:00+00:00` | -61.8710 | -1.1400 | `sl_hit` | `TRENDING` | `LONG` | `True` |
| `2026-01-28T08:00:00Z` | `2026-01-28T09:00:00+00:00` | `2026-01-29T02:00:00+00:00` | -72.3456 | -1.0300 | `sl_hit` | `TRENDING` | `LONG` | `True` |
| `2026-02-08T12:00:00Z` | `2026-02-08T13:00:00+00:00` | `2026-02-10T15:00:00+00:00` | -160.9868 | -0.9300 | `sl_hit` | `TRENDING` | `SHORT` | `True` |
| `2026-03-10T12:00:00Z` | `2026-03-10T13:00:00+00:00` | `2026-03-10T15:00:00+00:00` | 7.5423 | 0.0600 | `sl_hit` | `TRENDING` | `LONG` | `True` |
| `2026-03-13T08:00:00Z` | `2026-03-13T09:00:00+00:00` | `2026-03-14T02:00:00+00:00` | -85.2243 | -0.8300 | `sl_hit` | `RANGING` | `LONG` | `True` |
| `2026-03-16T20:00:00Z` | `2026-03-16T21:00:00+00:00` | `2026-03-18T12:00:00+00:00` | -113.9774 | -1.2300 | `sl_hit` | `TRENDING` | `LONG` | `True` |
| `2026-04-07T20:00:00Z` | `2026-04-07T21:00:00+00:00` | `2026-04-07T21:00:00+00:00` | -158.8946 | -1.6300 | `sl_hit` | `TRENDING` | `LONG` | `True` |
| `2026-04-07T20:00:00Z` | `2026-04-07T23:00:00+00:00` | `2026-04-12T21:00:00+00:00` | -35.9162 | -0.3700 | `unknown` | `TRENDING` | `LONG` | `True` |

## Next Action

- Do not promote this candidate.
- Freeze this BTC recovery-band lane unless a new candle-feature-only loss filter can be proven on matched trades without destroying cadence.
- Move the next frequency-complement research pass to a different family if no such filter is available.
