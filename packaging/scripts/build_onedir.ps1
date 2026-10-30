param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $scriptDir "..\\..")).Path
$specPath = Join-Path $projectRoot "packaging\\pyinstaller\\tools_box_onedir.spec"
$outputExe = Join-Path $projectRoot "dist\\DataForgeStudio\\DataForgeStudio.exe"

# Interpreter: $env:PYTHON, then the repo venv, then python on PATH.
$venvPython = Join-Path $projectRoot ".venv\\Scripts\\python.exe"
if ($env:PYTHON) {
    $python = $env:PYTHON
}
elseif (Test-Path $venvPython) {
    $python = $venvPython
}
else {
    $python = "python"
}
Write-Host "[python] $python"

if ($Clean) {
    Write-Host "[clean] Remove build/dist"
    Remove-Item -Path (Join-Path $projectRoot "build") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path (Join-Path $projectRoot "dist") -Recurse -Force -ErrorAction SilentlyContinue
}

Push-Location $projectRoot
try {
    Write-Host "[build] PyInstaller onedir build"
    & $python -m PyInstaller $specPath --clean --noconfirm
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

# Self-check: the windowed exe has no stdout, so it writes self_check.txt to the log dir
# (dataforge.core.logs.default_log_dir()).
$logDir = (& $python -c "from dataforge.core.logs import default_log_dir; print(default_log_dir())").Trim()
if ($LASTEXITCODE -ne 0 -or -not $logDir) {
    throw "failed to resolve dataforge log directory"
}
$resultFile = Join-Path $logDir "self_check.txt"
Remove-Item -Path $resultFile -Force -ErrorAction SilentlyContinue

Write-Host "[check] $outputExe --self-check"
$proc = Start-Process -FilePath $outputExe -ArgumentList "--self-check" -Wait -PassThru
$exitCode = $proc.ExitCode

if (Test-Path $resultFile) {
    Write-Host "[check] $resultFile :"
    Get-Content -Path $resultFile -Encoding UTF8 | ForEach-Object { Write-Host "  $_" }
}
else {
    Write-Host "[check] result file not found: $resultFile"
}

if ($exitCode -ne 0) {
    throw "self-check failed with exit code $exitCode"
}

Write-Host "[ok] self-check passed"
