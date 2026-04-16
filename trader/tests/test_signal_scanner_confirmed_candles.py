import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from trader.config import Config
from trader.indicators.technical import MarketFilter, MTFConfirmation, TechnicalAnalysis
from trader.risk.manager import SignalTierSystem


def _make_frame(rows: int, freq: str) -> pd.DataFrame:
    idx = pd.date_range('2026-01-01', periods=rows, freq=freq, tz='UTC')
    close = np.linspace(100.0, 200.0, rows)
    return pd.DataFrame({
        'timestamp': idx,
        'open': close,
        'high': close + 1.0,
        'low': close - 1.0,
        'close': close,
        'volume': np.full(rows, 1000.0),
        'adx': np.full(rows, 30.0),
    }, index=idx)


def test_scanner_drops_only_signal_candle_in_patch_a_runtime(mock_bot):
    trend_df = _make_frame(250, '4h')
    signal_df = _make_frame(100, '1h')
    mtf_df = _make_frame(100, '4h')
    captured = {}

    def capture_market(df, symbol):
        captured['market_df'] = df.copy()
        return True, 'ok', True

    def capture_trend(df, side):
        captured['trend_df'] = df.copy()
        return True, 'trend_ok'

    def capture_mtf(df, side):
        captured['mtf_df'] = df.copy()
        return True, 'mtf_ok'

    mock_bot.fetch_ohlcv = MagicMock(side_effect=[trend_df, signal_df, mtf_df])
    mock_bot._check_total_risk = MagicMock(return_value=True)
    mock_bot._execute_trade = MagicMock()

    with patch.object(Config, 'USE_SCANNER_SYMBOLS', False), \
         patch.object(Config, 'SYMBOLS', ['ETH/USDT']), \
         patch.object(Config, 'BTC_TREND_FILTER_ENABLED', False), \
         patch.object(Config, 'REGIME_ARBITER_ENABLED', False), \
         patch.object(Config, 'ENABLE_MTF_CONFIRMATION', True), \
         patch.object(Config, 'ENABLE_EMA_PULLBACK', True), \
         patch.object(Config, 'ENABLE_VOLUME_BREAKOUT', False), \
         patch.object(TechnicalAnalysis, 'calculate_indicators', side_effect=lambda df: df), \
         patch.object(MarketFilter, 'check_market_condition', side_effect=capture_market), \
         patch.object(TechnicalAnalysis, 'check_trend', side_effect=capture_trend), \
         patch.object(MTFConfirmation, 'check_mtf_alignment', side_effect=capture_mtf), \
         patch('trader.signal_scanner.detect_2b_with_pivots', return_value=(False, None)), \
         patch(
             'trader.signal_scanner.detect_ema_pullback',
             return_value=(True, {'side': 'LONG', 'signal_strength': 'strong', 'vol_ratio': 1.5}),
         ), \
         patch('trader.signal_scanner.detect_volume_breakout', return_value=(False, None)):
        mock_bot.scan_for_signals()

    assert captured['market_df'].index[-1] == trend_df.index[-1]
    assert captured['trend_df'].index[-1] == trend_df.index[-1]
    assert captured['mtf_df'].index[-1] == mtf_df.index[-1]

    execute_args = mock_bot._execute_trade.call_args[0]
    assert execute_args[4].index[-1] == signal_df.index[-2]


class _Collector:
    def __init__(self):
        self.rejects = []
        self.entries = []
        self.lane_race_events = []

    def record_reject(self, **kwargs):
        self.rejects.append(kwargs)

    def record_entry(self, **kwargs):
        self.entries.append(kwargs)

    def record_lane_race(self, **kwargs):
        self.lane_race_events.append(kwargs)


def test_scanner_audits_structured_tier_mtf_reject_fields(mock_bot):
    trend_df = _make_frame(250, '4h')
    signal_df = _make_frame(100, '1h')
    mtf_df = _make_frame(100, '4h')
    collector = _Collector()

    mock_bot._signal_audit = collector
    mock_bot._scanner_symbol_meta = {
        'ETH/USDT': {
            'scanner_source': 'l1_history',
            'scanner_rank': 2,
            'scanner_volume_24h': 200_000_000.0,
        }
    }
    mock_bot.fetch_ohlcv = MagicMock(side_effect=[trend_df, signal_df, mtf_df])
    mock_bot._check_total_risk = MagicMock(return_value=True)

    with patch.object(Config, 'USE_SCANNER_SYMBOLS', False), \
         patch.object(Config, 'SYMBOLS', ['ETH/USDT']), \
         patch.object(Config, 'BTC_TREND_FILTER_ENABLED', False), \
         patch.object(Config, 'REGIME_ARBITER_ENABLED', False), \
         patch.object(Config, 'ENABLE_MTF_CONFIRMATION', True), \
         patch.object(Config, 'ENABLE_EMA_PULLBACK', True), \
         patch.object(Config, 'ENABLE_VOLUME_BREAKOUT', False), \
         patch.object(Config, 'V7_MIN_SIGNAL_TIER', 'A'), \
         patch.object(TechnicalAnalysis, 'calculate_indicators', side_effect=lambda df: df), \
         patch.object(MarketFilter, 'check_market_condition', return_value=(True, 'market_ok', True)), \
         patch.object(TechnicalAnalysis, 'check_trend', return_value=(True, 'trend_ok')), \
         patch.object(MTFConfirmation, 'check_mtf_alignment', return_value=(False, 'mtf_fail')), \
         patch.object(
             MTFConfirmation,
             'get_alignment_snapshot',
             return_value={
                 'mtf_status': 'misaligned',
                 'mtf_close': 123.0,
                 'mtf_ema_fast': 118.0,
                 'mtf_ema_slow': 120.0,
                 'mtf_price_vs_fast_pct': 2.5,
                 'mtf_fast_vs_slow_pct': 1.7,
             },
         ), \
         patch('trader.signal_scanner.detect_2b_with_pivots', return_value=(False, None)), \
         patch(
             'trader.signal_scanner.detect_ema_pullback',
             return_value=(True, {'side': 'LONG', 'signal_strength': 'moderate', 'vol_ratio': 1.2}),
         ), \
         patch('trader.signal_scanner.detect_volume_breakout', return_value=(False, None)):
        mock_bot.scan_for_signals()

    assert len(collector.rejects) == 1
    reject = collector.rejects[0]
    assert reject['reject_reason'] == 'tier_filter'
    assert reject['mtf_status'] == 'misaligned'
    assert reject['mtf_aligned'] is False
    assert reject['tier_score'] == 0
    assert reject['tier_min'] == 'A'
    assert reject['tier_min_effective'] == 'A'
    assert reject['mtf_gate_mode'] == 'hard_blocked'
    assert reject['tier_component_mtf'] == 0
    assert reject['signal_candle_time'] == signal_df.index[-2].isoformat()
    assert reject['trend_candle_time'] == trend_df.index[-1].isoformat()
    assert reject['mtf_candle_time'] == mtf_df.index[-1].isoformat()


def test_scanner_audits_structured_tier_mtf_entry_fields(mock_bot):
    trend_df = _make_frame(250, '4h')
    signal_df = _make_frame(100, '1h')
    mtf_df = _make_frame(100, '4h')
    collector = _Collector()

    mock_bot._signal_audit = collector
    mock_bot._scanner_symbol_meta = {
        'ETH/USDT': {
            'scanner_source': 'l1_history',
            'scanner_rank': 2,
            'scanner_volume_24h': 200_000_000.0,
        }
    }
    mock_bot.fetch_ohlcv = MagicMock(side_effect=[trend_df, signal_df, mtf_df])
    mock_bot._check_total_risk = MagicMock(return_value=True)
    mock_bot._execute_trade = MagicMock()

    with patch.object(Config, 'USE_SCANNER_SYMBOLS', False), \
         patch.object(Config, 'SYMBOLS', ['ETH/USDT']), \
         patch.object(Config, 'BTC_TREND_FILTER_ENABLED', False), \
         patch.object(Config, 'REGIME_ARBITER_ENABLED', False), \
         patch.object(Config, 'ENABLE_MTF_CONFIRMATION', True), \
         patch.object(Config, 'ENABLE_EMA_PULLBACK', True), \
         patch.object(Config, 'ENABLE_VOLUME_BREAKOUT', False), \
         patch.object(Config, 'V7_MIN_SIGNAL_TIER', 'C'), \
         patch.object(TechnicalAnalysis, 'calculate_indicators', side_effect=lambda df: df), \
         patch.object(MarketFilter, 'check_market_condition', return_value=(True, 'market_ok', True)), \
         patch.object(TechnicalAnalysis, 'check_trend', return_value=(True, 'trend_ok')), \
         patch.object(MTFConfirmation, 'check_mtf_alignment', return_value=(True, 'mtf_ok')), \
         patch.object(
             MTFConfirmation,
             'get_alignment_snapshot',
             return_value={
                 'mtf_status': 'aligned',
                 'mtf_close': 123.0,
                 'mtf_ema_fast': 120.0,
                 'mtf_ema_slow': 118.0,
                 'mtf_price_vs_fast_pct': 2.5,
                 'mtf_fast_vs_slow_pct': 1.7,
             },
         ), \
         patch('trader.signal_scanner.detect_2b_with_pivots', return_value=(False, None)), \
         patch(
             'trader.signal_scanner.detect_ema_pullback',
             return_value=(True, {
                 'side': 'LONG',
                 'signal_strength': 'strong',
                 'vol_ratio': 1.5,
                 'candle_confirmed': True,
             }),
         ), \
         patch('trader.signal_scanner.detect_volume_breakout', return_value=(False, None)):
        mock_bot.scan_for_signals()

    assert len(collector.entries) == 1
    entry = collector.entries[0]
    assert entry['signal_tier'] == 'A'
    assert entry['tier_score'] == 7
    assert entry['mtf_status'] == 'aligned'
    assert entry['mtf_aligned'] is True
    assert entry['tier_component_mtf'] == 2
    assert entry['tier_component_market'] == 2
    assert entry['tier_component_volume'] == 2
    assert entry['tier_component_candle'] == 1
    assert entry['signal_candle_time'] == signal_df.index[-2].isoformat()
    assert entry['trend_candle_time'] == trend_df.index[-1].isoformat()
    assert entry['mtf_candle_time'] == mtf_df.index[-1].isoformat()
    assert entry['mtf_gate_mode'] == 'hard_aligned'
    assert entry['tier_min_effective'] == 'C'
    assert entry['scanner_source'] == 'l1_history'
    assert entry['scanner_rank'] == 2
    assert entry['scanner_volume_24h'] == 200_000_000.0


def test_scanner_ema_soft_mtf_gate_relaxes_floor_by_one_tier(mock_bot):
    trend_df = _make_frame(250, '4h')
    signal_df = _make_frame(100, '1h')
    mtf_df = _make_frame(100, '4h')
    collector = _Collector()

    mock_bot._signal_audit = collector
    mock_bot.fetch_ohlcv = MagicMock(side_effect=[trend_df, signal_df, mtf_df])
    mock_bot._check_total_risk = MagicMock(return_value=True)
    mock_bot._execute_trade = MagicMock()

    with patch.object(Config, 'USE_SCANNER_SYMBOLS', False), \
         patch.object(Config, 'SYMBOLS', ['ETH/USDT']), \
         patch.object(Config, 'BTC_TREND_FILTER_ENABLED', False), \
         patch.object(Config, 'REGIME_ARBITER_ENABLED', False), \
         patch.object(Config, 'ENABLE_MTF_CONFIRMATION', True), \
         patch.object(Config, 'ENABLE_EMA_PULLBACK', True), \
         patch.object(Config, 'ENABLE_VOLUME_BREAKOUT', False), \
         patch.object(Config, 'V7_MIN_SIGNAL_TIER', 'A'), \
         patch.object(Config, 'EMA_PULLBACK_SOFT_MTF_ENABLED', True), \
         patch.object(TechnicalAnalysis, 'calculate_indicators', side_effect=lambda df: df), \
         patch.object(MarketFilter, 'check_market_condition', return_value=(True, 'market_ok', True)), \
         patch.object(TechnicalAnalysis, 'check_trend', return_value=(True, 'trend_ok')), \
         patch.object(MTFConfirmation, 'check_mtf_alignment', return_value=(False, 'mtf_fail')), \
         patch.object(
             MTFConfirmation,
             'get_alignment_snapshot',
             return_value={
                 'mtf_status': 'misaligned',
                 'mtf_close': 119.0,
                 'mtf_ema_fast': 120.0,
                 'mtf_ema_slow': 118.0,
                 'mtf_price_vs_fast_pct': -0.833333,
                 'mtf_fast_vs_slow_pct': 1.694915,
             },
         ), \
         patch('trader.signal_scanner.detect_2b_with_pivots', return_value=(False, None)), \
         patch(
             'trader.signal_scanner.detect_ema_pullback',
             return_value=(True, {
                 'side': 'LONG',
                 'signal_type': 'EMA_PULLBACK',
                 'signal_strength': 'moderate',
                 'vol_ratio': 1.2,
                 'candle_confirmed': True,
             }),
         ), \
         patch('trader.signal_scanner.detect_volume_breakout', return_value=(False, None)):
        mock_bot.scan_for_signals()

    mock_bot._execute_trade.assert_called_once()
    assert len(collector.entries) == 1
    entry = collector.entries[0]
    assert entry['signal_tier'] == 'B'
    assert entry['tier_score'] == 4
    assert entry['tier_min'] == 'A'
    assert entry['tier_min_effective'] == 'B'
    assert entry['mtf_gate_mode'] == 'ema_soft_structure'


def _run_allowlist_scan(mock_bot, monkeypatch, allowed_signal_types, *, dry_count_only=False):
    trend_df = _make_frame(250, '4h')
    signal_df = _make_frame(100, '1h')
    collector = _Collector()

    mock_bot._signal_audit = collector
    mock_bot.fetch_ohlcv = MagicMock(side_effect=[trend_df, signal_df])
    mock_bot._check_total_risk = MagicMock(return_value=True)
    mock_bot._execute_trade = MagicMock()
    monkeypatch.setattr(Config, 'BACKTEST_ALLOWED_SIGNAL_TYPES', allowed_signal_types, raising=False)
    monkeypatch.setattr(Config, 'BACKTEST_DRY_COUNT_ONLY', dry_count_only, raising=False)

    common_details = {
        'side': 'LONG',
        'signal_strength': 'strong',
        'vol_ratio': 2.0,
        'entry_price': 100.0,
        'atr': 1.0,
        'stop_loss': 98.0,
    }
    with patch.object(Config, 'USE_SCANNER_SYMBOLS', False), \
         patch.object(Config, 'SYMBOLS', ['ETH/USDT']), \
         patch.object(Config, 'BTC_TREND_FILTER_ENABLED', False), \
         patch.object(Config, 'REGIME_ARBITER_ENABLED', False), \
         patch.object(Config, 'ENABLE_MTF_CONFIRMATION', False), \
         patch.object(Config, 'ENABLE_EMA_PULLBACK', True), \
         patch.object(Config, 'ENABLE_VOLUME_BREAKOUT', True), \
         patch.object(Config, 'V7_MIN_SIGNAL_TIER', 'C'), \
         patch.object(TechnicalAnalysis, 'calculate_indicators', side_effect=lambda df: df), \
         patch.object(MarketFilter, 'check_market_condition', return_value=(True, 'market_ok', True)), \
         patch.object(TechnicalAnalysis, 'check_trend', return_value=(True, 'trend_ok')), \
         patch('trader.signal_scanner.detect_2b_with_pivots', return_value=(True, {
             **common_details,
             'neckline': 99.0,
         })), \
         patch('trader.signal_scanner.detect_ema_pullback', return_value=(True, dict(common_details))), \
         patch('trader.signal_scanner.detect_volume_breakout', return_value=(True, dict(common_details))):
        mock_bot.scan_for_signals()

    return collector, mock_bot._execute_trade


def test_backtest_allowlist_ema_only_excludes_2b_and_vb(mock_bot, monkeypatch):
    collector, execute_trade = _run_allowlist_scan(
        mock_bot,
        monkeypatch,
        ['EMA_PULLBACK'],
    )

    execute_trade.assert_called_once()
    assert execute_trade.call_args[0][2] == 'EMA_PULLBACK'
    assert [entry['signal_type'] for entry in collector.entries] == ['EMA_PULLBACK']
    suppressed = {
        event['candidate_signal_type']: event['suppressed_by']
        for event in collector.lane_race_events
        if event.get('suppressed_by') == 'allowed_signal_types'
    }
    assert suppressed == {'2B': 'allowed_signal_types', 'VOLUME_BREAKOUT': 'allowed_signal_types'}


def test_backtest_allowlist_vb_only_excludes_2b_and_ema(mock_bot, monkeypatch):
    collector, execute_trade = _run_allowlist_scan(
        mock_bot,
        monkeypatch,
        ['VOLUME_BREAKOUT'],
    )

    execute_trade.assert_called_once()
    assert execute_trade.call_args[0][2] == 'VOLUME_BREAKOUT'
    assert [entry['signal_type'] for entry in collector.entries] == ['VOLUME_BREAKOUT']
    suppressed = {
        event['candidate_signal_type']: event['suppressed_by']
        for event in collector.lane_race_events
        if event.get('suppressed_by') == 'allowed_signal_types'
    }
    assert suppressed == {'2B': 'allowed_signal_types', 'EMA_PULLBACK': 'allowed_signal_types'}


def test_backtest_allowlist_all_preserves_production_priority(mock_bot, monkeypatch):
    collector, execute_trade = _run_allowlist_scan(
        mock_bot,
        monkeypatch,
        ['2B', 'EMA_PULLBACK', 'VOLUME_BREAKOUT'],
    )

    execute_trade.assert_called_once()
    assert execute_trade.call_args[0][2] == '2B'
    selected = [event for event in collector.lane_race_events if event['candidate_signal_type'] == '2B']
    assert selected[0]['selected_signal_type'] == '2B'
    assert selected[0]['won_race_vs'] == 'VOLUME_BREAKOUT,EMA_PULLBACK'


def test_backtest_dry_count_records_entry_without_execution(mock_bot, monkeypatch):
    collector, execute_trade = _run_allowlist_scan(
        mock_bot,
        monkeypatch,
        ['EMA_PULLBACK'],
        dry_count_only=True,
    )

    execute_trade.assert_not_called()
    assert [entry['signal_type'] for entry in collector.entries] == ['EMA_PULLBACK']
