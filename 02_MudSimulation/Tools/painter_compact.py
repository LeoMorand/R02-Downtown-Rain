import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]/'Verification/MudPainter'
if len(sys.argv)>2 and sys.argv[1]=='--graph':
    selected_path=Path(sys.argv[2]);del sys.argv[1:3]
else:selected_path=root/'selected_graph.json'
nodes={n['name']:n for n in json.loads(selected_path.read_text())['nodes']}
def resolve(name,pin):
    n=nodes[name]
    if n['class']=='NiagaraNodeReroute':
        links=next(p for p in n['pins'] if p['direction']=='input').get('linkedTo',[])
        if links:return resolve(links[0]['nodeName'],links[0]['pinName'])
    return name,pin
seen=set()
def walk(name,pin=''):
    name,pin=resolve(name,pin)
    if name in seen:return
    seen.add(name);n=nodes[name]
    if n['class']=='NiagaraNodeParameterMapGet':return
    inputs=[]
    for p in n['pins']:
        if p['direction']!='input' or p['name']=='Add':continue
        links=p.get('linkedTo',[])
        values=[]
        for l in links:
            a,b=resolve(l['nodeName'],l['pinName']);walk(a,b);values.append(a+'.'+b)
        inputs.append(p['name']+'='+('|'.join(values) if values else repr(p.get('defaultValue','[missing]'))))
    print(name+' '+n['title']+'('+', '.join(inputs)+')')
for name in sys.argv[1:]:walk(name)
