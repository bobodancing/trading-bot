# Strategy Research Backlog — Design Doc

> **Status: BACKLOG / SCHEDULED RECOVERY / DO-NOT-START.** This document is
> *future research backlog*, not active research. No plugin file, no `_catalog.py` entry, no
> `cartridge_spec_<id>.md`, and no implementation work may begin from this
> document until the activation precondition below is satisfied.

> Date: 2026-04-25
> Branch: `codex/strategy-runtime-reset`
> Author: 小波（PM-side brainstorming session with Ruei）
> Skill: `superpowers:brainstorming`
> Output type: research backlog reference

---

## 0. Activation Precondition (READ BEFORE TOUCHING)

This document lists **9 mechanism units / 18 plugins** as future research
candidates. They may **only** be activated after **both** conditions are
met simultaneously:

### 0.1 Condition (A): Current pipeline fully resolved

[plans/2026-04-25_portfolio_research_reorder_plan.md](2026-04-25_portfolio_research_reorder_plan.md)
must complete its full Phase 1 → Phase 5 sequence:

- **Phase 1** Slot A 解卡 (`squeeze_release_unconfirmed_late_entry_filter`
  candidate review + §3.4 sweep + 8-window supplemental)
- **Phase 2** Slot B Donchian 解凍補驗 (`donchian_range_fade_4h_range_width_cv_013`
  per-symbol matrix + `touch_atr_band` robustness sweep + freeze read 更新)
- **Phase 3** Combined A+B portfolio 級驗證 (combined backtest +
  reject-mix attribution + BTC_TREND_FILTER 互動專項 + decision gate)
- **Phase 4** RSI2 churn-reduction 二輪
  (`rsi2_pullback_1h_sma5_gap_guard` stop-out attribution → child cartridge
  → 三策略 combined backtest)
- **Phase 5** BB Fade Squeeze rescue 評估
  (`bb_fade_squeeze_1h` squeeze definition redesign，依 Phase 1-3 結果決定值不值得補位)

### 0.2 Condition (B): §5 trigger condition fires

[2026-04-25_portfolio_research_reorder_plan.md §5](2026-04-25_portfolio_research_reorder_plan.md)
明文限制新 mechanism 開發 trigger（依 regime 分開，不互通）：

- **新 trending mechanism / 新 Slot A 補位** → 只在以下都成立才討論：
  Slot A 勝出機制在 Phase 1 全項失敗，**且** Phase 4 RSI2 churn-reduction 二輪也失敗
- **新 ranging detection 機制** → 只在以下都成立才討論：
  Slot B (Donchian `range_width_cv_013`) 在 Phase 2 / Phase 3 失敗，
  **且** Phase 5 BB Fade Squeeze rescue 也失敗

本 doc 內 candidate 對應 trigger 對映：

| Candidate slot | 對應 §5 trigger |
|---|---|
| Slot A 三條 (A1/A2/A3) | trending mechanism trigger |
| Slot B 三條 (B1/B2/B3) | ranging mechanism trigger |
| Transition 三條 (T1/T2/T3) | 兩條都不對應，需另外與 Ruei 討論 trigger 條件 |

### 0.3 Codex 不得偷跑（明確警告）

Codex（與任何接手 implementer）在條件 (A)+(B) 未同時成立之前：

- **不得**將任何本 doc candidate id 加入 `trader/strategies/plugins/_catalog.py`（即使 `enabled: False`）
- **不得**實作任何本 doc 提到的 plugin file
- **不得**寫對應的 `plans/cartridge_spec_<id>.md`
- **不得**寫對應的 `trader/tests/test_<id>_strategy.py`
- **不得**將本 doc 內容 copy 到 active plan 並聲稱該 plan 是 active research

如果 Phase 1-5 完成且 §5 trigger 觸發，仍需 **Ruei 明確 approve** 才能將特定 candidate
從 backlog 升級為 active research。本 doc 不是 implementation order，是 reference pool。

### 0.4 2026-04-29 Optimized Scheduling Integration

Ruei approved the A+B runtime promotion on 2026-04-29. The backlog remains
`BACKLOG / SCHEDULED RECOVERY / DO-NOT-START`: it is now explicitly scheduled
as a recovery pool behind the promoted A+B control work, but it is still not
active research.

Execution order from here:

1. **Post-promotion control pass**: verify runtime-default parity, smoke the
   promoted A+B path without per-run strategy overrides, and define deployment
   boundary. This is not new alpha research.
2. **Phase 4 closeout**: run RSI2 third-slot attribution and only continue to
   an A+B+RSI2 combined test if the churn-reduction evidence is clean.
3. **Phase 5 closeout / park decision**: rescue BB Fade Squeeze only if the
   promoted A+B portfolio still shows a ranging-detection gap. If the gap is
   not real, Phase 5 should be explicitly parked rather than forced.
4. **Trigger review memo**: classify the remaining gap as Slot A trend/SHORT,
   Slot B ranging/frequency, or transition-window coverage. No backlog plugin
   can start before this memo exists.
5. **Backlog recovery Wave 1**: activate exactly one mechanism pair after Ruei
   approval. Do not open multiple backlog pairs in parallel until Wave 1 has a
   candidate review, parameter sweep, and combined A+B+candidate attribution.

Extra gate for SHORT candidates: `TRENDING_DOWN` is not yet a fully supported
promotion validation lane. SHORT pairs may be explored as research only after
the trigger review, but promotion testing for SHORT requires an explicit
checklist/report update for `TRENDING_DOWN` windows and BTC trend-filter
silent-block attribution.

---

## 1. Why This Document Exists

### 1.1 Portfolio thesis (Ruei 2026-04-25)

> 至少找到兩種互補策略：
> - Slot A: TRENDING 表現優異，並能壓低 RANGING 時虧損
> - Slot B: RANGING 表現不錯，突然轉 TRENDING 趨勢也能及時止損
> - 理想是 2-4 條策略一起運行(1~2組)，以維持交易量。

### 1.2 Current pipeline coverage gap (per reorder plan §1)

- **Slot A (TRENDING)**: 唯一候選 `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter` — BTC-only，4h，全 momentum / EMA cross family
- **Slot B (RANGING)**: 唯一候選 `donchian_range_fade_4h_range_width_cv_013` — BTC+ETH，4h，geometric range
- **Slot C 候選 (Phase 4)**: `rsi2_pullback_1h_sma5_gap_guard` — ANY-regime，trend-leaning
- **Phase 5 暫停**: `bb_fade_squeeze_1h` — RANGING gate 太嚴

**已試過但失敗或拋棄的方向**：
- ADX-only ranging detection（δ refuted: 65.6% nominal RANGING → arbiter classified TRENDING）
- 15m timeframe（infra：engine 不支援）
- Keltner breakout 1h（mechanism overlap with MACD family）

**Implication**：若 Phase 1-5 完成後仍有 portfolio 缺口（例如 Slot A 全項失敗），
需要 **mechanism-decorrelated** 候選池備用。本 doc 即此備用池。

### 1.3 Brainstorm scope agreed with Ruei

- **Breadth**（不是 gap-fill）— 6-10 個多元 candidate 作研究池
- **Indicator-extended + structural/geometric** — registry 範圍 + plugin-internal 延伸 + price-action geometry，**不**含 volume-derived，**不**含 cross-asset
- **BTC/ETH only**
- **Three regime classes**: Slot A (TRENDING_UP) / Slot B (RANGING) / Regime-transition
- **Bidirectional first-class**: 合約帳戶 SHORT 是 first-class direction，不只是 LONG mirror — 每 mechanism 拆 LONG/SHORT 兩 plugin pair

---

## 2. Locked Design Decisions

### 2.1 Mechanism unit accounting

每個「mechanism unit」描述一個 detection / entry / exit 邏輯家族。Implementation
時拆為兩個 mirror plugins（LONG + SHORT），catalog entries 兩個。

- 9 mechanism units → 18 plugin ids 為總 backlog
- 設計討論以 9 unit 為單位，避免重複描述對稱邏輯
- 個別 unit 可單獨 promote 到 active research（不必 mechanism-pair 同進同退）

### 2.2 Regime declaration mapping

| Slot | Regime declaration |
|---|---|
| Slot A LONG plugin | `TRENDING_UP` |
| Slot A SHORT plugin | `TRENDING_DOWN` |
| Slot B LONG plugin | `RANGING` |
| Slot B SHORT plugin | `RANGING` |
| Transition LONG plugin (T1/T2) | `TRENDING_UP` (post-transition target regime) |
| Transition SHORT plugin (T1/T2) | `TRENDING_DOWN` (post-transition target regime) |
| T3 LONG/SHORT (trend exhaustion reversal) | `ANY` (cross-regime thesis) |

### 2.3 BTC_TREND_FILTER interaction (cross-cutting)

Runtime baseline `BTC_TREND_FILTER_ENABLED = True` + `BTC_COUNTER_TREND_MULT = 0.0`
意味 counter-trend 進場被 sized to 0（silent block）。對本 doc candidate 的影響：

- **Slot A SHORT (TRENDING_DOWN)**：BTC 上行段 → silent block；BTC 下行段 → 開放。**自然 align**，不需 cartridge 內 hack
- **Slot B SHORT (RANGING)**：BTC 上行段 → silent block；只在 BTC 下行 + 個別資產 ranging 的窄窗口 fire（少見但高品質）
- **T3 (ANY-regime reversal)**：與 BTC_TREND_FILTER 有**設計核心衝突** — `downtrend_exhaustion_long_4h` 在 BTC 仍下行段 entry 會被 block，必須等 BTC trend 已 flip 才 fire。實務上是 narrow window，需要 explicit 列入 backtest report

Cartridge spec 與 backtest report 必須**explicit 列出** BTC_TREND_FILTER silent-block
統計 per cartridge per direction（依 [reorder plan Phase 3.2 BTC_TREND_FILTER 互動專項](2026-04-25_portfolio_research_reorder_plan.md) 同 pattern）。

### 2.4 Shared contract invariants

所有 18 plugins 都遵守 frozen StrategyPlugin contract：

- LONG-only or SHORT-only per plugin（雙方向不混在同 plugin）
- `risk_profile = StrategyRiskProfile.fixed_risk_pct()`，central RiskPlan 控 sizing
- `stop_hint` emit 給 central RiskPlan，不自 size
- `emit_once=True` + timestamp-based cooldown
- Plugin 不直接 size / place orders / mutate Config / load credentials / write persistence
- Catalog entry 預設 `enabled: False`
- 與 既有 mechanism family 不重疊（避開 MACD / EMA cross / RSI / BB squeeze pctrank / Donchian fade / RSI2 已 covered 範圍）

### 2.5 Per-cartridge spec format

當特定 candidate 從 backlog 升級為 active research 時，需依 [cartridge_promotion_checklist.md](cartridge_promotion_checklist.md)
§8 format 寫對應 `plans/cartridge_spec_<id>.md`，內容必含：

- Identity（id / version / tags / required_timeframes / required_indicators /
  allowed_symbols / risk_profile）
- Params schema
- Entry logic（LONG 或 SHORT，方向明確）
- Stop hint 計算
- Exit logic
- Cooldown mechanism
- Intent metadata
- Regime declaration（含 off-regime entry suppression for non-ANY）
- Mirror plugin reference（指向對向 spec）
- Pre-Committed Decision Gates（per checklist §3）
- Known risks

---

## 3. Slot A — TRENDING candidates (3 mechanism units, 6 plugins)

### 3.1 A1: SuperTrend flip pair

**Plugins**:
- `supertrend_flip_4h_trending_up` (LONG, regime: `TRENDING_UP`)
- `supertrend_flip_4h_trending_down` (SHORT, regime: `TRENDING_DOWN`)

**Mechanism**: SuperTrend(10, 3.0) `direction` 從一側翻到另一側 = entry trigger。
ATR-trailed direction switch 與既有 MACD（zero-line / signal cross）和 EMA cross
（rate-of-change）的 signal phase 完全不同。Volatility-adaptive trailing 自帶 regime filter。

**LONG entry**:
- `supertrend_direction[-1] == +1 AND supertrend_direction[-2] == -1`
- `close > ema_50` (HTF gate 防 false flip)
- Cooldown gate

**SHORT entry**: 對稱
- `supertrend_direction[-1] == -1 AND supertrend_direction[-2] == +1`
- `close < ema_50`

**Exit**: SuperTrend 翻回原方向 OR `close` cross `ema_50` 反向

**Stop**: `entry ± stop_atr_mult × atr_4h`（default 1.5）

**Symbols / TF**: BTC + ETH，4h

**Why complementary**: 既有 Slot A family 全走 momentum oscillator (MACD) 或
fixed-period MA cross (EMA 7/19)。SuperTrend 用 ATR 動態 trail，本質是
volatility-adjusted trend follow。Edge source 與 oscillator 是兩條獨立 alpha。

**Indicator registry status**:
- `supertrend`, `supertrend_direction` 已存在於 registry（length=10, mult=3.0）
- 若需自訂 length/mult，plugin-internal 計算

**Known risk**:
- SuperTrend 在 ranging 段會頻繁 flip → EMA50 HTF gate 是核心 filter
- 與 既有 MACD 在強趨勢段 signal overlap 機率（同 candle 同 emit）需 backtest 驗 decorrelation
- BTC SHORT 在 BTC 上行段被 BTC_TREND_FILTER silent block — 預期 trade frequency
  比 LONG 低

---

### 3.2 A2: Hull MA + ADX-DI directional pair

**Plugins**:
- `hull_ma_adx_di_1d_trending_up` (LONG, regime: `TRENDING_UP`)
- `hull_ma_adx_di_1d_trending_down` (SHORT, regime: `TRENDING_DOWN`)

**Mechanism**: Hull MA(20) `slope` + ADX(14) > 25 + DI directional confirm。
Hull MA = `WMA(2*WMA(price, n/2) - WMA(price, n), sqrt(n))`，比 EMA 同 length lag 少約 50%。
ADX 看強度，DI 看方向，三條件聯合 = redundancy 抗 single-indicator noise。

**LONG entry**:
- `hull_ma_20.slope > 0`（last 2 bars Hull MA 上行）
- `adx > 25`
- `di_plus > di_minus`
- Cooldown gate

**SHORT entry**: 對稱（slope < 0, di_minus > di_plus）

**Exit**: Hull MA slope flip OR `adx < 20`

**Stop**: `entry ± stop_atr_mult × atr_1d`（default 2.0，1d 較寬）

**Symbols / TF**: BTC + ETH，1d

**Why complementary**:
- 補目前 1d 端覆蓋（pipeline 1d 只有 `macd_zero_line_btc_1d_trending_up`，BTC-only，無 ETH 1d，無 SHORT 1d）
- 三條件 redundancy 抗單一 indicator noise
- 1d 自然低頻 (estimate 1-2/月) → fee drag 容忍度高，per-trade edge 標準可降低

**Indicator registry status**:
- `adx` 已存在於 registry
- DI+/DI- **不在 registry**，plugin-internal 計算（從 `+DM`、`-DM`、`tr` 計算）
- Hull MA **不在 registry**，plugin-internal 計算（pattern 同 `ema_cross_7_19.py` 的 `_with_emas`）

**Known risk**:
- 1d 進場 frequency 低，portfolio 觀感上「策略空閒」— 需 PM-level acceptance
- DI+/DI- 在 sideway 段會頻繁 cross → ADX > 25 gate 是核心 filter
- BTC SHORT 1d 在多年 BTC 累積上行的歷史窗口會非常稀少 — 樣本可能不足以通過 §1.2

---

### 3.3 A3: Aroon + structural break pair

**Plugins**:
- `aroon_break_hh_4h_trending_up` (LONG, regime: `TRENDING_UP`)
- `aroon_break_ll_4h_trending_down` (SHORT, regime: `TRENDING_DOWN`)

**Mechanism**: Aroon = time-since-max/min based oscillator，**訊號類型完全不同
於 momentum oscillator** (MACD/RSI 看 momentum，Aroon 看 recency-of-extreme)。
配合 swing high/low 結構 confirm = indicator + price-action geometry hybrid。

**LONG entry**:
- `aroon_up > 70 AND aroon_down < 30`
- `close > recent_swing_high`（lookback default 20 bars）
- Cooldown gate

**SHORT entry**: 對稱（aroon_down > 70, aroon_up < 30, close < recent_swing_low）

**Exit**: 對向 Aroon dominance 翻轉 (e.g. LONG exit on `aroon_down > 70`) OR
`close` 跌破對向 swing extreme

**Stop**: `entry ± stop_atr_mult × atr_4h`（default 1.5），可選用
`recent_swing_low ± 0.5×atr` 為結構 stop

**Symbols / TF**: BTC + ETH，4h

**Why complementary**:
- Aroon 是 pipeline 內**從未使用過**的 indicator class
- time-recency 訊號 + 結構 geometry 兩層獨立 confirmation，與既有 momentum-based Slot A
  完全 phase-decorrelated
- Bidirectional 對稱性 perfect

**Indicator registry status**:
- Aroon **不在 registry**，plugin-internal 計算
  （`aroon_up = ((period - bars_since_high) / period) * 100`，period default 14）
- Swing high/low 識別（local max/min within lookback + confirmation by next 2 bars not exceeding）
  plugin-internal

**Known risk**:
- Aroon 對 sideway chop 敏感（會有 frequent up/down dominance switch）— 需要嚴
  threshold (70/30) 而非寬 (50/50)
- Swing high 識別 confirmation rule 是 implementation 核心，rule 不嚴會產生 false breakout
- BTC SHORT 在 BTC 上行段被 silent block 的常見問題

---

## 4. Slot B — RANGING candidates (3 mechanism units, 6 plugins)

### 4.1 B1: Swing failure fade pair

**Plugins**:
- `swing_low_failure_fade_4h` (LONG, regime: `RANGING`)
- `swing_high_failure_fade_4h` (SHORT, regime: `RANGING`)

**Mechanism**: 純 price-action 結構 — ranging 區間內，price 突破前 swing low
（intra-bar low < prior swing low）但 close 收回上方 = 突破失敗 = 範圍下緣
支撐確認 → LONG fade。SHORT 對稱。**完全無 indicator 依賴**。

**LONG entry**:
- 找 last 20 bars 內 prior swing low（local minimum confirmed by next 2 bars not breaking lower）
- `low[-1] < prior_swing_low AND close[-1] > prior_swing_low`（failed break）
- RANGING confirm: `close 在 sma_50 ± 1.5 × atr 區間內`（防止在強趨勢誤判 failure）
- Cooldown gate

**SHORT entry**: 對稱（swing high failure pattern + close < prior_swing_high
+ close 在 sma_50 ± 1.5×atr 區間內）

**Exit**: close 達到對向 swing extreme OR 結構性 stop（穿透 prior swing low / high）

**Stop**: `entry ± stop_atr_mult × atr_4h`（default 1.5），可選用
`prior_swing_low ± 0.5×atr` 為結構 stop（取 tighter）

**Symbols / TF**: BTC + ETH，4h

**Why complementary**:
- pipeline 內**完全沒有 pure structural cartridge**（Donchian 是 geometric range，
  但用 indicator 確認；BB 是 statistical extreme）
- Failure pattern 是學術上 well-documented 的 false-breakout fade
- 對稱性 perfect → bidirectional 天然

**Indicator registry status**:
- 只用 `sma_50`（registry 提供）+ `atr`（registry 提供）+ price OHLC
- swing 識別 plugin-internal

**Known risk**:
- swing 識別 lookback + confirmation rule 是 implementation 核心
  （last N bars local min + next 2 bars 不破 = confirmed），rule 不嚴會誤判
- 在強趨勢中 swing failure 可能是 trend pause 而非 reversal — RANGING gate
  (`sma_50 ± 1.5 × atr`) 是核心 filter
- 結構 stop 與 ATR stop 取 tighter 的選擇需 backtest 驗哪個 max_dd 較小

---

### 4.2 B2: Ichimoku Kumo fade pair

**Plugins**:
- `ichimoku_kumo_lower_fade_4h` (LONG, regime: `RANGING`)
- `ichimoku_kumo_upper_fade_4h` (SHORT, regime: `RANGING`)

**Mechanism**: Ichimoku Cloud (Senkou A/B span) 是 forward-displaced average
形成的動態 range structure。Price 在雲內 ranging 並觸及雲邊緣 → fade 回 cloud mid。
Cloud thickness 自然 filter 出有 directional consensus 的 ranging window。

**LONG entry**:
- Price 在 cloud 內：
  `low ≥ min(senkou_a, senkou_b) AND high ≤ max(senkou_a, senkou_b)`
  持續 N bars（雲內 ranging confirm，default N = 5）
- `close ≤ min(senkou_a, senkou_b) + 0.25 × atr`（近雲底）
- `rsi_14 < 35`
- Cloud thickness gate: `|senkou_a - senkou_b| / atr > 1.0`（雲不太薄 = 有實質 range structure）
- Cooldown gate

**SHORT entry**: 對稱（near cloud top + rsi > 65 + cloud thickness gate）

**Exit**: `close` 達 cloud mid `(senkou_a + senkou_b) / 2` OR price 突破 cloud（thesis broken）

**Stop**: `entry ± stop_atr_mult × atr_4h`（default 1.5）

**Symbols / TF**: BTC + ETH，4h

**Why complementary**:
- Ichimoku 是 pipeline 內**從未使用過**的 indicator system
- Cloud (forward-displaced average) 與 Donchian (rolling min/max) / BB (std-dev band)
  是三種 mathematically 不同的 range structure 表示法
- Cloud thickness gate 自然 filter 薄雲段（無 directional consensus，不交易）

**Indicator registry status**:
- Ichimoku **完全不在 registry**，plugin-internal 計算所有 component
  - `tenkan_sen = (9-period high + 9-period low) / 2`
  - `kijun_sen = (26-period high + 26-period low) / 2`
  - `senkou_span_a = (tenkan_sen + kijun_sen) / 2` shifted 26 bars forward
  - `senkou_span_b = (52-period high + 52-period low) / 2` shifted 26 bars forward

**Known risk**:
- Ichimoku 多 component 計算複雜，plugin-internal 工作量比 Donchian 大
- Forward-displaced 計算要小心 lookahead bias — entry 必須只讀 already-displaced-into-now
  的值（即 current 的 senkou_a/b 是 26 bars 前計算 displaced 過來的），不可讀 future-displaced
- 薄雲段 gate 會大量 reject，可能造成 trade 數低於預期（< 5 trade 觸發 §1.2 sample size gate）

---

### 4.3 B3: Keltner mean reversion pair

**Plugins**:
- `keltner_lower_fade_1h` (LONG, regime: `RANGING`)
- `keltner_upper_fade_1h` (SHORT, regime: `RANGING`)

**Mechanism**: Keltner Channel = `ema_20 ± K × atr`（K default 1.5）。
與 BB（std-dev）和 Donchian（rolling extreme）用不同 volatility metric。
ATR-based linear scaling 對 fat-tail noise 比 std-dev 更 robust。

**LONG entry**:
- `close ≤ ema_20 - 1.5 × atr`（lower Keltner）
- `rsi_14 < 35`
- `adx < 22`（1h itself，ranging confirm）
- Cooldown gate

**SHORT entry**: 對稱（close ≥ ema_20 + 1.5×atr, rsi_14 > 65, adx < 22）

**Exit**: `close ≥ ema_20`（Keltner mid）OR `adx > 28`（regime flip safety valve）
／ SHORT 對稱

**Stop**: `entry ± stop_atr_mult × atr_1h`（default 1.5）

**Symbols / TF**: BTC + ETH，1h

**Why complementary**:
- 與既有 BB fade squeeze（BBW pctrank gate）用不同 volatility metric — Keltner ATR linear,
  BB std-dev nonlinear
- 補 Slot B 內 4h 主導的 frequency gap（current Slot B = Donchian 4h + BB squeeze 1h paused
  → 1h 段沒有 active candidate）

**Indicator registry status**:
- `ema_20`, `atr`, `adx`, `rsi_14` 全部在 registry
- Keltner band 作 `ema_20 ± K × atr` 簡單 plugin-internal 計算

**Known risk**:
- 1h 高頻 → fee-drag risk，類似 RSI2 fee economics 觀察點（年估 3-5/週/symbol → BTC+ETH ≈ 300-520/年，超過 Minara 200/年 fee-killer line）
- 在 trending 段 ATR 變大、Keltner 自動拉寬 — 若 ADX gate 不準仍會誤判 ranging
- 與 BB fade squeeze（如果 Phase 5 rescue 後 active）在 1h 同 TF 可能 signal-time overlap，需 backtest 驗 decorrelation

---

## 5. Regime-transition candidates (3 mechanism units, 6 plugins)

### 5.1 T1: Donchian break + retest pair

**Plugins**:
- `donchian_break_retest_up_4h` (LONG, regime: `TRENDING_UP`)
- `donchian_break_retest_down_4h` (SHORT, regime: `TRENDING_DOWN`)

**Mechanism**: 重用既有 Donchian range detection 邏輯（width CV + 兩側 touched）
作 prerequisite。當 range 被 detect 後 price 突破 boundary 並回測該 boundary
確認支撐/阻力翻轉 → 進場。**Range→trend transition catch**，與 Slot B 的
Donchian fade thesis 相反但共用 detection logic。

**LONG entry**:
- 過去 N bars (default 25) 內曾 detect valid range（per existing Donchian gate
  in `donchian_range_fade_4h_range_width_cv_013`）
- `close 突破 prior donchian_high + 0.5 × atr`
- 隨後 N bars 內回測：price 觸及 `prior_donchian_high ± 0.25 × atr`
- Retest bar `close` 收回 `prior_donchian_high` 之上（hold confirm）
- Plugin-internal state 記憶 break 時點等 retest

**SHORT entry**: 對稱（lower break + retest below prior donchian_low）

**Exit**:
- target = `entry + (range_height × 1.0)` measured move (LONG) / 對稱 (SHORT)
- 或 close 跌破 / 漲破 retest level（fail = thesis broken）

**Stop**: `prior_donchian_boundary - 0.5 × atr` (LONG) / 對稱 (SHORT)
— break-back-into-range = thesis 失效

**Symbols / TF**: BTC + ETH，4h

**Why complementary**:
- pipeline 內**沒有 retest-based entry pattern**（既有都是 fresh signal）
- Range→trend transition 補既有 Slot A trend continuation 之前的「trend init」窗口
- 重用 Donchian detection logic → implementation 重用 Slot B B1 active 候選的計算

**Indicator registry status**:
- Donchian 計算 plugin-internal（與既有 `donchian_range_fade_4h_range_width_cv_013` 共用 helper）
- `atr` 在 registry

**Known risk**:
- Retest 在實務常 fail（price break 後直接走不回測）→ trade frequency 預期低
- Plugin internal state（記憶 break 時點等 retest）比 Slot A/B 複雜，testing 工作量大
- 與既有 Slot A 同 candle signal overlap 機率高（兩者都看「trend 起動」）— combined
  backtest 必須監控 reject mix 與 position slot 競爭

---

### 5.2 T2: ATR ratio expansion breakout pair

**Plugins**:
- `atr_expansion_breakout_up_1h` (LONG, regime: `TRENDING_UP`)
- `atr_expansion_breakout_down_1h` (SHORT, regime: `TRENDING_DOWN`)

**Mechanism**: `atr(5) / atr(20) > 1.5` 作為短期波動相對長期暴增的 signal — vol regime
expansion 是 ranging→breakout 轉換的客觀 metric。配合 close 突破 short-window swing
確認方向。與既有 BB squeeze release 用 BBW absolute level 不同，ATR ratio 用相對變化。

**LONG entry**:
- `atr_short / atr_long > vol_expansion_ratio_min`（default 1.5; atr_short=ATR(5), atr_long=ATR(20)）
- `close` 突破 last 12 bars swing high
- HTF gate: `close[4h] > sma_50[4h]`（HTF 不在強烈下行）
- ATR short 須維持 ≥ 3 bars 的 expansion（防 single-bar spike 誤判）
- Cooldown gate

**SHORT entry**: 對稱（突破 swing low + HTF 不在強烈上行）

**Exit**: ATR ratio 收縮回 < 1.0（expansion 結束）OR `close` 跌回 / 漲回 entry breakout level

**Stop**: 進場 swing 反向 - 0.5×atr OR `entry ± stop_atr_mult × atr_1h`（取 tighter）

**Symbols / TF**: BTC + ETH，1h

**Why complementary**:
- 與既有 BB squeeze release（BBW level）+ Phase 1.1 squeeze_release_unconfirmed candidate
  用**不同 squeeze metric** → 可同時 active 不衝突
- pipeline 內 volatility regime change 機制只有 BBW path，加 ATR ratio path 是 mechanism 多元化
- 1h transition window 短 → trade 集中在 vol regime change 時刻

**Indicator registry status**:
- `atr` (length=14) 在 registry — 不直接用，需 plugin-internal 計算 ATR(5) 與 ATR(20)
- swing high/low 識別 plugin-internal（同 B1 pattern）

**Known risk**:
- ATR ratio 在 flash crash 時也會 spike（單 bar 大）→ `atr_short ≥ 3 bars expansion` gate
  是核心 filter
- Vol expansion 後 follow-through 不穩 → false breakout 比例高，stop discipline 必嚴
- HTF gate 選擇（4h sma_50 vs sma_200 vs ADX）需要 sweep verify

---

### 5.3 T3: Trend exhaustion reversal pair

**Plugins**:
- `downtrend_exhaustion_long_4h` (LONG, regime: `ANY`)
- `uptrend_exhaustion_short_4h` (SHORT, regime: `ANY`)

**Mechanism**: Trend 衰竭 + RSI divergence + 結構 confirmation = 經典
mean-reversion-after-trend reversal trade。**注意：entry 方向與被衰竭趨勢相反**
（downtrend 衰竭 → LONG，uptrend 衰竭 → SHORT）。

**LONG entry**:
- Last 8 bars 內至少 6 bars `close < open`（downtrend persistence confirm）
- Current bar `low > prior bar low`（new low 失敗）
- RSI(14) bullish divergence（current bar low vs 8 bars 前 low，price 較低但 rsi 較高）
- `close` 突破 last 3 bars 高點（early reversal confirm）
- Cooldown gate

**SHORT entry**: 對稱（uptrend 衰竭 + bearish divergence + close 跌破 last 3 bars 低點）

**Exit**:
- LONG: rsi 回中性 (45) OR 新趨勢 confirm (`close > sma_20`) OR `bars_in_position >= 12` (time stop)
- SHORT: 對稱

**Stop**:
- LONG: `prior_trend_extreme - 0.5 × atr` (即 downtrend 最低點下方一點) OR `entry - stop_atr_mult × atr_4h`
- SHORT: 對稱

**Symbols / TF**: BTC + ETH，4h

**Why complementary**:
- pipeline 內**完全沒有 reversal cartridge** — 既有都是 trend continuation 或 range fade
- 與 Slot A trending continuation 候選天然反向 — Slot A 在趨勢中段，T3 在趨勢末端
- ANY-regime declaration 對應其 cross-regime thesis（在 trending 末端進場，但 hold 進入 reversal）

**Indicator registry status**:
- `rsi_14`, `atr`, `sma_20` 在 registry
- RSI divergence 計算 plugin-internal（compare current low vs N bars 前 low + 對應 rsi 值）

**Known risk** ⚠️（最 severe 的 candidate）:
- **與 BTC_TREND_FILTER 互動是設計核心衝突**：LONG plugin 在 downtrend 中 entry =
  counter-trend，BTC LONG 會被 `BTC_COUNTER_TREND_MULT = 0.0` block。實務上只能在
  **BTC trend 已 flip uptrend 但 4h 仍顯 downtrend tail** 的窄窗口 fire。
  Combined backtest 中 BTC 端會看到「downtrend exhaustion long」silent block 高比率，
  這是 portfolio 紀律 enforce 不是 cartridge bug — 但要在 Phase 3-pattern 報告 explicit
  列出 silent-block 統計
- Reversal trade false signal 率不低，stop discipline 是核心
- ANY-regime 在 §3.2 需 net_pnl > 0 in 2/3 windows — RANGING window 預期 trade 數極低
  （無 trend 可衰竭）→ 可能在 RANGING 卡 §3.2 net_pnl > 0 gate（trade 數 < 5
  → checklist §1.2 sample-size gate 觸發）
- "Trend 持續性" 定義模糊（連續 lower closes vs ADX vs DI dominance？） — 需要明確
  plugin-internal rule，rule 選擇影響 trade 數量

---

## 6. Cross-Cutting Portfolio Notes

### 6.1 Slot B SHORT silent-block 預期

Slot B SHORT cartridges（B1/B2/B3 SHORT 各支）在 BTC 上行段被
`BTC_TREND_FILTER` silent block — 這是 runtime layer 自動 enforce 的 portfolio-level
紀律，cartridge 本身不需要額外 gate。預期 active 窗口集中在 **BTC 下行 + 個別資產 ranging**
這個少見但高品質的 setup。Trade frequency 估算上要把這個 silent-block 因素列入。

對應到 Phase 3-pattern combined backtest report：每支 Slot B SHORT 必須 explicit
列出 BTC_TREND_FILTER 命中數佔候選總數比率，避免 silent block 被誤讀為「cartridge 邊際 edge 不足」。

### 6.2 Transition cartridges 共通 portfolio 性質

Transition 三條（T1/T2/T3）共通：
- **Trade frequency 較低**：base rate 集中在 regime change moments，每 cartridge 估約
  1-2/週合計 BTC+ETH，但 per-trade R-multiple 預期較高（catch the turn）
- **Combined-backtest signal overlap**：T1 與 Slot A 在 trend 起動段、T3 與 Slot A 在
  trend 末端，可能同 candle 同 emit。**Cross-strategy reject mix（`position_slot_occupied`、
  `strategy_router_blocked`）必須在 combined backtest report per-cartridge 切**，避免單支
  策略被 silent 擠掉
- **Cooldown 設定**：因為 trade 稀疏 + R 較大，cooldown 可放寬（4h cartridge default 2 bars，
  1h cartridge default 4 bars）以免錯失 retest / re-test 機會

### 6.3 Combined-backtest 規劃 pattern (when candidate activated)

當任何本 doc candidate 升級為 active research、且通過個別 §3 / §4 gate 後，combined
backtest 設計需參考 [reorder plan Phase 3](2026-04-25_portfolio_research_reorder_plan.md)
同 pattern：
- ENABLED_STRATEGIES 包含當前 active 的 Slot A + Slot B + 此 candidate
- per-cartridge / portfolio 級 PnL / drawdown
- per-cartridge reject mix attribution（含 BTC_TREND_FILTER silent block）
- 同 symbol 同 candle multi-emit 計數
- portfolio 級 max_dd_pct（看真實 equity curve）

具體 decision gate 在每 candidate spec 階段才訂（不在本 backlog doc 預設），但
combined backtest **必跑** 是 promotion 前置條件。

### 6.4 Fee-drag aggregate 評估

當多 candidate 同時 active 時，aggregate 年交易數可能逼近或超過 Minara fee-killer line
(200 trades/year per single strategy)。已知 1h 候選（B3, T2）和 4h 候選 + transition
都活躍時，年估可能 600-1000 trades / portfolio。需在 combined backtest 報告 fee_drag_ratio
per cartridge per portfolio。

### 6.5 與 既有 RSI2 family 的關係

`rsi2_pullback_1h_sma5_gap_guard`（reorder plan Phase 4 候選）declared
`target_regime: ANY`，與本 doc T3 同 regime declaration。兩者 thesis 不同：
- RSI2 = 長趨勢 + 短回檔（continuation flavor）
- T3 = trend exhaustion divergence（reversal flavor）

實務上 T3 與 RSI2 在強 trending 段的 signal 應**反向**（RSI2 LONG = 下跌的回檔買進，
T3 LONG = 下跌衰竭的反轉買進）。Combined backtest 必須 verify 兩者不在同 candle 同
emit（否則 thesis conflict）。

---

## 7. Suggested Research Priority (when activated)

> 當 Phase 1-5 完成 + §5 trigger 觸發 + Ruei approve 後，本節給予 backlog 內部
> priority 建議。**這只是建議，最終順序由 Ruei 拍板。**

### 7.1 Implementation complexity gradient

**Tier 1（最簡單）**：
- B3 `keltner_lower_fade_1h` / `keltner_upper_fade_1h` — 全 indicator from registry，
  簡單 plugin-internal Keltner band 計算
- A1 `supertrend_flip_4h_*` — registry 已提供 supertrend_direction，加 EMA50 gate

**Tier 2（中等）**：
- A3 `aroon_break_*` — Aroon 自算 + swing 識別自算
- B1 `swing_*_failure_fade_4h` — 純 price-action，無 indicator 計算但 swing 識別自算
- T2 `atr_expansion_breakout_*_1h` — ATR(5)/ATR(20) 自算 + swing 識別

**Tier 3（複雜）**：
- A2 `hull_ma_adx_di_1d_*` — Hull MA + DI+/DI- 兩個都自算
- B2 `ichimoku_kumo_*_fade_4h` — Ichimoku 4 component 自算 + forward-displacement 處理（lookahead bias 風險）
- T1 `donchian_break_retest_*_4h` — plugin-internal state 管理 break/retest sequence
- T3 `*_exhaustion_*_4h` — RSI divergence 計算 + BTC_TREND_FILTER 互動 + ANY-regime §3.2 gate 風險

### 7.2 Portfolio-thesis priority

**最高優先（補既有 portfolio 確定缺口）**：
- A2 SHORT (`hull_ma_adx_di_1d_trending_down`) — 1d SHORT 完全空缺
- A1 SHORT / A3 SHORT — 4h SHORT family 在既有 pipeline 完全空缺，補 bear regime 的
  active carry trade

**第二優先（mechanism diversity 強）**：
- B1 (swing failure fade) — pure structural，與 既有 indicator family 完全 decorrelated
- T1 (donchian break retest) — 重用既有 detection 但 thesis 反向，研究效率高

**第三優先（高風險高 R）**：
- T3 (trend exhaustion reversal) — 與 BTC_TREND_FILTER 衝突大，研究投資報酬率最不確定
- B2 (Ichimoku Kumo) — 複雜計算 + lookahead bias 風險

### 7.3 Suggested first-pass order (建議，非強制)

1. A1 LONG/SHORT pair — Tier 1 + 補 SHORT 空缺
2. B3 LONG/SHORT pair — Tier 1 + 1h Slot B 空缺
3. B1 LONG/SHORT pair — pure structural decorrelation 高
4. A2 LONG/SHORT pair — 1d 補位（特別 SHORT）
5. T2 LONG/SHORT pair — vol regime expansion mechanism
6. A3 LONG/SHORT pair — Aroon novel indicator class
7. T1 LONG/SHORT pair — retest pattern
8. B2 LONG/SHORT pair — Ichimoku，先把上面跑完再評估
9. T3 LONG/SHORT pair — 最後評估（最複雜 + 與 BTC_TREND_FILTER 衝突）

每個 candidate pair 升級為 active research 仍須 **Ruei 明確 approve**，不會自動依此順序開工。

### 7.4 Optimized Wave Schedule After Promotion

The backlog should not be executed in the raw 1-9 order unless the trigger
review says all gaps are equal. Use this routing table after post-promotion
control and Phase 4/5 closeout:

| trigger after A+B | Wave 1 | Wave 2 | Park until infra |
| --- | --- | --- | --- |
| Slot A trend breadth or SHORT exposure gap | A1 `supertrend_flip_4h_*` | A2 `hull_ma_adx_di_1d_*` or A3 `aroon_break_*` | SHORT promotion until `TRENDING_DOWN` validation exists |
| Slot B ranging frequency / detection gap | B3 `keltner_*_fade_1h` | B1 `swing_*_failure_fade_4h` | B2 Ichimoku until lookahead-bias audit is designed |
| Transition-window gap | T2 `atr_expansion_breakout_*_1h` | T1 `donchian_break_retest_*_4h` | T3 until BTC trend-filter silent-block handling is explicit |
| No material gap | no backlog activation | monitor promoted A+B | all recovery backlog remains parked |

Wave 1 acceptance pattern:

1. Write one locked `cartridge_spec_<id>.md` pair from this backlog.
2. Implement only that pair and focused tests.
3. Run candidate review, one 3-cell sweep, and A+B+candidate combined
   attribution.
4. Stop after the Wave 1 report and ask Ruei whether to continue, park, or
   promote to a later review stage.

This preserves the recovery backlog as a controlled expansion valve instead of
turning it into a parallel alpha factory.

---

## 8. Out of Scope

本 backlog doc 明確不涵蓋：

- Volume-derived mechanisms（OBV, VWAP, MFI, accumulation/distribution）— Ruei 未開放
- Cross-asset / pair-trade mechanisms（BTC↔ETH lead-lag, relative strength）— Ruei 未開放
- 新 symbol 擴展（SOL, BNB 等）— Ruei locked BTC/ETH only
- 15m timeframe 候選 — engine 不支援（CLAUDE.md §5 gate）
- 任何要求 mutate `Config` defaults / 改 `STRATEGY_RUNTIME_ENABLED` / 改 `STRATEGY_ROUTER_POLICY`
  / 改 BTC_TREND_FILTER 設定的 candidate
- ADX-only ranging detection（δ refuted）
- 與既有 MACD / EMA cross / RSI / BB squeeze pctrank / Donchian fade / RSI2 mechanism overlap 的 candidate

---

## 9. References

### 9.1 Pipeline / planning docs (must read before activating any candidate)

- [plans/2026-04-25_portfolio_research_reorder_plan.md](2026-04-25_portfolio_research_reorder_plan.md) — current locked pipeline + §5 activation triggers
- [plans/cartridge_promotion_checklist.md](cartridge_promotion_checklist.md) — promotion gates (§1.2 sample, §2.5 regime, §3.2 net_pnl, §3.4 sweep, §4 max_dd, §5 timeframe)
- [plans/ranging_strategy_brainstorm_design.md](ranging_strategy_brainstorm_design.md) — design pattern 參考（既有三 ranging cartridge 的 brainstorm 結構）

### 9.2 Existing cartridge specs (mechanism overlap 對照)

- [plans/cartridge_spec_donchian_range_fade_4h_range_width_cv_013.md](cartridge_spec_donchian_range_fade_4h_range_width_cv_013.md) — Donchian detection 邏輯（T1 重用）
- [plans/cartridge_spec_bb_fade_squeeze_1h.md](cartridge_spec_bb_fade_squeeze_1h.md) — BBW squeeze pattern 對照（T2 differentiation）
- [plans/cartridge_spec_rsi2_pullback_1h.md](cartridge_spec_rsi2_pullback_1h.md) — RSI2 pullback ANY-regime（T3 differentiation）
- [plans/cartridge_spec_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter.md](cartridge_spec_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter.md) — Phase 1.1 squeeze release（T2 differentiation）

### 9.3 Reports providing failure-mode evidence

- [reports/rsi_mean_reversion_research_note.md](../reports/rsi_mean_reversion_research_note.md) — δ failure（ADX-only ranging refuted）
- [reports/donchian_range_fade_4h_freeze_read.md](../reports/donchian_range_fade_4h_freeze_read.md) — Donchian frozen-read 詮釋
- [reports/bb_fade_squeeze_1h_gate_attribution.md](../reports/bb_fade_squeeze_1h_gate_attribution.md) — BB squeeze gate 太嚴歸因

### 9.4 Implementation reference (when candidate activated)

- [trader/strategies/base.py](../trader/strategies/base.py) — StrategyPlugin contract
- [trader/strategies/plugins/macd_signal_trending_up_4h.py](../trader/strategies/plugins/macd_signal_trending_up_4h.py) — multi-TF access pattern
- [trader/strategies/plugins/ema_cross_7_19.py](../trader/strategies/plugins/ema_cross_7_19.py) — `_with_emas` style plugin-internal indicator computation
- [trader/strategies/plugins/donchian_range_fade_4h_range_width_cv_013.py](../trader/strategies/plugins/donchian_range_fade_4h_range_width_cv_013.py) — Donchian detection helper（T1 重用）
- [trader/indicators/registry.py](../trader/indicators/registry.py) — registry indicator scope

---

## 10. Document Status

- **Created**: 2026-04-25
- **Status**: BACKLOG / SCHEDULED RECOVERY / DO-NOT-START
- **Activation gate**: post-promotion control complete + Phase 4/5 closeout or explicit park decision + trigger review memo + Ruei approve
- **Next action**: finish post-promotion control, then close Phase 4/5 before activating any backlog mechanism pair.
- **Owner**: Ruei
- **Author**: 小波（PM-side）
