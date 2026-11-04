param([string]$EngineRoot='D:/aco/UE_5.8',[switch]$Iterative,[switch]$SkipBuild)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$reportRoot=Join-Path $projectRoot 'Verification/ShirtWetness/Production'
New-Item -ItemType Directory -Force -Path $reportRoot | Out-Null
$packageRoot=Join-Path $projectRoot 'Saved/Packages/ShirtWetness'
$cookRoot=Join-Path $projectRoot 'Saved/ShirtWetnessCook/Windows'
$autoSdk=Join-Path $projectRoot 'Intermediate/StormfallBuild/AutoSDK'
if(Test-Path -LiteralPath $autoSdk){$env:UE_SDKS_ROOT=$autoSdk}
$automationTool=Join-Path $EngineRoot 'Engine/Build/BatchFiles/RunUAT.bat'
$packageLog=Join-Path $reportRoot 'package.log'
$cookOptions=@()
if($Iterative){$cookOptions+='-iterate'}
$buildOptions=@('-build')
if($SkipBuild){$buildOptions=@('-skipbuild')}
& $automationTool BuildCookRun "-project=$projectRoot/Stormfall.uproject" -noP4 -platform=Win64 -clientconfig=Development @buildOptions -cook -stage -pak -skipiostore -archive "-archivedirectory=$packageRoot" "-CookOutputDir=$cookRoot" '-map=/Game/Stormfall/ShirtTrial/Wetness/L_ShirtWetness' '-AdditionalCookerOptions=-SkipZenStore -ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' -CookCultures=en -unattended -utf8output -NoCompileEditor -NoUBA -UBADisableRemote @cookOptions 2>&1 | Tee-Object -FilePath $packageLog
if($LASTEXITCODE -ne 0){throw "Shirt package failed. See $packageLog"}
Write-Output "SHIRT_PACKAGE_COMPLETE $packageRoot"

