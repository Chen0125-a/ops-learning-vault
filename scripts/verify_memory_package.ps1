param(
    [Parameter(Mandatory = $true)]
    [string]$VaultPath,

    [string[]]$SkillRoot = @()
)

$scriptPath = Join-Path $PSScriptRoot 'continuity.py'
$arguments = @($scriptPath, 'verify', '--vault', $VaultPath)
foreach ($root in $SkillRoot) {
    $arguments += @('--skill-root', $root)
}

& python @arguments
exit $LASTEXITCODE
