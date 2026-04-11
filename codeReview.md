# Trading Bot `feat/btc-atr-grid` Code Review

> 最後校驗：2026-04-04
> 範圍：`projects/trading_bot/.worktrees/feat-grid`
> 狀態：`449 passed`
> 本文件與 code 衝突時，以 code 為準。

## 摘要

- 核心編排層為 `trader/bot.py::TradingBot`；舊別名 `TradingBotV6 = TradingBot` 保留相容。
- Phase 3 拆分已完成：`bot.py` 現在是薄編排層 + 委派方法。
- 此 worktree 的方向性進場路由：
  - `2B` -> `v54_noscale`
  - `EMA_PULLBACK` -> `v54_noscale`
  - `VOLUME_BREAKOUT` -> `v54_noscale`
- 舊策略仍保留，位於 `trader/strategies/legacy/`。
- `v8_atr_grid` 和 `RegimeEngine` 是 feat-grid 獨有功能。
- 嚴格複查結論：Phase 3 重構未改變進出場/策略語義。後續修正僅涉及 telemetry。

---

## 複查結論

| 項目 | 結論 | 備註 |
|------|------|------|
| 進場信號 | 未發現語義變更 | `detect_2b_with_pivots` / `detect_ema_pullback` / `detect_volume_breakout` 搬入 `signal_scanner.py`，呼叫語義不變 |
| 信號優先級 | 不變 | 仍為 `2B > VOLUME_BREAKOUT > EMA_PULLBACK` |
| BTC 趨勢過濾 | 不變 | `RANGING` 阻擋方向性進場；逆勢乘數邏輯保留 |
| Tier 過濾 / 冷卻 | 不變 | Tier 門檻、2h/1h/12h 冷卻、同幣虧損冷卻全部保留 |
| 持倉出場 | 未發現語義變更 | `CLOSE` / `ADD` / `PARTIAL_CLOSE` dispatch 搬入 `position_monitor.py` |
| Grid 生命週期 | 未發現語義變更 | OPEN / CLOSE / confirm 路徑保留於 `grid_manager.py` |
| BTC regime context | 未發現語義變更 | 解析優先級仍為 `regime > 1D EMA20/50 fallback` |
| 非交易後續修正 | 已修 | `CYCLE_SUMMARY` 已補回空持倉時的發送；`V6_STAGE2_DEBUG_LOG` 移除僅影響 log 行為 |

### 值得記住的複查筆記

- `CYCLE_SUMMARY` 現在透過 `_emit_cycle_summary()` 發送，`active_trades` 為空時也會打。
- `V6_STAGE2_DEBUG_LOG` 已移除；Stage 2 診斷 log 改為無條件輸出。這是 log 行為變更，非交易邏輯變更。

---

## 當前架構

### 核心 Runtime

| 檔案 | 角色 |
|------|------|
| `trader/bot.py` | 主編排層，啟動 / 還原 / 對帳 / 主循環 |
| `trader/signal_scanner.py` | 方向性信號掃描、優先級排序、冷卻檢查 |
| `trader/position_monitor.py` | 持倉管理、平倉 / 加倉 / 減倉 dispatch、績效紀錄 |
| `trader/grid_manager.py` | V8 ATR Grid 生命週期，regime 驅動的開/平/converge |
| `trader/btc_context.py` | BTC regime context + 1D EMA fallback |
| `trader/utils.py` | 共用 trade log / PnL 工具 |
| `trader/positions.py` | `PositionManager`，策略狀態，持久化 payload |
| `trader/persistence.py` | `positions.json` atomic write，schema v2 envelope |
| `trader/regime.py` | `RegimeEngine`（`TRENDING / RANGING / SQUEEZE`，遲滯確認） |
| `trader/infrastructure/performance_db.py` | `performance.db` 交易紀錄器 |

### 策略註冊表

| 路徑 | 狀態 | 備註 |
|------|------|------|
| `trader/strategies/v54_noscale.py` | 啟用 | 當前方向性 runtime 策略 |
| `trader/strategies/v8_grid/` | 啟用 | Grid 專用（`V8AtrGrid`, `PoolManager`） |
| `trader/strategies/legacy/v7_structure.py` | Legacy | 舊倉位/還原倉位及測試仍使用 |
| `trader/strategies/legacy/v53_sop.py` | Legacy | 舊倉位可繼續在此策略下運行 |
| `trader/strategies/legacy/v6_pyramid.py` | 廢棄 | 僅保留相容性 |

### Bot 主循環

當前循環順序：

1. `scan_for_signals()`
2. `_monitor_grid_state()`
3. `_sync_exchange_positions()`
4. `monitor_positions()`
5. `telegram_handler.poll()`

重要細節：

- Grid 生命週期獨立於 `active_trades`。
- `_sync_exchange_positions()` 每個 cycle 都執行，包括空倉時。
- `bot.py` 保留薄委派方法，確保舊測試和 mock 不會斷裂。

---

## 策略路由

feat-grid 當前 `SIGNAL_STRATEGY_MAP`：

```python
SIGNAL_STRATEGY_MAP = {
    "2B": "v54_noscale",
    "EMA_PULLBACK": "v54_noscale",
    "VOLUME_BREAKOUT": "v54_noscale",
}
```

### `v54_noscale`

- 此 worktree 的主力方向性策略
- 不加倉、不減倉
- `1.0R` -> breakeven `+0.1R`
- `1.5R` / `2.0R` -> 鎖定，reason code `V54_LOCK_15R` / `V54_LOCK_20R`
- 主要出場：structure break / `stage1_timeout` / ATR trailing

### `v7_structure`

- 保留供 legacy 相容，非此 worktree 的預設進場路由
- 三段結構加倉邏輯
- 加倉條件仍為 結構 + K 棒 body/range + 量能

### `v53_sop`

- 在 feat-grid 中已非預設進場路由
- 舊倉位/還原倉位可繼續在 `v53_sop` 下完成
- 減倉路徑保留於 `position_monitor.handle_v53_reduce()`

### `v6_pyramid`

- 已廢棄
- 僅保留供相容性和舊狀態處理

### `v8_atr_grid`

- 與方向性進場分離的獨立 runtime
- 交易紀錄寫入 `strategy_name = "v8_atr_grid"`
- Regime exit：非 `RANGING` 時立即全平

---

## 關鍵 Runtime 行為

### 信號掃描

- `signal_scanner.py` 是當前進場守門員
- `_check_cooldowns()` 集中管理冷卻邏輯；行為保留不變
- Scanner 在決策前丟棄未完成 K 線
- Tier 門檻仍使用 `Config.V7_MIN_SIGNAL_TIER`

### BTC Context

- `btc_context.py` 提供：
  - BTC 4H regime context（透過 `RegimeEngine`）
  - BTC 1D EMA20/50 fallback
  - 最終解析 context（透過 `resolve_btc_trend_context()`）
- `BTC_EMA_RANGING_THRESHOLD = 0.005` 意即 EMA 差距 `< 0.5%` => `RANGING`

### 持倉監控

- `monitor_positions()` 是當前核心 dispatch 層
- `handle_close()` 仍保留失敗時的 rollback 語義
- `handle_stage2()` / `handle_stage3()` 仍依策略分支
- `handle_v53_reduce()` 仍累積 partial realized PnL
- MFE / MAE / `realized_r` / `capture_ratio` 等交易統計仍寫入 `performance.db`

### Grid Runtime

- `grid_manager.monitor_grid_state()` 負責 regime 路由
- `grid_manager.scan_grid_signals()` 處理 RANGING 啟動
- `grid_manager.execute_grid_action()` 負責 OPEN / CLOSE 執行
- Grid runtime 在 exchange 對帳時具備 hedge 感知

---

## 持久化、DB 與 Log

### 持久化

- `positions.json` 仍使用 atomic temp-file rename 寫入
- Envelope schema 目前為：

```json
{
  "schema_version": 2,
  "positions": { ... }
}
```

- Grid persistence v2 包含 pool snapshot 欄位：
  - `grid_allocated`
  - `grid_realized_pnl`
  - `grid_round_count`

### Runtime 檔案

| 路徑 | 用途 |
|------|------|
| `.log/positions.json` | 本機 runtime position 來源 |
| `performance.db` | 交易/績效 SQLite |
| `hot_symbols.json` | Scanner 選出的熱門標的 |
| `.log/bot.log` | 主 runtime log |
| `.log/trades.log` | 交易專用 log stream |
| `.log/scanner.log` | Scanner log |

---

## 測試

當前本機狀態：

- `python -m pytest trader/tests -q`
- 結果：`449 passed`

測試佈局：

- `trader/tests/` 存放當前 runtime 覆蓋
- `trader/tests/legacy/` 存放 legacy 策略相容性覆蓋
- `trader/tests/test_v54_noscale.py` 覆蓋啟用中的方向性策略
- Grid 覆蓋分布在 `test_grid_integration.py`、`test_grid_runtime_controls.py`、`test_pool_manager.py`

---

## 工具相容性

Bot runtime 之外的近期同步工作：

### `tools/Backtesting`

- 已更新為使用 `Config`（移除的 `ConfigV6` 已替換）
- 已更新 legacy 策略 import 路徑至 `trader/strategies/legacy/`
- 新增 `v54` 相容，feat-grid 交易不會被誤標為 `v53`
- 當前結果：
  - 預設根目錄：通過
  - `TRADING_BOT_ROOT=...\\.worktrees\\feat-grid`：通過

### `tools/quantDashboard`

- 已更新策略分類：
  - `v54_noscale` -> `V54`
  - `v8_atr_grid` -> `GRID`
- 防止 feat-grid 交易被歸入 `V53`
- README 和 DB 路徑文件已對齊至 `performance.db`

---

## 注意事項

- `_execute_trade()` 仍有一段歷史遺留的 2B 路徑（與 `use_v6` 相關），不要誤讀為「V6 策略仍是啟用中的 runtime 策略」。
- 硬止損更新仍為 `cancel -> place`，存在短暫非原子曝險窗口。
- Production `positions.json` 真實來源在 rwUbuntu；本機副本可能過時。
- 若涉及進出場/策略語義，先問。

---

## 優先閱讀檔案

1. `trader/config.py`
2. `trader/bot.py`
3. `trader/signal_scanner.py`
4. `trader/position_monitor.py`
5. `trader/grid_manager.py`
6. `trader/btc_context.py`
7. `trader/strategies/base.py`
8. `trader/strategies/v54_noscale.py`

---

## Patch B Research Note (2026-04-06)

- `Patch B` 的主題是把 higher-TF filter / BTC context / regime 改成 confirmed-candle only。
- 這包已完成 backtest 與 attribution 驗證，但 **不保留在 runtime**；目前 runtime 已回到 `Patch A` 語義。
- 保留的內容是研究結論與 instrumentation，不是交易路由本身。

### Why revert runtime

- `Patch B` 讓績效從 `Patch A` 的 `9.07% / PF 2.45 / Sharpe 2.58` 下到約 `5.67% / PF 1.75 / Sharpe 1.61`。
- attribution 顯示主因不是 regime，而是 `tier / MTF` timing 改變。
- `tier_filter` 裡約 `85%` 是 `mtf_status=misaligned`，而且大多數是 `tier_score=0` 的 hard gate。

### Key finding

- 最明顯受傷的是 `SHORT EMA_PULLBACK`。
- 已識別出 `9` 筆典型案例：原時間點是 `MTF misaligned`，只差 `1` 根 `4H` closed candle 就變成 `aligned`。
- 這 `9` 筆合計 PnL 從 `+15.022 USDT` 變成 `-27.664 USDT`，差額 `-42.686 USDT`。
- 也就是說，confirmed-candle 修正本身更乾淨，但對目前這套 alpha 來說，代價是 entry 晚一拍。

### Current decision

- runtime 維持 `Patch A` 語義：
  - `signal_scanner` 只 drop signal timeframe 未收 K
  - higher-TF trend / MTF / BTC daily / regime 仍使用最新 candle
- 下一步研究方向不是重新上 `Patch B`，而是探索更靈敏的 `EMA_PULLBACK / MTF` gate 設計。
