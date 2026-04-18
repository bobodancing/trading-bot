"""Compare bot_config.json with trader.config.Config class defaults."""

from __future__ import annotations

import argparse
import importlib.util
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON_PATH = PROJECT_ROOT / "bot_config.json"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "trader" / "config.py"

CRITICAL_KEYS = frozenset({
    "ARBITER_NEUTRAL_EXIT_THRESHOLD",
    "ARBITER_NEUTRAL_MIN_BARS",
    "ARBITER_NEUTRAL_THRESHOLD",
    "ENABLE_GRID_TRADING",
    "MACRO_OVERLAY_ENABLED",
    "MACRO_STALLED_SIZE_MULT",
    "MACRO_WEEKLY_EMA_SPREAD_THRESHOLD",
    "REGIME_ARBITER_ENABLED",
    "REGIME_ROUTER_ENABLED",
    "REGIME_ROUTER_TRACE_ENABLED",
    "STRATEGY_RUNTIME_ENABLED",
    "ENABLED_STRATEGIES",
    "STRATEGY_CATALOG",
    "STRATEGY_ROUTER_POLICY",
    "DEFAULT_STRATEGY_RISK_PROFILE",
})

CATEGORIES = (
    "MISSING_IN_JSON",
    "MISSING_IN_CONFIG",
    "VALUE_MISMATCH",
    "TYPE_MISMATCH",
)


@dataclass(frozen=True)
class ParityIssue:
    category: str
    key: str
    json_value: Any = None
    config_value: Any = None
    json_type: str = ""
    config_type: str = ""

    @property
    def critical(self) -> bool:
        return self.key in CRITICAL_KEYS


@dataclass(frozen=True)
class ParityResult:
    issues: tuple[ParityIssue, ...]

    @property
    def critical_issues(self) -> tuple[ParityIssue, ...]:
        return tuple(issue for issue in self.issues if issue.critical)

    def by_category(self, *, critical_only: bool = False) -> dict[str, list[ParityIssue]]:
        issues: Iterable[ParityIssue] = self.critical_issues if critical_only else self.issues
        grouped = {category: [] for category in CATEGORIES}
        for issue in issues:
            grouped[issue.category].append(issue)
        return grouped


def _canonical_key(json_key: str) -> str:
    return json_key.upper()


def _type_name(value: Any) -> str:
    return type(value).__name__


def _load_json_attrs(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return {_canonical_key(key): value for key, value in raw.items()}


def _load_config_class(path: Path):
    spec = importlib.util.spec_from_file_location("_config_parity_target", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load Config from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "Config"):
        raise RuntimeError(f"{path} does not define Config")
    return module.Config


def _load_config_attrs(path: Path) -> dict[str, Any]:
    config_cls = _load_config_class(path)
    attrs = {}
    for key, value in vars(config_cls).items():
        if not key.isupper() or key.startswith("_"):
            continue
        if isinstance(value, (classmethod, staticmethod)):
            continue
        if callable(value):
            continue
        attrs[key] = value
    return attrs


def _jsonish(value: Any) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        text = repr(value)
    if len(text) > 180:
        return text[:177] + "..."
    return text


def _escape_cell(value: Any) -> str:
    return _jsonish(value).replace("|", "\\|").replace("\n", " ")


def _values_equal_loose(left: Any, right: Any) -> bool:
    if left == right:
        return True
    if isinstance(left, str) and isinstance(right, bool):
        return left.lower() == str(right).lower()
    if isinstance(right, str) and isinstance(left, bool):
        return right.lower() == str(left).lower()
    return False


def compare_config_parity(
    json_path: Path = DEFAULT_JSON_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> ParityResult:
    json_attrs = _load_json_attrs(Path(json_path))
    config_attrs = _load_config_attrs(Path(config_path))

    issues: list[ParityIssue] = []
    for key in sorted(config_attrs):
        if key not in json_attrs:
            issues.append(ParityIssue(
                category="MISSING_IN_JSON",
                key=key,
                config_value=config_attrs[key],
                config_type=_type_name(config_attrs[key]),
            ))

    for key in sorted(json_attrs):
        if key not in config_attrs:
            issues.append(ParityIssue(
                category="MISSING_IN_CONFIG",
                key=key,
                json_value=json_attrs[key],
                json_type=_type_name(json_attrs[key]),
            ))
            continue

        json_value = json_attrs[key]
        config_value = config_attrs[key]
        json_type = _type_name(json_value)
        config_type = _type_name(config_value)
        if type(json_value) is not type(config_value) and _values_equal_loose(json_value, config_value):
            issues.append(ParityIssue(
                category="TYPE_MISMATCH",
                key=key,
                json_value=json_value,
                config_value=config_value,
                json_type=json_type,
                config_type=config_type,
            ))
        elif json_value != config_value:
            issues.append(ParityIssue(
                category="VALUE_MISMATCH",
                key=key,
                json_value=json_value,
                config_value=config_value,
                json_type=json_type,
                config_type=config_type,
            ))

    return ParityResult(tuple(sorted(issues, key=lambda item: (item.category, item.key))))


def render_markdown_report(
    result: ParityResult,
    *,
    json_path: Path = DEFAULT_JSON_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    critical_only: bool = False,
) -> str:
    grouped = result.by_category(critical_only=critical_only)
    rendered_issues = [issue for issues in grouped.values() for issue in issues]
    critical_count = len([issue for issue in rendered_issues if issue.critical])

    lines = [
        "# Config Parity Report",
        "",
        f"- Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"- JSON: `{Path(json_path)}`",
        f"- Config: `{Path(config_path)}`",
        f"- Mode: `{'critical-only' if critical_only else 'full'}`",
        "",
        "## Summary",
        "",
        "| category | count | critical |",
        "|---|---:|---:|",
    ]
    for category in CATEGORIES:
        issues = grouped[category]
        critical = len([issue for issue in issues if issue.critical])
        lines.append(f"| `{category}` | {len(issues)} | {critical} |")
    lines.extend([
        f"| `TOTAL` | {len(rendered_issues)} | {critical_count} |",
        "",
        "## Critical Keys",
        "",
        ", ".join(f"`{key}`" for key in sorted(CRITICAL_KEYS)),
        "",
    ])

    critical_issues = [issue for issue in rendered_issues if issue.critical]
    if critical_issues:
        lines.extend([
            "## Critical Findings",
            "",
            "| category | key | json | config | json_type | config_type |",
            "|---|---|---|---|---|---|",
        ])
        for issue in critical_issues:
            lines.append(_issue_row(issue))
        lines.append("")
    else:
        lines.extend(["## Critical Findings", "", "None.", ""])

    for category in CATEGORIES:
        lines.extend([f"## {category}", ""])
        issues = grouped[category]
        if not issues:
            lines.extend(["None.", ""])
            continue
        lines.extend([
            "| key | critical | json | config | json_type | config_type |",
            "|---|---:|---|---|---|---|",
        ])
        for issue in issues:
            lines.append(_issue_row(issue, include_category=False))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _issue_row(issue: ParityIssue, *, include_category: bool = True) -> str:
    cells = [
        f"`{issue.category}`",
        f"`{issue.key}`",
        _escape_cell(issue.json_value),
        _escape_cell(issue.config_value),
        f"`{issue.json_type}`" if issue.json_type else "",
        f"`{issue.config_type}`" if issue.config_type else "",
    ]
    if not include_category:
        cells = [
            f"`{issue.key}`",
            "yes" if issue.critical else "no",
            _escape_cell(issue.json_value),
            _escape_cell(issue.config_value),
            f"`{issue.json_type}`" if issue.json_type else "",
            f"`{issue.config_type}`" if issue.config_type else "",
        ]
    return "| " + " | ".join(cells) + " |"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare bot_config.json with Config class defaults.")
    parser.add_argument("--json", dest="json_path", type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument("--config", dest="config_path", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--out", dest="out_path", type=Path)
    parser.add_argument("--critical-only", action="store_true")
    args = parser.parse_args()

    result = compare_config_parity(args.json_path, args.config_path)
    report = render_markdown_report(
        result,
        json_path=args.json_path,
        config_path=args.config_path,
        critical_only=args.critical_only,
    )

    if args.out_path:
        args.out_path.parent.mkdir(parents=True, exist_ok=True)
        args.out_path.write_text(report, encoding="utf-8")
        print(f"Wrote {args.out_path}")
    else:
        print(report, end="")

    if result.critical_issues:
        print(f"Critical config parity issues: {len(result.critical_issues)}")
        return 2
    if result.issues:
        print(f"Non-critical config parity issues: {len(result.issues)}")
        return 0
    print("Config parity OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
