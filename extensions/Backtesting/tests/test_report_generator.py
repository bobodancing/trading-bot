# tools/Backtesting/tests/test_report_generator.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from backtest_engine import BacktestConfig, BacktestResult
from plugin_candidate_review import DEFAULT_WINDOWS, write_candidate_review_report
from report_generator import ReportGenerator


CANDIDATE_IDS = ("fixture_long", "macd_zero_line_btc_1d")


def make_fake_result():
    idx = pd.date_range("2026-01-01", periods=10, freq="1h", tz="UTC")
    equity = [(ts, 10000 + i * 50) for i, ts in enumerate(idx)]
    trades = [
        {"pnl_usdt": 100.0, "pnl_pct": 1.0, "exit_reason": "STRUCTURE_TRAIL",
         "stage_reached": 2, "symbol": "BTC/USDT", "side": "LONG",
         "strategy_id": "fixture_long", "strategy_version": "1.0.0",
         "entry_price": 40000.0, "exit_price": 40100.0,
         "entry_time": str(idx[0]), "exit_time": str(idx[5]),
         "holding_hours": 5.0, "realized_r": 1.5,
         "mfe_pct": 0.5, "mae_pct": -0.1},
        {"pnl_usdt": -50.0, "pnl_pct": -0.5, "exit_reason": "FAST_STOP",
         "stage_reached": 1, "symbol": "ETH/USDT", "side": "LONG",
         "entry_price": 2000.0, "exit_price": 1990.0,
         "entry_time": str(idx[1]), "exit_time": str(idx[3]),
         "holding_hours": 2.0, "realized_r": -1.0,
         "mfe_pct": 0.1, "mae_pct": -0.5},
    ]
    cfg = BacktestConfig(symbols=["BTC/USDT"], start="2026-01-01", end="2026-01-10")
    return BacktestResult(trades=trades, equity_curve=equity, config=cfg)


def test_report_generates_files(tmp_path):
    result = make_fake_result()
    gen = ReportGenerator()
    gen.generate(result, output_dir=tmp_path)
    assert (tmp_path / "trades.csv").exists()
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "equity_curve.html").exists()


def test_trades_csv_has_correct_columns(tmp_path):
    result = make_fake_result()
    gen = ReportGenerator()
    gen.generate(result, output_dir=tmp_path)
    import pandas as pd
    df = pd.read_csv(tmp_path / "trades.csv")
    for col in [
        "symbol", "side", "strategy_id", "strategy_version",
        "pnl_usdt", "exit_reason", "stage_reached",
    ]:
        assert col in df.columns
    assert df.iloc[0]["strategy_id"] == "fixture_long"
    assert df.iloc[0]["strategy_version"] == "1.0.0"


def test_summary_json_has_required_keys(tmp_path):
    import json
    result = make_fake_result()
    gen = ReportGenerator()
    gen.generate(result, output_dir=tmp_path)
    with open(tmp_path / "summary.json") as f:
        s = json.load(f)
    for key in ["total_trades", "win_rate", "profit_factor",
                "total_return_pct", "max_drawdown_pct", "sharpe"]:
        assert key in s


def _write_review_cell(
    output_dir: Path,
    candidate_id: str,
    window: str,
    *,
    errors=None,
    pnl=0.0,
    trades=0,
    max_dd=0.0,
    include_net_pnl=True,
):
    import json

    cell = output_dir / candidate_id / window
    cell.mkdir(parents=True, exist_ok=True)
    summary = {
        "total_trades": trades,
        "profit_factor": 0.0,
        "win_rate": 0.0,
        "max_drawdown_pct": max_dd,
        "sharpe": 0.0,
        "backtest_run_errors": errors or [],
        "backtest_run_error_count": len(errors or []),
    }
    if include_net_pnl:
        summary["net_pnl"] = pnl
    (cell / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (cell / "trades.csv").write_text(
        f"symbol,entry_time,signal_type,pnl_usdt,realized_r\nBTC/USDT,2026-01-01,fixture_long,{pnl},1.0\n",
        encoding="utf-8",
    )
    (cell / "signal_audit_summary.json").write_text("{}", encoding="utf-8")
    (cell / "signal_entries.csv").write_text("symbol,signal_type,signal_tier\n", encoding="utf-8")
    (cell / "lane_race_audit.csv").write_text(
        "symbol,candidate_signal_type,selected_signal_type,suppressed_by\n",
        encoding="utf-8",
    )


def _report_section(report: str, start: str, end: str) -> str:
    section_start = report.index(start)
    section_end = report.index(end, section_start)
    return report[section_start:section_end]


def _write_complete_review_matrix(output_dir: Path, *, error_cell=None):
    for candidate_id in CANDIDATE_IDS:
        for window in DEFAULT_WINDOWS:
            errors = None
            if error_cell == (candidate_id, window):
                errors = [{
                    "timestamp": "2026-01-01 00:00:00+00:00",
                    "symbol": "*ALL*",
                    "stage": "scan_for_signals",
                    "exc_type": "RuntimeError",
                    "message": "scanner boom",
                }]
            _write_review_cell(output_dir, candidate_id, window, errors=errors)


def test_incomplete_matrix_forces_needs_second_pass(tmp_path):
    (tmp_path / "reports").mkdir()
    output_dir = tmp_path / "results"
    output_dir.mkdir()

    verdict = write_candidate_review_report(tmp_path, output_dir, CANDIDATE_IDS)

    report = (tmp_path / "reports" / "strategy_plugin_candidate_review.md").read_text(encoding="utf-8")
    assert verdict == "NEEDS_SECOND_PASS"
    assert "Incomplete matrix" in report
    assert "Verdict: `NEEDS_SECOND_PASS`" in report


def test_backtest_run_errors_force_needs_second_pass(tmp_path):
    (tmp_path / "reports").mkdir()
    output_dir = tmp_path / "results"
    _write_complete_review_matrix(output_dir, error_cell=("fixture_long", "TRENDING_UP"))

    verdict = write_candidate_review_report(tmp_path, output_dir, CANDIDATE_IDS)

    report = (tmp_path / "reports" / "strategy_plugin_candidate_review.md").read_text(encoding="utf-8")
    assert verdict == "NEEDS_SECOND_PASS"
    assert "Backtest run errors: 1" in report
    assert "scanner boom" in report


def test_candidate_review_net_pnl_falls_back_to_trades_csv(tmp_path):
    (tmp_path / "reports").mkdir()
    output_dir = tmp_path / "results"
    for window in DEFAULT_WINDOWS:
        _write_review_cell(output_dir, "fixture_long", window, pnl=12.5, include_net_pnl=False)

    write_candidate_review_report(tmp_path, output_dir, ["fixture_long"])

    report = (tmp_path / "reports" / "strategy_plugin_candidate_review.md").read_text(encoding="utf-8")
    assert "| `fixture_long` | 3 | 0 | 37.5000 | 0.0000 |" in report


def test_candidate_review_invalid_entry_stop_forces_needs_second_pass(tmp_path):
    (tmp_path / "reports").mkdir()
    output_dir = tmp_path / "results"
    for window in DEFAULT_WINDOWS:
        _write_review_cell(output_dir, "fixture_long", window)

    bad_cell = output_dir / "fixture_long" / "TRENDING_UP"
    (bad_cell / "trades.csv").write_text(
        "symbol,side,entry_price,entry_initial_sl,pnl_usdt\n"
        "BTC/USDT,LONG,100.0,101.0,0.0\n",
        encoding="utf-8",
    )

    verdict = write_candidate_review_report(tmp_path, output_dir, ["fixture_long"])

    report = (tmp_path / "reports" / "strategy_plugin_candidate_review.md").read_text(encoding="utf-8")
    assert verdict == "NEEDS_SECOND_PASS"
    assert "Trade invariant failures: 1" in report
    assert "entry_initial_sl=101" in report


def test_candidate_review_report_renders_per_window_section(tmp_path):
    (tmp_path / "reports").mkdir()
    output_dir = tmp_path / "results"
    windows = list(DEFAULT_WINDOWS)

    for candidate_idx, candidate_id in enumerate(CANDIDATE_IDS, start=1):
        for window_idx, window in enumerate(windows, start=1):
            _write_review_cell(
                output_dir,
                candidate_id,
                window,
                pnl=10.0 * candidate_idx + window_idx,
                trades=candidate_idx + window_idx,
                max_dd=1.5 * window_idx,
            )

    write_candidate_review_report(tmp_path, output_dir, CANDIDATE_IDS)

    report = (tmp_path / "reports" / "strategy_plugin_candidate_review.md").read_text(encoding="utf-8")
    section = _report_section(report, "## Per-Window Detail", "## Run settings")
    assert section.count("| `") == 6
    assert "| `fixture_long` | TRENDING_UP | 2 | 11.0000 | 1.5000 | 0 | 0 |" in section
    assert "| `fixture_long` | RANGING | 3 | 12.0000 | 3.0000 | 0 | 0 |" in section
    assert "| `macd_zero_line_btc_1d` | MIXED | 5 | 23.0000 | 4.5000 | 0 | 0 |" in section
    assert "- `max_dd_pct` in aggregate tables is the max value across windows, not the sum." in report


def test_candidate_review_report_marks_missing_window(tmp_path):
    (tmp_path / "reports").mkdir()
    output_dir = tmp_path / "results"
    _write_review_cell(output_dir, "fixture_long", "TRENDING_UP", pnl=5.0, trades=1, max_dd=2.0)
    _write_review_cell(output_dir, "fixture_long", "MIXED", pnl=7.0, trades=2, max_dd=3.0)

    write_candidate_review_report(tmp_path, output_dir, ["fixture_long"])

    report = (tmp_path / "reports" / "strategy_plugin_candidate_review.md").read_text(encoding="utf-8")
    section = _report_section(report, "## Per-Window Detail", "## Run settings")
    assert "| `fixture_long` | RANGING (missing) | — | — | — | — | — |" in section
