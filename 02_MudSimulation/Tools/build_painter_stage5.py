"""Independent exact Painter blend and dual-target history transport.

Controlled source fields only. This does not yet reconstruct source tracking,
radial brush generation, neighbor lookup or the complete original Painter.
"""
import sys,json,math,struct
from pathlib import Path
import unreal as u
TOOLS=Path(__file__).parent
if str(TOOLS) not in sys.path:sys.path.insert(0,str(TOOLS))
from build_display_stage1 import Graph,SNAPSHOT
from build_pom_stage2 import custom
OUT=TOOLS.parents[1]/'Verification/MudPainter'
PACKAGE='/Game/MudStudy/Rebuild/Materials/'
CODE=(TOOLS/'Reference/PainterBlendStage5.hlsl').read_text()

def world():
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert w.get_name() in ['L_Mud_FromScratch','L_Mud_RealtimeCompare']
    assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world(),'Stop PIE first'
    return w

def params(g,history=False):
    g.mat.set_editor_property('allow_negative_emissive_color',True)
    for name,value in [('Source',u.LinearColor(-0.4,0.7,0.8,0.6))]+([] if history else [('Dest',u.LinearColor(0.9,-0.3,0.2,0.4))]):
        g.node(name,'VectorParameter',parameter_name=name,default_value=value)
    for name,value in [('BlendPow',1),('Additive',0),('OutputAlpha',0)]+([] if history else [('RebuildScale',1)]):
        g.node(name,'ScalarParameter',parameter_name=name,default_value=value)
    for name in (['Source'] if history else ['Source','Dest']):
        g.node(name+'4','AppendVector');g.link(name,name+'4','A');g.link(name,name+'4','B','A')

def build():
    world();OUT.mkdir(exist_ok=True);rows=[]
    g=Graph('M_PainterBlend_Difference');params(g)
    custom(g,'Independent',CODE,['Source','Dest','BlendPow','Additive','OutputAlpha'])
    for a,b in [('Source4','Source'),('Dest4','Dest'),('BlendPow','BlendPow'),('Additive','Additive'),('OutputAlpha','OutputAlpha')]:g.link(a,'Independent',b)
    # Faithful source function graph: SrcRGB*SrcA + DstRGB*(1-pow(SrcA,p)).
    g.node('SrcWeighted','Multiply');g.link('Source','SrcWeighted','A');g.link('Source','SrcWeighted','B','A')
    g.node('WeightPow','Power');g.link('Source','WeightPow','Base','A');g.link('BlendPow','WeightPow','Exp')
    g.node('DestWeight','OneMinus');g.link('WeightPow','DestWeight')
    g.node('DstWeighted','Multiply');g.link('Dest','DstWeighted','A');g.link('DestWeight','DstWeighted','B')
    g.node('Translucent','Add');g.link('SrcWeighted','Translucent','A');g.link('DstWeighted','Translucent','B')
    g.node('AdditiveRGB','Add');g.link('Source','AdditiveRGB','A');g.link('Dest','AdditiveRGB','B')
    g.node('ChooseBlend','LinearInterpolate');g.link('Translucent','ChooseBlend','A');g.link('AdditiveRGB','ChooseBlend','B');g.link('Additive','ChooseBlend','Alpha')
    g.node('AlphaMax','Max');g.link('Source','AlphaMax','A','A');g.link('Dest','AlphaMax','B','A')
    g.node('Reference','LinearInterpolate');g.link('ChooseBlend','Reference','A');g.link('AlphaMax','Reference','B');g.link('OutputAlpha','Reference','Alpha')
    g.node('Scale','Multiply');g.link('Independent','Scale','A');g.link('RebuildScale','Scale','B')
    g.node('Subtract','Subtract');g.link('Reference','Subtract','A');g.link('Scale','Subtract','B');g.node('Difference','Abs');g.link('Subtract','Difference');g.output('Difference','EMISSIVE_COLOR');rows.append(g.finish())
    g=Graph('M_PainterBlend_History');params(g,True)
    for name in ['PreviousRGB','PreviousAlpha']:
        g.node(name,'TextureObjectParameter',parameter_name=name,texture=u.load_asset(SNAPSHOT),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    g.node('UV','TextureCoordinate')
    # Two targets retain all four signed components without alpha blend side effects.
    code='''float3 previousRGB=Texture2DSampleLevel(PreviousRGB, PreviousRGBSampler, UV, 0).rgb;
float previousAlpha=Texture2DSampleLevel(PreviousAlpha, PreviousAlphaSampler, UV, 0).r;
float4 Dest=float4(previousRGB,previousAlpha);
''' + CODE
    custom(g,'Update',code,['PreviousRGB','PreviousAlpha','UV','Source','BlendPow','Additive','OutputAlpha'])
    for name in ['PreviousRGB','PreviousAlpha','UV','BlendPow','Additive','OutputAlpha']:g.link(name,'Update',name)
    g.link('Source4','Update','Source');g.output('Update','EMISSIVE_COLOR');rows.append(g.finish())
    (OUT/'build_manifest.json').write_text(json.dumps(rows,indent=2))
    return [{'path':r['path'],'nodes':len(r['nodes'])} for r in rows]

def target(w):return u.RenderingLibrary.create_render_target2d(w,32,32,u.TextureRenderTargetFormat.RTF_RGBA32F,u.LinearColor(0,0,0,0),False,False)
def draw(w,rt,mid):
    u.RenderingLibrary.draw_material_to_render_target(w,rt,mid)
    values=u.RenderingLibrary.read_render_target_raw_pixel_area(w,rt,0,0,32,32,False)
    assert len(values)==1024 and all(math.isfinite(v) for c in values for v in [c.r,c.g,c.b])
    return values

def verify():
    w=world();rt=target(w);mid=u.MaterialLibrary.create_dynamic_material_instance(w,u.load_asset(PACKAGE+'M_PainterBlend_Difference'))
    rows=[]
    for alpha in [0,0.01,0.4,1]:
        for power in [0.5,1,2]:
            for additive in [0,1]:
                mid.set_vector_parameter_value('Source',u.LinearColor(-0.4,0.7,0.8,alpha));mid.set_vector_parameter_value('Dest',u.LinearColor(0.9,-0.3,0.2,0.6))
                for name,value in [('BlendPow',power),('Additive',additive)]:mid.set_scalar_parameter_value(name,value)
                errors=[];controls=[]
                for mode in [0,1]:
                    mid.set_scalar_parameter_value('OutputAlpha',mode)
                    for scale,destination in [(1,errors),(0,controls)]:
                        mid.set_scalar_parameter_value('RebuildScale',scale)
                        destination.append(max(max(abs(c.r),abs(c.g),abs(c.b)) for c in draw(w,rt,mid)))
                rows.append({'alpha':alpha,'power':power,'additive':additive,'errors_rgb_alpha':errors,'zero_controls_rgb_alpha':controls})
    # Distinct previous/current pairs: both draws read exactly the same old state.
    pairs=[(target(w),target(w)),(target(w),target(w))]
    history=u.MaterialLibrary.create_dynamic_material_instance(w,u.load_asset(PACKAGE+'M_PainterBlend_History'))
    expected=[0.,0.,0.,0.];frames=[]
    for i in range(12):
        source=[-0.2,0.3,0.8,0.4] if i<4 else [0.,0.,0.,0.] if i<8 else [0.1,-0.7,0.2,0.3]
        additive=1 if i>=10 else 0;power=1
        previous=pairs[i%2];current=pairs[(i+1)%2]
        assert all(a!=b for a in previous for b in current)
        history.set_texture_parameter_value('PreviousRGB',previous[0]);history.set_texture_parameter_value('PreviousAlpha',previous[1])
        history.set_vector_parameter_value('Source',u.LinearColor(*source));history.set_scalar_parameter_value('Additive',additive)
        history.set_scalar_parameter_value('OutputAlpha',0);rgb=draw(w,current[0],history)
        history.set_scalar_parameter_value('OutputAlpha',1);mask=draw(w,current[1],history)
        expected=[source[j]+expected[j] if additive else source[j]*source[3]+expected[j]*(1-source[3]**power) for j in range(3)]+[max(source[3],expected[3])]
        error=max(max(abs(getattr(c,k)-expected[j]) for j,k in enumerate(['r','g','b'])) for c in rgb)
        error=max(error,max(abs(c.r-expected[3]) for c in mask))
        frames.append({'frame':i,'source':source,'additive':additive,'expected':expected[:],'gpu_first_pixel':[rgb[0].r,rgb[0].g,rgb[0].b,mask[0].r],'max_error':error})
    result={'scope':__doc__,'cases':rows,'history_frames':frames,'pass':all(max(r['errors_rgb_alpha'])<1e-5 and max(r['zero_controls_rgb_alpha'])>0.001 for r in rows) and max(r['max_error'] for r in frames)<1e-5}
    (OUT/'gpu_verification.json').write_text(json.dumps(result,indent=2));assert result['pass'],result
    return {'pass':result['pass'],'cases':len(rows),'max_blend_error':max(max(r['errors_rgb_alpha']) for r in rows),'max_history_error':max(r['max_error'] for r in frames)}
