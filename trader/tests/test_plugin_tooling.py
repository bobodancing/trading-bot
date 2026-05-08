from pathlib import Path

from trader.config import Config
from trader.strategies.plugins._catalog import (
    CATALOG_CLASS_FIXTURE,
    CATALOG_CLASS_RUNTIME,
    STRATEGY_CATALOG,
    STRATEGY_CATALOG_CLASSIFICATION,
    STRATEGY_CATALOG_CLASSIFICATION_NOTES,
    VALID_CATALOG_CLASSIFICATIONS,
    get_strategy_classification,
)
from tools.new_strategy_plugin import build_scaffold, class_name_from_id, module_name_from_id
from tools.strategy_plugin_check import check_strategy


PROMOTED_RUNTIME_STRATEGIES = [
    "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter",
    "donchian_range_fade_4h_range_width_cv_013",
    "donchian_range_fade_4h_range_width_cv_013_short",
]


def test_strategy_plugin_check_loads_fixture_long_without_errors():
    result = check_strategy("fixture_long", repo_root=Path.cwd())

    assert result.ok
    assert result.plugin_class == "FixtureLongStrategy"
    assert result.plugin_version == "1.0.0"
    assert result.classification == CATALOG_CLASS_FIXTURE


def test_strategy_plugin_check_loads_fixture_exit_without_errors():
    result = check_strategy("fixture_exit", repo_root=Path.cwd())

    assert result.ok
    assert result.plugin_class == "FixtureExitStrategy"
    assert result.plugin_version == "1.0.0"
    assert result.classification == CATALOG_CLASS_FIXTURE


def test_strategy_plugin_check_reports_missing_catalog_entry():
    result = check_strategy("missing_plugin", repo_root=Path.cwd())

    assert not result.ok
    assert result.errors == ["missing catalog entry: missing_plugin"]


def test_plugin_catalog_classification_is_complete():
    assert set(STRATEGY_CATALOG_CLASSIFICATION) == set(STRATEGY_CATALOG)
    assert set(STRATEGY_CATALOG_CLASSIFICATION_NOTES) <= set(STRATEGY_CATALOG)
    assert set(STRATEGY_CATALOG_CLASSIFICATION.values()) <= VALID_CATALOG_CLASSIFICATIONS
    assert get_strategy_classification("fixture_exit") == CATALOG_CLASS_FIXTURE


def test_runtime_enabled_plugins_are_classified_as_runtime():
    assert Config.ENABLED_STRATEGIES == PROMOTED_RUNTIME_STRATEGIES
    for strategy_id in PROMOTED_RUNTIME_STRATEGIES:
        assert get_strategy_classification(strategy_id) == CATALOG_CLASS_RUNTIME


def test_new_strategy_plugin_scaffold_is_dry_run_friendly():
    scaffold = build_scaffold(
        "sample_breakout_4h",
        symbols=("BTC/USDT", "ETH/USDT"),
        timeframe="4h",
        side="LONG",
    )

    assert module_name_from_id("sample_breakout_4h") == "sample_breakout_4h"
    assert class_name_from_id("sample_breakout_4h") == "SampleBreakout4hStrategy"
    assert Path("trader/strategies/plugins/sample_breakout_4h.py") in scaffold.files
    assert Path("trader/tests/test_sample_breakout_4h_strategy.py") in scaffold.files
    assert Path("plans/cartridge_spec_sample_breakout_4h.md") in scaffold.files
    assert '"enabled": False' in scaffold.catalog_snippet
    assert "class SampleBreakout4hStrategy" in scaffold.files[
        Path("trader/strategies/plugins/sample_breakout_4h.py")
    ]
