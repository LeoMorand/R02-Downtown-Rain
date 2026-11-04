import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]/'Verification/MudPainter'
g=json.loads((root/'selected_graph.json').read_text());nodes={n['name']:n for n in g['nodes']}
seen=set()
def walk(name,pin='',depth=0):
    if (name,pin) in seen:return
    seen.add((name,pin));n=nodes[name]
    if n['class']=='NiagaraNodeParameterMapGet':
        print('  '*depth+name+'.'+pin);return
    print('  '*depth+name+'.'+pin+' '+n['title'])
    for p in n['pins']:
        if p['direction']!='input' or p['name']=='Add':continue
        links=p.get('linkedTo',[])
        if not links:print('  '*(depth+1)+p['name']+' = '+p.get('defaultValue','[not serialized]'))
        for l in links:
            print('  '*(depth+1)+p['name']+' <-')
            walk(l['nodeName'],l['pinName'],depth+2)
for name in sys.argv[1:]:walk(name)
