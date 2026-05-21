"""Research-only Scanner V3 shadow universe diagnostics.

This module widens observation for promoted-style Slot B Donchian predicates,
but it never feeds StrategyRuntime or mutates runtime configuration.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

try:
    import ccxt
except ImportError:  # pragma: no cover - exercised only in stripped envs
    ccxt = None  # type: ignore

from scanner.universe_scanner import TIMEFRAME_MINUTES
from trader.config import Config
from trader.indicators.registry import IndicatorRegistry
from trader.infrastructure.data_provider import MarketDataProvider
from trader.strategies.plugins.donchian_range_fade_4h import DonchianRangeFade4hStrategy
from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013 import (
    DonchianRangeFade4hRangeWidthCv013Strategy,
)
from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013_short import (
    DonchianRangeFade4hRangeWidthCv013ShortStrategy,
)
from trader.utils import drop_unfinished_candle

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "scanner_config.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "scanner_shadow_universe.json"
DEFAULT_CSV_OUTPUT_PATH = PROJECT_ROOT / "scanner_shadow_universe.csv"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "reports" / "scanner_v3_shadow_universe_packet.md"
CONTRACT_VERSION = "scanner-shadow-universe/v1"
SLOT_B_LONG_ID = "donchian_range_fade_4h_range_width_cv_013"
SLOT_B_SHORT_ID = "donchian_range_fade_4h_range_width_cv_013_short"
DIAGNOSTIC_INDICATORS = {"atr", "rsi", "adx", "bbw"}


def _default_required_timeframes() -> dict[str, int]:
    return {"4h": 200}


def _default_watchlist_symbols() -> tuple[str, ...]:
    return ("SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", "LINK/USDT")


@dataclass(frozen=True)
class ShadowUniverseSettings:
    output_json_path: Path = DEFAULT_OUTPUT_PATH
    output_csv_path: Path = DEFAULT_CSV_OUTPUT_PATH
    report_path: Path = DEFAULT_REPORT_PATH
    exchange: str = "binance"
    trading_mode: str = "future"
    sandbox_mode: bool = False
    api_max_retries: int = 3
    retry_delay: float = 5.0
    top_n: int = 20
    candidate_scan_limit: int = 80
    min_quote_volume_usd: float = 20_000_000.0
    max_age_minutes: int = 30
    freshness_multiplier: float = 2.5
    max_excluded_symbols: int = 200
    max_shadow_candidates: int = 200
    required_timeframes: dict[str, int] = field(default_factory=_default_required_timeframes)
    watchlist_symbols: tuple[str, ...] = field(default_factory=_default_watchlist_symbols)
    excluded_symbols: tuple[str, ...] = (
        "USDC/USDT",
        "BUSD/USDT",
        "TUSD/USDT",
        "DAI/USDT",
        "FDUSD/USDT",
    )
    excluded_patterns: tuple[str, ...] = (
        "UP/USDT",
        "DOWN/USDT",
        "BEAR/",
        "BULL/",
        "3L/",
        "3S/",
    )

    @classmethod
    def from_json(cls, path: str | Path | None = None) -> "ShadowUniverseSettings":
        config_path = Path(path) if path else DEFAULT_CONFIG_PATH
        if not config_path.exists():
            return cls()

        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        required_timeframes = data.get("SCANNER_SHADOW_REQUIRED_TIMEFRAMES")
        if not isinstance(required_timeframes, dict):
            required_timeframes = _default_required_timeframes()

        return cls(
            output_json_path=_resolve_output_path(
                data.get("SCANNER_SHADOW_OUTPUT_JSON_PATH"),
                DEFAULT_OUTPUT_PATH,
            ),
            output_csv_path=_resolve_output_path(
                data.get("SCANNER_SHADOW_OUTPUT_CSV_PATH"),
                DEFAULT_CSV_OUTPUT_PATH,
            ),
            report_path=_resolve_output_path(
                data.get("SCANNER_SHADOW_REPORT_PATH"),
                DEFAULT_REPORT_PATH,
            ),
            exchange=str(data.get("EXCHANGE", cls.exchange)),
            trading_mode=str(data.get("MARKET_TYPE", data.get("TRADING_MODE", cls.trading_mode))),
            sandbox_mode=bool(data.get("SANDBOX_MODE", cls.sandbox_mode)),
            api_max_retries=int(data.get("API_MAX_RETRIES", cls.api_max_retries)),
            retry_delay=float(data.get("API_DELAY_BETWEEN_BATCHES", cls.retry_delay)),
            top_n=int(data.get("SCANNER_SHADOW_TOP_N", cls.top_n)),
            candidate_scan_limit=int(
                data.get("SCANNER_SHADOW_CANDIDATE_SCAN_LIMIT", cls.candidate_scan_limit)
            ),
            min_quote_volume_usd=float(
                data.get("SCANNER_SHADOW_MIN_QUOTE_VOLUME_USD", cls.min_quote_volume_usd)
            ),
            max_age_minutes=int(
                data.get("SCANNER_SHADOW_MAX_AGE_MINUTES", cls.max_age_minutes)
            ),
            freshness_multiplier=float(
                data.get("SCANNER_SHADOW_FRESHNESS_MULTIPLIER", cls.freshness_multiplier)
            ),
            required_timeframes={
                str(timeframe): int(warmup)
                for timeframe, warmup in required_timeframes.items()
            },
            watchlist_symbols=tuple(
                str(symbol)
                for symbol in data.get(
                    "SCANNER_SHADOW_WATCHLIST_SYMBOLS",
                    _default_watchlist_symbols(),
                )
            ),
            excluded_symbols=tuple(
                str(symbol) for symbol in data.get("L1_EXCLUDED_SYMBOLS", cls.excluded_symbols)
            ),
            excluded_patterns=tuple(
                str(pattern)
                for pattern in data.get("L1_EXCLUDED_PATTERNS", cls.excluded_patterns)
            ),
        )


class ScannerShadowUniverseScanner:
    """Build one-shot shadow diagnostics for non-runtime symbol observation."""

    def __init__(
        self,
        *,
        settings: ShadowUniverseSettings | None = None,
        exchange: Any = None,
        data_provider: Any = None,
        config_cls: Any = Config,
    ):
        self.settings = settings or ShadowUniverseSettings.from_json()
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
        self._slot_b_plugins = (
            DonchianRangeFade4hRangeWidthCv013Strategy(),
            DonchianRangeFade4hRangeWidthCv013ShortStrategy(),
        )

    def scan(
        self,
        *,
        write: bool = True,
        write_csv: bool = True,
        write_report: bool = False,
    ) -> dict[str, Any]:
        scan_time = datetime.now(timezone.utc)
        baseline_symbols = [str(symbol) for symbol in self.config.SYMBOLS]
        market_metadata = self._market_metadata_by_symbol()
        tickers = self._fetch_tickers()
        ranked = self._rank_tickers(tickers)
        ranked_by_symbol = {str(candidate["symbol"]): candidate for candidate in ranked}

        eligible: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        frames_by_symbol: dict[str, dict[str, pd.DataFrame]] = {}
        scanned_data_candidates = 0

        for candidate in ranked:
            market_meta = market_metadata.get(str(candidate["symbol"]))
            base_reasons = self._base_exclusion_reasons(candidate, market_meta)
            if base_reasons:
                self._append_excluded(excluded, candidate, base_reasons, {"market": market_meta})
                continue

            if len(eligible) >= self.settings.top_n:
                continue

            scanned_data_candidates += 1
            if scanned_data_candidates > self.settings.candidate_scan_limit:
                self._append_excluded(excluded, candidate, ["candidate_scan_limit"])
                continue

            data_report, data_reasons, frames = self._data_readiness(
                str(candidate["symbol"]),
                scan_time,
            )
            if data_reasons:
                self._append_excluded(
                    excluded,
                    candidate,
                    data_reasons,
                    {"timeframes": data_report},
                )
                continue

            symbol = str(candidate["symbol"])
            frames_by_symbol[symbol] = frames
            eligible.append(
                {
                    "symbol": symbol,
                    "rank": len(eligible) + 1,
                    "quote_volume_24h": _clean_number(candidate.get("quote_volume_24h")),
                    **_market_report_fields(market_metadata.get(symbol)),
                    "market_supported": True,
                    "data_ready": True,
                    "timeframes": data_report,
                    "reason_codes": [],
                }
            )

        baseline_diagnostics = self._baseline_diagnostics(
            baseline_symbols,
            frames_by_symbol,
            scan_time,
        )
        shadow_candidates = self._shadow_candidates(eligible, frames_by_symbol, baseline_symbols)
        watchlist_availability = self._watchlist_availability(
            ranked_by_symbol,
            market_metadata,
            frames_by_symbol,
            scan_time,
            {str(item["symbol"]) for item in eligible},
        )

        report = {
            "scanner_contract_version": CONTRACT_VERSION,
            "scan_time": scan_time.isoformat(),
            "expires_at": (scan_time + timedelta(minutes=self.settings.max_age_minutes)).isoformat(),
            "status": "ok",
            "runtime_selection_feeds_trading": False,
            "baseline_runtime_symbols": baseline_symbols,
            "config_scope": {
                "symbols": baseline_symbols,
                "enabled_strategies": list(self.config.ENABLED_STRATEGIES),
                "use_scanner_symbols": bool(self.config.USE_SCANNER_SYMBOLS),
                "scanner_universe_enabled": bool(
                    getattr(self.config, "SCANNER_UNIVERSE_ENABLED", False)
                ),
            },
            "eligible_symbols": eligible,
            "shadow_candidates": shadow_candidates,
            "watchlist_availability": watchlist_availability,
            "baseline_runtime_diagnostics": baseline_diagnostics,
            "excluded_symbols": excluded[: self.settings.max_excluded_symbols],
            "filter_config": {
                "market_type": self.settings.trading_mode,
                "quote": "USDT",
                "mode": "shadow_observation_only",
                "top_n": self.settings.top_n,
                "candidate_scan_limit": self.settings.candidate_scan_limit,
                "min_quote_volume_usd": self.settings.min_quote_volume_usd,
                "required_timeframes": dict(self.settings.required_timeframes),
                "slot_a_expansion": False,
                "slot_b_shadow_diagnostics": True,
                "asset_class_filter": "none_asset_class_tagged_only",
                "contract_type_filter": "linear USDT perpetuals",
                "watchlist_symbols": list(self.settings.watchlist_symbols),
            },
            "deployment_boundary": {
                "feeds_strategy_runtime": False,
                "writes_bot_symbols": False,
                "writes_hot_symbols": False,
                "order_execution": False,
                "risk_sizing": False,
                "runtime_defaults_changed": False,
            },
        }
        if write:
            self.write_json(report)
        if write_csv:
            self.write_csv(report)
        if write_report:
            self.write_markdown_report(report)
        return report

    def write_json(self, report: Mapping[str, Any]) -> Path:
        path = self.settings.output_json_path
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temp_path.write_text(
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True, default=_json_default),
            encoding="utf-8",
        )
        temp_path.replace(path)
        logger.info("Scanner shadow universe wrote %s", path)
        return path

    def write_csv(self, report: Mapping[str, Any]) -> Path:
        path = self.settings.output_csv_path
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        fieldnames = [
            "symbol",
            "strategy_id",
            "side",
            "asset_class",
            "contract_type",
            "candidate_class",
            "decision",
            "runtime_eligible",
            "reason_codes",
            "range_detected",
            "width_cv",
            "range_width_cv_max",
            "lower_touches",
            "upper_touches",
            "near_lower_entry_band",
            "near_upper_entry_band",
            "distance_to_lower_band_atr",
            "distance_to_upper_band_atr",
            "rsi_14",
            "rsi_entry",
        ]
        with temp_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for candidate in report.get("shadow_candidates", []):
                diagnostics = candidate.get("diagnostics", {})
                writer.writerow(
                    {
                        "symbol": candidate.get("symbol"),
                        "strategy_id": candidate.get("strategy_id"),
                        "side": candidate.get("side"),
                        "asset_class": candidate.get("asset_class"),
                        "contract_type": candidate.get("contract_type"),
                        "candidate_class": candidate.get("candidate_class"),
                        "decision": candidate.get("decision"),
                        "runtime_eligible": candidate.get("runtime_eligible"),
                        "reason_codes": "|".join(candidate.get("reason_codes", [])),
                        "range_detected": diagnostics.get("range_detected"),
                        "width_cv": diagnostics.get("width_cv"),
                        "range_width_cv_max": diagnostics.get("range_width_cv_max"),
                        "lower_touches": diagnostics.get("lower_touches"),
                        "upper_touches": diagnostics.get("upper_touches"),
                        "near_lower_entry_band": diagnostics.get("near_lower_entry_band"),
                        "near_upper_entry_band": diagnostics.get("near_upper_entry_band"),
                        "distance_to_lower_band_atr": diagnostics.get(
                            "distance_to_lower_band_atr"
                        ),
                        "distance_to_upper_band_atr": diagnostics.get(
                            "distance_to_upper_band_atr"
                        ),
                        "rsi_14": diagnostics.get("rsi_14"),
                        "rsi_entry": diagnostics.get("rsi_entry"),
                    }
                )
        temp_path.replace(path)
        logger.info("Scanner shadow universe wrote %s", path)
        return path

    def write_markdown_report(self, report: Mapping[str, Any]) -> Path:
        path = self.settings.report_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_markdown_report(report), encoding="utf-8")
        logger.info("Scanner shadow universe report wrote %s", path)
        return path

    def _init_exchange(self):
        if ccxt is None:
            raise RuntimeError("ccxt is required for live scanner shadow fetches")

        exchange_cls = getattr(ccxt, self.settings.exchange)
        options: dict[str, Any] = {"enableRateLimit": True, "options": {}}
        if self.settings.trading_mode in {"future", "futures"}:
            options["options"]["defaultType"] = "future"
        exchange = exchange_cls(options)
        if hasattr(exchange, "set_sandbox_mode"):
            exchange.set_sandbox_mode(self.settings.sandbox_mode)
        exchange.load_markets()
        return exchange

    def _fetch_tickers(self) -> Mapping[str, Any]:
        if self.exchange is None or not hasattr(self.exchange, "fetch_tickers"):
            return {}
        tickers = self.exchange.fetch_tickers()
        return tickers if isinstance(tickers, Mapping) else {}

    def _market_metadata_by_symbol(self) -> dict[str, dict[str, Any]]:
        markets = getattr(self.exchange, "markets", None)
        if not markets or not isinstance(markets, Mapping):
            return {}

        metadata: dict[str, dict[str, Any]] = {}
        for key, market in markets.items():
            if not isinstance(market, Mapping):
                continue
            raw_symbol = market.get("symbol") if isinstance(market.get("symbol"), str) else key
            if not isinstance(raw_symbol, str):
                continue
            symbol = _normalize_symbol(raw_symbol)
            candidate = _market_metadata(symbol, market)
            existing = metadata.get(symbol)
            if existing is None or _market_metadata_score(candidate) > _market_metadata_score(existing):
                metadata[symbol] = candidate
        return metadata

    def _rank_tickers(self, tickers: Mapping[str, Any]) -> list[dict[str, Any]]:
        candidates_by_symbol: dict[str, dict[str, Any]] = {}
        for key, ticker in tickers.items():
            if not isinstance(ticker, Mapping):
                continue
            raw_symbol = ticker.get("symbol") or key
            if not isinstance(raw_symbol, str):
                continue
            symbol = _normalize_symbol(raw_symbol)
            quote_volume = _as_float(ticker.get("quoteVolume"))
            candidate = {
                "symbol": symbol,
                "quote_volume_24h": quote_volume,
                "raw_symbol": raw_symbol,
            }
            existing = candidates_by_symbol.get(symbol)
            if existing is None or _volume_sort_value(candidate) > _volume_sort_value(existing):
                candidates_by_symbol[symbol] = candidate
        return sorted(
            candidates_by_symbol.values(),
            key=_volume_sort_value,
            reverse=True,
        )

    def _base_exclusion_reasons(
        self,
        candidate: Mapping[str, Any],
        market_meta: Optional[Mapping[str, Any]],
    ) -> list[str]:
        symbol = str(candidate["symbol"])
        reasons: list[str] = []
        if not symbol.endswith("/USDT"):
            reasons.append("quote_not_usdt")
        if symbol in self.settings.excluded_symbols:
            reasons.append("excluded_symbol")
        if any(_matches_excluded_pattern(symbol, pattern) for pattern in self.settings.excluded_patterns):
            reasons.append("excluded_pattern")
        if market_meta is None:
            reasons.append("market_unsupported")
        else:
            if not bool(market_meta.get("active", True)):
                reasons.append("inactive_market")
            if not bool(market_meta.get("linear")) or market_meta.get("settle") != "USDT":
                reasons.append("not_linear_usdt_contract")
            if "PERPETUAL" not in str(market_meta.get("contract_type") or "").upper():
                reasons.append("not_perpetual_contract")

        quote_volume = candidate.get("quote_volume_24h")
        if quote_volume is None:
            reasons.append("volume_unavailable")
        elif float(quote_volume) < self.settings.min_quote_volume_usd:
            reasons.append("low_volume")
        return reasons

    def _data_readiness(
        self,
        symbol: str,
        scan_time: datetime,
    ) -> tuple[dict[str, Any], list[str], dict[str, pd.DataFrame]]:
        report: dict[str, Any] = {}
        reasons: list[str] = []
        frames: dict[str, pd.DataFrame] = {}
        for timeframe, required_rows in self.settings.required_timeframes.items():
            frame, fetch_reason = self._fetch_closed_frame(symbol, timeframe, required_rows)
            latest_ts = _latest_timestamp(frame)
            fresh = self._is_fresh(timeframe, latest_ts, scan_time)
            ready = frame is not None and len(frame) >= int(required_rows) and fresh
            if fetch_reason:
                reasons.append(f"{fetch_reason}:{timeframe}")
            if frame is None or len(frame) < int(required_rows):
                reasons.append(f"insufficient_data:{timeframe}")
            if not fresh:
                reasons.append(f"stale_data:{timeframe}")
            frames[timeframe] = frame
            report[timeframe] = {
                "rows": int(len(frame)) if frame is not None else 0,
                "required_rows": int(required_rows),
                "latest_closed_candle": latest_ts.isoformat() if latest_ts is not None else None,
                "fresh": bool(fresh),
                "data_ready": bool(ready),
            }
        return report, sorted(set(reasons)), frames

    def _fetch_closed_frame(
        self,
        symbol: str,
        timeframe: str,
        required_rows: int,
    ) -> tuple[pd.DataFrame, Optional[str]]:
        try:
            raw = self.data_provider.fetch_ohlcv(symbol, timeframe, limit=max(required_rows + 1, 2))
        except Exception:
            return pd.DataFrame(), "fetch_failed"
        if raw is None or raw.empty:
            return pd.DataFrame(), "fetch_empty"
        frame = drop_unfinished_candle(raw)
        return IndicatorRegistry.apply(frame, DIAGNOSTIC_INDICATORS), None

    def _is_fresh(
        self,
        timeframe: str,
        latest_ts: Optional[pd.Timestamp],
        scan_time: datetime,
    ) -> bool:
        if latest_ts is None:
            return False
        if latest_ts.tzinfo is None:
            latest_ts = latest_ts.tz_localize(timezone.utc)
        allowed_minutes = TIMEFRAME_MINUTES.get(timeframe, 60) * self.settings.freshness_multiplier
        age_minutes = (pd.Timestamp(scan_time) - latest_ts).total_seconds() / 60.0
        return age_minutes <= allowed_minutes

    def _append_excluded(
        self,
        excluded: list[dict[str, Any]],
        candidate: Mapping[str, Any],
        reason_codes: list[str],
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        if len(excluded) >= self.settings.max_excluded_symbols:
            return
        item = {
            "symbol": candidate["symbol"],
            "reason_codes": sorted(set(reason_codes)),
            "quote_volume_24h": _clean_number(candidate.get("quote_volume_24h")),
        }
        if extra:
            item.update(dict(extra))
        excluded.append(item)

    def _baseline_diagnostics(
        self,
        baseline_symbols: list[str],
        frames_by_symbol: dict[str, dict[str, pd.DataFrame]],
        scan_time: datetime,
    ) -> dict[str, Any]:
        diagnostics: dict[str, Any] = {}
        for symbol in baseline_symbols:
            frames = frames_by_symbol.get(symbol)
            timeframes: dict[str, Any] = {}
            if frames is None:
                timeframes, _reasons, frames = self._data_readiness(symbol, scan_time)
                frames_by_symbol[symbol] = frames
            else:
                for timeframe, required_rows in self.settings.required_timeframes.items():
                    frame = frames.get(timeframe, pd.DataFrame())
                    latest_ts = _latest_timestamp(frame)
                    fresh = self._is_fresh(timeframe, latest_ts, scan_time)
                    timeframes[timeframe] = {
                        "rows": int(len(frame)),
                        "required_rows": int(required_rows),
                        "latest_closed_candle": (
                            latest_ts.isoformat() if latest_ts is not None else None
                        ),
                        "fresh": bool(fresh),
                        "data_ready": bool(len(frame) >= int(required_rows) and fresh),
                    }

            diagnostics[symbol] = {
                "runtime_symbol": True,
                "timeframes": timeframes,
                "slot_b": [
                    self._donchian_candidate(
                        symbol=symbol,
                        plugin=plugin,
                        frame=frames.get("4h", pd.DataFrame()),
                        runtime_symbol=True,
                    )
                    for plugin in self._slot_b_plugins
                ],
            }
        return diagnostics

    def _shadow_candidates(
        self,
        eligible: list[dict[str, Any]],
        frames_by_symbol: Mapping[str, Mapping[str, pd.DataFrame]],
        baseline_symbols: list[str],
    ) -> list[dict[str, Any]]:
        baseline_set = set(baseline_symbols)
        candidates: list[dict[str, Any]] = []
        for item in eligible:
            symbol = str(item["symbol"])
            if symbol in baseline_set:
                continue
            frame = frames_by_symbol.get(symbol, {}).get("4h", pd.DataFrame())
            for plugin in self._slot_b_plugins:
                candidates.append(
                    self._donchian_candidate(
                        symbol=symbol,
                        plugin=plugin,
                        frame=frame,
                        runtime_symbol=False,
                        market_fields={
                            "asset_class": item.get("asset_class"),
                            "contract_type": item.get("contract_type"),
                            "underlying_subtype": item.get("underlying_subtype"),
                            "market_type": item.get("market_type"),
                            "linear": item.get("linear"),
                            "settle": item.get("settle"),
                        },
                    )
                )
                if len(candidates) >= self.settings.max_shadow_candidates:
                    return candidates
        return candidates

    def _watchlist_availability(
        self,
        ranked_by_symbol: Mapping[str, Mapping[str, Any]],
        market_metadata: Mapping[str, Mapping[str, Any]],
        frames_by_symbol: dict[str, dict[str, pd.DataFrame]],
        scan_time: datetime,
        eligible_symbols: set[str],
    ) -> list[dict[str, Any]]:
        availability: list[dict[str, Any]] = []
        blocking_reasons = {
            "market_unsupported",
            "inactive_market",
            "not_linear_usdt_contract",
            "not_perpetual_contract",
            "quote_not_usdt",
            "excluded_symbol",
            "excluded_pattern",
        }
        for symbol in dict.fromkeys(str(item) for item in self.settings.watchlist_symbols):
            candidate = ranked_by_symbol.get(
                symbol,
                {
                    "symbol": symbol,
                    "quote_volume_24h": None,
                    "raw_symbol": symbol,
                },
            )
            market_meta = market_metadata.get(symbol)
            reason_codes = self._base_exclusion_reasons(candidate, market_meta)
            data_report: dict[str, Any] = {}
            data_reasons: list[str] = []
            if not (set(reason_codes) & blocking_reasons):
                if symbol in frames_by_symbol:
                    data_report, data_reasons = self._data_report_from_frames(
                        frames_by_symbol[symbol],
                        scan_time,
                    )
                else:
                    data_report, data_reasons, frames = self._data_readiness(symbol, scan_time)
                    frames_by_symbol[symbol] = frames

            reason_codes = sorted(set(reason_codes + data_reasons))
            availability.append(
                {
                    "symbol": symbol,
                    "quote_volume_24h": _clean_number(candidate.get("quote_volume_24h")),
                    **_market_report_fields(market_meta),
                    "market_supported": market_meta is not None,
                    "data_ready": bool(data_report) and not data_reasons,
                    "in_top_eligible": symbol in eligible_symbols,
                    "timeframes": data_report,
                    "reason_codes": reason_codes,
                }
            )
        return availability

    def _data_report_from_frames(
        self,
        frames: Mapping[str, pd.DataFrame],
        scan_time: datetime,
    ) -> tuple[dict[str, Any], list[str]]:
        report: dict[str, Any] = {}
        reasons: list[str] = []
        for timeframe, required_rows in self.settings.required_timeframes.items():
            frame = frames.get(timeframe, pd.DataFrame())
            latest_ts = _latest_timestamp(frame)
            fresh = self._is_fresh(timeframe, latest_ts, scan_time)
            ready = frame is not None and len(frame) >= int(required_rows) and fresh
            if frame is None or len(frame) < int(required_rows):
                reasons.append(f"insufficient_data:{timeframe}")
            if not fresh:
                reasons.append(f"stale_data:{timeframe}")
            report[timeframe] = {
                "rows": int(len(frame)) if frame is not None else 0,
                "required_rows": int(required_rows),
                "latest_closed_candle": latest_ts.isoformat() if latest_ts is not None else None,
                "fresh": bool(fresh),
                "data_ready": bool(ready),
            }
        return report, sorted(set(reasons))

    def _donchian_candidate(
        self,
        *,
        symbol: str,
        plugin: DonchianRangeFade4hStrategy,
        frame: pd.DataFrame,
        runtime_symbol: bool,
        market_fields: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        side = "SHORT" if plugin.id == SLOT_B_SHORT_ID else "LONG"
        diagnostics = _donchian_diagnostics(plugin, frame, side)
        candidate_class, reason_codes = _classify_donchian(diagnostics, side)
        return {
            "symbol": symbol,
            "strategy_id": plugin.id,
            "slot_hint": "slot_b",
            "side": side,
            **dict(market_fields or {}),
            "candidate_class": candidate_class,
            "decision": "observe",
            "runtime_eligible": bool(runtime_symbol),
            "diagnostics": diagnostics,
            "reason_codes": reason_codes,
        }


def _donchian_diagnostics(
    plugin: DonchianRangeFade4hStrategy,
    frame: pd.DataFrame,
    side: str,
) -> dict[str, Any]:
    timeframe = str(plugin.params.get("timeframe") or "4h")
    donchian_len = int(plugin.params.get("donchian_len", 20))
    range_window = int(plugin.params.get("range_window", 15))
    touch_atr_band = float(plugin.params.get("touch_atr_band", 0.25))
    range_width_cv_max = float(plugin.params.get("range_width_cv_max", 0.13))
    min_lower_touches = int(plugin.params.get("min_lower_touches", 1))
    min_upper_touches = int(plugin.params.get("min_upper_touches", 1))
    rsi_entry = float(plugin.params.get("rsi_entry", 60.0 if side == "SHORT" else 40.0))

    enriched = DonchianRangeFade4hStrategy._with_donchian(
        frame,
        donchian_len,
        range_window,
    )
    columns_ready = DonchianRangeFade4hStrategy._has_entry_columns(enriched, range_window)
    diagnostics: dict[str, Any] = {
        "timeframe": timeframe,
        "columns_ready": bool(columns_ready),
        "range_width_cv_max": range_width_cv_max,
        "touch_atr_band": touch_atr_band,
        "rsi_entry": rsi_entry,
    }
    if not columns_ready:
        return diagnostics

    latest = enriched.iloc[-1]
    range_state = DonchianRangeFade4hStrategy._range_state(
        enriched,
        range_window=range_window,
        range_width_cv_max=range_width_cv_max,
        touch_atr_band=touch_atr_band,
        min_lower_touches=min_lower_touches,
        min_upper_touches=min_upper_touches,
    )
    close = float(latest["close"])
    atr = float(latest["atr"])
    lower_entry_band = float(latest["donchian_low"]) + touch_atr_band * atr
    upper_entry_band = float(latest["donchian_high"]) - touch_atr_band * atr
    rsi_14 = float(latest["rsi_14"])
    near_lower = close <= lower_entry_band
    near_upper = close >= upper_entry_band

    diagnostics.update(
        {
            "range_detected": bool(range_state["range_detected"]),
            "width_cv_ok": bool(float(latest["width_cv"]) < range_width_cv_max),
            "lower_touches": int(range_state["lower_touches"]),
            "upper_touches": int(range_state["upper_touches"]),
            "bars_in_range": int(range_state["bars_in_range"]),
            "width_cv": _clean_number(latest["width_cv"]),
            "donchian_high": _clean_number(latest["donchian_high"]),
            "donchian_low": _clean_number(latest["donchian_low"]),
            "donchian_mid": _clean_number(latest["donchian_mid"]),
            "close": _clean_number(close),
            "atr": _clean_number(atr),
            "rsi_14": _clean_number(rsi_14),
            "entry_lower_band": _clean_number(lower_entry_band),
            "entry_upper_band": _clean_number(upper_entry_band),
            "near_lower_entry_band": bool(near_lower),
            "near_upper_entry_band": bool(near_upper),
            "distance_to_lower_band_atr": _clean_number(
                (close - lower_entry_band) / atr if atr else None
            ),
            "distance_to_upper_band_atr": _clean_number(
                (upper_entry_band - close) / atr if atr else None
            ),
            "rsi_long_ready": bool(rsi_14 < rsi_entry) if side == "LONG" else None,
            "rsi_short_ready": bool(rsi_14 > rsi_entry) if side == "SHORT" else None,
        }
    )
    return diagnostics


def _classify_donchian(diagnostics: Mapping[str, Any], side: str) -> tuple[str, list[str]]:
    if not diagnostics.get("columns_ready"):
        return "eligible_only", ["indicator_columns_not_ready"]

    range_detected = bool(diagnostics.get("range_detected"))
    near_band = bool(
        diagnostics.get("near_upper_entry_band")
        if side == "SHORT"
        else diagnostics.get("near_lower_entry_band")
    )
    rsi_ready = bool(
        diagnostics.get("rsi_short_ready")
        if side == "SHORT"
        else diagnostics.get("rsi_long_ready")
    )
    width_cv_ok = bool(diagnostics.get("width_cv_ok"))
    touches = int(diagnostics.get("lower_touches") or 0) + int(
        diagnostics.get("upper_touches") or 0
    )

    reason_codes: list[str] = []
    if not range_detected:
        reason_codes.append("range_not_detected")
    if not near_band:
        reason_codes.append("not_near_upper_band" if side == "SHORT" else "not_near_lower_band")
    if not rsi_ready:
        reason_codes.append("rsi_not_ready")

    if range_detected and near_band and rsi_ready:
        return "entry_ready_shadow", []
    if range_detected and (near_band or rsi_ready):
        return "near_setup", reason_codes
    if range_detected or (width_cv_ok and touches >= 2):
        return "regime_compatible", reason_codes
    return "eligible_only", reason_codes


def _markdown_report(report: Mapping[str, Any]) -> str:
    candidates = list(report.get("shadow_candidates", []))
    eligible = list(report.get("eligible_symbols", []))
    excluded = list(report.get("excluded_symbols", []))
    watchlist = list(report.get("watchlist_availability", []))
    class_counts = Counter(str(item.get("candidate_class")) for item in candidates)
    asset_counts = Counter(str(item.get("asset_class")) for item in eligible)
    reason_counts = Counter(
        reason for item in excluded for reason in item.get("reason_codes", [])
    )
    candidate_reason_counts = Counter(
        reason for item in candidates for reason in item.get("reason_codes", [])
    )
    baseline = report.get("baseline_runtime_diagnostics", {})

    lines = [
        "# Scanner V3 Shadow Universe Packet",
        "",
        f"Date: {_date_from_iso(str(report.get('scan_time', '')))}",
        "Branch: `codex/post-promotion-control-20260430`",
        "Status: `STAGE_A_ONE_SHOT_SHADOW_PACKET`",
        "",
        "## Executive Read",
        "",
        "Scanner V3 Stage A produced a one-shot shadow-universe packet without "
        "feeding StrategyRuntime or changing runtime defaults.",
        "",
        "This packet is observational only. It does not authorize symbol "
        "expansion, scanner runtime consumption, strategy promotion, threshold "
        "loosening, order execution, or risk sizing.",
        "",
        "## Boundary Check",
        "",
        "| item | value |",
        "| --- | --- |",
        f"| runtime_selection_feeds_trading | `{report.get('runtime_selection_feeds_trading')}` |",
        f"| baseline runtime symbols | `{', '.join(report.get('baseline_runtime_symbols', []))}` |",
        f"| use scanner symbols | `{report.get('config_scope', {}).get('use_scanner_symbols')}` |",
        f"| scanner universe enabled | `{report.get('config_scope', {}).get('scanner_universe_enabled')}` |",
        "| Slot A expansion | `False` |",
        "| Slot B shadow diagnostics | `True` |",
        "",
        "## Strategy Compatibility",
        "",
        "| slot | promoted scope | shadow treatment |",
        "| --- | --- | --- |",
        "| Slot A LONG | `BTC/USDT` only | non-BTC symbols are not evaluated for Slot A |",
        "| Slot B LONG | `BTC/USDT`, `ETH/USDT` runtime only | non-runtime linear USDT perpetuals get diagnostics only |",
        "| Slot B SHORT | `BTC/USDT`, `ETH/USDT` runtime only | non-runtime linear USDT perpetuals get diagnostics only |",
        "",
        "## Summary",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| eligible symbols | {len(eligible)} |",
        f"| shadow candidate rows | {len(candidates)} |",
        f"| entry-ready shadow rows | {class_counts.get('entry_ready_shadow', 0)} |",
        f"| near-setup rows | {class_counts.get('near_setup', 0)} |",
        f"| regime-compatible rows | {class_counts.get('regime_compatible', 0)} |",
        f"| eligible-only rows | {class_counts.get('eligible_only', 0)} |",
        f"| eligible COIN rows | {asset_counts.get('COIN', 0)} |",
        f"| eligible non-COIN rows | {len(eligible) - asset_counts.get('COIN', 0)} |",
        f"| excluded symbols | {len(excluded)} |",
        "",
        "## Top Eligible Symbols",
        "",
        "| rank | symbol | asset class | contract | quote volume 24h | data ready |",
        "| ---: | --- | --- | --- | ---: | --- |",
    ]
    for item in eligible[:20]:
        lines.append(
            f"| {item.get('rank')} | `{item.get('symbol')}` | "
            f"`{item.get('asset_class')}` | `{item.get('contract_type')}` | "
            f"{_fmt_number(item.get('quote_volume_24h'))} | `{item.get('data_ready')}` |"
        )

    lines.extend(
        [
            "",
            "## Watchlist Availability",
            "",
            "| symbol | asset class | contract | quote volume 24h | data ready | in top eligible | reason codes |",
            "| --- | --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for item in watchlist:
        lines.append(
            f"| `{item.get('symbol')}` | `{item.get('asset_class')}` | "
            f"`{item.get('contract_type')}` | "
            f"{_fmt_number(item.get('quote_volume_24h'))} | `{item.get('data_ready')}` | "
            f"`{item.get('in_top_eligible')}` | "
            f"`{', '.join(item.get('reason_codes', [])) or 'none'}` |"
        )

    lines.extend(
        [
            "",
            "## Top Shadow Candidates",
            "",
            "| symbol | side | asset class | class | reason codes | width CV | RSI |",
            "| --- | --- | --- | --- | --- | ---: | ---: |",
        ]
    )
    for item in candidates[:30]:
        diag = item.get("diagnostics", {})
        lines.append(
            f"| `{item.get('symbol')}` | `{item.get('side')}` | "
            f"`{item.get('asset_class')}` | "
            f"`{item.get('candidate_class')}` | "
            f"`{', '.join(item.get('reason_codes', [])) or 'none'}` | "
            f"{_fmt_number(diag.get('width_cv'))} | {_fmt_number(diag.get('rsi_14'))} |"
        )

    lines.extend(
        [
            "",
            "## Baseline Slot B Diagnostics",
            "",
            "| symbol | side | class | reason codes | rows 4h |",
            "| --- | --- | --- | --- | ---: |",
        ]
    )
    for symbol, item in baseline.items():
        rows_4h = item.get("timeframes", {}).get("4h", {}).get("rows")
        for slot in item.get("slot_b", []):
            lines.append(
                f"| `{symbol}` | `{slot.get('side')}` | `{slot.get('candidate_class')}` | "
                f"`{', '.join(slot.get('reason_codes', [])) or 'none'}` | "
                f"{rows_4h} |"
            )

    lines.extend(
        [
            "",
            "## Reason-Code Distribution",
            "",
            "| source | reason | count |",
            "| --- | --- | ---: |",
        ]
    )
    for reason, count in sorted(candidate_reason_counts.items()):
        lines.append(f"| shadow candidate | `{reason}` | {count} |")
    for reason, count in sorted(reason_counts.items()):
        lines.append(f"| exclusion | `{reason}` | {count} |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Stage A proves the shadow scanner can separate baseline BTC/ETH diagnostics "
            "from non-runtime shadow symbols.",
            "- Economic value is not evaluated here; that requires Stage C historical "
            "replay and holdout review.",
            "- Runtime selection remains fixed on the promoted BTC/ETH baseline.",
            "",
        ]
    )
    return "\n".join(lines)


def _resolve_output_path(value: Any, default: Path) -> Path:
    output_path = Path(value) if value else default
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    return output_path


def _market_metadata(symbol: str, market: Mapping[str, Any]) -> dict[str, Any]:
    info = market.get("info") if isinstance(market.get("info"), Mapping) else {}
    return {
        "symbol": symbol,
        "raw_symbol": market.get("symbol"),
        "market_id": market.get("id"),
        "base": market.get("base"),
        "quote": market.get("quote"),
        "settle": market.get("settle"),
        "market_type": market.get("type"),
        "active": bool(market.get("active", True)),
        "contract": bool(market.get("contract")),
        "swap": bool(market.get("swap")),
        "linear": bool(market.get("linear")),
        "contract_type": info.get("contractType"),
        "underlying_type": info.get("underlyingType"),
        "underlying_subtype": info.get("underlyingSubType"),
    }


def _market_metadata_score(metadata: Mapping[str, Any]) -> int:
    score = 0
    score += 16 if metadata.get("active") else 0
    score += 16 if metadata.get("contract") else 0
    score += 16 if metadata.get("swap") else 0
    score += 16 if metadata.get("linear") else 0
    score += 8 if metadata.get("settle") == "USDT" else 0
    score += 4 if "PERPETUAL" in str(metadata.get("contract_type") or "").upper() else 0
    score += 4 if str(metadata.get("underlying_type") or "").upper() == "COIN" else 0
    return score


def _market_report_fields(metadata: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    if metadata is None:
        return {
            "asset_class": None,
            "contract_type": None,
            "underlying_subtype": None,
            "market_type": None,
            "linear": None,
            "settle": None,
        }
    return {
        "asset_class": metadata.get("underlying_type"),
        "contract_type": metadata.get("contract_type"),
        "underlying_subtype": metadata.get("underlying_subtype"),
        "market_type": metadata.get("market_type"),
        "linear": metadata.get("linear"),
        "settle": metadata.get("settle"),
    }


def _normalize_symbol(symbol: str) -> str:
    return symbol.split(":")[0] if ":" in symbol else symbol


def _matches_excluded_pattern(symbol: str, pattern: str) -> bool:
    base = symbol.split("/")[0]
    token = pattern.split("/")[0]
    if token in {"UP", "DOWN", "BEAR", "BULL", "3L", "3S"}:
        return base.endswith(token) and len(base) > len(token) + 1
    return pattern in symbol


def _latest_timestamp(frame: Optional[pd.DataFrame]) -> Optional[pd.Timestamp]:
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
    return ts


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


def _volume_sort_value(candidate: Mapping[str, Any]) -> float:
    quote_volume = candidate.get("quote_volume_24h")
    return float(quote_volume) if quote_volume is not None else -1.0


def _fmt_number(value: Any) -> str:
    number = _as_float(value)
    if number is None:
        return "n/a"
    if abs(number) >= 1_000_000:
        return f"{number:,.0f}"
    return f"{number:.4f}"


def _date_from_iso(value: str) -> str:
    try:
        return datetime.fromisoformat(value).date().isoformat()
    except ValueError:
        return datetime.now(timezone.utc).date().isoformat()


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Scanner V3 shadow universe diagnostics")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--output", default=None)
    parser.add_argument("--csv-output", default=None)
    parser.add_argument("--report", default=None)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--no-csv", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    args = _parse_args(argv)
    settings = ShadowUniverseSettings.from_json(args.config)
    if args.output:
        settings = replace(settings, output_json_path=_resolve_output_path(args.output, DEFAULT_OUTPUT_PATH))
    if args.csv_output:
        settings = replace(
            settings,
            output_csv_path=_resolve_output_path(args.csv_output, DEFAULT_CSV_OUTPUT_PATH),
        )
    if args.report:
        settings = replace(settings, report_path=_resolve_output_path(args.report, DEFAULT_REPORT_PATH))

    scanner = ScannerShadowUniverseScanner(settings=settings)
    report = scanner.scan(
        write=not args.no_write,
        write_csv=not args.no_csv and not args.no_write,
        write_report=bool((args.write_report or args.report) and not args.no_write),
    )
    if args.no_write:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True, default=_json_default))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
