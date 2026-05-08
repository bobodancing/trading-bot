from trader.bot import TradingBot
from trader.config import Config
from trader.utils import RUNTIME_LABEL, build_log_base


def test_trade_log_base_uses_current_runtime_label():
    fields = build_log_base("TRADE_OPEN", "trade-1", "BTC/USDT", "LONG")

    assert fields["bot"] == RUNTIME_LABEL
    assert fields["bot"] == "strategy-runtime"


def test_strategy_display_names_keep_startup_portfolio_readable():
    names = TradingBot._strategy_display_names(Config.ENABLED_STRATEGIES)

    assert names == [
        "Slot A LONG / BTC 4h MACD",
        "Slot B LONG / Donchian range fade",
        "Slot B SHORT / Donchian range fade",
    ]
    assert all(len(name) < 90 for name in names)
