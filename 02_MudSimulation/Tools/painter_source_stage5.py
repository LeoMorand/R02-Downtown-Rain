"""Read-only extraction of Painter version selection and runtime inputs."""
import unreal as u
import json
from pathlib import Path
OUT=Path('D:/aco/unreal/Stormfall/Verification/MudPainter')

def extract():
    OUT.mkdir(exist_ok=True)
    script=u.load_asset('/Game/FluidNinjaLive/Core/Modules/Ninja_Painter')
    versions=script.get_editor_property('version_data')
    rows=[]
    for v in versions:
        row={}
        for key in ['version','source']:
            value=v.get_editor_property(key)
            row[key]=value.get_path_name() if isinstance(value,u.Object) else str(value)
        rows.append(row)
    (OUT/'versions.json').write_text(json.dumps(rows,indent=2))
    return rows
