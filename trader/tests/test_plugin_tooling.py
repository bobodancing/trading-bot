from pathlib import Path

from tools.new_strategy_plugin import build_scaffold, class_name_from_id, module_name_from_id
from tools.strategy_plugin_check import check_strategy


def test_strategy_plugin_check_loads_fixture_long_without_errors():
    result = check_strategy("fixture_long", repo_root=Path.cwd())

    assert result.ok
    assert result.plugin_class == "FixtureLongStrategy"
    assert result.plugin_version == "1.0.0"


def test_strategy_plugin_check_reports_missing_catalog_entry():
    result = check_strategy("missing_plugin", repo_root=Path.cwd())

    assert not result.ok
    assert result.errors == ["missing catalog entry: missing_plugin"]


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
