param(
    [Parameter(Mandatory = $true)]
    [string]$VaultPath
)

function Resolve-PackagePath {
    param([string]$BasePath)

    $directories = @($BasePath)
    $directories += Get-ChildItem -LiteralPath $BasePath -Directory -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty FullName

    foreach ($directory in $directories) {
        if ((Test-Path -LiteralPath (Join-Path $directory 'README.md') -PathType Leaf) -and
            (Test-Path -LiteralPath (Join-Path $directory 'CURRENT.md') -PathType Leaf) -and
            (Test-Path -LiteralPath (Join-Path $directory 'COLLABORATION_MEMORY.md') -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $directory).Path
        }
    }

    return $null
}

$package = Resolve-PackagePath -BasePath $VaultPath
if (-not $package) {
    Write-Error "Portable memory package was not found below: $VaultPath"
    exit 1
}

$required = @(
    'README.md',
    'CURRENT.md',
    'USER_PROFILE.md',
    'COLLABORATION_MEMORY.md',
    'DECISIONS.md',
    'LESSONS.md',
    'ENVIRONMENT.md',
    'MEMORY_INBOX.md',
    'MEMORY_CHANGELOG.md',
    'RESTORE.md',
    'BACKUP.md'
)

$missing = @()
foreach ($relative in $required) {
    $path = Join-Path $package $relative
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $missing += $relative
    }
}

if ($missing.Count -gt 0) {
    $missing | ForEach-Object { Write-Error "Missing required file: $_" }
    exit 1
}

$forbiddenNames = Get-ChildItem -LiteralPath $package -File -Recurse | Where-Object {
    $_.Name -match '(?i)(^\.env($|\.)|auth\.json|token|secret|credential|\.pem$|\.key$|\.pfx$|\.p12$|\.kdbx$|\.sqlite3?$)'
}

if ($forbiddenNames) {
    $forbiddenNames | ForEach-Object { Write-Error "Forbidden filename in memory package: $($_.FullName)" }
    exit 1
}

Write-Output "Portable memory package verified: $package"
Write-Output "Required files: $($required.Count)"
exit 0
