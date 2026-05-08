Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $RepoRoot
try {
    $code = @'
from trader.config import Config
from trader.strategies.plugins._catalog import get_strategy_catalog

Config.validate()
catalog = get_strategy_catalog(Config.ENABLED_STRATEGIES)

print("Config.validate PASS")
print(f"STRATEGY_RUNTIME_ENABLED={Config.STRATEGY_RUNTIME_ENABLED}")
print(f"STRATEGY_RUNTIME_SIDE_FILTER={Config.STRATEGY_RUNTIME_SIDE_FILTER}")
print(f"ENABLED_STRATEGIES={Config.ENABLED_STRATEGIES}")
print(f"SYMBOLS={Config.SYMBOLS}")
print(f"USE_SCANNER_SYMBOLS={Config.USE_SCANNER_SYMBOLS}")
print(f"SCANNER_UNIVERSE_ENABLED={Config.SCANNER_UNIVERSE_ENABLED}")
print(f"REGIME_ARBITER_ENABLED={Config.REGIME_ARBITER_ENABLED}")
print(f"REGIME_ROUTER_ENABLED={Config.REGIME_ROUTER_ENABLED}")
print(f"STRATEGY_ROUTER_POLICY={Config.STRATEGY_ROUTER_POLICY}")
print(f"BTC_TREND_FILTER_ENABLED={Config.BTC_TREND_FILTER_ENABLED}")
print(f"BTC_TREND_FILTER_RUNTIME_MODE={Config.BTC_TREND_FILTER_RUNTIME_MODE}")
print(f"BTC_COUNTER_TREND_MULT={Config.BTC_COUNTER_TREND_MULT}")
print(f"RISK_PER_TRADE={Config.RISK_PER_TRADE}")
print(f"MAX_TOTAL_RISK={Config.MAX_TOTAL_RISK}")
print("catalog:")
for strategy_id in Config.ENABLED_STRATEGIES:
    entry = catalog.get(strategy_id, {})
    print(f"- {strategy_id}: enabled={bool(entry.get('enabled'))} module={entry.get('module')} class={entry.get('class')}")
'@
    $code | python -
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}
