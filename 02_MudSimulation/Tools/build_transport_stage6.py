"""Signed RT implementations of source transport/differential/pressure kernels."""
import sys,json,math,re
from pathlib import Path
import unreal as u
TOOLS=Path(__file__).parent
if str(TOOLS) not in sys.path:sys.path.insert(0,str(TOOLS))
from build_display_stage1 import Graph,SNAPSHOT
from build_pom_stage2 import custom
from build_painter_stage5 import world,target as create_target,draw
OUT=TOOLS.parents[1]/'Verification/MudSolver';PACKAGE='/Game/MudStudy/Rebuild/Materials/'

def target(w):
    rt=create_target(w)
    rt.set_editor_property('address_x',u.TextureAddress.TA_CLAMP)
    rt.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
    return rt

def base(g,scalars):
    g.mat.set_editor_property('allow_negative_emissive_color',True)
    g.node('UV','TextureCoordinate')
    g.node('SizeParam','VectorParameter',parameter_name='CellSize',default_value=u.LinearColor(1/32,1/32,0,0))
    g.node('CellSize','ComponentMask',r=True,g=True,b=False,a=False);g.link('SizeParam','CellSize')
    g.node('Field','TextureObjectParameter',parameter_name='Field',texture=u.load_asset(SNAPSHOT),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    for name,value in scalars.items():g.node(name,'ScalarParameter',parameter_name=name,default_value=value)

def build():
    world();OUT.mkdir(exist_ok=True);rows=[]
    definitions=[('M_Solver_Advection','TransportStage6.hlsl',{'SimSpeed':1,'Feedback':.9,'AreaClamp':1}),
        ('M_Solver_Differential','DifferentialStage6.hlsl',{'Mode':0,'SimSpeed':1})]
    for name,file,scalars in definitions:
        g=Graph(name);base(g,scalars);names=['Field','UV','CellSize']+list(scalars)
        custom(g,'Kernel',(TOOLS/'Reference'/file).read_text(),names)
        for n in names:g.link(n,'Kernel',n)
        g.output('Kernel','EMISSIVE_COLOR');rows.append(g.finish())
    g=Graph('M_Solver_Pressure');scalars={'SimSpeed':1,'KIInput':2,'OffsetInput':0,'StepInput':0,'ClampInput':1,'PressureFeedback':1,'DivergenceFeedback':1};base(g,scalars)
    g.node('Pressure','TextureObjectParameter',parameter_name='Pressure',texture=u.load_asset(SNAPSHOT),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    names=['Pressure','UV','CellSize']+list(scalars)
    custom(g,'Kernel',(TOOLS/'Reference/PressureStage6.hlsl').read_text(),names)
    for n in names:g.link(n,'Kernel',n)
    g.output('Kernel','EMISSIVE_COLOR');rows.append(g.finish())
    g=Graph('M_Solver_Fixture');g.mat.set_editor_property('allow_negative_emissive_color',True);g.node('UV','TextureCoordinate')
    custom(g,'Fixture','return float3(sin(UV.x*6.2831853)*0.5,cos(UV.y*6.2831853)*0.3,0.2+0.6*UV.x*UV.y);',['UV']);g.link('UV','Fixture','UV');g.output('Fixture','EMISSIVE_COLOR');rows.append(g.finish())
    (OUT/'build_manifest.json').write_text(json.dumps(rows,indent=2))
    return [{'path':r['path'],'nodes':len(r['nodes'])} for r in rows]

def sampler(pixels,x,y,c):
    # Hardware linear clamp for UV coordinates, with centers at (i+.5)/N.
    px=x*32-.5;py=y*32-.5;x0=math.floor(px);y0=math.floor(py);tx=px-x0;ty=py-y0
    # D3D sampler subtexel weights use fixed-point interpolation precision.
    tx=round(tx*256)/256;ty=round(ty*256)/256
    def at(a,b):return pixels[max(0,min(31,b))*32+max(0,min(31,a))][c]
    return (at(x0,y0)*(1-tx)+at(x0+1,y0)*tx)*(1-ty)+(at(x0,y0+1)*(1-tx)+at(x0+1,y0+1)*tx)*ty

def verify():
    w=world();source=target(w);output=target(w)
    fixture=u.MaterialLibrary.create_dynamic_material_instance(w,u.load_asset(PACKAGE+'M_Solver_Fixture'))
    pixels=[(c.r,c.g,c.b) for c in draw(w,source,fixture)]
    adv=u.MaterialLibrary.create_dynamic_material_instance(w,u.load_asset(PACKAGE+'M_Solver_Advection'));adv.set_texture_parameter_value('Field',source)
    dif=u.MaterialLibrary.create_dynamic_material_instance(w,u.load_asset(PACKAGE+'M_Solver_Differential'));dif.set_texture_parameter_value('Field',source)
    rows=[]
    for speed in [.5,1,3]:
        for clamp in [0,1]:
            adv.set_scalar_parameter_value('SimSpeed',speed);adv.set_scalar_parameter_value('AreaClamp',clamp)
            actual=draw(w,output,adv);errors=[]
            for i,c in enumerate(actual):
                x,y=(i%32+.5)/32,(i//32+.5)/32;x-=pixels[i][0]/32*speed;y-=pixels[i][1]/32*speed
                if not clamp:x%=1;y%=1
                errors.extend(abs(getattr(c,k)-sampler(pixels,x,y,j)*.9) for j,k in enumerate(['r','g','b']))
            rows.append({'stage':'advection','speed':speed,'clamp':clamp,'max_error':max(errors)})
    for mode in [0,1,2]:
        dif.set_scalar_parameter_value('Mode',mode);actual=draw(w,output,dif);errors=[]
        def at(x,y,c):return pixels[y*32+x][c] if 0<=x<32 and 0<=y<32 else 0
        for i,c in enumerate(actual):
            x,y=i%32,i//32
            if mode==2:expected=[at(x+1,y,0)-at(x-1,y,0)+at(x,y+1,1)-at(x,y-1,1),0,0]
            else:
                ux,uy=(x+.5)/32,(y+.5)/32
                dx=sampler(pixels,ux+1/32,uy,0)-sampler(pixels,ux-1/32,uy,0)
                dy=sampler(pixels,ux,uy+1/32,0)-sampler(pixels,ux,uy-1/32,0)
                expected=[dx*.5,dy*.5,0] if mode==1 else [dx+sampler(pixels,ux,uy+1/32,1)-sampler(pixels,ux,uy-1/32,1),0,0]
            errors.extend(abs(getattr(c,k)-expected[j]) for j,k in enumerate(['r','g','b']))
        rows.append({'stage':{0:'selected_divergence_1_7',1:'pressure_gradient',2:'legacy_integer_divergence_not_selected'}[mode],'max_error':max(errors)})
    pressure=u.MaterialLibrary.create_dynamic_material_instance(w,u.load_asset(PACKAGE+'M_Solver_Pressure'));pressure.set_texture_parameter_value('Pressure',source)
    body=(TOOLS/'Reference/PressureStage6.hlsl').read_text()
    def coefficients(name):
        block=body.split(name+'[6][15] =',1)[1].split(';',1)[0]
        return [[float(x) for x in re.findall(r'-?\d+(?:\.\d+)?',row)] for row in re.findall(r'\{([^{}]+)\}',block)]
    gauss=coefficients('GaussKernels');customs=coefficients('CustomKernels')
    for ki,offset in [(1,0),(2,-1),(4,1),(5,0)]:
        for step in [0,1]:
            for name,value in [('KIInput',ki),('OffsetInput',offset),('StepInput',step)]:pressure.set_scalar_parameter_value(name,value)
            actual=draw(w,output,pressure);count=15-ki*2;errors=[]
            for i,c in enumerate(actual):
                uv=[(i%32+.5)/32,(i//32+.5)/32];direction=[(1-step)/32,step/32];center=uv[:];center[step]-=(count-1)/64
                average=[0.,0.]
                for ix in range(count+1):
                    # Preserve original vector-valued (ix-Direction), inclusive loop.
                    sample=[(max(0,min(1,center[j]+direction[j]*(ix-direction[j]))))%1 for j in range(2)]
                    average[0]+=sampler(pixels,*sample,0)*gauss[ki+offset][ix+ki]
                    average[1]+=sampler(pixels,*sample,1)*customs[ki][ix+ki]
                if step:average[0]-=average[1]
                expected=[average[0]*.999,average[1]*.999,0]
                errors.extend(abs(getattr(c,k)-expected[j]) for j,k in enumerate(['r','g','b']))
            rows.append({'stage':'pressure','ki':ki,'offset':offset,'step':step,'max_error':max(errors)})
    result={'scope':__doc__,'reference':'CPU evaluation over GPU fixture values; integer zero-border and bilinear-clamp are distinct','cases':rows,'pass':all(r['max_error']<.0001 for r in rows)}
    (OUT/'gpu_verification.json').write_text(json.dumps(result,indent=2));assert result['pass'],result
    return {'pass':True,'cases':len(rows),'max_error':max(r['max_error'] for r in rows)}
