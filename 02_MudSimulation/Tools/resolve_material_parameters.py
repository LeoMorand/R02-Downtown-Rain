"""Resolve original parent MI parameters with Unreal's getters; no asset edits."""
import json
from pathlib import Path
import unreal as u

def run():
    root=Path('D:/aco/unreal/Stormfall')
    rows=json.loads((root/'Verification/MudTeardown/Raw/surface_expressions.json').read_text(encoding='utf-8-sig'))['rows']
    mi=u.load_asset('/Game/FluidNinjaLive/OutputMaterials/Surface_Various/MI_Mud1_WorldSpace')
    result={'parent':mi.get_path_name(),'static':{},'scalar':{},'texture':{},'vector':{},'errors':[]}
    for row in rows:
        name=row['props'].get('ParameterName')
        if not name:continue
        cls=row['className']
        kind='static' if cls in ['MaterialExpressionStaticSwitchParameter','MaterialExpressionStaticBoolParameter'] else 'scalar' if cls=='MaterialExpressionScalarParameter' else 'vector' if cls=='MaterialExpressionVectorParameter' else 'texture' if cls in ['MaterialExpressionTextureObjectParameter','MaterialExpressionTextureSampleParameter2D'] else None
        if not kind or name in result[kind]:continue
        try:
            fn=getattr(u.MaterialEditingLibrary,'get_material_instance_'+('static_switch' if kind=='static' else kind)+'_parameter_value')
            value=fn(mi,name)
            if kind=='texture':value=value.get_path_name() if value else None
            if kind=='vector':value=[value.r,value.g,value.b,value.a]
            result[kind][name]=value
        except Exception as e:result['errors'].append({'name':name,'error':str(e)})
    # Captured MID overrides, separate from inherited parent values.
    result['dynamicScalarOverrides']={'ForceLocalSpace':1.0,'FlowMapUVOffsetRandomize':0.0,'WorldOffsetX':0.0,'WorldOffsetY':0.0}
    out=root/'Verification/MudMaterial';out.mkdir(exist_ok=True)
    (out/'resolved_parameters.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return {k:len(result[k]) for k in ['static','scalar','texture','vector','errors']}
