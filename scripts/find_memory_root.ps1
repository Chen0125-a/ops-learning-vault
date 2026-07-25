param(
    [string]$StartPath = (Get-Location).Path
)

function Find-PackageInDirectory {
    param([string]$BasePath)

    if (-not (Test-Path -LiteralPath $BasePath -PathType Container)) {
        return $null
    }

    $directories = @($BasePath)
    $directories += Get-ChildItem -LiteralPath $BasePath -Directory -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty FullName

    foreach ($directory in $directories) {
        $required = @('README.md', 'CURRENT.md', 'COLLABORATION_MEMORY.md', 'DECISIONS.md')
        $matches = $true
        foreach ($name in $required) {
            if (-not (Test-Path -LiteralPath (Join-Path $directory $name) -PathType Leaf)) {
                $matches = $false
                break
            }
        }
        if ($matches) {
            return (Resolve-Path -LiteralPath $directory).Path
        }
    }

    return $null
}

$candidates = [System.Collections.Generic.List[string]]::new()
if ($env:OBSIDIAN_MEMORY_VAULT) {
    $candidates.Add($env:OBSIDIAN_MEMORY_VAULT)
}

$current = [System.IO.DirectoryInfo]::new((Resolve-Path -LiteralPath $StartPath).Path)
while ($null -ne $current) {
    $candidates.Add($current.FullName)
    $current = $current.Parent
}

if (Test-Path -LiteralPath 'D:\') {
    $candidates.Add('D:\')
}

foreach ($candidate in $candidates | Select-Object -Unique) {
    $result = Find-PackageInDirectory -BasePath $candidate
    if ($result) {
        Write-Output $result
        exit 0
    }
}

Write-Error 'Portable memory package not found. Supply the vault path or set OBSIDIAN_MEMORY_VAULT.'
exit 1
