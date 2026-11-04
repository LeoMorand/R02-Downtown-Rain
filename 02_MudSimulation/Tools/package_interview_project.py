"""Copy a cache-free interview project into the delivery folder, preserving originals."""
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

WORK = Path('D:/aco/unreal/Stormfall')
SOURCE = Path('D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy')
OUT = WORK/'Deliverables/MudInterview_20261031'
TARGET = OUT/'UE_Project'
TARGET.mkdir(parents=True, exist_ok=True)
rows = []
def copy(source, relative):
    target = TARGET/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    assert source_hash == hashlib.sha256(target.read_bytes()).hexdigest(), relative
    rows.append(dict(path=relative.as_posix(), sha256=source_hash, bytes=target.stat().st_size))

for directory in ['Content','Config']:
    for source in (SOURCE/directory).rglob('*'):
        if source.is_file(): copy(source, source.relative_to(SOURCE))
for name in ['MudRuntime','MudShaderLab','MudAuthoring']:
    for source in (SOURCE/'Plugins'/name).rglob('*'):
        if not source.is_file(): continue
        rel = source.relative_to(SOURCE/'Plugins'/name)
        if rel.parts[0] in ['Source','Shaders','Resources'] or source.suffix == '.uplugin' or (rel.parts[0]=='Binaries' and source.suffix in ['.dll','.modules']):
            copy(source, source.relative_to(SOURCE))
project = json.loads((SOURCE/'FluidNinjaLive.uproject').read_text(encoding='utf-8-sig'))
for plugin in project.get('Plugins',[]):
    if plugin['Name']=='UE_MCP_Bridge': plugin['Enabled']=False
(TARGET/'FluidNinjaLive.uproject').write_text(json.dumps(project,indent=2)+'\n',encoding='utf-8')
config_path = TARGET/'Config/DefaultEngine.ini'
config = config_path.read_text(encoding='utf-8-sig')
for key in ['GameDefaultMap','EditorStartupMap']:
    config = re.sub(r'^'+key+r'=.*$',key+'=/Game/MudStudy/Professional/Phase18/L_Mud_VisibleTrails.L_Mud_VisibleTrails',config,flags=re.M)
config = re.sub(r'^DefaultGraphicsRHI=.*$','DefaultGraphicsRHI=DefaultGraphicsRHI_DX12',config,flags=re.M)
# This setting is unrelated to the demo and does not belong in a handoff copy.
config = re.sub(r'^SecurityToken=.*\n?','',config,flags=re.M)
config_path.write_text(config,encoding='utf-8')
for row in rows:
    if row['path']=='Config/DefaultEngine.ini':
        row['copiedSha256BeforeConfigAdjustments']=row['sha256']
        row['sha256']=hashlib.sha256(config_path.read_bytes()).hexdigest()
        row['bytes']=config_path.stat().st_size
rows.append(dict(path='FluidNinjaLive.uproject',sha256=hashlib.sha256((TARGET/'FluidNinjaLive.uproject').read_bytes()).hexdigest(),bytes=(TARGET/'FluidNinjaLive.uproject').stat().st_size))
(OUT/'project-file-manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(dict(project=str(TARGET/'FluidNinjaLive.uproject'),files=len(rows),totalMiB=round(sum(r['bytes'] for r in rows)/1024**2,1),originalProjectModified=False)))
