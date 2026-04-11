import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.config_parity_check import (
    ParityIssue,
    ParityResult,
    compare_config_parity,
)
from trader.bot import TradingBot
from trader.config import Config
from trader.risk.manager import PrecisionHandler


def _write_config(path: Path, attrs: dict):
    lines = ["class Config:"]
    for key, value in attrs.items():
        lines.append(f"    {key} = {value!r}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_parity_passes_when_aligned(tmp_path):
    json_path = tmp_path / "bot_config.json"
    config_path = tmp_path / "config.py"
    json_path.write_text(json.dumps({
        "enable_ema_pullback": False,
        "enable_volume_breakout": False,
        "enable_grid_trading": False,
        "v7_min_signal_tier": "A",
        "signal_strategy_map": {"2B": "v54_noscale"},
    }), encoding="utf-8")
    _write_config(config_path, {
        "ENABLE_EMA_PULLBACK": False,
        "ENABLE_VOLUME_BREAKOUT": False,
        "ENABLE_GRID_TRADING": False,
        "V7_MIN_SIGNAL_TIER": "A",
        "SIGNAL_STRATEGY_MAP": {"2B": "v54_noscale"},
    })

    result = compare_config_parity(json_path, config_path)

    assert result.issues == ()
    assert result.critical_issues == ()


def test_parity_fails_on_critical_mismatch(monkeypatch):
    issue = ParityIssue(
        category="VALUE_MISMATCH",
        key="ENABLE_EMA_PULLBACK",
        json_value=True,
        config_value=False,
        json_type="bool",
        config_type="bool",
    )
    monkeypatch.setattr(
        "scripts.config_parity_check.compare_config_parity",
        lambda **kwargs: ParityResult((issue,)),
    )

    with pytest.raises(RuntimeError, match="Config parity check failed: VALUE_MISMATCH:ENABLE_EMA_PULLBACK"):
        TradingBot()


def test_parity_warns_on_noncritical_mismatch(monkeypatch, caplog):
    issue = ParityIssue(
        category="VALUE_MISMATCH",
        key="MAX_TOTAL_RISK",
        json_value=0.06,
        config_value=0.05,
        json_type="float",
        config_type="float",
    )
    monkeypatch.setattr(
        "scripts.config_parity_check.compare_config_parity",
        lambda **kwargs: ParityResult((issue,)),
    )

    with caplog.at_level("WARNING"):
        assert TradingBot._verify_config_parity() is True

    assert "non-critical issue" in caplog.text


def test_bypass_env_var_skips_check(monkeypatch):
    def _raise_if_called(**kwargs):
        raise AssertionError("compare_config_parity should not be called")

    monkeypatch.setattr("scripts.config_parity_check.compare_config_parity", _raise_if_called)
    monkeypatch.setenv("BYPASS_CONFIG_PARITY", "1")

    assert TradingBot._verify_config_parity() is True


def test_signal_strategy_map_json_replaces_config_default(tmp_path, monkeypatch):
    config_path = tmp_path / "bot_config.json"
    config_path.write_text(json.dumps({
        "signal_strategy_map": {"2B": "v54_noscale"},
    }), encoding="utf-8")
    monkeypatch.setattr(Config, "SIGNAL_STRATEGY_MAP", {
        "2B": "v54_noscale",
        "EMA_PULLBACK": "v54_noscale",
        "VOLUME_BREAKOUT": "v54_noscale",
    })

    Config.load_from_json(str(config_path))

    assert Config.SIGNAL_STRATEGY_MAP == {"2B": "v54_noscale"}


def test_bot_init_uses_parity_hook(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(TradingBot, "_verify_config_parity", lambda self=None: calls.append("checked") or True)
    mock_exchange = MagicMock()
    mock_exchange.load_markets.return_value = {}
    mock_exchange.markets = {}

    with patch.object(TradingBot, "_init_exchange", return_value=mock_exchange), \
         patch.object(PrecisionHandler, "_load_exchange_info"), \
         patch.object(TradingBot, "_restore_positions"), \
         patch("trader.bot.Config.POSITIONS_JSON_PATH", str(tmp_path / "positions.json")), \
         patch("trader.bot.Config.DB_PATH", str(tmp_path / "perf.db")):
        TradingBot()

    assert calls == ["checked"]
