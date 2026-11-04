param([string]$PackageRoot='D:/aco/unreal/Stormfall/Saved/Packages/ShirtWetness/Windows')
$ErrorActionPreference='Stop'
$executable=Join-Path $PackageRoot 'Stormfall.exe'
if(-not(Test-Path -LiteralPath $executable)){throw "Package not found: $executable"}
Start-Process -FilePath $executable -ArgumentList @('/Game/Stormfall/ShirtTrial/Wetness/L_ShirtWetness','-windowed','-ResX=1600','-ResY=900') -WorkingDirectory $PackageRoot -WindowStyle Hidden
