# Ranging Strategy Brainstorm — Design Doc

> Status: **READY FOR HANDOFF (2026-04-24).** Documentation-side complete.
> Implementation handoff: **Codex** per pipeline split agreed on 2026-04-24
> (小波 produces spec/plan, Codex implements code + runs backtests).
> Date: 2026-04-24
> Branch: `codex/strategy-runtime-reset`
> Author: 小波 (brainstorming session with Ruei)
> Skill: `superpowers:brainstorming`

---

## 0. Why this document exists

The current strategy-plugin surface is biased toward TRENDING_UP cartridges (MACD family on 4h/1d, EMA cross). The one RANGING attempt, δ (`rsi_mean_reversion_1h`), failed its own declared regime:

- Declared `target_regime: RANGING`, but `net_pnl = -0.48%` in the RANGING window (§3.2 fail).
- Root cause (per `reports/rsi_mean_reversion_research_note.md` learning 3(a)): local snapshot `adx < 25` is not a reliable "truly ranging" filter — the arbiter classified 65.6% of the nominal RANGING window as TRENDING.
- The γ sibling (`rsi_mean_reversion_15m`) is parked on infra grounds (§5 gate: backtest engine lacks 15m support).

This doc brainstorms three replacement RANGING candidates, each designed around a **different "ranging detection" mechanism** so the portfolio is not single-point-of-failure on one filter.

All three are intended to be converted into `plans/cartridge_spec_<id>.md` files and implemented as StrategyPlugins, but **neither conversion nor implementation has started**. This doc only captures the design consensus reached with Ruei during the brainstorming session.

---

## 1. Shared Architecture & Locked Decisions

### 1.1 Portfolio shape

| | Cartridge 1 | Cartridge 2 | Cartridge 3 |
|---|---|---|---|
| id | `bb_fade_squeeze_1h` | `donchian_range_fade_4h` | `rsi2_pullback_1h` |
| Entry TF | 1h | 4h | 1h |
| HTF gate | 4h ADX | (none — geometric filter) | 4h SMA(200) |
| Entry mechanism | Oscillator (BB + RSI) + squeeze percentile | Price geometry (Donchian width stability + two-side touch) | Short-window RSI(2) + long-trend SMA |
| Decorrelation source | HTF regime gate + BBW squeeze | Not indicator-based | Cross-TF trend alignment |
| Expected frequency (BTC+ETH) | 3–5/week | 1–2/week | 4–6/week |
| Regime declaration | `RANGING` | `RANGING` | `ANY` |

Combined target: ~8–13 trades/week — above Ruei's ≥5/week floor with three uncorrelated edge sources.

### 1.2 Decision A — Regime declarations (LOCKED)

- **C1**: `target_regime: RANGING`. BBW squeeze + HTF ADX gate specifically targets compressed, non-trending structure.
- **C2**: `target_regime: RANGING`. Geometric range filter is the declared thesis.
- **C3**: `target_regime: ANY`. Thesis is cross-regime (long-trend + short-pullback); forcing `RANGING` would misalign §3.2 with actual edge profile.

Per checklist §2.5: C1 and C2 must carry an `off-regime entry suppression` line in their Locked Spec; C3 does not need one.

### 1.3 Decision B — Multi-TF access pattern (VERIFIED 2026-04-24)

**Verification result: PASSED.** C1 and C3 can proceed with HTF gates in primary spec; §1.4 fallback is moot.

Evidence collected:

- `trader/strategies/base.py:114` — `MarketSnapshot.get(symbol, timeframe) -> DataFrame` is a simple dict lookup `self.frames.get(symbol, {}).get(timeframe, pd.DataFrame())`. Any timeframe passed in is served if populated.
- `trader/strategy_runtime.py:40–64` — `MarketSnapshotBuilder.build` iterates every enabled plugin's `required_timeframes.items()`, unions `(warmup, required_indicators)` per timeframe across all plugins, then fetches + applies indicators per (symbol, timeframe) and packages into `frames[symbol][timeframe]`.
- Existing multi-TF precedent: `macd_signal_trending_up_4h.py` declares `required_timeframes = {"4h": 200, "1d": 260}` and reads both `entry_frame = context.snapshot.get(symbol, entry_timeframe)` and `trend_frame = context.snapshot.get(symbol, trend_timeframe)` in `generate_candidates`. Matches exactly the pattern C1 and C3 need.

**Side-effect that implementers should know**: indicators are unioned **across all declared TFs**. If C1 declares `required_indicators = {"bollinger", "rsi", "bbw", "adx", "atr"}` and `required_timeframes = {"1h": 200, "4h": 120}`, then **all five indicators are applied to both 1h and 4h frames**. The plugin only reads `adx` from 4h, but `bbw`, `bb_lower`, `rsi_14`, `atr` are also computed on 4h. Harmless (extra compute, no correctness issue), and may actually be useful for future exit-logic additions.

### 1.4 Fallback plan (not triggered — §1.3 passed)

Retained for documentation. Would have applied if cross-TF access were unavailable:

- **C1 downgrade**: drop 4h ADX gate; replace with 1h ADX persistence filter `adx[1h] < 20 for last 10 bars`.
- **C3 downgrade**: drop 4h SMA(200) gate; rely solely on 1h SMA(200).

### 1.5 Indicator registry constraints (verified 2026-04-24 from `trader/indicators/registry.py`)

The registry emits fixed-parameter indicator columns only. Plugins must compute anything non-standard internally.

| Registry output | Source |
|---|---|
| `ema_20`, `ema_50`, `ema_200` | `ema` group |
| `sma_20`, `sma_50`, `sma_200` | `sma` group |
| `atr` (length=14) | `atr` group |
| `adx` (length=14) | `adx` group |
| `bbw` (length=20, std=2.0) | `bbw` group |
| `rsi_14` (length=14 only) | `rsi` group |
| `bb_mid`, `bb_upper`, `bb_lower` (length=20, std=2.0) | `bollinger` group |
| `macd`, `macd_signal`, `macd_hist` (12/26/9) | `macd` group |
| `supertrend`, `supertrend_direction` (length=10, mult=3.0) | `supertrend` group |

Cartridge-specific plugin-internal computations required:

- **C1**: `bbw_pctrank` — rolling percentile rank of `bbw` over `bbw_pctrank_window` bars. Not a registry column.
- **C2**: `donchian_high`, `donchian_low`, `donchian_mid`, `width_cv`, touch counts — all plugin-internal. Not a registry column.
- **C3**: `rsi_2` — registry only emits `rsi_14`. Plugin must reuse `IndicatorRegistry._rsi(close, length=2)` or mirror the formula. Also `sma_5` — registry only emits 20/50/200; plugin uses `frame["close"].rolling(5).mean()`.

Pattern precedent: `trader/strategies/plugins/ema_cross_7_19.py` uses `_with_emas` helper to add non-registry EMA lengths. Same approach applies here.

### 1.6 Shared contract invariants

All three cartridges follow the frozen StrategyPlugin contract:

- LONG-only primary; short-mirror logic documented in spec "Out of Scope" but not implemented in first pass.
- `risk_profile = StrategyRiskProfile.fixed_risk_pct()`, overridable via param `risk_pct`.
- `stop_hint` emits to central `RiskPlan`; no self-sizing.
- `emit_once=True` + timestamp-based `cooldown_bars` to prevent duplicate intents on the same candle or in rapid succession.
- Registered in `trader/strategies/plugins/_catalog.py` with `enabled: False` at first land.
- Each cartridge gets a `plans/cartridge_spec_<id>.md` per checklist §8 format.

---

## 2. Cartridge 1 — `bb_fade_squeeze_1h`

### 2.1 Identity

```python
id = "bb_fade_squeeze_1h"
version = "0.1.0"
tags = {"external_candidate", "bollinger", "rsi", "bbw_squeeze", "1h", "long_only", "mean_reversion", "ranging"}
required_timeframes = {"1h": 200, "4h": 120}
required_indicators = {"bollinger", "rsi", "bbw", "adx", "atr"}
allowed_symbols = {"BTC/USDT", "ETH/USDT"}
max_concurrent_positions = None
risk_profile = StrategyRiskProfile.fixed_risk_pct()
```

### 2.2 Params schema

```python
params_schema = {
    "symbol": "str",
    "timeframe": "str",              # default "1h"
    "htf_timeframe": "str",          # default "4h"
    "rsi_entry": "float",            # default 30.0
    "rsi_exit": "float",             # default 55.0
    "bbw_pctrank_max": "float",      # default 20.0
    "bbw_pctrank_window": "int",     # default 100
    "htf_adx_max": "float",          # default 20.0
    "htf_adx_exit": "float",         # default 25.0
    "stop_atr_mult": "float",        # default 1.5
    "cooldown_bars": "int",          # default 5
    "emit_once": "bool",             # default True
    "risk_pct": "float",
}
```

### 2.3 Entry logic (LONG)

All conditions on latest closed 1h bar:

1. `rsi_14[1h] < rsi_entry` (oversold)
2. `close[1h] <= bb_lower[1h]` (statistical extreme)
3. `bbw_pctrank[1h] < bbw_pctrank_max` where pctrank is current `bbw` ranked within last `bbw_pctrank_window` bars, scale 0..100 (true compression, not casual low)
4. `adx[4h] < htf_adx_max` (HTF non-trending)
5. Cooldown since last signal ≥ `cooldown_bars`

### 2.4 Why this addresses δ's failure

δ's only regime filter was snapshot `adx[1h] < 25`. This cartridge upgrades regime detection to two independent checks:

- **HTF ADX** — a higher-timeframe, slower-moving gauge of directional strength.
- **BBW percentile over a 4-day window** — a history-aware check that current volatility compression is genuinely atypical, not casually low.

This directly answers research-note learning 3(a) (65.6% of δ's RANGING window was still TRENDING per the arbiter).

### 2.5 Stop hint

```python
stop_price = entry_price - stop_atr_mult * atr_1h    # default mult = 1.5
StopHint(
    price=stop_price,
    reason="bb_fade_squeeze_atr_stop",
    metadata={
        "atr_1h": atr_1h, "atr_mult": stop_atr_mult,
        "bb_lower": bb_lower, "bbw_pctrank": bbw_pctrank,
        "htf_adx": htf_adx,
    },
)
```

### 2.6 Exit logic (`update_position`)

Exit on ANY of:

1. `close[1h] > bb_mid[1h]` — mean reversion target (primary)
2. `rsi_14[1h] > rsi_exit` — RSI back to neutral
3. `adx[4h] > htf_adx_exit` — HTF regime flip safety valve

### 2.7 Cooldown

Timestamp-based, sharing δ's `_last_signal_ts` + `_bars_since(frame, ts)` pattern. Default 5 hours.

### 2.8 Intent metadata

```python
{
    "rsi_14": float, "bb_lower": float, "bb_mid": float, "bb_upper": float,
    "bbw": float, "bbw_pctrank": float,
    "htf_adx": float, "atr_1h": float, "close": float,
    "htf_timeframe": "4h",
}
```

### 2.9 Regime Declaration (for `plans/cartridge_spec_bb_fade_squeeze_1h.md`)

```
- target_regime: RANGING
- rationale: BBW percentile squeeze + HTF (4h) ADX gate specifically
  targets compressed, non-trending structure.
- off-regime entry suppression: entry requires `adx[4h] < htf_adx_max`;
  entries blocked when HTF is trending.
```

### 2.10 Short mirror (documented only, not implemented first pass)

```
entry: close >= bb_upper, rsi_14 > 100 - rsi_entry (70),
       bbw_pctrank < bbw_pctrank_max, adx[4h] < htf_adx_max
stop:  entry + stop_atr_mult * atr_1h
exit:  close < bb_mid  OR  rsi_14 < 100 - rsi_exit (45)
       OR  adx[4h] > htf_adx_exit
```

### 2.11 Implementation notes

- `bbw_pctrank` is **not** a registry column. Plugin computes rolling percentile internally:
  `frame["bbw"].rolling(bbw_pctrank_window).rank(pct=True).iloc[-1] * 100`
- HTF access via `context.snapshot.get(symbol, self.params["htf_timeframe"])` (subject to §1.3 verification).
- `bb_lower`, `bb_mid`, `bb_upper`, `bbw`, `rsi_14`, `adx`, `atr` are all registry-provided.

---

## 3. Cartridge 2 — `donchian_range_fade_4h`

### 3.1 Identity

```python
id = "donchian_range_fade_4h"
version = "0.1.0"
tags = {"external_candidate", "donchian", "structural_range", "rsi", "4h", "long_only", "mean_reversion", "ranging"}
required_timeframes = {"4h": 200}    # single-TF, geometric filter self-contained
required_indicators = {"rsi", "atr"}
allowed_symbols = {"BTC/USDT", "ETH/USDT"}
max_concurrent_positions = None
risk_profile = StrategyRiskProfile.fixed_risk_pct()
```

### 3.2 Params schema

```python
params_schema = {
    "symbol": "str",
    "timeframe": "str",              # default "4h"
    "donchian_len": "int",           # default 20
    "range_window": "int",           # default 15
    "range_width_cv_max": "float",   # default 0.10
    "touch_atr_band": "float",       # default 0.25
    "min_lower_touches": "int",      # default 1
    "min_upper_touches": "int",      # default 1
    "rsi_entry": "float",            # default 40.0
    "exit_target": "str",            # default "mid" | alt "opposite"
    "break_atr_mult": "float",       # default 0.5
    "stop_atr_mult": "float",        # default 1.5
    "cooldown_bars": "int",          # default 3
    "emit_once": "bool",             # default True
    "risk_pct": "float",
}
```

### 3.3 Range structure detection

Given latest bar index `i`, window `W = range_window`, `N = donchian_len`:

```
donchian_high[t] = max(high[t-N+1 .. t])
donchian_low[t]  = min(low[t-N+1 .. t])
donchian_mid[t]  = (donchian_high[t] + donchian_low[t]) / 2
width[t]         = donchian_high[t] - donchian_low[t]

range_detected iff ALL:
  (a) stability:
        std(width[i-W+1..i]) / mean(width[i-W+1..i]) < range_width_cv_max
  (b) lower tested:
        count of t in [i-W+1..i] where
          low[t] <= donchian_low[t] + touch_atr_band * atr[t]
        is >= min_lower_touches
  (c) upper tested:
        count of t in [i-W+1..i] where
          high[t] >= donchian_high[t] - touch_atr_band * atr[t]
        is >= min_upper_touches
```

(a) filters out expanding/contracting channels. (b)+(c) require evidence that both boundaries have actually been tested — the box is observed, not inferred.

### 3.4 Entry logic (LONG)

All conditions on latest closed 4h bar:

1. `range_detected` per §3.3
2. `close <= donchian_low + touch_atr_band * atr` (price hugs lower boundary)
3. `rsi_14 < rsi_entry` (confirmation)
4. Cooldown since last signal ≥ `cooldown_bars`

### 3.5 Why this avoids δ's trap

No ADX anywhere. "This is a range" is established by price geometry over the last 15 × 4h bars (~2.5 days): width stable, both sides touched. This is structurally observed range, not indicator-inferred.

### 3.6 Stop hint

```python
stop_price = entry_price - stop_atr_mult * atr    # default 1.5
StopHint(
    price=stop_price,
    reason="donchian_range_fade_atr_stop",
    metadata={
        "atr": atr, "atr_mult": stop_atr_mult,
        "donchian_low": donchian_low, "donchian_high": donchian_high,
        "width_cv": width_cv,
    },
)
```

Not using `donchian_low - k*ATR` as stop: the rolling-min channel trails on new lows, stops drift. Fixed ATR stop is more controlled and consistent with sibling cartridges.

### 3.7 Exit logic (`update_position`)

Exit on ANY of:

1. `exit_target == "mid"`: `close >= donchian_mid` (conservative, higher hit rate)
   `exit_target == "opposite"`: `close >= donchian_high - touch_atr_band * atr` (aggressive, full range payoff)
2. Range broken:
   ```
   donchian_high[now] > donchian_high[now-1] + break_atr_mult * atr
     OR
   donchian_low[now]  < donchian_low[now-1]  - break_atr_mult * atr
   ```

Condition 2 is the structural safety valve: box breaks → thesis invalidated → exit regardless of stop distance.

### 3.8 Cooldown

4h × 3 = 12 hours. Prevents repeated re-entries within the same range box.

### 3.9 Intent metadata

```python
{
    "donchian_high": float, "donchian_low": float, "donchian_mid": float,
    "donchian_width": float, "width_cv": float,
    "lower_touches": int, "upper_touches": int,
    "rsi_14": float, "atr": float, "close": float,
    "bars_in_range": int,    # = range_window
}
```

### 3.10 Regime Declaration

```
- target_regime: RANGING
- rationale: Structural geometric range filter — Donchian width
  stability (CV < 10%) AND both boundaries tested within 15-bar
  window. Observed range, not inferred.
- off-regime entry suppression: `range_detected` gate fails when
  channel width is expanding/contracting or one side untested;
  entries blocked outside verified range structure.
```

### 3.11 Short mirror (documented only)

```
entry: range_detected, close >= donchian_high - touch_atr_band * atr,
       rsi_14 > 100 - rsi_entry (60), cooldown ok
stop:  entry + stop_atr_mult * atr
exit:  close <= donchian_mid (or donchian_low for "opposite")
       OR range broken (same rule)
```

### 3.12 Implementation notes

- Donchian not a registry column. Plugin computes:
  `frame["high"].rolling(donchian_len).max()` / `frame["low"].rolling(donchian_len).min()`.
- `width_cv = width.rolling(range_window).std() / width.rolling(range_window).mean()`.
- Touch counts via boolean masks within the window.
- Range-break detection needs `donchian_high/low` at `t-1` — read from frame `.iloc[-2]`.
- Lookback budget: `donchian_len + range_window + buffer ≈ 50 bars`; `required_timeframes = {"4h": 200}` has headroom.

### 3.13 Known risk / limitations

1. **Lag on range break**: cartridge may enter on the bar that turns out to be the first break. Mitigated by fixed ATR stop + exit condition 2.
2. **Stable intervals inside trends**: a pause within a strong trend can satisfy §3.3 for a handful of bars. If the trend resumes against the trade, that's a legitimate thesis cost.
3. **Frequency risk**: CV < 10% is strict; real-world range intervals may be scarcer than estimated. If backtest shows <1/week, consider `range_width_cv_max = 0.15` in sweep.

---

## 4. Cartridge 3 — `rsi2_pullback_1h`

### 4.0 Section 1 revision (LOCKED)

Section 1.1 originally listed C3's HTF gate as "4h ADX". That choice was reconsidered during Section 4 design: ADX is directionless, but C3's thesis is direction-sensitive (long-trend + short pullback). ADX cannot distinguish strong uptrend (desirable for Connors-style entries) from strong downtrend (catastrophic for long entries).

**Revision (Ruei approved Y)**: HTF gate → `close[4h] > sma_200[4h]`. Cross-TF double confirmation of long-term uptrend, matching Connors' original formulation.

### 4.1 Identity

```python
id = "rsi2_pullback_1h"
version = "0.1.0"
tags = {"external_candidate", "rsi2", "connors_style", "sma_trend", "1h", "long_only", "pullback", "high_freq"}
required_timeframes = {"1h": 400, "4h": 250}
required_indicators = {"rsi", "sma", "atr"}
allowed_symbols = {"BTC/USDT", "ETH/USDT"}
max_concurrent_positions = None
risk_profile = StrategyRiskProfile.fixed_risk_pct()
```

### 4.2 Params schema

```python
params_schema = {
    "symbol": "str",
    "timeframe": "str",              # default "1h"
    "htf_timeframe": "str",          # default "4h"
    "rsi_period": "int",             # default 2
    "rsi_entry": "float",            # default 10.0
    "rsi_exit": "float",             # default 70.0
    "sma_trend_len": "int",          # default 200 (on 1h)
    "sma_exit_len": "int",           # default 5 (on 1h)
    "htf_sma_trend_len": "int",      # default 200 (on 4h)
    "stop_atr_mult": "float",        # default 2.0
    "max_hold_bars": "int",          # default 10
    "cooldown_bars": "int",          # default 4
    "emit_once": "bool",             # default True
    "risk_pct": "float",
}
```

### 4.3 Entry logic (LONG)

All conditions on latest closed 1h bar:

1. `rsi_2[1h] < rsi_entry` (deep short-window oversold, default 10)
2. `close[1h] > sma_200[1h]` (1h long-term uptrend)
3. `close[4h] > sma_200[4h]` (4h cross-TF uptrend confirmation)
4. Cooldown since last signal ≥ `cooldown_bars`

### 4.4 Thesis

Within a structurally long uptrend, sudden sharp dips (rsi_2 < 10 — rare, roughly 1–3×/week per symbol in practice) are generally noise or short-term reactions, not trend reversals. Double SMA(200) filter ensures long-term direction is unambiguous, avoiding knife-catches in downtrends.

### 4.5 Stop hint

```python
stop_price = entry_price - stop_atr_mult * atr_1h    # default 2.0 (wider than C1/C2)
StopHint(
    price=stop_price,
    reason="rsi2_pullback_atr_stop",
    metadata={
        "atr_1h": atr_1h, "atr_mult": stop_atr_mult,
        "rsi_2": rsi_2, "sma_200_1h": sma_200_1h, "sma_200_4h": sma_200_4h,
    },
)
```

Stop wider than siblings because rsi_2 entries commonly see a secondary probe of the lows. A 1.5 ATR stop eats too many entries on that second leg.

### 4.6 Exit logic (`update_position`)

Exit on ANY of:

1. `rsi_2[1h] > rsi_exit` (default 70, primary target)
2. `close[1h] > sma_5[1h]` (bounce to short MA)
3. `bars_in_position >= max_hold_bars` (10-hour time stop — Connors-style discipline)
4. `close[4h] < sma_200[4h]` (HTF regime flip safety)

Condition 3 is central to Connors-style logic. Short-window pullback thesis weakens the longer the trade is open; at 10 bars, close unconditionally and wait for the next setup.

**Implementation dependency**: `bars_in_position` needs `position.opened_candle_ts` (or equivalent) from `PositionManager`. Verify during implementation; if unavailable, degrade to conditions 1/2/4 only (ships, but loses the time-stop edge). See §4.11.

### 4.7 Cooldown

1h × 4 = 4 hours. rsi_2 < 10 is rare; cooldown primarily guards against threshold-hover re-triggers.

### 4.8 Intent metadata

```python
{
    "rsi_2": float, "sma_200_1h": float, "sma_200_4h": float,
    "sma_5_1h": float, "atr_1h": float,
    "close": float, "close_4h": float,
    "htf_timeframe": "4h",
}
```

### 4.9 Regime Declaration

```
- target_regime: ANY
- rationale: Long-trend + short-pullback thesis spans regimes.
  Edge is conditional on long-term uptrend (1h & 4h SMA200),
  not on a specific ADX/ranging state. Forcing non-ANY would
  misalign §3.2 gates with actual edge profile.
- (off-regime entry suppression: N/A under ANY)
```

Checklist §3.2 under ANY: needs `net_pnl > 0` in ≥ 2 of 3 DEFAULT_WINDOWS. Expected strongest in TRENDING_UP and MIXED; weakest in RANGING (rsi_2 < 10 is rare in pure consolidation).

### 4.10 Short mirror (documented only)

```
entry: rsi_2 > 100 - rsi_entry (90),
       close[1h] < sma_200[1h], close[4h] < sma_200[4h]
stop:  entry + stop_atr_mult * atr_1h
exit:  rsi_2 < 100 - rsi_exit (30)  OR  close > sma_5[1h]
       OR  bars >= max_hold_bars   OR  close[4h] > sma_200[4h]
```

### 4.11 Implementation notes

- `rsi_2` registry support: verify `IndicatorRegistry` produces `rsi_2`. If it only emits `rsi_14`, plugin computes internally with `period=2` following the existing `_with_emas` pattern in `ema_cross_7_19.py`.
- `sma_5` on 1h: if registry doesn't emit it, compute via `frame["close"].rolling(sma_exit_len).mean()`.
- HTF `close` and `sma_200` on 4h: `context.snapshot.get(symbol, "4h")`; registry must apply `sma_200` group to the 4h frame. Verify at implementation.
- `bars_in_position`: inspect `trader/positions.py` Position dataclass. Expected field: opened candle timestamp. Compute bars as `(latest_1h_ts - opened_candle_ts) / 1h`.

### 4.12 Fee-drag risk (PRIMARY CONCERN)

C3 is the most fee-sensitive of the three.

- Minara study: 200+ trades/year is the danger zone.
- Estimate: rsi_2 < 10 fires ~2–3×/week per symbol → BTC + ETH combined = 4–6/week = ~208–312/year. Right on the danger line.
- True trigger rate is unknown until backtest.

Mitigations already in spec:
- Strict `rsi_entry = 10` (vs common Connors 20)
- `max_hold_bars = 10` time stop caps long-tail losers
- `cooldown_bars = 4` prevents re-triggers

Mandatory at backtest evaluation: fee drag as % of gross return. Minara benchmarks — warning at >15%, danger at >20%. If drag exceeds 20%, reconsider param defaults (counterintuitively, loosening `rsi_entry` can improve drag ratio if gross edge grows faster than fees; that's a §3.4 sweep question, not a spec question).

### 4.13 Portfolio-level fee economics

Combined estimate across all three cartridges: ~8–13 trades/week ≈ 416–676 trades/year. Well above Minara's single-strategy 200/year line.

Rationale for accepting this:
- Three mechanically decorrelated edge sources (indicator oscillator, price geometry, Connors pullback).
- Each cartridge carries its own strict per-trade filter.
- Fee risk is absorbed at the portfolio level by edge diversification, not single-strategy tightening.

This economic argument is **conditional on backtest evidence** that each cartridge's gross-of-fees expectancy is sufficient. Until backtest lands, it remains a design hypothesis.

---

## 5. Testing, Backtest Plan, File Structure

### 5.1 File structure (per cartridge)

Codex creates:

```
trader/strategies/plugins/bb_fade_squeeze_1h.py
trader/strategies/plugins/donchian_range_fade_4h.py
trader/strategies/plugins/rsi2_pullback_1h.py
trader/tests/test_bb_fade_squeeze_1h_strategy.py
trader/tests/test_donchian_range_fade_4h_strategy.py
trader/tests/test_rsi2_pullback_1h_strategy.py
plans/cartridge_spec_bb_fade_squeeze_1h.md
plans/cartridge_spec_donchian_range_fade_4h.md
plans/cartridge_spec_rsi2_pullback_1h.md
```

Codex modifies:

```
trader/strategies/plugins/_catalog.py        # +3 entries, enabled: False
CLAUDE.md                                    # "Current known plugin entries" +3 lines
```

### 5.2 Catalog entries (exact content for `_catalog.py`)

```python
"bb_fade_squeeze_1h": {
    "enabled": False,
    "module": "trader.strategies.plugins.bb_fade_squeeze_1h",
    "class": "BbFadeSqueeze1hStrategy",
    "params": {
        "timeframe": "1h",
        "htf_timeframe": "4h",
        "rsi_entry": 30.0,
        "rsi_exit": 55.0,
        "bbw_pctrank_max": 20.0,
        "bbw_pctrank_window": 100,
        "htf_adx_max": 20.0,
        "htf_adx_exit": 25.0,
        "stop_atr_mult": 1.5,
        "cooldown_bars": 5,
    },
},
"donchian_range_fade_4h": {
    "enabled": False,
    "module": "trader.strategies.plugins.donchian_range_fade_4h",
    "class": "DonchianRangeFade4hStrategy",
    "params": {
        "timeframe": "4h",
        "donchian_len": 20,
        "range_window": 15,
        "range_width_cv_max": 0.10,
        "touch_atr_band": 0.25,
        "min_lower_touches": 1,
        "min_upper_touches": 1,
        "rsi_entry": 40.0,
        "exit_target": "mid",
        "break_atr_mult": 0.5,
        "stop_atr_mult": 1.5,
        "cooldown_bars": 3,
    },
},
"rsi2_pullback_1h": {
    "enabled": False,
    "module": "trader.strategies.plugins.rsi2_pullback_1h",
    "class": "Rsi2Pullback1hStrategy",
    "params": {
        "timeframe": "1h",
        "htf_timeframe": "4h",
        "rsi_period": 2,
        "rsi_entry": 10.0,
        "rsi_exit": 70.0,
        "sma_trend_len": 200,
        "sma_exit_len": 5,
        "htf_sma_trend_len": 200,
        "stop_atr_mult": 2.0,
        "max_hold_bars": 10,
        "cooldown_bars": 4,
    },
},
```

### 5.3 Unit test plan (per cartridge)

Template for each `trader/tests/test_<cartridge>_strategy.py`, mirroring `trader/tests/test_rsi_mean_reversion_1h_strategy.py`:

**Common to all three** (required by promotion checklist §2):

1. `test_registry_loads_<cartridge>_plugin` — `StrategyRegistry.from_config` loads; `id`, `allowed_symbols`, `risk_profile`, `required_timeframes`, `required_indicators` match spec.
2. `test_<cartridge>_generates_long_on_happy_path` — all entry conditions met; exactly one `SignalIntent` emitted with correct `side`, `entry_type`, `candle_ts`, and `stop_hint.price` math.
3. `test_<cartridge>_stop_hint_calculation` — `stop_price = entry - stop_atr_mult * atr` within tolerance; `StopHint.metadata` carries the documented keys.
4. `test_<cartridge>_skips_unsupported_symbol` — symbol outside `allowed_symbols` → no intent.
5. `test_<cartridge>_handles_insufficient_data` — frame with < warmup rows → graceful empty return, no exception.
6. `test_<cartridge>_handles_nan_indicators` — NaN in required columns → graceful empty return.
7. `test_<cartridge>_cooldown_blocks_rapid_signals` — two consecutive qualifying bars → only the first emits.

**C1-specific** (`test_bb_fade_squeeze_1h_strategy.py`):

8. `test_c1_requires_rsi_below_entry` — `rsi_14 = 35` (above 30) → no intent.
9. `test_c1_requires_close_at_or_below_bb_lower` — `close > bb_lower` → no intent.
10. `test_c1_requires_bbw_pctrank_below_threshold` — `bbw_pctrank = 30` (above 20) → no intent.
11. `test_c1_requires_htf_adx_below_gate` — 4h `adx = 25` (above 20) → no intent.
12. `test_c1_exit_on_close_above_bb_mid` — `update_position` returns `CLOSE` with reason.
13. `test_c1_exit_on_rsi_recovery` — `rsi_14 = 60` → `CLOSE`.
14. `test_c1_exit_on_htf_adx_flip` — 4h `adx = 26` (above 25 exit gate) → `CLOSE`.
15. `test_c1_hold_when_still_oversold` — entry condition partially met but exit not triggered → `HOLD`.

**C2-specific** (`test_donchian_range_fade_4h_strategy.py`):

8. `test_c2_requires_range_stability_cv` — synthetic frame where `width_cv = 0.20` (above 0.10) → no intent.
9. `test_c2_requires_lower_touches` — `width_cv` passes but no lower touches within window → no intent.
10. `test_c2_requires_upper_touches` — touches only lower side → no intent.
11. `test_c2_requires_close_near_lower_band` — range detected but `close` mid-range → no intent.
12. `test_c2_requires_rsi_below_entry` — range + close at lower but `rsi_14 > rsi_entry` → no intent.
13. `test_c2_exit_on_close_reaching_mid_target` — `exit_target="mid"`, `close >= donchian_mid` → `CLOSE`.
14. `test_c2_exit_on_close_reaching_opposite_target` — `exit_target="opposite"`, `close >= donchian_high - touch_band` → `CLOSE`.
15. `test_c2_exit_on_range_break_up` — `donchian_high` jumps > `break_atr_mult * atr` → `CLOSE`.
16. `test_c2_exit_on_range_break_down` — `donchian_low` drops > `break_atr_mult * atr` → `CLOSE`.

**C3-specific** (`test_rsi2_pullback_1h_strategy.py`):

8. `test_c3_requires_rsi2_below_entry` — `rsi_2 = 15` (above 10) → no intent.
9. `test_c3_requires_close_above_1h_sma200` — `close[1h] < sma_200[1h]` → no intent.
10. `test_c3_requires_close_above_4h_sma200` — 1h trend passes but 4h `close < sma_200[4h]` → no intent.
11. `test_c3_computes_rsi2_when_registry_absent` — verifies plugin-internal RSI(2) computation path; rsi_2 value matches reference.
12. `test_c3_computes_sma5_when_registry_absent` — verifies plugin-internal SMA(5) path.
13. `test_c3_exit_on_rsi2_recovery` — `rsi_2 > 70` → `CLOSE`.
14. `test_c3_exit_on_close_above_sma5` — `close > sma_5` → `CLOSE`.
15. `test_c3_exit_on_max_hold_bars` — `bars_in_position = max_hold_bars` → `CLOSE` reason `TIME_STOP`.
16. `test_c3_exit_on_htf_flip` — `close[4h] < sma_200[4h]` → `CLOSE`.
17. `test_c3_hold_when_conditions_intact` — mid-trade, no exit triggers → `HOLD`.

### 5.4 Backtest presets

Expected additions to `extensions/Backtesting/config_presets.py` if not already whitelisted:

```
# Already in ALLOWED_BACKTEST_OVERRIDES (verify before change):
STRATEGY_RUNTIME_ENABLED, ENABLED_STRATEGIES, RISK_PER_TRADE,
MAX_TOTAL_RISK, MAX_SL_DISTANCE_PCT, SYMBOLS
```

No new config keys required — all cartridge behavior is plugin-parameterized.

Per-cartridge single-plugin backtest preset pattern (example for C1):

```python
def bb_fade_squeeze_1h_candidate_review():
    return {
        "STRATEGY_RUNTIME_ENABLED": True,
        "ENABLED_STRATEGIES": ["bb_fade_squeeze_1h"],
        "SYMBOLS": ["BTC/USDT", "ETH/USDT"],
        "RISK_PER_TRADE": 0.017,
    }
```

Mirror for C2 and C3. Combined preset (all three active) can be added later once each individual cartridge passes candidate review.

### 5.5 Candidate review pass

Each cartridge runs through the standard candidate review runner (same runner δ used) across all three DEFAULT_WINDOWS (TRENDING_UP, RANGING, MIXED). Output rows land in `reports/strategy_plugin_candidate_review.md`.

**Expected profile per cartridge** (hypotheses to falsify, not predictions):

| | TRENDING_UP | RANGING (declared target) | MIXED |
|---|---|---|---|
| C1 `bb_fade_squeeze_1h` | flat-to-slight-positive (HTF gate suppresses most entries) | **primary evidence window, must be >0** | positive but smaller than RANGING |
| C2 `donchian_range_fade_4h` | near-zero trade count (range rarely detected in trends) | **primary evidence window, must be >0** | modest positive (where stable ranges form) |
| C3 `rsi2_pullback_1h` (ANY) | strongest window (long uptrends = most pullbacks) | weakest window (rsi_2 < 10 rare in pure consolidation) | second-strongest |

If any cartridge's profile deviates materially from this hypothesis (e.g. C1 is strongest in TRENDING_UP but weak in RANGING), the thesis is invalidated even if §3.2 technically passes — flag as `NEEDS_SECOND_PASS`.

### 5.6 Parameter sweep (§3.4 requirement)

Per cartridge, one sweep with ≥ 3 cells. Priority param per cartridge:

| Cartridge | Sweep param | Cells (suggested) |
|---|---|---|
| C1 | `bbw_pctrank_max` | 15.0, 20.0, 25.0 |
| C2 | `range_width_cv_max` | 0.08, 0.10, 0.13 |
| C3 | `rsi_entry` | 5.0, 10.0, 15.0 |

Sweep report file pattern: `reports/strategy_plugin_parameter_sweep_<cartridge>_<param>_min<N>.md`. Status line: `RESEARCH_SWEEP_ONLY`.

### 5.7 Evaluation criteria

All cartridges — promotion checklist gates:

- §2 invariants: `entry_stop_violations == 0`, `backtest_run_error_count == 0`, unit tests pass.
- §3.2 `net_pnl > 0` in declared regime (C1, C2) OR in 2/3 windows (C3 under ANY).
- §3.4 sweep: no declared regime (C1, C2) or no window at all (C3) where all cells have `net_pnl < 0`.
- §4 `max_dd_pct <= 40.0` in every window.

**C3-specific fee-drag gate (proposed addition to evaluation, not yet checklist law)**:

- Compute `fee_drag_ratio = total_fees_usdt / gross_pnl_positive_usdt`.
- Warning at `fee_drag_ratio > 0.15`; hard fail at `> 0.20`.
- Rationale: Minara study established 200+ trades/year as the fee-kill zone; C3's estimated 200–310 trades/year puts it in that zone by design.
- If C3 fails the fee-drag gate, revisit `rsi_entry` sweep before discarding — sometimes loosening entries improves the ratio because gross edge grows faster than fees. This is a sweep-phase decision.

### 5.8 Handoff artifact order

Codex should build in this order (each step independent of the next except for ordering dependencies noted):

1. C2 `donchian_range_fade_4h` — least moving parts (single TF, plugin-internal math only, no HTF gate).
2. C1 `bb_fade_squeeze_1h` — medium complexity (HTF gate, BBW pctrank calc).
3. C3 `rsi2_pullback_1h` — most moving parts (rsi_2 + sma_5 plugin-internal, HTF gate, bars_in_position lookup from Position dataclass).

Ordering is not enforced by dependencies — all three are independent. Purely a complexity gradient to let Codex build confidence with the pattern.

---

## 6. Resumption Checklist

When picking this back up (after `context_gated_weak_tape_defense` research reaches its checkpoint):

1. **Re-read this doc** — especially Section 1 decisions and Section 4.0 revision.
2. **Verify multi-TF snapshot API** — `trader/strategies/base.py` and `trader/strategy_runtime.py`. Confirm `context.snapshot.get(symbol, other_tf)` works or trigger §1.4 fallback plan.
3. **Complete Section 5** — testing / backtest plan / file structure.
4. **Spec self-review** — placeholder scan, internal consistency, scope, ambiguity.
5. **User review gate** — Ruei reviews this doc; iterate if changes requested.
6. **Generate cartridge spec files** — three separate `plans/cartridge_spec_<id>.md` per checklist §8 format. **These are the artifacts that drive implementation**, not this brainstorm doc.
7. **Hand off to `superpowers:writing-plans`** skill to generate the implementation plan.
8. **Do NOT start coding before steps 2–7 are complete.**

---

## 7. References

- `reports/rsi_mean_reversion_research_note.md` — δ failure analysis (source of the "ranging detection" design drive)
- `plans/dual_regime_strategy_plan.md` — prior dual-regime attempt (Keltner breakout + RSI MR); structural template followed here
- `plans/cartridge_promotion_checklist.md` — §2.5 regime declaration, §3.2 net_pnl gate, §8 spec format, §5 timeframe support gate
- `plans/cartridge_spec_rsi_mean_reversion_1h.md` — δ spec (format reference)
- `trader/strategies/plugins/rsi_mean_reversion_1h.py` — closest implementation reference for C1 (oscillator family)
- `trader/strategies/plugins/macd_signal_trending_up_4h.py` — reference for multi-TF access pattern (1d gate + 4h entry)
- `trader/strategies/plugins/ema_cross_7_19.py` — reference for `_with_emas`-style plugin-internal indicator computation (C2 Donchian, C3 RSI(2))
