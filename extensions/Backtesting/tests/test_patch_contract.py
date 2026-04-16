"""
Interface Contract — 驗證 backtest_bot.py 依賴的所有 patch 點仍然存在。
如果 trading_bot 重構導致 attribute 改名/移動，這裡會立即 FAIL。
"""
import sys
from pathlib import Path

TRADING_BOT_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "projects" / "trading_bot"
sys.path.insert(0, str(TRADING_BOT_ROOT))

import pytest
from bot_compat import get_bot_class, get_config_class, get_datetime_patch_module_names


class TestPatchTargetsExist:
    """驗證 monkey-patch 目標屬性仍然存在於 trading_bot"""

    def test_bot_has_init_exchange(self):
        bot_cls = get_bot_class()
        assert hasattr(bot_cls, "_init_exchange")

    def test_bot_has_restore_positions(self):
        bot_cls = get_bot_class()
        assert hasattr(bot_cls, "_restore_positions")

    def test_bot_has_sync_exchange_positions(self):
        bot_cls = get_bot_class()
        assert hasattr(bot_cls, "_sync_exchange_positions")

    def test_bot_has_scan_for_signals(self):
        bot_cls = get_bot_class()
        assert hasattr(bot_cls, "scan_for_signals")

    def test_bot_has_monitor_positions(self):
        bot_cls = get_bot_class()
        assert hasattr(bot_cls, "monitor_positions")

    def test_bot_has_handle_close(self):
        bot_cls = get_bot_class()
        assert hasattr(bot_cls, "_handle_close")

    def test_precision_handler_has_load_exchange_info(self):
        from trader.risk.manager import PrecisionHandler
        assert hasattr(PrecisionHandler, "_load_exchange_info")

    def test_config_has_required_attrs(self):
        config_cls = get_config_class()
        required = [
            "POSITIONS_JSON_PATH", "DB_PATH", "SYMBOLS",
            "USE_SCANNER_SYMBOLS", "V6_DRY_RUN", "SIGNAL_STRATEGY_MAP",
        ]
        for attr in required:
            assert hasattr(config_cls, attr), f"Config missing: {attr}"


class TestInjectionTargetsExist:
    """驗證 inject 目標屬性在 bot instance 上存在"""

    def test_bot_instance_attributes(self):
        """驗證 create_backtest_bot 依賴的 instance attributes"""
        import inspect
        bot_cls = get_bot_class()

        # 檢查 __init__ source 中有設定這些 attributes
        source = inspect.getsource(bot_cls.__init__)
        expected_attrs = [
            "data_provider", "execution_engine", "exchange",
            "perf_db", "persistence", "risk_manager",
        ]
        for attr in expected_attrs:
            assert f"self.{attr}" in source, f"{bot_cls.__name__}.__init__ missing: self.{attr}"


class TestDatetimePatchTargetsExist:
    """驗證所有使用 datetime.now() 的 module 都有被 patch"""

    def test_all_datetime_now_modules_are_patched(self):
        """
        掃描 trader/ 下所有 .py 的 datetime.now() 使用，
        確認都在已知 patch 清單或已知 mock 清單中。
        """
        import ast

        patched_modules = get_datetime_patch_module_names()
        mocked_modules = {
            "trader.persistence",  # bot.persistence = MagicMock()
            "trader.infrastructure.telegram_handler",  # polling loop 不啟動
        }

        known = patched_modules | mocked_modules

        # 掃描所有 .py（排除 tests/）
        trader_dir = TRADING_BOT_ROOT / "trader"
        unpatched = []

        for py_file in trader_dir.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except Exception:
                continue

            has_datetime_now = False
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # datetime.now(...) or datetime.datetime.now(...)
                    func = node.func
                    if isinstance(func, ast.Attribute) and func.attr == "now":
                        if isinstance(func.value, ast.Name) and func.value.id == "datetime":
                            has_datetime_now = True
                        elif isinstance(func.value, ast.Attribute):
                            if func.value.attr == "datetime":
                                has_datetime_now = True

            if has_datetime_now:
                # 推算 module name
                rel = py_file.relative_to(TRADING_BOT_ROOT)
                mod_name = str(rel).replace("\\", "/").replace("/", ".").removesuffix(".py")
                if mod_name not in known:
                    unpatched.append(mod_name)

        assert unpatched == [], (
            f"以下 module 使用 datetime.now() 但未在 patch/mock 清單中: {unpatched}\n"
            f"請更新 backtest_engine.py _backtest_context() 或確認該 module 已被 mock。"
        )
