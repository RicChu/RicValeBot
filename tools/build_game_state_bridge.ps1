[CmdletBinding()]
param(
    [string]$GameDir = "C:\Program Files (x86)\Steam\steamapps\common\SpiritVale"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$project = Join-Path $repoRoot "integrations\SpiritValeGameStateBridge\SpiritValeGameStateBridge.csproj"
$localDotnet = Join-Path $repoRoot ".dotnet\dotnet.exe"

$requiredPaths = @(
    (Join-Path $GameDir "SpiritVale.exe"),
    (Join-Path $GameDir "BepInEx\core\BepInEx.Core.dll"),
    (Join-Path $GameDir "BepInEx\interop\Assembly-CSharp.dll")
)
foreach ($requiredPath in $requiredPaths) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required SpiritVale file was not found: $requiredPath"
    }
}

if (Test-Path -LiteralPath $localDotnet) {
    $dotnet = $localDotnet
} else {
    $dotnetCommand = Get-Command dotnet -ErrorAction SilentlyContinue
    if ($null -eq $dotnetCommand) {
        throw "A .NET SDK is required. Install it locally into .dotnet or install .NET SDK 8."
    }
    $sdkList = & $dotnetCommand.Source --list-sdks
    if ($LASTEXITCODE -ne 0 -or -not $sdkList) {
        throw "The dotnet host exists but no SDK is installed. Install .NET SDK 8 or create .dotnet with Microsoft's dotnet-install.ps1."
    }
    $dotnet = $dotnetCommand.Source
}

$arguments = @(
    "build",
    $project,
    "--configuration", "Release",
    "-p:GameDir=$GameDir"
)
& $dotnet @arguments | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) {
    throw "SpiritValeGameStateBridge build failed with exit code $LASTEXITCODE."
}

$dll = Join-Path $repoRoot "integrations\SpiritValeGameStateBridge\bin\Release\net6.0\SpiritValeGameStateBridge.dll"
if (-not (Test-Path -LiteralPath $dll)) {
    throw "Build completed without the expected DLL: $dll"
}
Write-Output $dll
