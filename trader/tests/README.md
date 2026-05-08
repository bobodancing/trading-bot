# Trader Test Ownership

`trader/tests` is grouped by the runtime surface each test protects.

- `runtime/`: StrategyRuntime kernel, BTC trend diagnostics, scanner handoff,
  runtime observability, and runtime config contracts.
- `plugins/promoted/`: focused tests for currently promoted runtime plugins.
- `plugins/research/`: focused tests for default-off research, superseded, or
  retire-candidate plugins.
- `scanner/`: scanner universe and advisory signal behavior.
- `market/`: indicators, regime, arbiter, and structure helpers.
- `infrastructure/`: data provider, notifier, Telegram command handler,
  sync, and performance database behavior.
- `persistence/`: position persistence, post-fill stop handling, and risk guard
  compatibility surfaces.
- `tooling/`: local Codex/plugin scaffolding and validation tools.

Keep shared fixtures in root `conftest.py` unless a fixture is only useful for
one ownership group.
