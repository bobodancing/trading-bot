"""
Test: _handle_close rollback 行為

場景：close_position 丟出 Exception 時，
  - 回傳 False（不從 active_trades 移除）
  - _save_positions 被呼叫（positions.json 確保可重試）
  - 持倉狀態 (is_closed) 維持 False
  - stop_order_id 已移至 pending_stop_cancels（平倉優先邏輯）

正常路徑：close 成功 → 回傳 True
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from trader.tests.conftest import make_pm


# ──────────────────────────────────────────────
# Rollback Tests
# ──────────────────────────────────────────────

class TestHandleCloseRollback:

    def test_failure_returns_false(self, mock_bot):
        """close_position 丟 Exception → _handle_close 回傳 False"""
        pm = make_pm()
        mock_bot.execution_engine.close_position = MagicMock(
            side_effect=Exception("Network timeout")
        )
        mock_bot._save_positions = MagicMock()

        result = mock_bot._handle_close(pm, current_price=50000.0)

        assert result is False

    def test_failure_calls_save_positions(self, mock_bot):
        """rollback：_save_positions 必須被呼叫（確保 positions.json 保留持倉）"""
        pm = make_pm()
        mock_bot.execution_engine.close_position = MagicMock(
            side_effect=Exception("API error")
        )
        mock_bot._save_positions = MagicMock()

        mock_bot._handle_close(pm, current_price=50000.0)

        mock_bot._save_positions.assert_called_once()

    def test_failure_position_remains_active(self, mock_bot):
        """rollback：active_trades 仍保留該 symbol（不被移除）"""
        pm = make_pm()
        mock_bot.active_trades['BTC/USDT'] = pm
        mock_bot.execution_engine.close_position = MagicMock(
            side_effect=Exception("Exchange down")
        )
        mock_bot._save_positions = MagicMock()

        mock_bot._handle_close(pm, current_price=50000.0)

        assert 'BTC/USDT' in mock_bot.active_trades

    def test_close_failure_keeps_live_stop_order(self, mock_bot):
        """
        stop_order_id 在 close 下單前就移入 pending_stop_cancels（平倉優先）。
        即使 close 失敗，stop 已在 pending list、stop_order_id 已清空。
        注意：這是已知邊界情境——下個 cycle 的 pending_stop_cancels 處理
        可能誤取消止損。測試把此行為顯式化。
        """
        pm = make_pm()
        pm.stop_order_id = 'stop_order_123'
        mock_bot.execution_engine.close_position = MagicMock(
            side_effect=Exception("Timeout")
        )
        mock_bot._save_positions = MagicMock()

        mock_bot._handle_close(pm, current_price=50000.0)

        assert pm.pending_stop_cancels == []
        assert pm.stop_order_id == 'stop_order_123'

    # ──────────────────────────────────────────────
    # 正常路徑（Sanity Check）
    # ──────────────────────────────────────────────

    def test_success_returns_true(self, mock_bot):
        """正常路徑：close_position 成功 → 回傳 True"""
        pm = make_pm()
        mock_bot.execution_engine.close_position = MagicMock(
            return_value={'orderId': 'order_456', 'status': 'FILLED'}
        )
        mock_bot._save_positions = MagicMock()

        result = mock_bot._handle_close(pm, current_price=51000.0)

        assert result is True

    def test_success_records_actual_fill_price(self, mock_bot):
        """full close 應以實際 fill price 落 DB。"""
        pm = make_pm(
            entry_price=50000.0,
            stop_loss=49000.0,
            position_size=0.01,
        )
        pm.original_size = pm.total_size
        pm.realized_partial_pnl = 0.0

        mock_bot.execution_engine.close_position = MagicMock(
            return_value={'orderId': 'order_789', 'avgPrice': '50500.0', 'status': 'FILLED'}
        )

        result = mock_bot._handle_close(pm, current_price=50400.0)

        assert result is True
        payload = mock_bot.perf_db.record_trade.call_args[0][0]
        assert payload['exit_price'] == pytest.approx(50500.0)
        assert payload['exit_price_source'] == 'exchange_fill'
        assert payload['pnl_usdt'] == pytest.approx(5.0)
        assert payload['realized_r'] == pytest.approx(0.25)

    def test_external_close_uses_assumed_sl_exit_price_source(self, mock_bot):
        """exchange 已平倉時，收尾要用 assumed SL 價格且不可再送 close order。"""
        pm = make_pm(
            entry_price=50000.0,
            stop_loss=49000.0,
            position_size=0.01,
        )
        pm.current_sl = 49250.0
        pm.original_size = pm.total_size
        pm.realized_partial_pnl = 0.0
        pm.exit_reason = 'hard_stop_hit'
        mock_bot.execution_engine.close_position = MagicMock()

        result = mock_bot._handle_close(
            pm,
            current_price=pm.current_sl,
            external_close=True,
            exit_price_source='assumed_sl',
        )

        assert result is True
        mock_bot.execution_engine.close_position.assert_not_called()
        payload = mock_bot.perf_db.record_trade.call_args[0][0]
        assert payload['exit_price'] == pytest.approx(49250.0)
        assert payload['exit_price_source'] == 'assumed_sl'

    def test_success_records_v54_protection_telemetry(self, mock_bot):
        """V54 鎖利保護後被打掉時，資料庫要保留 milestone 與 signal_type。"""
        pm = make_pm(
            entry_price=50000.0,
            stop_loss=49000.0,
            position_size=0.01,
            strategy_name='v54_noscale',
            signal_type='2B',
        )
        pm.exit_reason = 'sl_hit'
        pm.highest_price = 52000.0
        pm.lowest_price = 49950.0
        pm.strategy.is_breakeven_protected = True
        pm.strategy.is_15r_locked = True
        pm.strategy.is_trailing_active = True

        mock_bot.execution_engine.close_position = MagicMock(
            return_value={'orderId': 'order_999', 'avgPrice': '50050.0', 'status': 'FILLED'}
        )

        result = mock_bot._handle_close(pm, current_price=49990.0)

        assert result is True
        payload = mock_bot.perf_db.record_trade.call_args[0][0]
        assert payload['signal_type'] == '2B'
        assert payload['exit_price_source'] == 'exchange_fill'
        assert payload['protection_state'] == 'V54_LOCK_15R'
        assert payload['protected_exit'] == 1
        assert payload['max_r_reached'] == pytest.approx(2.0)
