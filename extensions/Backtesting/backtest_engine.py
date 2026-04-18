"""?????????"""
import os
import sys
import logging
import datetime as _real_datetime_module
import statistics
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Optional


def _resolve_bot_root() -> Path:
    """Resolve the trading bot root for both isolated repos and legacy worktrees."""
    env = os.environ.get("TRADING_BOT_ROOT")
    if env:
        return Path(env).resolve()

    local_repo = Path(__file__).resolve().parents[2]
    if (local_repo / "trader" / "bot.py").exists():
        return local_repo

    workspace = local_repo.parent
    for candidate in (
        workspace / "projects" / "trading_bot" / ".worktrees" / "feat-regime-router",
        workspace / "projects" / "trading_bot" / ".worktrees" / "feat-grid",
        workspace / "projects" / "trading_bot",
    ):
        if (candidate / "trader" / "bot.py").exists():
            return candidate.resolve()

    return local_repo


TRADING_BOT_ROOT = _resolve_bot_root()
sys.path.insert(0, str(TRADING_BOT_ROOT))

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(x, **kw):
        return x

from data_loader import BacktestDataLoader, CACHE_DIR
from time_series_engine import TimeSeriesEngine
from mock_components import MockOrderEngine
from backtest_bot import create_backtest_bot
from bot_compat import get_config_class, get_datetime_patch_modules
from signal_audit import SignalAuditCollector

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_DAYS = 180


# ???? Simulation time patch ????????????????????????????????????????????????????????????????????????????????????????????????????????
# bot.py / positions.py ??datetime.now(timezone.utc) ????????? entry_time??
# ????????????eal now() ?豯????啣? <1s??????
#   (1) ????豯折???? ???謍????trade ????? symbol ?豯折?????
#   (2) entry_time ??exit_time ??holding_hours ??0 ??TIME_EXIT ?豯折?????
# ?鞈?僱???onkey-patch trader.bot.datetime / trader.positions.datetime??? now() ?????穿???????

_sim_ts_container: list = [None]   # [pd.Timestamp | None]??oop ??bar ???


class _BacktestDatetime(_real_datetime_module.datetime):
    """datetime ?????ow() ????????????????????????"""

    @classmethod
    def now(cls, tz=None):
        ts = _sim_ts_container[0]
        if ts is None:
            return _real_datetime_module.datetime.now(tz)
        result = ts.to_pydatetime()
        if tz is not None and result.tzinfo is None:
            result = result.replace(tzinfo=_real_datetime_module.timezone.utc)
        elif tz is None and result.tzinfo is not None:
            result = result.replace(tzinfo=None)
        return result


# Strategy plugins are supplied by id via --strategies.


def _cache_symbol(symbol: str) -> str:
    return symbol.replace("/", "").upper()


def _parse_cache_filename(path: Path):
    """Parse SYMBOL_TF_YYYYMMDD_YYYYMMDD.parquet cache names."""
    if path.suffix != ".parquet":
        return None
    parts = path.stem.rsplit("_", 3)
    if len(parts) != 4:
        return None
    symbol, timeframe, start_s, end_s = parts
    try:
        start_date = datetime.strptime(start_s, "%Y%m%d").date()
        end_date = datetime.strptime(end_s, "%Y%m%d").date()
    except ValueError:
        return None
    return symbol.upper(), timeframe, start_date, end_date


def _latest_cache_end_date(
    symbols: List[str],
    *,
    timeframe: str = "1h",
    cache_dir: Optional[Path] = None,
) -> Optional[date]:
    """Return the latest shared cache end date for requested symbols/timeframe."""
    cache_path = Path(cache_dir) if cache_dir is not None else CACHE_DIR
    if not cache_path.exists():
        return None

    latest_by_symbol = {}
    wanted = {_cache_symbol(symbol) for symbol in symbols}
    for path in cache_path.glob("*.parquet"):
        parsed = _parse_cache_filename(path)
        if parsed is None:
            continue
        symbol, tf, _start_date, end_date = parsed
        if symbol not in wanted or tf != timeframe:
            continue
        current = latest_by_symbol.get(symbol)
        if current is None or end_date > current:
            latest_by_symbol[symbol] = end_date

    if not latest_by_symbol:
        return None

    # For multi-symbol runs, use the earliest "latest" end date so the
    # generated default window is covered by every cached symbol we found.
    return min(latest_by_symbol.values())


def _today_date(today=None) -> date:
    if today is None:
        return date.today()
    if isinstance(today, datetime):
        return today.date()
    return today


def _parse_iso_date(value: str) -> date:
    return datetime.fromisoformat(value).date()


def resolve_backtest_window(
    symbols: List[str],
    start: Optional[str],
    end: Optional[str],
    *,
    cache_dir: Optional[Path] = None,
    timeframe: str = "1h",
    window_days: int = DEFAULT_WINDOW_DAYS,
    today=None,
) -> Tuple[str, str]:
    """
    Resolve omitted CLI start/end from the latest local cache window.

    Explicit start/end pairs are left untouched for reproducibility. When either
    side is omitted, the default end is the latest cache end date for the
    requested symbol/timeframe set; if no matching cache exists, use today.
    """
    if start is not None and end is not None:
        return start, end

    end_date = (
        _parse_iso_date(end)
        if end is not None
        else _latest_cache_end_date(symbols, timeframe=timeframe, cache_dir=cache_dir)
    )
    if end_date is None:
        end_date = _today_date(today)

    start_date = _parse_iso_date(start) if start is not None else end_date - timedelta(days=window_days)
    return start_date.isoformat(), end_date.isoformat()


def _record_strategy_ids(active_trades: dict, pm_registry: dict) -> None:
    """
    Record strategy ids for report attribution without mutating positions.
    """
    for pm in active_trades.values():
        tid = pm.trade_id
        if tid not in pm_registry:
            pm_registry[tid] = getattr(pm, "strategy_id", "unknown")


@dataclass
class BacktestConfig:
    symbols: List[str]
    start: str
    end: str
    initial_balance: float = 10000.0
    fee_rate: float = 0.0004
    warmup_bars: int = 100
    enabled_strategies: List[str] = field(default_factory=list)
    dry_count_only: bool = False
    precompute_indicators: bool = False
    config_overrides: dict = field(default_factory=dict)


@dataclass
class BacktestResult:
    trades: List[dict]
    equity_curve: List[Tuple]
    config: BacktestConfig
    summary: dict = field(default_factory=dict)
    signal_audit: Optional[object] = None  # SignalAuditCollector when available
    backtest_run_errors: List[dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.summary:
            self.summary = self._calc_summary()
        errors = list(self.backtest_run_errors or [])
        self.summary["backtest_run_errors"] = errors
        self.summary["backtest_run_error_count"] = len(errors)

    def _calc_summary(self) -> dict:
        if not self.trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_return_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "sharpe": 0.0,
                "trades_per_week": 0.0,
            }

        pnls = [t.get("pnl_usdt", 0) for t in self.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        total_pnl = sum(pnls)
        win_rate = len(wins) / len(pnls)
        gross_profit = sum(wins) if wins else 0.0
        gross_loss = abs(sum(losses)) if losses else 0.0
        pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        total_return = total_pnl / self.config.initial_balance * 100

        values = [v for _, v in self.equity_curve]
        max_dd = 0.0
        if values:
            peak = values[0]
            for v in values:
                peak = max(peak, v)
                dd = (peak - v) / peak * 100 if peak > 0 else 0.0
                max_dd = max(max_dd, dd)

        sharpe = 0.0
        if len(values) > 1:
            daily_rets = [
                (values[i] - values[i - 1]) / values[i - 1]
                for i in range(1, len(values))
                if values[i - 1] > 0
            ]
            if daily_rets and statistics.stdev(daily_rets) > 0:
                sharpe = (statistics.mean(daily_rets) / statistics.stdev(daily_rets)) * (8760 ** 0.5)  # hourly ??annualized

        # trades_per_week: ??????????/ 7
        from datetime import datetime
        start_dt = datetime.fromisoformat(self.config.start)
        end_dt = datetime.fromisoformat(self.config.end)
        duration_weeks = (end_dt - start_dt).days / 7
        trades_per_week = len(pnls) / max(duration_weeks, 1)

        return {
            "strategy": ",".join(self.config.enabled_strategies) or "none",
            "total_trades": len(pnls),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(pf, 4),
            "total_return_pct": round(total_return, 4),
            "max_drawdown_pct": round(max_dd, 4),
            "sharpe": round(sharpe, 4),
            "trades_per_week": round(trades_per_week, 2),
        }


# ???? Backtest context manager ????????????????????????????????????????????????????????????????????????????????????????????????
# Config override + datetime patch + cleanup????遴?????run ?????撓?????

def _derive_regime_probe_trend(context: dict) -> Optional[str]:
    """Mirror regime routing into a comparable trend label for audit only."""
    regime = context.get("regime")
    direction = context.get("direction")
    if regime == "RANGING":
        return "RANGING"
    if regime == "TRENDING" and direction in ("LONG", "SHORT"):
        return direction
    return None


def _regime_probe_snapshot(context: dict, candle_time) -> dict:
    """Return the backtest entry-time regime fields recorded on closed trades."""
    direction = context.get("direction")
    if direction not in ("LONG", "SHORT"):
        direction = None

    regime = context.get("regime")
    if not isinstance(regime, str):
        regime = "UNKNOWN"

    return {
        "entry_regime": regime,
        "entry_regime_trend": _derive_regime_probe_trend(context),
        "entry_regime_direction": direction,
        "entry_regime_reason": context.get("reason", "regime_probe"),
        "entry_regime_candle_time": str(candle_time),
    }


def _assign_entry_regime(active_trades: dict, regime_registry: dict, snapshot: Optional[dict]) -> None:
    """Capture the latest BTC 4H regime probe when a trade is first observed."""
    if not snapshot:
        return

    for pm in active_trades.values():
        tid = getattr(pm, "trade_id", None)
        if tid and tid not in regime_registry:
            regime_registry[tid] = dict(snapshot)


def _record_regime_probe(bot, timestamp, *, grid_enabled: bool) -> None:
    """
    Advance BTC 4H regime state during backtest even when grid is disabled.

    This is an audit-only sidecar for Patch B baseline coverage. It should not
    affect scan routing under the current live config.
    """
    if grid_enabled:
        return

    audit = getattr(bot, "_signal_audit", None)
    if audit is None:
        return

    update_fn = getattr(bot, "_update_btc_regime_context", None)
    if update_fn is None:
        return

    try:
        context = update_fn() or {}
    except Exception as e:
        logger.debug(f"regime probe error at {timestamp}: {e}")
        return

    candle_time = context.get("candle_time") or str(timestamp)
    if candle_time == getattr(bot, "_backtest_last_regime_probe_candle", None):
        return
    bot._backtest_last_regime_probe_candle = candle_time

    regime = context.get("regime")
    if not isinstance(regime, str):
        regime = "UNKNOWN"

    snapshot = _regime_probe_snapshot(context, candle_time)
    bot._backtest_latest_regime_probe_snapshot = snapshot

    audit.record_btc_trend(
        timestamp=candle_time,
        source="regime_probe",
        trend=snapshot["entry_regime_trend"],
        regime=regime,
        direction=snapshot["entry_regime_direction"],
        reason=snapshot["entry_regime_reason"],
    )


@contextmanager
def _backtest_context(config_overrides: dict):
    """
    Context manager: ?豯?? Config ????+ datetime monkey-patch??
    ??????????????????????????run_single() ?????撓?????
    """
    Config = get_config_class()
    datetime_modules = get_datetime_patch_modules()
    import copy
    from trader.indicators.technical import TechnicalAnalysis

    _orig_config_attrs = {
        key: copy.deepcopy(value)
        for key, value in vars(Config).items()
        if key.isupper()
        and not key.startswith("_")
        and not isinstance(value, (classmethod, staticmethod))
        and not callable(value)
    }

    # NOTE: bot_config.json removed; Config class defaults are now runtime truth.
    # Follow-up: revisit backtest-specific config injection (per-run overrides
    # already land via config_overrides below).
    _override_keys = set(config_overrides or {})
    _missing_override_keys = {key for key in _override_keys if not hasattr(Config, key)}
    if config_overrides:
        for k, v in config_overrides.items():
            setattr(Config, k, v)

    # ????????
    _orig_symbols = Config.SYMBOLS
    _orig_use_scanner = Config.USE_SCANNER_SYMBOLS
    _orig_dry_run = Config.DRY_RUN
    _orig_datetimes = {
        module.__name__: module.datetime
        for module in datetime_modules
        if hasattr(module, "datetime")
    }
    _orig_calculate_indicators = TechnicalAnalysis.calculate_indicators

    # ??? datetime patch???????????datetime.now() ??module??
    for module in datetime_modules:
        if hasattr(module, "datetime"):
            module.datetime = _BacktestDatetime
    _sim_ts_container[0] = None

    if getattr(Config, "BACKTEST_USE_PRECOMPUTED_INDICATORS", False):
        required_indicator_columns = {
            "ema_trend", "vol_ma", "atr", "ema_fast", "ema_slow", "ema_10", "ema_20", "adx"
        }

        def _cached_calculate_indicators(df):
            if not df.empty and required_indicator_columns.issubset(df.columns):
                return df
            return _orig_calculate_indicators(df)

        TechnicalAnalysis.calculate_indicators = staticmethod(_cached_calculate_indicators)

    try:
        yield Config
    finally:
        for key, value in _orig_config_attrs.items():
            setattr(Config, key, value)
        for key in _missing_override_keys:
            if hasattr(Config, key):
                delattr(Config, key)
        for module in datetime_modules:
            if module.__name__ in _orig_datetimes:
                module.datetime = _orig_datetimes[module.__name__]
        TechnicalAnalysis.calculate_indicators = _orig_calculate_indicators
        _sim_ts_container[0] = None


class BacktestEngine:
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.loader = BacktestDataLoader()

    def _load_data(self, cfg: BacktestConfig) -> dict:
        """???????symbol ??1H + 4H + 1D ??? + funding rate"""
        from datetime import datetime, timedelta
        from funding_loader import FundingLoader
        trend_start = (
            datetime.fromisoformat(cfg.start) - timedelta(days=300)
        ).strftime("%Y-%m-%d")

        data = {}
        funding_loader = FundingLoader()
        for sym in cfg.symbols:
            df_1h = self.loader.get_data(sym, "1h", cfg.start, cfg.end)
            df_4h = self.loader.get_data(sym, "4h", cfg.start, cfg.end)
            df_1d = self.loader.get_data(sym, "1d", trend_start, cfg.end)
            funding = funding_loader.get_funding_rates(sym, cfg.start, cfg.end)
            data[sym] = {"1h": df_1h, "4h": df_4h, "1d": df_1d, "funding": funding}
        return data

    @staticmethod
    def _precompute_indicators(data: dict) -> None:
        """Precompute standard indicators once for backtest-only replay speed."""
        from trader.indicators.technical import TechnicalAnalysis

        for frames in data.values():
            for timeframe in ("1h", "4h", "1d"):
                df = frames.get(timeframe)
                if df is not None and not df.empty:
                    frames[timeframe] = TechnicalAnalysis.calculate_indicators(df.copy())

    def _effective_config_overrides(self, cfg: BacktestConfig) -> dict:
        """Build backtest-only Config overrides without mutating runtime files."""
        from trader.config import Config

        overrides = dict(cfg.config_overrides or {})
        enabled = list(cfg.enabled_strategies or [])
        catalog = dict(getattr(Config, "STRATEGY_CATALOG", {}))
        for strategy_id in enabled:
            entry = dict(catalog.get(strategy_id) or {})
            if entry:
                entry["enabled"] = True
                catalog[strategy_id] = entry
        overrides["STRATEGY_RUNTIME_ENABLED"] = bool(enabled)
        overrides["ENABLED_STRATEGIES"] = enabled
        overrides["STRATEGY_CATALOG"] = catalog

        if cfg.dry_count_only:
            overrides["BACKTEST_DRY_COUNT_ONLY"] = True
        else:
            overrides.pop("BACKTEST_DRY_COUNT_ONLY", None)

        if cfg.precompute_indicators:
            overrides["BACKTEST_USE_PRECOMPUTED_INDICATORS"] = True
        else:
            overrides.pop("BACKTEST_USE_PRECOMPUTED_INDICATORS", None)

        return overrides

    def run_single(self, verbose: bool = False) -> BacktestResult:
        """
        Side-effect-free single backtest?????BacktestResult??
        ???∵策??????????????????? AutoTrader ???????????

        Args:
            verbose: True ??????????????LI ?????alse ??????AutoTrader ???
        """
        cfg = self.config

        if verbose:
            print(f"\n[Backtest] ??? {len(cfg.symbols)} ????????..")

        effective_overrides = self._effective_config_overrides(cfg)

        with _backtest_context(effective_overrides) as Config:
            data = self._load_data(cfg)
            if cfg.precompute_indicators:
                self._precompute_indicators(data)
            if verbose:
                for sym, frames in data.items():
                    print(f"  {sym} 1H: {len(frames['1h'])} rows, "
                          f"4H: {len(frames['4h'])} rows, 1D: {len(frames['1d'])} rows")

            tse = TimeSeriesEngine(data)
            mock_engine = MockOrderEngine(tse, cfg.fee_rate, cfg.initial_balance)

            captured_trades: List[dict] = []
            pm_registry: dict = {}
            regime_registry: dict = {}
            backtest_run_errors: List[dict] = []
            audit = SignalAuditCollector()
            bot = create_backtest_bot(tse, mock_engine, effective_overrides)

            # Inject signal audit collector
            bot._signal_audit = audit

            # Wire regime transition callback
            if hasattr(bot, 'regime_engine') and bot.regime_engine is not None:
                bot.regime_engine._on_transition = (
                    lambda ts, old, new, cnt: audit.record_regime_transition(ts, old, new, cnt)
                )

            def _collect_trade(d):
                tid = d.get("trade_id")
                d["exit_strategy"] = d.get("strategy_name") or pm_registry.get(tid, "unknown") if tid else "unknown"
                if tid and tid in regime_registry:
                    d.update(regime_registry[tid])
                captured_trades.append(d)
                return True

            bot.perf_db.record_trade = _collect_trade

            Config.SYMBOLS = cfg.symbols

            def _record_run_error(stage: str, ts, exc: Exception) -> None:
                payload = {
                    "timestamp": str(ts),
                    "symbol": "*ALL*",
                    "stage": stage,
                    "exc_type": type(exc).__name__,
                    "message": str(exc),
                }
                backtest_run_errors.append(payload)
                logger.warning("%s error at %s: %s", stage, ts, exc)

            all_ts = tse.get_1h_timestamps(cfg.symbols)
            if verbose:
                print(f"[Backtest] ??{len(all_ts)} ??1H bars??armup={cfg.warmup_bars}")

            equity_curve: List[Tuple] = []
            iter_ts = tqdm(all_ts, desc="Backtesting") if verbose else all_ts

            for i, ts in enumerate(iter_ts):
                tse.set_time(ts)
                _sim_ts_container[0] = ts

                _record_regime_probe(
                    bot,
                    ts,
                    grid_enabled=Config.ENABLE_GRID_TRADING,
                )

                if i < cfg.warmup_bars:
                    equity_curve.append((ts, cfg.initial_balance))
                    continue

                # a) ??單?????? ???謢???賹???
                triggered = mock_engine.check_stop_triggers()
                for sym in triggered:
                    if sym in bot.active_trades:
                        pm = bot.active_trades[sym]
                        bot._handle_close(
                            pm,
                            tse.get_current_price(sym),
                            decision_reason="BACKTEST_STOP_TRIGGER",
                        )

                # b) ?????+ ???????
                try:
                    bot.scan_for_signals()
                except Exception as e:
                    _record_run_error("scan_for_signals", ts, e)

                for pm in bot.active_trades.values():
                    pm_registry.setdefault(pm.trade_id, getattr(pm, "strategy_id", "unknown"))
                _assign_entry_regime(
                    bot.active_trades,
                    regime_registry,
                    getattr(bot, "_backtest_latest_regime_probe_snapshot", None),
                )

                try:
                    bot.monitor_positions()
                except Exception as e:
                    _record_run_error("monitor_positions", ts, e)

                # d) funding rate ?????0:00, 08:00, 16:00 UTC??
                if ts.hour in (0, 8, 16) and ts.minute == 0:
                    for sym, pm in bot.active_trades.items():
                        if getattr(pm, "is_closed", False):
                            continue
                        funding_series = data[sym].get("funding")
                        if funding_series is not None and ts in funding_series.index:
                            rate = funding_series.loc[ts]
                            avg_entry = getattr(pm, "avg_entry", 0.0) or 0.0
                            total_size = getattr(pm, "total_size", 0.0) or 0.0
                            mock_engine.deduct_funding(sym, pm.side, total_size, avg_entry, rate)

                # c) ?????? equity
                closed_pnl = sum(t.get("pnl_usdt", 0) for t in captured_trades)
                unrealized = 0.0
                for sym, pm in bot.active_trades.items():
                    if getattr(pm, "is_closed", False):
                        continue
                    current_price = tse.get_current_price(sym)
                    avg_entry = getattr(pm, "avg_entry", 0.0) or 0.0
                    total_size = getattr(pm, "total_size", 0.0) or 0.0
                    if pm.side == "LONG":
                        unrealized += (current_price - avg_entry) * total_size
                    else:
                        unrealized += (avg_entry - current_price) * total_size

                portfolio_value = (
                    cfg.initial_balance + closed_pnl - mock_engine.total_fees + unrealized
                )
                equity_curve.append((ts, portfolio_value))

            # ?謢???賹????????????
            for sym, pm in list(bot.active_trades.items()):
                if not getattr(pm, "is_closed", False):
                    try:
                        bot._handle_close(
                            pm,
                            tse.get_current_price(sym),
                            decision_reason="BACKTEST_END",
                        )
                    except Exception as e:
                        if verbose:
                            print(f"[Backtest] WARNING: force close {sym} failed: {e}")

            return BacktestResult(
                trades=captured_trades,
                equity_curve=equity_curve,
                config=cfg,
                signal_audit=audit,
                backtest_run_errors=backtest_run_errors,
            )

    def run(self) -> BacktestResult:
        """?????啣? CLI ?????un_single(verbose=True)"""
        return self.run_single(verbose=True)


if __name__ == "__main__":
    import argparse
    from report_generator import ReportGenerator

    parser = argparse.ArgumentParser(description="Strategy Runtime Backtest Engine")
    parser.add_argument("--symbols", nargs="+", default=["BTC/USDT"],
                        help="Symbols, e.g. BTC/USDT ETH/USDT")
    parser.add_argument("--start", default=None, help="Start date YYYY-MM-DD")
    parser.add_argument("--end",   default=None, help="End date YYYY-MM-DD")
    parser.add_argument("--balance", type=float, default=10000.0)
    parser.add_argument("--strategies", nargs="+", default=[], help="Enabled strategy plugin ids")
    parser.add_argument("--output", default="results", help="Output directory")
    parser.add_argument(
        "--dry-count-only",
        action="store_true",
        help="Record signal funnel candidates without opening positions",
    )
    parser.add_argument(
        "--precompute-indicators",
        action="store_true",
        help="Backtest-only speedup: precompute indicators once and reuse slices",
    )
    args = parser.parse_args()
    start, end = resolve_backtest_window(args.symbols, args.start, args.end)

    cfg = BacktestConfig(
        symbols=args.symbols,
        start=start,
        end=end,
        initial_balance=args.balance,
        enabled_strategies=args.strategies,
        dry_count_only=args.dry_count_only,
        precompute_indicators=args.precompute_indicators,
    )
    engine = BacktestEngine(cfg)
    result = engine.run()

    out_dir = Path(__file__).parent / args.output
    ReportGenerator().generate(result, out_dir)
    print(f"\nSummary: {result.summary}")
