"""回測報表生成 — CSV + JSON + Plotly HTML"""
import json
import pandas as pd
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backtest_engine import BacktestResult


REGIME_ORDER = ("TRENDING", "RANGING", "SQUEEZE")


class ReportGenerator:
    def generate(self, result: "BacktestResult", output_dir: Path):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        regime_composition = self._window_regime_composition(result)

        self._write_trades_csv(result, output_dir)
        self._write_summary_json(result, output_dir, regime_composition)
        self._write_equity_html(result, output_dir)
        self._write_signal_audit(result, output_dir)
        self._print_regime_composition(regime_composition)
        print(f"[Report] 輸出至 {output_dir}")

    def _write_trades_csv(self, result, output_dir: Path):
        TRADE_COLUMNS = [
            "symbol", "side", "exit_strategy", "pnl_usdt", "pnl_pct",
            "exit_reason", "stage_reached",
            "entry_price", "exit_price", "entry_time", "exit_time",
            "holding_hours", "realized_r", "mfe_pct", "mae_pct",
        ]
        if result.trades:
            df = pd.DataFrame(result.trades)
        else:
            df = pd.DataFrame(columns=TRADE_COLUMNS)
        df.to_csv(output_dir / "trades.csv", index=False)

    def _write_summary_json(self, result, output_dir: Path, regime_composition=None):
        summary = dict(result.summary)
        if regime_composition:
            summary["window_regime_composition_4h"] = regime_composition
        with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    def _write_equity_html(self, result, output_dir: Path):
        try:
            import plotly.graph_objects as go
        except ImportError:
            print("[Report] plotly 未安裝，跳過 equity_curve.html")
            # 建立空檔避免測試 FileNotFoundError
            (output_dir / "equity_curve.html").write_text("<p>plotly not installed</p>")
            return

        times = [str(ts) for ts, _ in result.equity_curve]
        values = [v for _, v in result.equity_curve]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=times, y=values, mode="lines",
            name="Portfolio Value", line=dict(color="#00d4aa", width=2)
        ))
        fig.update_layout(
            title=f"Equity Curve [{result.config.strategy}] ({result.config.start} ~ {result.config.end})",
            xaxis_title="Time", yaxis_title="USDT",
            template="plotly_dark",
        )
        fig.write_html(str(output_dir / "equity_curve.html"))

    def _write_signal_audit(self, result, output_dir: Path):
        audit = getattr(result, 'signal_audit', None)
        if audit is None:
            return
        audit.save(output_dir)
        print(f"[Report] Signal audit: {len(audit.rejects)} rejects, "
              f"{len(audit.entries)} entries, "
              f"{len(audit.regime_transitions)} regime transitions, "
              f"{len(audit.btc_trend_snapshots)} BTC trend snapshots")

    def _window_regime_composition(self, result):
        audit = getattr(result, "signal_audit", None)
        if audit is None:
            return None

        df = audit.btc_trend_df()
        if df.empty or "regime" not in df.columns:
            return None

        df = df[df["source"].isin(["regime_probe", "regime"])]
        if df.empty:
            return None

        # Prefer the audit-only probe because it is deduped to one row per BTC
        # 4H candle even when grid is disabled.
        if (df["source"] == "regime_probe").any():
            df = df[df["source"] == "regime_probe"]

        df = df[df["regime"].isin(REGIME_ORDER)].drop_duplicates(
            subset=["timestamp"],
            keep="last",
        )
        if df.empty:
            return None

        counts = df["regime"].value_counts().to_dict()
        total = int(sum(counts.values()))
        composition = {
            "source": "BTC/USDT",
            "timeframe": "4h",
            "total_bars": total,
        }
        for regime in REGIME_ORDER:
            bars = int(counts.get(regime, 0))
            pct = round((bars / total * 100.0) if total else 0.0, 1)
            composition[regime] = {"pct": pct, "bars": bars}
        return composition

    def _print_regime_composition(self, composition):
        if not composition:
            return
        print("[Report] Window regime composition (4H bars):")
        for regime in REGIME_ORDER:
            item = composition[regime]
            print(f"  {regime:<8} : {item['pct']:.1f}% ({item['bars']} bars)")
