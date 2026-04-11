# Config Parity Report

- Generated: 2026-04-11T17:06:33+08:00
- JSON: `C:\Users\user\Documents\Claude.ai\projects\trading_bot\.worktrees\feat-grid\bot_config.json`
- Config: `C:\Users\user\Documents\Claude.ai\projects\trading_bot\.worktrees\feat-grid\trader\config.py`
- Mode: `full`

## Summary

| category | count | critical |
|---|---:|---:|
| `MISSING_IN_JSON` | 69 | 0 |
| `MISSING_IN_CONFIG` | 0 | 0 |
| `VALUE_MISMATCH` | 8 | 0 |
| `TYPE_MISMATCH` | 0 | 0 |
| `TOTAL` | 77 | 0 |

## Critical Keys

`ENABLE_EMA_PULLBACK`, `ENABLE_GRID_TRADING`, `ENABLE_VOLUME_BREAKOUT`, `SIGNAL_STRATEGY_MAP`, `V7_MIN_SIGNAL_TIER`

## Critical Findings

None.

## MISSING_IN_JSON

| key | critical | json | config | json_type | config_type |
|---|---:|---|---|---|---|
| `ADX_BASE_THRESHOLD` | no | null | 15 |  | `int` |
| `ADX_MAX_2B` | no | null | 50 |  | `int` |
| `ADX_STRONG_THRESHOLD` | no | null | 25 |  | `int` |
| `API_KEY` | no | null | "your_api_key_here" |  | `str` |
| `API_SECRET` | no | null | "your_api_secret_here" |  | `str` |
| `ATR_NORMAL_MULTIPLIER` | no | null | 1.5 |  | `float` |
| `ATR_QUIET_MULTIPLIER` | no | null | 1.2 |  | `float` |
| `ATR_QUIET_RATIO` | no | null | 0.8 |  | `float` |
| `ATR_VOLATILE_MULTIPLIER` | no | null | 2.0 |  | `float` |
| `ATR_VOLATILE_RATIO` | no | null | 1.5 |  | `float` |
| `BTC_EMA_RANGING_THRESHOLD` | no | null | 0.005 |  | `float` |
| `EMA_PULLBACK_FAST` | no | null | 10 |  | `int` |
| `EMA_PULLBACK_LOOKBACK_BARS` | no | null | 3 |  | `int` |
| `EMA_PULLBACK_MIN_BODY_RATIO` | no | null | 0.12 |  | `float` |
| `EMA_PULLBACK_MIN_TREND_SIDE_BARS` | no | null | 2 |  | `int` |
| `EMA_PULLBACK_REQUIRE_PREV_COUNTER_BAR` | no | null | true |  | `bool` |
| `EMA_PULLBACK_SLOW` | no | null | 20 |  | `int` |
| `EMA_PULLBACK_SOFT_MTF_ENABLED` | no | null | true |  | `bool` |
| `EMA_PULLBACK_THRESHOLD` | no | null | 0.02 |  | `float` |
| `EMA_TREND` | no | null | 200 |  | `int` |
| `GRID_ATR_MULTIPLIER` | no | null | 2.5 |  | `float` |
| `GRID_ATR_PERIOD` | no | null | 14 |  | `int` |
| `GRID_CAPITAL_RATIO` | no | null | 0.3 |  | `float` |
| `GRID_CONVERGE_TIMEOUT_HOURS` | no | null | 72 |  | `int` |
| `GRID_COOLDOWN_HOURS` | no | null | 6 |  | `int` |
| `GRID_LEVELS` | no | null | 5 |  | `int` |
| `GRID_MAX_DRAWDOWN` | no | null | 0.05 |  | `float` |
| `GRID_MAX_NOTIONAL` | no | null | 0.0 |  | `float` |
| `GRID_MAX_TOTAL_RISK` | no | null | 0.075 |  | `float` |
| `GRID_RESET_DRIFT_RATIO` | no | null | 0.5 |  | `float` |
| `GRID_RISK_PER_TRADE` | no | null | 0.025 |  | `float` |
| `GRID_SMA_PERIOD` | no | null | 20 |  | `int` |
| `GRID_WEIGHT_CENTER` | no | null | 0.5 |  | `float` |
| `GRID_WEIGHT_EDGE` | no | null | 1.5 |  | `float` |
| `LOG_FILE_PATH` | no | null | "C:\\Users\\user\\Documents\\Claude.ai\\projects\\trading_bot\\.worktrees\\feat-grid\\.log\\bot.log" |  | `str` |
| `MAX_FAKEOUT_ATR` | no | null | 1.5 |  | `float` |
| `MAX_RETRY` | no | null | 3 |  | `int` |
| `MTF_EMA_FAST` | no | null | 20 |  | `int` |
| `MTF_EMA_SLOW` | no | null | 50 |  | `int` |
| `REGIME_ADX_RANGING` | no | null | 20 |  | `int` |
| `REGIME_ADX_TRENDING` | no | null | 25 |  | `int` |
| `REGIME_ATR_SQUEEZE_MULT` | no | null | 1.1 |  | `float` |
| `REGIME_ATR_TRENDING_MULT` | no | null | 1.3 |  | `float` |
| `REGIME_BBW_HISTORY` | no | null | 50 |  | `int` |
| `REGIME_BBW_RANGING_PCT` | no | null | 25 |  | `int` |
| `REGIME_BBW_SQUEEZE_PCT` | no | null | 10 |  | `int` |
| `REGIME_CONFIRM_CANDLES` | no | null | 3 |  | `int` |
| `REGIME_TIMEFRAME` | no | null | "4h" |  | `str` |
| `RETRY_DELAY` | no | null | 5 |  | `int` |
| `SL_ATR_BUFFER_SIGNAL` | no | null | 0.5 |  | `float` |
| `STAGE1_MAX_HOURS` | no | null | 24 |  | `int` |
| `STAGE3_EMA_TOUCH_TOLERANCE` | no | null | 0.02 |  | `float` |
| `STRATEGY` | no | null | "v6_pyramid" |  | `str` |
| `STRUCTURE_BREAK_LOOKBACK` | no | null | 10 |  | `int` |
| `STRUCTURE_BREAK_TOLERANCE` | no | null | 0.005 |  | `float` |
| `TELEGRAM_BOT_TOKEN` | no | null | "" |  | `str` |
| `TELEGRAM_CHAT_ID` | no | null | "" |  | `str` |
| `TIMEFRAME_MTF` | no | null | "4h" |  | `str` |
| `TIMEFRAME_SIGNAL` | no | null | "1h" |  | `str` |
| `TIMEFRAME_TREND` | no | null | "1d" |  | `str` |
| `TREND_CACHE_HOURS` | no | null | 4 |  | `int` |
| `TREND_CAPITAL_RATIO` | no | null | 0.7 |  | `float` |
| `V6_BREAKEVEN_BUFFER_R` | no | null | 0.1 |  | `float` |
| `V6_BREAKEVEN_ENABLED` | no | null | true |  | `bool` |
| `V6_BREAKEVEN_MFE_R` | no | null | 1.5 |  | `float` |
| `V6_FAST_TRAIL_REQUIRE_BOS` | no | null | false |  | `bool` |
| `V6_FAST_TRAIL_RIGHT_BARS` | no | null | 2 |  | `int` |
| `VOLUME_BREAKOUT_MULT` | no | null | 2.0 |  | `float` |
| `VOLUME_PULLBACK_MIN_RATIO` | no | null | 0.6 |  | `float` |

## MISSING_IN_CONFIG

None.

## VALUE_MISMATCH

| key | critical | json | config | json_type | config_type |
|---|---:|---|---|---|---|
| `EMA_ENTANGLEMENT_THRESHOLD` | no | 0.03 | 0.02 | `float` | `float` |
| `MAX_POSITION_PERCENT` | no | 0.14592592592592593 | 0.146 | `float` | `float` |
| `MAX_TOTAL_RISK` | no | 0.06418518518518519 | 0.05 | `float` | `float` |
| `MIN_FAKEOUT_ATR` | no | 0.3 | 0.6 | `float` | `float` |
| `POSITIONS_JSON_PATH` | no | "positions.json" | "C:\\Users\\user\\Documents\\Claude.ai\\projects\\trading_bot\\.worktrees\\feat-grid\\.log\\positions.json" | `str` | `str` |
| `SCANNER_MAX_AGE_MINUTES` | no | 30 | 60 | `int` | `int` |
| `SYMBOLS` | no | ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT"] | ["BTC/USDT", "ETH/USDT", "SOL/USDT"] | `list` | `list` |
| `TIER_A_POSITION_MULT` | no | 0.7 | 1.0 | `float` | `float` |

## TYPE_MISMATCH

None.
