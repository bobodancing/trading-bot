# Portfolio Research Reorder Plan

Date: 2026-04-25
Status: historical / superseded by A+B runtime promotion. Do not use this as
current runtime authority.
Owner: Ruei
Branch: originally `codex/strategy-runtime-reset`; carried forward on
`codex/post-promotion-control-20260430`
Author: 小波 (PM 角色 review，codex 限額期間整理)

## 0. Post-Promotion Hygiene Note

This plan was written before the A+B promotion decision. The Phase 1-3 path
below has since completed:

- Ruei approved A+B runtime promotion on 2026-04-29.
- Catalog enablement landed in `5dee878`.
- Config runtime defaults landed in `1933e65`.
- Post-promotion control passed in `1a9725a`.
- Scanner production universe work remains plan-only / observe-only in
  `d85012f`.

Treat this document as the historical research-order rationale that led into
the A+B promotion packet. For current runtime truth, trust code first:
`trader/config.py`, `trader/strategies/plugins/_catalog.py`, and
`reports/portfolio_ab_post_promotion_control.md`.

This document does not authorize any new runtime promotion, scanner
integration, production/testnet state change, or Phase 4/5 activation.

## 1. Why Reorder

CLAUDE.md "Current Next Work" 的順序是 codex 在 per-lane research 紀律下排的：
MACD 結構研究持續推進、Donchian frozen-read、然後 `bb_fade_squeeze_1h` rescue、再
`rsi2_pullback_1h` 二輪 churn。這個順序適合「把每條 ranging detection 機制都跑一遍」
的研究邏輯。

但 Ruei 在 2026-04-25 重新明確了 **portfolio 命題**：

> 至少找到兩種互補策略：
> - Slot A: TRENDING 表現優異，並能壓低 RANGING 時虧損
> - Slot B: RANGING 表現不錯，突然轉 TRENDING 趨勢也能及時止損
>
> 理想是 2-3 條策略一起運行。

對應到目前 cartridge：

| Slot | 唯一可用候選 | 主要缺項 |
| --- | --- | --- |
| Slot A | `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter` | §3.4 sweep 未跑、bear-defense 比較未做完、被 `squeeze_release_unconfirmed` 阻擋 |
| Slot B | `donchian_range_fade_4h_range_width_cv_013` | freeze 前未跑 8-window supplemental matrix、第二維 robustness sweep 未做、per-symbol cut 缺、樣本只 15 trades |

`bb_fade_squeeze_1h` 與 `rsi2_pullback_1h` 對 portfolio 命題邊際效益偏低：

- `bb_fade_squeeze_1h` 也是 RANGING 候選（和 Donchian 卡同一個 slot），但 ranging edge 更弱
  （22476 bars 中只 1 bar 過 gate，需要 squeeze definition 重新定義）
- `rsi2_pullback_1h_sma5_gap_guard` declared `target_regime: ANY` 但實質 trend-leaning
  （RANGING 視窗只 1 trade），不填補 Slot A 也不填補 Slot B

## 2. Locked Decisions (Ruei 2026-04-25)

1. **解凍 Donchian** 跑 supplemental matrix + robustness sweep — APPROVED
   （sweep 維度於 review 階段下調為一維，理由見 Phase 2.2「為什麼放棄原本的二維 9-cell sweep」）
2. **Combined backtest risk 參數** 維持 `RISK_PER_TRADE = 0.017`，接受兩支同時 active 時
   portfolio 上限上拉至 `0.034` 的設計選擇 — APPROVED
3. **暫停 BB Fade Squeeze rescue**，等 Slot A、Slot B 都 promotion-shape 後再決定值不值得補位 — APPROVED

## 3. New Phase Order

### Phase 1 — 解 Slot A 卡點（最高槓桿）

#### 1.0 確認 plugin 實作存在（pre-flight）

`squeeze_release_unconfirmed_late_entry_filter` 目前**只有 spec，plugin 檔尚未實作**
(2026-04-25 確認 `trader/strategies/plugins/` 內無對應 `.py`)。

執行 1.1 之前需要：
- 依 spec 在 `trader/strategies/plugins/macd_signal_trending_up_4h_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter.py`
  實作 plugin（沿用 `transition_aware_tightened` 同層 cartridge 為 base，僅替換 entry 側
  side-branch gate 機制）
- 在 `trader/tests/` 補對應 focused tests（依 promotion checklist §2 invariant gates）
- 在 `trader/strategies/plugins/_catalog.py` 加 `enabled: False` entry
- 跑 `python -c "from trader.config import Config; Config.validate()"` 與
  `python -m pytest trader/tests extensions/Backtesting/tests -q` 確認沒打壞既有 path

只有以上完成後才能進到 1.1。

#### 1.1 跑 `squeeze_release_unconfirmed_late_entry_filter` pinned cell candidate review

- spec: [plans/cartridge_spec_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter.md](cartridge_spec_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter.md)
- runner: `python -m extensions.Backtesting.scripts.run_candidate_review --candidate macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter`
- 守 spec 內建的 No-Sweep Clause：先 pinned cell，**不要** sweep
- 寫報告：`reports/macd_signal_btc_4h_trending_up_squeeze_release_unconfirmed_first_pass.md`
- 對照 spec 的 Pre-Committed Decision Gates：
  - `sideways_transition` net_pnl ≥ -50（必過）
  - `bull_strong_up_1` ≥ +100（必過）
  - `classic_rollercoaster_2021_2022` ≥ +1700（必過）
  - 預設 `TRENDING_UP` ≥ +1484.5085（必過）

**同時也要寫**：`reports/macd_signal_btc_4h_trending_up_side_branch_mechanism_compare.md`，按
squeeze spec 規定的 evaluation order 做 4 層比較：

| 層 | 對照候選 | 角色 | 該層新工作量 |
| --- | --- | --- | --- |
| 1 | `chop_trend_tightened` | localized-state 參考 | 既有資料，引用即可 |
| 2 | `transition_aware_tightened` | divergence-based 參考 | 既有資料，引用即可 |
| 3 | `late_entry_filter` (raw) | 防守上限 ceiling | 既有資料，引用即可 |
| 4 | `partial67` working baseline | 改善起點 | 既有資料，引用即可 |

新工作 = 把 `squeeze_release_unconfirmed` 的 candidate review 數字併入這四層既有資料表，**不重跑** 1-4 任何一個既有候選。

#### 1.2 對勝出機制跑 §3.4 parameter sweep

- 若 squeeze_release_unconfirmed 通過 Decision Gates 且 head-to-head 勝出 →
  sweep 它的 `squeeze_trough_pctrank_max` 在 `10.0 / 15.0 / 20.0`
- 若 transition_aware_tightened 勝出 → sweep `transition_extension_atr_trigger`
  在 `2.5 / 3.0 / 3.5`
- 寫 sweep 報告 status `RESEARCH_SWEEP_ONLY`
- sweep 通過後 Slot A 才符合 promotion checklist §3.4

#### 1.3 補 Slot A 的 8-window supplemental matrix（**conditional**）

執行條件：**只在勝出機制尚未有完整 8 視窗資料時才跑**。

- 若勝出 = `transition_aware_tightened`：8-window 資料已存於
  [reports/macd_signal_btc_4h_trending_up_transition_aware_tightening.md](../reports/macd_signal_btc_4h_trending_up_transition_aware_tightening.md)
  Supplemental Matrix 段落，**Phase 1.3 為零工作量，引用即可**
- 若勝出 = `squeeze_release_unconfirmed`：spec 內建 Pre-Committed Decision Gates 只覆蓋 4 視窗
  (`sideways_transition` / `bull_strong_up_1` / `classic_rollercoaster_2021_2022` /
  default `TRENDING_UP`)，需補跑剩餘 4 視窗
  (`bear_persistent_down` / `range_low_vol` / `bull_recovery_2026` /
  `ftx_style_crash` / `recovery_2023_2024`)，沿用 [reports/macd_signal_btc_4h_trending_up_baseline.md](../reports/macd_signal_btc_4h_trending_up_baseline.md)
  Supplemental Matrix 段落定義的固定 8 視窗
- 確認沒有打壞 `classic_rollercoaster` 與 `bear_persistent_down`

### Phase 2 — 補 Slot B 統計證據（Donchian 解凍）

#### 2.0 Freeze 詮釋

[reports/donchian_range_fade_4h_freeze_read.md](../reports/donchian_range_fade_4h_freeze_read.md)
原本寫「不再做 Donchian micro-pass」，那項禁令仍然有效——指的是不再做
`mid_drift_guard` / `touch_imbalance_guard` 那類**結構性 child cartridge**。

Phase 2 的 supplemental matrix 與 robustness sweep **不屬於** 結構性 child，而是把現有 frozen 候選
從「frozen-skip」升級為「portfolio-required」的二次驗證。兩者性質不同，不互相否定。

#### 2.1 對 `donchian_range_fade_4h_range_width_cv_013` 跑 8-window supplemental matrix

- 沿用 Phase 1.3 同一組 8 視窗
- runner / report pattern 仿 MACD 家族
- **per-symbol slice 強制**：BTC/USDT 與 ETH/USDT 必須各自獨立列出 trades / net_pnl /
  max_dd_pct，不能只給聯合數字。原因：候選 review 那 15 trades / 2 RANGING 的 symbol 分布
  尚未公開，若 2 RANGING 全部來自 ETH 則 BTC 上 Slot B 等於零證據，會直接影響 Phase 3
  combined backtest 的 BTC 端結論
- 寫報告：`reports/donchian_range_fade_4h_range_width_cv_013_supplemental_matrix.md`

#### 2.2 一維 robustness sweep：`touch_atr_band`

- cells（3 cell）：`touch_atr_band ∈ {0.20, 0.25, 0.30}`
- 其他 param 全部凍結在 frozen 候選的 locked 值
- runner: `python -m extensions.Backtesting.scripts.run_parameter_sweep`
- status `RESEARCH_SWEEP_ONLY`
- **角色澄清**：這不是「補 §3.4」，§3.4 已由既有 `range_width_cv_max` 3-cell sweep 通過。
  此 sweep 是 portfolio 命題下的 robustness 加碼，目的是確認 `0.13 / 0.25 / 1` 那組 locked
  value 不是 knife-edge

**為什麼放棄原本的二維 9-cell sweep**：Donchian 候選 review 全部 15 trades / RANGING 僅 2 trades，
攤平到 9 cell 之後 RANGING 平均每 cell 0.22 trade，noise 會壓過 signal，過擬合風險高於資訊
取得；統計上不划算。

#### 2.3 更新 [reports/donchian_range_fade_4h_freeze_read.md](../reports/donchian_range_fade_4h_freeze_read.md)

- 新增 "2026-04-25 Portfolio Re-Validation" 段落
- 引用 2.1 / 2.2 結果
- 維持 verdict 為 `KEEP_RESEARCH_ONLY` 或重新分類
- 明確聲明：原 freeze 對「結構性 child」禁令仍生效，本次只升級已有 frozen 候選的驗證層

### Phase 3 — Portfolio 級驗證（**目前完全缺，必須加**）

#### 3.1 Combined A + B backtest

Risk 參數依 Locked Decision 2：`RISK_PER_TRADE = 0.017`。`MAX_TOTAL_RISK` 沿用
`trader/config.py` 的 Config class default（2026-04-29 為 `0.0642`），不在 combined
backtest 內下修成 `0.034`。

**RISK_PER_TRADE / MAX_TOTAL_RISK 互動需驗證**：`RISK_PER_TRADE` 是 per-trade 上限，
`MAX_TOTAL_RISK` 是同時持倉累加上限。Phase 3.2 reject mix 仍需獨立列
`central_risk_blocked` 計數做歸因，但讀法是檢查 Config default 是否實際擠掉 Slot B，
不是強制模擬兩支策略名目風險相加的 `0.034` cap。

config_overrides（依當下 winning Slot A 機制決定 plugin id）：

```python
{
    "STRATEGY_RUNTIME_ENABLED": True,
    "ENABLED_STRATEGIES": [
        "<winning_slot_a_plugin_id>",          # Phase 1 結束後決定
        "donchian_range_fade_4h_range_width_cv_013",
    ],
    "SYMBOLS": ["BTC/USDT", "ETH/USDT"],
    "RISK_PER_TRADE": 0.017,
    # MAX_TOTAL_RISK intentionally omitted; use Config default 0.0642.
}
```

注意：Slot A 是 BTC-only，Slot B 是 BTC + ETH，所以 `SYMBOLS` 取聯集。

#### 3.2 Combined backtest report

寫 `reports/portfolio_a_b_combined_first_pass.md`，至少包含：

- 三個 DEFAULT_WINDOWS 的 per-cartridge 與 portfolio 級 PnL / drawdown
- 8-window supplemental 同樣切到 per-cartridge / portfolio 級
- Reject mix attribution（**per-cartridge 切**，不要混算）：
  - `position_slot_occupied`（兩支對同 symbol 同時排隊？）
  - `strategy_router_blocked`（arbiter 對哪一支 reject 比較多？）
  - `cooldown`
  - `central_risk_blocked`（驗 §3.1 的 `MAX_TOTAL_RISK` 互動；reject reason 字串由
    [trader/strategy_runtime.py](../trader/strategy_runtime.py) 與 central RiskPlan 提供）
  - BTC_TREND_FILTER 互動現況註記（見下；2026-04-29 review 確認 StrategyRuntime entry path
    目前沒有使用 `BTC_TREND_FILTER_ENABLED` / `BTC_COUNTER_TREND_MULT` 做 reject 或 size=0
    suppression）
- 同 symbol 同 candle 兩支同時 emit intent 的計數（central RiskPlan 如何處理）
- portfolio 級 max_dd_pct（不是兩支各自最大值的較大者，要看真實 equity curve）

**BTC_TREND_FILTER 現況註記**：CLAUDE.md runtime baseline 載明
`BTC_TREND_FILTER_ENABLED = True` 與 `BTC_COUNTER_TREND_MULT = 0.0`，但 2026-04-29
code review 確認 StrategyRuntime entry path 目前只走 regime arbiter/router 與 central
RiskPlan，沒有把 BTC trend filter 接成顯式 reject 或 sizing multiplier。Phase 3.2 report
只需明確註明「current StrategyRuntime does not enforce BTC_TREND_FILTER on plugin
entries」，不得把缺席的 filter 誤讀成 Slot B 壓制。

#### 3.3 Decision gate

如果 Phase 3 暴露下列任一狀況，promotion 要回頭重看：

- portfolio max_dd_pct > 8% （單 cartridge 上限是 4.41% × 2 + 緩衝）
- arbiter `strategy_router_blocked` 對某支 reject 率 > 50%（fail_closed 把好訊號擋掉）
- 同 symbol 同 candle 兩支同時觸發 > 5 次（central risk 沒有打架的設計）

如果通過，A + B 雙 slot portfolio 第一次具備 promotion 候選資格。

### Phase 4 — 第 3 條補位（ideal portfolio）

#### 4.1 `rsi2_pullback_1h_sma5_gap_guard` 殘餘 stop-out attribution

- 已知狀況：first pass 通過 §3.2 ANY 規則（TRENDING_UP / MIXED 正），fee_drag 0.183
  在硬閘下 0.20，max_dd 3.47%
- 已知缺項：32 aggregate `sl_hit` trades，是殘餘 drawdown 主因
- spec 已建議：「inspect residual `sl_hit` trades before adding any second guard」
- 寫 `reports/rsi2_pullback_1h_sma5_gap_guard_stop_out_attribution.md`

#### 4.2 churn-reduction 二輪

依 4.1 attribution 結果決定：
- 若 stop-out 集中在某 ATR / hold-time / sma200_dist bucket，用單一 churn-reduction
  guard 寫一支 child cartridge spec
- 若分散，park RSI2 lane

#### 4.3 三策略 combined backtest（A + B + RSI2 child）

- 同 Phase 3 pattern，但 ENABLED_STRATEGIES 三支
- 寫 `reports/portfolio_a_b_rsi2_combined_first_pass.md`
- Decision gate 沿用 Phase 3.3 三條，調整參數對應 3-strategy 規模：
  - portfolio max_dd_pct 上限放寬到 **12%**（三支 × 4%）
  - arbiter `strategy_router_blocked` reject 率 > 50%（任一支觸發即 fail，門檻不變）
  - 同 symbol 同 candle **三支以上**同時觸發 > 5 次（兩支共 emit 不算，需要至少 3 支同時 emit）

### Phase 5 — BB Fade Squeeze rescue（**降級**）

依 Locked Decision 3，**暫停**。等 Phase 1-3 都通過、Slot A 與 Slot B 都實際 promote
到 runtime 之後，再回頭看：

- 是否 portfolio 在 RANGING window 還有不夠覆蓋的 surface
- 若有，依 [reports/bb_fade_squeeze_1h_gate_attribution.md](../reports/bb_fade_squeeze_1h_gate_attribution.md)
  重新定義 squeeze gate（不要動 4h ADX gate）

## 4. What Changes from CLAUDE.md "Current Next Work"

**這份 plan 只改 research 順序，不改 runtime baseline**。CLAUDE.md 的下列段落維持不動，
任何 runtime config 變更仍需走 [plans/cartridge_promotion_checklist.md](cartridge_promotion_checklist.md)
§6 兩 commit 流程：

- Runtime Baseline 段（`STRATEGY_RUNTIME_ENABLED = false` / `ENABLED_STRATEGIES = []` /
  `REGIME_ARBITER_ENABLED = true` / `STRATEGY_ROUTER_POLICY = "fail_closed"` /
  `BTC_TREND_FILTER_ENABLED = true` 等）
- Frozen Contract 段（plugin / runtime 邊界、central RiskPlan、persistence schema）
- Safety Boundaries 段（不 promote、不開 STRATEGY_RUNTIME_ENABLED、不改 router policy）

CLAUDE.md "Current Next Work" 不要在這份 plan 落地之前修改。當 codex 實際開始 Phase 1
工作時，由 codex 同步更新 "Current Next Work" 段反映進度，避免兩處 source of truth 不一致。

差異對照：

| CLAUDE.md 現行條目 | 新計畫對應 |
| --- | --- |
| MACD 家族繼續 | Phase 1（更具體：先跑 squeeze_release_unconfirmed） |
| Donchian frozen-read | **解凍**；Phase 2.0 詮釋 + 2.1 / 2.2 / 2.3 補完 |
| 下一條 ranging = bb_fade_squeeze_1h | **降級到 Phase 5**（暫停） |
| 然後 rsi2_pullback_1h | 移到 Phase 4 |
| Add focused unit tests | 不變，每支新 child 仍需 |
| Run candidate backtests via StrategyRuntime | 不變 |
| Use `reports/strategy_plugin_candidate_review.md` for promotion-gated review | 不變 |

## 5. Out of Scope

Runtime / config 邊界：

- 本 plan 本身不得修改 runtime defaults。注意：這是 2026-04-25 的 pre-promotion guardrail；
  A+B runtime defaults 已於 2026-04-29 經 Ruei approval 後 promoted，現況以
  `trader/config.py` 為準。
- 修改 production scanner defaults
- 修改 Config class defaults
- 不得以本 plan 單獨授權任何 plugin promotion；A+B promotion 已由後續 approval packet 完成

研究紀律邊界（受既有 research note 與 spec 明文禁令約束）：

- OR-stacking `transition_aware_tightened` + `chop_trend_tightened`（research note 明文禁止）
- OR-stacking `transition_aware_tightened` + `late_entry_filter`（research note 明文禁止）
- 重啟 `dual_regime_strategy_plan.md` 的 ADX-partition 架構（已被 δ 駁回）
- BB Fade Squeeze rescue（暫停，見 Phase 5）

新機制開發 trigger（**依 regime 分開**，不互通）：

- **新 ranging detection 機制** → 只在以下都成立才討論：Slot B（Donchian
  `range_width_cv_013`）在 Phase 2 / Phase 3 失敗，**且** Phase 5 BB Fade Squeeze rescue
  也失敗。RSI2 的成敗與此無關（RSI2 不是 ranging 機制）
- **新 trending mechanism / 新 Slot A 補位** → 只在以下都成立才討論：Slot A 勝出機制在
  Phase 1 全項失敗，**且** Phase 4 RSI2 churn-reduction 二輪也失敗

Portfolio 結構邊界：

- 任何第 4 / 第 5 / ... slot 的設計（保持 ideal 上限 = 3 strategies）

## 6. Promotion Path

Post-promotion note: §6.1 的 2-slot path 已完成並 promoted。以下保留為
historical path description，不是新的待辦授權。

實際 promote 仍依 [plans/cartridge_promotion_checklist.md](cartridge_promotion_checklist.md) §6
兩 commit 流程：

1. `trader/strategies/plugins/_catalog.py` 對應 entry `enabled` 改 `True`
2. `trader/config.py` 把 plugin id 加到 `ENABLED_STRATEGIES`，`STRATEGY_RUNTIME_ENABLED`
   設 `True`（若仍 `False`）

對應到 portfolio 命題的兩條 promotion path：

### 6.1 2-slot 最低 promotion（Slot A + Slot B） — Completed 2026-04-29

Completion record:

- Approved by Ruei on 2026-04-29.
- Catalog enablement: `5dee878`.
- Config runtime defaults: `1933e65`.
- Recovery backlog scheduling: `827b5a7`.
- Post-promotion control: `reports/portfolio_ab_post_promotion_control.md`.

**前提條件**：

- Phase 1 (1.1 / 1.2 / 1.3) 全部通過，Slot A 勝出機制與 §3.4 sweep 完成
- Phase 2 (2.1 / 2.2 / 2.3) 全部通過，Slot B per-symbol matrix 與 robustness sweep 完成
- Phase 3 (3.1 / 3.2 / 3.3) 全部通過，且 3.3 三個 Decision gate 沒有觸發 fail
- 兩支 slot candidate 各自仍滿足 [cartridge_promotion_checklist.md](cartridge_promotion_checklist.md)
  §2 / §3 / §4 / §5 全部 gate
- Ruei 明確 approve

達成後：兩支 plugin id 同時加入 `ENABLED_STRATEGIES`。

### 6.2 3-slot 理想 promotion（Slot A + Slot B + RSI2 child） — Not Active

僅在 6.1 已實際 promote 並且 Phase 4 全部通過後才考慮。

**前提條件**（在 6.1 之上加碼）：

- Phase 4.1 stop-out attribution 結果支持 single-guard child 設計（不是分散到無法收斂）
- Phase 4.2 churn-reduction 二輪 child 通過 §3.2 / §3.4 / §4 全部 gate
- Phase 4.3 三策略 combined backtest 通過，portfolio max_dd 不超過 12%
- Ruei 明確 approve（不是自動延伸自 6.1 的授權）

達成後：第 3 支 plugin id 加入 `ENABLED_STRATEGIES`。

### 6.3 Promotion 不適用的情況

- 任一 phase 的 Decision gate 觸發 fail → 退回該 phase 重做，**不得**部分 promote
- BB Fade Squeeze（Phase 5）暫停期間不在任何 promotion path 內
- 沒有「先 promote Slot A 等 Slot B 之後再加」的分階段路徑：A+B 必須同時 promote 才能驗證
  Phase 3 的 portfolio 級 invariants 在生產環境一致

## 7. Resume / Handoff

Current handoff status: historical only. Do not resume Phase 1 from this
document; Phase 1-3 already fed the A+B promotion. Phase 4 RSI2 closeout, Phase
5 BB rescue/park, and scanner universe integration require fresh explicit Ruei
direction.

Original handoff text below is obsolete and kept only to explain the historical
sequence that already ran:

1. 先讀這份 plan
2. 從 Phase 1.1 開始（squeeze_release_unconfirmed pinned cell candidate review）
3. 每完成一個 sub-phase 寫對應 report，並 update CLAUDE.md "Current Next Work" 反映進度
4. 遇到 Decision gate 失敗 / 樣本不足以結論的狀況，**停下來等 Ruei 拍板**，不要自行
   橫向擴展研究範圍

## 8. References

- [reports/macd_signal_btc_4h_trending_up_research_note.md](../reports/macd_signal_btc_4h_trending_up_research_note.md)
- [reports/macd_signal_btc_4h_trending_up_transition_aware_tightening.md](../reports/macd_signal_btc_4h_trending_up_transition_aware_tightening.md)
- [reports/donchian_range_fade_4h_freeze_read.md](../reports/donchian_range_fade_4h_freeze_read.md)
- [reports/bb_fade_squeeze_1h_first_pass.md](../reports/bb_fade_squeeze_1h_first_pass.md)
- [reports/bb_fade_squeeze_1h_gate_attribution.md](../reports/bb_fade_squeeze_1h_gate_attribution.md)
- [reports/rsi2_pullback_1h_sma5_gap_guard_first_pass.md](../reports/rsi2_pullback_1h_sma5_gap_guard_first_pass.md)
- [reports/rsi2_pullback_1h_trade_attribution.md](../reports/rsi2_pullback_1h_trade_attribution.md)
- [reports/rsi_mean_reversion_research_note.md](../reports/rsi_mean_reversion_research_note.md)
- [plans/cartridge_promotion_checklist.md](cartridge_promotion_checklist.md)
- [plans/cartridge_spec_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter.md](cartridge_spec_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter.md)
- [plans/cartridge_spec_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter.md](cartridge_spec_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter.md)
- [plans/cartridge_spec_donchian_range_fade_4h_range_width_cv_013.md](cartridge_spec_donchian_range_fade_4h_range_width_cv_013.md)
- [plans/dual_regime_strategy_plan.md](dual_regime_strategy_plan.md) — superseded，僅保留 historical context
- [plans/ranging_strategy_brainstorm_design.md](ranging_strategy_brainstorm_design.md) — 三條 ranging cartridge 設計來源
