# Weekly Profit Phase 5 Candidate Scoreboard / Closeout

Date: 2026-05-17
Branch: `codex/post-promotion-control-20260430`
Status: `PHASE_5_CANDIDATE_BATCH_CLOSED_NO_PROMOTION`

## Executive Read

The current weekly-profit candidate batch is closed with **no promotion**.

The promoted runtime baseline remains the only approved runtime portfolio:

- Slot A LONG: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- Slot B LONG: `donchian_range_fade_4h_range_width_cv_013`
- Slot B SHORT: `donchian_range_fade_4h_range_width_cv_013_short`

The research batch proved the original diagnosis was correct: weekly participation is the dominant gap. It also proved the harder point: adding trades is easy, preserving after-fee weekly quality and drawdown stability is not.

No runtime defaults, scanner runtime universe settings, promoted strategy list, risk defaults, or thresholds should be changed from this batch.

## Baseline Reference

Primary control packet latest contract-grade baseline:

| metric | value |
| --- | ---: |
| active-entry week ratio 8w | 0.6250 |
| rolling 8w entry trades | 9 |
| positive all-week ratio 8w, after fee | 0.3750 |
| positive exit-active ratio 8w, after fee | 0.6000 |
| rolling 8w net after-fee PnL | 106.4680 |
| portfolio max DD review window | 2.1778 |
| state | `investigate` |

The baseline is net-positive but not yet a credible weekly machine because all-week positive density remains weak.

## Candidate Scoreboard

| lane | target gap | primary result | hard failure | decision |
| --- | --- | --- | --- | --- |
| `btc_recovery_band_trend_breadth_4h` | frequency complement / silent weeks | active-entry improved by 0.2500, but combined state became `reopen_research` | candidate edge confirmed: 8 trades, 1 win, net PnL `-681.6736`, 7 `sl_hit` losses | `PARK_EDGE_FAIL` |
| `range_break_retest_4h_conservative_30` | range-break participation complement | active-entry improved by 0.3750 | rolling 8w after-fee PnL delta `-180.1378`; exit-active quality and losing-week streak failed | `PARK_ECONOMICS_FAIL` |
| `range_break_retest_quality_repair` | repair 4D loss quality | active-entry improved by 0.1250 | still reduced rolling 8w after-fee PnL by `-76.8629`; state remained `investigate` | `PARK_REPAIR_INSUFFICIENT` |
| Slot B full symbol expansion | expand Donchian LONG/SHORT to SOL/BNB/XRP/ADA/LINK | active-entry improved by 0.2500 and rolling 8w after-fee PnL improved by `+261.5372` | positive exit-active ratio declined by `-0.0286` | `REPAIR_REQUIRED` |
| Slot B symbol expansion repair | drop `ADA LONG` + `LINK SHORT` | primary window passed all hard gates; candidate after-fee `+1476.3888` | holdout robustness failed: `0 / 4` windows pass | `NO_PROMOTION_HOLDOUT_FAIL` |

## Slot B Expansion Detail

The best primary-window result came from side-specific Slot B symbol admission:

- LONG admits `SOL/USDT`, `BNB/USDT`, `XRP/USDT`, `LINK/USDT`
- SHORT admits `SOL/USDT`, `BNB/USDT`, `XRP/USDT`, `ADA/USDT`
- dropped `ADA LONG`
- dropped `LINK SHORT`

Primary-window repair read:

| metric | delta vs baseline |
| --- | ---: |
| active-entry week ratio 8w | +0.1250 |
| rolling 8w entry trades | +10 |
| positive all-week ratio 8w, after fee | +0.1250 |
| positive exit-active ratio 8w, after fee | +0.0667 |
| rolling 8w net after-fee PnL | +382.8464 |
| portfolio max DD review window | +0.3784 |

This was the only candidate packet that looked promotion-shaped in the primary window.

Holdout killed the promotion read:

| window | pass | candidate after-fee | failed gates |
| --- | --- | ---: | --- |
| `default/TRENDING_UP` | `False` | 776.3668 | `positive_exit_active_8w_ratio_not_down` |
| `default/RANGING` | `False` | 740.3545 | `max_dd_not_materially_larger` |
| `default/MIXED` | `False` | 565.4079 | `positive_exit_active_8w_ratio_not_down`, `max_dd_not_materially_larger` |
| `supplemental/range_low_vol` | `False` | -365.8698 | rolling PnL, candidate after-fee, exit-active quality, DD, losing-symbol volume |

Closeout judgment: this lane has useful signal, but it is not robust enough to alter runtime defaults.

## Lessons

1. Participation repair is real but fragile.
   Every serious candidate increased active-entry participation somewhere.

2. The weekly-profit bottleneck has shifted from "can we find trades?" to "can added trades preserve weekly quality?"

3. Primary-window success is not enough.
   Slot B repair passed the primary packet cleanly, then failed all four holdout windows.

4. Broad symbol expansion is too blunt.
   Symbol/side admission helps, but the failure is regime/window-sensitive, not only a single bad symbol.

5. BTC recovery-band and range-break families should not be revived without a new pre-registered loss mechanism.
   Their current evidence is not a tuning problem; it is candidate-edge damage.

## Closeout Decisions

| item | decision |
| --- | --- |
| promote any Phase 5 candidate | `NO` |
| change `trader/config.py` defaults | `NO` |
| add new symbols to runtime `SYMBOLS` | `NO` |
| enable scanner runtime universe | `NO` |
| loosen thresholds for participation | `NO` |
| keep Slot B symbol repair as research evidence | `YES` |
| keep BTC recovery-band lane active | `NO` |
| keep range-break retest lane active | `NO` |

## Recommended Next Work

1. Commit this closeout memo.
2. Run targeted 4E holdout failure attribution:
   - per window
   - per symbol/side
   - per week
   - DD contribution
   - exit-active quality damage
3. If attribution finds a stable, pre-registerable filter, run one bounded repair pass.
4. If attribution does not find a clean filter, park symbol expansion and move back to the operational evidence loop.

The next research action should be attribution, not another candidate family.
