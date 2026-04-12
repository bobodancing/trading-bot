# Regime Arbiter Design

- **Date**: 2026-04-12
- **Author**: 小波 + Ruei
- **Scope**: trading_bot feat-grid（`trader/regime.py`, 新增 `trader/arbiter/`） + tools/Backtesting（diagnostics 重跑）
- **Status**: Spec only. 無 code。等 R0 診斷結果回填 Open Questions 後，R1 才開始實作
- **Supersedes**: 不取代 `2026-04-11_post_ema_baseline_roadmap.md`，但**接續其 P0.5/P0.6 結論**並開出獨立 R 軌道（R0–R5），避免跟舊 roadmap 的 P1 撞名

---

## Hard Guardrails（這份 spec 從頭到尾的 invariant）

1. **V54 strategy logic FROZEN.** 不改 `trader/strategies/v54_noscale/` 的出場、鎖利、position lifecycle、scaling。所有「保護 V54」的邏輯都寫在 arbiter / router 層。Arbiter 只決定「這個 2B signal 能不能餵給 V54」，不改 V54 收到 signal 後怎麼做
2. **新 range strategy 必須先對標 V54-in-RANGING baseline.** P0.6 dedupe 顯示 V54 在 entry-time RANGING bucket 的 PF 2.17（n=22, +169 USDT）。任何「寫一個新 range 策略」的提案都要先證明 V54-in-RANGING 有明確 capture gap / risk gap / setup gap。沒 gap = 不寫
3. **RegimeEngine 先診斷，後修.** 不為了讓 SQUEEZE coverage 從 0 變非 0 而調 threshold。順序是「肉眼 chart sanity → 確認該段該不該是 SQUEEZE → 才決定改 threshold 或改 window 選擇」。診斷不通過 = 不動引擎參數

---

## Context

P0.5 + P0.6（2026-04-11 ~ 04-12）給出三個關鍵 finding：

1. **V54 在 clean trend 期表現好**：`TRENDING_UP` PF 1.73 / `TRENDING_DOWN` PF 3.70。其中 `TRENDING_DOWN` 的 entry-time TRENDING bucket PF **9.91**（n=10）
2. **V54 在 entry-time RANGING bucket 也賺**：cross-window dedupe PF 2.17（n=22）。**「V54 不能做 range」是錯命題**
3. **V54 真正的 weakness 是 chop-trend 誤標**：MIXED window 的 entry-time TRENDING bucket PF 0.16（n=9），8/9 集中在 2025-04-27 ~ 2025-05-20 BTC 90–105k consolidation 期。RegimeEngine hysteresis 在 March impulse 之後沒及時降回 RANGING，V54 拿著錯誤 TRENDING tag 進場連吃 mean revert

**結論**：問題不在 V54，問題在 RegimeEngine 的 label 太粗 + 沒有 router 層保護。這份 spec 的所有 R 軌道都圍繞「修 label / 加 guard / 保 V54」三件事。

## Framing

- **Arbiter 優先於新策略**：先把 RegimeEngine 修對 + Arbiter contract 定下來，然後才談要不要寫新策略。順序顛倒會讓新策略內部散落 routing 條件，未來重構會痛
- **新策略是 conditional**：R3 只在 R2 deep dive 找到明確 gap 時才啟動。否則 V54 兼任 ranging
- **Transition trap 是 router 層問題**，不是策略內部能解的。Mitigation 寫在 Arbiter contract，不寫在策略裡
- **保險方針**：採 **Neutral Zone (A) + Macro Overlay (C)**，**不採 Position Handover (B)**。B 在實盤前會變成狀態機地雷

---

## R Tracks

**順序硬性**。前一軌沒過不能跳下一軌。

---

### R0 — RegimeEngine Diagnostics

- **Who**: Codex 跑診斷 + 出 report，小波讀，Ruei 決策
- **Goal**: 在動引擎之前先理解現狀。重點是「為什麼 hysteresis 黏」+「SQUEEZE 0 coverage 是 bug 還是 window 問題」
- **Why R0**: 不診斷就修 = 過擬合補丁。引擎是後續所有 routing 的基礎，動之前必須確認問題在哪一層

#### Tasks

1. **Apr-May 2025 hysteresis replay**
   - 取 `2025-03-15 ~ 2025-06-15`（涵蓋 March impulse + Apr-May consolidation）BTC 4H bars
   - 逐 bar 印出 `regime_label`, `confirm_count`, `BBW`, `ATR%`, `ADX`, `transition_event`
   - 輸出 `reports/regime_diagnostic_apr_may_2025.md`，含表格 + Ruei 可眼看的 chart link / png
   - **目標**：找到「regime 應該翻 RANGING 但 hysteresis 卡住沒翻」的具體 bar timestamp + 卡住的指標值

2. **SQUEEZE coverage diagnostic**
   - 取 P0.5 四個 window 共 3988 bars 的 BTC 4H feature dump
   - 對每 bar 計算 `BBW_percentile`（BBW 在 window 內的百分位）+ `ATR_percentile`
   - 找出所有 `BBW_percentile < 20` 的 bar
   - 輸出 `reports/squeeze_coverage_audit.md`：
     - 表 A：低 BBW bars 的時間分布（哪些日期是「肉眼可能 squeeze」候選）
     - 表 B：當前引擎 SQUEEZE 判定條件 + 為什麼這些低 BBW bar 沒被 tag
   - **不要**根據結果直接改 threshold。輸出後停手等 Ruei review

3. **Confidence score POC（spec only，code 留 R1）**
   - 列出可能的 confidence input：ADX absolute, ADX slope, BBW percentile, ATR%, regime persistence (已穩定幾個 bar)
   - **只**寫成 markdown spec：「如果做 confidence 我會這樣做」
   - 不在 R0 改 `regime.py`

#### Acceptance

- [ ] `reports/regime_diagnostic_apr_may_2025.md` 完成，找到至少 1 個明確的 hysteresis stuck case 並指出哪個指標是兇手
- [ ] `reports/squeeze_coverage_audit.md` 完成，回答「3988 bars 裡有沒有肉眼合理 squeeze」這個 yes/no
- [ ] Confidence score POC markdown 完成，列出 candidate inputs + 規範化策略
- [ ] **不動 `trader/regime.py`**

#### Do NOT

- 不要為了讓 SQUEEZE 出現就調 BBW threshold
- 不要為了通過 hysteresis case 就縮短 confirm_count
- 不要在 R0 寫任何 production code
- 不要把 confidence score 直接 wire 進 RegimeEngine

#### Deliverable

- `reports/regime_diagnostic_apr_may_2025.md`
- `reports/squeeze_coverage_audit.md`
- `plans/2026-04-12_regime_arbiter_design.md` Open Questions 補上 R0 結論

---

### R1 — Arbiter Spec & Contract

- **Who**: 小波 draft，Ruei review，Codex 後續按 spec 實作（R1 本身不寫 code，只定 contract）
- **Goal**: 把 Regime Arbiter 的 state machine、strategy contract、transition policy 全部寫成可被實作的 spec。R2 之後的所有 code 都依這份 contract
- **Why R1 在 R2 之前**: contract 會反向 constraint 策略 API。先定 contract 才知道策略要實作哪些介面

#### Tasks

1. **State machine 定義**
   - State set: `TRENDING_UP`, `TRENDING_DOWN`, `RANGING`, `NEUTRAL`, `SQUEEZE`, `UNKNOWN`
   - Transition matrix：哪些 state 之間允許直接跳，哪些必須經過 `NEUTRAL`
   - 每個 state 的 entry condition / exit condition（基於 RegimeEngine + confidence）
   - State persistence: 至少待幾個 bar 才允許離開（防 thrashing）

2. **Strategy contract**
   ```
   class StrategyContract:
       def can_enter(regime, confidence) -> bool
       def required_regimes() -> set[str]
       def min_confidence_to_enter() -> float
       def behavior_on_regime_change(old, new) -> "exit_self_managed" | "freeze_new_entries"
   ```
   - 所有現有 + 未來策略都要實作這個 contract
   - V54 的實作：`required_regimes = {TRENDING_UP, TRENDING_DOWN, RANGING}`，`min_confidence = TBD R0 結論回填`，`behavior_on_change = exit_self_managed`（既有倉位用 V54 自己的 stop/lock 邏輯管到死，**不被新 regime 接管**）
   - **RANGING 的角色**：留給 V54 是作為 **baseline fallback**，不是「V54 永遠主導 RANGING」。如果 R2 = SKIP 或 R3 新策略沒贏 baseline，V54 就是 RANGING 的 default executor；如果 R3 = GO 且新策略證明 PF 贏 baseline，**arbiter 必須實作 strategy priority 機制決定 RANGING entry 餵給哪一個**，禁止兩個策略同時搶 RANGING entry。priority 規則寫進 R3 的 deliverable
   - Strategy priority enum: `PRIMARY` / `FALLBACK` / `OFF`。同一個 regime 同一時間只允許一個 `PRIMARY`

3. **Transition Policy: Neutral Zone (A)**
   - Confidence < `NEUTRAL_THRESHOLD` → arbiter 進入 `NEUTRAL` state
   - `NEUTRAL` 期間：**所有策略 freeze new entries，既有倉位用進場時的策略邏輯管理到 exit**
   - 退出 `NEUTRAL` 條件：confidence ≥ `NEUTRAL_EXIT_THRESHOLD` 且新 regime 已穩定 N bars
   - `NEUTRAL_THRESHOLD` / `NEUTRAL_EXIT_THRESHOLD` / `N` 全部寫成 `Config` constants，**不 hardcode**

4. **Transition Policy: Macro Overlay (C)**
   - 加一層 BTC weekly trend gate（1W EMA 50/200 alignment 或 1W ADX）
   - Macro state: `MACRO_BULL`, `MACRO_BEAR`, `MACRO_STALLED`
   - Override 規則：
     - `MACRO_STALLED` → 所有 trend strategy freeze new entries，size 收緊 50%
     - `MACRO_BULL → MACRO_BEAR` flip → 24h cooldown 全策略 freeze
     - 對稱
   - **驗證義務**：spec 必須包含 backtest plan 證明 macro overlay 不是 lookahead bias / 事後諸葛

5. **Position handling rules**
   - 倉位由「進場時的策略 + 進場時的 regime」標記
   - Regime 翻轉後：既有倉位用**進場時策略**的 exit logic 處理（**不**被接管）
   - 新進場倉位用**當前 regime + 當前 arbiter decision**
   - 明確禁止 Handover (B)

6. **Config exposure（spec only — 不在 R1 改 config parity）**
   - 列出 R1 code implementation 階段需要納入 `bot_config.json` + `trader/config.py` 的 arbiter 參數清單
   - **這份 spec 不修改 P0 config parity guard。** R1 進入 implementation 時才把以下 keys 加進 `CRITICAL_KEYS` 並補對應的 JSON 預設值，由 implementation commit 一起處理，避免 spec commit 跟 config commit 混在一起
   - 候選 critical keys（R1 implementation 時 finalize）：
     ```
     ARBITER_NEUTRAL_THRESHOLD
     ARBITER_NEUTRAL_EXIT_THRESHOLD
     ARBITER_NEUTRAL_MIN_BARS
     MACRO_OVERLAY_ENABLED
     MACRO_STALLED_SIZE_MULT
     ```

#### Acceptance

- [ ] State machine diagram（mermaid 或 ascii）寫進 spec
- [ ] StrategyContract Python interface 寫進 spec（pseudo-code，不是真 code）
- [ ] V54 對 contract 的 implementation 樣本寫進 spec
- [ ] Neutral Zone + Macro Overlay 兩個 policy 各自的 pseudo-code + edge case 列表
- [ ] Macro overlay 的反 lookahead 驗證計畫寫進 spec
- [ ] CRITICAL_KEYS 擴充清單列出
- [ ] **不動 `trader/regime.py`，不新增 `trader/arbiter/` 目錄**

#### Do NOT

- 不要在 R1 寫實作 code
- 不要在 contract 裡留 Position Handover 介面（B 永久 out of scope）
- 不要把 V54 的 `required_regimes` 縮成 `{TRENDING}`（會殺掉 V54-in-RANGING 那 22 筆 PF 2.17）
- 不要 hardcode threshold

#### Deliverable

- `plans/2026-04-12_regime_arbiter_design.md` 的 R1 章節從 spec only 變成 full contract（這份檔案會被多次更新）

---

### R2 — V54-in-RANGING Deep Dive

- **Who**: 小波 + Ruei 一起讀資料，Codex 跑 sub-analysis
- **Goal**: 把 P0.6 dedupe 出的 22 筆 V54-in-RANGING entries 攤開看，回答「V54 在 range 裡 capture 到的是哪一類 setup、漏掉的是哪一類」
- **Why R2 在 R3 之前**: R3（寫新 range strategy）的存在前提是 R2 找到 gap。沒 gap 直接跳 R4

#### Tasks

1. **22 筆 trade 細部分析**
   - 從 `tools/Backtesting/results/p06_regime_diagnostics_20260412/` 取四個 window 的 trades.csv
   - filter `entry_regime == "RANGING"`
   - 攤開欄位：entry/exit price, MFE, MAE, MaxR, realized R, capture ratio, hold hours, exit reason, BBW at entry, ATR% at entry, ADX at entry
   - 分桶：
     - 賺錢且 capture ratio > 0.5 的 → V54 在做的事
     - 賺錢但 capture < 0.5 的 → V54 抓到但鎖太早
     - 賠錢的 → V54 進對 regime 但 setup 本身錯
   - 輸出 `reports/v54_in_ranging_22trades.md`

2. **Gap 假設驗證**
   - 對每一筆 V54 沒進場的 ranging 候選 setup（從 signal_audit `rejects` 撈），看：
     - 為什麼 V54 沒進（tier filter? market filter? 沒 2B?）
     - 如果有別的策略（mean reversion, BB band fade, range breakout）會不會進
   - 列出 V54 的「結構性盲區」候選 list

3. **Gap criteria（決定 R3 走不走）**
   - **R3 啟動條件**（必須全部成立）：
     - V54-in-RANGING 至少 30% 的賺錢 trade capture < 0.4（代表鎖太早）**或**
     - V54 在 ranging 期漏掉 ≥ 20 個非 2B 的 A-tier 候選 setup（代表結構盲區）**或**
     - V54-in-RANGING 的 max single-trade DD 超過 2R（代表 risk shape 不對）
   - 都不成立 → R3 取消，直接跳 R4

#### Acceptance

- [ ] `reports/v54_in_ranging_22trades.md` 完成
- [ ] Gap criteria 三條都被明確 evaluated（pass/fail）
- [ ] R3 走或不走的決定寫進 `plans/2026-04-12_regime_arbiter_design.md` 的 Decision Log

#### Do NOT

- 不要因為「直覺新 strategy 應該存在」就跳過 gap criteria
- 不要拿 22 筆裡少數異常 case 當代表（要求 ≥ 30% / ≥ 20 個 / 超過 2R 是門檻，不是 cherry-pick）
- 不要在 R2 寫任何新策略 code

#### Deliverable

- `reports/v54_in_ranging_22trades.md`
- Decision Log entry: `R3 = GO` 或 `R3 = SKIP`

---

### R3 — Range Strategy Implementation（CONDITIONAL）

- **啟動條件**: R2 結論 = `R3 = GO`
- **如果 R2 = SKIP**: 整個 R3 章節作廢，直接 R4
- **Who**: Codex 實作，小波 review，Ruei 決策上線
- **Goal**: 寫一個或多個 range strategy 候選，**對標 V54-in-RANGING baseline**，必須在 R2 找出的 gap 上有顯著改善

#### Tasks (high-level，R2 完成後再展開)

1. 選 strategy 類型：mean reversion / BB fade / range breakout / 其他
2. 實作為 `trader/strategies/<name>/`，遵守 R1 的 StrategyContract
3. Backtest vs V54-in-RANGING：必須在同一個 22-trade 樣本 + 額外 forward window 上 PF / Sharpe 都贏
4. 整合進 arbiter routing：`required_regimes = {RANGING}`

#### Acceptance（暫定，R2 完成後 finalize）

- [ ] 新策略在 P0.5 四個 window 的 RANGING entries 上跑出 PF ≥ 2.17 × 1.3 = **2.82**（V54 baseline + 30% margin）
- [ ] **小樣本 caveat — 三條都要過，不能只在 22 筆 subset 上贏**：
  - (a) **Forward sample 不惡化**：在 R4 的 4 個 transition window 上的 RANGING entries 也要贏 V54，PF margin 至少 +15%（不要求 30%，因為 transition 樣本更小）
  - (b) **MaxDD 不顯著惡化**：新策略 max single-trade R loss ≤ V54-in-RANGING 同窗結果；新策略 cumulative MaxDD% 不超過 V54-in-RANGING 同窗 1.2 倍
  - (c) **R 分布不偏 fat tail**：新策略 realized R 的中位數 ≥ V54-in-RANGING 中位數 × 0.8，且 top-2 winner 貢獻 PnL 占比 < 60%（防 PF 由少數異常 trade 撐起）
- [ ] 不破壞 V54-in-RANGING 既有路徑：V54 仍可被 arbiter 選為 RANGING fallback executor（按 strategy priority 規則）

#### Do NOT

- 不要 lower bar 來救新策略（PF margin 是硬條件）
- 不要把新策略包成「替代 V54」，要包成「補充 V54」

---

### R4 — Transition Stress Test

- **Who**: Codex 跑 backtest，小波讀，Ruei 決策
- **Goal**: 手選 4 個歷史 transition 段（V-reversal × 2, fade × 2）跑 V54 + arbiter，驗證 Neutral Zone 與 Macro Overlay 在實際 transition 期的行為

#### Tasks

1. **手選 4 個 transition window**（Ruei 回填具體日期到 Open Questions）：
   - **熊→牛 V-reversal**: 候選 `2023-10-01 ~ 2023-11-30`（FTX 後反彈）
   - **牛→熊 V-reversal**: 候選 `2024-03-10 ~ 2024-05-30`（73k → 56k）
   - **趨勢→橫盤 fade**: `2025-04-01 ~ 2025-06-15`（Apr-May consolidation，已知 V54 連敗段）
   - **橫盤→趨勢 breakout**: 候選 `2024-09-01 ~ 2024-11-15`（盤整破 73k）

2. **三個對照組**
   - A: V54 alone（baseline）
   - B: V54 + Neutral Zone only
   - C: V54 + Neutral Zone + Macro Overlay

3. **Metrics**
   - Total return / MaxDD / PF
   - **Transition zone metrics**：regime flip 前 5 bars 到後 10 bars 的 P&L 變化
   - 是否避開了 **P0.6 MIXED entry-time TRENDING loss cluster**——定義：`trades.csv` 內 `entry_regime == "TRENDING"` 且 entry_time 落在 fade window 內的虧損序列。實際筆數以 R0 重對齊（hysteresis case 邊界釐清）後為準，**不在 spec 階段 hardcode 連敗筆數**

#### Acceptance

- [ ] 4 個 window 在 A/B/C 三個對照組都跑完
- [ ] B 組在 fade window 的 P&L 顯著優於 A 組：明確標的是 **P0.6 MIXED entry-time TRENDING loss cluster**（定義同 Tasks 第 3 條）。改善幅度的具體門檻（例如「避開 ≥ 50%」）等 R0 重對齊後在 Decision Log 補上
- [ ] C 組在 V-reversal window 不出現 catastrophic drawdown
- [ ] 結果寫進 `reports/transition_stress_test.md`

#### Do NOT

- 不要把 transition window 選成 cherry-pick 對 B/C 有利的段
- 不要忽略 B/C 帶來的機會成本（dead zone 期沒交易也是成本）

---

### R5 — rwUbuntu Testnet

- **啟動條件**: R4 通過
- **Who**: Ruei deploy
- **Goal**: 把 V54 + arbiter（Neutral Zone + Macro Overlay）丟上 rwUbuntu testnet，跑 ≥ 4 週收 forward sample
- **out of scope** for this spec：testnet validation criteria 用既有 `memory/testnet_validation.md` 規範

---

## Open Questions

**R0 完成後填（2026-04-12 已填）**

- [x] **Hysteresis 兇手 = ADX ≥ 25 在 chop 期仍成立。** `adx_trending` 占 Apr-May 361 bars 中的 215 bars（59.6%）。次要因素：`_detect_regime` 回 None 保留前狀態（81 bars = 22.4%）。ATR expansion 不是兇手（4 bars = 1.1%）。RANGING confirm 被 None 中斷累不到 3（5 個 stuck case，max_confirm ≤ 2）。見 `reports/regime_diagnostic_apr_may_2025.md`
- [x] **SQUEEZE 0 coverage = engine guard (`bbw_ratio < 0.15`) 太嚴。** 784 個低 BBW 候選裡 72.1% 被 bbw_ratio 擋，27.9% 被 ADX 提升為 TRENDING。Report answer = **yes**（likely real squeeze candidates missed）。Chart Review Queue 10 個 timestamp range，**Ruei 正在肉眼確認 top 3**。見 `reports/squeeze_coverage_audit.md`
- [x] **Confidence score input 列表：** 5 個候選（ADX absolute / ADX slope / BBW percentile / ATR% / regime persistence），4 個 combination strategy（weighted sum / min gate / vote / hybrid），6 個 R1 open questions。見 `reports/confidence_score_poc.md`

**R0 後決策（2026-04-12 Ruei 決定）**

- [x] **D2: Confidence score = Scalar。** 一個 `confidence ∈ [0,1]` 代表當前 regime label 可信度。理由：V54 是目前唯一策略，scalar 夠用；複雜度殺項目；scalar 可日後升級 vector，反過來不行
- [x] **D3: Hysteresis stuck 修正方向 = C（Confidence gate，不改 RegimeEngine）。** 不動 `trader/regime.py`，由 arbiter 層看 ADX slope + persistence → confidence < threshold → NEUTRAL → freeze entries。理由：符合 Hard Guardrail #3（先診斷後修）+ V54 frozen 精神；A（None 不重置 counter）有 regression 風險；B（ADX slope guard）加新參數需 tuning
- [ ] **D1: SQUEEZE chart review = pending。** Ruei 正在看 top 3 候選段（`2023-10-14~15` / `2025-06-28~29` / `2025-02-16~17`），結果回填後決定 R1 SQUEEZE state 是 active 還是 placeholder

**R1 完成後填**

- [ ] `NEUTRAL_THRESHOLD` 初始值
- [ ] `NEUTRAL_MIN_BARS` 初始值
- [ ] Macro overlay 用 1W EMA alignment 還是 1W ADX
- [ ] V54 的 `min_confidence_to_enter`

**R2 完成後填**

- [ ] R3 = GO 或 SKIP
- [ ] 如果 GO，新策略的 type 與 thesis 一句話

**R4 完成後填**

- [ ] 4 個 transition window 的具體日期（Ruei 提供或同意候選）
- [ ] Acceptance 的 50% 改善門檻是否合理

---

## Out of Scope（明確列）

- **改 V54 strategy logic**: 任何對 `trader/strategies/v54_noscale/` 的修改都不在這份 spec 內
- **Position Handover (B)**: 永久 out of scope
- **新 trend strategy**: 這份 spec 只談 range / arbiter / regime；trend 路線由舊 roadmap 處理
- **Live trading deployment**: 只做到 testnet（R5），mainnet 不在這份 spec
- **Multi-asset portfolio rebalancing**: 不碰
- **GUI / Dashboard**: 不碰

---

## Decision Log

- `2026-04-12`: spec draft v0 by 小波
- `2026-04-12`: Ruei 接受三條 hard guardrail（V54 freeze / range strategy thesis / regime diagnose-first）
- `2026-04-12`: 採用 A + C transition policy，B 永久 out of scope
- `2026-04-12`: R 軌道命名敲定（R0–R5），不跟舊 roadmap P1 撞名
- `2026-04-12`: spec v1 patch by 小波（per Ruei review）：
  - V54 `required_regimes` 補 baseline fallback 語意 + strategy priority 機制（防 R3 GO 後雙策略搶 RANGING entry）
  - R3 acceptance 補小樣本 caveat 三條（forward sample / MaxDD / R 分布）
  - R4 「P0.6 8 連敗」改寫成「P0.6 MIXED entry-time TRENDING loss cluster」精確定義；連敗筆數延後到 R0 重對齊後再 hardcode
  - R1 task 6 wording 釐清：spec 階段不動 P0 config parity，CRITICAL_KEYS 擴充延到 R1 implementation commit
- `2026-04-12`: R0 complete（codex 產出 3 reports + 2 CSV artifacts + 1 diagnostic helper，小波 review pass）
- `2026-04-12`: Ruei 決策三項：
  - D2 Confidence score = **Scalar**（`confidence ∈ [0,1]` for current regime label）
  - D3 Hysteresis fix = **C（Confidence gate in arbiter layer, do not modify RegimeEngine）**
  - D1 SQUEEZE chart review = **pending**（Ruei 正看 top 3 候選段）
- `2026-04-12`: spec v2 patch by 小波：R0 Open Questions 填入 findings + D2/D3 決策

---

## Naming Convention

- **P 軌道** = 舊 `2026-04-11_post_ema_baseline_roadmap.md` 的 priority tracks（P0, P0.5, P1...）
- **R 軌道** = 這份 spec 的 regime arbiter tracks（R0, R1...）
- 兩條軌道**並行**，不互相阻塞，但 R 軌道的 R5 testnet 必須等 P 軌道的 testnet validation 框架定稿

---

*活文件。R0 跑完之後會大改。*
