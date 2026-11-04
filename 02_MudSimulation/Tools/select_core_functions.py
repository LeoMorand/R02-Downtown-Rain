import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]/'Verification/MudPainter'
def main():
    calls=json.loads((ROOT/'core_calls.json').read_text())['rows']
    versions={r['assetPath']:r['props']['VersionData'] for r in json.loads((ROOT/'core_function_versions.json').read_text())['rows']}
    selected=[]
    for path,text in versions.items():
        name=path.split('.')[-1];guids={r['props'].get('SelectedScriptVersion') for r in calls if r['props'].get('FunctionScript')==path}
        for guid in guids:
            tail=text.split('VersionGuid='+guid,1)[1]
            source=re.search(r'Source="[^\']*\'([^\']+)\'"',tail).group(1)
            graphs=json.loads((ROOT/'Functions'/f'{name}.json').read_text())['graphs']
            g=next(g for g in graphs if g['path'].startswith(source+'.'))
            out=ROOT/'SelectedFunctions';out.mkdir(exist_ok=True)
            (out/f'{name}.json').write_text(json.dumps(g,indent=2))
            lines=[]
            for n in g['nodes']:
                if n['class']=='EdGraphNode_Comment':continue
                lines+=['## '+n['name']+' '+n['title']]
                for p in n['pins']:
                    if p['direction']!='input' or p['name']=='Add':continue
                    links=p.get('linkedTo',[])
                    lines+=[p['name']+' <- '+(' | '.join(l['nodeName']+'.'+l['pinName'] for l in links) if links else repr(p.get('defaultValue','')))]
                lines+=['']
            (out/f'{name}.md').write_text('\n'.join(lines),encoding='utf-8')
            selected.append({'function':name,'guid':guid,'source':source,'nodes':len(g['nodes'])})
    (ROOT/'core_function_locks.json').write_text(json.dumps(selected,indent=2));print(json.dumps(selected,indent=2))
if __name__=='__main__':main()
