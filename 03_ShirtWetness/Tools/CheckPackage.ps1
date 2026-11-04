param([string]$PackageRoot='D:/aco/unreal/Stormfall/Saved/Packages/ShirtWetness/Windows',[switch]$Benchmark,[switch]$CaptureCsv)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$reportRoot=Join-Path $projectRoot 'Verification/ShirtWetness/Production'
$gameExecutable=Join-Path $PackageRoot 'Stormfall/Binaries/Win64/Stormfall.exe'
if(-not(Test-Path -LiteralPath $gameExecutable)){throw "Missing packaged game: $gameExecutable"}
$reportStem=if($CaptureCsv){'packaged-csv-diagnostic'}elseif($Benchmark){'packaged-benchmark'}else{'packaged-runtime'}
$runtimeLog=Join-Path $reportRoot "$reportStem.log"
$arguments=@('/Game/Stormfall/ShirtTrial/Wetness/L_ShirtWetness','-windowed','-ResX=1280','-ResY=720','-unattended','-nosound','-nosplash','-seconds=15','-ExecCmds=viewactor CameraActor_1',"-abslog=$runtimeLog","-UserDir=$projectRoot/Saved/ShirtWetnessPackageUser")
if($Benchmark){$arguments+=@('-benchmark','-fps=60')}
if($CaptureCsv){$arguments+=@('-csvCaptureFrames=600','-csvGpuStats')}
$start=[Diagnostics.ProcessStartInfo]::new()
$start.FileName=$gameExecutable;$start.WorkingDirectory=$PackageRoot
$start.UseShellExecute=$false;$start.CreateNoWindow=$true;$start.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
$start.RedirectStandardOutput=$true;$start.RedirectStandardError=$true
foreach($argument in $arguments){$start.ArgumentList.Add($argument)}
$gameProcess=[Diagnostics.Process]::new();$gameProcess.StartInfo=$start
[void]$gameProcess.Start()
$stdout=$gameProcess.StandardOutput.ReadToEndAsync();$stderr=$gameProcess.StandardError.ReadToEndAsync()
$watch=[Diagnostics.Stopwatch]::StartNew()
while(-not $gameProcess.WaitForExit(1000)){
    if($watch.Elapsed.TotalSeconds -gt 180){$gameProcess.Kill($true);throw 'Packaged verification timed out; only this test process was stopped.'}
}
[IO.File]::WriteAllText((Join-Path $reportRoot "$reportStem-stdout.log"),$stdout.GetAwaiter().GetResult())
[IO.File]::WriteAllText((Join-Path $reportRoot "$reportStem-stderr.log"),$stderr.GetAwaiter().GetResult())
$logText=Get-Content -LiteralPath $runtimeLog -Raw
$mapLoaded=$logText -match 'Bringing.*L_ShirtWetness.*up for play'
$fatal=$logText -match 'Fatal error:|Assertion failed:|Unhandled Exception:|GPU Crash'
$passed=$gameProcess.ExitCode -eq 0 -and $mapLoaded -and -not $fatal
$result=[ordered]@{passed=$passed;exit_code=$gameProcess.ExitCode;map_loaded=$mapLoaded;fatal_detected=$fatal;wall_seconds=$watch.Elapsed.TotalSeconds;resolution='1280x720';benchmark=[bool]$Benchmark;csv_capture=[bool]$CaptureCsv;requested_runtime_seconds=15;executable=$gameExecutable;arguments=$arguments;note='Development build, one bounded smoke test. Benchmark uses fixed 60Hz simulation, not a stable-FPS certification. CSV capture is a separate diagnostic with a known shutdown failure; exit-code validation remains strict.'}
$result | ConvertTo-Json -Depth 4 | Out-File -LiteralPath (Join-Path $reportRoot "$reportStem.json") -Encoding utf8
if(-not $passed){throw "Packaged verification failed. See $runtimeLog"}
Write-Output 'SHIRT_PACKAGED_RUNTIME_PASSED'
$result | ConvertTo-Json -Depth 4
