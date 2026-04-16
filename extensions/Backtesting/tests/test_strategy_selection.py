"""Tests for _apply_strategy_map() strategy override logic."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backtest_engine import STRATEGY_PRESETS, _apply_strategy_map


def _make_pm(
    trade_id: str,
    strategy_name: str = "v53_sop",
    is_v6_pyramid: bool = False,
    neckline=None,
):
    pm = MagicMock()
    pm.trade_id = trade_id
    pm.strategy_name = strategy_name
    pm.is_v6_pyramid = is_v6_pyramid
    pm.neckline = neckline
    return pm


def test_v7_routes_2b_to_v7_ema_to_v53():
    """--strategy v7: 2B→v7_structure, EMA→v53_sop"""
    pm_2b  = _make_pm("t1", strategy_name="v7_structure")
    pm_ema = _make_pm("t2", strategy_name="v53_sop")
    registry = {}
    _apply_strategy_map(
        {"sym1": pm_2b, "sym2": pm_ema},
        STRATEGY_PRESETS["v7"],
        registry,
    )
    assert pm_2b.strategy_name == "v7_structure", "2B signal should use v7_structure"
    assert pm_ema.strategy_name == "v53_sop", "EMA signal should stay v53_sop"
    assert registry["t1"] == "v7"
    assert registry["t2"] == "v53"


def test_v6_forces_all_v6():
    """--strategy v6: 2B and EMA signals both forced to v6_pyramid"""
    pm_2b  = _make_pm("t1", strategy_name="v6_pyramid", is_v6_pyramid=True)
    pm_ema = _make_pm("t2", strategy_name="v53_sop")
    registry = {}
    _apply_strategy_map(
        {"sym1": pm_2b, "sym2": pm_ema},
        STRATEGY_PRESETS["v6"],
        registry,
    )
    assert pm_2b.strategy_name == "v6_pyramid", "2B signal should stay v6_pyramid"
    assert pm_ema.strategy_name == "v6_pyramid", "EMA signal should be forced to v6_pyramid"


def test_v53_forces_all_v53():
    """--strategy v53: 2B signal also forced to v53_sop"""
    pm_2b  = _make_pm("t1", strategy_name="v6_pyramid", is_v6_pyramid=True)
    pm_ema = _make_pm("t2", strategy_name="v53_sop")
    registry = {}
    _apply_strategy_map(
        {"sym1": pm_2b, "sym2": pm_ema},
        STRATEGY_PRESETS["v53"],
        registry,
    )
    assert pm_2b.strategy_name == "v53_sop", "2B signal should be forced to v53_sop"
    assert pm_ema.strategy_name == "v53_sop", "EMA signal should stay v53_sop"


def test_live_mode_no_override():
    """--strategy live (strategy_map=None): no interference"""
    pm_2b  = _make_pm("t1", strategy_name="v7_structure")
    pm_ema = _make_pm("t2", strategy_name="v53_sop")
    registry = {}
    _apply_strategy_map(
        {"sym1": pm_2b, "sym2": pm_ema},
        None,   # live mode
        registry,
    )
    assert pm_2b.strategy_name == "v7_structure", "live mode must not override"
    assert pm_ema.strategy_name == "v53_sop", "live mode must not override"


def test_live_mode_preserves_v54_registry_label():
    """feat-grid live mode: V54 trades should be recorded as v54, not fallback to v53"""
    pm = _make_pm("t1", strategy_name="v54_noscale", neckline=105.0)
    registry = {}
    _apply_strategy_map({"sym": pm}, None, registry)
    assert registry["t1"] == "v54"
    assert pm.strategy_name == "v54_noscale"


def test_v7_override_uses_neckline_to_identify_v54_2b_trade():
    """V54 trade with neckline should be treated as 2B when forcing v7 exits"""
    pm = _make_pm("t1", strategy_name="v54_noscale", neckline=105.0)
    registry = {}
    _apply_strategy_map({"sym": pm}, STRATEGY_PRESETS["v7"], registry)
    assert registry["t1"] == "v54"
    assert pm.strategy_name == "v7_structure"


def test_v7_override_keeps_non_2b_v54_trade_on_v53_path():
    """V54 trade without neckline is treated as EMA/volume when forcing v7 exits"""
    pm = _make_pm("t1", strategy_name="v54_noscale", neckline=None)
    registry = {}
    _apply_strategy_map({"sym": pm}, STRATEGY_PRESETS["v7"], registry)
    assert registry["t1"] == "v54"
    assert pm.strategy_name == "v53_sop"


def test_pm_registry_records_original_signal_type():
    """pm_registry records bot original decision, unaffected by override"""
    pm_2b = _make_pm("t1", strategy_name="v6_pyramid", is_v6_pyramid=True)
    registry = {}
    _apply_strategy_map({"sym": pm_2b}, STRATEGY_PRESETS["v53"], registry)
    assert registry["t1"] == "v6"


def test_pm_registry_idempotent_on_existing_trades():
    """Same PM called multiple times per bar, registry only records first call"""
    pm = _make_pm("t1", strategy_name="v6_pyramid", is_v6_pyramid=True)
    registry = {}
    _apply_strategy_map({"sym": pm}, STRATEGY_PRESETS["v53"], registry)
    assert registry["t1"] == "v6"
    # Second call: pm.strategy_name already changed to v53_sop, registry must not change
    _apply_strategy_map({"sym": pm}, STRATEGY_PRESETS["v53"], registry)
    assert registry["t1"] == "v6", "registry must not be overwritten on second call"
