"""Strategy-neutral position state."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

POSITION_SCHEMA_VERSION = 2
LEGACY_MANUAL_STRATEGY_ID = "legacy_manual"


@dataclass
class EntryRecord:
    price: float
    size: float
    stage: int
    time: str


class PositionManager:
    """Single-symbol position state, independent of strategy implementation."""

    def __init__(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        position_size: float,
        strategy_id: Optional[str] = None,
        strategy_version: str = "unknown",
        plugin_state: Optional[dict[str, Any]] = None,
        risk_plan: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
        trade_id: Optional[str] = None,
        schema_version: int = POSITION_SCHEMA_VERSION,
        # Legacy constructor compatibility. These are intentionally not used to
        # load old strategy classes.
        strategy_name: Optional[str] = None,
        is_v6_pyramid: Optional[bool] = None,
        neckline: Optional[float] = None,
        equity_base: float = 0.0,
        initial_r: float = 0.0,
        signal_tier: str = "CENTRAL",
        signal_type: Optional[str] = None,
        market_regime: str = "UNKNOWN",
        strategy: Any = None,
    ):
        self.schema_version = schema_version
        self.symbol = symbol
        self.side = side.upper()
        self.trade_id = trade_id or (
            datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            + "_"
            + symbol.replace("/", "")
        )

        legacy_metadata = dict(metadata or {})
        if strategy_name and strategy_id is None:
            legacy_metadata["legacy_strategy_name"] = strategy_name
        if signal_type and strategy_id is None:
            legacy_metadata["legacy_signal_type"] = signal_type

        self.strategy_id = strategy_id or LEGACY_MANUAL_STRATEGY_ID
        self.strategy_version = strategy_version
        self.plugin_state = dict(plugin_state or {})
        self.risk_plan = dict(risk_plan or {})
        self.metadata = legacy_metadata

        self.stage = 1
        self.entries = [
            EntryRecord(
                price=float(entry_price),
                size=float(position_size),
                stage=1,
                time=datetime.now(timezone.utc).isoformat(),
            )
        ]

        self.total_size = float(position_size)
        self.avg_entry = float(entry_price)
        self.current_sl = float(stop_loss)
        self.initial_sl = float(stop_loss)
        self.initial_r = float(initial_r) if initial_r else self.total_size * abs(self.avg_entry - self.current_sl)
        self.risk_dist = abs(self.avg_entry - self.initial_sl)
        self.original_size = float(position_size)
        self.realized_partial_pnl = 0.0

        self.neckline = neckline
        self.equity_base = equity_base
        self.signal_tier = signal_tier
        self.signal_type = signal_type or self.strategy_id
        self.market_regime = market_regime

        self.stop_order_id: Optional[str] = None
        self.pending_stop_cancels: list[str] = []
        self.is_closed = False
        self.closed_on_exchange = False
        self.external_close_reason: Optional[str] = None
        self.external_exit_price: Optional[float] = None
        self.external_exit_price_source: Optional[str] = None

        self.entry_time = datetime.now(timezone.utc)
        self.monitor_count = 0
        self.highest_price = float(entry_price)
        self.lowest_price = float(entry_price)
        self.atr: Optional[float] = None
        self.exit_reason: Optional[str] = None

        self.entry_adx: Optional[float] = None
        self.fakeout_depth_atr: Optional[float] = None
        self.btc_trend_aligned: Optional[bool] = None
        self.reverse_2b_depth_atr: Optional[float] = None
        self.trend_adx: Optional[float] = None
        self.mtf_aligned: Optional[bool] = None
        self.volume_grade: Optional[str] = None
        self.tier_score: Optional[int] = None

        if strategy is not None:
            logger.warning("PositionManager ignores injected legacy strategy objects")
        if is_v6_pyramid is not None:
            self.metadata["legacy_is_v6_pyramid"] = bool(is_v6_pyramid)

    @property
    def strategy_name(self) -> str:
        return self.strategy_id

    @strategy_name.setter
    def strategy_name(self, value: str) -> None:
        self.metadata["legacy_strategy_name_assignment"] = value
        self.strategy_id = value or LEGACY_MANUAL_STRATEGY_ID

    @property
    def is_v6_pyramid(self) -> bool:
        return False

    @is_v6_pyramid.setter
    def is_v6_pyramid(self, value: bool) -> None:
        self.metadata["legacy_is_v6_pyramid_assignment"] = bool(value)

    @property
    def entry_price(self) -> float:
        return self.avg_entry

    @property
    def current_size(self) -> float:
        return self.total_size

    def monitor(self, *_args, **_kwargs) -> dict[str, Any]:
        return {"action": "HOLD", "reason": "POSITION_MANAGER_NEUTRAL", "new_sl": None, "close_pct": None}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": POSITION_SCHEMA_VERSION,
            "symbol": self.symbol,
            "side": self.side,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "plugin_state": dict(self.plugin_state),
            "risk_plan": dict(self.risk_plan),
            "metadata": dict(self.metadata),
            "stage": self.stage,
            "entries": [asdict(e) for e in self.entries],
            "total_size": self.total_size,
            "avg_entry": self.avg_entry,
            "current_sl": self.current_sl,
            "initial_sl": self.initial_sl,
            "initial_r": self.initial_r,
            "neckline": self.neckline,
            "equity_base": self.equity_base,
            "stop_order_id": self.stop_order_id,
            "entry_time": self.entry_time.isoformat(),
            "highest_price": self.highest_price,
            "lowest_price": self.lowest_price,
            "signal_tier": self.signal_tier,
            "signal_type": self.signal_type,
            "trade_id": self.trade_id,
            "market_regime": self.market_regime,
            "entry_adx": self.entry_adx,
            "fakeout_depth_atr": self.fakeout_depth_atr,
            "btc_trend_aligned": self.btc_trend_aligned,
            "reverse_2b_depth_atr": self.reverse_2b_depth_atr,
            "trend_adx": self.trend_adx,
            "mtf_aligned": self.mtf_aligned,
            "volume_grade": self.volume_grade,
            "tier_score": self.tier_score,
            "pending_stop_cancels": list(self.pending_stop_cancels),
            "original_size": self.original_size,
            "realized_partial_pnl": self.realized_partial_pnl,
            # Compatibility fields for old tools. They no longer select logic.
            "strategy_name": self.strategy_id,
            "strategy_type": "neutral",
            "strategy_state": dict(self.plugin_state),
            "is_v6_pyramid": False,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PositionManager":
        metadata = dict(data.get("metadata") or {})
        strategy_id = data.get("strategy_id")
        if strategy_id is None:
            metadata["legacy_strategy_name"] = data.get("strategy_name")
            metadata["legacy_strategy_type"] = data.get("strategy_type")
            metadata["legacy_is_v6_pyramid"] = data.get("is_v6_pyramid")
            strategy_id = LEGACY_MANUAL_STRATEGY_ID

        pm = cls(
            symbol=data["symbol"],
            side=data["side"],
            entry_price=float(data.get("avg_entry", data.get("entry_price", 0.0))),
            stop_loss=float(data.get("current_sl", data.get("stop_loss", 0.0))),
            position_size=float(data.get("total_size", data.get("position_size", 0.0))),
            strategy_id=strategy_id,
            strategy_version=data.get("strategy_version", "unknown"),
            plugin_state=data.get("plugin_state") or data.get("strategy_state") or data.get("v53_state") or {},
            risk_plan=data.get("risk_plan") or {},
            metadata=metadata,
            trade_id=data.get("trade_id"),
            schema_version=int(data.get("schema_version", 1)),
            neckline=data.get("neckline"),
            equity_base=float(data.get("equity_base", 0.0) or 0.0),
            initial_r=float(data.get("initial_r", 0.0) or 0.0),
            signal_tier=data.get("signal_tier", "CENTRAL"),
            signal_type=data.get("signal_type"),
            market_regime=data.get("market_regime", "UNKNOWN"),
        )

        pm.stage = int(data.get("stage", 1) or 1)
        pm.entries = [EntryRecord(**e) for e in data.get("entries", [])] or pm.entries
        pm.total_size = float(data.get("total_size", pm.total_size))
        pm.avg_entry = float(data.get("avg_entry", pm.avg_entry))
        pm.current_sl = float(data.get("current_sl", pm.current_sl))
        pm.initial_sl = float(data.get("initial_sl", pm.current_sl))
        pm.initial_r = float(data.get("initial_r", pm.initial_r) or pm.initial_r)
        pm.risk_dist = abs(pm.avg_entry - pm.initial_sl) if pm.initial_sl else 0.0
        pm.stop_order_id = data.get("stop_order_id")
        pm.highest_price = float(data.get("highest_price", pm.avg_entry))
        pm.lowest_price = float(data.get("lowest_price", pm.avg_entry))
        pm.pending_stop_cancels = list(data.get("pending_stop_cancels", []))
        pm.original_size = float(data.get("original_size", pm.entries[0].size if pm.entries else pm.total_size))
        pm.realized_partial_pnl = float(data.get("realized_partial_pnl", 0.0) or 0.0)

        entry_time_str = data.get("entry_time")
        if entry_time_str:
            try:
                parsed = datetime.fromisoformat(str(entry_time_str))
                pm.entry_time = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pm.entry_time = datetime.now(timezone.utc)

        pm.entry_adx = data.get("entry_adx")
        pm.fakeout_depth_atr = data.get("fakeout_depth_atr")
        pm.btc_trend_aligned = data.get("btc_trend_aligned")
        pm.reverse_2b_depth_atr = data.get("reverse_2b_depth_atr")
        pm.trend_adx = data.get("trend_adx")
        pm.mtf_aligned = data.get("mtf_aligned")
        pm.volume_grade = data.get("volume_grade")
        pm.tier_score = data.get("tier_score")
        return pm
