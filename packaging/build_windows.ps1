# PowerShell build script for Windows standalone binary distribution
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

Set-Location $RepoRoot

Write-Host "=== [1/3] Generating Application Icons ===" -ForegroundColor Cyan
uv run python packaging/generate_icons.py

Write-Host "=== [2/3] Building Windows Standalone Executable via PyInstaller ===" -ForegroundColor Cyan
uv run pyinstaller packaging/hikvision-downloader.spec --clean --noconfirm

Write-Host "=== [3/3] Verifying Release Executable ===" -ForegroundColor Cyan
$ExeOutput = Join-Path $RepoRoot "dist\HikVision-Downloader-Windows-x64.exe"

if (-not (Test-Path $ExeOutput)) {
    $AltExe = Join-Path $RepoRoot "dist\hikvision-downloader.exe"
    if (Test-Path $AltExe) {
        Move-Item $AltExe $ExeOutput -Force
    } else {
        Write-Error "Error: Windows executable '$ExeOutput' was not found."
        exit 1
    }
}

Write-Host "=== Windows Build Completed Successfully ===" -ForegroundColor Green
Write-Host "Artifact: $ExeOutput"
Get-Item $ExeOutput | Format-List Length, LastWriteTime
