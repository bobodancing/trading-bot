# Cartridge Spec: BTC Recovery-Band Trend Breadth 4h

Date: 2026-05-13
Status: `RESEARCH_PLUGIN_CANDIDATE`

## Intent

Build one research-only frequency-complement cartridge for the weekly-profit lane:

- fill promoted A+B silent-or-zero weeks when evidence supports it
- stay BTC-only
- keep current runtime defaults untouched
- enter only inside the Phase 4A recovery-band precision filter that passed attribution review

## Plugin Contract

| field | value |
| --- | --- |
| plugin id | `btc_recovery_band_trend_breadth_4h` |
| catalog classification | `active_research` |
| runtime default activation | `false` |
| symbol scope | `BTC/USDT` only |
| side | `LONG` |
| entry timeframe | `4h` |
| trend timeframe | completed `1d` candle only |
| central sizing | `StrategyRuntime` / `RiskPlan` only |

## Entry

The plugin emits one `LONG` intent when all conditions hold:

1. Completed 1d EMA spread is inside the recovery band:
   `-0.08 <= (ema_20 - ema_50) / ema_50 <= -0.01`
2. At least one 4h breadth trigger fires:
   `supertrend_flip`
   or
   `aroon_break_hh`
3. The chosen trigger anchor is not stretched:
   `distance_atr <= 3.0`
4. Same-candle duplicate emits are suppressed.

### Trigger Definitions

| trigger | condition | anchor |
| --- | --- | --- |
| `supertrend_flip` | previous `supertrend_direction <= -1`, current `>= 1` | current `supertrend` |
| `aroon_break_hh` | `aroon_up > 70`, `aroon_down < 30`, close above prior 20-bar swing high | prior swing high |

When both triggers fire on the same candle, the plugin emits one intent and
selects the lower `distance_atr` trigger as the primary mechanism while
retaining both trigger payloads in metadata.

## Exit

The candidate is closed by plugin logic when either condition holds:

- completed 1d EMA spread leaves the recovery band
- 4h SuperTrend flips from bullish to bearish

Hard stop remains central:

- `stop_price = entry_price - 1.5 * ATR(4h)`

## Evidence Link

This cartridge implements the Phase 4A recommended precision filter:

- 11 selected diagnostic candidates
- 9 / 11 on silent-or-zero baseline weeks
- 5 silent zero-entry weeks hit
- 0 same-symbol same-candle promoted overlaps

See:

- `reports/weekly_profit_phase4a_trend_companion_precision_attribution.md`

## Out Of Scope

- no runtime promotion
- no `Config.ENABLED_STRATEGIES` changes
- no scanner-universe activation
- no threshold loosening to manufacture volume
- no capital claim before combined A+B+candidate packet evaluation
