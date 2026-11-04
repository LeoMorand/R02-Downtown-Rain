"""Independent first tracked brush RGBA, including sampled noise and packing."""
import sys,json
from pathlib import Path
import unreal as u
TOOLS=Path(__file__).parent
if str(TOOLS) not in sys.path:sys.path.insert(0,str(TOOLS))
from build_display_stage1 import Graph
from build_pom_stage2 import custom
from build_brush_stage5b import SCALARS,VECTORS,configure
from build_painter_stage5 import world,target,draw
OUT=TOOLS.parents[1]/'Verification/MudPainter'
PACKAGE='/Game/MudStudy/Rebuild/Materials/'
EXTRA={'VelocityNoiseScale':30,'VelocityNoiseFrequency':0.1,'VelocityNoiseAmount':0.5,'SimTime':1.75,
 'DensityNoiseScale':3,'DensityNoiseFrequency':40,'DensityNoisePower':2,'DensityNoiseAmount':0.4,
 'NoiseWorldSpace':1,'VelocityPower':1.6,'VelocityZMultiplier':1,'VelocityXYMultiplier':1,
 'SlowVelocityThreshold':0.4,'BrushStrength':1,'DensityEnable':1,'InputFeedback':0,'OutputAlpha':0}
S=(SCALARS|EXTRA);S.pop('DensityNoise')
V=VECTORS|{'WorldOffset':(0.23,-0.41,0)}
NAMES=['UV','NoiseTexture']+list(S)+list(V)

def independent_code():
    prefix='''float2 noiseUV=NoiseWorldSpace>0.5 ? UV+WorldOffset : UV*0.5;
float2 VelocityNoise=(Texture2DSampleLevel(NoiseTexture,NoiseTextureSampler,noiseUV*VelocityNoiseScale+SimTime*VelocityNoiseFrequency,0).rg-0.5)*0.1*VelocityNoiseAmount;
float densitySample=Texture2DSampleLevel(NoiseTexture,NoiseTextureSampler,noiseUV*DensityNoiseScale+trunc(SimTime*DensityNoiseFrequency)*0.1,0).r;
float DensityNoise=max(pow(max(densitySample,0),DensityNoisePower),1-DensityNoiseAmount);
'''
    shape=(TOOLS/'Reference/BrushShapeStage5b.hlsl').read_text().replace('return float3(kernel,mask,radius);','')
    return prefix+shape+(TOOLS/'Reference/StrokePackingStage5c.hlsl').read_text()

def build():
    world();g=Graph('M_StrokeRGBA_Difference')
    g.node('UV','TextureCoordinate')
    for k,v in S.items():g.node(k,'ScalarParameter',parameter_name=k,default_value=v)
    for k,v in V.items():
        g.node(k if k=='Velocity' else k+'Param','VectorParameter',parameter_name=k,default_value=u.LinearColor(*v,0))
        if k!='Velocity':g.node(k,'ComponentMask',r=True,g=True,b=False,a=False);g.link(k+'Param',k)
    g.node('NoiseTexture','TextureObjectParameter',parameter_name='NoiseTexture',texture=u.load_asset('/Game/FluidNinjaLive/Core/Assets/T_NoiseTemplate2'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    custom(g,'Reference',(TOOLS/'Reference/StrokeReferenceStage5c.hlsl').read_text(),NAMES)
    custom(g,'Independent',independent_code(),NAMES)
    for k in NAMES:g.link(k,'Reference',k);g.link(k,'Independent',k)
    g.node('RebuildScale','ScalarParameter',parameter_name='RebuildScale',default_value=1)
    g.node('Scale','Multiply');g.link('Independent','Scale','A');g.link('RebuildScale','Scale','B')
    g.node('Subtract','Subtract');g.link('Reference','Subtract','A');g.link('Scale','Subtract','B')
    g.node('Abs','Abs');g.link('Subtract','Abs');g.output('Abs','EMISSIVE_COLOR')
    row=g.finish();(OUT/'stroke_build_manifest.json').write_text(json.dumps(row,indent=2))
    return {'path':row['path'],'nodes':len(row['nodes'])}

def verify():
    w=world();rt=target(w);mid=u.MaterialLibrary.create_dynamic_material_instance(w,u.load_asset(PACKAGE+'M_StrokeRGBA_Difference'))
    cases=[{'name':'selected_defaults'}, {'name':'negative_velocity','vector':{'Velocity':(-.25,.12,0)}},
        {'name':'no_density','scalar':{'DensityEnable':0}}, {'name':'puncture','vector':{'Velocity':(.1,.1,-.8)},'scalar':{'NegativePuncture':1,'Age':12,'Puncture':.8}},
        {'name':'feedback','scalar':{'InputFeedback':.8}}, {'name':'slow_threshold_equal','vector':{'Velocity':(.4,0,0)}},
        {'name':'local_noise','scalar':{'NoiseWorldSpace':0,'SimTime':2.731}}, {'name':'no_noise','scalar':{'VelocityNoiseAmount':0,'DensityNoiseAmount':0}},
        {'name':'z_fade','scalar':{'FadeByZ':1,'PositionZ':.65,'FieldHeight':2,'SimTime':.135}},
        {'name':'velocity_clamp','vector':{'Velocity':(-4,3,0)},'scalar':{'VelocityClamp':2,'VelocityXYMultiplier':.3}}]
    rows=[]
    for case in cases:
        for k,v in (S|case.get('scalar',{})).items():mid.set_scalar_parameter_value(k,v)
        for k,v in (V|case.get('vector',{})).items():mid.set_vector_parameter_value(k,u.LinearColor(*v,0))
        errors=[];controls=[]
        for mode in [0,1]:
            mid.set_scalar_parameter_value('OutputAlpha',mode)
            for scale,destination in [(1,errors),(0,controls)]:
                mid.set_scalar_parameter_value('RebuildScale',scale);values=draw(w,rt,mid)
                destination.append(max(max(c.r,c.g,c.b) for c in values))
        rows.append(case|{'max_error_rgb_alpha':errors,'zero_control_rgb_alpha':controls})
    result={'scope':__doc__,'cases':rows,'pass':all(max(r['max_error_rgb_alpha'])<0.001 and max(r['zero_control_rgb_alpha'])>0.001 for r in rows)}
    (OUT/'stroke_gpu_verification.json').write_text(json.dumps(result,indent=2));assert result['pass'],result
    return {'pass':True,'cases':len(rows),'max_error':max(max(r['max_error_rgb_alpha']) for r in rows)}
