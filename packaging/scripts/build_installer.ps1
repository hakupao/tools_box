param(
    [switch]$Clean,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $scriptDir "..\\..")).Path
$buildOnedirScript = Join-Path $scriptDir "build_onedir.ps1"
$installerScript = Join-Path $projectRoot "packaging\\installer\\tools_box.iss"
$sourceDir = Join-Path $projectRoot "dist\\DataForgeStudio"
$outputDir = Join-Path $projectRoot "dist_installer"
$versionFile = Join-Path $projectRoot "src\\version.py"
$appIcon = Join-Path $projectRoot "assets\\icons\\favicon.ico"

if (-not $SkipBuild) {
    $buildArgs = @()
    if ($Clean) {
        $buildArgs += "-Clean"
    }
    & $buildOnedirScript @buildArgs
}

if (-not (Test-Path (Join-Path $sourceDir "DataForgeStudio.exe"))) {
    throw "missing executable: $sourceDir\\DataForgeStudio.exe"
}

$qtPlugin = Get-ChildItem -Path $sourceDir -Recurse -Filter "qwindows.dll" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $qtPlugin) {
    throw "missing Qt platform plugin: qwindows.dll"
}

$tkdndDir = Get-ChildItem -Path $sourceDir -Recurse -Directory -Filter "tkdnd" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $tkdndDir) {
    throw "missing tkdnd payload directory"
}

if (-not (Test-Path $appIcon)) {
    throw "missing app icon: $appIcon"
}

$versionMatch = Select-String -Path $versionFile -Pattern 'VERSION\s*=\s*"([^"]+)"' | Select-Object -First 1
if (-not $versionMatch) {
    throw "failed to parse VERSION from $versionFile"
}
$version = $versionMatch.Matches[0].Groups[1].Value

$isccCommand = Get-Command "iscc.exe" -ErrorAction SilentlyContinue
if ($isccCommand) {
    $isccPath = $isccCommand.Source
}
else {
    $candidatePaths = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\\ISCC.exe")
    )
    $isccPath = $candidatePaths | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}

if (-not $isccPath) {
    throw "ISCC.exe not found. Install Inno Setup 6 or add iscc.exe to PATH."
}

New-Item -Path $outputDir -ItemType Directory -Force | Out-Null

Write-Host "[build] Inno Setup installer"
& $isccPath "/DMyAppVersion=$version" "/DSourceDir=$sourceDir" "/DOutputDir=$outputDir" "/DMyAppIcon=$appIcon" $installerScript
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compiler failed with exit code $LASTEXITCODE"
}

$installerExe = Get-ChildItem -Path $outputDir -Filter "DataForgeStudio-Setup-$version*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $installerExe) {
    throw "installer build failed under $outputDir"
}

Write-Host "[ok] installer output: $($installerExe.FullName)"
