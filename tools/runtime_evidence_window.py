"""Rotate local runtime evidence into a timestamped archive.

The tool prepares a clean Phase 3 observation window without touching runtime
defaults or placing orders. By default it archives evidence files only; stateful
runtime files such as positions.json and performance.db require explicit flags.
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARCHIVE_ROOT = REPO_ROOT / ".log" / "evidence_archive"

DEFAULT_EVIDENCE_PATHS = (
    ".log/runtime_observability/strategy_runtime_funnel.jsonl",
    ".log/runtime_observability/strategy_runtime_latest.json",
    ".log/weekly_control/runtime_weekly_control_packet.md",
    ".log/weekly_control/runtime_weekly_control_packets.json",
    ".log/weekly_control/runtime_weekly_control_packets.csv",
    ".log/weekly_control/runtime_weekly_control_packet_baseline_scoped.md",
    ".log/weekly_control/runtime_weekly_control_packets_baseline_scoped.json",
    ".log/weekly_control/runtime_weekly_control_packets_baseline_scoped.csv",
    "runtime_scanner.json",
)
OPTIONAL_DB_PATHS = ("performance.db",)
OPTIONAL_POSITION_PATHS = (".log/positions.json",)


@dataclass(frozen=True)
class RotationItem:
    relative_path: str
    source_path: Path
    archive_path: Path
    exists: bool
    size_bytes: int | None
    kind: str


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _resolve_under_repo(repo_root: Path, relative_path: str) -> Path:
    root = repo_root.resolve()
    target = (root / relative_path).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"path escapes repo root: {relative_path}")
    return target


def _build_items(
    *,
    repo_root: Path,
    archive_root: Path,
    stamp: str,
    include_db: bool,
    include_positions: bool,
) -> list[RotationItem]:
    paths = list(DEFAULT_EVIDENCE_PATHS)
    if include_db:
        paths.extend(OPTIONAL_DB_PATHS)
    if include_positions:
        paths.extend(OPTIONAL_POSITION_PATHS)

    items: list[RotationItem] = []
    for relative_path in paths:
        source = _resolve_under_repo(repo_root, relative_path)
        archive = archive_root / stamp / relative_path
        exists = source.exists()
        kind = "file" if source.is_file() else "missing"
        items.append(
            RotationItem(
                relative_path=relative_path,
                source_path=source,
                archive_path=archive,
                exists=exists,
                size_bytes=source.stat().st_size if exists and source.is_file() else None,
                kind=kind,
            )
        )
    return items


def _manifest(
    *,
    stamp: str,
    items: list[RotationItem],
    repo_root: Path,
    archive_root: Path,
    dry_run: bool,
    include_db: bool,
    include_positions: bool,
) -> dict[str, Any]:
    moved = [item for item in items if item.exists and item.kind == "file"]
    return {
        "schema": "strategy_runtime_evidence_window_rotation.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "timestamp": stamp,
        "repo_root": str(repo_root),
        "archive_root": str(archive_root),
        "dry_run": dry_run,
        "include_db": include_db,
        "include_positions": include_positions,
        "moved_count": 0 if dry_run else len(moved),
        "planned_move_count": len(moved),
        "items": [
            {
                "relative_path": item.relative_path,
                "source_path": str(item.source_path),
                "archive_path": str(item.archive_path),
                "exists": item.exists,
                "size_bytes": item.size_bytes,
                "kind": item.kind,
                "action": "move" if item.exists and item.kind == "file" else "skip_missing",
            }
            for item in items
        ],
        "next_packet_command": (
            "python tools/runtime_weekly_control_packet.py "
            "--config-profile promoted_baseline"
        ),
    }


def rotate_runtime_evidence_window(
    *,
    repo_root: Path = REPO_ROOT,
    archive_root: Path = DEFAULT_ARCHIVE_ROOT,
    stamp: str | None = None,
    include_db: bool = False,
    include_positions: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Move local evidence files into a timestamped archive."""

    repo_root = repo_root.resolve()
    archive_root = archive_root.resolve()
    if repo_root != archive_root and repo_root not in archive_root.parents:
        raise ValueError("archive_root must stay under repo root")

    resolved_stamp = stamp or _timestamp()
    items = _build_items(
        repo_root=repo_root,
        archive_root=archive_root,
        stamp=resolved_stamp,
        include_db=include_db,
        include_positions=include_positions,
    )
    archive_dir = archive_root / resolved_stamp

    if not dry_run:
        archive_dir.mkdir(parents=True, exist_ok=True)
        for item in items:
            if not item.exists or item.kind != "file":
                continue
            item.archive_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item.source_path), str(item.archive_path))

    manifest = _manifest(
        stamp=resolved_stamp,
        items=items,
        repo_root=repo_root,
        archive_root=archive_root,
        dry_run=dry_run,
        include_db=include_db,
        include_positions=include_positions,
    )
    if not dry_run:
        manifest_path = archive_dir / "manifest.json"
        manifest["manifest_path"] = str(manifest_path)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Archive local runtime evidence before a clean observation window."
    )
    parser.add_argument("--archive-root", type=Path, default=DEFAULT_ARCHIVE_ROOT)
    parser.add_argument("--timestamp", default=None)
    parser.add_argument("--include-db", action="store_true")
    parser.add_argument("--include-positions", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest = rotate_runtime_evidence_window(
        archive_root=args.archive_root,
        stamp=args.timestamp,
        include_db=args.include_db,
        include_positions=args.include_positions,
        dry_run=args.dry_run,
    )
    print(json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
