import json
from pathlib import Path
root=Path('D:/aco/unreal/Stormfall/Verification/MudStudy')
data=json.loads((root/'niagara_core_graph.json').read_text(encoding='utf-8-sig'))
for g in data.get('graphs',[]):
    for n in g.get('nodes',[]):
        if 'Painter' in n.get('title',''):
            print(json.dumps(n,ensure_ascii=False)[:14000])
