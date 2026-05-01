"""Scanner package exports."""

from .market_scanner import (
    SCANNER_AVAILABLE,
    MarketScanner,
    MarketSummary,
    ScanResult,
    ScannerConfig,
    SignalSide,
    SignalType,
    StructureAnalysis,
    StructureQuality,
    VolumeGrade,
    get_sector,
)
from .runtime_scanner import RuntimeScanner, RuntimeScannerSettings

__version__ = "2.0.0"


def __getattr__(name: str):
    if name in {"ScannerUniverseScanner", "ScannerUniverseSettings"}:
        from .universe_scanner import ScannerUniverseScanner, ScannerUniverseSettings

        exports = {
            "ScannerUniverseScanner": ScannerUniverseScanner,
            "ScannerUniverseSettings": ScannerUniverseSettings,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "MarketScanner",
    "ScannerConfig",
    "ScanResult",
    "MarketSummary",
    "StructureAnalysis",
    "SignalSide",
    "SignalType",
    "VolumeGrade",
    "StructureQuality",
    "get_sector",
    "SCANNER_AVAILABLE",
    "RuntimeScanner",
    "RuntimeScannerSettings",
    "ScannerUniverseScanner",
    "ScannerUniverseSettings",
]
