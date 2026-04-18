# EMA/VB Entry Lane Backtest Plan

Date: 2026-04-15

Status: plan only. Do not enable EMA/VB in runtime from this plan alone.

Owner: Ruei

Plan source: `projects/trading_bot/.worktrees/feat-grid`

Execution branch / worktree: `projects/trading_bot/.worktrees/feat-regime-router` (`feat/regime-router-contract`)

Backtest workspace: `extensions/Backtesting/`

## 背景

目前 R5 testnet candidate 是 `V54 + Neutral Arbiter only`，Macro Overlay off。runtime 已經安全跑起來，但到目前為止沒有任何成交。從 log 看，問題不是下單層壞掉，而是 `2B -> v54_noscale` 這條 lane 太窄，runtime 大多在 market filter / trend filter / tier gate 前後被擋掉。

這代表 V54 的 live validation 進度停在 0 筆成交，也代表「開始賺錢」的進度被單一 entry lane 限制。接下來可以評估是否把 `EMA_PULLBACK` 和 `VOLUME_BREAKOUT` 重新納入，但必須先經過 isolated backtest，不可以直接開 live。

## 核心假設

`v54_noscale` 不一定只能吃 `2B` entry。它也可能作為一個 frozen exit / position-management engine，搭配多個 entry lane：

```text
2B              -> v54_noscale
EMA_PULLBACK    -> v54_noscale
VOLUME_BREAKOUT -> v54_noscale
```

但這只是待驗證假設。EMA/VB 不是已通過 R5 的 runtime 邏輯，也不是 range/mixed/squeeze 策略的替代品。它們優先被視為 trend specialist 的補充 entry lane。

## Hard Guardrails

1. **V54 strategy logic frozen**  
   不改 `v54_noscale` 的 exit、lock、SL、timeout、position-management 行為。這輪只評估 entry lane 是否能安全接到 V54。

2. **不直接開 runtime**  
   `enable_ema_pullback` / `enable_volume_breakout` 維持 false，直到 backtest 報告通過 Ruei 決策。runtime 現階段仍是 `2B only`。

3. **不盲目調參**  
   第一輪只跑現有 config shape。不要一邊看結果一邊調 `EMA_PULLBACK_THRESHOLD`、`VOLUME_BREAKOUT_MULT`、tier 門檻或 market filter threshold。

4. **不污染 frozen research folder**  
   不新增檔案到 `extensions/Backtesting/results/ema_weekend_review_20260411/`。新結果放在新的 output folder。

5. **不把 EMA/VB 當成 range solution**  
   EMA/VB 可以增加 trend entry density，但 RANGING / MIXED / SQUEEZE 策略與 arbiter/router track 仍然獨立存在。

6. **後續實作切到 feat-regime-router**  
   這條線屬於 strategy expansion + routing work，不繼續壓在 `feat-grid`。`feat-grid` 保留作為 R5 runtime baseline / history；EMA/VB lane tooling、router contract、後續 strategy promotion 都在 `feat-regime-router` 做。

## 已知程式狀態

runtime 目前故意收斂為：

```text
signal_strategy_map = {"2B": "v54_noscale"}
enable_ema_pullback = false
enable_volume_breakout = false
v7_min_signal_tier = "A"
regime_arbiter_enabled = true
macro_overlay_enabled = false
```

`extensions/Backtesting/backtest_engine.py` 的 `--strategy v54` 已經有「三種 signal 都接 V54」的 preset 概念：

```text
{"2B": "v54", "EMA_PULLBACK": "v54", "VOLUME_BREAKOUT": "v54"}
```

但這不等於 runtime 已經可以安全開 EMA/VB。回測需要更細的 lane matrix，尤其要能跑 `EMA_ONLY` / `VB_ONLY`。如果現有工具沒有 signal allowlist，就先補 backtest-only tooling，不改 production runtime 行為。

## 舊 EMA 研究的讀法

`ema_weekend_review_20260411` 的結論曾經是 `EMA_PULLBACK keep off`。這個結論仍然有效，但它的 scope 是當時的 EMA patch review，不是完整的 multi-lane V54 runtime review。

這輪不是推翻舊結論，而是回答新的問題：

- 在 R5 已經收斂成 `V54 + Neutral Arbiter` 後，EMA/VB 是否能補足 `2B only` 的交易密度？
- EMA/VB 接到 `v54_noscale` 後，是增加 winner，還是只是增加 chop loss？
- EMA/VB 在不同 regime 的表現是否穩定，還是只在單一 window 好看？

## 要回答的問題

1. `EMA_PULLBACK` 單獨接 V54 是否有正 edge？
2. `VOLUME_BREAKOUT` 單獨接 V54 是否有正 edge？
3. `2B + EMA + VB` 是否比 `2B only` 顯著改善交易密度，而且沒有破壞 PF / MaxDD？
4. 新增 entry lane 的收益是否 incremental，還是跟 `2B` 高度重疊？
5. EMA/VB 的虧損是否集中在 RANGING / MIXED / transition window？
6. V54 的 lock / trailing / timeout 是否適合 EMA/VB entry，或會提早砍掉該放的趨勢？
7. 若開 runtime，應該只開 EMA、只開 VB，還是兩者都開？

## Run Windows

第一輪沿用 P0.5 的 4 個 window，避免又換一組日期造成讀法漂移。

| Label | Date Range | 用途 |
|---|---|---|
| `TRENDING_UP` | `2023-10-01 -> 2024-03-31` | 驗證多頭趨勢中 EMA/VB 是否補進趨勢中段 |
| `TRENDING_DOWN` | `2025-10-07 -> 2026-04-06` | 驗證空頭趨勢中 EMA/VB 是否補進順勢 short |
| `RANGING` | `2024-12-31 -> 2025-03-31` | 檢查 EMA/VB 是否在 chop 中過度進場 |
| `MIXED` | `2025-02-01 -> 2025-08-31` | 檢查 transition / mixed market 是否產生系統性虧損 |

注意：`RANGING` 和 `MIXED` 在 `2025-02-01 -> 2025-03-31` 有重疊。報告不可把 4 個 window 的 trade count 直接加總成「獨立樣本數」。總結必須同時提供 per-window view 和 cross-window deduped view。

第二輪若第一輪通過，再跑 R4 transition stress windows。R4 不作為第一輪必要條件，避免一開始矩陣過大。

## Symbols

第一輪用 P0.5 同一組 full-symbol universe：

```text
BTC/USDT ETH/USDT SOL/USDT BNB/USDT XRP/USDT DOGE/USDT
```

如果第一輪有 candidate lane 通過，再加一輪 runtime-like universe：

```text
scanner L1 high-volume symbols + current bot_symbols snapshot
```

runtime-like universe 只做 robustness check，不拿來取代 6-symbol baseline。

## Backtest Matrix

每個 window 都跑下列 matrix：

| Run ID | 2B | EMA_PULLBACK | VOLUME_BREAKOUT | Strategy map | 目的 |
|---|---:|---:|---:|---|---|
| `BASE_2B_ONLY` | on | off | off | `2B -> v54_noscale` | 現行 R5 baseline |
| `EMA_ONLY` | off | on | off | `EMA_PULLBACK -> v54_noscale` | 看 EMA 本身 edge |
| `VB_ONLY` | off | off | on | `VOLUME_BREAKOUT -> v54_noscale` | 看 VB 本身 edge |
| `EMA_VB_ONLY` | off | on | on | EMA/VB -> V54 | 看非 2B lane 組合 |
| `2B_EMA` | on | on | off | 2B/EMA -> V54 | 看 EMA 是否補強 2B |
| `2B_VB` | on | off | on | 2B/VB -> V54 | 看 VB 是否補強 2B |
| `2B_EMA_VB` | on | on | on | all -> V54 | 最終 runtime 候選 |

注意：production 目前沒有 `ENABLE_2B` flag。若工具無法關閉 2B，需補 backtest-only signal allowlist，例如：

```text
allowed_signal_types = ["EMA_PULLBACK"]
allowed_signal_types = ["VOLUME_BREAKOUT"]
```

這個 allowlist 只能在 Backtesting tooling 使用，不可改 production scanner 的預設行為。

若需要新增 backtest-only `allowed_signal_types` tooling，必須同時補 unit test，驗證：

- `EMA_ONLY` 不會產生 `2B` / `VOLUME_BREAKOUT` entry
- `VB_ONLY` 不會產生 `2B` / `EMA_PULLBACK` entry
- `2B_EMA_VB` 仍保留 production priority order

## Preflight Dry Counting Pass

正式 backtest matrix 前，先跑 dry counting pass，不開倉、不計 exit，只統計每條 lane 的 raw signal funnel。

每個 window / symbol / lane 至少輸出：

```text
raw_signal_count
market_filter_pass_count
trend_filter_pass_count
mtf_aligned_count
tier_A_count
tier_B_count
tier_C_count
final_candidate_count
```

目的不是 promotion，而是避免把「被 Tier A gate 鎖死」誤讀成「EMA/VB 沒 edge」。如果 `EMA_PULLBACK` 或 `VOLUME_BREAKOUT` 在 4 個 window 的 `tier_A_count` 幾乎為 0，正式報告必須明確標記：runtime-parity A-tier 無法評估該 lane 的 edge，需要 Ruei 決定是否開 diagnostic B-tier pass。B-tier diagnostic 不可直接作為 live promotion 依據。

輸出：

```text
reports/ema_vb_tier_count_dry_run.md
extensions/Backtesting/results/ema_vb_entry_lane_review_20260415/tier_count_summary.csv
```

## Lane Race / Cooldown Accounting

多 lane run 必須明確記錄同一 symbol / candle 內誰贏得 entry slot。production priority 目前是：

```text
2B > VOLUME_BREAKOUT > EMA_PULLBACK
```

`2B_EMA` / `2B_VB` / `2B_EMA_VB` 的 incremental math 必須把下列情況拆開：

- pure new trade：baseline 沒有同 candle 2B entry，新 lane 補出新 trade
- replaced trade：新 lane 搶走或延後 baseline 2B entry
- suppressed signal：有 signal，但因 cooldown / existing position / priority race 被丟掉
- unchanged 2B：baseline 2B trade 不受新 lane 影響

`signal_audit_summary.json` 若無法承載這些欄位，需另產 `lane_race_audit.csv`。必要欄位：

```text
timestamp
symbol
candidate_signal_type
selected_signal_type
suppressed_by
won_race_vs
same_symbol_cooldown_block
position_slot_block
block_reason
baseline_match_key
```

如果無法證明新增 PnL 是 pure new trade 而不是替換掉原本 2B，promotion verdict 必須是 `NEEDS_SECOND_PASS`。

## Runtime-Parity Config

第一輪 matrix 預設使用 `extensions/Backtesting/config_presets.py` 的 `runtime_parity()` preset。preset 只能 copy `trader.config.Config` 既有 defaults，不可另建一份平行 runtime default：

```text
v7_min_signal_tier = "A"
regime_arbiter_enabled = true
arbiter_neutral_threshold = 0.5
arbiter_neutral_exit_threshold = 0.5
arbiter_neutral_min_bars = 1
macro_overlay_enabled = false
btc_trend_filter_enabled = true
btc_counter_trend_mult = 0.0
```

若某個舊 plan key 在當前 `Config` 不存在，不可在 preset 硬塞動態 attr；需先回 Ruei 對齊 current runtime contract。

報告必須列出使用的 fee / slippage / starting balance / funding 設定，並說明是否與 R5 runtime/backtesting standard 一致。若工具預設值不明，該 run 不可用於 promotion。

如果需要解釋為什麼某條 lane 沒交易，可以加 diagnostic-only run，使用 `diagnostic_arbiter_off()` preset：

```text
regime_arbiter_enabled = false
```

但 promotion decision 只能看 runtime-parity run，不能拿 diagnostic-only run 當 live 依據。

## Required Outputs

新 output root：

```text
extensions/Backtesting/results/ema_vb_entry_lane_review_20260415/
```

每個 run/window 至少產出：

```text
<RUN_ID>/<WINDOW>/
  trades.csv
  summary.json
  signal_audit_summary.json
  lane_race_audit.csv  # multi-lane run only; if data is already in signal_audit_summary.json, explain where
```

總結報告：

```text
reports/ema_vb_entry_lane_review.md
reports/ema_vb_tier_count_dry_run.md
```

如果有 backtest-only tooling patch，另寫：

```text
reports/ema_vb_tooling_notes.md
```

## Report Schema

`reports/ema_vb_entry_lane_review.md` 必須包含：

1. **Executive read**  
   用 5 行以內說明是否有 candidate lane 值得進下一階段。

2. **Matrix summary**  
   row = run id，columns = total trades / PF / WR / MaxDD / Sharpe / net PnL / avg R / max losing streak。

3. **By-window table**  
   每個 run 在 4 個 window 的 PF、trade count、MaxDD、net PnL。

4. **By-regime table**  
   依 entry-time regime 分桶：TRENDING / RANGING / MIXED / NEUTRAL / SQUEEZE candidate。

5. **Incremental contribution**  
   比較 `BASE_2B_ONLY` vs `2B_EMA` / `2B_VB` / `2B_EMA_VB`：
   - 新增幾筆 trade
   - 新增 trade 的 PF / MaxDD / realized R
   - pure new / replaced / suppressed / unchanged 2B 的拆分
   - 是否移除、搶走或延後原本 2B trade
   - overlap ratio

6. **Exit compatibility**  
   EMA/VB entry 走 V54 exit 後：
   - `V54_LOCK_15R` / `V54_LOCK_20R` 出現比例
   - structure break / stage1 timeout / ATR trailing 比例
   - capture ratio 是否比 2B 更差
   - 是否常常 0R 附近被 timeout 磨掉
   - EMA/VB subset capture ratio 是否低於 2B subset 的 70%
   - EMA/VB subset 0R timeout 比例是否高於 2B subset 的 1.5 倍

7. **Failure modes**  
   明列最差 window、最差 symbol、最大連敗、最大單筆虧損、虧損是否集中於 RANGING/MIXED。

8. **Promotion verdict**  
   只能使用下列其中之一：
   - `PROMOTE_EMA_ONLY`
   - `PROMOTE_VB_ONLY`
   - `PROMOTE_EMA_AND_VB`
   - `KEEP_2B_ONLY`
   - `NEEDS_SECOND_PASS`

## Acceptance Criteria

任一新 lane 要進 runtime candidate，至少要滿足：

1. `2B_EMA` / `2B_VB` / `2B_EMA_VB` 的 total PF 不低於 `BASE_2B_ONLY` 的 90%。
2. MaxDD 不高於 `BASE_2B_ONLY` 的 1.25 倍。
3. trade count 至少增加 30%，否則不值得增加 runtime 複雜度。
4. 新增 trades 的 PF 必須 > 1.2。
5. net PnL 必須 >= `BASE_2B_ONLY` net PnL；PF 允許小幅下降的前提是絕對收益和 throughput 真的改善。
6. RANGING + MIXED bucket 不可出現明顯系統性虧損；若 PF < 1 且 `(trade count >= 20 或該 bucket net loss 佔該 lane 總虧損 > 30%)`，該 lane 不可 promotion。
7. EMA/VB subset 的 capture ratio 不低於 2B subset 的 70%；若樣本數不足 10 筆，標為 inconclusive，不可單靠這條 promotion。
8. EMA/VB subset 的 0R 附近 timeout 比例不高於 2B subset 的 1.5 倍；若超過，代表 V54 exit 可能不對症，不可 promotion。
9. multi-lane incremental PnL 必須主要來自 pure new trade，不可主要靠 replaced 2B trade 撐起。
10. dry counting pass 必須證明該 lane 在 runtime-parity A-tier 下有足夠候選；若 A-tier 幾乎 0 筆，只能結論為「A-tier runtime 無法評估」，不能結論為「signal 沒 edge」。
11. 單一 symbol 不可貢獻超過新增 PnL 的 60%。
12. 不可靠單一 outlier window 撐起全部 PF。

如果 `2B_EMA_VB` 通過，但 `EMA_ONLY` 或 `VB_ONLY` 有明顯 poison bucket，promotion 時要拆開，不要為了簡單一次全開。

## Decision Tree

```text
第一輪 matrix 完成
  |
  |-- 沒有任何 lane 通過 acceptance
  |     -> KEEP_2B_ONLY
  |     -> EMA/VB 不開 runtime
  |     -> 重心轉回 RANGING/MIXED/SQUEEZE strategy + router
  |
  |-- 單一 lane 通過
  |     -> 跑 R4 transition stress windows
  |     -> 通過才做 runtime config patch
  |
  |-- EMA + VB 都通過
        -> 檢查 overlap / cooldown / shared risk
        -> 優先 promote incremental edge 較乾淨的一條
        -> 不預設兩條同時開
```

## Runtime Patch Shape

如果 Ruei 決定 promotion，runtime patch 才能改成類似：

```json
{
  "enable_ema_pullback": true,
  "enable_volume_breakout": false,
  "signal_strategy_map": {
    "2B": "v54_noscale",
    "EMA_PULLBACK": "v54_noscale"
  }
}
```

或：

```json
{
  "enable_ema_pullback": false,
  "enable_volume_breakout": true,
  "signal_strategy_map": {
    "2B": "v54_noscale",
    "VOLUME_BREAKOUT": "v54_noscale"
  }
}
```

兩條都開必須有明確 evidence，不作為預設。

runtime promotion 不只改 flag，還要同時決定：

- EMA/VB 是否共用 2B 的 same-symbol cooldown
- EMA/VB 是否共用 2B 的 risk budget / max concurrent position
- Telegram / DB / signal audit 是否清楚標記 entry lane
- scanner multi-lane candidate 是否需要同步調整

## Config Validation Requirement

`bot_config.json` 已移除；runtime config 單一來源是 `trader/config.py`。任何 runtime patch 後都必須跑：

```bash
python -c "from trader.config import Config; Config.validate()"
```

必須無例外。entry lane 相關 key 的調整仍需經 Ruei 核對。

## Stop Conditions

Codex / executor 完成第一輪 matrix 和報告後停手。不要自行：

- 開 runtime EMA/VB
- 修改 `trader/config.py` 的 runtime flag default
- push
- restart rwUbuntu services
- 調整 thresholds
- patch `v54_noscale`

promotion 由 Ruei 決策。
