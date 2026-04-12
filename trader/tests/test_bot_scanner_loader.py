import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from trader.config import Config


def _write_scanner_json(path: Path, **overrides):
    payload = {
        'scan_time': datetime.now(timezone.utc).isoformat(),
        'hot_symbols': [],
        'bot_symbols': [],
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding='utf-8')


def test_load_scanner_results_prefers_bot_symbols_and_filters_testnet_markets(mock_bot, tmp_path):
    scanner_path = tmp_path / 'hot_symbols.json'
    _write_scanner_json(
        scanner_path,
        bot_symbols=[
            {'symbol': 'BNB/USDT', 'source': 'l1_history', 'rank': 1, 'volume_24h': 300.0},
            {'symbol': 'ETH/USDT', 'source': 'l1_history', 'rank': 2, 'volume_24h': 200.0},
        ],
        hot_symbols=[
            {'symbol': 'BTC/USDT', 'rank': 1, 'volume_24h': 500.0},
        ],
    )
    mock_bot.exchange.markets = {
        'ETH/USDT:USDT': {'symbol': 'ETH/USDT:USDT'},
        'BTC/USDT:USDT': {'symbol': 'BTC/USDT:USDT'},
    }

    with patch.object(Config, 'SCANNER_JSON_PATH', str(scanner_path)), \
         patch.object(Config, 'SCANNER_MAX_AGE_MINUTES', 60):
        symbols = mock_bot.load_scanner_results()

    assert symbols == ['ETH/USDT']
    assert mock_bot._scanner_symbol_meta['ETH/USDT'] == {
        'scanner_source': 'l1_history',
        'scanner_rank': 2,
        'scanner_volume_24h': 200.0,
    }


def test_load_scanner_results_falls_back_to_hot_symbols_when_bot_symbols_unsupported(mock_bot, tmp_path):
    scanner_path = tmp_path / 'hot_symbols.json'
    _write_scanner_json(
        scanner_path,
        bot_symbols=[
            {'symbol': 'BNB/USDT', 'source': 'l1_history', 'rank': 1, 'volume_24h': 300.0},
        ],
        hot_symbols=[
            {'symbol': 'BTC/USDT', 'rank': 1, 'volume_24h': 500.0},
        ],
    )
    mock_bot.exchange.markets = {
        'BTC/USDT:USDT': {'symbol': 'BTC/USDT:USDT'},
    }

    with patch.object(Config, 'SCANNER_JSON_PATH', str(scanner_path)), \
         patch.object(Config, 'SCANNER_MAX_AGE_MINUTES', 60):
        symbols = mock_bot.load_scanner_results()

    assert symbols == ['BTC/USDT']
    assert mock_bot._scanner_symbol_meta['BTC/USDT']['scanner_source'] == 'hot_2b'


def test_load_scanner_results_uses_hot_symbols_for_old_json(mock_bot, tmp_path):
    scanner_path = tmp_path / 'hot_symbols.json'
    _write_scanner_json(
        scanner_path,
        hot_symbols=[
            {'symbol': 'BTC/USDT', 'rank': 1, 'volume_24h': 500.0},
        ],
    )
    mock_bot.exchange.markets = {}

    with patch.object(Config, 'SCANNER_JSON_PATH', str(scanner_path)), \
         patch.object(Config, 'SCANNER_MAX_AGE_MINUTES', 60):
        symbols = mock_bot.load_scanner_results()

    assert symbols == ['BTC/USDT']
    assert mock_bot._scanner_symbol_meta['BTC/USDT']['scanner_source'] == 'hot_2b'


def test_load_scanner_results_stale_json_uses_default_symbols_and_clears_meta(mock_bot, tmp_path):
    scanner_path = tmp_path / 'hot_symbols.json'
    _write_scanner_json(
        scanner_path,
        scan_time='2000-01-01T00:00:00+00:00',
        bot_symbols=[
            {'symbol': 'ETH/USDT', 'source': 'l1_history', 'rank': 1, 'volume_24h': 200.0},
        ],
    )
    mock_bot._scanner_symbol_meta = {'ETH/USDT': {'scanner_source': 'l1_history'}}

    with patch.object(Config, 'SCANNER_JSON_PATH', str(scanner_path)), \
         patch.object(Config, 'SCANNER_MAX_AGE_MINUTES', 60), \
         patch.object(Config, 'SYMBOLS', ['BTC/USDT']):
        symbols = mock_bot.load_scanner_results()

    assert symbols == ['BTC/USDT']
    assert mock_bot._scanner_symbol_meta == {}
