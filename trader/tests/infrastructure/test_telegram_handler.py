"""Tests for TelegramCommandHandler."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from trader.infrastructure.telegram_handler import TelegramCommandHandler


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.active_trades = {}
    bot._start_time = datetime.now(timezone.utc) - timedelta(hours=2)
    bot.initial_balance = 10000.0
    bot.risk_manager.get_balance.return_value = 10500.0
    return bot


@pytest.fixture
def handler(mock_bot):
    with patch('trader.infrastructure.telegram_handler.Config') as mock_cfg:
        mock_cfg.TELEGRAM_ENABLED = True
        mock_cfg.TELEGRAM_BOT_TOKEN = 'fake-token'
        mock_cfg.TELEGRAM_CHAT_ID = '12345'
        mock_cfg.DRY_RUN = False
        mock_cfg.SYMBOLS = ['BTC/USDT', 'ETH/USDT']
        h = TelegramCommandHandler(mock_bot)
        yield h


class TestTelegramCommands:

    def test_cmd_positions_empty(self, handler):
        result = handler._cmd_positions()
        assert 'No open positions' in result

    def test_cmd_positions_with_trades(self, handler):
        pm = MagicMock()
        pm.side = 'LONG'
        pm.strategy_name = 'fixture_long'
        pm.avg_entry = 100.0
        pm.current_sl = 95.0
        pm.total_size = 0.5
        pm.stage = 2
        pm.signal_tier = 'A'
        pm.entry_time = datetime.now(timezone.utc) - timedelta(hours=3)
        pm.highest_price = 105.0
        pm.lowest_price = 98.0
        handler.bot.active_trades = {'BTC/USDT': pm}

        result = handler._cmd_positions()
        assert 'Open Positions (1)' in result
        assert 'BTC/USDT' in result
        assert 'LONG' in result
        assert 'fixture_long' in result
        assert 'Stage: 2' in result

    def test_cmd_positions_shows_manual_label(self, handler):
        pm = MagicMock()
        pm.side = 'SHORT'
        pm.strategy_name = 'legacy_manual'
        pm.avg_entry = 100.0
        pm.current_sl = 105.0
        pm.total_size = 0.25
        pm.stage = 1
        pm.signal_tier = 'A'
        pm.entry_time = datetime.now(timezone.utc) - timedelta(hours=1)
        pm.highest_price = 101.0
        pm.lowest_price = 96.0
        handler.bot.active_trades = {'ETH/USDT': pm}

        result = handler._cmd_positions()
        assert 'ETH/USDT' in result
        assert 'Manual/Protective' in result

    def test_cmd_status(self, handler):
        with patch('trader.infrastructure.telegram_handler.Config') as mock_cfg:
            mock_cfg.DRY_RUN = False
            mock_cfg.SYMBOLS = ['BTC/USDT', 'ETH/USDT']
            result = handler._cmd_status()

        assert 'Bot Status' in result
        assert 'Active positions: 0' in result
        assert 'Strategy mix: None' in result
        assert 'DRY RUN: No' in result

    def test_cmd_status_counts_strategy_labels(self, handler):
        pm_manual = MagicMock()
        pm_manual.strategy_name = 'legacy_manual'
        pm_fixture = MagicMock()
        pm_fixture.strategy_name = 'fixture_long'
        handler.bot.active_trades = {
            'BTC/USDT': pm_manual,
            'ETH/USDT': pm_fixture,
        }

        with patch('trader.infrastructure.telegram_handler.Config') as mock_cfg:
            mock_cfg.DRY_RUN = False
            mock_cfg.SYMBOLS = ['BTC/USDT', 'ETH/USDT']
            result = handler._cmd_status()

        assert 'Active positions: 2' in result
        assert 'Manual/Protective: 1' in result
        assert 'fixture_long: 1' in result

    def test_cmd_balance(self, handler):
        with patch('trader.infrastructure.telegram_handler.Config') as mock_cfg:
            mock_cfg.DRY_RUN = False
            result = handler._cmd_balance()

        assert '$10500.00' in result
        assert '+$500.00' in result

    def test_cmd_help(self, handler):
        result = handler._cmd_help()
        assert '/positions' in result
        assert '/status' in result
        assert '/balance' in result


class TestTelegramSecurity:

    @patch('trader.infrastructure.telegram_handler.requests.get')
    @patch('trader.infrastructure.telegram_handler.requests.post')
    def test_ignores_wrong_chat_id(self, mock_post, mock_get, handler):
        mock_get.return_value = MagicMock(
            ok=True,
            json=lambda: {'result': [{
                'update_id': 1,
                'message': {
                    'chat': {'id': 99999},
                    'text': '/positions',
                }
            }]}
        )
        with patch('trader.infrastructure.telegram_handler.Config') as mock_cfg:
            mock_cfg.TELEGRAM_ENABLED = True
            mock_cfg.TELEGRAM_BOT_TOKEN = 'fake-token'
            mock_cfg.TELEGRAM_CHAT_ID = '12345'
            handler.poll()

        mock_post.assert_not_called()

    @patch('trader.infrastructure.telegram_handler.requests.get')
    @patch('trader.infrastructure.telegram_handler.requests.post')
    def test_responds_correct_chat_id(self, mock_post, mock_get, handler):
        mock_get.return_value = MagicMock(
            ok=True,
            json=lambda: {'result': [{
                'update_id': 1,
                'message': {
                    'chat': {'id': 12345},
                    'text': '/help',
                }
            }]}
        )
        mock_post.return_value = MagicMock(ok=True)
        with patch('trader.infrastructure.telegram_handler.Config') as mock_cfg:
            mock_cfg.TELEGRAM_ENABLED = True
            mock_cfg.TELEGRAM_BOT_TOKEN = 'fake-token'
            mock_cfg.TELEGRAM_CHAT_ID = '12345'
            handler.poll()

        mock_post.assert_called_once()

    @patch('trader.infrastructure.telegram_handler.requests.get')
    def test_ignores_non_command(self, mock_get, handler):
        mock_get.return_value = MagicMock(
            ok=True,
            json=lambda: {'result': [{
                'update_id': 1,
                'message': {
                    'chat': {'id': 12345},
                    'text': 'hello',
                }
            }]}
        )
        with patch('trader.infrastructure.telegram_handler.Config') as mock_cfg:
            mock_cfg.TELEGRAM_ENABLED = True
            mock_cfg.TELEGRAM_BOT_TOKEN = 'fake-token'
            mock_cfg.TELEGRAM_CHAT_ID = '12345'
            handler.poll()


class TestTelegramPolling:

    @patch('trader.infrastructure.telegram_handler.requests.get')
    def test_updates_last_update_id(self, mock_get, handler):
        mock_get.return_value = MagicMock(
            ok=True,
            json=lambda: {'result': [{
                'update_id': 42,
                'message': {
                    'chat': {'id': 12345},
                    'text': 'hello',
                }
            }]}
        )
        with patch('trader.infrastructure.telegram_handler.Config') as mock_cfg:
            mock_cfg.TELEGRAM_ENABLED = True
            mock_cfg.TELEGRAM_BOT_TOKEN = 'fake-token'
            mock_cfg.TELEGRAM_CHAT_ID = '12345'
            handler.poll()

        assert handler.last_update_id == 42

    def test_poll_disabled(self, handler):
        with patch('trader.infrastructure.telegram_handler.Config') as mock_cfg:
            mock_cfg.TELEGRAM_ENABLED = False
            with patch('trader.infrastructure.telegram_handler.requests.get') as mock_get:
                handler.poll()
                mock_get.assert_not_called()
