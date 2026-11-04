"""Offline, read-only evidence index. Run from the Stormfall workspace root."""
import json
from pathlib import Path
from collections import Counter

ROOT = Path('Verification/MudTeardown')
RAW = ROOT / 'Raw'
PAIRS = {'tick':'component_tick','owner':'component_owner','targets':'component_targets',
         'parameters':'component_parameters','materials':'component_materials',
         'material_update':'component_material_update','interactions':'component_interactions'}

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def main():
    result = {'scope':'Static source evidence; not a runtime equivalence test', 'graphs':{}, 'writes':[]}
    for key, name in PAIRS.items():
        graph = read(RAW / (name+'.json'))
        links = read(RAW / (key+'_connections.json'))
        nodes = {n['id']:n for n in graph['nodes']}
        edges = links['connections']
        unresolved = [e for e in edges if e['fromNodeId'] not in nodes or e['toNodeId'] not in nodes]
        result['graphs'][key] = {'nodes':len(nodes),'edges':len(edges),
            'unresolvedEndpoints':len(unresolved),'hasMore':links.get('hasMore',False)}
        for node in nodes.values():
            title = node.get('title','')
            if not any(s in title for s in ['Set Niagara','Niagara Set','Set Texture Parameter','Set Float Parameter','Set Vector Parameter','Make Vector4','Make Vector 4']):
                continue
            inputs = []
            for pin in node.get('pins',[]):
                if pin.get('direction') != 'Input' or pin.get('type') == 'exec': continue
                sources = [{'node':e['fromNodeTitle'],'pin':e['fromPin'],'id':e['fromNodeId']} for e in edges if e['toNodeId']==node['id'] and e['toPin']==pin['name']]
                inputs.append({'pin':pin['name'],'sources':sources,
                    'default':pin.get('defaultObject',pin.get('defaultValue','')) if not sources else None})
            result['writes'].append({'graph':key,'node':title,'id':node['id'],'inputs':inputs})
    rows = read(RAW / 'surface_expressions.json')['rows']
    result['materialExpressionClasses'] = dict(Counter(r['className'] for r in rows))
    result['materialExpressionCount'] = len(rows)
    (ROOT/'evidence_index.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    hlsl_dir = ROOT/'HLSL'
    hlsl_dir.mkdir(exist_ok=True)
    exported=[]
    for source in Path('Verification/MudStudy').glob('*custom_hlsl.json'):
        data=read(source)
        for i,node in enumerate(data.get('customHlslNodes',[])):
            code=node.get('hlsl','')
            if not code: continue
            target=hlsl_dir/(source.stem.replace('_custom_hlsl','')+'_'+str(i)+'.hlsl')
            target.write_text('// Extracted verbatim; graph wiring and switches determine use.\n// '+str(node.get('functionName',''))+'\n'+code,encoding='utf-8')
            exported.append(str(target))
    result['extractedHlsl']=exported
    (ROOT/'evidence_index.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'graphs':result['graphs'],'materialExpressions':len(rows),'writes':len(result['writes']),'hlslFiles':len(exported)},ensure_ascii=False))

if __name__ == '__main__': main()
