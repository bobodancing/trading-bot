import json

from tools.runtime_evidence_window import rotate_runtime_evidence_window


def test_rotate_runtime_evidence_window_moves_default_evidence(tmp_path):
    jsonl = tmp_path / ".log" / "runtime_observability" / "strategy_runtime_funnel.jsonl"
    latest = tmp_path / ".log" / "runtime_observability" / "strategy_runtime_latest.json"
    packet = tmp_path / ".log" / "weekly_control" / "runtime_weekly_control_packet.md"
    scanner = tmp_path / "runtime_scanner.json"
    db = tmp_path / "performance.db"
    positions = tmp_path / ".log" / "positions.json"

    for path, content in (
        (jsonl, "{}\n"),
        (latest, "{}"),
        (packet, "# packet\n"),
        (scanner, "{}"),
        (db, "db"),
        (positions, "{}"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    manifest = rotate_runtime_evidence_window(
        repo_root=tmp_path,
        archive_root=tmp_path / ".log" / "evidence_archive",
        stamp="20260518T000000Z",
    )

    assert manifest["dry_run"] is False
    assert manifest["planned_move_count"] == 4
    assert manifest["moved_count"] == 4
    assert not jsonl.exists()
    assert not latest.exists()
    assert not packet.exists()
    assert not scanner.exists()
    assert db.exists()
    assert positions.exists()
    assert (
        tmp_path
        / ".log"
        / "evidence_archive"
        / "20260518T000000Z"
        / ".log"
        / "runtime_observability"
        / "strategy_runtime_funnel.jsonl"
    ).exists()

    archived_manifest = json.loads(
        (
            tmp_path
            / ".log"
            / "evidence_archive"
            / "20260518T000000Z"
            / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert archived_manifest["schema"] == "strategy_runtime_evidence_window_rotation.v1"
    assert archived_manifest["include_db"] is False
    assert archived_manifest["include_positions"] is False


def test_rotate_runtime_evidence_window_dry_run_is_non_mutating(tmp_path):
    jsonl = tmp_path / ".log" / "runtime_observability" / "strategy_runtime_funnel.jsonl"
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    jsonl.write_text("{}\n", encoding="utf-8")

    manifest = rotate_runtime_evidence_window(
        repo_root=tmp_path,
        archive_root=tmp_path / ".log" / "evidence_archive",
        stamp="20260518T000000Z",
        dry_run=True,
    )

    assert manifest["dry_run"] is True
    assert manifest["planned_move_count"] == 1
    assert manifest["moved_count"] == 0
    assert jsonl.exists()
    assert not (tmp_path / ".log" / "evidence_archive").exists()


def test_rotate_runtime_evidence_window_requires_explicit_stateful_files(tmp_path):
    db = tmp_path / "performance.db"
    positions = tmp_path / ".log" / "positions.json"
    for path in (db, positions):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("state", encoding="utf-8")

    manifest = rotate_runtime_evidence_window(
        repo_root=tmp_path,
        archive_root=tmp_path / ".log" / "evidence_archive",
        stamp="20260518T000000Z",
        include_db=True,
        include_positions=True,
    )

    assert manifest["planned_move_count"] == 2
    assert not db.exists()
    assert not positions.exists()
    assert (
        tmp_path
        / ".log"
        / "evidence_archive"
        / "20260518T000000Z"
        / "performance.db"
    ).exists()
    assert (
        tmp_path
        / ".log"
        / "evidence_archive"
        / "20260518T000000Z"
        / ".log"
        / "positions.json"
    ).exists()
