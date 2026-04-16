"""Replay BTC regime, arbiter, and router decisions over historical 4H bars.

This is a research harness. It does not place orders and does not require the
runtime router flag to be enabled.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import pandas as pd


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOT_ROOT = WORKSPACE_ROOT / "projects" / "trading_bot" / ".worktrees" / "feat-regime-router"
FALLBACK_BOT_ROOT = WORKSPACE_ROOT / "projects" / "trading_bot" / ".worktrees" / "feat-grid"


def _resolve_bot_root(cli_value: Optional[str]) -> Path:
    if cli_value:
        return Path(cli_value).resolve()
    env = os.environ.get("TRADING_BOT_ROOT")
    if env:
        return Path(env).resolve()
    if (DEFAULT_BOT_ROOT / "trader" / "bot.py").exists():
        return DEFAULT_BOT_ROOT.resolve()
    return FALLBACK_BOT_ROOT.resolve()


def _bootstrap_bot_root(bot_root: Path) -> None:
    os.environ["TRADING_BOT_ROOT"] = str(bot_root)
    sys.path.insert(0, str(bot_root))


def _prepare_btc_features(df: pd.DataFrame) -> pd.DataFrame:
    from trader.indicators.technical import TechnicalAnalysis, _adx, _bbw

    prepared = df.copy()
    prepared = TechnicalAnalysis.calculate_indicators(prepared)
    prepared["bbw"] = _bbw(prepared["close"])
    adx_data = _adx(prepared["high"], prepared["low"], prepared["close"], length=14)
    if adx_data is not None:
        for col in adx_data.columns:
            if col.startswith("DMP") or col.startswith("DMN"):
                prepared[col] = adx_data[col]
    return prepared


def _make_context(regime_engine, regime: str, candle_time) -> dict:
    return {
        "source": "regime",
        "trend": None,
        "regime": regime,
        "detected": regime_engine.last_detected_regime,
        "direction": regime_engine.direction_hint,
        "candle_time": str(candle_time),
        "reason": "regime_replay",
    }


def _mixed_bucket(snapshot, raw_regime: str, detected: Optional[str]) -> str:
    components = getattr(snapshot, "components", {}) or {}
    reason = getattr(snapshot, "reason", "") or ""
    if components.get("chop_trend") == 1.0 or "chop_trend" in reason:
        return "chop_trend"
    if raw_regime == "TRENDING" and detected and detected not in {"TRENDING", "UNKNOWN"}:
        return "transition"
    if getattr(snapshot, "label", None) == "NEUTRAL":
        return "neutral"
    return ""


def run_replay(
    *,
    symbols: list[str],
    start: str,
    end: str,
    output_dir: Path,
    bot_root: Path,
    policy: Optional[str] = None,
    warmup_bars: int = 60,
    analysis_start: Optional[str] = None,
    analysis_end: Optional[str] = None,
) -> tuple[pd.DataFrame, dict]:
    _bootstrap_bot_root(bot_root)

    import backtest_engine as backtest_engine_module
    from data_loader import BacktestDataLoader
    from trader.arbiter import RegimeArbiter
    from trader.regime import RegimeEngine
    from trader.routing import RegimeRouter

    backtest_engine_module.TRADING_BOT_ROOT = bot_root
    cfg = backtest_engine_module.BacktestConfig(symbols=symbols, start=start, end=end)
    loader = BacktestDataLoader()
    btc_df = loader.get_data("BTC/USDT", "4h", cfg.start, cfg.end)
    if btc_df.empty:
        raise RuntimeError("No BTC/USDT 4h data available for replay window")

    rows: list[dict] = []
    analysis_start_ts = pd.to_datetime(analysis_start, utc=True) if analysis_start else None
    analysis_end_ts = pd.to_datetime(analysis_end, utc=True) if analysis_end else None
    with backtest_engine_module._backtest_context({}) as Config:
        regime_engine = RegimeEngine()
        arbiter = RegimeArbiter()
        router = RegimeRouter(policy=policy or getattr(Config, "REGIME_ROUTER_POLICY", None))

        for i, candle_time in enumerate(btc_df.index):
            if i < warmup_bars:
                continue
            visible = _prepare_btc_features(btc_df.loc[:candle_time].tail(100))
            regime = regime_engine.update(visible)
            context = _make_context(regime_engine, regime, candle_time)
            snapshot = arbiter.evaluate(context=context, df_4h=visible)
            candle_ts = pd.Timestamp(candle_time)
            if candle_ts.tzinfo is None:
                candle_ts = candle_ts.tz_localize("UTC")
            else:
                candle_ts = candle_ts.tz_convert("UTC")
            if analysis_start_ts is not None and candle_ts < analysis_start_ts:
                continue
            if analysis_end_ts is not None and candle_ts > analysis_end_ts:
                continue

            for signal_side in ("LONG", "SHORT"):
                decision = router.route(snapshot, signal_type="2B", signal_side=signal_side)
                rows.append({
                    "timestamp": pd.Timestamp(candle_time).isoformat(),
                    "signal_type": "2B",
                    "signal_side": signal_side,
                    "raw_regime": context.get("regime"),
                    "detected_regime": context.get("detected"),
                    "arbiter_label": snapshot.label,
                    "arbiter_confidence": snapshot.confidence,
                    "arbiter_entry_allowed": snapshot.entry_allowed,
                    "arbiter_reason": snapshot.reason,
                    "router_decision": "allow" if decision.allowed else "block",
                    "router_allowed": decision.allowed,
                    "router_selected_strategy": decision.selected_strategy,
                    "router_reason": decision.reason,
                    "router_block_reason": "" if decision.allowed else decision.reason,
                    "router_policy": decision.policy,
                    "mixed_bucket": _mixed_bucket(
                        snapshot,
                        str(context.get("regime")),
                        context.get("detected"),
                    ),
                })

    result = pd.DataFrame(rows)
    summary = {
        "rows": int(len(result)),
        "bot_root": str(bot_root),
        "start": start,
        "end": end,
        "analysis_start": analysis_start,
        "analysis_end": analysis_end,
        "router_allowed": (
            result["router_allowed"].value_counts(dropna=False).to_dict()
            if not result.empty else {}
        ),
        "router_decision": (
            result["router_decision"].value_counts(dropna=False).to_dict()
            if not result.empty else {}
        ),
        "arbiter_label": (
            result["arbiter_label"].value_counts(dropna=False).to_dict()
            if not result.empty else {}
        ),
        "mixed_bucket": (
            result["mixed_bucket"].replace("", "none").value_counts(dropna=False).to_dict()
            if not result.empty else {}
        ),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_dir / "regime_router_replay.csv", index=False)
    (output_dir / "regime_router_replay_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay regime arbiter/router decisions.")
    parser.add_argument("--symbols", nargs="+", default=["BTC/USDT"])
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", default="results/regime_router_replay")
    parser.add_argument("--bot-root", default=None)
    parser.add_argument("--policy", default=None)
    parser.add_argument("--warmup-bars", type=int, default=60)
    parser.add_argument("--analysis-start", default=None)
    parser.add_argument("--analysis-end", default=None)
    args = parser.parse_args()

    bot_root = _resolve_bot_root(args.bot_root)
    output_dir = Path(__file__).resolve().parent / args.output
    _, summary = run_replay(
        symbols=args.symbols,
        start=args.start,
        end=args.end,
        output_dir=output_dir,
        bot_root=bot_root,
        policy=args.policy,
        warmup_bars=args.warmup_bars,
        analysis_start=args.analysis_start,
        analysis_end=args.analysis_end,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
