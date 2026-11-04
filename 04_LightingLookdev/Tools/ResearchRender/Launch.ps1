param([int]$Width=1600,[int]$Height=900,[switch]$Final,[switch]$Draft,[switch]$Study,[switch]$StudyFinal)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSCommandPath
$taskProject=(Resolve-Path (Join-Path $taskRoot '../../Stormfall.uproject')).Path
$taskEditor='D:/aco/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
if (!(Test-Path -LiteralPath $taskEditor)) { throw "Editor not found: $taskEditor" }
if (Test-Path -LiteralPath (Join-Path $taskRoot 'active.json')) {
    $taskActive=Get-Content -LiteralPath (Join-Path $taskRoot 'active.json') -Raw | ConvertFrom-Json
    if (Get-Process -Id $taskActive.pid -ErrorAction SilentlyContinue) { throw 'ResearchRender process is already running.' }
}
$taskScript=if ($StudyFinal) {'study_final.py'} elseif ($Study) {'study.py'} elseif ($Final -or $Draft) {'final.py'} else {'pipeline.py'}
$taskArgs=@(('"'+$taskProject+'"'),'/Engine/Maps/Entry','-ResearchRender','-EnablePlugins=MovieRenderPipeline','-RenderOffscreen','-windowed',"-ResX=$Width","-ResY=$Height",'-NoSound','-NoSplash','-unattended','-NoLoadStartupPackages',('-ExecutePythonScript="'+(Join-Path $taskRoot $taskScript)+'"'),('-abslog="'+(Join-Path $taskRoot 'editor.log')+'"'))
$taskArgs+='-DisablePlugins=UE_MCP_Bridge'
if ($Draft) {$taskArgs+='-RRDraft'}
$taskProcess=Start-Process -FilePath $taskEditor -ArgumentList $taskArgs -WindowStyle Hidden -PassThru
@{pid=$taskProcess.Id;started=(Get-Date -Format o)} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot 'active.json')
Write-Output "ResearchRender PID $($taskProcess.Id). Results: $taskRoot/runs"
