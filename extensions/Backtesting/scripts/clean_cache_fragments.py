"""Dry-run cache fragment cleaner for Backtesting parquet files."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


@dataclass(frozen=True)
class CacheFile:
    path: Path
    symbol: str
    timeframe: str
    start: date
    end: date

    @property
    def key(self) -> tuple[str, str]:
        return self.symbol, self.timeframe

    @property
    def days(self) -> int:
        return (self.end - self.start).days


def parse_cache_file(path: Path) -> CacheFile | None:
    """Parse SYMBOL_TF_YYYYMMDD_YYYYMMDD.parquet cache filenames."""
    if path.suffix != ".parquet":
        return None

    parts = path.stem.rsplit("_", 3)
    if len(parts) != 4:
        return None

    symbol, timeframe, start_s, end_s = parts
    try:
        start = datetime.strptime(start_s, "%Y%m%d").date()
        end = datetime.strptime(end_s, "%Y%m%d").date()
    except ValueError:
        return None

    return CacheFile(
        path=path,
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
    )


def find_cache_fragments(cache_dir: Path, min_days: int) -> list[CacheFile]:
    parsed = [
        item
        for path in cache_dir.glob("*.parquet")
        if (item := parse_cache_file(path)) is not None
    ]

    by_key: dict[tuple[str, str], list[CacheFile]] = defaultdict(list)
    for item in parsed:
        by_key[item.key].append(item)

    fragments = []
    for item in parsed:
        if len(by_key[item.key]) == 1:
            continue
        if item.days < min_days:
            fragments.append(item)

    return sorted(fragments, key=lambda item: (item.symbol, item.timeframe, item.start, item.end))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List short Backtesting cache parquet files; delete only with --apply.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help="Cache directory to scan (default: tools/Backtesting/cache).",
    )
    parser.add_argument(
        "--min-days",
        type=int,
        default=14,
        help="Delete candidates with end-start below this many days (default: 14).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete candidates. Omit for dry-run.",
    )
    args = parser.parse_args()

    cache_dir = args.cache_dir.resolve()
    if not cache_dir.exists():
        print(f"Cache directory not found: {cache_dir}")
        return 1

    fragments = find_cache_fragments(cache_dir, args.min_days)
    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"[{mode}] cache={cache_dir} min_days={args.min_days}")
    print(f"Candidates: {len(fragments)}")

    for item in fragments:
        rel = item.path.relative_to(cache_dir)
        print(f"  {rel} ({item.days} days)")
        if args.apply:
            item.path.unlink()

    if not args.apply:
        print("No files deleted. Re-run with --apply to delete candidates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
