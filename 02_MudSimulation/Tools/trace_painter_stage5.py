"""Select the actual Painter version and emit linked, pin-faithful evidence."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]/'Verification/MudPainter'
def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))
def main():
    selected=read('SelectedScriptVersion.json')['properties']['SelectedScriptVersion']
    versions=read('VersionData.json')['values']['VersionData']
    version=next(v for v in versions if ''.join(f'{v["Version"]["VersionGuid"][k]&0xffffffff:08X}' for k in 'ABCD')==selected)
    graph=next(g for g in read('painter_graph.json')['graphs'] if g['path'].startswith(version['Source']+'.'))
    lock={'guid':selected,'major':version['Version']['MajorVersion'],'minor':version['Version']['MinorVersion'],'source':version['Source'],'nodes':graph['nodeCount'],'changes':version['VersionChangeDescription']}
    (ROOT/'version_lock.json').write_text(json.dumps(lock,indent=2))
    (ROOT/'selected_graph.json').write_text(json.dumps(graph,indent=2))
    lines=['# Selected Ninja Painter 2.0','', 'Linked input defaults are not effective input values. Function internals require separate expansion.','']
    for n in graph['nodes']:
        lines+=['## '+n['name']+' — '+n['title'],'']
        for p in n['pins']:
            if p['direction']!='input' or p['name']=='Add':continue
            links=p.get('linkedTo',[])
            lines+=['- '+p['name']+' ← '+(' | '.join(l['nodeName']+'.'+l['pinName'] for l in links) if links else 'default '+repr(p.get('defaultValue','not serialized')))]
        lines+=['']
    (ROOT/'selected_graph.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(lock))
if __name__=='__main__':main()
