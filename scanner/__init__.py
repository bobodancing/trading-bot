# -*- coding: utf-8 -*-
"""
Market Scanner 模組
==================
從 scanner 資料夾導入主要類別
"""

from .market_scanner import (
    MarketScanner,
    ScannerConfig,
    ScanResult,
    MarketSummary,
    StructureAnalysis,
    SignalSide,
    SignalType,
    VolumeGrade,
    StructureQuality,
    get_sector,
    SCANNER_AVAILABLE
)

__version__ = "1.0.0"
__all__ = [
    'MarketScanner',
    'ScannerConfig', 
    'ScanResult',
    'MarketSummary',
    'StructureAnalysis',
    'SignalSide',
    'SignalType',
    'VolumeGrade',
    'StructureQuality',
    'get_sector',
    'SCANNER_AVAILABLE'
]
