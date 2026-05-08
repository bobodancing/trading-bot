param(
    [ValidateSet("validate", "focused", "fast", "full")]
    [string]$Scope = "validate",

    [string[]]$Tests = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $RepoRoot
try {
    Write-Host "[agent_check] Config.validate"
    python -c "from trader.config import Config; Config.validate(); print('Config.validate PASS')"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    if ($Scope -eq "validate") {
        exit 0
    }

    if ($Scope -eq "focused") {
        if ($Tests.Count -eq 0) {
            throw "-Scope focused requires one or more -Tests paths or node ids"
        }
        $pytestArgs = @($Tests) + @("-q")
    } elseif ($Scope -eq "fast") {
        $pytestArgs = @("trader/tests", "extensions/Backtesting/tests", "-m", "not slow", "-q")
    } else {
        $pytestArgs = @("trader/tests", "extensions/Backtesting/tests", "-q")
    }

    Write-Host "[agent_check] python -m pytest $($pytestArgs -join ' ')"
    python -m pytest @pytestArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}
