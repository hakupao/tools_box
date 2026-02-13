param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $scriptDir "..\\..")).Path
$specPath = Join-Path $projectRoot "packaging\\pyinstaller\\tools_box_onedir.spec"
$outputExe = Join-Path $projectRoot "dist\\DataForgeStudio\\DataForgeStudio.exe"

if ($Clean) {
    Write-Host "[clean] Remove build/dist/temp_tkdnd"
    Remove-Item -Path (Join-Path $projectRoot "build") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path (Join-Path $projectRoot "dist") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path (Join-Path $projectRoot "temp_tkdnd") -Recurse -Force -ErrorAction SilentlyContinue
}

Push-Location $projectRoot
try {
    Write-Host "[build] PyInstaller onedir build"
    python -m PyInstaller $specPath --clean --noconfirm
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

if (-not (Test-Path $outputExe)) {
    throw "onedir build failed: missing $outputExe"
}

Write-Host "[ok] build output: $outputExe"
