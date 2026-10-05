# PowerShell build script for Windows standalone binary distribution
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

Set-Location $RepoRoot

Write-Host "=== [1/3] Generating Application Icons ===" -ForegroundColor Cyan
uv run python packaging/generate_icons.py

Write-Host "=== [2/3] Building Windows Binary via PyInstaller ===" -ForegroundColor Cyan
uv run pyinstaller packaging/hikvision-downloader.spec --clean --noconfirm

Write-Host "=== [3/3] Creating Release ZIP Archive ===" -ForegroundColor Cyan
$DistFolder = Join-Path $RepoRoot "dist\hikvision-downloader"
$ZipOutput = Join-Path $RepoRoot "dist\HikVision-Downloader-Windows-x64.zip"

if (Test-Path $ZipOutput) {
    Remove-Item $ZipOutput -Force
}

if (-not (Test-Path $DistFolder)) {
    Write-Error "Error: Dist folder '$DistFolder' was not found."
    exit 1
}

Compress-Archive -Path "$DistFolder\*" -DestinationPath $ZipOutput -CompressionLevel Optimal

Write-Host "=== Windows Build Completed Successfully ===" -ForegroundColor Green
Write-Host "Artifact: $ZipOutput"
Get-Item $ZipOutput | Format-List Length, LastWriteTime
