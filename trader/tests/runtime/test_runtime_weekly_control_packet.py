import json
import sqlite3
from pathlib import Path

from trader.config import Config
from tools.runtime_weekly_control_packet import (
    RUNTIME_CONFIG_CONTRACT_KEYS,
    build_runtime_weekly_control_payload,
    csv_rows,
    write_runtime_weekly_control_packet,
)


def _write_jsonl(path: Path, events: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n",
        encoding="utf-8",
    )


def _write_positions(path: Path, positions: dict) -> None:
    path.write_text(
        json.dumps({"schema_version": 2, "positions": positions}, indent=2),
        encoding="utf-8",
    )


def _init_trade_db(path: Path, rows: list[dict]) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE trades (
                trade_id TEXT,
                symbol TEXT,
                side TEXT,
                signal_type TEXT,
                strategy_name TEXT,
                entry_price REAL,
                exit_price REAL,
                total_size REAL,
                original_size REAL,
                entry_time TEXT,
                exit_time TEXT,
                pnl_usdt REAL,
                exit_reason TEXT
            )
            """
        )
        for row in rows:
            conn.execute(
                """
                INSERT INTO trades (
                    trade_id, symbol, side, signal_type, strategy_name,
                    entry_price, exit_price, total_size, original_size,
                    entry_time, exit_time, pnl_usdt, exit_reason
                ) VALUES (
                    :trade_id, :symbol, :side, :signal_type, :strategy_name,
                    :entry_price, :exit_price, :total_size, :original_size,
                    :entry_time, :exit_time, :pnl_usdt, :exit_reason
                )
                """,
                row,
            )
        conn.commit()


def _trade(**overrides):
    row = {
        "trade_id": "t1",
        "symbol": "BTC/USDT",
        "side": "LONG",
        "signal_type": "slot_a",
        "strategy_name": "slot_a",
        "entry_price": 100.0,
        "exit_price": 110.0,
        "total_size": 1.0,
        "original_size": 1.0,
        "entry_time": "2026-05-12T00:00:00+00:00",
        "exit_time": "2026-05-16T00:00:00+00:00",
        "pnl_usdt": 120.0,
        "exit_reason": "target",
    }
    row.update(overrides)
    return row


def _baseline_config():
    return {
        key: getattr(Config, key)
        for key in RUNTIME_CONFIG_CONTRACT_KEYS
        if hasattr(Config, key)
    }


def test_runtime_packet_merges_observability_db_positions_and_scanner(tmp_path):
    events_path = tmp_path / "strategy_runtime_funnel.jsonl"
    db_path = tmp_path / "performance.db"
    positions_path = tmp_path / "positions.json"
    scanner_path = tmp_path / "runtime_scanner.json"

    _write_jsonl(
        events_path,
        [
            {
                "ts": "2026-05-12T00:00:00+00:00",
                "event": "config_snapshot",
                "config": {"SYMBOLS": ["BTC/USDT", "ETH/USDT", "SOL/USDT"]},
            },
            {
                "ts": "2026-05-12T01:00:00+00:00",
                "event": "scan_cycle_end",
                "status": "completed",
            },
            {
                "ts": "2026-05-12T02:00:00+00:00",
                "event": "plugin_candidates",
                "plugin_id": "donchian_range_fade_4h_range_width_cv_013",
                "candidate_count": 0,
            },
            {
                "ts": "2026-05-12T03:00:00+00:00",
                "event": "strategy_entry_ready",
                "strategy_id": "slot_a",
            },
            {
                "ts": "2026-05-12T04:00:00+00:00",
                "event": "strategy_reject",
                "reason": "cooldown",
            },
            {
                "ts": "2026-05-12T05:00:00+00:00",
                "event": "execution_filled",
                "strategy_id": "slot_a",
            },
            {
                "ts": "2026-05-13T00:00:00+00:00",
                "event": "execution_failure",
                "strategy_id": "slot_a",
                "reason": "order_execution_exception",
            },
            {
                "ts": "2026-05-14T00:00:00+00:00",
                "event": "execution_skipped",
                "strategy_id": "slot_a",
                "reason": "dry_run",
            },
        ],
    )
    _init_trade_db(db_path, [_trade()])
    _write_positions(
        positions_path,
        {
            "BTC/USDT": {
                "symbol": "BTC/USDT",
                "side": "LONG",
                "avg_entry": 100.0,
                "current_sl": 90.0,
                "risk_plan": {"hard_stop_required": False},
            },
            "ETH/USDT": {
                "symbol": "ETH/USDT",
                "side": "SHORT",
                "avg_entry": 100.0,
                "current_sl": 90.0,
                "risk_plan": {"hard_stop_required": False},
            },
        },
    )
    scanner_path.write_text(
        json.dumps(
            {
                "scanner_contract_version": "runtime-context/v1",
                "scan_time": "2026-05-16T00:00:00+00:00",
                "runtime_selection_feeds_trading": False,
                "runtime_symbols": ["BTC/USDT", "ETH/USDT"],
                "symbols": {"BTC/USDT": {}, "ETH/USDT": {}},
            }
        ),
        encoding="utf-8",
    )

    payload = build_runtime_weekly_control_payload(
        events_path=events_path,
        db_path=db_path,
        positions_path=positions_path,
        scanner_report_path=scanner_path,
        as_of="2026-05-17",
        weeks=8,
    )

    latest = payload["latest_packet"]
    latest_detail = payload["runtime_weekly_details"][-1]

    assert latest["week_start"] == "2026-05-11"
    assert latest["weekly_inputs"]["entry_trades"] == 1
    assert latest["weekly_inputs"]["exit_trades"] == 1
    assert latest["weekly_inputs"]["gross_pnl_usdt"] == 120.0
    assert latest["weekly_inputs"]["fees_est_usdt"] == 0.084
    assert latest["weekly_inputs"]["net_after_fee_est_usdt"] == 119.916
    assert latest["kpis"]["execution_attempt_count_weekly"] == 2
    assert latest["kpis"]["execution_failure_count_weekly"] == 1
    assert latest["kpis"]["config_drift_events_weekly"] == 1
    assert latest["kpis"]["unprotected_position_events_weekly"] == 1
    assert latest["decision"]["state"] == "pause"
    assert set(latest["decision"]["pause_triggers"]) == {
        "config_drift_events_weekly",
        "unprotected_position_events_weekly",
    }

    assert latest_detail["scan_cycle_count"] == 1
    assert latest_detail["strategy_entry_ready_count"] == 1
    assert latest_detail["strategy_reject_reason_counts"] == {"cooldown": 1}
    assert latest_detail["dry_run_execution_skipped_count"] == 1
    assert latest_detail["plugin_zero_candidate_counts"] == {
        "donchian_range_fade_4h_range_width_cv_013": 1
    }
    assert latest_detail["unprotected_position_symbols"] == ["ETH/USDT"]
    assert payload["source_quality"]["scanner_diagnostics"]["symbol_count"] == 2


def test_runtime_packet_can_scope_to_promoted_baseline_profile(tmp_path):
    events_path = tmp_path / "strategy_runtime_funnel.jsonl"
    incomplete_baseline_config = _baseline_config()
    incomplete_baseline_config.pop("MACRO_OVERLAY_ENABLED", None)
    fixture_config = {
        **_baseline_config(),
        "ENABLED_STRATEGIES": ["fixture_long"],
        "SYMBOLS": ["BTC/USDT"],
        "REGIME_ARBITER_ENABLED": False,
    }
    _write_jsonl(
        events_path,
        [
            {
                "ts": "2026-05-12T00:00:00+00:00",
                "event": "config_snapshot",
                "config": _baseline_config(),
            },
            {
                "ts": "2026-05-12T01:00:00+00:00",
                "event": "execution_filled",
                "strategy_id": Config.ENABLED_STRATEGIES[0],
            },
            {
                "ts": "2026-05-12T01:30:00+00:00",
                "event": "config_snapshot",
                "config": incomplete_baseline_config,
            },
            {
                "ts": "2026-05-12T01:45:00+00:00",
                "event": "execution_filled",
                "strategy_id": "incomplete_snapshot_should_drop",
            },
            {
                "ts": "2026-05-12T02:00:00+00:00",
                "event": "config_snapshot",
                "config": fixture_config,
            },
            {
                "ts": "2026-05-12T03:00:00+00:00",
                "event": "execution_failure",
                "strategy_id": "fixture_long",
                "reason": "post_fill_stop_violation",
            },
        ],
    )

    payload = build_runtime_weekly_control_payload(
        events_path=events_path,
        db_path=tmp_path / "missing.db",
        positions_path=tmp_path / "missing_positions.json",
        scanner_report_path=tmp_path / "missing_scanner.json",
        as_of="2026-05-17",
        weeks=1,
        config_profile="promoted_baseline",
    )

    packet = payload["latest_packet"]
    assert payload["evidence_scope"]["mode"] == "config_profile:promoted_baseline"
    assert payload["source_quality"]["runtime_event_count_before_scope"] == 6
    assert payload["source_quality"]["runtime_event_count_after_scope"] == 2
    assert payload["source_quality"]["runtime_event_count_dropped_by_scope"] == 4
    assert payload["source_quality"]["selected_config_snapshot_count"] == 1
    assert packet["weekly_inputs"]["entry_trades"] == 1
    assert packet["kpis"]["execution_attempt_count_weekly"] == 1
    assert packet["kpis"]["execution_failure_count_weekly"] == 0
    assert packet["decision"]["state"] == "continue"


def test_runtime_packet_uses_db_entry_fallback_when_execution_fills_are_absent(tmp_path):
    db_path = tmp_path / "performance.db"
    _init_trade_db(
        db_path,
        [
            _trade(
                trade_id="t1",
                entry_time="2026-03-31T00:00:00+00:00",
                exit_time="2026-04-02T00:00:00+00:00",
            ),
            _trade(
                trade_id="t2",
                entry_time="2026-04-01T00:00:00+00:00",
                exit_time="2026-04-03T00:00:00+00:00",
                pnl_usdt=-20.0,
            ),
        ],
    )

    payload = build_runtime_weekly_control_payload(
        events_path=tmp_path / "missing.jsonl",
        db_path=db_path,
        positions_path=tmp_path / "missing_positions.json",
        scanner_report_path=tmp_path / "missing_scanner.json",
        as_of="2026-04-05",
        weeks=1,
    )

    packet = payload["latest_packet"]
    assert packet["week_start"] == "2026-03-30"
    assert packet["weekly_inputs"]["entry_trades"] == 2
    assert packet["weekly_inputs"]["exit_trades"] == 2
    assert packet["weekly_inputs"]["gross_pnl_usdt"] == 100.0
    assert payload["source_quality"]["entry_trade_source"] == "performance_db_closed_trade_entry_time"


def test_runtime_packet_writer_outputs_json_csv_and_markdown(tmp_path):
    json_path = tmp_path / "packet.json"
    csv_path = tmp_path / "packet.csv"
    report_path = tmp_path / "packet.md"

    payload = write_runtime_weekly_control_packet(
        events_path=tmp_path / "missing.jsonl",
        db_path=tmp_path / "missing.db",
        positions_path=tmp_path / "missing_positions.json",
        scanner_report_path=tmp_path / "missing_scanner.json",
        json_path=json_path,
        csv_path=csv_path,
        report_path=report_path,
        as_of="2026-05-17",
        weeks=2,
    )

    assert json.loads(json_path.read_text(encoding="utf-8"))["schema"] == payload["schema"]
    assert csv_path.read_text(encoding="utf-8").splitlines()[0].startswith("week_start,")
    assert "Runtime Weekly Control Packet" in report_path.read_text(encoding="utf-8")
    assert len(csv_rows(payload)) == 2
