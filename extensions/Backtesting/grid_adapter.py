"""
GridBacktestAdapter — V8 ATR Grid 策略獨立回測
不走 bot.scan_for_signals()，直接驅動純函數 grid.tick()。

用法：
    cd tools/Backtesting
    python grid_adapter.py --symbols BTC/USDT ETH/USDT --start 2023-01-01 --end 2023-04-30
    python grid_adapter.py --symbols BTC/USDT SOL/USDT --start 2024-06-01 --end 2025-01-01 --balance 5000 --output results_v8
"""
import sys
import os
import json
import argparse
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# ── import 路徑 ──────────────────────────────────────────────────────────────
_BOT_ROOT = os.environ.get("TRADING_BOT_ROOT") or str(
    Path(__file__).resolve().parent.parent.parent / "projects" / "trading_bot"
)
_WORKTREE = str(
    Path(__file__).resolve().parent.parent.parent / "projects" / "trading_bot" /
    ".worktrees" / "feat-grid"
)
# 優先用 worktree（feat/btc-atr-grid 分支），沒有再用 main
for _p in [_WORKTREE, _BOT_ROOT]:
    if Path(_p).exists():
        sys.path.insert(0, _p)
        break

import pandas as pd
import numpy as np

from data_loader import BacktestDataLoader
from bot_compat import get_config_class
from trader.regime import RegimeEngine
from trader.strategies.v8_grid import V8AtrGrid, GridState, GridAction, PoolManager
from trader.indicators.technical import _bbw, _adx, TechnicalAnalysis

Config = get_config_class()

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


# ── 結果 dataclass ───────────────────────────────────────────────────────────

@dataclass
class GridBacktestResult:
    trades: List[dict] = field(default_factory=list)
    equity_curve: List[Tuple] = field(default_factory=list)  # (timestamp, equity)
    regime_log: List[dict] = field(default_factory=list)     # {ts, regime}
    initial_balance: float = 10000.0

    def summary(self) -> dict:
        if not self.trades:
            return {"total_trades": 0, "note": "No trades — possibly never RANGING"}
        wins = [t for t in self.trades if t["pnl"] > 0]
        losses = [t for t in self.trades if t["pnl"] < 0]
        total_pnl = sum(t["pnl"] for t in self.trades)
        gross_profit = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        return {
            "total_trades": len(self.trades),
            "win_rate": len(wins) / len(self.trades) if self.trades else 0,
            "total_pnl_usdt": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl / self.initial_balance * 100, 2),
            "profit_factor": round(gross_profit / gross_loss, 3) if gross_loss > 0 else float("inf"),
            "avg_pnl": round(total_pnl / len(self.trades), 2),
            "max_win": round(max(t["pnl"] for t in self.trades), 2),
            "max_loss": round(min(t["pnl"] for t in self.trades), 2),
            "avg_hold_hours": round(
                sum(t.get("hold_hours", 0) for t in self.trades) / len(self.trades), 1
            ),
            "by_level": _pnl_by_level(self.trades),
            "regime_bars": _regime_counts(self.regime_log),
        }

    def print_summary(self, symbol: str = ""):
        s = self.summary()
        header = f"  Grid Backtest Summary{f'  [{symbol}]' if symbol else ''}"
        print("\n" + "=" * 55)
        print(header)
        print("=" * 55)
        for k, v in s.items():
            if k in ("by_level", "regime_bars"):
                continue
            print(f"  {k:<25} {v}")
        if "regime_bars" in s:
            print("\n  Regime distribution:")
            for r, n in s["regime_bars"].items():
                print(f"    {r:<12} {n} bars")
        if "by_level" in s and s["by_level"]:
            print("\n  PnL by grid level:")
            for lv, stats in sorted(s["by_level"].items()):
                print(f"    L{lv:<4} {stats['n']:>3} trades  avg={stats['avg']:>+8.2f}  total={stats['total']:>+9.2f}")
        print("=" * 55)

    def to_dict(self, symbol: str = "") -> dict:
        s = self.summary()
        return {
            "symbol": symbol,
            "initial_balance": self.initial_balance,
            "summary": s,
            "trades": [
                {k: str(v) if hasattr(v, "isoformat") else v for k, v in t.items()}
                for t in self.trades
            ],
            "equity_curve": [[str(ts), eq] for ts, eq in self.equity_curve],
        }


def _pnl_by_level(trades: List[dict]) -> dict:
    by_lv = {}
    for t in trades:
        lv = abs(t.get("level", 0))
        if lv not in by_lv:
            by_lv[lv] = []
        by_lv[lv].append(t["pnl"])
    return {
        lv: {"n": len(v), "avg": round(sum(v) / len(v), 2), "total": round(sum(v), 2)}
        for lv, v in by_lv.items()
    }


def _regime_counts(regime_log: List[dict]) -> dict:
    counts: dict = {}
    for r in regime_log:
        counts[r["regime"]] = counts.get(r["regime"], 0) + 1
    return counts


# ── 指標計算 ─────────────────────────────────────────────────────────────────

def _add_regime_indicators(df_4h: pd.DataFrame) -> pd.DataFrame:
    """在 4H df 上計算 adx / bbw / atr（RegimeEngine 需要）"""
    df = df_4h.copy()
    # ADX (and DMP/DMN)
    adx_data = _adx(df["high"], df["low"], df["close"], length=14)
    if adx_data is not None:
        for col in adx_data.columns:
            df[col] = adx_data[col]
        adx_cols = [c for c in adx_data.columns if c.startswith("ADX")]
        if adx_cols:
            df["adx"] = adx_data[adx_cols[0]]
    # BBW
    df["bbw"] = _bbw(df["close"], length=20, std_dev=2.0)
    # ATR
    from trader.indicators.technical import _atr
    df["atr"] = _atr(df["high"], df["low"], df["close"], length=14)
    return df


# ── 主回測邏輯 ────────────────────────────────────────────────────────────────

class GridBacktestAdapter:
    """
    V8 Grid 回測適配器。

    流程：
        1. 逐根 4H bar → RegimeEngine.update() 判斷 regime
        2. RANGING → PoolManager.activate() + grid.activate()
        3. 對應的 1H bars → grid.tick() → 收集 GridAction
        4. TRENDING/SQUEEZE → grid.converge() / force_close()
        5. 彙整所有交易，計算 PnL
    """

    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.result = GridBacktestResult(initial_balance=initial_balance)

    def run(
        self,
        df_4h: pd.DataFrame,
        df_1h: pd.DataFrame,
        verbose: bool = False,
    ) -> GridBacktestResult:
        """
        Args:
            df_4h: 4H OHLCV，已含 adx/bbw/atr column（用 _add_regime_indicators()）
            df_1h: 1H OHLCV，index=UTC timestamp
            verbose: 印出每筆交易
        """
        regime_engine = RegimeEngine()
        pool = PoolManager()
        grid = V8AtrGrid(api_client=None, notifier=None)

        equity = self.initial_balance
        open_positions: List[dict] = []   # 模擬開倉記錄

        # 逐根 4H bar（從 warmup 後開始）
        warmup = 60
        for idx in range(warmup, len(df_4h)):
            bar_4h = df_4h.iloc[: idx + 1]
            ts_4h = df_4h.index[idx]

            # ── Regime 更新 ──
            old_regime = regime_engine.current_regime
            regime = regime_engine.update(bar_4h)
            self.result.regime_log.append({"ts": ts_4h, "regime": regime})

            if regime != old_regime and verbose:
                print(f"[{ts_4h}] Regime: {old_regime} → {regime}")

            # ── 取對應的 1H bars（這根 4H bar 內的 4 根 1H）──
            bar_end = ts_4h
            bar_start = df_4h.index[idx - 1] if idx > 0 else ts_4h
            mask_1h = (df_1h.index > bar_start) & (df_1h.index <= bar_end)
            slice_1h = df_1h[mask_1h]

            # ── 非 RANGING：converge（等均值回歸，72h timeout 保護）──
            if regime != "RANGING":
                if grid.state and not grid.state.converging:
                    grid.converge(market_ts=ts_4h)
                    if verbose:
                        print(f"[{ts_4h}] Grid converge → {regime}")
                if grid.state and grid.state.converging:
                    if not slice_1h.empty:
                        close_price = slice_1h["close"].iloc[-1]
                        actions = grid.tick(close_price, slice_1h, market_ts=ts_4h)
                        for action in actions:
                            pnl, closed = self._simulate_action(
                                action, close_price, open_positions, equity, ts_4h, verbose
                            )
                            equity += pnl
                            pool.grid_realized_pnl += pnl
                    if grid.state and grid.state.converging and not grid.state.active_positions:
                        pool.deactivate_grid_pool()
                        grid.deactivate()
                        if verbose:
                            print(f"[{ts_4h}] Grid converge complete")
                continue

            # ── RANGING：啟動網格（如果未啟動）──
            if not grid.state:
                if pool.activate_grid_pool(equity):
                    grid.activate(bar_4h, pool.get_grid_balance())
                    if verbose and grid.state:
                        print(
                            f"[{ts_4h}] Grid activated: center={grid.state.center:.0f} "
                            f"spacing={grid.state.grid_spacing:.0f}"
                        )

            # ── 逐根 1H bar 驅動 grid.tick() ──
            if grid.state and not slice_1h.empty:
                for i in range(len(slice_1h)):
                    sub_1h = slice_1h.iloc[: i + 1]
                    if sub_1h.empty:
                        continue
                    current_price = sub_1h["close"].iloc[-1]
                    ts_1h = sub_1h.index[-1]

                    actions = grid.tick(current_price, sub_1h, market_ts=ts_1h)
                    for action in actions:
                        pnl, closed = self._simulate_action(
                            action, current_price, open_positions, equity, ts_1h, verbose
                        )
                        equity += pnl
                        pool.grid_realized_pnl += pnl

            # equity curve（每 4H bar 記一次）
            self.result.equity_curve.append((ts_4h, round(equity, 2)))

        # 回測結束 — 強平所有剩餘持倉
        if grid.state and grid.state.active_positions:
            last_price = df_1h["close"].iloc[-1]
            last_ts = df_1h.index[-1]
            for pos in list(grid.state.active_positions):
                if pos["side"] == "LONG":
                    pnl = (last_price - pos["entry"]) * pos["size"]
                else:
                    pnl = (pos["entry"] - last_price) * pos["size"]
                equity += pnl
                self.result.trades.append({
                    "ts": last_ts,
                    "side": pos["side"],
                    "level": pos["level"],
                    "entry": pos["entry"],
                    "exit": last_price,
                    "size": pos["size"],
                    "pnl": round(pnl, 4),
                    "hold_hours": 0,
                    "reason": "backtest_end",
                })

        self.result.equity_curve.append((df_4h.index[-1], round(equity, 2)))
        return self.result

    def _simulate_action(
        self,
        action: GridAction,
        current_price: float,
        open_positions: List[dict],
        equity: float,
        ts,
        verbose: bool,
    ) -> Tuple[float, bool]:
        """模擬單筆 GridAction，回傳 (realized_pnl, is_close)。"""
        if action.type == "OPEN":
            open_positions.append({
                "level": action.level,
                "side": action.side,
                "entry": current_price,
                "size": action.size,
                "ts_open": ts,
            })
            return 0.0, False

        elif action.type == "CLOSE":
            # 找對應開倉
            matched = None
            for pos in open_positions:
                if pos["level"] == action.level and pos["side"] == action.side:
                    matched = pos
                    break
            if matched is None:
                return 0.0, True

            open_positions.remove(matched)
            if action.side == "LONG":
                pnl = (current_price - matched["entry"]) * matched["size"]
            else:
                pnl = (matched["entry"] - current_price) * matched["size"]

            hold_h = (
                (ts - matched["ts_open"]).total_seconds() / 3600
                if hasattr(ts - matched["ts_open"], "total_seconds")
                else 0
            )
            self.result.trades.append({
                "ts": ts,
                "side": action.side,
                "level": action.level,
                "entry": matched["entry"],
                "exit": current_price,
                "size": matched["size"],
                "pnl": round(pnl, 4),
                "hold_hours": round(hold_h, 2),
                "reason": "grid_close",
            })
            if verbose:
                emoji = "🟢" if pnl >= 0 else "🔴"
                print(
                    f"  {emoji} [{ts}] L{abs(action.level)} {action.side} "
                    f"entry={matched['entry']:.0f} exit={current_price:.0f} "
                    f"pnl={pnl:+.2f}"
                )
            return pnl, True

        return 0.0, False


# ── CLI 入口 ──────────────────────────────────────────────────────────────────

def _run_one(symbol: str, args, loader: "BacktestDataLoader") -> Optional["GridBacktestResult"]:
    print(f"\n[{symbol}] Loading {args.start} → {args.end}...")
    df_4h = loader.get_data(symbol, "4h", args.start, args.end)
    df_1h = loader.get_data(symbol, "1h", args.start, args.end)

    if df_4h.empty or df_1h.empty:
        print(f"[{symbol}] ERROR: No data loaded. Skipping.")
        return None

    print(f"[{symbol}] 4H bars: {len(df_4h)}, 1H bars: {len(df_1h)}")
    df_4h = _add_regime_indicators(df_4h)

    adapter = GridBacktestAdapter(initial_balance=args.balance)
    result = adapter.run(df_4h, df_1h, verbose=args.verbose)
    result.print_summary(symbol=symbol)
    return result


def main():
    parser = argparse.ArgumentParser(description="Grid Backtest Adapter")
    parser.add_argument("--symbols", nargs="+", default=["BTC/USDT"],
                        help="One or more trading pairs (e.g. BTC/USDT ETH/USDT SOL/USDT)")
    parser.add_argument("--start", default="2025-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2025-12-31", help="End date (YYYY-MM-DD)")
    parser.add_argument("--balance", type=float, default=10000.0, help="Initial balance per symbol (USDT)")
    parser.add_argument("--output", default="", help="Output directory for JSON results (optional)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print each trade")
    args = parser.parse_args()

    loader = BacktestDataLoader()
    all_results = {}

    for symbol in args.symbols:
        result = _run_one(symbol, args, loader)
        if result:
            all_results[symbol] = result

    # ── 多幣彙總 ──
    if len(args.symbols) > 1:
        print("\n" + "=" * 55)
        print("  Multi-Symbol Summary")
        print("=" * 55)
        total_pnl = 0.0
        for sym, res in all_results.items():
            s = res.summary()
            pnl = s.get("total_pnl_usdt", 0)
            pnl_pct = s.get("total_pnl_pct", 0)
            trades = s.get("total_trades", 0)
            wr = s.get("win_rate", 0)
            total_pnl += pnl
            print(f"  {sym:<14} pnl={pnl:>+9.2f} ({pnl_pct:>+6.2f}%)  trades={trades:>4}  wr={wr:.1%}")
        print(f"  {'TOTAL':<14} pnl={total_pnl:>+9.2f}")
        print("=" * 55)

    # ── 儲存結果 ──
    if args.output and all_results:
        _script_dir = Path(__file__).resolve().parent
        out_dir = _script_dir / args.output if not Path(args.output).is_absolute() else Path(args.output)
        out_dir.mkdir(parents=True, exist_ok=True)
        for sym, res in all_results.items():
            safe_name = sym.replace("/", "_")
            out_file = out_dir / f"{safe_name}_{args.start}_{args.end}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(res.to_dict(symbol=sym), f, ensure_ascii=False, indent=2)
            print(f"Saved: {out_file}")
        # 彙總檔
        summary_file = out_dir / "summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(
                {sym: res.summary() for sym, res in all_results.items()},
                f, ensure_ascii=False, indent=2
            )
        print(f"Saved: {summary_file}")


if __name__ == "__main__":
    main()
