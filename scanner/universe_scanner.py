"""Production scanner universe filter.

This module builds the scanner-universe contract consumed by StrategyRuntime.
It is an eligibility filter only: no alpha scoring, no order sizing, no Config
mutation, and no execution hints.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

import pandas as pd

try:
    import ccxt
except ImportError:  # pragma: no cover - exercised only in stripped envs
    ccxt = None  # type: ignore

from trader.config import Config
from trader.infrastructure.data_provider import MarketDataProvider
from trader.utils import drop_unfinished_candle

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "scanner_config.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "scanner_universe.json"
CONTRACT_VERSION = "scanner-universe/v1"

TIMEFRAME_MINUTES = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "2h": 120,
    "4h": 240,
    "6h": 360,
    "8h": 480,
    "12h": 720,
    "1d": 1440,
}


def _default_required_timeframes() -> dict[str, int]:
    return {"4h": 200, "1d": 260}


@dataclass(frozen=True)
class ScannerUniverseSettings:
    output_json_path: Path = DEFAULT_OUTPUT_PATH
    exchange: str = "binance"
    trading_mode: str = "future"
    sandbox_mode: bool = False
    api_max_retries: int = 3
    retry_delay: float = 5.0
    top_n: int = 20
    candidate_scan_limit: int = 60
    min_quote_volume_usd: float = 20_000_000.0
    max_age_minutes: int = 30
    freshness_multiplier: float = 2.5
    max_excluded_symbols: int = 200
    required_timeframes: dict[str, int] = field(default_factory=_default_required_timeframes)
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
    def from_json(cls, path: str | Path | None = None) -> "ScannerUniverseSettings":
        config_path = Path(path) if path else DEFAULT_CONFIG_PATH
        if not config_path.exists():
            return cls()

        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        output_path = Path(data.get("SCANNER_UNIVERSE_OUTPUT_JSON_PATH") or DEFAULT_OUTPUT_PATH)
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path

        required_timeframes = data.get("SCANNER_UNIVERSE_REQUIRED_TIMEFRAMES")
        if not isinstance(required_timeframes, dict):
            required_timeframes = _default_required_timeframes()

        return cls(
            output_json_path=output_path,
            exchange=str(data.get("EXCHANGE", cls.exchange)),
            trading_mode=str(data.get("MARKET_TYPE", data.get("TRADING_MODE", cls.trading_mode))),
            sandbox_mode=bool(data.get("SANDBOX_MODE", cls.sandbox_mode)),
            api_max_retries=int(data.get("API_MAX_RETRIES", cls.api_max_retries)),
            retry_delay=float(data.get("API_DELAY_BETWEEN_BATCHES", cls.retry_delay)),
            top_n=int(data.get("SCANNER_UNIVERSE_TOP_N", cls.top_n)),
            candidate_scan_limit=int(
                data.get("SCANNER_UNIVERSE_CANDIDATE_SCAN_LIMIT", cls.candidate_scan_limit)
            ),
            min_quote_volume_usd=float(
                data.get("SCANNER_UNIVERSE_MIN_QUOTE_VOLUME_USD", cls.min_quote_volume_usd)
            ),
            max_age_minutes=int(
                data.get("SCANNER_UNIVERSE_MAX_AGE_MINUTES", cls.max_age_minutes)
            ),
            freshness_multiplier=float(
                data.get("SCANNER_UNIVERSE_FRESHNESS_MULTIPLIER", cls.freshness_multiplier)
            ),
            required_timeframes={
                str(timeframe): int(warmup)
                for timeframe, warmup in required_timeframes.items()
            },
            excluded_symbols=tuple(
                str(symbol) for symbol in data.get("L1_EXCLUDED_SYMBOLS", cls.excluded_symbols)
            ),
            excluded_patterns=tuple(
                str(pattern)
                for pattern in data.get("L1_EXCLUDED_PATTERNS", cls.excluded_patterns)
            ),
        )


class ScannerUniverseScanner:
    """Build `scanner_universe.json` from liquid Binance futures markets."""

    def __init__(
        self,
        *,
        settings: ScannerUniverseSettings | None = None,
        exchange: Any = None,
        data_provider: Any = None,
    ):
        self.settings = settings or ScannerUniverseSettings.from_json()
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
        scan_time = datetime.now(timezone.utc)
        supported_symbols = self._supported_symbols()
        tickers = self._fetch_tickers()
        ranked = self._rank_tickers(tickers)

        eligible: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        scanned_data_candidates = 0

        for candidate in ranked:
            base_reasons = self._base_exclusion_reasons(candidate, supported_symbols)
            if base_reasons:
                self._append_excluded(excluded, candidate, base_reasons)
                continue

            if len(eligible) >= self.settings.top_n:
                continue

            scanned_data_candidates += 1
            if scanned_data_candidates > self.settings.candidate_scan_limit:
                self._append_excluded(excluded, candidate, ["candidate_scan_limit"])
                continue

            data_report, data_reasons = self._data_readiness(candidate["symbol"], scan_time)
            if data_reasons:
                self._append_excluded(excluded, candidate, data_reasons, {"timeframes": data_report})
                continue

            eligible.append(
                {
                    "symbol": candidate["symbol"],
                    "rank": len(eligible) + 1,
                    "quote_volume_24h": _clean_number(candidate["quote_volume_24h"]),
                    "data_ready": True,
                    "market_supported": True,
                    "reason_codes": [],
                    "timeframes": data_report,
                }
            )

        report = {
            "scanner_contract_version": CONTRACT_VERSION,
            "scan_time": scan_time.isoformat(),
            "expires_at": (scan_time + timedelta(minutes=self.settings.max_age_minutes)).isoformat(),
            "status": "ok",
            "eligible_symbols": eligible,
            "excluded_symbols": excluded[: self.settings.max_excluded_symbols],
            "filter_config": {
                "market_type": self.settings.trading_mode,
                "quote": "USDT",
                "top_n": self.settings.top_n,
                "candidate_scan_limit": self.settings.candidate_scan_limit,
                "min_quote_volume_usd": self.settings.min_quote_volume_usd,
                "mode": "eligibility_only",
                "required_timeframes": dict(self.settings.required_timeframes),
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
        logger.info("Scanner universe wrote %s", path)
        return path

    def _init_exchange(self):
        if ccxt is None:
            raise RuntimeError("ccxt is required for live scanner universe fetches")

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

    def _supported_symbols(self) -> Optional[set[str]]:
        markets = getattr(self.exchange, "markets", None)
        if not markets or not isinstance(markets, Mapping):
            return None

        supported: set[str] = set()
        for key, market in markets.items():
            if isinstance(key, str):
                supported.add(_normalize_symbol(key))
            if isinstance(market, Mapping):
                symbol = market.get("symbol")
                if isinstance(symbol, str):
                    supported.add(_normalize_symbol(symbol))
        return supported or None

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
        supported_symbols: Optional[set[str]],
    ) -> list[str]:
        symbol = str(candidate["symbol"])
        reasons: list[str] = []
        if not symbol.endswith("/USDT"):
            reasons.append("quote_not_usdt")
        if symbol in self.settings.excluded_symbols:
            reasons.append("excluded_symbol")
        if any(pattern in symbol for pattern in self.settings.excluded_patterns):
            reasons.append("excluded_pattern")
        if supported_symbols is not None and symbol not in supported_symbols:
            reasons.append("market_unsupported")

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
    ) -> tuple[dict[str, Any], list[str]]:
        report: dict[str, Any] = {}
        reasons: list[str] = []
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
            report[timeframe] = {
                "rows": int(len(frame)) if frame is not None else 0,
                "required_rows": int(required_rows),
                "latest_closed_candle": latest_ts.isoformat() if latest_ts is not None else None,
                "data_ready": bool(ready),
            }
        return report, sorted(set(reasons))

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
        return drop_unfinished_candle(raw), None

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


def _normalize_symbol(symbol: str) -> str:
    return symbol.split(":")[0] if ":" in symbol else symbol


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
    parser = argparse.ArgumentParser(description="Generate scanner production universe")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--output", default=None)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    args = _parse_args(argv)
    settings = ScannerUniverseSettings.from_json(args.config)
    if args.output:
        output_path = Path(os.path.expanduser(args.output))
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path
        settings = replace(settings, output_json_path=output_path)

    scanner = ScannerUniverseScanner(settings=settings)
    report = scanner.scan(write=not args.no_write)
    if args.no_write:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True, default=_json_default))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
