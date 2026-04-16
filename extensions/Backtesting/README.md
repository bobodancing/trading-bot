# Trading Bot 回測外掛

Trading Bot 的獨立回測工具。**零修改** `projects/trading_bot/trader/` — 完全透過 patch + inject 的方式將 bot 的網路 I/O 替換成本地 mock，讓真實策略邏輯在歷史數據上執行。

---

## 目錄

- [架構概覽](#架構概覽)
- [前置需求](#前置需求)
- [目錄結構](#目錄結構)
- [快速開始](#快速開始)
- [策略選擇](#策略選擇)
- [模組說明](#模組說明)
- [CLI 參考](#cli-參考)
- [程式化使用](#程式化使用)
- [Multi-Window Backtest Standard](#multi-window-backtest-standard)
- [AutoTrader 整合](#autotrader-整合)
- [Trade Replayer](#trade-replayer)
- [設計決策](#設計決策)
- [已知限制](#已知限制)
- [執行測試](#執行測試)

---

## 架構概覽

```
歷史 K 線 (Binance API / Parquet 快取)
        ↓
  BacktestDataLoader  ←  FundingLoader（funding rate Parquet 快取）
        ↓
  TimeSeriesEngine          ← 時間視窗控制（防 look-ahead bias）
        ↓              ↓
MockDataProvider    MockOrderEngine
                       ├─ deduct_funding()  ← funding rate 結算
                       └─ check_stop_triggers()
        ↓              ↓
   create_backtest_bot()   ← patch TradingBot runtime（5 patches + 7 injections）
        ↓
  _backtest_context()       ← Context Manager（Config + datetime patch，覆蓋 current/legacy modules）
        ↓
  BacktestEngine            ← 主迴圈（per 1H bar）
   ├─ run_single()          ← 純計算 API（供 AutoTrader 程式化呼叫）
   │   ├─ check_stop_triggers()
   │   ├─ scan_for_signals()    ← 真實進場邏輯（2B / EMA Pullback / Volume Breakout）
   │   ├─ _apply_strategy_map() ← 策略覆寫（v54 / v7 / v6 / v53 / live）
   │   ├─ monitor_positions()   ← 真實出場邏輯（由策略決定）
   │   ├─ funding rate 結算     ← 每 8H（00:00 / 08:00 / 16:00 UTC）
   │   └─ equity_curve 計算
   └─ run()                 ← CLI 入口（= run_single(verbose=True)）
        ↓
  BacktestResult（含 trades_per_week metric）
        ↓
  ReportGenerator           → trades.csv / summary.json / equity_curve.html
```

**核心原則：** `TimeSeriesEngine.set_time(ts)` 在每根 bar 前呼叫，確保 `get_bars()` 只回傳 `<= ts` 的資料，徹底防止 look-ahead bias。

---

## 前置需求

### Python 套件

```bash
pip install ccxt pandas pyarrow plotly tqdm rich
```

| 套件 | 用途 |
|------|------|
| ccxt | K 線下載 + Funding Rate 下載（Binance） |
| pandas + pyarrow | DataFrame + Parquet 快取 |
| plotly | equity_curve.html |
| tqdm | 進度條 |
| rich | Trade Replayer 表格輸出（可選） |

### 路徑結構

路徑由各模組自動解析，環境變數優先，fallback 到相對路徑：

```python
def _resolve_bot_root() -> Path:
    env = os.environ.get("TRADING_BOT_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent.parent / "projects" / "trading_bot"
```

| 環境變數 | 預設值 | 用途 |
|---------|-------|------|
| `TRADING_BOT_ROOT` | `Claude.ai/projects/trading_bot` | trading bot 根目錄；要測 feat-grid 可指到 `.worktrees/feat-grid` |
| `BACKTEST_CACHE_DIR` | `tools/Backtesting/cache` | Parquet 快取目錄 |

確保 `tools/Backtesting/` 在 `Claude.ai/tools/` 下，且 `projects/trading_bot/` 在 `Claude.ai/projects/` 下即可（若不改環境變數）。

---

## 目錄結構

```
tools/Backtesting/
├── data_loader.py          # K 線下載 + Parquet 快取（支援 BACKTEST_CACHE_DIR env）
├── funding_loader.py       # Funding Rate 下載 + Parquet 快取
├── time_series_engine.py   # 時間推進引擎（防 look-ahead）
├── mock_components.py      # MockDataProvider + MockOrderEngine（含 deduct_funding）
├── backtest_bot.py         # TradingBot runtime 工廠函式（patch + inject）
├── backtest_engine.py      # 主迴圈 + CLI + run_single() API + _backtest_context CM
├── report_generator.py     # 報表輸出（CSV / JSON / HTML）
├── trade_replayer.py       # 歷史交易重播 + CLI
├── pull_db.sh              # 從 rwUbuntu 拉 v6_performance.db
├── cache/                  # Parquet 快取（自動建立）
│   ├── BTCUSDT_1h_....parquet
│   └── BTCUSDT_funding_....parquet
├── tests/
│   ├── test_time_series_engine.py   (6 tests)
│   ├── test_mock_components.py      (9 tests)
│   ├── test_backtest_bot.py         (3 tests)
│   ├── test_backtest_engine.py      (8 tests)
│   ├── test_report_generator.py     (3 tests)
│   ├── test_trade_replayer.py       (3 tests)
│   ├── test_strategy_selection.py   (5 tests)
│   ├── test_datetime_patch.py       (2 tests)  ← datetime patch 覆蓋驗證
│   ├── test_funding_rate.py         (4 tests)  ← FundingLoader + deduct_funding
│   ├── test_patch_contract.py       (10 tests) ← interface contract（防 patch 點靜默失效）
│   └── test_paths.py                (2 tests)  ← env var 路徑解析
└── docs/
    └── plans/
        ├── 2026-02-28-backtesting-phase2-4.md
        ├── 2026-02-28-backtesting-phase2-4-design.md
        ├── 2026-02-28-strategy-selection.md
        ├── 2026-02-28-strategy-selection-design.md
        └── 2026-03-23-backtest-hardening.md     ← datetime fix + funding + contract + paths
```

---

## 快速開始

### 1. 回測

```bash
cd /c/Users/user/Documents/Claude.ai

# 單一標的（預設 live 策略）
python tools/Backtesting/backtest_engine.py \
  --symbols BTC/USDT \
  --start 2026-01-01 \
  --end 2026-02-28 \
  --balance 10000

# 指定出場策略
python tools/Backtesting/backtest_engine.py \
  --symbols SOL/USDT \
  --start 2026-01-01 \
  --end 2026-02-28 \
  --strategy v54    # 全部走 V54NoScale 出場

python tools/Backtesting/backtest_engine.py \
  --symbols SOL/USDT \
  --start 2026-01-01 \
  --end 2026-02-28 \
  --strategy v53    # 全部走 V53SopStrategy 出場

# 多標的
python tools/Backtesting/backtest_engine.py \
  --symbols BTC/USDT ETH/USDT SOL/USDT \
  --start 2026-01-01 \
  --end 2026-02-28 \
  --strategy v6 \
  --output my_results
```

輸出在 `tools/Backtesting/results/`（或 `--output` 指定目錄）：
- `trades.csv` — 每筆交易明細
- `summary.json` — 績效摘要
- `equity_curve.html` — 互動式 Plotly 圖表

### 2. Trade Replayer

```bash
# 從 rwUbuntu 拉取 DB
bash tools/Backtesting/pull_db.sh

# 重播最近 10 筆
python tools/Backtesting/trade_replayer.py \
  --db tools/Backtesting/v6_performance.db \
  --limit 10

# 重播特定交易 + what_if 參數測試
python tools/Backtesting/trade_replayer.py \
  --db tools/Backtesting/v6_performance.db \
  --trade-id abc123 \
  --what_if MIN_MFE_R_FOR_PULLBACK=0.5
```

### 3. 執行測試

```bash
cd /c/Users/user/Documents/Claude.ai
python -m pytest tools/Backtesting/tests/ -v
# 預期：60/60 passed
```

---

## 策略選擇

回測支援 `--strategy` 參數，選擇哪個**出場策略**套用到所有交易：

| 參數 | 出場策略 | 說明 |
|------|---------|------|
| `live`（預設） | 依目標 bot tree / `bot_config.json` | 維持 live bot 行為；main 與 feat-grid 可能不同 |
| `v54` | V54NoScaleStrategy | 所有信號強制走 V54 純移損 |
| `v7` | V7StructureStrategy + V53 fallback | 2B 強制走 V7；EMA/VB 走 V53 |
| `v6` | V6PyramidStrategy | 所有信號強制走 3 段滾倉（結構追蹤 + 獲利回吐保護） |
| `v53` | V53SopStrategy | 所有信號強制走 1R/1.5R/2.0R SOP |

> **進場邏輯不變**：所有模式都跑相同的 `scan_for_signals()`（2B / EMA Pullback / Volume Breakout）。差別只在出場。

### 設計原理

`STRATEGY_PRESETS` 是 `strategy_map` dict，映射 signal type → 出場策略名稱：

```python
STRATEGY_PRESETS = {
    "live": None,
    "v54": {"2B": "v54", "EMA_PULLBACK": "v54", "VOLUME_BREAKOUT": "v54"},
    "v7":  {"2B": "v7",  "EMA_PULLBACK": "v53", "VOLUME_BREAKOUT": "v53"},
    "v6":  {"2B": "v6",  "EMA_PULLBACK": "v6",  "VOLUME_BREAKOUT": "v6"},
    "v53": {"2B": "v53", "EMA_PULLBACK": "v53", "VOLUME_BREAKOUT": "v53"},
}
```

每根 bar `scan_for_signals()` 之後，`_apply_strategy_map()` 根據 `strategy_map` 覆寫 `pm.strategy_name`，讓 `monitor_positions()` 走正確的策略出場路徑。`pm_registry`（keyed by `trade_id`）記錄每個 PM 的**原始** exit strategy，避免多 bar 重設覆寫污染。

### 新增自訂策略

1. 在 `trader/strategies/` 實作新策略（繼承 `TradingStrategy`）
2. 在 `STRATEGY_PRESETS` 加新 key：
   ```python
   "v7": {"2B": "v7", "EMA_PULLBACK": "v53", "VOLUME_BREAKOUT": "v53"},
   ```
3. 新增 CLI choice 會自動生效（`choices=list(STRATEGY_PRESETS.keys())`）

### 報表欄位

- `summary.json` 新增 `strategy` 欄位
- `trades.csv` 新增 `exit_strategy` 欄（每筆交易實際使用的出場策略）
- `equity_curve.html` 標題加入 strategy 名稱

---

## 模組說明

### `data_loader.py` — BacktestDataLoader

從 Binance 下載 OHLCV，自動存 Parquet 快取。

```python
from data_loader import BacktestDataLoader

loader = BacktestDataLoader()
df = loader.get_data("BTC/USDT", "1h", "2026-01-01", "2026-02-28")
# Returns: DataFrame, index=UTC DatetimeIndex, columns=[open,high,low,close,volume]
```

- 快取目錄：預設 `cache/`，可用 `BACKTEST_CACHE_DIR` 環境變數覆蓋
- 快取命名：`BTCUSDT_1h_20260101_20260228.parquet`
- 批次下載（每批 1500 根），rate limit 友善（0.5s sleep）

---

### `funding_loader.py` — FundingLoader

從 Binance 下載歷史 funding rate（Futures），自動存 Parquet 快取。

```python
from funding_loader import FundingLoader

loader = FundingLoader()
rates = loader.get_funding_rates("BTC/USDT", "2026-01-01", "2026-02-28")
# Returns: pd.Series, index=UTC DatetimeIndex, values=funding_rate
# 每 8 小時一筆（00:00 / 08:00 / 16:00 UTC）
```

- 快取命名：`BTCUSDT_funding_20260101_20260228.parquet`
- 批次下載（每批 1000 筆），batch 間 `sleep(0.5)`，失敗 `sleep(5)` retry
- `BacktestEngine._load_data()` 自動為每個 symbol 載入並存入 `data[sym]["funding"]`

---

### `time_series_engine.py` — TimeSeriesEngine

回測核心：控制時間視窗，防 look-ahead bias。

```python
from time_series_engine import TimeSeriesEngine

tse = TimeSeriesEngine({
    "BTC/USDT": {
        "1h": df_1h,   # index=UTC DatetimeIndex
        "4h": df_4h,
    }
})

# 設定當前時間（必須在 get_bars 之前呼叫）
tse.set_time(timestamp)

# 只回傳 <= current_time 的最後 N 根
bars = tse.get_bars("BTC/USDT", "1h", limit=100)

# 當前 bar close price
price = tse.get_current_price("BTC/USDT")

# 取所有 symbol 共同的 1H timestamps（交集，已排序）
ts_list = tse.get_1h_timestamps(["BTC/USDT", "ETH/USDT"])
```

> 未呼叫 `set_time()` 就呼叫 `get_bars()` → 拋出 `RuntimeError`（防止靜默 look-ahead）

---

### `mock_components.py` — MockDataProvider / MockOrderEngine

替換 bot 的真實 I/O 元件。

#### MockDataProvider

```python
from mock_components import MockDataProvider

provider = MockDataProvider(tse)
df = provider.fetch_ohlcv("BTC/USDT", "1h", limit=100)
# 回傳格式與 MarketDataProvider 完全一致：timestamp 為 column（非 index），UTC-naive
```

#### MockOrderEngine

```python
from mock_components import MockOrderEngine

engine = MockOrderEngine(tse, fee_rate=0.0004, initial_balance=10000.0)

# 下單（回傳 Binance 格式）
result = engine.create_order("BTC/USDT", "BUY", 0.1)
# {"orderId": ..., "avgPrice": 40000.0, "status": "FILLED", "executedQty": "0.1"}

# 止損單
order_id = engine.place_hard_stop_loss("BTC/USDT", "LONG", 0.1, stop_price=39000.0)
engine.cancel_stop_loss_order("BTC/USDT", order_id)
engine.update_hard_stop_loss(pm, new_stop=39500.0)

# 每 bar 檢查止損觸發（BacktestEngine 負責呼叫）
triggered_symbols = engine.check_stop_triggers()

# Funding rate 結算（BacktestEngine 每 8H 呼叫）
engine.deduct_funding("BTC/USDT", "LONG", 0.1, 100000.0, 0.0001)
# fee = size * entry_price * rate（LONG 付錢，SHORT 收錢）

# 累計費用（含交易手續費 + funding fee）
print(engine.total_fees)
```

止損觸發邏輯：
- LONG：`bar.low <= stop_price` → 觸發
- SHORT：`bar.high >= stop_price` → 觸發

Funding fee 邏輯：
```
LONG:  fee = size * entry_price * rate       (rate > 0 → 付錢, rate < 0 → 收錢)
SHORT: fee = size * entry_price * (-rate)    (相反)
```

---

### `backtest_bot.py` — create_backtest_bot()

工廠函式，建立完全 mock 的 TradingBot runtime。

```python
from backtest_bot import create_backtest_bot

bot = create_backtest_bot(
    tse=tse,
    mock_engine=mock_engine,
    config_overrides={"SL_ATR_BUFFER": 1.5},  # 可選，會覆蓋 Config
)
```

內部執行的 patches：

| Patch 對象 | 替換為 |
|-----------|--------|
| `TradingBot._init_exchange` / `TradingBotV6._init_exchange` | `MagicMock()`（阻斷 ccxt 網路） |
| `PrecisionHandler._load_exchange_info` | no-op（阻斷 Binance HTTP） |
| `TradingBot._restore_positions` / `TradingBotV6._restore_positions` | no-op（不載入真實 positions.json） |
| `Config.POSITIONS_JSON_PATH` | tempfile |
| `Config.DB_PATH` | tempfile |

注入的元件：

| 屬性 | 注入內容 |
|------|---------|
| `bot.data_provider` | `MockDataProvider(tse)` |
| `bot.execution_engine` | `mock_engine` |
| `bot.exchange.fetch_ticker` | `lambda sym: {"last": tse.get_current_price(sym), ...}` |
| `bot.perf_db.record_trade` | `MagicMock()`（BacktestEngine 會覆寫為收集器） |
| `bot.persistence` | `MagicMock()` |
| `bot._sync_exchange_positions` | `MagicMock()` |
| `Config.USE_SCANNER_SYMBOLS` | `False` |
| `Config.V6_DRY_RUN` | `False`（讓 `_execute_trade` / `_handle_close` 走完整路徑） |
| `bot.risk_manager.get_balance` | `MagicMock(return_value=10000.0)`（阻斷 get_balance() 網路呼叫） |

---

### `backtest_engine.py` — BacktestEngine

主迴圈。每根 1H bar 執行：止損觸發 → 掃信號 → 監控持倉 → funding 結算 → 計算 equity。

提供兩層 API：
- **`run_single(verbose=False)`** — 純計算，回傳 `BacktestResult`，無 side effect（供 AutoTrader 等程式化呼叫）
- **`run()`** — CLI 入口，等同 `run_single(verbose=True)`

#### `_backtest_context` — Config/Datetime 隔離

Context manager，管理 Config 覆寫 + datetime monkey-patch。進入時套用，離開時還原，確保多次 `run_single()` 不互相污染。

**datetime patch 覆蓋的 4 個 modules：**

| Module | 為何需要 patch |
|--------|--------------|
| `trader.bot` | 冷卻計時（`datetime.now()` 比較 entry/cooldown） |
| `trader.positions` | `entry_time` 記錄 |
| `trader.signal_scanner` | cooldown / recently_exited / order_failed 計時 |
| `trader.position_monitor` | close/summary timestamp 與 `holding_hours` |
| `trader.strategies.legacy.v53_sop` or `trader.strategies.v53_sop` | `hours_held` 計算（`TIME_EXIT` 觸發） |
| `trader.strategies.legacy.v6_pyramid` or `trader.strategies.v6_pyramid` | `hours_held` 計算（`V6_STAGE1_MAX_HOURS` 觸發） |
| `trader.strategies.legacy.v7_structure` or `trader.strategies.v7_structure` | Stage 1 timeout / V7 lifecycle |
| `trader.strategies.v54_noscale` | feat-grid 主力策略的 `hours_held` / timeout |

> legacy `v53_sop` / `v6_pyramid` / `v7_structure` 與 feat-grid 的 `v54_noscale`、`signal_scanner`、`position_monitor` 都會直接吃 module-level `datetime`，漏 patch 會讓 `hours_held`、cooldown 或 summary timestamp 偏離模擬時間。

```python
from backtest_engine import BacktestConfig, BacktestEngine

cfg = BacktestConfig(
    symbols=["BTC/USDT", "ETH/USDT"],
    start="2026-01-01",
    end="2026-02-28",
    initial_balance=10000.0,   # USDT
    fee_rate=0.0004,           # 0.04% per trade
    warmup_bars=100,           # 前 N 根 bar 不執行策略（indicator 暖機）
    strategy="live",           # "live" | "v6" | "v53"
    config_overrides={},       # 覆蓋 Config 參數（回測結束後自動還原）
)

engine = BacktestEngine(cfg)

# 程式化呼叫（AutoTrader 用）
result = engine.run_single()          # 靜默，純回傳 BacktestResult

# CLI 呼叫（人工用）
result = engine.run()                 # 等同 run_single(verbose=True)

print(result.summary)
# {
#   "strategy": "live",       # 使用的出場策略
#   "total_trades": 15,
#   "win_rate": 0.6,
#   "profit_factor": 1.85,
#   "total_return_pct": 12.34,
#   "max_drawdown_pct": 5.67,
#   "sharpe": 1.42,           # 年化（1H resolution，sqrt(8760)）
#   "trades_per_week": 3.75,  # 交易頻率（AutoTrader 評分用）
# }

print(result.trades)         # List[dict]，來自 perf_db.record_trade
print(result.equity_curve)   # List[(pd.Timestamp, float)]
```

**Equity 計算公式：**
```
portfolio_value = initial_balance + gross_closed_pnl - total_fees + unrealized_pnl
```
`pnl_usdt` 來自 `perf_db.record_trade`，是 **GROSS**（未扣費）。`total_fees` 由 `MockOrderEngine` 獨立追蹤（交易手續費 + funding fee），不重複扣減。

---

### `report_generator.py` — ReportGenerator

```python
from report_generator import ReportGenerator
from pathlib import Path

ReportGenerator().generate(result, output_dir=Path("results"))
```

輸出：

| 檔案 | 內容 |
|------|------|
| `trades.csv` | 所有交易欄位，含 `exit_strategy`（每筆實際使用的出場策略）；無交易時輸出含標頭的空 CSV |
| `summary.json` | `strategy / total_trades / win_rate / profit_factor / total_return_pct / max_drawdown_pct / sharpe / trades_per_week` |
| `equity_curve.html` | Plotly dark theme 互動圖表，標題含 strategy 名稱 |

---

### `trade_replayer.py` — TradeReplayer

從本機 `v6_performance.db` 讀歷史交易，逐根 K 線重播 `PositionManager` 決策，比對 actual vs replayed exit。

```python
from trade_replayer import TradeReplayer

replayer = TradeReplayer(
    db_path="v6_performance.db",
    what_if={"MIN_MFE_R_FOR_PULLBACK": 0.5},  # 可選，Config 覆蓋（執行後自動還原）
)

# 載入交易
trades = replayer.load_trades(limit=20, symbol="BTC/USDT")

# 重播
results = [replayer.replay(t) for t in trades]

# 輸出表格
replayer.report(results)
```

`replay()` 回傳結構：

```python
{
    "trade_id": "abc123",
    "symbol": "BTC/USDT",
    "side": "LONG",
    "actual_exit_reason": "STRUCTURE_TRAIL",
    "actual_exit_price": 42000.0,
    "replayed_exit_reason": "PROFIT_PULLBACK",  # 若不同→黃色高亮
    "replayed_exit_price": 41800.0,             # None 表示重播超時未觸發出場
    "decisions": [
        {"time": "2026-01-15 12:00:00+00:00", "price": 40500.0,
         "action": "ACTIVE", "reason": None, "new_sl": None},
        ...
    ],
    "what_if": {"MIN_MFE_R_FOR_PULLBACK": 0.5},
}
```

**PositionManager 重建：**
- `stop_loss` 從 `trade["initial_r"]` 推導（`entry_price - initial_r` for LONG）
- 非 5% 硬碼，確保 `risk_dist` 正確 → Stage 2/3 觸發與 trailing 邏輯忠實重現

---

### `pull_db.sh` — 拉取 DB

```bash
bash tools/Backtesting/pull_db.sh
```

從 rwUbuntu 拉 `v6_performance.db` 到 `tools/Backtesting/v6_performance.db`。失敗立即退出（`set -e`）。

手動等效指令：
```bash
scp rwfunder@100.67.114.104:/home/rwfunder/文件/tradingbot/trading_bot_v6/v6_performance.db \
    tools/Backtesting/v6_performance.db
```

---

## CLI 參考

### backtest_engine.py

```
python tools/Backtesting/backtest_engine.py [options]

Options:
  --symbols    BTC/USDT ETH/USDT ...   標的列表（預設：BTC/USDT）
  --start      YYYY-MM-DD              開始日期（預設：2026-01-01）
  --end        YYYY-MM-DD              結束日期（預設：2026-02-28）
  --balance    float                   初始資金 USDT（預設：10000.0）
  --output     dir                     輸出目錄（預設：results，相對於腳本）
  --strategy   live|v54|v7|v6|v53      出場策略（預設：live）
```

### trade_replayer.py

```
python tools/Backtesting/trade_replayer.py [options]

Required:
  --db         path                    v6_performance.db 路徑

Options:
  --limit      int                     讀取筆數（預設：10）
  --symbol     str                     過濾 symbol（e.g. BTC/USDT）
  --trade-id   str                     重播指定 trade_id
  --what_if    KEY=VALUE ...           覆蓋 Config 參數

What_if 範例：
  --what_if MIN_MFE_R_FOR_PULLBACK=0.5 MIN_FAKEOUT_ATR=0.5
  --what_if V6_4H_EMA20_FORCE_EXIT=true
```

---

## 程式化使用

### 完整回測流程（CLI 風格）

```python
from backtest_engine import BacktestConfig, BacktestEngine
from report_generator import ReportGenerator
from pathlib import Path

cfg = BacktestConfig(
    symbols=["BTC/USDT"],
    start="2026-01-01",
    end="2026-02-28",
    initial_balance=10000.0,
    strategy="v53",
    config_overrides={"MIN_MFE_R_FOR_PULLBACK": 0.5},
)

result = BacktestEngine(cfg).run()
ReportGenerator().generate(result, Path("results"))
```

### 程式化呼叫（AutoTrader 用）

```python
from backtest_engine import BacktestConfig, BacktestEngine

cfg = BacktestConfig(
    symbols=["BTC/USDT", "ETH/USDT"],
    start="2021-01-01",
    end="2021-04-30",
    config_overrides={"SL_ATR_BUFFER": 0.6, "ADX_THRESHOLD": 20},
)

# run_single(): 靜默、無 side effect、純回傳 BacktestResult
result = BacktestEngine(cfg).run_single()

print(result.summary["trades_per_week"])  # AutoTrader 評分 gate
print(result.summary["profit_factor"])
print(result.summary["sharpe"])
```

### 客製化資料注入（不下載）

```python
import pandas as pd
from time_series_engine import TimeSeriesEngine
from mock_components import MockOrderEngine
from backtest_bot import create_backtest_bot

# 自備數據
df = pd.read_parquet("my_data.parquet")  # index=UTC DatetimeIndex

tse = TimeSeriesEngine({"BTC/USDT": {"1h": df, "4h": df}})
engine = MockOrderEngine(tse, fee_rate=0.0004)
bot = create_backtest_bot(tse, engine)

# 手動推進時間
for ts in df.index:
    tse.set_time(ts)
    bot.scan_for_signals()
    bot.monitor_positions()
```

---

## Multi-Window Backtest Standard

單一 window 很容易把 regime 偏差誤讀成策略 edge。任何要升級到 runtime 的 detector / filter / exit 變更，預設要跑 multi-window，比較重點放在相對變化，而不是只看某一段的絕對 PF。

### Baseline Matrix

基準 symbol 組合：

```text
BTC/USDT
ETH/USDT
SOL/USDT
BNB/USDT
XRP/USDT
DOGE/USDT
```

基準 period 組合 (Ruei 回填 2026-04-11，來自 BTC 4H RegimeEngine + avg BBW 回放)：

| period label | date range | BTC replay note |
|---|---|---|
| TRENDING up | `2023-10-01 -> 2024-03-31` | 強上升段 |
| TRENDING down | `2022-02-15 -> 2022-06-15` | BTC -50.8%; TRENDING 75.9%, trend dir SHORT 64.2%; 比 2025/26 的 recent bear 更乾淨 |
| RANGING | `2024-12-31 -> 2025-03-31` | BTC -11.9%; RANGING 51.8% / TRENDING 48.2% |
| SQUEEZE (low-vol proxy) | `2023-07-01 -> 2023-10-01` | RegimeEngine SQUEEZE 0% **但** avg BBW 較低；**標為 proxy，不是真正 RegimeEngine SQUEEZE** |
| mixed | `2025-02-01 -> 2025-08-31` | BTC +6.8%; TRENDING 59.3% / RANGING 40.7%; mixed / transition |
| recent 90d | `2026-01-06 -> 2026-04-06` | 最新 cache 90d; BTC -26.3%; TRENDING 68.4% / RANGING 31.6% |

**Caveat — SQUEEZE proxy**: `SQUEEZE (low-vol proxy)` 那格 **不是** 真正 RegimeEngine SQUEEZE。RegimeEngine 回放 BTC 4H 幾乎抓不到 SQUEEZE regime (大部分 period 為 0%)，所以這欄使用 avg BBW 較低的 2023 夏季區間作 proxy，目的是觀察 V54 在低波動環境的 shape，不要當成 "SQUEEZE regime gate test"。

**Caveat — cache coverage**: `tools/Backtesting/cache/` 目前缺 `BNBUSDT` / `XRPUSDT` 的 `1h` / `4h` / `1d` / `funding` parquet cache。跑 full 6 symbols × 6 periods matrix 前必須先補齊，覆蓋範圍 `2022-02-15` 到 `2026-04-06`。

### Gate Reading

- Prefer relative PF / Sharpe / max drawdown deltas against the matching baseline window.
- Use absolute floors only when an aggregate gate explicitly defines them.
- Treat signal-count shifts as first-class evidence, especially when cooldown or lane occupancy can distort trade attribution.
- Validate the actual runtime signal set directly; do not infer runtime performance from a richer research signal set.

### Case Study

`results/ema_weekend_review_20260411/ema_research_epilogue.md` 的 `Window selection bias` 段記錄了一次具體踩坑：EMA 研究長時間落在同一個 BTC bear / downtrend / ranging slice，導致 evidence 幾乎都是 SHORT-only。後續重開 EMA 或類似 detector 研究時，第一步應先修正/確認 review window 覆蓋，而不是直接調 detector。

---

## AutoTrader 整合

回測引擎是 AutoTrader（AI 自主參數優化）的底層。已完成 Phase 0 Round 1 基礎設施：

| 完成項目 | 說明 |
|---------|------|
| `run_single()` API | 純計算，無 side effect，供 AutoTrader 連續呼叫 |
| `_backtest_context` CM | Config + datetime patch 隔離（4 modules），多次 run 不互相污染 |
| `trades_per_week` metric | 交易頻率統計，AutoTrader 評分 gate 用 |
| Import path 對齊 | 全部用 `trader.*`，與主專案一致 |
| Funding rate 模擬 | `FundingLoader` + `MockOrderEngine.deduct_funding()`，equity 更精確 |

### Phase 0 Round 2（待做）

| 項目 | 說明 |
|------|------|
| `evaluator.py` | Gates + composite score（PF/Sharpe/DD/WR/Freq 加權） |
| `experiment_db.py` | SQLite CRUD，記錄實驗參數/分數/推理 |
| Regime data | 定義 bull/bear/sideways/lowvol 時間區間 + 下載 K-line cache |
| Baseline calibration | 用現有參數跑 baseline，校準 trade frequency gate |

> 詳見 `docs/superpowers/specs/2026-03-22-autotrader-design.md`

---

## Trade Replayer

Trade Replayer 的設計目的是**驗證出場邏輯**：給定一筆真實交易的進場條件，用當時的市場數據重跑 PositionManager，看出場原因是否與實際一致。

### 典型用途

**1. 驗證參數調整效果**
```bash
# 目前參數重播
python trade_replayer.py --db v6_performance.db --limit 20

# what_if：提高 MIN_MFE_R 門檻後，profit_pullback 觸發率是否下降？
python trade_replayer.py --db v6_performance.db --limit 20 \
  --what_if MIN_MFE_R_FOR_PULLBACK=0.5
```

**2. 診斷特定交易**
```bash
# 看某筆交易每根 bar 的決策過程
python trade_replayer.py --db v6_performance.db --trade-id <trade_id>
```

**3. 輸出解讀**

| 顏色 | 意思 |
|------|------|
| 綠色 | actual_exit_reason == replayed_exit_reason（完全一致） |
| 黃色 | 出場原因不同（可能是 SL 位移、參數差異） |
| `replayed_exit_price = None` | 重播超時未觸發出場（`timeout_in_replay`） |

### 限制

- `stop_loss` 從 `initial_r` 推導（近似值）。若實際持倉在 Stage 2/3 時 SL 已移動，重播起點的 SL 與實際可能有落差。
- 重播從 entry_time 所在 bar 開始，不含進場前的 indicator 暖機。bars < 10 時跳過 `pm.monitor()`。

---

## 設計決策

### 為何 Composition + Patch，不繼承？

直接繼承 TradingBot runtime 會讓回測耦合 bot 內部實作。用 `unittest.mock.patch` 替換具體元件（data_provider、execution_engine），bot 的 `scan_for_signals()` / `monitor_positions()` / `_handle_close()` 等核心邏輯完全不動，最大化 fidelity。

### 為何 TimeSeriesEngine？

直接操作 DataFrame 的 iloc 也能實作，但容易不小心 slice 到未來的 bar（look-ahead bias）。TimeSeriesEngine 提供明確的 API 邊界：只有 `set_time()` 呼叫後，`get_bars()` 才回傳對應時間點的資料，從根本消除這個風險。

### datetime patch 為何需要 4 個 modules？

`bot.py` 和 `positions.py` 之外，feat-grid 拆出的 `signal_scanner.py`、`position_monitor.py`、`grid_manager.py`、`utils.py`，以及 `v54_noscale.py` / legacy strategies 也都可能直接用到 `datetime.now()`。因此 `_backtest_context()` 會一次 patch current + legacy modules；若漏掉，`hours_held`、cooldown、`CYCLE_SUMMARY` 時間戳都會回到真實時鐘。`test_patch_contract.py` 會 AST 掃描 trader/ 確保所有 `datetime.now()` 呼叫都在 patch 清單中。

### pnl_usdt 是 GROSS 還是 NET？

`perf_db.record_trade` 的 `pnl_usdt` 是 **GROSS**（未扣手續費）。這是 bot 原始計算方式（`_handle_close`：`pnl_usdt = pm.total_size * (exit_price - avg_entry)`）。`MockOrderEngine.total_fees` 獨立累計所有 entry + exit 手續費和 funding fee。兩者分開避免重複扣減。

### Sharpe 年化因子

Equity curve 是 1H resolution，所以每個 return 是小時報酬。年化需乘 `sqrt(24 × 365) = sqrt(8760)` ≈ 93.6，而非 `sqrt(24)`。

---

## 已知限制

1. **成交模型簡化**：以 current bar close price 成交，無 slippage 模型。真實市價單有滑點，尤其 Stage 2/3 加倉。
2. **Stop 觸發近似**：`check_stop_triggers()` 用 bar close 作為成交價（實際 SL 以 stop price 成交）。影響 pnl 計算的精確度。
3. **多標的並行限制**：BacktestEngine 按 1H bar 串行處理所有 symbol，不模擬真實 bot 的 asyncio 並發。
4. **4H EMA20 force exit 暫停**：`V6_4H_EMA20_FORCE_EXIT=False`（bot 主線），回測也沿用此設定。
5. **Parquet 快取 key 包含日期**：回測相同 symbol 但不同日期範圍時，舊快取不會自動合併，需手動管理 `cache/` 目錄。
6. **Funding rate 精確度**：以 1H bar 時間戳對 `funding_series.index` 做精確 match（需 timestamp 完全對齊）。若 Binance 回傳的 timestamp 有秒級誤差，當根 bar 不會結算。

---

## 執行測試

```bash
cd /c/Users/user/Documents/Claude.ai

# 全部測試
python -m pytest tools/Backtesting/tests/ -v

# 單一模組
python -m pytest tools/Backtesting/tests/test_backtest_engine.py -v

# 含覆蓋率
python -m pytest tools/Backtesting/tests/ --cov=tools/Backtesting --cov-report=term-missing
```

| 測試檔 | 測試數 | 涵蓋範圍 |
|--------|--------|---------|
| test_time_series_engine.py | 6 | look-ahead 防護、limit、get_current_price、intersection |
| test_mock_components.py | 9 | 格式對齊、fee deduction、stop 觸發邏輯 |
| test_backtest_bot.py | 3 | 無網路建立、data_provider/execution_engine 注入 |
| test_backtest_engine.py | 8 | smoke test、Config 還原、trades_per_week、run_single API |
| test_report_generator.py | 3 | 三個輸出檔、欄位、summary keys |
| test_trade_replayer.py | 3 | load_trades、symbol filter、replay 結構 |
| test_strategy_selection.py | 8 | v54 / v7 / v6 / v53 override、registry 原始值、registry 冪等 |
| test_datetime_patch.py | 2 | strategy modules 使用模擬時間、離開 context 後還原 |
| test_funding_rate.py | 4 | cache hit、download rate limit、LONG/SHORT fee 方向 |
| test_patch_contract.py | 10 | patch 目標存在、inject 屬性存在、datetime.now() 全覆蓋掃描 |
| test_paths.py | 2 | env var 優先、fallback 相對路徑 |

**合計：60/60 passed**
