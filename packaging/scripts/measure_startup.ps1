param(
    [string]$BaselineExe = ".\\dist\\DataForgeStudio.exe",
    [string]$CandidateExe = ".\\dist\\DataForgeStudio\\DataForgeStudio.exe",
    [int]$Runs = 5,
    [int]$Warmup = 1,
    [int]$TimeoutSec = 30
)

$ErrorActionPreference = "Stop"

function Resolve-ExecutablePath {
    param([string]$PathValue)
    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return $null
    }
    try {
        return (Resolve-Path $PathValue -ErrorAction Stop).Path
    }
    catch {
        return $null
    }
}

function Measure-Launch {
    param(
        [string]$ExePath,
        [int]$TimeoutSec
    )

    $proc = Start-Process -FilePath $ExePath -WorkingDirectory (Split-Path $ExePath -Parent) -PassThru
    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    try {
        [void]$proc.WaitForInputIdle($TimeoutSec * 1000)
    }
    catch {
    }

    $ready = $false
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSec) {
        $proc.Refresh()
        if ($proc.MainWindowHandle -ne 0) {
            $ready = $true
            break
        }
        Start-Sleep -Milliseconds 100
    }

    $sw.Stop()
    $elapsedMs = [math]::Round($sw.Elapsed.TotalMilliseconds, 0)

    try {
        if (-not $proc.HasExited) {
            [void]$proc.CloseMainWindow()
            if (-not $proc.WaitForExit(4000)) {
                $proc.Kill()
                $proc.WaitForExit()
            }
        }
    }
    catch {
    }

    return [pscustomobject]@{
        Ready = $ready
        ElapsedMs = $elapsedMs
    }
}

function Get-Median {
    param([int[]]$Values)
    $sorted = @($Values | Sort-Object)
    if (-not $sorted -or $sorted.Count -eq 0) {
        return $null
    }

    if ($sorted.Count % 2 -eq 1) {
        $index = [int][math]::Floor($sorted.Count / 2)
        return $sorted[$index]
    }
    $upper = [int]($sorted.Count / 2)
    $lower = $upper - 1
    return [math]::Round(($sorted[$lower] + $sorted[$upper]) / 2, 0)
}

function Invoke-Benchmark {
    param(
        [string]$Label,
        [string]$ExePath
    )

    Write-Host "[bench] $Label -> $ExePath"
    for ($i = 1; $i -le $Warmup; $i++) {
        [void](Measure-Launch -ExePath $ExePath -TimeoutSec $TimeoutSec)
    }

    $results = @()
    for ($i = 1; $i -le $Runs; $i++) {
        $row = Measure-Launch -ExePath $ExePath -TimeoutSec $TimeoutSec
        $results += [pscustomobject]@{
            Label = $Label
            Run = $i
            Ready = $row.Ready
            ElapsedMs = $row.ElapsedMs
        }
        Write-Host "  run $i/$Runs : $($row.ElapsedMs) ms (ready=$($row.Ready))"
    }
    return $results
}

$baselinePath = Resolve-ExecutablePath -PathValue $BaselineExe
$candidatePath = Resolve-ExecutablePath -PathValue $CandidateExe

if (-not $baselinePath -and -not $candidatePath) {
    throw "No executable found. Baseline=`"$BaselineExe`", Candidate=`"$CandidateExe`"."
}

$allRows = @()
if ($baselinePath) {
    $allRows += Invoke-Benchmark -Label "baseline" -ExePath $baselinePath
}
if ($candidatePath) {
    $allRows += Invoke-Benchmark -Label "candidate" -ExePath $candidatePath
}

Write-Host ""
Write-Host "Raw results:"
$allRows | Format-Table -AutoSize

$summary = @()
$groups = $allRows | Group-Object Label
foreach ($group in $groups) {
    $msValues = $group.Group | ForEach-Object { [int]$_.ElapsedMs }
    $readyCount = ($group.Group | Where-Object { $_.Ready }).Count
    $summary += [pscustomobject]@{
        Label = $group.Name
        Runs = $group.Count
        ReadyRuns = $readyCount
        AvgMs = [math]::Round((($msValues | Measure-Object -Average).Average), 0)
        MinMs = ($msValues | Measure-Object -Minimum).Minimum
        MaxMs = ($msValues | Measure-Object -Maximum).Maximum
        MedianMs = Get-Median -Values $msValues
    }
}

Write-Host ""
Write-Host "Summary:"
$summary | Format-Table -AutoSize

if ($summary.Count -eq 2) {
    $base = $summary | Where-Object { $_.Label -eq "baseline" } | Select-Object -First 1
    $cand = $summary | Where-Object { $_.Label -eq "candidate" } | Select-Object -First 1
    if ($base -and $cand -and $base.AvgMs -gt 0) {
        $delta = [math]::Round((($cand.AvgMs - $base.AvgMs) / $base.AvgMs) * 100, 1)
        Write-Host ""
        Write-Host "Delta(candidate vs baseline): $delta %"
    }
}
