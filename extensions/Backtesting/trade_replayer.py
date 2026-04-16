"""
Trade Replayer — 從 performance.db 讀取歷史交易，逐根 K 線重播 PositionManager 決策。

使用前：先從 rwUbuntu pull DB
  bash pull_db.sh

用法：
  python trade_replayer.py --db performance.db --limit 20
  python trade_replayer.py --db performance.db --trade-id abc123 --what_if MIN_MFE_R_FOR_PULLBACK=0.5
"""
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

TRADING_BOT_ROOT = Path(__file__).resolve().parent.parent.parent / "projects" / "trading_bot"
sys.path.insert(0, str(TRADING_BOT_ROOT))

from data_loader import BacktestDataLoader
from time_series_engine import TimeSeriesEngine
from bot_compat import get_config_class
from trader.positions import PositionManager
from trader.indicators.technical import TechnicalAnalysis


class TradeReplayer:
    def __init__(self, db_path: str, what_if: dict = None):
        self.db_path = db_path
        self.what_if = what_if or {}
        self.loader = BacktestDataLoader()

    def load_trades(self, limit: int = 50,
                    symbol: Optional[str] = None) -> List[dict]:
        """從 SQLite 讀取交易紀錄"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            q = "SELECT * FROM trades"
            params = []
            if symbol:
                q += " WHERE symbol = ?"
                params.append(symbol)
            q += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]

    def replay(self, trade: dict, buffer_bars: int = 20) -> dict:
        """
        重播單筆交易。
        1. 下載 entry_time 前後的 OHLCV
        2. 重建 PositionManager
        3. 逐根 bar 呼叫 pm.monitor()，記錄每步決策
        4. 比對 actual exit vs replayed exit
        """
        import pandas as pd

        symbol = trade["symbol"]
        # 解析時間（帶 timezone）
        entry_time = datetime.fromisoformat(trade["entry_time"])
        exit_time = datetime.fromisoformat(trade["exit_time"])

        # 拉取 entry_time 前 50 根到 exit_time 後 buffer_bars 根的數據
        start_str = entry_time.strftime("%Y-%m-%d")
        exit_ts = pd.Timestamp(exit_time)
        end_str = (exit_ts + pd.Timedelta(hours=buffer_bars)).strftime("%Y-%m-%d")

        df_1h = self.loader.get_data(symbol, "1h", start_str, end_str)
        df_4h = self.loader.get_data(symbol, "4h", start_str, end_str)

        if df_1h.empty:
            return {"error": "No OHLCV data for replay"}

        # 套用 what_if Config overrides（try/finally 確保還原）
        _config_saved = {}
        try:
            if self.what_if:
                Config = get_config_class()
                for k, v in self.what_if.items():
                    _config_saved[k] = getattr(Config, k, None)
                    setattr(Config, k, v)

            # 重建 PositionManager（從 trade record）
            initial_r = trade.get("initial_r") or 0.0
            stop_loss = (
                trade["entry_price"] - initial_r
                if trade["side"] == "LONG"
                else trade["entry_price"] + initial_r
            )
            pm = PositionManager(
                symbol=trade["symbol"],
                side=trade["side"],
                entry_price=trade["entry_price"],
                stop_loss=stop_loss,
                position_size=trade["total_size"],
            )
            pm.entry_time = entry_time if entry_time.tzinfo else \
                entry_time.replace(tzinfo=timezone.utc)
            pm.initial_r = trade["initial_r"]
            pm.is_v6_pyramid = bool(trade["is_v6_pyramid"])
            pm.signal_tier = trade.get("signal_tier")
            pm.highest_price = trade["entry_price"]
            pm.lowest_price = trade["entry_price"]
            pm.market_regime = trade.get("market_regime", "TRENDING")

            # TSE 控制時間視窗
            tse = TimeSeriesEngine({
                symbol: {"1h": df_1h, "4h": df_4h}
            })

            # 找 entry_time 在 df_1h 中對應的 bar index
            entry_ts = pd.Timestamp(entry_time).tz_localize("UTC") \
                if entry_time.tzinfo is None else pd.Timestamp(entry_time)
            ts_list = sorted(df_1h.index)
            # 從 entry_time 所在 bar 開始推進
            start_idx = next(
                (i for i, t in enumerate(ts_list) if t >= entry_ts), 0
            )

            decisions = []
            replayed_exit_reason = "still_open"
            replayed_exit_price = None  # only set when action == "CLOSE"

            for i in range(start_idx, len(ts_list)):
                ts = ts_list[i]
                tse.set_time(ts)
                current_price = tse.get_current_price(symbol)

                # 取數據（需要 reset_index 轉 timestamp 為 column）
                bars_1h = tse.get_bars(symbol, "1h", limit=50).reset_index()
                if "timestamp" in bars_1h.columns and \
                   hasattr(bars_1h["timestamp"].dtype, "tz") and \
                   bars_1h["timestamp"].dt.tz is not None:
                    bars_1h["timestamp"] = bars_1h["timestamp"].dt.tz_convert(None)

                bars_4h = tse.get_bars(symbol, "4h", limit=50)
                bars_4h_fmt = None
                if not bars_4h.empty:
                    bars_4h_fmt = bars_4h.reset_index()
                    if "timestamp" in bars_4h_fmt.columns and \
                       hasattr(bars_4h_fmt["timestamp"].dtype, "tz") and \
                       bars_4h_fmt["timestamp"].dt.tz is not None:
                        bars_4h_fmt["timestamp"] = bars_4h_fmt["timestamp"].dt.tz_convert(None)
                    bars_4h_fmt = TechnicalAnalysis.calculate_indicators(bars_4h_fmt)

                if len(bars_1h) >= 10:
                    bars_1h = TechnicalAnalysis.calculate_indicators(bars_1h)
                    decision = pm.monitor(current_price, bars_1h, bars_4h_fmt)
                else:
                    decision = {"action": "ACTIVE"}

                decisions.append({
                    "time": str(ts),
                    "price": current_price,
                    "action": decision.get("action", "ACTIVE"),
                    "reason": decision.get("reason"),
                    "new_sl": decision.get("new_sl"),
                })

                action = decision.get("action", "ACTIVE")
                if action == "CLOSE":
                    replayed_exit_reason = decision.get("reason", "CLOSE")
                    replayed_exit_price = current_price
                    break
                # 超過 exit_time + buffer → 停止
                if ts > exit_ts + pd.Timedelta(hours=buffer_bars):
                    replayed_exit_reason = "timeout_in_replay"
                    break

            return {
                "trade_id": trade.get("trade_id"),
                "symbol": symbol,
                "side": trade["side"],
                "actual_exit_reason": trade.get("exit_reason"),
                "actual_exit_price": trade.get("exit_price"),
                "replayed_exit_reason": replayed_exit_reason,
                "replayed_exit_price": replayed_exit_price,
                "decisions": decisions,
                "what_if": self.what_if,
            }
        finally:
            if _config_saved:
                Config = get_config_class()
                for k, v in _config_saved.items():
                    setattr(Config, k, v)

    def report(self, results: List[dict]):
        """輸出 rich 表格（actual vs replayed）"""
        try:
            from rich.table import Table
            from rich.console import Console
            console = Console()
            table = Table(title="Trade Replay Results")
            table.add_column("trade_id", style="cyan")
            table.add_column("symbol")
            table.add_column("actual_exit")
            table.add_column("replayed_exit")
            table.add_column("actual_price", justify="right")
            table.add_column("replayed_price", justify="right")
            table.add_column("bars_replayed", justify="right")
            for r in results:
                same = r["actual_exit_reason"] == r["replayed_exit_reason"]
                style = "green" if same else "yellow"
                table.add_row(
                    str(r.get("trade_id", ""))[:12],
                    r.get("symbol", ""),
                    r.get("actual_exit_reason", ""),
                    r.get("replayed_exit_reason", ""),
                    f"{r.get('actual_exit_price', 0):.2f}",
                    f"{r.get('replayed_exit_price', 0):.2f}" if r.get("replayed_exit_price") else "-",
                    str(len(r.get("decisions", []))),
                    style=style,
                )
            console.print(table)
        except ImportError:
            for r in results:
                print(f"{r.get('trade_id')} | actual: {r.get('actual_exit_reason')} | "
                      f"replayed: {r.get('replayed_exit_reason')}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="V6 Trade Replayer")
    parser.add_argument("--db", required=True, help="perf_db SQLite 路徑")
    parser.add_argument("--limit", type=int, default=10, help="讀取筆數")
    parser.add_argument("--symbol", help="過濾 symbol")
    parser.add_argument("--trade-id", help="重播指定 trade_id")
    parser.add_argument("--what_if", nargs="*",
                        help="覆蓋 Config 參數，格式 KEY=VALUE")
    args = parser.parse_args()

    what_if = {}
    if args.what_if:
        for item in args.what_if:
            k, v = item.split("=", 1)
            if v.lower() in ("true", "false"):
                v = v.lower() == "true"
            else:
                try:
                    v = float(v)
                except ValueError:
                    pass
            what_if[k] = v

    replayer = TradeReplayer(db_path=args.db, what_if=what_if)

    if args.trade_id:
        all_trades = replayer.load_trades(limit=1000)
        trades = [t for t in all_trades if t.get("trade_id") == args.trade_id]
    else:
        trades = replayer.load_trades(limit=args.limit, symbol=args.symbol)

    print(f"Replaying {len(trades)} trades...")
    results = [replayer.replay(t) for t in trades]
    replayer.report(results)
