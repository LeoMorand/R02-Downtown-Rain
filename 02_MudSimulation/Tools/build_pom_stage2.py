"""Independent local POM against the ORIGINAL FluidNinja function on geometry.

Own assets only; use the existing learning map and frozen source texture.
"""
import json,math,sys
from pathlib import Path
import unreal as u
TOOLS=Path('D:/aco/unreal/Stormfall/Tools/MudStudy')
if str(TOOLS) not in sys.path:sys.path.insert(0,str(TOOLS))
from build_display_stage1 import Graph,world,SNAPSHOT,HLSL as NORMAL_HLSL
ROOT=Path('D:/aco/unreal/Stormfall/Verification/MudRebuildPOM')
PACKAGE='/Game/MudStudy/Rebuild/Materials'
ORIGINAL='/Game/FluidNinjaLive/OutputMaterials/Base/Functions/MF_ParallaxOcclusionMappingSimple'
CODE=(TOOLS/'Reference/POMStage2.hlsl').read_text(encoding='utf-8')

def custom(g,name,code,names,output=u.CustomMaterialOutputType.CMOT_FLOAT3):
    pins=[]
    for name_ in names:
        pin=u.CustomInput();pin.set_editor_property('input_name',name_);pins.append(pin)
    return g.node(name,'Custom',code=code,inputs=pins,output_type=output)

def common(g,reference=True,rebuild=True):
    g.node('UV','TextureCoordinate')
    g.node('Height','TextureObjectParameter',parameter_name='FrozenVelocityDensity',texture=u.load_asset(SNAPSHOT),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    for name,value in [('HeightRatio',0.01),('ReferencePlane',0.9),('MinSteps',8),('MaxSteps',32)]+([('RebuildHeightScale',1)] if rebuild else []):
        g.node(name,'ScalarParameter',parameter_name=name,default_value=value)
    if reference:
        g.node('ReferencePOM','MaterialFunctionCall')
        assert g.nodes['ReferencePOM'].set_material_function(u.load_asset(ORIGINAL))
        for a,pin in [('Height','Heightmap Texture'),('HeightRatio','Height Ratio'),('ReferencePlane','Reference Plane'),('MinSteps','Min Steps'),('MaxSteps','Max Steps'),('UV','UVs')]:g.link(a,'ReferencePOM',pin)
        g.node('ChannelB','Constant4Vector',constant=u.LinearColor(0,0,1,0));g.link('ChannelB','ReferencePOM','Heightmap Channel')
        g.node('UseWorld','StaticBool',value=True);g.link('UseWorld','ReferencePOM','UseWorldCoordinates')
        g.node('Up','VertexNormalWS');g.link('Up','ReferencePOM','UpVector')
    if rebuild:
        g.node('ViewWS','CameraVectorWS');g.node('ViewTS','Transform',transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
        g.link('ViewWS','ViewTS')
        g.node('VertexNormal','VertexNormalWS');g.node('WorldPos','WorldPosition')
        g.node('CameraForward','MaterialFunctionCall')
        assert g.nodes['CameraForward'].set_material_function(u.load_asset('/Engine/Functions/Engine_MaterialFunctions02/Utility/CameraDirectionVector'))
        names=['Height','UV','HeightRatio','ReferencePlane','MinSteps','MaxSteps','ViewTS','ViewWS','VertexNormal','WorldPos','CameraForward','RebuildHeightScale']
        custom(g,'IndependentPOM',CODE,names)
        for name in names:g.link(name,'IndependentPOM',name)
    return g

def instance(name,mat):
    path=PACKAGE+'/'+name
    mi=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset(name,PACKAGE,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    u.MaterialEditingLibrary.set_material_instance_parent(mi,mat)
    u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi,'ForceLocalSpace',1)
    assert u.EditorAssetLibrary.save_loaded_asset(mi)
    return path

def build():
    world();ROOT.mkdir(exist_ok=True)
    rows=[]
    for name,original in [('M_POM_Reference',True),('M_POM_Rebuilt',False)]:
        g=Graph(name,False);common(g,reference=original,rebuild=not original)
        if original:
            uvnode,uvout='ReferencePOM','Parallax UVs';depthnode,depthout='ReferencePOM','Pixel Depth Offset'
        else:
            g.node('ParallaxUV','ComponentMask',r=True,g=True,b=False,a=False);g.link('IndependentPOM','ParallaxUV')
            g.node('Depth','ComponentMask',r=False,g=False,b=True,a=False);g.link('IndependentPOM','Depth')
            uvnode,uvout='ParallaxUV','';depthnode,depthout='Depth',''
        g.node('NormalOffset','ScalarParameter',parameter_name='NormalOffset',default_value=0.0005)
        g.node('NormalStrength','ScalarParameter',parameter_name='NormalStrength',default_value=40)
        custom(g,'Normal',NORMAL_HLSL,['Height','UV','Offset','Strength'])
        g.link('Height','Normal','Height');g.link(uvnode,'Normal','UV',uvout);g.link('NormalOffset','Normal','Offset');g.link('NormalStrength','Normal','Strength')
        g.output('Normal','NORMAL')
        g.node('Brown','Constant3Vector',constant=u.LinearColor(0.14536,0.073858,0.040263,1));g.output('Brown','BASE_COLOR')
        for n,v,prop in [('Roughness',0.1,'ROUGHNESS'),('Specular',0.2,'SPECULAR')]:g.node(n,'Constant',r=v);g.output(n,prop)
        row=g.finish();row['instance']=instance('MI_'+name[2:],g.mat)
        # UE marks MP_PixelDepthOffset Hidden, so the Python enum omits it.
        # Wire this via native MCP material.connect_to_property after build.
        row['pendingNativeDepthConnection']={'expression':g.nodes[depthnode].get_name(),'output':depthout}
        rows.append(row)
    g=Graph('M_POM_Difference');common(g)
    g.node('ReferencePacked','AppendVector');g.link('ReferencePOM','ReferencePacked','A','Parallax UVs');g.link('ReferencePOM','ReferencePacked','B','Pixel Depth Offset')
    g.node('Subtract','Subtract');g.link('ReferencePacked','Subtract','A');g.link('IndependentPOM','Subtract','B')
    g.node('Absolute','Abs');g.link('Subtract','Absolute');g.output('Absolute','EMISSIVE_COLOR')
    row=g.finish();row['instance']=instance('MI_POM_Difference',g.mat);rows.append(row)
    (ROOT/'build_manifest.json').write_text(json.dumps({'reference_function':ORIGINAL,'hlsl':CODE,'materials':rows},indent=2),encoding='utf-8')
    return {'materials':[{'path':r['path'],'nodes':len(r['nodes'])} for r in rows]}

def layout():
    w=world();sub=u.get_editor_subsystem(u.EditorActorSubsystem);actors={a.get_actor_label():a for a in sub.get_all_level_actors()}
    for label,x,mat,text in [('POM_Reference',-700,'MI_POM_Reference','P1 Original POM'),('POM_Rebuilt',0,'MI_POM_Rebuilt','P2 Independent POM'),('POM_Difference',700,'MI_POM_Difference','P3 UV/PDO difference')]:
        a=actors.get(label)
        if a is None:a=sub.spawn_actor_from_class(u.StaticMeshActor,u.Vector(x,1700,5));a.set_actor_label(label)
        mesh=a.get_component_by_class(u.StaticMeshComponent);mesh.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'));mesh.set_relative_scale3d(u.Vector(6,6,1));mesh.set_material(0,u.load_asset(PACKAGE+'/'+mat))
        title=actors.get(label+'_Label')
        if title is None:title=sub.spawn_actor_from_class(u.TextRenderActor,u.Vector(x,1270,50));title.set_actor_label(label+'_Label')
        title.set_actor_rotation(u.Rotator(pitch=0,yaw=-90,roll=0),False)
        comp=title.get_component_by_class(u.TextRenderComponent);comp.set_text(u.Text(text));comp.set_world_size(30);comp.set_horizontal_alignment(u.HorizTextAligment.EHTA_CENTER)
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    return {'map':w.get_path_name(),'row_y':1700}

def verify_gpu():
    w=world();sub=u.get_editor_subsystem(u.EditorActorSubsystem)
    target=next(a for a in sub.get_all_level_actors() if a.get_actor_label()=='POM_Difference')
    mesh=target.get_component_by_class(u.StaticMeshComponent);old=u.load_asset(PACKAGE+'/MI_POM_Difference')
    mid=u.MaterialLibrary.create_dynamic_material_instance(w,u.load_asset(PACKAGE+'/M_POM_Difference'))
    mid.set_scalar_parameter_value('ForceLocalSpace',1);mesh.set_material(0,mid)
    rt=u.RenderingLibrary.create_render_target2d(w,64,64,u.TextureRenderTargetFormat.RTF_RGBA16F,u.LinearColor(0,0,0,1),False,False)
    actor=None;rows=[]
    try:
        actor=sub.spawn_actor_from_class(u.SceneCapture2D,u.Vector(700,1000,605));actor.set_actor_label('Stage2_TransientCapture')
        actor.set_actor_rotation(u.Rotator(pitch=-40.6,yaw=90,roll=0),False)
        cap=actor.get_component_by_class(u.SceneCaptureComponent2D);cap.set_editor_property('texture_target',rt);cap.set_editor_property('fov_angle',50)
        cap.set_editor_property('capture_every_frame',False);cap.set_editor_property('capture_on_movement',False)
        cap.set_editor_property('primitive_render_mode',u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST);cap.show_only_actor_components(target)
        flags=[]
        for name in ['Fog','Atmosphere','Bloom','EyeAdaptation','TemporalAA','Tonemapper']:
            flag=u.EngineShowFlagsSetting();flag.set_editor_property('show_flag_name',name);flag.set_editor_property('enabled',False);flags.append(flag)
        cap.set_editor_property('show_flag_settings',flags)
        cases=[('oblique',700,600,0.01,0.9),('near_normal',50,900,0.01,0.9),
               ('grazing',1200,150,0.01,0.9),('height_reference_variant',700,600,0.02,0.5)]
        for label,back,height,ratio,reference in cases:
            actor.set_actor_location(u.Vector(700,1700-back,5+height),False,False)
            actor.set_actor_rotation(u.Rotator(pitch=-math.degrees(math.atan2(height,back)),yaw=90,roll=0),False)
            mid.set_scalar_parameter_value('HeightRatio',ratio);mid.set_scalar_parameter_value('ReferencePlane',reference)
            samples=[]
            for scale in [1,0]:
                mid.set_scalar_parameter_value('RebuildHeightScale',scale)
                cap.capture_scene()
                pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(w,rt,0,0,64,64,False)
                assert len(pixels)==4096
                values=[(c.r,c.g,c.b) for c in pixels]
                assert all(math.isfinite(v) for c in values for v in c),'Nonfinite result'
                maxima=[max(abs(c[i]) for c in values) for i in range(3)]
                samples.append({'height_scale':scale,'pixels':len(pixels),'max_abs_UV_PDO':maxima})
            rows.append({'case':label,'height_ratio':ratio,'reference_plane':reference,
                'camera_back_cm':back,'camera_height_cm':height,'readbacks':samples,
                'pass':max(samples[0]['max_abs_UV_PDO'][:2])<0.0002 and samples[0]['max_abs_UV_PDO'][2]<0.05 and max(samples[1]['max_abs_UV_PDO'])>0.001})
    finally:
        mesh.set_material(0,old)
        if actor:sub.destroy_actor(actor)
    result={'scope':'Original POM function vs independent local desktop HLSL; four geometry/camera/parameter fixtures; frozen texture; 64x64 each',
        'cases':rows,'pass':all(r['pass'] for r in rows)}
    (ROOT/'gpu_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    assert result['pass'],result
    return result

def cleanup():
    world();sub=u.get_editor_subsystem(u.EditorActorSubsystem);removed=[]
    for actor in sub.get_all_level_actors():
        if isinstance(actor,u.SceneCapture2D) and (actor.get_actor_label().startswith('Stage2_') or actor.get_actor_label()=='SceneCapture2D'):
            removed.append(actor.get_actor_label());sub.destroy_actor(actor)
        elif actor.get_actor_label()=='POM_Difference':actor.get_component_by_class(u.StaticMeshComponent).set_material(0,u.load_asset(PACKAGE+'/MI_POM_Difference'))
    return {'removed':removed}
