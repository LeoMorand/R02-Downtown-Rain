"""Emit a small, typed expression slice directly from selected Painter 2.0 pins.

The FieldCapture sampling result is an explicit input, not an emulated DI.
"""
import json,re
from pathlib import Path
TOOLS=Path(__file__).resolve().parent
OUT=TOOLS.parents[1]/'Verification/MudPainter'
NODES={n['name']:n for n in json.loads((OUT/'selected_graph.json').read_text())['nodes']}
LEAVES={
 'Local.Module.UnitCoords':('UV',2), 'Local.Module.GridAspect':('Aspect',2),
 'Transient.Pos':('Position',2),'Transient.LastPos':('PreviousPosition',2),
 'Transient.Velo':('Velocity',3),'Transient.TrackedObjectSize':('ObjectSize',1),
 'Module.BrushVeloClamp':('VelocityClamp',1),'Module.NegativePuncture':('NegativePuncture',1),
 'Emitter.Age':('Age',1),'Module.BrushPuncture':('Puncture',1),
 'Module.WorldGridExtents':('WorldExtents',2),'Module.BrushSize':('BrushSize',1),
 'Local.Module.WorldOffsetDelta':('OffsetDelta',2),
 'Module.KillInterpolatorAboveThisVelocity':('InterpolationLimit',1),
 'Module.PosInterpolator':('Interpolate',1),'Module.BrushHardness':('Hardness',1),
 'Module.BrushHardnessScaledByObjSize':('HardnessBySize',1),
 'Module.FadeBrushByZPosMult':('ZFadeScale',1),'Transient.PosZ':('PositionZ',1),
 'Module.FadeBrushByZPos':('FadeByZ',1),'Local.Module.BrushDensityNoise':('DensityNoise',1)}

class Emit:
    def __init__(self):self.cache={};self.lines=[];self.audit=[]
    def input(self,n,pin):
        p=next(p for p in n['pins'] if p['direction']=='input' and p['name']==pin)
        links=p.get('linkedTo',[])
        if links:return self.emit(links[0]['nodeName'],links[0]['pinName'])
        v=p.get('defaultValue','')
        if not v:
            assert (n['name'],pin) in [('NiagaraNodeOp_7','Min'),('NiagaraNodeOp_152','B'),('NiagaraNodeOp_92','Min')],(n['name'],pin)
            self.audit.append({'node':n['name'],'pin':pin,'emptyDefault':0})
            v='0'
        if v in ['true','false']:return v,'bool'
        return repr(float(v)),1
    def emit(self,name,pin):
        key=(name,pin)
        if key in self.cache:return self.cache[key]
        n=NODES[name];kind=n['class'];title=n['title'];get=lambda p:self.input(n,p)
        if kind=='NiagaraNodeReroute':return get('InputPin')
        if kind=='NiagaraNodeParameterMapGet':
            result=LEAVES[pin];self.cache[key]=result;return result
        if kind=='NiagaraNodeFunctionCall' and name=='NiagaraNodeFunctionCall_31':return 'FieldHeight',1
        if kind=='NiagaraNodeOp':
            inputs=[get(p['name']) for p in n['pins'] if p['direction']=='input' and p['name']!='Add']
            args=[a[0] for a in inputs];dims=[a[1] for a in inputs];dim=max(d for d in dims if isinstance(d,int)) if any(isinstance(d,int) for d in dims) else 'bool'
            a=args[0];b=args[1] if len(args)>1 else None
            if title in ['Add','Subtract','Multiply','Divide']:expr='('+{'Add':'+','Subtract':'-','Multiply':'*','Divide':'/'}[title].join(args)+')'
            elif title=='Pow':expr=f'pow(max(0.0,{a}),{b})'
            elif title in ['Max','Min','Clamp','Abs','Normalize','Length','Dot']:expr=title.lower()+'('+','.join(args)+')';dim=1 if title in ['Dot','Length'] else dim
            elif title=='One Minus':expr=f'(1.0-{a})'
            elif title in ['Greater Than','Equal']:expr=f'({a}{">" if title=="Greater Than" else "=="}{b})';dim='bool'
            elif title in ['Logic OR','Logic AND']:expr='('+('||' if title=='Logic OR' else '&&').join(f'({a}!=0)' for a in args)+')';dim='bool'
            else:raise ValueError((name,title))
        elif kind=='NiagaraNodeSelect':
            pins=[p['name'] for p in n['pins'] if p['direction']=='input']
            t,dim=get(next(p for p in pins if 'if True' in p));f,_=get(next(p for p in pins if 'if False' in p));s,_=get('Selector');expr=f'(({s}!=0)?{t}:{f})'
        elif kind=='NiagaraNodeConvert':
            p=next(p['name'] for p in n['pins'] if p['direction']=='input' and p['name']!='Add');v,_=get(p)
            sw={'X':'x','Y':'y','Z':'z','XY':'xy'}[pin];expr=f'({v}).{sw}';dim=len(sw)
        elif kind=='NiagaraNodeFunctionCall':
            if title.startswith('Saturate Float'):v,dim=get('Value');expr=f'saturate({v})'
            elif name=='NiagaraNodeFunctionCall_53' and pin=='Length':v,_=get('V');expr=f'length({v})';dim=1
            else:raise ValueError((name,title,pin))
        elif kind=='NiagaraNodeCustomHlsl' and name=='NiagaraNodeCustomHlsl_2':
            a,_=get('Min');b,_=get('Max');c,_=get('Alpha');expr=f'smoothstep({a},{b},{c})';dim=1
        else:raise ValueError((name,title,pin))
        variable='r'+str(len(self.lines));typ='bool' if dim=='bool' else 'float'+(str(dim) if dim>1 else '')
        self.lines.append(f'{typ} {variable} = {expr}; // {name}.{pin}')
        self.cache[key]=(variable,dim);self.audit.append({'node':name,'pin':pin,'expression':expr,'type':typ})
        return variable,dim

def main():
    e=Emit();kernel,_=e.emit('NiagaraNodeSelect_4','NiagaraFloat');mask,_=e.emit('NiagaraNodeCustomHlsl_2','Value');radius,_=e.emit('NiagaraNodeOp_73','Result')
    code='\n'.join(e.lines)+f'\nreturn float3({kernel},{mask},{radius});\n'
    (TOOLS/'Reference/BrushReferenceStage5b.hlsl').write_text(code)
    (OUT/'brush_reference_provenance.json').write_text(json.dumps({'source':'Ninja_Painter 2.0 Source_10','externalInputs':LEAVES,'nodes':e.audit},indent=2))
    print(json.dumps({'expressions':len(e.lines),'output':['kernel','hardened_mask','radius'],'external_field_height_is_sample_result':True}))
if __name__=='__main__':main()
