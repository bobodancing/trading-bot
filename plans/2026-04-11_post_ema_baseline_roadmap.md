# Post-EMA Baseline Roadmap

- **Date**: 2026-04-11
- **Author**: 小波 + Ruei
- **Scope**: trading_bot feat-grid + tools/Backtesting + rwUbuntu
- **Status**: Active. Awaiting Ruei to fill Open Questions before P0 starts.

---

## Context

週末 (2026-04-10 ~ 04-11) 決策收斂：

- `EMA_PULLBACK` 研究結論 = **keep off**，不升 runtime
- `Patch B` (higher-TF confirmed-candle) 實驗 **revert**，live 回到 Patch A 語義
- `V54 NoScale` (2B-only, A-tier only, 不加倉不減倉，純移損 1.0R/1.5R/2.0R + ATR trailing) 為 **唯一主力 baseline 候選**
- Tools cleanup 4 commits 已落地 (tools/Backtesting master `5caa5f8..6134365`)
- EMA research package 已 frozen (tools/Backtesting master `dc985ce`) 與 (trading_bot feat/btc-atr-grid `a45b854`)

但工具修好只是 plumbing 層。真正的進展要等 V54 baseline 被 multi-window + forward sample 驗證過，才能算「可信」。

## Framing

現階段目標 **不是「策略突破」**，是建立 **乾淨可驗證的 V54 baseline**。

- 少虧冤枉錢 = process debt 償還 = alpha protection
- 目前卡住的都是 process debt（工具 / config / 流程），可 linear 清償
- 離「開始賺錢」還有一段距離，估計 ~10% 進度。差的不是一個新策略，是穩定的 baseline + 真實 live sample
- Discipline: 每個 Priority track 完成後 **停**、**複查**、**commit**，才進下一個

## Priority Tracks

**順序是硬性的**。前一個沒過不能跳下一個。

---

### P0 — Config Parity Verification

- **Who**: Codex 寫 code + test，Ruei 審 reconcile 決策
- **Goal**: 消除 `bot_config.json` vs `trader/config.py` 的 silent divergence，避免 runtime 跑到被研究否決的 EMA/VB/Grid 組合
- **Why P0**: 這是唯一會讓所有上游研究一夕歸零的 single point of failure。EMA 研究結論寫「keep off」，但如果 JSON 把 `ENABLE_EMA_PULLBACK=True` 送進 runtime，整個研究等於白做

#### Tasks

1. **新增 `scripts/config_parity_check.py`** (在 `projects/trading_bot/.worktrees/feat-grid/scripts/`)
   - 讀 `bot_config.json` 所有 top-level keys
   - 讀 `trader/config.py` 的 `Config` class 所有 UPPERCASE class attrs
   - 對比並分類：
     - `MISSING_IN_JSON` — Config 有，JSON 無
     - `MISSING_IN_CONFIG` — JSON 有，Config 無
     - `VALUE_MISMATCH` — 兩邊都有但值不同
     - `TYPE_MISMATCH` — 值相等但 type 不同 (例如 `"True"` str vs `True` bool)
   - 輸出 markdown report: `reports/config_parity_YYYYMMDD.md`
   - CLI: `--json <path>` / `--config <path>` / `--out <path>` / `--critical-only`

2. **Critical Key List** (寫在 script 內 `CRITICAL_KEYS = frozenset({...})`)
   ```
   ENABLE_EMA_PULLBACK
   ENABLE_VOLUME_BREAKOUT
   ENABLE_GRID_TRADING
   V7_MIN_SIGNAL_TIER
   SIGNAL_STRATEGY_MAP
   ```
   Ruei 後續若要擴充會在 Open Questions 補

3. **Bot init parity hook** (`trader/bot.py`)
   - 在 `__init__` 或 `_init_exchange` 前加 `_verify_config_parity()`
   - 呼叫 parity check
   - Critical mismatch → `raise RuntimeError("Config parity check failed: <list>")`
   - Non-critical mismatch → `logger.warning(...)` 但不 abort
   - 加 env var escape: `BYPASS_CONFIG_PARITY=1` 給 backtest harness 用（backtest 必須能 bypass，不然 CI/自動化全壞）

4. **Tests** (`trader/tests/test_config_parity.py`，新增檔)
   - `test_parity_passes_when_aligned`: 模擬乾淨 config → check 通過
   - `test_parity_fails_on_critical_mismatch`: 注入 `ENABLE_EMA_PULLBACK=True` 在 JSON → bot init raise
   - `test_parity_warns_on_noncritical_mismatch`: 非 critical key 不 abort
   - `test_bypass_env_var_skips_check`: 設 `BYPASS_CONFIG_PARITY=1` → 跳過檢查

#### Acceptance

- [ ] `python scripts/config_parity_check.py --out reports/config_parity_20260411.md` 產出 report
- [ ] 如果 current state 有 **critical mismatch**，**Codex 立即停手**，貼 report 給小波 + Ruei 決定怎麼 reconcile（不要自行改任何 JSON 或 Config 值）
- [ ] `cd projects/trading_bot/.worktrees/feat-grid && python -m pytest trader/tests/ -v` 全過（含新增 parity tests）
- [ ] `cd tools/Backtesting && python -m pytest tests/ -v` 全過（驗證 bypass env 生效）
- [ ] Bot 實際 init smoke test：乾淨 config 通過、注入 mismatch 時 abort

#### Do NOT

- 不要修改 `bot_config.json` 任何值
- 不要修改 `trader/config.py` default
- 不要為了讓 test 過就自己選「canonical 值」— reconcile 決策 **全部** 給 Ruei
- 不要把 parity check 寫成 strict mode without bypass — backtest 必須能繞過
- 不要把 runtime 新 feature 塞進這個 commit（scope creep）

#### Deliverable

- `scripts/config_parity_check.py`
- `trader/bot.py` patch (init hook)
- `trader/tests/test_config_parity.py`
- `reports/config_parity_20260411.md` (first run output)

---

### P0.5 — V54 Baseline Shape Discovery

- **Who**: Codex 跑 backtest + 收資料，Ruei 定 window 日期 + 讀結論
- **Goal**: 在跑 6×6 full matrix 前，先知道 V54 NoScale 長什麼樣。沒有 shape knowledge，matrix 結果也讀不出所以然

#### Window Selection (resolved 2026-04-11)

Ruei 已回填 4 個 window (來自 BTC 4H RegimeEngine 回放)。P0.5 必須跑 **全部 4 個**。

| Label | Date Range | BTC replay observation |
|---|---|---|
| `TRENDING_UP` | `2023-10-01 -> 2024-03-31` | BTC +158.5%; TRENDING 80.5% / RANGING 19.5%; trend dir LONG 65.7% |
| `TRENDING_DOWN` | `2025-10-07 -> 2026-04-06` | BTC -44.4%; TRENDING 67.4% / RANGING 32.6%; trend dir SHORT 73.0% (recent bear, 不是純 trend) |
| `RANGING` | `2024-12-31 -> 2025-03-31` | BTC -11.9%; RANGING 51.8% / TRENDING 48.2% |
| `MIXED` | `2025-02-01 -> 2025-08-31` | BTC +6.8%; TRENDING 59.3% / RANGING 40.7%; mixed / transition |

**重要**: 第 4 個 window label 是 `MIXED`，**不要** 寫成 `SQUEEZE`。理由：RegimeEngine 回放 BTC 4H 幾乎抓不到真 SQUEEZE (大部分 period 接近 0%)，label 成 SQUEEZE 會誤導讀者。

#### Run Config (所有 window 共用)

- Symbols: `BTC/USDT ETH/USDT SOL/USDT BNB/USDT XRP/USDT DOGE/USDT`
- Strategy flag: `--strategy live` (= 依 bot_config.json，V54-only)
- Runtime flags (確認 P0 通過後這幾個一定是):
  - `ENABLE_EMA_PULLBACK=False`
  - `ENABLE_VOLUME_BREAKOUT=False`
  - `ENABLE_GRID_TRADING=False`
  - `V7_MIN_SIGNAL_TIER=A`
- Initial balance: `10000`
- CLI: 用 `resolve_backtest_window` 的 explicit `--start/--end` 模式 (不要用 latest-cache default)
- Cache prerequisite:
  - 目前 `tools/Backtesting/cache/` **缺 `BNBUSDT` 和 `XRPUSDT`** 的 parquet cache，執行 P0.5 前必須先補
  - 每個 symbol 需要 `1h` + `4h` + `1d` + `funding` 四種 timeframe 覆蓋 4 個 window 的日期範圍 (最早 `2023-10-01`，最晚 `2026-04-06`)
  - 使用現有 `BacktestDataLoader` 機制補 cache，不要新寫下載邏輯
  - 若 cache 下載 API 受 rate limit，可分 symbol 串行跑並回報進度
  - Cache 補完後以 `python scripts/clean_cache_fragments.py` dry-run 確認沒產生新碎片

#### Per-Window Collection

每個 window 跑完要收的資料：

- `summary.json`:
  - PF / Sharpe / MaxDD / trade_count / trades_per_week
  - 新增的 `window_regime_composition_4h` (Patch 3)
- Signal count by symbol (從 trades.csv 或 signal_audit 聚合)
- R distribution histogram，bucket:
  - `SL_hit` (< 0R)
  - `[0, 1)`
  - `[1, 2)`
  - `[2, 3)`
  - `[3, 5)`
  - `[5+)`
- Entry density: 按月份 bucket signal count (找 "4 個月只 6 筆" 那種 harness anomaly)
- Hold time median (bar count)

#### Output Directory

```
tools/Backtesting/results/baseline_shape_v54_20260411/
├── TRENDING_UP/
│   ├── trades.csv
│   ├── summary.json
│   ├── equity_curve.html
│   └── signal_audit.json
├── TRENDING_DOWN/...
├── RANGING/...
├── MIXED/...
└── SHAPE_SUMMARY.md
```

#### SHAPE_SUMMARY.md 必須包含

- **Header**: window dates, Codex 執行時間, feat-grid commit hash, `trader/config.py` hash
- **Side-by-side metric table**: PF / Sharpe / MaxDD / trade_count / trades_per_week × 4 windows
- **R distribution table**: row = window, col = bucket, cell = count + pct
- **Regime composition verification**: 實際 4H regime % 是否符合 label 預期
- **Signal count by symbol**: 確認沒有單一 symbol 吃掉 80%+ 的訊號
- **Entry density anomalies**: 按月列 signal count，flag 任何月份 < 3 筆
- **Objective observations** (舉例, 數字填實際值):
  - "V54 在 TRENDING_UP 的 PF 是 X，在 RANGING 的 PF 是 Y，相對差 Z%"
  - "A-tier gate 在 RANGING 過濾了 X% 的 raw 2B signal"
  - "R distribution 尾部 (>= 3R) 在 TRENDING_UP 佔 X%，RANGING 佔 Y%"

#### SHAPE_SUMMARY.md **禁止** 出現的字眼

- "V54 looks good" / "passes" / "promising" / "ready"
- 任何 promotion 或 go/no-go 判斷
- 任何參數調整建議

這份是 **observation report**，不是 decision memo。決策是 Ruei + 小波讀完後做的。

#### Acceptance

- [ ] 所有指定 window 成功跑完 (0 exception)
- [ ] 每個 window 的實際 regime composition 與 roadmap Window Selection 表格填寫的 BTC replay observation 在 ±5% 以內 (例：TRENDING_UP 實跑 RANGING 應落在 14.5% ~ 24.5%，roadmap 寫 19.5%)。超出 ±5% 必須在 `SHAPE_SUMMARY.md` 明確 flag，不要隱瞞。`TRENDING_DOWN` 本來就有 RANGING 32.6% (非純 trend)，這是 Ruei 已接受的特徵，不視為 flag 條件
- [ ] 沒有 entry density anomaly (或有的話在報表明確 flag)
- [ ] SHAPE_SUMMARY.md 有上述所有 section 且數字自洽
- [ ] `trades_per_week` metric 非 0 非爆量 (每週 `[0.5, 20]` 是 sanity 區間)

#### Do NOT

- 不要自己調參數 / 換 tier gate / 改 SL logic
- 不要在 SHAPE_SUMMARY.md 做 promotion 判斷
- 不要跑 6×6 full matrix (那是 P2)
- 不要在數據未出前預測 "V54 應該會 pass"
- 不要寫進 `results/ema_weekend_review_*` 資料夾
- 不要 commit 這些 results；這個 folder 會被 `.gitignore` 的 `results/*` 擋掉，**不要** whitelist 例外

#### Deliverable

- 4 個 (或 3 個) window 資料夾 + `SHAPE_SUMMARY.md`
- 交付後 **停**，等小波 + Ruei 讀完再進 P1

---

### P1 — Runtime Parity Enforcement

- **Who**: Codex
- **Goal**: 根據 P0 parity report + P0.5 shape knowledge，把 runtime invariants 寫成 code (不再只是 docs)

#### Prerequisite

- P0 parity check 已 reconcile
- P0.5 SHAPE_SUMMARY 已產出並被小波 + Ruei 讀過
- 小波會根據 P0.5 結果補上 P1 具體 spec (目前先 placeholder)

#### Placeholder Spec (等 P0.5 完成後小波會細化)

- 把 P0.5 觀察到的 invariants 寫進 `trader/config.py` module-level
  - 例如: `assert V7_MIN_SIGNAL_TIER == 'A', "V54 NoScale requires A-tier only"`
- Bot 啟動時 print runtime profile summary (enabled strategies / tier gate / grid / EMA / VB)
- `codeReview.md` 加 "Runtime Invariants (2026-04-11)" section
- 新增 test 驗證 invariants 被 enforce

#### Do NOT

- 等 P0.5 完成前不要動任何 P1 code
- 不要把 P0.5 的觀察 "幫小波做 promotion"

---

### P2 — Multi-Window Matrix Validation

- **Who**: Codex 執行，Ruei + 小波 判讀
- **Goal**: 用 `tools/Backtesting/README.md` 定義的 6 symbols × 6 periods matrix 驗證 V54 是否跨 regime stable

#### Prerequisite

- P0 / P0.5 / P1 全過
- Ruei 已在 `tools/Backtesting/README.md` 的 `Multi-Window Backtest Standard` section 填入 6 個 period 的具體日期 (目前是 `<TBD by Ruei>`)

#### Tasks

1. 按 README baseline matrix 跑 6 × 6 = 36 runs
2. Aggregate: 跨 36 runs 的 PF / Sharpe / DD / trade_count median / min / max / std
3. By-regime grouping: 把 period 對應的 dominant regime 聚合 (依 Patch 3 regime composition)
4. Gate check: 依 README `Gate Reading` 原則產出 pass/fail verdict + reasoning

#### Output

- `tools/Backtesting/results/matrix_v54_20260411/matrix_report.md`
- 36 個 run 資料夾

#### Acceptance

- [ ] 36 runs 全部成功
- [ ] Matrix report 有完整表格 + by-regime summary
- [ ] Gate verdict 明確 (pass / fail)，附 reasoning

#### Do NOT

- 不要因為結果不好就自己調參數
- 不要跳過看起來 "outlier" 的 window
- 不要 promote 去 P3 — 那是小波 + Ruei 讀完 matrix report 後的決定

---

### P3 — feat-grid rwUbuntu Deployment + Forward Sample

- **Who**: Ruei 執行 deployment，Codex 寫 diff tooling
- **Goal**: 確認 V54 在 Linux 真實環境跑得起來 + 收 testnet runtime sample 跟 P2 backtest 對照

#### Prerequisite

- P2 matrix verdict = pass

#### Tasks

1. **Ruei 手動**:
   ```bash
   ssh rwfunder@solita7y-andes.nord
   cd /home/rwfunder/文件/tradingbot/trading_bot
   git fetch && git checkout feat/btc-atr-grid && git pull
   python -m pytest trader/tests/ -v   # Linux 相容性 check
   # 過了才 enable testnet
   ```
2. **Codex 寫** `scripts/forward_vs_backtest_diff.py`:
   - 讀 testnet trade log (from `performance.db` or Telegram export)
   - 讀同期的 backtest trade log (用 P2 或 P0.5 的 run)
   - 產出 divergence report:
     - Entry timestamp diff
     - Exit reason diff
     - Realized R diff
     - Slippage estimate
     - Signal 漏抓率

#### Acceptance

- [ ] Linux `pytest trader/tests/` 全過
- [ ] 7~14 天 testnet sample 收集完 (最少 30 筆 trade)
- [ ] Divergence report: 主要 metric (PF, Sharpe, trade count) 差異在 Ruei 定義的 threshold 內

---

### P4 — 小資金 Live 試跑

暫不展開。等 P3 pass 且 Ruei 確認 divergence acceptable 才 plan。

---

## Discipline Rules

1. **不跳關**: P0 -> P0.5 -> P1 -> P2 -> P3 -> P4 順序硬性
2. **不自行決策**: Window dates / thresholds / reconcile / gate tuning / promotion 都要 Ruei 批
3. **不污染 frozen research**: `results/ema_weekend_review_20260411/` 已 committed 不加新檔
4. **每 P 完成後**:
   - Codex 貼 diff / report 給小波複查
   - 小波決定 commit strategy (local / push origin / 或先不 commit)
   - 不要在小波複查前就自己 push
5. **Commit pipeline**: Codex 改 -> 小波複查 -> commit + push -> rwUbuntu pull 測試 (只有 P3 會真的 pull)
6. **不偷跑**: 手癢也不要超前到 P2+

## Rollback Plan

- P0 / P1 改動破壞 testnet 或 runtime -> `git revert`，不 rewrite history
- P0.5 / P2 發現 V54 在某 regime fail -> **不 silent tune**，寫進報表當 finding，停下來討論
- P3 rwUbuntu Linux 環境問題 -> 修環境，不 bypass test
- 所有 commit 保留 author + Co-Authored-By tag (除非 Open Question 決定不加)

## Out of Scope (Not This Roadmap)

- 新策略研究 (EMA / VB / Grid 維持 disabled)
- `tools/Backtesting/` 新 feature (cleanup 4 patches 後 frozen)
- AutoTrader Phase 0 Round 2 (`evaluator.py`, `experiment_db.py`)
- `projects/remoteMonitoring/` Phase 1/2/3
- `map_generator_v3.py` / `project_structure_map_v3.md` 更新 (除非 P1 需要)

## Resolved Decisions (2026-04-11)

- [x] **Q1** — `CRITICAL_KEYS` 不擴充，維持 5 個 (`ENABLE_EMA_PULLBACK`, `ENABLE_VOLUME_BREAKOUT`, `ENABLE_GRID_TRADING`, `V7_MIN_SIGNAL_TIER`, `SIGNAL_STRATEGY_MAP`)。其他 risk / config mismatch 進 report + warning，**不 abort**
- [x] **Q2** — P0.5 window 已填在 P0.5 `Window Selection` 表格，4 個 window 全跑
- [x] **Q3** — 跑第 4 個 window，label = `MIXED`，**不要** 寫成 `SQUEEZE`。理由: RegimeEngine 回放 BTC 4H 幾乎抓不到真 SQUEEZE (大部分 period 接近 0%)，label 成 SQUEEZE 會誤導讀者
- [x] **Q4** — P2 README 6 periods 已填在 `tools/Backtesting/README.md` 的 `Multi-Window Backtest Standard` section。其中 `SQUEEZE` 標為 **low-vol proxy**，不是真正 RegimeEngine SQUEEZE
- [x] **Q5** — P3 divergence threshold (第一階段小樣本):
  - PF diff `<= 25%`
  - trade count / trades_per_week diff `<= 30%`
  - Unmatched entries `<= 20%`
  - Median realized R diff `<= 0.25R`
  - Unknown / unsafe exit `<= 5%`
  - Position sync / order safety error `== 0` (不能有任何)
  - 累積樣本 **> 100 筆** 後收緊到 PF `<= 15%`、trade count `<= 20%`
- [x] **Q6** — Codex commit 加 footer `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`，沿用小波 pipeline 慣例。若要精準標 Codex 自己可再加第二行 `Co-Authored-By: Codex <noreply@openai.com>`，但不是強制

---

## Known Constraints (2026-04-11)

- **Cache 缺 BNBUSDT / XRPUSDT**: `tools/Backtesting/cache/` 目前沒有這兩個 symbol 的 parquet。P0.5 / P2 跑 6 symbols 前必須先補 (見 P0.5 `Run Config` 的 `Cache prerequisite`)。這不影響 P0 開工，但會延長 P0.5 / P2 的 wall-clock 時間
- **SQUEEZE proxy 不是真 SQUEEZE**: 見 Q3 / Q4。所有報表裡看到 `SQUEEZE` 欄位時都要記得是 low-vol proxy，不是 RegimeEngine 判定的 SQUEEZE regime

---

*所有 Open Questions 已 resolved。Codex 可從 P0 開始動工。每個 P 完成停一次，小波複查完才進下一個。*
