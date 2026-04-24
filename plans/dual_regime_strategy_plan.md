# Dual-Regime Strategy Plugin Plan

> **Status: SUPERSEDED (2026-04-24).** Archived for context only. Do not
> drive new candidate research from this document.
>
> **Why superseded:**
> - Plugin B (`rsi_mean_reversion_15m`) has been attempted and failed twice:
>   γ parked on checklist §5 infra gate (engine lacks 15m support);
>   δ (`rsi_mean_reversion_1h`, 1h retry) failed checklist §3.2 RANGING
>   `net_pnl > 0` gate. See `reports/rsi_mean_reversion_research_note.md`.
> - Plugin A (`keltner_breakout_1h`) intentionally abandoned: edge-source
>   overlap with the existing `macd_signal_btc_4h_trending_up_*` family
>   (10+ variants in `trader/strategies/plugins/`) gives low marginal
>   decorrelation value; the actual gap in the portfolio is RANGING, not
>   another TRENDING_UP continuation cartridge.
> - The plan's governing architecture — ADX-based regime complement
>   ("A runs when ADX>25, B runs when ADX<25") — is refuted by δ's
>   learning 3(a): 65.6% of a nominally-RANGING window was classified as
>   TRENDING by the arbiter. Local ADX is not a reliable regime
>   switcher. Future research follows per-cartridge regime declaration
>   per checklist §2.5, not a portfolio-level ADX partition.
> - Plan predates checklist §2.5 (Regime Declaration) and §5 (timeframe
>   support gate); sections below do not satisfy current process.
>
> **Superseded by:** `plans/ranging_strategy_brainstorm_design.md`
> (three decorrelated RANGING cartridges: `bb_fade_squeeze_1h` directly
> replaces Plugin B; `donchian_range_fade_4h` and `rsi2_pullback_1h`
> cover the remaining portfolio slots without re-using the refuted ADX
> complement framing).
>
> Original metadata below retained as historical context.
>
> Status (original): DRAFT — 等待 Ruei review 後交付 Claude Code 實作
> Date (original): 2026-04-21
> Branch: `codex/strategy-runtime-reset`
> Context: Minara 236 TradingView backtest study + codebase capability audit

---

## 1. Background & Motivation

### 1.1 Minara Study Key Findings

Minara 用 HyperLiquid 真實費率回測了 236 個公開 TradingView 策略，核心結論：

- 236 → 63 通過 trade-by-trade replication → 36 盈利 → **21 個年化 > 10%**
- **Trade frequency 是費用殺手**：所有從盈轉虧的策略年交易 200+ 次
- **沒有單一策略類型主宰** — SuperTrend、BB、Keltner、EMA、MACD、RSI 都有 Tier 1 成員
- **低 win rate + 高 profit factor** 是贏家 profile（win rate 35-50%，靠大贏小輸）
- 策略存活的 predictor 是 **per-trade edge vs fee cost**，不是指標類型

### 1.2 Codebase Current State

已有 plugin：
- `macd_zero_line_btc_1d` — MACD 零軸交叉，BTC 1d，long-only（對應 Minara #7，+34.5% APR）
- `ema_cross_7_19_long_only` — EMA 7/19 交叉，BTC/ETH 4h，long-only（對應 Minara #11，+28.4% APR）

Indicator registry 已支援：`ema`, `sma`, `atr`, `adx`, `bbw`, `rsi`, `macd`, `bollinger`, `supertrend`

### 1.3 Design Goal

Ruei 的需求：
- **頻率**：一週至少 5 筆交易
- **報酬**：年化 30%+ 目標
- **市場覆蓋**：能應付 trending 和 ranging 兩種 regime
- 可以是兩個獨立策略分別處理

---

## 2. Strategy Design

### 2.1 Architecture: ADX Regime Complement

兩個 plugin 靠 ADX 天然分工：

| | Plugin A: Keltner Breakout | Plugin B: RSI Mean Reversion |
|---|---|---|
| Regime | Trending (ADX > 25) | Ranging (ADX < 25) |
| Style | Breakout / Momentum continuation | Mean reversion / Fade extremes |
| Timeframe | 1h | 15m |
| Symbols | BTC/USDT, ETH/USDT | BTC/USDT, ETH/USDT |
| Side | LONG only | LONG only |
| Inspiration | Minara #2 Volatility Breakout (+124.6% APR), #15 Keltner Breakout (+21% APR) | Minara #1 RSI Mean Reversion (+204.6% APR) |
| Expected freq | 2-4/week during trends | 3-5/week during ranges |

市場在 trending/ranging 之間輪替，合計頻率比單策略穩定。

---

## 3. Plugin A: `keltner_breakout_1h`

### 3.1 Identity

```python
id = "keltner_breakout_1h"
version = "0.1.0"
tags = {"external_candidate", "keltner", "atr", "1h", "long_only", "trend", "breakout"}
required_timeframes = {"1h": 200}
required_indicators = {"ema", "atr", "adx", "supertrend"}
allowed_symbols = {"BTC/USDT", "ETH/USDT"}
max_concurrent_positions = None  # kernel per-symbol limit applies
risk_profile = StrategyRiskProfile.fixed_risk_pct()
```

### 3.2 Params Schema

```python
params_schema = {
    "symbol": "str",           # optional: lock to single symbol
    "timeframe": "str",        # default "1h"
    "keltner_ema_len": "int",  # default 20 (Keltner center line EMA length)
    "keltner_atr_mult": "float",  # default 1.5 (Keltner channel width)
    "adx_threshold": "float",  # default 25.0 (minimum ADX for trend confirmation)
    "stop_atr_mult": "float",  # default 2.0 (stop-loss = entry - mult * ATR)
    "cooldown_bars": "int",    # default 3 (min bars between signals on same symbol)
    "emit_once": "bool",       # default True
    "risk_pct": "float",       # optional override per-plugin risk
}
```

### 3.3 Entry Logic: `generate_candidates()`

```
KELTNER_UPPER = EMA(close, keltner_ema_len) + keltner_atr_mult * ATR(14)

Entry conditions (ALL must be true):
  1. close > KELTNER_UPPER                    — price broke above channel
  2. previous close <= previous KELTNER_UPPER — confirmed cross (not already above)
  3. ADX(14) > adx_threshold                  — trend is established
  4. cooldown check passed                    — no signal in last N bars for this symbol
```

**Why this works:** Keltner channel = EMA + ATR×mult。ATR 讓 channel 自動適應 volatility — 高波動時 channel 寬，需要更大的 move 才觸發，天然過濾假突破。ADX gate 確保只在有方向性的市場出手。

**Implementation notes:**
- `KELTNER_UPPER` 不是 registry 內建欄位，需要在 plugin 內從 `ema_20` 和 `atr` 計算。
  - `ema_20` 來自 registry（`IndicatorRegistry` apply 時 `ema` group 會產生 `ema_20`）
  - `atr` 來自 registry
  - Plugin 內算 `keltner_upper = ema_20 + keltner_atr_mult * atr`
- 如果 `keltner_ema_len` 不是 20，需要用 `_ema(close, length=keltner_ema_len)` 自行計算（參考 `ema_cross_7_19.py` 的 `_with_emas` pattern）
- `adx` 來自 registry（`IndicatorRegistry` apply 時 `adx` group 會產生 `adx` column）

### 3.4 Stop Hint

```python
stop_price = entry_price - stop_atr_mult * atr
StopHint(
    price=stop_price,
    reason="keltner_breakout_atr_stop",
    metadata={"atr": atr, "atr_mult": stop_atr_mult, "keltner_upper": keltner_upper},
)
```

### 3.5 Exit Logic: `update_position()`

```
Exit conditions (ANY triggers CLOSE):
  1. close < EMA(close, keltner_ema_len)  — price fell back below center line
  2. ADX(14) < 20                         — trend exhaustion

Optional trailing stop (stretch goal, use UPDATE_SL action):
  - If supertrend_direction == 1: new_sl = max(current_sl, supertrend_line)
  - SuperTrend 作為動態 trailing stop，在趨勢持續時逐步上移
```

### 3.6 Cooldown Mechanism

用 `_emitted_keys: set[str]` 追蹤最近 N bars 的已發訊號（同 `macd_zero_line.py` pattern），或用 `_last_signal_ts: dict[str, datetime]` 記錄每個 symbol 最後發訊號的 candle timestamp，比較 bar 距離。

```python
# Preferred: timestamp-based cooldown
key = f"{symbol}|{timeframe}"
if key in self._last_signal_ts:
    bars_since = self._bars_since(frame, self._last_signal_ts[key])
    if bars_since < self._cooldown_bars():
        return  # skip, still in cooldown
```

### 3.7 Metadata

```python
metadata = {
    "ema_center": float,        # Keltner center line value
    "keltner_upper": float,     # Keltner upper channel value
    "adx": float,               # ADX value at entry
    "atr": float,               # ATR value at entry
    "supertrend_dir": int,      # SuperTrend direction at entry (context)
    "prev_close": float,        # Previous candle close (for cross verification)
}
```

---

## 4. Plugin B: `rsi_mean_reversion_15m`

### 4.1 Identity

```python
id = "rsi_mean_reversion_15m"
version = "0.1.0"
tags = {"external_candidate", "rsi", "bollinger", "15m", "long_only", "mean_reversion"}
required_timeframes = {"15m": 200}
required_indicators = {"rsi", "bollinger", "atr", "adx"}
allowed_symbols = {"BTC/USDT", "ETH/USDT"}
max_concurrent_positions = None  # kernel per-symbol limit applies
risk_profile = StrategyRiskProfile.fixed_risk_pct()
```

### 4.2 Params Schema

```python
params_schema = {
    "symbol": "str",              # optional: lock to single symbol
    "timeframe": "str",           # default "15m"
    "rsi_entry": "float",         # default 25.0 (RSI below this = oversold entry)
    "rsi_exit": "float",          # default 60.0 (RSI above this = exit target)
    "adx_max": "float",           # default 25.0 (ADX above this = trending, skip)
    "bb_confirm": "bool",         # default True (require price <= bb_lower for entry)
    "stop_atr_mult": "float",     # default 1.5 (stop-loss = entry - mult * ATR)
    "cooldown_bars": "int",       # default 5 (min bars between signals, ~1.25h on 15m)
    "emit_once": "bool",          # default True
    "risk_pct": "float",          # optional override per-plugin risk
}
```

### 4.3 Entry Logic: `generate_candidates()`

```
Entry conditions (ALL must be true):
  1. RSI(14) < rsi_entry                     — deep oversold
  2. close <= bb_lower (if bb_confirm=True)   — price at/below lower Bollinger Band
  3. ADX(14) < adx_max                        — NOT trending (mean reversion viable)
  4. cooldown check passed                    — no signal in last N bars for this symbol
```

**Why this works:** RSI < 25 是深度超賣，不是隨便的 dip。加上 BB lower band 確認 price 確實在統計極端。ADX < 25 確保市場是 ranging 而不是 breakdown — 在 breakdown 裡做 mean reversion 會被碾壓。雙重確認提高 per-trade edge，讓策略能承受較高的交易頻率。

**Implementation notes:**
- `rsi_14` 來自 registry（`IndicatorRegistry` apply 時 `rsi` group 產生 `rsi_14`）
- `bb_lower` 來自 registry（`bollinger` group 產生 `bb_lower`）
- `adx` 來自 registry（`adx` group 產生 `adx`）
- `atr` 來自 registry
- 全部是現成欄位，plugin 內不需要自行計算 indicator

### 4.4 Stop Hint

```python
stop_price = entry_price - stop_atr_mult * atr
StopHint(
    price=stop_price,
    reason="rsi_mean_reversion_atr_stop",
    metadata={"atr": atr, "atr_mult": stop_atr_mult, "rsi": rsi_value, "bb_lower": bb_lower},
)
```

### 4.5 Exit Logic: `update_position()`

```
Exit conditions (ANY triggers CLOSE):
  1. RSI(14) > rsi_exit           — mean reversion target reached
  2. close > bb_mid               — price returned to BB middle line
  3. ADX(14) > 30                 — market shifted to trending, abort reversion thesis
```

Condition 3 是安全閥 — 如果持倉期間市場突然進入趨勢，mean reversion thesis 失效，立即出場。

### 4.6 Cooldown Mechanism

同 Plugin A pattern，但 `cooldown_bars` default = 5（15m × 5 = 1.25h minimum between entries per symbol）。

### 4.7 Metadata

```python
metadata = {
    "rsi": float,               # RSI value at entry
    "bb_lower": float,          # BB lower band at entry
    "bb_mid": float,            # BB middle line (exit target reference)
    "adx": float,               # ADX value at entry
    "atr": float,               # ATR value at entry
    "close": float,             # Close price at entry
}
```

---

## 5. Catalog Registration

在 `trader/strategies/plugins/_catalog.py` 的 `STRATEGY_CATALOG` 新增：

```python
"keltner_breakout_1h": {
    "enabled": False,
    "module": "trader.strategies.plugins.keltner_breakout",
    "class": "KeltnerBreakoutStrategy",
    "params": {
        "timeframe": "1h",
        "keltner_ema_len": 20,
        "keltner_atr_mult": 1.5,
        "adx_threshold": 25.0,
        "stop_atr_mult": 2.0,
        "cooldown_bars": 3,
    },
},
"rsi_mean_reversion_15m": {
    "enabled": False,
    "module": "trader.strategies.plugins.rsi_mean_reversion",
    "class": "RsiMeanReversionStrategy",
    "params": {
        "timeframe": "15m",
        "rsi_entry": 25.0,
        "rsi_exit": 60.0,
        "adx_max": 25.0,
        "bb_confirm": True,
        "stop_atr_mult": 1.5,
        "cooldown_bars": 5,
    },
},
```

**重要：`enabled: False`** — catalog presence 不是 runtime promotion。遵守 CLAUDE.md safety boundary。

---

## 6. File Structure

新增檔案：

```
trader/strategies/plugins/keltner_breakout.py       # Plugin A
trader/strategies/plugins/rsi_mean_reversion.py      # Plugin B
trader/tests/test_keltner_breakout_strategy.py       # Plugin A tests
trader/tests/test_rsi_mean_reversion_strategy.py     # Plugin B tests
```

修改檔案：

```
trader/strategies/plugins/_catalog.py               # 新增兩個 catalog entries
```

---

## 7. Test Plan

### 7.1 Test Pattern

遵循 `test_macd_zero_line_strategy.py` 的 pattern：

- `_frame()` helper：建立帶有所需 indicator columns 的 mock DataFrame
- `_context()` helper：包裝成 `StrategyContext` with `SimpleNamespace` snapshot
- 每個 test 獨立建構 plugin instance，不依賴 global state

### 7.2 Plugin A Tests (`test_keltner_breakout_strategy.py`)

```
test_registry_loads_keltner_breakout_plugin
  — StrategyRegistry.from_config 能正確載入，驗證 id/symbols/risk_profile

test_keltner_breakout_generates_long_on_channel_break
  — prev close <= keltner_upper, current close > keltner_upper, ADX > 25 → emit intent

test_keltner_breakout_requires_adx_above_threshold
  — close > keltner_upper but ADX = 20 → no intent

test_keltner_breakout_requires_cross_not_already_above
  — prev close already > keltner_upper → no intent (not a fresh breakout)

test_keltner_breakout_cooldown_blocks_rapid_signals
  — 連續兩根 bar 都符合 → 只有第一根 emit

test_keltner_breakout_exit_on_close_below_ema
  — update_position: close < ema_center → CLOSE

test_keltner_breakout_exit_on_adx_exhaustion
  — update_position: ADX < 20 → CLOSE

test_keltner_breakout_hold_when_trend_intact
  — update_position: close > ema_center AND ADX > 25 → HOLD

test_keltner_breakout_stop_hint_calculation
  — verify stop_price = entry - stop_atr_mult * atr, metadata correct

test_keltner_breakout_skips_unsupported_symbol
  — symbol not in allowed_symbols → no intent

test_keltner_breakout_handles_insufficient_data
  — frame with < 2 rows → graceful empty return
```

### 7.3 Plugin B Tests (`test_rsi_mean_reversion_strategy.py`)

```
test_registry_loads_rsi_mean_reversion_plugin
  — StrategyRegistry.from_config 能正確載入

test_rsi_mr_generates_long_on_oversold_with_bb
  — RSI < 25, close <= bb_lower, ADX < 25 → emit intent

test_rsi_mr_requires_rsi_below_threshold
  — RSI = 35 (above 25) → no intent

test_rsi_mr_requires_bb_lower_confirmation
  — RSI < 25 but close > bb_lower, bb_confirm=True → no intent

test_rsi_mr_can_disable_bb_confirmation
  — RSI < 25, close > bb_lower, bb_confirm=False → emit intent

test_rsi_mr_blocks_in_trending_market
  — RSI < 25, close <= bb_lower, but ADX = 30 → no intent

test_rsi_mr_cooldown_blocks_rapid_signals
  — 連續 bars 符合 → cooldown 內只 emit 一次

test_rsi_mr_exit_on_rsi_recovery
  — update_position: RSI > 60 → CLOSE

test_rsi_mr_exit_on_price_to_bb_mid
  — update_position: close > bb_mid → CLOSE

test_rsi_mr_exit_on_trend_onset
  — update_position: ADX > 30 → CLOSE (safety valve)

test_rsi_mr_hold_when_still_oversold
  — update_position: RSI = 40, close < bb_mid, ADX < 25 → HOLD

test_rsi_mr_stop_hint_calculation
  — verify stop_price and metadata

test_rsi_mr_handles_nan_indicators
  — frame 有 NaN RSI/BB → graceful empty return
```

---

## 8. Backtest Plan

### 8.1 Config Presets

兩個 plugin 的 backtest 都走 StrategyRuntime path，不 bypass central risk。

`extensions/Backtesting/config_presets.py` 需要確認以下 key 已在 `ALLOWED_BACKTEST_OVERRIDES` 中（大部分已有）：

- `STRATEGY_RUNTIME_ENABLED` (需要設 True)
- `ENABLED_STRATEGIES` (需要設為 target plugin id)
- `RISK_PER_TRADE`, `MAX_TOTAL_RISK`, `MAX_SL_DISTANCE_PCT` (已有)

### 8.2 Backtest Run Configuration

```python
# Plugin A backtest
config_overrides = {
    "STRATEGY_RUNTIME_ENABLED": True,
    "ENABLED_STRATEGIES": ["keltner_breakout_1h"],
    "SYMBOLS": ["BTC/USDT", "ETH/USDT"],
    "RISK_PER_TRADE": 0.017,
}

# Plugin B backtest
config_overrides = {
    "STRATEGY_RUNTIME_ENABLED": True,
    "ENABLED_STRATEGIES": ["rsi_mean_reversion_15m"],
    "SYMBOLS": ["BTC/USDT", "ETH/USDT"],
    "RISK_PER_TRADE": 0.017,
}

# Combined backtest
config_overrides = {
    "STRATEGY_RUNTIME_ENABLED": True,
    "ENABLED_STRATEGIES": ["keltner_breakout_1h", "rsi_mean_reversion_15m"],
    "SYMBOLS": ["BTC/USDT", "ETH/USDT"],
    "RISK_PER_TRADE": 0.017,
}
```

### 8.3 Backtest Evaluation Criteria

Per Minara study findings, key metrics to evaluate:

| Metric | Target | Rationale |
|---|---|---|
| APR (after fees) | > 30% | Ruei's requirement |
| Sharpe ratio | > 1.0 | Risk-adjusted return |
| Max drawdown | < 25% | Capital preservation |
| Profit factor | > 1.5 | Win size vs loss size |
| Trade count / year | > 250 combined | ≥ 5/week requirement |
| Fee drag | < 15% of gross return | Minara: >20% drag = danger |
| Win rate | 35-55% | Aligned with Minara winners profile |

---

## 9. Implementation Order

### Phase 1: Plugin A — `keltner_breakout_1h`

1. 建立 `trader/strategies/plugins/keltner_breakout.py`
2. 建立 `trader/tests/test_keltner_breakout_strategy.py`
3. 新增 catalog entry（`enabled: False`）
4. 跑 tests: `python -m pytest trader/tests/test_keltner_breakout_strategy.py -v`
5. 跑 Config validate: `python -c "from trader.config import Config; Config.validate()"`

### Phase 2: Plugin B — `rsi_mean_reversion_15m`

6. 建立 `trader/strategies/plugins/rsi_mean_reversion.py`
7. 建立 `trader/tests/test_rsi_mean_reversion_strategy.py`
8. 新增 catalog entry（`enabled: False`）
9. 跑 tests: `python -m pytest trader/tests/test_rsi_mean_reversion_strategy.py -v`
10. 跑 full test suite: `python -m pytest trader/tests extensions/Backtesting/tests -q`

### Phase 3: Backtest Validation

11. Plugin A 單獨 backtest（BTC/ETH, 1h, ≥ 730 bars）
12. Plugin B 單獨 backtest（BTC/ETH, 15m, ≥ 90 days）
13. Combined backtest（both plugins active）
14. 寫 backtest report 到 `reports/`

---

## 10. Risk & Edge Cases

### 10.1 Fee Sensitivity

Minara 發現年交易 200+ 次是危險區。我們的 combined target 是 260/年。
**Mitigation:** cooldown mechanism + strict entry gates (ADX/RSI/BB multi-confirm) 確保 per-trade edge 夠大。Backtest 時要用真實費率結構驗證。

### 10.2 ADX Regime Overlap

ADX 在 23-27 之間時兩個策略可能同時安靜（A 嫌 ADX 不夠高，B 嫌 ADX 不夠低）。
**Mitigation:** 這是 feature 不是 bug — 不確定的市場就不交易。但如果 backtest 顯示 gap 太大，可以微調 threshold（A 降到 23，B 升到 27）讓區間 overlap。

### 10.3 Ranging Market Breakdown

Plugin B 在 ADX < 25 時做 mean reversion，但 range 可能突然變成 breakdown。
**Mitigation:** ADX > 30 safety valve exit + ATR stop hint。update_position 裡的 trend-onset exit 就是為了這個。

### 10.4 15m Timeframe Data Volume

15m bars lookback 200 = 50 hours。如果 data provider 有限制，確認能取到足夠的 historical data。
**Mitigation:** 確認 `required_timeframes = {"15m": 200}` 在 data fetching layer 有被尊重。

### 10.5 Plugin 不可違反的 Frozen Contract

兩個 plugin 都必須遵守：
- 不直接 size orders（只 emit `SignalIntent` with `stop_hint`）
- 不直接 place orders（交給 kernel execution）
- 不 mutate `Config` defaults
- 不 load credentials
- 不 write runtime persistence
- 不 bypass central risk / arbiter / router / execution handoff

---

## 11. Stretch Goals (Optional, 不在 Phase 1-3 scope)

- **Trailing stop via UPDATE_SL:** Plugin A 用 SuperTrend line 做 trailing stop（`PositionDecision(action=Action.UPDATE_SL, new_sl=supertrend_line)`）
- **PARTIAL_CLOSE:** Plugin B 在 RSI 回到 45 時先平一半，RSI > 60 平剩餘
- **Cross-symbol correlation filter:** 如果 BTC 和 ETH 同時觸發 mean reversion，可能是 market-wide event 而不是 range-bound dip — 考慮只取一邊
- **Dynamic risk_pct:** 根據 recent drawdown 動態調整 risk per trade

---

## 12. References

- [Minara: "We backtested 236 TradingView strategies"](https://x.com/minara/status/2044436294764519851)
- [MinaraCN 中文版](https://x.com/MinaraCN/status/2044620258506625334)
- Existing plugin reference: `trader/strategies/plugins/macd_zero_line.py`
- Existing plugin reference: `trader/strategies/plugins/ema_cross_7_19.py`
- Existing test reference: `trader/tests/test_macd_zero_line_strategy.py`
- Plugin contract: `trader/strategies/base.py`
- Indicator registry: `trader/indicators/registry.py`
- Catalog: `trader/strategies/plugins/_catalog.py`
