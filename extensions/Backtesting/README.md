# Trading Bot ?葫憭?

Trading Bot ?蝡?皜砍極?瑯?*?嗡耨??* `projects/trading_bot/trader/` ??摰?? patch + inject ?撘? bot ?雯頝?I/O ?踵????mock嚗??祕蝑?摩?冽風?脫???瑁???

---

## ?桅?

- [?嗆?璁汗](#?嗆?璁汗)
- [?蔭?瘙(#?蔭?瘙?
- [?桅?蝯?](#?桅?蝯?)
- [敹恍?憪(#敹恍?憪?
- [蝑?豢?](#蝑?豢?)
- [璅∠?隤芣?](#璅∠?隤芣?)
- [CLI ?(#cli-??
- [蝔??蝙?沘(#蝔??蝙??
- [Multi-Window Backtest Standard](#multi-window-backtest-standard)
- [AutoTrader ?游?](#autotrader-?游?)
- [Trade Replayer](#trade-replayer)
- [閮剛?瘙箇?](#閮剛?瘙箇?)
- [撌脩?](#撌脩?)
- [?瑁?皜祈岫](#?瑁?皜祈岫)

---

## ?嗆?璁汗

```
甇瑕 K 蝺?(Binance API / Parquet 敹怠?)
        ??
  BacktestDataLoader  ?? FundingLoader嚗unding rate Parquet 敹怠?嚗?
        ??
  TimeSeriesEngine          ????閬??批嚗 look-ahead bias嚗?
        ??             ??
MockDataProvider    MockOrderEngine
                       ?? deduct_funding()  ??funding rate 蝯?
                       ?? check_stop_triggers()
        ??             ??
   create_backtest_bot()   ??patch TradingBot runtime嚗? patches + 7 injections嚗?
        ??
  _backtest_context()       ??Context Manager嚗onfig + datetime patch嚗???current/legacy modules嚗?
        ??
  BacktestEngine            ??銝餉艘??per 1H bar嚗?
   ?? run_single()          ??蝝?蝞?API嚗? AutoTrader 蝔???恬?
   ??  ?? check_stop_triggers()
   ??  ?? scan_for_signals()    ???祕?脣?摩嚗?B / EMA Pullback / Volume Breakout嚗?
   ??  ?? _apply_strategy_map() ??蝑閬神嚗54 / v7 / v6 / v53 / live嚗?
   ??  ?? monitor_positions()   ???祕?箏?摩嚗蝑瘙箏?嚗?
   ??  ?? funding rate 蝯?     ??瘥?8H嚗?0:00 / 08:00 / 16:00 UTC嚗?
   ??  ?? equity_curve 閮?
   ?? run()                 ??CLI ?亙嚗? run_single(verbose=True)嚗?
        ??
  BacktestResult嚗 trades_per_week metric嚗?
        ??
  ReportGenerator           ??trades.csv / summary.json / equity_curve.html
```

**?詨???嚗?* `TimeSeriesEngine.set_time(ts)` ?冽???bar ??恬?蝣箔? `get_bars()` ?芸???`<= ts` ????敺孵??脫迫 look-ahead bias??

---

## ?蔭?瘙?

### Python 憟辣

```bash
pip install ccxt pandas pyarrow plotly tqdm rich
```

| 憟辣 | ?券?|
|------|------|
| ccxt | K 蝺?頛?+ Funding Rate 銝?嚗inance嚗?|
| pandas + pyarrow | DataFrame + Parquet 敹怠? |
| plotly | equity_curve.html |
| tqdm | ?脣漲璇?|
| rich | Trade Replayer 銵冽頛詨嚗?賂? |

### 頝臬?蝯?

頝臬??勗?璅∠??芸?閫??嚗憓??詨??fallback ?啁撠楝敺?

```python
def _resolve_bot_root() -> Path:
    env = os.environ.get("TRADING_BOT_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent.parent / "projects" / "trading_bot"
```

| ?啣?霈 | ?身??| ?券?|
|---------|-------|------|
| `TRADING_BOT_ROOT` | `Claude.ai/projects/trading_bot` | trading bot ?寧??閬葫 feat-grid ?舀???`.worktrees/feat-grid` |
| `BACKTEST_CACHE_DIR` | `tools/Backtesting/cache` | Parquet 敹怠??桅? |

蝣箔? `tools/Backtesting/` ??`Claude.ai/tools/` 銝?銝?`projects/trading_bot/` ??`Claude.ai/projects/` 銝?荔??乩??寧憓??賂???

---

## ?桅?蝯?

```
tools/Backtesting/
??? data_loader.py          # K 蝺?頛?+ Parquet 敹怠?嚗??BACKTEST_CACHE_DIR env嚗?
??? funding_loader.py       # Funding Rate 銝? + Parquet 敹怠?
??? time_series_engine.py   # ???券脣?????look-ahead嚗?
??? mock_components.py      # MockDataProvider + MockOrderEngine嚗 deduct_funding嚗?
??? backtest_bot.py         # TradingBot runtime 撌亙??賢?嚗atch + inject嚗?
??? backtest_engine.py      # 銝餉艘??+ CLI + run_single() API + _backtest_context CM
??? report_generator.py     # ?梯”頛詨嚗SV / JSON / HTML嚗?
??? trade_replayer.py       # 甇瑕鈭斗?? + CLI
??? pull_db.sh              # 敺?rwUbuntu ??v6_performance.db
??? cache/                  # Parquet 敹怠?嚗?遣蝡?
??  ??? BTCUSDT_1h_....parquet
??  ??? BTCUSDT_funding_....parquet
??? tests/
??  ??? test_time_series_engine.py   (6 tests)
??  ??? test_mock_components.py      (9 tests)
??  ??? test_backtest_bot.py         (3 tests)
??  ??? test_backtest_engine.py      (8 tests)
??  ??? test_report_generator.py     (3 tests)
??  ??? test_trade_replayer.py       (3 tests)
??  ??? test_strategy_selection.py   (5 tests)
??  ??? test_datetime_patch.py       (2 tests)  ??datetime patch 閬?撽?
??  ??? test_funding_rate.py         (4 tests)  ??FundingLoader + deduct_funding
??  ??? test_patch_contract.py       (10 tests) ??interface contract嚗 patch 暺?暺仃??
??  ??? test_paths.py                (2 tests)  ??env var 頝臬?閫??
??? docs/
    ??? plans/
        ??? 2026-02-28-backtesting-phase2-4.md
        ??? 2026-02-28-backtesting-phase2-4-design.md
        ??? 2026-02-28-strategy-selection.md
        ??? 2026-02-28-strategy-selection-design.md
        ??? 2026-03-23-backtest-hardening.md     ??datetime fix + funding + contract + paths
```

---

## 敹恍?憪?

### 1. ?葫

```bash
cd /c/Users/user/Documents/Claude.ai

# ?桐?璅?嚗?閮?live 蝑嚗?
python tools/Backtesting/backtest_engine.py \
  --symbols BTC/USDT \
  --start 2026-01-01 \
  --end 2026-02-28 \
  --balance 10000

# ???箏蝑
python tools/Backtesting/backtest_engine.py \
  --symbols SOL/USDT \
  --start 2026-01-01 \
  --end 2026-02-28 \
  --strategy v54    # ?券韏?V54NoScale ?箏

python tools/Backtesting/backtest_engine.py \
  --symbols SOL/USDT \
  --start 2026-01-01 \
  --end 2026-02-28 \
  --strategy v53    # ?券韏?V53SopStrategy ?箏

# 憭???
python tools/Backtesting/backtest_engine.py \
  --symbols BTC/USDT ETH/USDT SOL/USDT \
  --start 2026-01-01 \
  --end 2026-02-28 \
  --strategy v6 \
  --output my_results
```

頛詨??`tools/Backtesting/results/`嚗? `--output` ???桅?嚗?
- `trades.csv` ??瘥?鈭斗??敦
- `summary.json` ??蝮暹???
- `equity_curve.html` ??鈭?撘?Plotly ?”

### 2. Trade Replayer

```bash
# 敺?rwUbuntu ?? DB
bash tools/Backtesting/pull_db.sh

# ??餈?10 蝑?
python tools/Backtesting/trade_replayer.py \
  --db tools/Backtesting/v6_performance.db \
  --limit 10

# ??孵?鈭斗? + what_if ?皜祈岫
python tools/Backtesting/trade_replayer.py \
  --db tools/Backtesting/v6_performance.db \
  --trade-id abc123 \
  --what_if MIN_MFE_R_FOR_PULLBACK=0.5
```

### 3. ?瑁?皜祈岫

```bash
cd /c/Users/user/Documents/Claude.ai
python -m pytest tools/Backtesting/tests/ -v
# ??嚗?0/60 passed
```

---

## 蝑?豢?

?葫?舀 `--strategy` ?嚗???*?箏蝑**憟?唳??漱??

| ? | ?箏蝑 | 隤芣? |
|------|---------|------|
| `live`嚗?閮哨? | `trader/config.py` defaults | 蝬剜? live bot 銵嚗ain ??feat-grid ?航銝? |
| `v54` | V54NoScaleStrategy | ??縑?撥?嗉粥 V54 蝝宏??|
| `v7` | V7StructureStrategy + V53 fallback | 2B 撘瑕韏?V7嚗MA/VB 韏?V53 |
| `v6` | V6PyramidStrategy | ??縑?撥?嗉粥 3 畾菜遝??蝯?餈質馱 + ?脣??靽風嚗?|
| `v53` | V53SopStrategy | ??縑?撥?嗉粥 1R/1.5R/2.0R SOP |

> **?脣?摩銝?**嚗??芋撘頝?? `scan_for_signals()`嚗?B / EMA Pullback / Volume Breakout嚗榆?亙?典?氬?

### 閮剛???

`STRATEGY_PRESETS` ??`strategy_map` dict嚗?撠?signal type ???箏蝑?迂嚗?

```python
STRATEGY_PRESETS = {
    "live": None,
    "v54": {"2B": "v54", "EMA_PULLBACK": "v54", "VOLUME_BREAKOUT": "v54"},
    "v7":  {"2B": "v7",  "EMA_PULLBACK": "v53", "VOLUME_BREAKOUT": "v53"},
    "v6":  {"2B": "v6",  "EMA_PULLBACK": "v6",  "VOLUME_BREAKOUT": "v6"},
    "v53": {"2B": "v53", "EMA_PULLBACK": "v53", "VOLUME_BREAKOUT": "v53"},
}
```

瘥 bar `scan_for_signals()` 銋?嚗_apply_strategy_map()` ?寞? `strategy_map` 閬神 `pm.strategy_name`嚗? `monitor_positions()` 韏唳迤蝣箇?蝑?箏頝臬??pm_registry`嚗eyed by `trade_id`嚗?????PM ??*??** exit strategy嚗?? bar ?身閬神瘙⊥???

### ?啣??芾?蝑

1. ??`trader/strategies/` 撖虫??啁??伐?蝜潭 `TradingStrategy`嚗?
2. ??`STRATEGY_PRESETS` ? key嚗?
   ```python
   "v7": {"2B": "v7", "EMA_PULLBACK": "v53", "VOLUME_BREAKOUT": "v53"},
   ```
3. ?啣? CLI choice ?????`choices=list(STRATEGY_PRESETS.keys())`嚗?

### ?梯”甈?

- `summary.json` ?啣? `strategy` 甈?
- `trades.csv` ?啣? `exit_strategy` 甈?瘥?鈭斗?撖阡?雿輻??渡??伐?
- `equity_curve.html` 璅?? strategy ?迂

---

## 璅∠?隤芣?

### `data_loader.py` ??BacktestDataLoader

敺?Binance 銝? OHLCV嚗?? Parquet 敹怠???

```python
from data_loader import BacktestDataLoader

loader = BacktestDataLoader()
df = loader.get_data("BTC/USDT", "1h", "2026-01-01", "2026-02-28")
# Returns: DataFrame, index=UTC DatetimeIndex, columns=[open,high,low,close,volume]
```

- 敹怠??桅?嚗?閮?`cache/`嚗??`BACKTEST_CACHE_DIR` ?啣?霈閬?
- 敹怠??賢?嚗BTCUSDT_1h_20260101_20260228.parquet`
- ?寞活銝?嚗???1500 ?對?嚗ate limit ??嚗?.5s sleep嚗?

---

### `funding_loader.py` ??FundingLoader

敺?Binance 銝?甇瑕 funding rate嚗utures嚗??芸?摮?Parquet 敹怠???

```python
from funding_loader import FundingLoader

loader = FundingLoader()
rates = loader.get_funding_rates("BTC/USDT", "2026-01-01", "2026-02-28")
# Returns: pd.Series, index=UTC DatetimeIndex, values=funding_rate
# 瘥?8 撠?銝蝑?00:00 / 08:00 / 16:00 UTC嚗?
```

- 敹怠??賢?嚗BTCUSDT_funding_20260101_20260228.parquet`
- ?寞活銝?嚗???1000 蝑?嚗atch ??`sleep(0.5)`嚗仃??`sleep(5)` retry
- `BacktestEngine._load_data()` ?芸??箸???symbol 頛銝血???`data[sym]["funding"]`

---

### `time_series_engine.py` ??TimeSeriesEngine

?葫?詨?嚗?嗆???蝒???look-ahead bias??

```python
from time_series_engine import TimeSeriesEngine

tse = TimeSeriesEngine({
    "BTC/USDT": {
        "1h": df_1h,   # index=UTC DatetimeIndex
        "4h": df_4h,
    }
})

# 閮剖??嗅???嚗?? get_bars 銋??澆嚗?
tse.set_time(timestamp)

# ?芸???<= current_time ??敺?N ??
bars = tse.get_bars("BTC/USDT", "1h", limit=100)

# ?嗅? bar close price
price = tse.get_current_price("BTC/USDT")

# ????symbol ?勗???1H timestamps嚗漱??撌脫?摨?
ts_list = tse.get_1h_timestamps(["BTC/USDT", "ETH/USDT"])
```

> ?芸??`set_time()` 撠勗??`get_bars()` ??? `RuntimeError`嚗甇ａ?暺?look-ahead嚗?

---

### `mock_components.py` ??MockDataProvider / MockOrderEngine

?踵? bot ??撖?I/O ?辣??

#### MockDataProvider

```python
from mock_components import MockDataProvider

provider = MockDataProvider(tse)
df = provider.fetch_ohlcv("BTC/USDT", "1h", limit=100)
# ??澆???MarketDataProvider 摰銝?湛?timestamp ??column嚗? index嚗?UTC-naive
```

#### MockOrderEngine

```python
from mock_components import MockOrderEngine

engine = MockOrderEngine(tse, fee_rate=0.0004, initial_balance=10000.0)

# 銝嚗???Binance ?澆?嚗?
result = engine.create_order("BTC/USDT", "BUY", 0.1)
# {"orderId": ..., "avgPrice": 40000.0, "status": "FILLED", "executedQty": "0.1"}

# 甇Ｘ???
order_id = engine.place_hard_stop_loss("BTC/USDT", "LONG", 0.1, stop_price=39000.0)
engine.cancel_stop_loss_order("BTC/USDT", order_id)
engine.update_hard_stop_loss(pm, new_stop=39500.0)

# 瘥?bar 瑼Ｘ甇Ｘ?閫貊嚗acktestEngine 鞎痊?澆嚗?
triggered_symbols = engine.check_stop_triggers()

# Funding rate 蝯?嚗acktestEngine 瘥?8H ?澆嚗?
engine.deduct_funding("BTC/USDT", "LONG", 0.1, 100000.0, 0.0001)
# fee = size * entry_price * rate嚗ONG 隞嚗HORT ?園嚗?

# 蝝航?鞎餌嚗鈭斗???鞎?+ funding fee嚗?
print(engine.total_fees)
```

甇Ｘ?閫貊?摩嚗?
- LONG嚗bar.low <= stop_price` ??閫貊
- SHORT嚗bar.high >= stop_price` ??閫貊

Funding fee ?摩嚗?
```
LONG:  fee = size * entry_price * rate       (rate > 0 ??隞, rate < 0 ???園)
SHORT: fee = size * entry_price * (-rate)    (?詨?)
```

---

### `backtest_bot.py` ??create_backtest_bot()

撌亙??賢?嚗遣蝡???mock ??TradingBot runtime??

```python
from backtest_bot import create_backtest_bot

bot = create_backtest_bot(
    tse=tse,
    mock_engine=mock_engine,
    config_overrides={"SL_ATR_BUFFER": 1.5},  # ?舫嚗?閬? Config
)
```

?折?瑁???patches嚗?

| Patch 撠情 | ?踵???|
|-----------|--------|
| `TradingBot._init_exchange` / `TradingBotV6._init_exchange` | `MagicMock()`嚗??ccxt 蝬脰楝嚗?|
| `PrecisionHandler._load_exchange_info` | no-op嚗??Binance HTTP嚗?|
| `TradingBot._restore_positions` / `TradingBotV6._restore_positions` | no-op嚗?頛?祕 positions.json嚗?|
| `Config.POSITIONS_JSON_PATH` | tempfile |
| `Config.DB_PATH` | tempfile |

瘜典??隞塚?

| 撅祆?| 瘜典?批捆 |
|------|---------|
| `bot.data_provider` | `MockDataProvider(tse)` |
| `bot.execution_engine` | `mock_engine` |
| `bot.exchange.fetch_ticker` | `lambda sym: {"last": tse.get_current_price(sym), ...}` |
| `bot.perf_db.record_trade` | `MagicMock()`嚗acktestEngine ??撖怎?園??剁? |
| `bot.persistence` | `MagicMock()` |
| `bot._sync_exchange_positions` | `MagicMock()` |
| `Config.USE_SCANNER_SYMBOLS` | `False` |
| `Config.DRY_RUN` | `False`嚗? `_execute_trade` / `_handle_close` 韏啣??渲楝敺? |
| `bot.risk_manager.get_balance` | `MagicMock(return_value=10000.0)`嚗??get_balance() 蝬脰楝?澆嚗?|

---

### `backtest_engine.py` ??BacktestEngine

銝餉艘????1H bar ?瑁?嚗迫?孛?????縑??????????funding 蝯? ??閮? equity??

???拙惜 API嚗?
- **`run_single(verbose=False)`** ??蝝?蝞?? `BacktestResult`嚗 side effect嚗? AutoTrader 蝑?撘??澆嚗?
- **`run()`** ??CLI ?亙嚗???`run_single(verbose=True)`

#### `_backtest_context` ??Config/Datetime ?

Context manager嚗恣??Config 閬神 + datetime monkey-patch?脣???剁??ａ?????蝣箔?憭活 `run_single()` 銝??豢情??

**datetime patch 閬???4 ??modules嚗?*

| Module | ?箔??閬?patch |
|--------|--------------|
| `trader.bot` | ?瑕閮?嚗datetime.now()` 瘥? entry/cooldown嚗?|
| `trader.positions` | `entry_time` 閮? |
| `trader.signal_scanner` | cooldown / recently_exited / order_failed 閮? |
| `trader.position_monitor` | close/summary timestamp ??`holding_hours` |
| `trader.strategies.legacy.v53_sop` or `trader.strategies.v53_sop` | `hours_held` 閮?嚗TIME_EXIT` 閫貊嚗?|
| `trader.strategies.legacy.v6_pyramid` or `trader.strategies.v6_pyramid` | `hours_held` 閮?嚗V6_STAGE1_MAX_HOURS` 閫貊嚗?|
| `trader.strategies.legacy.v7_structure` or `trader.strategies.v7_structure` | Stage 1 timeout / V7 lifecycle |
| `trader.strategies.v54_noscale` | feat-grid 銝餃?蝑??`hours_held` / timeout |

> legacy `v53_sop` / `v6_pyramid` / `v7_structure` ??feat-grid ??`v54_noscale`?signal_scanner`?position_monitor` ?賣??湔??module-level `datetime`嚗? patch ?? `hours_held`?ooldown ??summary timestamp ?璅⊥????

```python
from backtest_engine import BacktestConfig, BacktestEngine

cfg = BacktestConfig(
    symbols=["BTC/USDT", "ETH/USDT"],
    start="2026-01-01",
    end="2026-02-28",
    initial_balance=10000.0,   # USDT
    fee_rate=0.0004,           # 0.04% per trade
    warmup_bars=100,           # ??N ??bar 銝銵??伐?indicator ??嚗?
    strategy="live",           # "live" | "v6" | "v53"
    config_overrides={},       # 閬? Config ?嚗?皜祉????芸???嚗?
)

engine = BacktestEngine(cfg)

# 蝔???恬?AutoTrader ?剁?
result = engine.run_single()          # ??嚗?? BacktestResult

# CLI ?澆嚗犖撌亦嚗?
result = engine.run()                 # 蝑? run_single(verbose=True)

print(result.summary)
# {
#   "strategy": "live",       # 雿輻??渡???
#   "total_trades": 15,
#   "win_rate": 0.6,
#   "profit_factor": 1.85,
#   "total_return_pct": 12.34,
#   "max_drawdown_pct": 5.67,
#   "sharpe": 1.42,           # 撟游?嚗?H resolution嚗qrt(8760)嚗?
#   "trades_per_week": 3.75,  # 鈭斗??餌?嚗utoTrader 閰??剁?
# }

print(result.trades)         # List[dict]嚗???perf_db.record_trade
print(result.equity_curve)   # List[(pd.Timestamp, float)]
```

**Equity 閮??砍?嚗?*
```
portfolio_value = initial_balance + gross_closed_pnl - total_fees + unrealized_pnl
```
`pnl_usdt` 靘 `perf_db.record_trade`嚗 **GROSS**嚗??祥嚗total_fees` ??`MockOrderEngine` ?函?餈質馱嚗漱??蝥祥 + funding fee嚗?銝?銴皜?

---

### `report_generator.py` ??ReportGenerator

```python
from report_generator import ReportGenerator
from pathlib import Path

ReportGenerator().generate(result, output_dir=Path("results"))
```

頛詨嚗?

| 瑼? | ?批捆 |
|------|------|
| `trades.csv` | ??漱??雿???`exit_strategy`嚗?蝑祕?蝙?函??箏蝑嚗??∩漱??頛詨?急??剔?蝛?CSV |
| `summary.json` | `strategy / total_trades / win_rate / profit_factor / total_return_pct / max_drawdown_pct / sharpe / trades_per_week` |
| `equity_curve.html` | Plotly dark theme 鈭??”嚗?憿 strategy ?迂 |

---

### `trade_replayer.py` ??TradeReplayer

敺璈?`v6_performance.db` 霈甇瑕鈭斗?嚗 K 蝺???`PositionManager` 瘙箇?嚗?撠?actual vs replayed exit??

```python
from trade_replayer import TradeReplayer

replayer = TradeReplayer(
    db_path="v6_performance.db",
    what_if={"MIN_MFE_R_FOR_PULLBACK": 0.5},  # ?舫嚗onfig 閬?嚗銵??芸???嚗?
)

# 頛鈭斗?
trades = replayer.load_trades(limit=20, symbol="BTC/USDT")

# ?
results = [replayer.replay(t) for t in trades]

# 頛詨銵冽
replayer.report(results)
```

`replay()` ?蝯?嚗?

```python
{
    "trade_id": "abc123",
    "symbol": "BTC/USDT",
    "side": "LONG",
    "actual_exit_reason": "STRUCTURE_TRAIL",
    "actual_exit_price": 42000.0,
    "replayed_exit_reason": "PROFIT_PULLBACK",  # ?乩???暺擃漁
    "replayed_exit_price": 41800.0,             # None 銵函內?頞??芾孛?澆??
    "decisions": [
        {"time": "2026-01-15 12:00:00+00:00", "price": 40500.0,
         "action": "ACTIVE", "reason": None, "new_sl": None},
        ...
    ],
    "what_if": {"MIN_MFE_R_FOR_PULLBACK": 0.5},
}
```

**PositionManager ?遣嚗?*
- `stop_loss` 敺?`trade["initial_r"]` ?典?嚗entry_price - initial_r` for LONG嚗?
- ??5% 蝖祉Ⅳ嚗Ⅱ靽?`risk_dist` 甇?Ⅱ ??Stage 2/3 閫貊??trailing ?摩敹祕?

---

### `pull_db.sh` ???? DB

```bash
bash tools/Backtesting/pull_db.sh
```

敺?rwUbuntu ??`v6_performance.db` ??`tools/Backtesting/v6_performance.db`?仃???喲?綽?`set -e`嚗?

??蝑??誘嚗?
```bash
scp rwfunder@100.67.114.104:/home/rwfunder/?辣/tradingbot/trading_bot_v6/v6_performance.db \
    tools/Backtesting/v6_performance.db
```

---

## CLI ??

### backtest_engine.py

```
python tools/Backtesting/backtest_engine.py [options]

Options:
  --symbols    BTC/USDT ETH/USDT ...   璅??”嚗?閮哨?BTC/USDT嚗?
  --start      YYYY-MM-DD              ???交?嚗?閮哨?2026-01-01嚗?
  --end        YYYY-MM-DD              蝯??交?嚗?閮哨?2026-02-28嚗?
  --balance    float                   ??鞈? USDT嚗?閮哨?10000.0嚗?
  --output     dir                     頛詨?桅?嚗?閮哨?results嚗撠?單嚗?
  --strategy   live|v54|v7|v6|v53      ?箏蝑嚗?閮哨?live嚗?
```

### trade_replayer.py

```
python tools/Backtesting/trade_replayer.py [options]

Required:
  --db         path                    v6_performance.db 頝臬?

Options:
  --limit      int                     霈???賂??身嚗?0嚗?
  --symbol     str                     ?蕪 symbol嚗.g. BTC/USDT嚗?
  --trade-id   str                     ??? trade_id
  --what_if    KEY=VALUE ...           閬? Config ?

What_if 蝭?嚗?
  --what_if MIN_MFE_R_FOR_PULLBACK=0.5 MIN_FAKEOUT_ATR=0.5
  --what_if V6_4H_EMA20_FORCE_EXIT=true
```

---

## 蝔??蝙??

### 摰?葫瘚?嚗LI 憸冽嚗?

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

### 蝔???恬?AutoTrader ?剁?

```python
from backtest_engine import BacktestConfig, BacktestEngine

cfg = BacktestConfig(
    symbols=["BTC/USDT", "ETH/USDT"],
    start="2021-01-01",
    end="2021-04-30",
    config_overrides={"SL_ATR_BUFFER": 0.6, "ADX_THRESHOLD": 20},
)

# run_single(): ??? side effect??? BacktestResult
result = BacktestEngine(cfg).run_single()

print(result.summary["trades_per_week"])  # AutoTrader 閰? gate
print(result.summary["profit_factor"])
print(result.summary["sharpe"])
```

### 摰Ｚˊ???釣?伐?銝?頛?

```python
import pandas as pd
from time_series_engine import TimeSeriesEngine
from mock_components import MockOrderEngine
from backtest_bot import create_backtest_bot

# ?芸??豢?
df = pd.read_parquet("my_data.parquet")  # index=UTC DatetimeIndex

tse = TimeSeriesEngine({"BTC/USDT": {"1h": df, "4h": df}})
engine = MockOrderEngine(tse, fee_rate=0.0004)
bot = create_backtest_bot(tse, engine)

# ???券脫???
for ts in df.index:
    tse.set_time(ts)
    bot.scan_for_signals()
    bot.monitor_positions()
```

---

## Multi-Window Backtest Standard

?桐? window 敺捆?? regime ?榆隤方?????edge?遙雿?????runtime ??detector / filter / exit 霈嚗?閮剛?頝?multi-window嚗?頛?暺?函撠??????臬??銝畾萇?蝯? PF??

### Baseline Matrix

?箸? symbol 蝯?嚗?

```text
BTC/USDT
ETH/USDT
SOL/USDT
BNB/USDT
XRP/USDT
DOGE/USDT
```

?箸? period 蝯? (Ruei ?‵ 2026-04-11嚗???BTC 4H RegimeEngine + avg BBW ?)嚗?

| period label | date range | BTC replay note |
|---|---|---|
| TRENDING up | `2023-10-01 -> 2024-03-31` | 撘瑚??挾 |
| TRENDING down | `2022-02-15 -> 2022-06-15` | BTC -50.8%; TRENDING 75.9%, trend dir SHORT 64.2%; 瘥?2025/26 ??recent bear ?港嗾瘛?|
| RANGING | `2024-12-31 -> 2025-03-31` | BTC -11.9%; RANGING 51.8% / TRENDING 48.2% |
| SQUEEZE (low-vol proxy) | `2023-07-01 -> 2023-10-01` | RegimeEngine SQUEEZE 0% **雿?* avg BBW 頛?嚗?*璅 proxy嚗??舐?甇?RegimeEngine SQUEEZE** |
| mixed | `2025-02-01 -> 2025-08-31` | BTC +6.8%; TRENDING 59.3% / RANGING 40.7%; mixed / transition |
| recent 90d | `2026-01-06 -> 2026-04-06` | ???cache 90d; BTC -26.3%; TRENDING 68.4% / RANGING 31.6% |

**Caveat ??SQUEEZE proxy**: `SQUEEZE (low-vol proxy)` ?? **銝** ?迤 RegimeEngine SQUEEZE?egimeEngine ? BTC 4H 撟曆?????SQUEEZE regime (憭折??period ??0%)嚗?隞仿?雿輻 avg BBW 頛???2023 憭迤??? proxy嚗?閫撖?V54 ?其?瘜Ｗ??啣???shape嚗?閬??"SQUEEZE regime gate test"??

**Caveat ??cache coverage**: `tools/Backtesting/cache/` ?桀?蝻?`BNBUSDT` / `XRPUSDT` ??`1h` / `4h` / `1d` / `funding` parquet cache?? full 6 symbols ? 6 periods matrix ????鋆?嚗?????`2022-02-15` ??`2026-04-06`??

### Gate Reading

- Prefer relative PF / Sharpe / max drawdown deltas against the matching baseline window.
- Use absolute floors only when an aggregate gate explicitly defines them.
- Treat signal-count shifts as first-class evidence, especially when cooldown or lane occupancy can distort trade attribution.
- Validate the actual runtime signal set directly; do not infer runtime performance from a richer research signal set.

### Case Study

`results/ema_weekend_review_20260411/ema_research_epilogue.md` ??`Window selection bias` 畾菔???銝甈∪擃萱??EMA ?弦?瑟???典?銝??BTC bear / downtrend / ranging slice嚗???evidence 撟曆??賣 SHORT-only??蝥???EMA ??隡?detector ?弦??蝚砌?甇交??耨甇?蝣箄? review window 閬?嚗??舐?亥矽 detector??

---

## AutoTrader ?游?

?葫撘???AutoTrader嚗I ?芯蜓??芸?嚗?摨惜?歇摰? Phase 0 Round 1 ?箇?閮剜嚗?

| 摰?? | 隤芣? |
|---------|------|
| `run_single()` API | 蝝?蝞???side effect嚗? AutoTrader ????澆 |
| `_backtest_context` CM | Config + datetime patch ?嚗? modules嚗?憭活 run 銝??豢情??|
| `trades_per_week` metric | 鈭斗??餌?蝯梯?嚗utoTrader 閰? gate ??|
| Import path 撠? | ?券??`trader.*`嚗?銝餃?獢???|
| Funding rate 璅⊥ | `FundingLoader` + `MockOrderEngine.deduct_funding()`嚗quity ?渡移蝣?|

### Phase 0 Round 2嚗???

| ? | 隤芣? |
|------|------|
| `evaluator.py` | Gates + composite score嚗F/Sharpe/DD/WR/Freq ??嚗?|
| `experiment_db.py` | SQLite CRUD嚗??祕撽????/?函? |
| Regime data | 摰儔 bull/bear/sideways/lowvol ?????+ 銝? K-line cache |
| Baseline calibration | ?函???貉? baseline嚗皞?trade frequency gate |

> 閰唾? `docs/superpowers/specs/2026-03-22-autotrader-design.md`

---

## Trade Replayer

Trade Replayer ?身閮?**撽??箏?摩**嚗策摰?蝑?撖虫漱???脣璇辣嚗?嗆????湔??頝?PositionManager嚗??箏???臬?祕???氬?

### ?詨??券?

**1. 撽??隤踵??**
```bash
# ?桀???
python trade_replayer.py --db v6_performance.db --limit 20

# what_if嚗?擃?MIN_MFE_R ?瑼餃?嚗rofit_pullback 閫貊??虫???
python trade_replayer.py --db v6_performance.db --limit 20 \
  --what_if MIN_MFE_R_FOR_PULLBACK=0.5
```

**2. 閮箸?孵?鈭斗?**
```bash
# ??蝑漱????bar ?捱蝑?蝔?
python trade_replayer.py --db v6_performance.db --trade-id <trade_id>
```

**3. 頛詨閫??**

| 憿 | ??|
|------|------|
| 蝬 | actual_exit_reason == replayed_exit_reason嚗??其??湛? |
| 暺 | ?箏??銝?嚗?賣 SL 雿宏???詨榆?堆? |
| `replayed_exit_price = None` | ?頞??芾孛?澆?湛?`timeout_in_replay`嚗?|

### ?

- `stop_loss` 敺?`initial_r` ?典?嚗?隡澆潘??撖阡?? Stage 2/3 ??SL 撌脩宏???韏琿???SL ?祕??賣??賢榆??
- ?敺?entry_time ???bar ??嚗??恍脣?? indicator ???ars < 10 ?歲??`pm.monitor()`??

---

## 閮剛?瘙箇?

### ?箔? Composition + Patch嚗?蝜潭嚗?

?湔蝜潭 TradingBot runtime ???葫?血? bot ?折撖虫?? `unittest.mock.patch` ?踵??琿??辣嚗ata_provider?xecution_engine嚗?bot ??`scan_for_signals()` / `monitor_positions()` / `_handle_close()` 蝑敹?頛臬??其????憭批? fidelity??

### ?箔? TimeSeriesEngine嚗?

?湔?? DataFrame ??iloc 銋撖虫?嚗?摰寞?銝?敹?slice ?唳靘? bar嚗ook-ahead bias嚗imeSeriesEngine ???Ⅱ??API ??嚗??`set_time()` ?澆敺?`get_bars()` ???喳?????????敺?祆??日◢?芥?

### datetime patch ?箔??閬?4 ??modules嚗?

`bot.py` ??`positions.py` 銋?嚗eat-grid ???`signal_scanner.py`?position_monitor.py`?grid_manager.py`?utils.py`嚗誑??`v54_noscale.py` / legacy strategies 銋?航?湔?典 `datetime.now()`??甇?`_backtest_context()` ??甈?patch current + legacy modules嚗瞍?嚗hours_held`?ooldown?CYCLE_SUMMARY` ???喲???啁?撖行??test_patch_contract.py` ??AST ?? trader/ 蝣箔????`datetime.now()` ?澆?賢 patch 皜銝准?

### pnl_usdt ??GROSS ? NET嚗?

`perf_db.record_trade` ??`pnl_usdt` ??**GROSS**嚗???蝥祥嚗 bot ??閮??孵?嚗_handle_close`嚗pnl_usdt = pm.total_size * (exit_price - avg_entry)`嚗MockOrderEngine.total_fees` ?函?蝝航????entry + exit ??鞎餃? funding fee??????銴皜?

### Sharpe 撟游???

Equity curve ??1H resolution嚗?隞交???return ?臬???研僑??銋?`sqrt(24 ? 365) = sqrt(8760)` ??93.6嚗? `sqrt(24)`??

---

## 撌脩?

1. **?漱璅∪?蝪∪?**嚗誑 current bar close price ?漱嚗 slippage 璅∪???撖血??孵??暺?撠文 Stage 2/3 ??
2. **Stop 閫貊餈撮**嚗check_stop_triggers()` ??bar close 雿?漱?對?撖阡? SL 隞?stop price ?漱嚗蔣??pnl 閮??移蝣箏漲??
3. **憭??蒂銵???*嚗acktestEngine ??1H bar 銝脰??????symbol嚗?璅⊥?祕 bot ??asyncio 銝衣??
4. **4H EMA20 force exit ?怠?**嚗V6_4H_EMA20_FORCE_EXIT=False`嚗ot 銝餌?嚗??葫銋窒?冽迨閮剖???
5. **Parquet 敹怠? key ??交?**嚗?皜祉??symbol 雿??????嚗?敹怠?銝??芸??蔥嚗???蝞∠? `cache/` ?桅???
6. **Funding rate 蝎曄Ⅱ摨?*嚗誑 1H bar ???喳? `funding_series.index` ?移蝣?match嚗? timestamp 摰撠?嚗 Binance ???timestamp ??蝝炊撌殷??嗆 bar 銝?蝯???

---

## ?瑁?皜祈岫

```bash
cd /c/Users/user/Documents/Claude.ai

# ?券皜祈岫
python -m pytest tools/Backtesting/tests/ -v

# ?桐?璅∠?
python -m pytest tools/Backtesting/tests/test_backtest_engine.py -v

# ?怨???
python -m pytest tools/Backtesting/tests/ --cov=tools/Backtesting --cov-report=term-missing
```

| 皜祈岫瑼?| 皜祈岫??| 瘨菔?蝭? |
|--------|--------|---------|
| test_time_series_engine.py | 6 | look-ahead ?脰風?imit?et_current_price?ntersection |
| test_mock_components.py | 9 | ?澆?撠??ee deduction?top 閫貊?摩 |
| test_backtest_bot.py | 3 | ?∠雯頝臬遣蝡ata_provider/execution_engine 瘜典 |
| test_backtest_engine.py | 8 | smoke test?onfig ???rades_per_week?un_single API |
| test_report_generator.py | 3 | 銝撓?箸???雿ummary keys |
| test_trade_replayer.py | 3 | load_trades?ymbol filter?eplay 蝯? |
| test_strategy_selection.py | 8 | v54 / v7 / v6 / v53 override?egistry ???潦egistry ?芰? |
| test_datetime_patch.py | 2 | strategy modules 雿輻璅⊥?????context 敺???|
| test_funding_rate.py | 4 | cache hit?ownload rate limit?ONG/SHORT fee ?孵? |
| test_patch_contract.py | 10 | patch ?格?摮?nject 撅祆批??具atetime.now() ?刻?????|
| test_paths.py | 2 | env var ?芸??allback ?詨?頝臬? |

**??嚗?0/60 passed**
