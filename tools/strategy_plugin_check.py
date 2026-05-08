"""Validate StrategyPlugin catalog entries without changing runtime defaults."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from trader.config import Config
from trader.strategies import StrategyRegistry
from trader.strategies.plugins._catalog import (
    STRATEGY_CATALOG,
    get_strategy_catalog,
    get_strategy_classification,
)


@dataclass
class PluginCheckResult:
    strategy_id: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    plugin_class: str | None = None
    plugin_version: str | None = None
    classification: str | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def check_strategy(strategy_id: str, *, repo_root: Path | None = None) -> PluginCheckResult:
    """Check one strategy id against the catalog and registry contract."""
    repo_root = Path(repo_root or _repo_root())
    result = PluginCheckResult(strategy_id=strategy_id)

    if strategy_id not in STRATEGY_CATALOG:
        result.errors.append(f"missing catalog entry: {strategy_id}")
        return result

    result.classification = get_strategy_classification(strategy_id)
    if result.classification is None:
        result.errors.append(f"missing plugin classification: {strategy_id}")
        return result

    catalog = get_strategy_catalog([strategy_id])
    try:
        registry = StrategyRegistry.from_config(catalog, [strategy_id])
        plugin = registry.require(strategy_id)
    except Exception as exc:
        result.errors.append(f"registry load failed: {type(exc).__name__}: {exc}")
        return result

    result.plugin_class = type(plugin).__name__
    result.plugin_version = getattr(plugin, "version", None)

    if not getattr(plugin, "version", ""):
        result.errors.append("plugin version is empty")
    if getattr(plugin, "id", None) != strategy_id:
        result.errors.append(f"plugin id mismatch: {getattr(plugin, 'id', None)}")
    if not isinstance(getattr(plugin, "required_timeframes", None), dict):
        result.errors.append("required_timeframes must be a dict")
    if isinstance(getattr(plugin, "required_indicators", None), (str, bytes)):
        result.errors.append("required_indicators must be a set/list, not a string")

    if not _has_focused_test(repo_root, strategy_id):
        result.warnings.append(f"no focused test coverage found for {strategy_id}")

    spec_path = repo_root / "plans" / f"cartridge_spec_{strategy_id}.md"
    if not spec_path.exists():
        result.warnings.append(f"missing locked spec file: {spec_path.relative_to(repo_root)}")

    return result


def _has_focused_test(repo_root: Path, strategy_id: str) -> bool:
    tests_dir = repo_root / "trader" / "tests"
    if list(tests_dir.glob(f"test_{strategy_id}*.py")):
        return True
    for path in tests_dir.glob("test_*.py"):
        try:
            if strategy_id in path.read_text(encoding="utf-8"):
                return True
        except OSError:
            continue
    return False


def check_many(strategy_ids: Iterable[str], *, repo_root: Path | None = None) -> list[PluginCheckResult]:
    return [check_strategy(str(strategy_id), repo_root=repo_root) for strategy_id in strategy_ids]


def _print_result(result: PluginCheckResult) -> None:
    status = "PASS" if result.ok else "FAIL"
    details = []
    if result.classification:
        details.append(result.classification)
    if result.plugin_class:
        details.append(result.plugin_class)
    if result.plugin_version:
        details.append(f"v{result.plugin_version}")
    suffix = f" ({', '.join(details)})" if details else ""
    print(f"[{status}] {result.strategy_id}{suffix}")
    for warning in result.warnings:
        print(f"  WARN: {warning}")
    for error in result.errors:
        print(f"  ERROR: {error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate StrategyPlugin catalog entries")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--strategy-id", action="append", help="Strategy id to validate; repeatable")
    group.add_argument("--runtime-enabled", action="store_true", help="Validate Config.ENABLED_STRATEGIES")
    group.add_argument("--all-catalog", action="store_true", help="Validate every catalog entry")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    args = parser.parse_args(argv)

    Config.validate()
    if args.runtime_enabled:
        strategy_ids = list(Config.ENABLED_STRATEGIES)
    elif args.all_catalog:
        strategy_ids = sorted(STRATEGY_CATALOG)
    else:
        strategy_ids = list(args.strategy_id or [])

    results = check_many(strategy_ids)
    for result in results:
        _print_result(result)

    has_errors = any(result.errors for result in results)
    has_warnings = any(result.warnings for result in results)
    return 1 if has_errors or (args.strict and has_warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
