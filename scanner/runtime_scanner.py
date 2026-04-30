"""Runtime-context scanner for the promoted StrategyRuntime portfolio.

This scanner is advisory only. It reports data health and market context for
the enabled plugin portfolio, but it does not publish a tradable symbol
universe and it does not alter runtime configuration.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

import pandas as pd

try:
    import ccxt
except ImportError:  # pragma: no cover - exercised only in stripped envs
    ccxt = None  # type: ignore

from trader.arbiter.regime_arbiter import RegimeArbiter
from trader.config import Config
from trader.indicators.registry import IndicatorRegistry
from trader.infrastructure.data_provider import MarketDataProvider
from trader.strategies import StrategyPlugin, StrategyRegistry
from trader.strategies.plugins._catalog import get_strategy_catalog
from trader.strategies.plugins.donchian_range_fade_4h import DonchianRangeFade4hStrategy
from trader.strategies.plugins.macd_signal_trending_up_4h import MacdSignalTrendingUp4hStrategy
from trader.utils import drop_unfinished_candle

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "scanner_config.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "runtime_scanner.json"


@dataclass(frozen=True)
class RuntimeScannerSettings:
    output_json_path: Path = DEFAULT_OUTPUT_PATH
    exchange: str = "binance"
    trading_mode: str = "future"
    sandbox_mode: bool = False
    api_max_retries: int = 3
    retry_delay: float = 5.0

    @classmethod
    def from_json(cls, path: str | Path | None = None) -> "RuntimeScannerSettings":
        config_path = Path(path) if path else DEFAULT_CONFIG_PATH
        if not config_path.exists():
            return cls()

        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        output_path = Path(data.get("RUNTIME_OUTPUT_JSON_PATH") or DEFAULT_OUTPUT_PATH)
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path

        return cls(
            output_json_path=output_path,
            exchange=str(data.get("EXCHANGE", cls.exchange)),
            trading_mode=str(data.get("MARKET_TYPE", data.get("TRADING_MODE", cls.trading_mode))),
            sandbox_mode=bool(data.get("SANDBOX_MODE", cls.sandbox_mode)),
            api_max_retries=int(data.get("API_MAX_RETRIES", cls.api_max_retries)),
            retry_delay=float(data.get("API_DELAY_BETWEEN_BATCHES", cls.retry_delay)),
        )


class RuntimeScanner:
    """Build a fixed-portfolio runtime diagnostics report."""

    CONTRACT_VERSION = "runtime-context/v1"
    DIAGNOSTIC_INDICATORS = {"ema", "atr", "adx", "bbw", "rsi", "macd"}

    def __init__(
        self,
        *,
        settings: RuntimeScannerSettings | None = None,
        exchange: Any = None,
        data_provider: Any = None,
        config_cls: Any = Config,
    ):
        self.settings = settings or RuntimeScannerSettings.from_json()
        self.config = config_cls
        self.exchange = exchange
        if data_provider is not None:
            self.data_provider = data_provider
        else:
            if self.exchange is None:
                self.exchange = self._init_exchange()
            self.data_provider = MarketDataProvider(
                self.exchange,
                max_retry=self.settings.api_max_retries,
                retry_delay=self.settings.retry_delay,
                sandbox_mode=self.settings.sandbox_mode,
                trading_mode=self.settings.trading_mode,
            )

    def scan(self, *, write: bool = True) -> dict[str, Any]:
        plugins = self._enabled_plugins()
        plugin_scopes = self._plugin_scopes(plugins)
        runtime_symbols = self._runtime_symbols(plugins)
        requirements = self._requirements_by_symbol(plugins, runtime_symbols)

        frames: dict[str, dict[str, pd.DataFrame]] = {}
        for symbol in runtime_symbols:
            frames[symbol] = {}
            for timeframe, warmup in requirements.get(symbol, {}).items():
                frames[symbol][timeframe] = self._fetch_frame(symbol, timeframe, warmup)

        report = {
            "scanner_contract_version": self.CONTRACT_VERSION,
            "scan_time": datetime.now(timezone.utc).isoformat(),
            "runtime_source": "Config.ENABLED_STRATEGIES + plugin.allowed_symbols",
            "runtime_selection_feeds_trading": False,
            "runtime_symbol_selection": "fixed_config_plugin_scope",
            "config": {
                "strategy_runtime_enabled": bool(self.config.STRATEGY_RUNTIME_ENABLED),
                "use_scanner_symbols": bool(self.config.USE_SCANNER_SYMBOLS),
                "config_symbols": list(self.config.SYMBOLS),
                "enabled_strategies": list(self.config.ENABLED_STRATEGIES),
            },
            "runtime_symbols": runtime_symbols,
            "plugin_scopes": plugin_scopes,
            "symbols": {
                symbol: self._symbol_report(symbol, plugins, frames.get(symbol, {}), requirements)
                for symbol in runtime_symbols
            },
            "deployment_boundary": {
                "feeds_strategy_runtime": False,
                "writes_bot_symbols": False,
                "writes_hot_symbols": False,
                "order_execution": False,
                "risk_sizing": False,
                "runtime_trade_universe_source": "Config.SYMBOLS filtered by plugin.allowed_symbols",
            },
        }

        if write:
            self.write_report(report)
        return report

    def write_report(self, report: Mapping[str, Any]) -> Path:
        path = self.settings.output_json_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True, default=_json_default),
            encoding="utf-8",
        )
        logger.info("Runtime scanner wrote %s", path)
        return path

    def _init_exchange(self):
        if ccxt is None:
            raise RuntimeError("ccxt is required for live runtime scanner fetches")

        exchange_cls = getattr(ccxt, self.settings.exchange)
        options: dict[str, Any] = {"enableRateLimit": True, "options": {}}
        if self.settings.trading_mode in {"future", "futures"}:
            options["options"]["defaultType"] = "future"
        exchange = exchange_cls(options)
        if hasattr(exchange, "set_sandbox_mode"):
            exchange.set_sandbox_mode(self.settings.sandbox_mode)
        exchange.load_markets()
        return exchange

    def _enabled_plugins(self) -> list[StrategyPlugin]:
        if not bool(self.config.STRATEGY_RUNTIME_ENABLED):
            return []
        registry = StrategyRegistry.from_config(
            get_strategy_catalog(self.config.ENABLED_STRATEGIES),
            self.config.ENABLED_STRATEGIES,
        )
        return list(registry.plugins.values())

    def _plugin_scopes(self, plugins: Iterable[StrategyPlugin]) -> dict[str, dict[str, Any]]:
        scopes: dict[str, dict[str, Any]] = {}
        for plugin in plugins:
            scopes[plugin.id] = {
                "allowed_symbols": self._ordered_symbols(plugin.allowed_symbols or self.config.SYMBOLS),
                "required_timeframes": dict(plugin.required_timeframes),
                "required_indicators": sorted(plugin.required_indicators),
                "tags": sorted(plugin.tags),
                "slot_hint": _slot_hint(plugin.id),
            }
        return scopes

    def _runtime_symbols(self, plugins: Iterable[StrategyPlugin]) -> list[str]:
        scoped: list[str] = []
        for plugin in plugins:
            candidates = plugin.allowed_symbols or set(self.config.SYMBOLS)
            scoped.extend(str(symbol) for symbol in candidates)
        return self._ordered_symbols(scoped)

    def _requirements_by_symbol(
        self,
        plugins: Iterable[StrategyPlugin],
        runtime_symbols: Iterable[str],
    ) -> dict[str, dict[str, int]]:
        runtime_set = set(runtime_symbols)
        requirements: dict[str, dict[str, int]] = {symbol: {} for symbol in runtime_symbols}
        for plugin in plugins:
            scoped_symbols = set(plugin.allowed_symbols or self.config.SYMBOLS) & runtime_set
            for symbol in scoped_symbols:
                for timeframe, warmup in plugin.required_timeframes.items():
                    requirements[symbol][timeframe] = max(
                        int(warmup),
                        requirements[symbol].get(timeframe, 0),
                    )
        return requirements

    def _ordered_symbols(self, symbols: Iterable[str]) -> list[str]:
        wanted = {str(symbol) for symbol in symbols}
        ordered = [symbol for symbol in self.config.SYMBOLS if symbol in wanted]
        ordered.extend(sorted(symbol for symbol in wanted if symbol not in set(ordered)))
        return ordered

    def _fetch_frame(self, symbol: str, timeframe: str, warmup: int) -> pd.DataFrame:
        try:
            raw = self.data_provider.fetch_ohlcv(symbol, timeframe, limit=max(int(warmup) + 1, 2))
        except Exception as exc:
            logger.warning("Runtime scanner fetch failed for %s %s: %s", symbol, timeframe, exc)
            return pd.DataFrame()

        if raw is None or raw.empty:
            return pd.DataFrame()

        frame = drop_unfinished_candle(raw)
        return IndicatorRegistry.apply(frame, self.DIAGNOSTIC_INDICATORS)

    def _symbol_report(
        self,
        symbol: str,
        plugins: Iterable[StrategyPlugin],
        frames: Mapping[str, pd.DataFrame],
        requirements: Mapping[str, Mapping[str, int]],
    ) -> dict[str, Any]:
        timeframe_report = {
            timeframe: self._timeframe_report(frame, requirements.get(symbol, {}).get(timeframe, 0))
            for timeframe, frame in frames.items()
        }
        return {
            "timeframes": timeframe_report,
            "liquidity": self._liquidity_report(symbol),
            "regime_context": self._regime_report(frames.get("4h")),
            "strategy_readiness": {
                plugin.id: self._strategy_report(plugin, symbol, frames)
                for plugin in plugins
                if symbol in set(plugin.allowed_symbols or self.config.SYMBOLS)
            },
        }

    def _timeframe_report(self, frame: pd.DataFrame, required_rows: int) -> dict[str, Any]:
        latest = frame.iloc[-1] if frame is not None and not frame.empty else None
        return {
            "rows": int(len(frame)) if frame is not None else 0,
            "required_rows": int(required_rows),
            "data_ready": bool(frame is not None and len(frame) >= int(required_rows)),
            "latest_closed_candle": _latest_timestamp(frame),
            "close": _clean_number(latest.get("close") if latest is not None else None),
            "atr_pct": _atr_pct(frame),
            "adx": _last_float(frame.get("adx")) if frame is not None and "adx" in frame else None,
            "bbw_pct50": _bbw_pct(frame),
        }

    def _liquidity_report(self, symbol: str) -> dict[str, Any]:
        if self.exchange is None or not hasattr(self.exchange, "fetch_ticker"):
            return {"available": False}
        try:
            ticker = self.exchange.fetch_ticker(symbol)
        except Exception as exc:
            return {"available": False, "reason": f"ticker_fetch_failed:{exc}"}

        bid = _as_float(ticker.get("bid"))
        ask = _as_float(ticker.get("ask"))
        last = _as_float(ticker.get("last"))
        quote_volume = _as_float(ticker.get("quoteVolume"))
        spread_pct = None
        if bid is not None and ask is not None and last not in (None, 0.0):
            spread_pct = (ask - bid) / last
        return {
            "available": True,
            "last": _clean_number(last),
            "quote_volume_24h": _clean_number(quote_volume),
            "spread_pct": _clean_number(spread_pct),
        }

    def _regime_report(self, frame_4h: Optional[pd.DataFrame]) -> dict[str, Any]:
        components = RegimeArbiter._feature_components(frame_4h)  # internal runtime parity helper
        return {
            "source": "RegimeArbiter.feature_components",
            "components": _clean_mapping(components),
            "entry_freeze_hint": bool(components.get("squeeze_like") == 1.0),
        }

    def _strategy_report(
        self,
        plugin: StrategyPlugin,
        symbol: str,
        frames: Mapping[str, pd.DataFrame],
    ) -> dict[str, Any]:
        required_ready = all(
            len(frames.get(timeframe, pd.DataFrame())) >= int(warmup)
            for timeframe, warmup in plugin.required_timeframes.items()
        )
        report = {
            "slot_hint": _slot_hint(plugin.id),
            "data_ready": bool(required_ready),
            "diagnostic_only": True,
        }
        if plugin.id.startswith("macd_signal"):
            report["macd_context"] = self._macd_context(plugin, frames)
        elif plugin.id.startswith("donchian_range_fade"):
            report["donchian_context"] = self._donchian_context(plugin, frames)
        return report

    def _macd_context(
        self,
        plugin: StrategyPlugin,
        frames: Mapping[str, pd.DataFrame],
    ) -> dict[str, Any]:
        entry_timeframe = str(plugin.params.get("entry_timeframe") or "4h")
        trend_timeframe = str(plugin.params.get("trend_timeframe") or "1d")
        entry = frames.get(entry_timeframe, pd.DataFrame())
        trend = frames.get(trend_timeframe, pd.DataFrame())

        context: dict[str, Any] = {
            "entry_timeframe": entry_timeframe,
            "trend_timeframe": trend_timeframe,
            "entry_columns_ready": bool(MacdSignalTrendingUp4hStrategy._has_entry_columns(entry)),
            "trend_columns_ready": bool(MacdSignalTrendingUp4hStrategy._has_trend_columns(trend)),
        }
        if context["entry_columns_ready"]:
            latest = entry.iloc[-1]
            previous = entry.iloc[-2]
            atr = _as_float(latest.get("atr"))
            close = _as_float(latest.get("close"))
            ema_20 = _as_float(latest.get("ema_20"))
            macd_value = _as_float(latest.get("macd"))
            context.update(
                {
                    "macd": _clean_number(latest.get("macd")),
                    "macd_signal": _clean_number(latest.get("macd_signal")),
                    "macd_hist": _clean_number(latest.get("macd_hist")),
                    "macd_cross_up_latest": bool(
                        previous["macd"] <= previous["macd_signal"]
                        and latest["macd"] > latest["macd_signal"]
                    ),
                    "macd_above_zero": bool(macd_value is not None and macd_value > 0.0),
                    "entry_extension_atr": _clean_number(
                        abs(close - ema_20) / atr
                        if close is not None and ema_20 is not None and atr not in (None, 0.0)
                        else None
                    ),
                }
            )
        if context["trend_columns_ready"]:
            trend_spread_min = float(plugin.params.get("trend_spread_min", 0.005))
            trend_allowed, trend_spread = MacdSignalTrendingUp4hStrategy._trend_gate(
                trend,
                trend_spread_min,
            )
            latest_trend = trend.iloc[-1]
            context.update(
                {
                    "trend_gate_ready": bool(trend_allowed),
                    "trend_spread": _clean_number(trend_spread),
                    "trend_spread_min": trend_spread_min,
                    "trend_ema_20": _clean_number(latest_trend.get("ema_20")),
                    "trend_ema_50": _clean_number(latest_trend.get("ema_50")),
                }
            )
        return context

    def _donchian_context(
        self,
        plugin: StrategyPlugin,
        frames: Mapping[str, pd.DataFrame],
    ) -> dict[str, Any]:
        timeframe = str(plugin.params.get("timeframe") or "4h")
        frame = frames.get(timeframe, pd.DataFrame())
        donchian_len = int(plugin.params.get("donchian_len", 20))
        range_window = int(plugin.params.get("range_window", 15))
        touch_atr_band = float(plugin.params.get("touch_atr_band", 0.25))
        range_width_cv_max = float(plugin.params.get("range_width_cv_max", 0.10))
        min_lower_touches = int(plugin.params.get("min_lower_touches", 1))
        min_upper_touches = int(plugin.params.get("min_upper_touches", 1))
        rsi_entry = float(plugin.params.get("rsi_entry", 40.0))

        enriched = DonchianRangeFade4hStrategy._with_donchian(
            frame,
            donchian_len,
            range_window,
        )
        columns_ready = DonchianRangeFade4hStrategy._has_entry_columns(enriched, range_window)
        context: dict[str, Any] = {
            "timeframe": timeframe,
            "columns_ready": bool(columns_ready),
            "range_width_cv_max": range_width_cv_max,
            "touch_atr_band": touch_atr_band,
            "rsi_entry": rsi_entry,
        }
        if not columns_ready:
            return context

        latest = enriched.iloc[-1]
        range_state = DonchianRangeFade4hStrategy._range_state(
            enriched,
            range_window=range_window,
            range_width_cv_max=range_width_cv_max,
            touch_atr_band=touch_atr_band,
            min_lower_touches=min_lower_touches,
            min_upper_touches=min_upper_touches,
        )
        lower_entry_band = float(latest["donchian_low"]) + touch_atr_band * float(latest["atr"])
        context.update(
            {
                "range_detected": bool(range_state["range_detected"]),
                "lower_touches": int(range_state["lower_touches"]),
                "upper_touches": int(range_state["upper_touches"]),
                "bars_in_range": int(range_state["bars_in_range"]),
                "width_cv": _clean_number(latest["width_cv"]),
                "donchian_high": _clean_number(latest["donchian_high"]),
                "donchian_low": _clean_number(latest["donchian_low"]),
                "donchian_mid": _clean_number(latest["donchian_mid"]),
                "close": _clean_number(latest["close"]),
                "rsi_14": _clean_number(latest["rsi_14"]),
                "entry_lower_band": _clean_number(lower_entry_band),
                "near_lower_entry_band": bool(float(latest["close"]) <= lower_entry_band),
                "rsi_entry_ready": bool(float(latest["rsi_14"]) < rsi_entry),
            }
        )
        return context


def _slot_hint(strategy_id: str) -> str:
    if strategy_id.startswith("macd_signal"):
        return "slot_a"
    if strategy_id.startswith("donchian_range_fade"):
        return "slot_b"
    return "unassigned"


def _latest_timestamp(frame: Optional[pd.DataFrame]) -> Optional[str]:
    if frame is None or frame.empty:
        return None
    if isinstance(frame.index, pd.DatetimeIndex):
        ts = pd.Timestamp(frame.index[-1])
    elif "timestamp" in frame.columns:
        ts = pd.Timestamp(frame["timestamp"].iloc[-1])
    else:
        return None
    if pd.isna(ts):
        return None
    if ts.tzinfo is None:
        ts = ts.tz_localize(timezone.utc)
    return ts.isoformat()


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_number(value: Any, digits: int = 8) -> Optional[float]:
    number = _as_float(value)
    if number is None:
        return None
    return round(number, digits)


def _clean_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, (int, float)):
            cleaned[str(key)] = _clean_number(value)
        else:
            cleaned[str(key)] = value
    return cleaned


def _last_float(series: Any) -> Optional[float]:
    if series is None:
        return None
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return None
    return _clean_number(clean.iloc[-1])


def _atr_pct(frame: Optional[pd.DataFrame]) -> Optional[float]:
    if frame is None or frame.empty or "atr" not in frame or "close" not in frame:
        return None
    atr = _last_float(frame["atr"])
    close = _last_float(frame["close"])
    if atr is None or close in (None, 0.0):
        return None
    return _clean_number(atr / close)


def _bbw_pct(frame: Optional[pd.DataFrame]) -> Optional[float]:
    if frame is None or frame.empty or "bbw" not in frame:
        return None
    clean = pd.to_numeric(frame["bbw"], errors="coerce").dropna()
    if len(clean) < 20:
        return None
    current = float(clean.iloc[-1])
    history = clean.iloc[-50:] if len(clean) >= 50 else clean
    return _clean_number((history < current).sum() / len(history) * 100.0)


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate runtime scanner diagnostics")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--output", default=None)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    args = _parse_args(argv)
    settings = RuntimeScannerSettings.from_json(args.config)
    if args.output:
        output_path = Path(os.path.expanduser(args.output))
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path
        settings = replace(settings, output_json_path=output_path)

    scanner = RuntimeScanner(settings=settings)
    report = scanner.scan(write=not args.no_write)
    if args.no_write:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True, default=_json_default))
    return 0


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
