from unittest.mock import MagicMock, patch

import pandas as pd

from trader.arbiter import RegimeSnapshot
from trader.config import Config
from trader.routing import RegimeRouter, StrategyRoute


def _snapshot(
    label: str,
    *,
    entry_allowed: bool = True,
    confidence: float = 0.85,
    macro_state: str = "DISABLED",
):
    return RegimeSnapshot(
        label=label,
        confidence=confidence,
        direction="LONG" if label == "TRENDING_UP" else None,
        source_regime="TRENDING" if label.startswith("TRENDING") else label,
        detected=label,
        macro_state=macro_state,
        entry_allowed=entry_allowed,
        reason="clean_trend" if entry_allowed else f"{label.lower()}_freeze",
    )


def _scan_df(rows: int = 120) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=rows, freq="1h")
    return pd.DataFrame(
        {
            "open": [100.0] * rows,
            "high": [102.0] * rows,
            "low": [99.0] * rows,
            "close": [101.0] * rows,
            "volume": [1000.0] * rows,
            "adx": [30.0] * rows,
        },
        index=idx,
    )


def _patch_scanner_to_emit_2b(mock_bot, monkeypatch):
    df = _scan_df()
    monkeypatch.setattr(Config, "USE_SCANNER_SYMBOLS", False)
    monkeypatch.setattr(Config, "SYMBOLS", ["ETH/USDT"])
    monkeypatch.setattr(Config, "ENABLE_GRID_TRADING", False)
    monkeypatch.setattr(Config, "REGIME_ARBITER_ENABLED", True)
    monkeypatch.setattr(Config, "BTC_TREND_FILTER_ENABLED", False)
    monkeypatch.setattr(Config, "ENABLE_MTF_CONFIRMATION", False)
    monkeypatch.setattr(Config, "ENABLE_EMA_PULLBACK", False)
    monkeypatch.setattr(Config, "ENABLE_VOLUME_BREAKOUT", False)
    monkeypatch.setattr(Config, "V7_MIN_SIGNAL_TIER", "C")

    mock_bot.fetch_ohlcv = MagicMock(return_value=df)
    mock_bot._check_total_risk = MagicMock(return_value=True)
    mock_bot._execute_trade = MagicMock()

    def update_context():
        mock_bot._regime_arbiter_snapshot = _snapshot("TRENDING_UP")
        return {"regime": "TRENDING", "detected": "TRENDING", "direction": "LONG"}

    mock_bot._update_btc_regime_context = MagicMock(side_effect=update_context)

    patches = [
        patch("trader.signal_scanner.MarketFilter.check_market_condition", return_value=(True, "ok", False)),
        patch("trader.signal_scanner.TechnicalAnalysis.calculate_indicators", side_effect=lambda data: data),
        patch("trader.signal_scanner.TechnicalAnalysis.check_trend", return_value=(True, "trend ok")),
        patch(
            "trader.signal_scanner.detect_2b_with_pivots",
            return_value=(
                True,
                {
                    "side": "LONG",
                    "entry_price": 101.0,
                    "lowest_point": 99.0,
                    "stop_level": 99.0,
                    "atr": 1.0,
                    "vol_ratio": 1.5,
                    "signal_strength": "moderate",
                    "candle_confirmed": True,
                },
            ),
        ),
        patch(
            "trader.signal_scanner.SignalTierSystem.get_tier_diagnostics",
            return_value={
                "tier": "C",
                "tier_multiplier": 1.0,
                "tier_score": 1,
                "mtf_gate_mode": "disabled",
                "volume_grade": "moderate",
                "candle_confirmed": True,
                "tier_component_mtf": 0,
                "tier_component_market": 0,
                "tier_component_volume": 0,
                "tier_component_candle": 1,
            },
        ),
        patch("trader.signal_scanner.TelegramNotifier.notify_arbiter_block"),
    ]
    return patches


def test_router_allows_v54_for_phase1_labels():
    router = RegimeRouter()

    for label in ("TRENDING_UP", "TRENDING_DOWN", "RANGING"):
        decision = router.route(_snapshot(label), signal_type="2B", signal_side="LONG")
        assert decision.allowed is True
        assert decision.selected_strategy == "v54_noscale"


def test_router_freezes_squeeze_neutral_unknown():
    router = RegimeRouter()

    for label in ("SQUEEZE", "NEUTRAL", "UNKNOWN"):
        decision = router.route(
            _snapshot(label, entry_allowed=False),
            signal_type="2B",
            signal_side="LONG",
        )
        assert decision.allowed is False
        assert decision.selected_strategy is None


def test_router_rejects_mixed_as_runtime_label():
    decision = RegimeRouter().route(_snapshot("MIXED"), signal_type="2B", signal_side="LONG")

    assert decision.allowed is False
    assert decision.reason == "invalid_runtime_label:MIXED"


def test_router_priority_selects_single_winner():
    router = RegimeRouter(routes=[
        StrategyRoute(
            strategy_name="fallback",
            signal_types=frozenset({"2B"}),
            allowed_labels=frozenset({"RANGING"}),
            priority=20,
        ),
        StrategyRoute(
            strategy_name="primary",
            signal_types=frozenset({"2B"}),
            allowed_labels=frozenset({"RANGING"}),
            priority=10,
        ),
    ])

    decision = router.route(_snapshot("RANGING"), signal_type="2B", signal_side="LONG")

    assert decision.allowed is True
    assert decision.selected_strategy == "primary"


def test_router_refuses_ambiguous_same_priority():
    routes = [
        StrategyRoute(
            strategy_name="first",
            signal_types=frozenset({"2B"}),
            allowed_labels=frozenset({"RANGING"}),
            priority=10,
        ),
        StrategyRoute(
            strategy_name="second",
            signal_types=frozenset({"2B"}),
            allowed_labels=frozenset({"RANGING"}),
            priority=10,
        ),
    ]

    try:
        RegimeRouter(routes=routes)
    except ValueError as exc:
        assert "ambiguous route priority" in str(exc)
    else:
        raise AssertionError("same-priority duplicate route should fail closed")


def test_router_blocks_macro_stalled(monkeypatch):
    monkeypatch.setattr(Config, "MACRO_OVERLAY_ENABLED", True)

    decision = RegimeRouter().route(
        _snapshot("TRENDING_UP", macro_state="MACRO_STALLED"),
        signal_type="2B",
        signal_side="LONG",
    )

    assert decision.allowed is False
    assert decision.reason == "macro_overlay_blocked:macro_stalled"


def test_router_blocks_macro_bull_short(monkeypatch):
    monkeypatch.setattr(Config, "MACRO_OVERLAY_ENABLED", True)

    decision = RegimeRouter().route(
        _snapshot("TRENDING_UP", macro_state="MACRO_BULL"),
        signal_type="2B",
        signal_side="SHORT",
    )

    assert decision.allowed is False
    assert decision.reason == "macro_overlay_blocked:bull_blocks_short"


def test_router_blocks_macro_bear_long(monkeypatch):
    monkeypatch.setattr(Config, "MACRO_OVERLAY_ENABLED", True)

    decision = RegimeRouter().route(
        _snapshot("TRENDING_DOWN", macro_state="MACRO_BEAR"),
        signal_type="2B",
        signal_side="LONG",
    )

    assert decision.allowed is False
    assert decision.reason == "macro_overlay_blocked:bear_blocks_long"


def test_router_ignores_macro_when_overlay_disabled(monkeypatch):
    monkeypatch.setattr(Config, "MACRO_OVERLAY_ENABLED", False)

    decision = RegimeRouter().route(
        _snapshot("TRENDING_UP", macro_state="MACRO_STALLED"),
        signal_type="2B",
        signal_side="LONG",
    )

    assert decision.allowed is True
    assert decision.selected_strategy == "v54_noscale"


def test_scanner_router_enabled_does_not_call_can_enter(mock_bot, monkeypatch):
    monkeypatch.setattr(Config, "REGIME_ROUTER_ENABLED", True)
    monkeypatch.setattr(Config, "REGIME_ROUTER_TRACE_ENABLED", True)
    mock_bot.regime_arbiter.can_enter = MagicMock(return_value=(False, "should_not_be_called"))
    mock_bot.regime_router = RegimeRouter()

    patches = _patch_scanner_to_emit_2b(mock_bot, monkeypatch)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        mock_bot.signal_scanner.scan_for_signals()

    mock_bot.regime_arbiter.can_enter.assert_not_called()
    mock_bot._execute_trade.assert_called_once()
    signal_details = mock_bot._execute_trade.call_args.args[1]
    assert signal_details["_router_strategy_name"] == "v54_noscale"


def test_scanner_router_disabled_keeps_legacy_can_enter(mock_bot, monkeypatch):
    monkeypatch.setattr(Config, "REGIME_ROUTER_ENABLED", False)
    monkeypatch.setattr(Config, "REGIME_ROUTER_TRACE_ENABLED", True)
    mock_bot.regime_arbiter.can_enter = MagicMock(return_value=(False, "legacy_block"))
    mock_bot.regime_router = RegimeRouter()

    patches = _patch_scanner_to_emit_2b(mock_bot, monkeypatch)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        mock_bot.signal_scanner.scan_for_signals()

    mock_bot.regime_arbiter.can_enter.assert_called_once()
    mock_bot._execute_trade.assert_not_called()


def test_scanner_router_trace_logs_when_disabled(mock_bot, monkeypatch, caplog):
    monkeypatch.setattr(Config, "REGIME_ROUTER_ENABLED", False)
    monkeypatch.setattr(Config, "REGIME_ROUTER_TRACE_ENABLED", True)
    mock_bot.regime_arbiter.can_enter = MagicMock(return_value=(True, "legacy_allow"))
    mock_bot.regime_router = RegimeRouter()

    patches = _patch_scanner_to_emit_2b(mock_bot, monkeypatch)
    with caplog.at_level("INFO", logger="trader.signal_scanner"):
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            mock_bot.signal_scanner.scan_for_signals()

    assert "ETH/USDT: router_trace signal=2B side=LONG" in caplog.text
    assert "allowed=True" in caplog.text
    assert "strategy=v54_noscale" in caplog.text
    mock_bot.regime_arbiter.can_enter.assert_called_once()
    mock_bot._execute_trade.assert_called_once()
