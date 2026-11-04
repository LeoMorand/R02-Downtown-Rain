"""Resolve selected Niagara versions before emitting a pin-level source listing."""
import json
from pathlib import Path

ROOT=Path('Verification/MudTeardown')
RAW=ROOT/'Raw'
FILES={
 'Ninja_Pressure':('pressure_versions.json',RAW/'pressure_graph.json'),
 'Ninja_CompositeAndGradient':('Ninja_CompositeAndGradient_versions.json',Path('Verification/MudStudy/composite_graph.json')),
 'Ninja_Advection':('Ninja_Advection_versions.json',Path('Verification/MudStudy/advection_graph.json')),
 'CopyGridToRenderTarget':('CopyGridToRenderTarget_versions.json',Path('Verification/MudStudy/buffer_export_graph.json'))}
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def guid(g):return ''.join(f'{g[k]&0xffffffff:08X}' for k in 'ABCD')
def main():
    calls=read(RAW/'selected_module_versions.json')['rows']
    locks=[]
    out=ROOT/'SelectedGraphs';out.mkdir(exist_ok=True)
    for name,(versions,graphfile) in FILES.items():
        selected={r['props']['SelectedScriptVersion'] for r in calls if r['props']['FunctionScript'].split('.')[-1]==name}
        assert len(selected)==1,(name,selected)
        selected=selected.pop()
        version=next(v for v in read(RAW/versions)['value'] if guid(v['Version']['VersionGuid'])==selected)
        graph=next(g for g in read(graphfile)['graphs'] if g['path'].startswith(version['Source']+'.'))
        locks.append({'module':name,'guid':selected,'source':version['Source'],'version':str(version['Version']['MajorVersion'])+'.'+str(version['Version']['MinorVersion']),'nodes':graph['nodeCount']})
        (out/(name+'.json')).write_text(json.dumps(graph,ensure_ascii=False,indent=2),encoding='utf-8')
        ns={n['name']:n for n in graph['nodes']}
        missing=[]
        lines=['# '+name,'','Selected version: '+selected,'Source: '+version['Source'],'',
               'Pin-level listing; not executable HLSL. Function internals and compiler branch elimination are not expanded. Linked input defaults are omitted.','']
        for n in graph['nodes']:
            if n['class']=='EdGraphNode_Comment':continue
            lines += ['## '+n['name']+' — '+n['title'],'']
            for p in n['pins']:
                if p['direction']!='input' or p['name']=='Add':continue
                links=p.get('linkedTo',[])
                refs=[]
                for l in links:
                    if l['nodeName'] not in ns:missing.append(l)
                    refs.append(l['nodeName']+'.'+l['pinName'])
                lines.append('- '+p['name']+' ← '+(' | '.join(refs) if refs else 'default '+repr(p.get('defaultValue','[not serialized]'))))
            lines.append('')
        assert not missing,(name,missing)
        (out/(name+'.md')).write_text('\n'.join(lines),encoding='utf-8')
    (ROOT/'version_lock.json').write_text(json.dumps(locks,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(locks,ensure_ascii=False))
if __name__=='__main__':main()
