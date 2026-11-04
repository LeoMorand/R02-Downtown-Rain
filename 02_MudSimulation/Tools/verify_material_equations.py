"""Compare hand-derived formulas with an interpreter of captured material nodes.

Function/texture outputs are supplied test inputs. This verifies the mixing
algebra only; it does not validate texture sampling, GPU shaders or full visuals.
"""
import json,math,random,re
from material_equations import Equations
from trace_material import refs,ROOT

def op(fn,*values):
    size=max((len(v) for v in values if isinstance(v,tuple)),default=0)
    if not size:return fn(*values)
    expanded=[v if isinstance(v,tuple) else (v,)*size for v in values]
    assert all(len(v)==size for v in expanded),expanded
    return tuple(fn(*v) for v in zip(*expanded))

class Interpreter:
    def __init__(self,e,boundary):self.e=e;self.boundary=boundary;self.cache={}
    def value(self,key,index=0):
        key,index=self.e.resolve(key,index);tag=(key,index)
        if tag in self.boundary:return self.boundary[tag]
        if tag in self.cache:return self.cache[tag]
        n=self.e.t.nodes[key];p=n['props'];c=n['className'].removeprefix('MaterialExpression')
        def field(name,fallback=None):
            rr=refs(p.get(name))
            if not rr:return fallback
            v=self.value(*rr[0]);raw=p[name]
            if isinstance(v,tuple) and re.search(r'\bMask=1\b',raw):
                v=tuple(v[i] for i,k in enumerate('RGBA') if re.search(r'Mask'+k+r'=1\b',raw))
                if len(v)==1:v=v[0]
            return v
        if c=='ScalarParameter':v=self.e.t.scalar[p['ParameterName']]
        elif c=='VectorParameter':v=tuple(self.e.t.params['vector'][p['ParameterName']])
        elif c=='Constant':v=p['R']
        elif c.startswith('Constant') and 'Vector' in c:
            v=tuple(float(x) for x in re.findall(r'[RGBA]=([-\d.eE+]+)',p.get('Constant','')))
        elif c in ['Add','Subtract','Multiply','Divide','Min','Max']:
            a,b=field('A',p.get('ConstA')),field('B',p.get('ConstB'))
            fn={'Add':lambda a,b:a+b,'Subtract':lambda a,b:a-b,'Multiply':lambda a,b:a*b,
                'Divide':lambda a,b:a/b,'Min':min,'Max':max}[c]
            v=op(fn,a,b)
        elif c=='Power':v=op(lambda a,b:a**b,field('Base'),field('Exponent',p.get('ConstExponent')))
        elif c=='OneMinus':v=op(lambda a:1-a,field('Input'))
        elif c=='Abs':v=op(abs,field('Input'))
        elif c=='Saturate':v=op(lambda a:min(max(a,0),1),field('Input'))
        elif c=='ComponentMask':
            a=field('Input');v=tuple(a[i] for i,k in enumerate('RGBA') if p.get(k,False))
            if len(v)==1:v=v[0]
        elif c=='LinearInterpolate':v=op(lambda a,b,t:a+(b-a)*t,field('A',p.get('ConstA')),field('B',p.get('ConstB')),field('Alpha',p.get('ConstAlpha')))
        elif c=='TwoSidedSign':v=1.0 # Tested front-facing baseline only.
        else:raise ValueError((key,index,c))
        self.cache[tag]=v;return v

def main():
    e=Equations();rng=random.Random(20261025);maximum=0.0
    attrs=e.t.nodes['MaterialExpressionMakeMaterialAttributes_0']['props']
    for case in range(1000):
        d,t1,t2=rng.random(),rng.random(),rng.random()
        flow=tuple(rng.random() for _ in range(3));distance=rng.uniform(1000,2500)
        ns=tuple(rng.uniform(-2,2) for _ in range(3))
        n1=tuple(rng.uniform(-2,2) for _ in range(3));n2=tuple(rng.uniform(-2,2) for _ in range(3))
        b={('MaterialExpressionTextureSample_1',3):d,('MaterialExpressionTextureSample_0',1):t1,
           ('MaterialExpressionTextureSample_2',1):t2,('MaterialExpressionMaterialFunctionCall_0',0):flow,
           ('MaterialExpressionMaterialFunctionCall_9',0):ns,('MaterialExpressionMaterialFunctionCall_15',0):n1,
           ('MaterialExpressionMaterialFunctionCall_16',0):n2,('MaterialExpressionDistance_3',0):distance,
           # This mask is algebraically 1 because TileMapMaskedBySimVelocity=0;
           # retain a varying source to check the Max node eliminates it.
           ('MaterialExpressionAbs_9',0):rng.uniform(0,3)}
        inter=Interpreter(e,b)
        fade=min(max(2*(distance-1500)/500,0),1)
        tile=t1-0.1*t2
        density=min(d*(1+tile*fade),1)
        f=tuple(0.5*(1-v)**2*density**0.1 for v in flow)
        alpha=f[0]+0.25*density**10
        c1=e.t.params['vector']['Color 1'][:3];c2=e.t.params['vector']['Color 2'][:3]
        expected={'Normal':tuple(a+fade*d*d*(b-0.1*c) for a,b,c in zip(ns,n1,n2)),
            'BaseColor':tuple(a+(b-a)*alpha for a,b in zip(c2,c1)),
            'Roughness':min(max(0.1*d,0.1+0.1*(1-tile*fade)+min(2*f[0],1)),1),
            'Specular':0.2}
        for slot,target in expected.items():
            actual=inter.value(*refs(attrs[slot])[0])
            if isinstance(actual,tuple):
                # Material BaseColor consumes RGB; serialized color parameters carry A too.
                errors=[abs(a-b) for a,b in zip(actual,target)]
            else:errors=[abs(actual-target)]
            maximum=max(maximum,*errors)
            assert max(errors)<1e-6,(case,slot,actual,target)
    result={'cases':1000,'seed':20261025,'max_absolute_error':maximum,
        'scope':__doc__,'front_facing_only':True,'tested_density_and_tiles_range':[0,1],
        'function_outputs':'supplied independently; internals not covered'}
    (ROOT/'mixing_formula_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
if __name__=='__main__':main()
