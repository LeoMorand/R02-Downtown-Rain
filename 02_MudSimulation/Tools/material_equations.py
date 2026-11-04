"""Emit ordered, pin-faithful equations after reroute/switch resolution.

This is an inspection notation, NOT compilable HLSL. Opaque engine/function nodes
retain their class, output index and serialized properties for later expansion.
"""
import json
from trace_material import Trace,refs,ROOT

class Equations:
    def __init__(self):self.t=Trace();self.rows={};self.visiting=set()
    def resolve(self,key,index=0):
        node=self.t.nodes[key];props=node['props'];kind=node['className']
        edges=self.t.edges(key,index)
        if kind in ['MaterialExpressionReroute','MaterialExpressionNamedRerouteDeclaration','MaterialExpressionNamedRerouteUsage'] and edges:
            return self.resolve(*edges[0][1])
        choice=self.t.choices.get(key)
        if choice:
            rr=refs(props.get(choice['branch']))
            if rr:return self.resolve(*rr[0])
        return key,index
    def emit(self,key,index=0):
        key,index=self.resolve(key,index);tag=key+'.'+str(index)
        if tag in self.rows:return tag
        assert tag not in self.visiting,tag
        self.visiting.add(tag)
        n=self.t.nodes[key];p=n['props'];kind=n['className'].removeprefix('MaterialExpression')
        edges=self.t.edges(key,index)
        inputs=[{'pin':pin,'value':self.emit(*ref)} for pin,ref in edges]
        data={k:v for k,v in p.items() if not refs(v) and k not in ['bCollapsed','Desc','FunctionOutputs','ReroutePins']}
        name=p.get('ParameterName')
        if kind=='ScalarParameter':data['effectiveValue']=self.t.scalar.get(name)
        elif kind=='VectorParameter':data['effectiveValue']=self.t.params['vector'].get(name)
        elif kind.startswith('Texture') and name:
            data['parentTexture']=self.t.params['texture'].get(name)
            if name in ['VelocityDensityBuffer','PressureDivergenceBuffer','PaintBuffer']:
                data['runtimeTexture']='Use captured MID binding, not parent default'
        self.rows[tag]={'expression':key,'outputIndex':index,'operation':kind,'inputs':inputs,'properties':data}
        self.visiting.remove(tag)
        return tag

def main():
    e=Equations();attrs=e.t.nodes['MaterialExpressionMakeMaterialAttributes_0']['props']
    outputs={slot:e.emit(*refs(attrs[slot])[0]) for slot in ['Normal','BaseColor','Roughness','Specular']}
    result={'scope':__doc__,'outputs':outputs,'equations':e.rows,'branchSelections':e.t.choices}
    (ROOT/'ordered_equations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Ordered material equations','','Inspection notation, not compilable HLSL. Texture-sample ports retain native output indices.','']
    for tag,row in e.rows.items():
        lines+=['## '+tag,'',row['operation'],'']
        lines+=['- '+x['pin']+' = '+x['value'] for x in row['inputs']]
        lines+=['- '+k+' = '+str(v) for k,v in row['properties'].items()]
        lines.append('')
    lines+=['# Outputs','']+[k+' = '+v for k,v in outputs.items()]
    (ROOT/'ordered_equations.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'outputs':outputs,'orderedExpressions':len(e.rows)},ensure_ascii=False))
if __name__=='__main__':main()
