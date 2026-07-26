param(
    [string]$StartPath = (Get-Location).Path,
    [string]$VaultPath
)

$scriptPath = Join-Path $PSScriptRoot 'continuity.py'
$arguments = @($scriptPath, 'discover', '--start', $StartPath)
if ($VaultPath) {
    $arguments += @('--vault', $VaultPath)
}

& python @arguments
exit $LASTEXITCODE
