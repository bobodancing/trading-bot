import json
import sys
from pathlib import Path
from types import SimpleNamespace


BACKTEST_ROOT = Path(__file__).resolve().parents[1]
if str(BACKTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKTEST_ROOT))

from plugin_parameter_sweep import build_sweep_cells
from plugin_parameter_sweep import write_parameter_sweep_report
from scripts import run_parameter_sweep as sweep


def test_build_sweep_cells_is_small_and_deterministic():
    cells = build_sweep_cells({"atr_mult": [1.0, 1.5], "fast_len": [7, 9]})

    assert [cell["cell_id"] for cell in cells] == ["cell_001", "cell_002", "cell_003", "cell_004"]
    assert cells[0]["params"] == {"atr_mult": 1.0, "fast_len": 7}
    assert cells[-1]["params"] == {"atr_mult": 1.5, "fast_len": 9}


def test_parameter_sweep_writes_separate_artifacts_without_touching_baseline(tmp_path, monkeypatch):
    baseline = tmp_path / "reports" / "strategy_plugin_candidate_review.md"
    baseline.parent.mkdir(parents=True)
    baseline.write_text("locked baseline\n", encoding="utf-8")

    configs = []

    class FakeBacktestEngine:
        def __init__(self, config):
            self.config = config
            configs.append(config)

        def run(self):
            return SimpleNamespace(config=self.config)

    class FakeReportGenerator:
        def generate(self, result, output_dir):
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            params = result.config.strategy_params_override["fixture_long"]
            stop_pct = float(params["stop_pct"])
            (output_dir / "summary.json").write_text(
                json.dumps({
                    "total_trades": 1,
                    "max_drawdown_pct": stop_pct,
                    "backtest_run_error_count": 0,
                }),
                encoding="utf-8",
            )
            (output_dir / "trades.csv").write_text(
                "symbol,side,entry_price,entry_initial_sl,pnl_usdt\n"
                f"BTC/USDT,LONG,100.0,99.0,{stop_pct}\n",
                encoding="utf-8",
            )
            (output_dir / "signal_audit_summary.json").write_text("{}", encoding="utf-8")
            (output_dir / "signal_entries.csv").write_text("symbol,signal_type\n", encoding="utf-8")

    monkeypatch.setattr(sweep, "BacktestEngine", FakeBacktestEngine)
    monkeypatch.setattr(sweep, "ReportGenerator", FakeReportGenerator)

    report_path, manifest_path = sweep.run_parameter_sweep(
        "fixture_long",
        {"stop_pct": [0.01, 0.02]},
        sweep_id="fixture_stop_sweep",
        symbols=["BTC/USDT"],
        windows={"SMOKE": ("2026-01-01", "2026-01-02")},
        results_root=tmp_path / "results" / "sweeps",
        repo_root=tmp_path,
    )

    assert baseline.read_text(encoding="utf-8") == "locked baseline\n"
    assert report_path.name == "strategy_plugin_parameter_sweep_fixture_stop_sweep.md"
    assert manifest_path.exists()
    assert "`cell_001`" in report_path.read_text(encoding="utf-8")
    assert "`cell_002`" in report_path.read_text(encoding="utf-8")
    assert "RESEARCH_SWEEP_ONLY" in report_path.read_text(encoding="utf-8")
    assert configs[0].strategy_params_override == {"fixture_long": {"stop_pct": 0.01}}
    assert configs[1].strategy_params_override == {"fixture_long": {"stop_pct": 0.02}}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["promotion_eligible"] is False
    assert manifest["cells"][1]["params"] == {"stop_pct": 0.02}


def test_parameter_sweep_rejects_unknown_plugin_param(tmp_path):
    try:
        sweep.run_parameter_sweep(
            "fixture_long",
            {"not_real": [1]},
            sweep_id="bad_sweep",
            windows={"SMOKE": ("2026-01-01", "2026-01-02")},
            results_root=tmp_path / "results",
            repo_root=tmp_path,
        )
    except ValueError as exc:
        assert "unknown param" in str(exc)
    else:
        raise AssertionError("expected unknown param to fail fast")


def _write_sweep_window(output_dir: Path, *, trades: int, pnl: float, max_dd: float, errors=None):
    output_dir.mkdir(parents=True, exist_ok=True)
    errors = errors or []
    (output_dir / "summary.json").write_text(
        json.dumps({
            "total_trades": trades,
            "net_pnl": pnl,
            "max_drawdown_pct": max_dd,
            "backtest_run_error_count": len(errors),
            "backtest_run_errors": errors,
        }),
        encoding="utf-8",
    )
    (output_dir / "trades.csv").write_text(
        "symbol,side,entry_price,entry_initial_sl,pnl_usdt\n"
        f"BTC/USDT,LONG,100.0,99.0,{pnl}\n",
        encoding="utf-8",
    )


def _report_section(report: str, start: str, end: str) -> str:
    section_start = report.index(start)
    section_end = report.index(end, section_start)
    return report[section_start:section_end]


def test_sweep_report_renders_cell_by_window_matrix(tmp_path):
    sweep_dir = tmp_path / "results" / "sweeps" / "fixture" / "fixture_sweep"
    cells = [
        {"cell_id": "cell_001", "params": {"atr_mult": 1.0}},
        {"cell_id": "cell_002", "params": {"atr_mult": 1.5}},
    ]
    windows = {
        "TRENDING_UP": ("2026-01-01", "2026-01-02"),
        "RANGING": ("2026-01-03", "2026-01-04"),
    }
    _write_sweep_window(sweep_dir / "cell_001" / "TRENDING_UP", trades=1, pnl=10.0, max_dd=2.0)
    _write_sweep_window(sweep_dir / "cell_001" / "RANGING", trades=2, pnl=20.0, max_dd=3.0)
    _write_sweep_window(sweep_dir / "cell_002" / "TRENDING_UP", trades=3, pnl=30.0, max_dd=4.0)
    _write_sweep_window(sweep_dir / "cell_002" / "RANGING", trades=4, pnl=40.0, max_dd=5.0)

    report_path = write_parameter_sweep_report(
        tmp_path,
        sweep_dir,
        sweep_id="fixture_sweep",
        candidate_id="fixture_long",
        cells=cells,
        windows=windows,
    )

    report = report_path.read_text(encoding="utf-8")
    section = _report_section(report, "## Per-Window Detail", "## Interpretation Guardrails")
    assert section.count("| `cell_") == 4
    assert "| `cell_001` | `{\"atr_mult\": 1.0}` | TRENDING_UP | 1 | 10.0000 | 2.0000 | 0 | 0 |" in section
    assert "| `cell_001` | `{\"atr_mult\": 1.0}` | RANGING | 2 | 20.0000 | 3.0000 | 0 | 0 |" in section
    assert "| `cell_002` | `{\"atr_mult\": 1.5}` | RANGING | 4 | 40.0000 | 5.0000 | 0 | 0 |" in section
    assert "- `max_dd_pct` in aggregate tables is the max value across windows, not the sum." in report


def test_sweep_report_marks_missing_cell_window(tmp_path):
    sweep_dir = tmp_path / "results" / "sweeps" / "fixture" / "fixture_sweep"
    cells = [{"cell_id": "cell_001", "params": {"atr_mult": 1.0}}]
    windows = {
        "TRENDING_UP": ("2026-01-01", "2026-01-02"),
        "RANGING": ("2026-01-03", "2026-01-04"),
    }
    _write_sweep_window(sweep_dir / "cell_001" / "TRENDING_UP", trades=1, pnl=10.0, max_dd=2.0)

    report_path = write_parameter_sweep_report(
        tmp_path,
        sweep_dir,
        sweep_id="fixture_sweep",
        candidate_id="fixture_long",
        cells=cells,
        windows=windows,
    )

    report = report_path.read_text(encoding="utf-8")
    section = _report_section(report, "## Per-Window Detail", "## Interpretation Guardrails")
    assert "| `cell_001` | `{\"atr_mult\": 1.0}` | RANGING (missing) | — | — | — | — | — |" in section
