[CmdletBinding()]
param(
    [string]$GameDir = "C:\Program Files (x86)\Steam\steamapps\common\SpiritVale"
)

$ErrorActionPreference = "Stop"
$buildScript = Join-Path $PSScriptRoot "build_game_state_bridge.ps1"
$dll = & $buildScript -GameDir $GameDir
if (-not (Test-Path -LiteralPath $dll)) {
    throw "Build script did not return a valid plugin DLL."
}

$pluginDir = Join-Path $GameDir "BepInEx\plugins\SpiritValeGameStateBridge"
New-Item -ItemType Directory -Force -Path $pluginDir | Out-Null
$destination = Join-Path $pluginDir "SpiritValeGameStateBridge.dll"
Copy-Item -LiteralPath $dll -Destination $destination -Force
Write-Output "Installed read-only bridge: $destination"
