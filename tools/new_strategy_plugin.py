"""Dry-run scaffold helper for StrategyPlugin cartridges."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent


def module_name_from_id(plugin_id: str) -> str:
    module = re.sub(r"[^a-zA-Z0-9_]+", "_", plugin_id.strip()).strip("_").lower()
    if not module or not module[0].isalpha():
        raise ValueError("plugin id must produce a module name starting with a letter")
    return module


def class_name_from_id(plugin_id: str) -> str:
    parts = [part for part in re.split(r"[^a-zA-Z0-9]+|_", plugin_id) if part]
    if not parts:
        raise ValueError("plugin id must contain at least one alphanumeric token")
    return "".join(part[:1].upper() + part[1:] for part in parts) + "Strategy"


@dataclass(frozen=True)
class Scaffold:
    files: dict[Path, str]
    catalog_snippet: str


def build_scaffold(
    plugin_id: str,
    *,
    class_name: str | None = None,
    symbols: tuple[str, ...] = ("BTC/USDT",),
    timeframe: str = "4h",
    side: str = "LONG",
    warmup_bars: int = 100,
) -> Scaffold:
    module_name = module_name_from_id(plugin_id)
    class_name = class_name or class_name_from_id(plugin_id)
    side = side.upper()
    if side not in {"LONG", "SHORT"}:
        raise ValueError("side must be LONG or SHORT")

    symbol_literal = ", ".join(repr(symbol) for symbol in symbols)
    tags = "short_only" if side == "SHORT" else "long_only"
    plugin_path = Path("trader") / "strategies" / "plugins" / f"{module_name}.py"
    test_path = (
        Path("trader")
        / "tests"
        / "plugins"
        / "research"
        / f"test_{module_name}_strategy.py"
    )
    spec_path = Path("plans") / f"cartridge_spec_{module_name}.md"

    plugin_source = dedent(
        f'''
        """StrategyPlugin scaffold for {plugin_id}."""

        from __future__ import annotations

        from trader.strategies import SignalIntent, StrategyContext, StrategyPlugin, StrategyRiskProfile


        class {class_name}(StrategyPlugin):
            id = "{plugin_id}"
            version = "0.1.0"
            tags = {{"research", "{tags}"}}
            required_timeframes = {{"{timeframe}": {warmup_bars}}}
            required_indicators = set()
            params_schema = {{"timeframe": "str"}}
            allowed_symbols = {{{symbol_literal}}}
            max_concurrent_positions = 1
            risk_profile = StrategyRiskProfile.fixed_risk_pct()

            def generate_candidates(self, context: StrategyContext) -> list[SignalIntent]:
                # Add locked-spec entry logic here. Do not size or execute orders.
                return []
        '''
    ).lstrip()

    test_source = dedent(
        f'''
        from trader.strategies import StrategyRegistry
        from trader.strategies.plugins.{module_name} import {class_name}


        def test_{module_name}_contract_smoke():
            plugin = {class_name}(params={{"timeframe": "{timeframe}"}})

            assert plugin.id == "{plugin_id}"
            assert plugin.required_timeframes == {{"{timeframe}": {warmup_bars}}}
            assert plugin.allowed_symbols == {{{symbol_literal}}}


        def test_{module_name}_registry_loads_from_catalog_copy():
            registry = StrategyRegistry.from_config(
                {{
                    "{plugin_id}": {{
                        "enabled": True,
                        "module": "trader.strategies.plugins.{module_name}",
                        "class": "{class_name}",
                        "params": {{"timeframe": "{timeframe}"}},
                    }}
                }},
                ["{plugin_id}"],
            )

            assert isinstance(registry.require("{plugin_id}"), {class_name})
        '''
    ).lstrip()

    spec_source = dedent(
        f'''
        # Cartridge Spec: {plugin_id}

        ## Locked Spec

        - id: {plugin_id}
        - scope: {", ".join(symbols)}, {timeframe}, {side}
        - indicators: TBD
        - entry gate: TBD
        - stop hint: TBD
        - regime: target_regime = ANY
        - off-regime entry suppression: not required for ANY

        ## Regime Declaration

        - target_regime: ANY
        - rationale: TBD

        ## Out of Scope

        - runtime promotion
        - scanner default changes
        - direct sizing or execution
        '''
    ).lstrip()

    catalog_snippet = dedent(
        f'''
        "{plugin_id}": {{
            "enabled": False,
            "module": "trader.strategies.plugins.{module_name}",
            "class": "{class_name}",
            "params": {{"timeframe": "{timeframe}"}},
        }},
        '''
    ).strip()

    return Scaffold(
        files={
            plugin_path: plugin_source,
            test_path: test_source,
            spec_path: spec_source,
        },
        catalog_snippet=catalog_snippet,
    )


def write_scaffold(scaffold: Scaffold, *, repo_root: Path) -> None:
    for rel_path, content in scaffold.files.items():
        path = repo_root / rel_path
        if path.exists():
            raise FileExistsError(f"refusing to overwrite existing file: {rel_path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a StrategyPlugin scaffold")
    parser.add_argument("--id", required=True, dest="plugin_id", help="Stable strategy plugin id")
    parser.add_argument("--class-name", default=None)
    parser.add_argument("--symbols", nargs="+", default=["BTC/USDT"])
    parser.add_argument("--timeframe", default="4h")
    parser.add_argument("--side", choices=["LONG", "SHORT"], default="LONG")
    parser.add_argument("--warmup-bars", type=int, default=100)
    parser.add_argument("--write", action="store_true", help="Write scaffold files; default is dry-run")
    args = parser.parse_args(argv)

    scaffold = build_scaffold(
        args.plugin_id,
        class_name=args.class_name,
        symbols=tuple(args.symbols),
        timeframe=args.timeframe,
        side=args.side,
        warmup_bars=args.warmup_bars,
    )

    print("Planned files:")
    for rel_path in scaffold.files:
        print(f"- {rel_path}")
    print("\nCatalog snippet:")
    print(scaffold.catalog_snippet)

    if args.write:
        write_scaffold(scaffold, repo_root=Path.cwd())
        print("\nWrote scaffold files.")
    else:
        print("\nDry-run only. Re-run with --write to create files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
