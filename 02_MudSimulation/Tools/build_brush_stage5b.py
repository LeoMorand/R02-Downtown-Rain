"""GPU-check the selected Painter footprint slice, not the complete Painter.

Reference HLSL is emitted directly from selected graph pins. Independent HLSL
uses simplified algebra. Noise and sampled field height remain explicit inputs.
"""
import sys,json,math
from pathlib import Path
import unreal as u
TOOLS=Path(__file__).parent
if str(TOOLS) not in sys.path:sys.path.insert(0,str(TOOLS))
from build_display_stage1 import Graph
from build_pom_stage2 import custom
from build_painter_stage5 import world,target,draw
OUT=TOOLS.parents[1]/'Verification/MudPainter'
PACKAGE='/Game/MudStudy/Rebuild/Materials/'
SCALARS={'ObjectSize':0.05,'VelocityClamp':1,'NegativePuncture':0,'Age':2,'Puncture':0.2,'BrushSize':2,
 'InterpolationLimit':0.5,'Interpolate':1,'Hardness':0.1,'HardnessBySize':0.2,
 'ZFadeScale':5,'PositionZ':0.5,'FadeByZ':0,'DensityNoise':1,'FieldHeight':0}
VECTORS={'Aspect':(1,1,0),'Position':(0.65,0.5,0),'PreviousPosition':(0.35,0.5,0),
 'Velocity':(0.2,0,0),'WorldExtents':(20,20,0),'OffsetDelta':(0,0,0)}
NAMES=['UV']+list(SCALARS)+list(VECTORS)

def common(g):
    g.node('UV','TextureCoordinate')
    for k,v in SCALARS.items():g.node(k,'ScalarParameter',parameter_name=k,default_value=v)
    for k,v in VECTORS.items():
        g.node(k if k=='Velocity' else k+'Param','VectorParameter',parameter_name=k,default_value=u.LinearColor(*v,0))
        if k!='Velocity':g.node(k,'ComponentMask',r=True,g=True,b=False,a=False);g.link(k+'Param',k)

def build():
    world();rows=[]
    ref=(TOOLS/'Reference/BrushReferenceStage5b.hlsl').read_text()
    independent=(TOOLS/'Reference/BrushShapeStage5b.hlsl').read_text()
    g=Graph('M_BrushShape_Difference');common(g)
    custom(g,'Reference',ref,NAMES);custom(g,'Independent',independent,NAMES)
    for name in NAMES:
        g.link(name,'Reference',name)
        if name!='Interpolate':g.link(name,'Independent',name)
    g.node('InterpolationControl','ScalarParameter',parameter_name='InterpolationControl',default_value=1)
    g.node('InterpolateScale','Multiply');g.link('Interpolate','InterpolateScale','A');g.link('InterpolationControl','InterpolateScale','B');g.link('InterpolateScale','Independent','Interpolate')
    g.node('RebuildScale','ScalarParameter',parameter_name='RebuildScale',default_value=1)
    g.node('Scale','Multiply');g.link('Independent','Scale','A');g.link('RebuildScale','Scale','B')
    g.node('Subtract','Subtract');g.link('Reference','Subtract','A');g.link('Scale','Subtract','B')
    g.node('Abs','Abs');g.link('Subtract','Abs');g.output('Abs','EMISSIVE_COLOR');rows.append(g.finish())
    g=Graph('M_BrushShape_Preview');common(g)
    custom(g,'Brush',independent,NAMES)
    for name in NAMES:g.link(name,'Brush',name)
    g.node('Mask','ComponentMask',r=False,g=True,b=False,a=False);g.link('Brush','Mask');g.output('Mask','EMISSIVE_COLOR');rows.append(g.finish())
    g=Graph('M_SourceVelocityGuard');g.mat.set_editor_property('allow_negative_emissive_color',True)
    for k,v in [('Current',(0.2,0.1,0)),('Previous',(0.1,0.1,0))]:g.node(k,'VectorParameter',parameter_name=k,default_value=u.LinearColor(*v,0))
    g.node('Multiplier','ScalarParameter',parameter_name='Multiplier',default_value=8)
    custom(g,'Guard','return length(Current-Previous)<1 ? Current*Multiplier : float3(0,0,0);',['Current','Previous','Multiplier'])
    for name in ['Current','Previous','Multiplier']:g.link(name,'Guard',name)
    g.output('Guard','EMISSIVE_COLOR');rows.append(g.finish())
    (OUT/'brush_build_manifest.json').write_text(json.dumps(rows,indent=2))
    return [{'path':r['path'],'nodes':len(r['nodes'])} for r in rows]

def configure(mid,case):
    for k,v in (SCALARS|case.get('scalar',{})).items():mid.set_scalar_parameter_value(k,v)
    for k,v in (VECTORS|case.get('vector',{})).items():mid.set_vector_parameter_value(k,u.LinearColor(*v,0))

def verify():
    w=world();rt=target(w)
    mid=u.MaterialLibrary.create_dynamic_material_instance(w,u.load_asset(PACKAGE+'M_BrushShape_Difference'))
    cases=[{'name':'moving_segment'}, {'name':'zero_velocity','vector':{'Velocity':(0,0,0)}},
        {'name':'too_fast','vector':{'Velocity':(0.5001,0,0)}},
        {'name':'speed_equal_limit','vector':{'Velocity':(0.5,0,0)}},
        {'name':'initial_age_boundary','scalar':{'Age':0.25}},
        {'name':'after_age_boundary','scalar':{'Age':0.2501}},
        {'name':'interpolation_off','scalar':{'Interpolate':0}},
        {'name':'aspect_and_offset','vector':{'Aspect':(2,1,0),'WorldExtents':(40,20,0),'OffsetDelta':(1,-2,0)}},
        {'name':'puncture_positive','scalar':{'Age':12,'Puncture':0.8},'vector':{'Velocity':(0.1,0,0.8)}},
        {'name':'negative_puncture','scalar':{'NegativePuncture':1,'Puncture':0.6},'vector':{'Velocity':(0.1,0,-0.6)}},
        {'name':'z_fade_field_noise','scalar':{'FadeByZ':1,'PositionZ':0.7,'FieldHeight':2,'DensityNoise':0.65}},
        {'name':'hardness_clamp','scalar':{'Hardness':0.9,'HardnessBySize':20}},
        {'name':'larger_brush','scalar':{'ObjectSize':0.1,'BrushSize':3}},
        {'name':'reverse_segment','vector':{'Position':(0.35,0.5,0),'PreviousPosition':(0.65,0.5,0),'Velocity':(-0.2,0,0)}},
        {'name':'coincident_positions','vector':{'PreviousPosition':(0.65,0.5,0)}}]
    rows=[]
    for case in cases:
        configure(mid,case);mid.set_scalar_parameter_value('RebuildScale',1);mid.set_scalar_parameter_value('InterpolationControl',1)
        pixels=draw(w,rt,mid);errors=[max(abs(getattr(c,k)) for c in pixels) for k in ['r','g','b']]
        mid.set_scalar_parameter_value('RebuildScale',0);control=max(max(c.r,c.g,c.b) for c in draw(w,rt,mid))
        mid.set_scalar_parameter_value('RebuildScale',1);mid.set_scalar_parameter_value('InterpolationControl',0)
        disabled=max(c.r for c in draw(w,rt,mid))
        rows.append(case|{'max_error_kernel_mask_radius':errors,'zero_output_control':control,'force_point_kernel_difference':disabled})
    guard=u.MaterialLibrary.create_dynamic_material_instance(w,u.load_asset(PACKAGE+'M_SourceVelocityGuard'));guards=[]
    for current,previous in [((0.2,0.1,0),(0.1,0.1,0)),((1,0,0),(0,0,0)),((0.9999,0,0),(0,0,0)),((1.0001,0,0),(0,0,0)),((-0.2,0.3,-0.1),(-0.2,0.3,-0.1)),((0,0,0),(1,0,0))]:
        for k,v in [('Current',current),('Previous',previous)]:guard.set_vector_parameter_value(k,u.LinearColor(*v,0))
        guard.set_scalar_parameter_value('Multiplier',8)
        expected=[x*8 for x in current] if math.dist(current,previous)<1 else [0,0,0]
        pixels=draw(w,rt,guard);error=max(max(abs(getattr(c,k)-expected[j]) for j,k in enumerate(['r','g','b'])) for c in pixels)
        guards.append({'current':current,'previous':previous,'expected':expected,'gpu':[pixels[0].r,pixels[0].g,pixels[0].b],'error':error})
    result={'scope':__doc__,'cases':rows,'velocity_guard':guards,
        'pass':all(max(r['max_error_kernel_mask_radius'])<0.001 and r['zero_output_control']>0.001 for r in rows) and max(g['error'] for g in guards)<1e-5
            and rows[0]['force_point_kernel_difference']>0.1 and rows[1]['force_point_kernel_difference']<0.001 and rows[2]['force_point_kernel_difference']<0.001
            and rows[3]['force_point_kernel_difference']>0.1 and rows[4]['force_point_kernel_difference']<0.001 and rows[5]['force_point_kernel_difference']>0.1}
    (OUT/'brush_gpu_verification.json').write_text(json.dumps(result,indent=2));assert result['pass'],result
    return {'pass':result['pass'],'cases':len(rows),'max_shape_error':max(max(r['max_error_kernel_mask_radius']) for r in rows),'max_guard_error':max(g['error'] for g in guards)}

def previews():
    w=world();mid=u.MaterialLibrary.create_dynamic_material_instance(w,u.load_asset(PACKAGE+'M_BrushShape_Preview'))
    rt=u.RenderingLibrary.create_render_target2d(w,256,256,u.TextureRenderTargetFormat.RTF_RGBA8,u.LinearColor(0,0,0,1),False,False)
    paths=[]
    for name,interpolate in [('brush-point',0),('brush-segment',1)]:
        configure(mid,{'scalar':{'Interpolate':interpolate}})
        u.RenderingLibrary.draw_material_to_render_target(w,rt,mid)
        u.RenderingLibrary.export_render_target(w,rt,str(OUT),name+'.png')
        paths.append(str(OUT/(name+'.png')))
    return paths
