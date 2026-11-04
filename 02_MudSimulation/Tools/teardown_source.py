"""Read source assets, export connection evidence to the analysis workspace."""
import json
from pathlib import Path
import unreal as u

OUT=Path('D:/aco/unreal/Stormfall/Verification/MudTeardown/Raw')

def probe():
    path='/Game/FluidNinjaLive/OutputMaterials/Base/MF_NinjaOutput_BaseFunction_SURFACE'
    function=u.load_asset(path)
    data=u.find_object(function,'MF_NinjaOutput_BaseFunction_SURFACEEditorOnlyData')
    result={'function':function.get_path_name(),'data':str(data)}
    try:
        collection=data.get_editor_property('ExpressionCollection')
        expressions=collection.get_editor_property('Expressions')
        result['count']=len(expressions)
        result['samples']=[]
        for node in expressions[:8]:
            if not node:continue
            row={'name':node.get_name(),'class':node.get_class().get_name()}
            for name in ['a','b','input','inputs','base_color','normal','output_index','input_name','material_function']:
                try:
                    v=node.get_editor_property(name)
                    if isinstance(v,u.Object):row[name]=v.get_path_name()
                    elif hasattr(v,'get_editor_property'):
                        try:
                            expr=v.get_editor_property('expression')
                            row[name]={'expression':expr.get_path_name() if expr else None,'output':v.get_editor_property('output_index')}
                        except Exception:row[name]=str(v)
                    else:row[name]=str(v)
                except Exception:pass
            result['samples'].append(row)
    except Exception as exc:result['error']=str(exc)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'material_probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
