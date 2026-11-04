"""Conservative output-specific material dependency slicing from exported evidence.

Resolves composite ports, named reroutes, effective MI static switches and known
uniform Lerp branches. Function calls are opaque: all connected inputs retained.
This is not the engine compiler or a GPU instruction count.
"""
import json,re
from pathlib import Path
WORKSPACE=Path(__file__).resolve().parents[2]
ROOT=WORKSPACE/'Verification/MudMaterial'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def refs(value):
    if not isinstance(value,str):return []
    result=[]
    for m in re.finditer(r'Expression="[^"\n]*:(MaterialExpression\w+)\x27"([^()]*)',value):
        ix=re.search(r'OutputIndex=(-?\d+)',m[2])
        result.append((m[1],int(ix[1]) if ix else 0))
    return result
def short(v):return str(v).split(':')[-1]

class Trace:
    def __init__(self):
        self.nodes={}
        for p in [WORKSPACE/'Verification/MudTeardown/Raw/surface_expressions.json',WORKSPACE/'Verification/MudTeardown/Raw/surface_structural_properties.json',ROOT/'expression_supplement.json']:
            for n in read(p)['rows']:
                key=n['assetName']
                if key not in self.nodes:self.nodes[key]=n
                else:self.nodes[key]['props'].update(n['props'])
        self.params=read(ROOT/'resolved_parameters.json')
        self.scalar=self.params['scalar']|self.params['dynamicScalarOverrides']
        self.choices={}
        self.unresolved=[]
    def evaluate(self,key,index=0,seen=None):
        seen=set() if seen is None else seen.copy()
        if key in seen:return None
        seen.add(key)
        n=self.nodes[key];p=n['props'];c=n['className']
        def v(field,fallback=None):
            rr=refs(p.get(field));return self.evaluate(*rr[0],seen) if len(rr)==1 else fallback
        if c=='MaterialExpressionScalarParameter':return self.scalar.get(p.get('ParameterName'),p.get('DefaultValue'))
        if c in ['MaterialExpressionStaticBoolParameter','MaterialExpressionStaticSwitchParameter']:
            val=self.params['static'].get(p.get('ParameterName'),p.get('DefaultValue'))
            return val if c.endswith('BoolParameter') else v('A' if val else 'B')
        if c=='MaterialExpressionConstant':return p.get('R')
        if c in ['MaterialExpressionReroute','MaterialExpressionNamedRerouteDeclaration']:return v('Input')
        if c=='MaterialExpressionNamedRerouteUsage':return self.evaluate(short(p['Declaration']),index,seen)
        if c=='MaterialExpressionOneMinus':
            a=v('Input');return 1-a if a is not None else None
        if c in ['MaterialExpressionAdd','MaterialExpressionSubtract','MaterialExpressionMultiply','MaterialExpressionDivide']:
            a,b=v('A',p.get('ConstA')),v('B',p.get('ConstB'))
            if a is None or b is None:return None
            if c.endswith('Add'):return a+b
            if c.endswith('Subtract'):return a-b
            if c.endswith('Multiply'):return a*b
            return a/b if b else None
        return None
    def edges(self,key,index=0):
        n=self.nodes[key];p=n['props'];c=n['className']
        if c=='MaterialExpressionComposite':
            pin=short(p['OutputExpressions']);ports=refs(self.nodes[pin]['props']['ReroutePins'])
            if index>=len(ports):self.unresolved.append([key,index,'composite port']);return []
            return [('output '+str(index),ports[index])]
        if c=='MaterialExpressionPinBase':
            ports=refs(p.get('ReroutePins',''))
            if index>=len(ports):self.unresolved.append([key,index,'pinbase port']);return []
            return [('port '+str(index),ports[index])]
        if c=='MaterialExpressionNamedRerouteUsage':return [('Declaration',(short(p['Declaration']),0))]
        fields=list(p)
        if c=='MaterialExpressionStaticSwitchParameter':
            value=self.params['static'].get(p.get('ParameterName'),p.get('DefaultValue'))
            fields=['A' if value else 'B'];self.choices[key]={'parameter':p.get('ParameterName'),'value':value,'branch':fields[0]}
        if c=='MaterialExpressionStaticSwitch':
            rr=refs(p.get('Value'));value=self.evaluate(*rr[0]) if rr else p.get('DefaultValue')
            if value is not None:fields=['Value','A' if value else 'B'];self.choices[key]={'value':value,'branch':fields[-1]}
        if c=='MaterialExpressionLinearInterpolate':
            rr=refs(p.get('Alpha'));value=self.evaluate(*rr[0]) if rr else p.get('ConstAlpha')
            if value in [0,1]:fields=['Alpha','B' if value==1 else 'A'];self.choices[key]={'alpha':value,'branch':fields[-1]}
        if c=='MaterialExpressionIf':
            ar,br=refs(p.get('A')),refs(p.get('B'))
            a=self.evaluate(*ar[0]) if ar else None
            b=self.evaluate(*br[0]) if br else p.get('ConstB')
            # Avoid assuming an unexported equality tolerance near the threshold.
            if a is not None and b is not None and (abs(a-b)>0.001 or a==b):
                branch='AEqualsB' if a==b else 'AGreaterThanB' if a>b else 'ALessThanB'
                fields=['A','B',branch];self.choices[key]={'a':a,'b':b,'branch':branch}
        return [(field,ref) for field in fields if field not in ['FunctionOutputs','ReroutePins'] for ref in refs(p[field])]
    def walk(self,roots):
        seen=set();pending=list(roots)
        while pending:
            key,index=pending.pop()
            if (key,index) in seen:continue
            if key not in self.nodes:self.unresolved.append([key,index,'missing node']);continue
            seen.add((key,index));pending.extend(r for _,r in self.edges(key,index))
        return seen
    def summarize(self,seen):
        names={k for k,i in seen};ns=[self.nodes[k] for k in sorted(names)]
        return {'expressionCount':len(names),'nodes':sorted(names),
            'parameters':sorted({n['props']['ParameterName'] for n in ns if 'ParameterName' in n['props']}),
            'functions':[{'node':n['assetName'],'function':n['props']['MaterialFunction']} for n in ns if 'MaterialFunction' in n['props']],
            'composites':[{'node':n['assetName'],'label':n['props'].get('SubgraphName')} for n in ns if n['className']=='MaterialExpressionComposite']}
def main():
    t=Trace();attrs=t.nodes['MaterialExpressionMakeMaterialAttributes_0']['props']
    result={'scope':__doc__,'outputs':{}}
    selected={}
    for slot in ['BaseColor','Normal','Roughness','Specular','WorldPositionOffset','PixelDepthOffset']:
        seen=t.walk(refs(attrs[slot]));result['outputs'][slot]=t.summarize(seen)
        for ref in seen:selected[ref]=t.edges(*ref)
    result['branchSelections']=t.choices;result['unresolved']=t.unresolved
    (ROOT/'active_paths.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Material dependency listing','', 'Effective WorldSpace Parent + captured MID scalar overrides. Opaque function calls retain all inputs. No shader instruction-count claim.','']
    for (key,index),edges in sorted(selected.items()):
        n=t.nodes[key];p=n['props'];lines+=['## '+key+' output '+str(index),'',n['className']+' '+str(p.get('ParameterName',p.get('SubgraphName',p.get('Name','')))),'']
        lines += ['- '+label+' ← '+ref[0]+' output '+str(ref[1]) for label,ref in edges]
        if key in t.choices:lines+=['- selection: '+json.dumps(t.choices[key],ensure_ascii=False)]
        lines.append('')
    (ROOT/'active_dependencies.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'outputs':{k:{'expressions':v['expressionCount'],'functions':len(v['functions'])} for k,v in result['outputs'].items()},'unresolved':len(t.unresolved),'selections':len(t.choices)},ensure_ascii=False))
if __name__=='__main__':main()
