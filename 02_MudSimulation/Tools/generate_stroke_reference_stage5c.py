"""Extend the selected-graph emitter to the first tracked brush's full RGBA."""
from generate_brush_reference_stage5b import Emit,LEAVES,NODES,TOOLS,OUT
import json
LEAVES.update({
 'Module.VeloNoiseScale':('VelocityNoiseScale',1),'Module.VeloNoiseFreq':('VelocityNoiseFrequency',1),
 'Module.BrushVelocityNoise':('VelocityNoiseAmount',1),'Engine.Time':('SimTime',1),
 'Module.DensityNoiseScale':('DensityNoiseScale',1),'Module.DensityNoiseFreq':('DensityNoiseFrequency',1),
 'Module.DensityNoisePow':('DensityNoisePower',1),'Module.BrushDensityNoise':('DensityNoiseAmount',1),
 'Module.BrushNoiseInWorldSpace':('NoiseWorldSpace',1),'Module.WorldOffset':('WorldOffset',2),
 'Module.BrushVelocityPow':('VelocityPower',1),'Module.VeloMultZ':('VelocityZMultiplier',1),
 'Module.VeloMultXY':('VelocityXYMultiplier',1),'Module.KillBrushBelowThisVelocity':('SlowVelocityThreshold',1),
 'Module.BrushStrength':('BrushStrength',1),'Transient.SelectivelyKillDensity':('DensityEnable',1),
 'Module.InputFeedback':('InputFeedback',1)})

class Stroke(Emit):
    def input(self,n,pin):
        p=next(p for p in n['pins'] if p['direction']=='input' and p['name']==pin)
        if not p.get('linkedTo') and not p.get('defaultValue') and (n['name'],pin) in [('NiagaraNodeOp_12','B'),('NiagaraNodeOp_119','B')]:return '0.0',1
        return super().input(n,pin)
    def emit(self,name,pin):
        key=(name,pin)
        if key in self.cache:return self.cache[key]
        n=NODES[name];kind=n['class'];get=lambda p:self.input(n,p)
        if kind=='NiagaraNodeParameterMapGet' and pin in ['Local.Module.BrushDensityNoise','Local.Module.BrushVelocityNoise','Local.Module.NoiseUV']:
            node,port={'Local.Module.BrushDensityNoise':('NiagaraNodeOp_66','Result'),'Local.Module.BrushVelocityNoise':('NiagaraNodeOp_23','Result'),'Local.Module.NoiseUV':('NiagaraNodeSelect_3','Vector2f')}[pin]
            return self.emit(node,port)
        if kind=='NiagaraNodeParameterMapForIndex':return '0',1
        if kind=='NiagaraNodeFunctionCall' and name in ['NiagaraNodeFunctionCall_1','NiagaraNodeFunctionCall_9']:
            uv,_=get('UV');expr=f'Texture2DSampleLevel(NoiseTexture,NoiseTextureSampler,{uv},0)';dim=4
        elif kind=='NiagaraNodeOp' and n['title'] in ['Sign','Trunc']:
            a,dim=get('A');expr=n['title'].lower()+f'({a})'
        elif kind=='NiagaraNodeOp' and n['title']=='Greater Than Or Equal':
            a,_=get('A');b,_=get('B');expr=f'({a}>={b})';dim='bool'
        elif kind=='NiagaraNodeConvert':
            if name in ['NiagaraNodeConvert_19','NiagaraNodeConvert_112','NiagaraNodeConvert_0','NiagaraNodeConvert_11']:
                dims={'NiagaraNodeConvert_19':4,'NiagaraNodeConvert_112':3,'NiagaraNodeConvert_0':3,'NiagaraNodeConvert_11':3};dim=dims[name]
                inputs=[get(p['name'])[0] for p in n['pins'] if p['direction']=='input' and p['name']!='Add'];expr=f'float{dim}('+','.join(inputs)+')'
            elif name in ['NiagaraNodeConvert_7','NiagaraNodeConvert_18','NiagaraNodeConvert_5']:
                p=next(p['name'] for p in n['pins'] if p['direction']=='input' and p['name']!='Add');v,_=get(p)
                sw={'NiagaraNodeConvert_7':'rg','NiagaraNodeConvert_18':'r','NiagaraNodeConvert_5':'xy'}[name];dim=len(sw);expr=f'({v}).{sw}'
            else:return super().emit(name,pin)
        else:return super().emit(name,pin)
        variable='r'+str(len(self.lines));typ='bool' if dim=='bool' else 'float'+(str(dim) if dim>1 else '')
        self.lines.append(f'{typ} {variable}={expr}; // {name}.{pin}');self.cache[key]=(variable,dim)
        self.audit.append({'node':name,'pin':pin,'expression':expr,'type':typ})
        return variable,dim

def main():
    e=Stroke();out,_=e.emit('NiagaraNodeConvert_19','Out')
    code='\n'.join(e.lines)+f'\nreturn OutputAlpha>0.5 ? ({out}).aaa : ({out}).rgb;\n'
    (TOOLS/'Reference/StrokeReferenceStage5c.hlsl').write_text(code)
    (OUT/'stroke_reference_provenance.json').write_text(json.dumps({'scope':'First tracked brush only; sampled height is external','expressions':e.audit},indent=2))
    print({'expressions':len(e.lines)})
if __name__=='__main__':main()
