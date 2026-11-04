"""Live RT integration in a copied source map; original solver is retained.

Editor configuration changes only /Game/MudStudy/Maps/L_Mud_RealtimeCompare.
The original NinjaLive actor type is preserved. Probe actors belong to the copied
map; their dynamic materials and readback targets are transient.
"""
import json,math
from pathlib import Path
import unreal as u
OUT=Path('D:/aco/unreal/Stormfall/Verification/MudRealtime')
MAP='L_Mud_RealtimeCompare'
MATERIALS='/Game/MudStudy/Rebuild/Materials/'
STATE={}

def build_probe():
    import sys
    directory=str(Path(__file__).parent)
    if directory not in sys.path:sys.path.insert(0,directory)
    from build_display_stage1 import Graph,SNAPSHOT
    g=Graph('M_LiveRT_Probe')
    g.node('Buffer','TextureSampleParameter2D',parameter_name='Buffer',texture=u.load_asset(SNAPSHOT),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    g.output('Buffer','EMISSIVE_COLOR')
    return g.finish()

def field_probe(w,rt):
    STATE['field_mid'].set_texture_parameter_value('Buffer',rt)
    u.RenderingLibrary.draw_material_to_render_target(w,STATE['field_rt'],STATE['field_mid'])
    colors=u.RenderingLibrary.read_render_target_raw_pixel_area(w,STATE['field_rt'],0,0,64,64,False)
    values=[(c.r,c.g,c.b) for c in colors]
    assert len(values)==4096
    if 'field_baseline' not in STATE:STATE['field_baseline']=values
    base=STATE['field_baseline']
    delta=[max(abs(a-b) for a,b in zip(v,base[i])) for i,v in enumerate(values)]
    return {'resolution':[64,64],'changed_pixels':sum(d>0.001 for d in delta),'max_delta':max(delta),
        'max_abs_velocity':max(max(abs(v[0]),abs(v[1])) for v in values),
        'density_range':[min(v[2] for v in values),max(v[2] for v in values)]}

def vec(v):return {'x':v.x,'y':v.y,'z':v.z}
def find_actor(w):return next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor) if a.get_actor_label()=='NinjaLive_Mud1')
def configure_editor():
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert w.get_name()==MAP,w.get_path_name()
    actor=find_actor(w);assert actor.get_class().get_name()=='NinjaLive_C'
    sim=actor.get_editor_property('NinjaLiveComponent');items=list(sim.get_editor_property('PrimaryOutputMaterials'))
    mat=u.load_asset(MATERIALS+'MI_Surface_Rebuilt');paths=[x.get_path_name() for x in items]
    if mat.get_path_name() not in paths:items.append(mat)
    index=next(i for i,x in enumerate(items) if x==mat)
    sim.set_editor_property('PrimaryOutputMaterials',items);sim.set_editor_property('PrimaryOutputMaterialSelected',index)
    sub=u.get_editor_subsystem(u.EditorActorSubsystem);existing={a.get_actor_label():a for a in sub.get_all_level_actors()}
    position=actor.get_actor_location();position=u.Vector(position.x+3500,position.y,position.z)
    probe=existing.get('Stage4_ComparisonPlane')
    if probe is None:probe=sub.spawn_actor_from_class(u.StaticMeshActor,position);probe.set_actor_label('Stage4_ComparisonPlane')
    mesh=probe.get_component_by_class(u.StaticMeshComponent);mesh.set_mobility(u.ComponentMobility.MOVABLE);mesh.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);mesh.set_editor_property('generate_overlap_events',False)
    mesh.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'));mesh.set_relative_scale3d(u.Vector(20,20,1));mesh.set_material(0,u.load_asset(MATERIALS+'MI_Surface_Difference'))
    cap=existing.get('Stage4_Capture')
    if cap is None:cap=sub.spawn_actor_from_class(u.SceneCapture2D,u.Vector(position.x,position.y-2050,position.z+1800));cap.set_actor_label('Stage4_Capture')
    comp=cap.get_component_by_class(u.SceneCaptureComponent2D);comp.set_editor_property('capture_every_frame',False);comp.set_editor_property('capture_on_movement',False)
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    OUT.mkdir(exist_ok=True)
    info={'map':w.get_path_name(),'actor_class':actor.get_class().get_path_name(),'selected':index,'materials':[x.get_path_name() for x in items]}
    (OUT/'editor_configuration.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    return info

def copy_parameters(source,target):
    counts={}
    for kind,setter in [('scalar','set_scalar_parameter_value'),('vector','set_vector_parameter_value'),('texture','set_texture_parameter_value')]:
        values=source.get_editor_property(kind+'_parameter_values');count=0
        for entry in values:
            info=entry.get_editor_property('parameter_info');name=info.get_editor_property('name');value=entry.get_editor_property('parameter_value')
            if value is not None:getattr(target,setter)(name,value);count+=1
        counts[kind]=count
    return counts

def sync():
    sim=STATE['sim'];source=sim.get_editor_property('MI_Output');rt=sim.get_editor_property('RT_VelocityDensity')
    assert source and rt,'Source deactivated or RT missing'
    assert source.get_editor_property('parent').get_path_name().endswith('MI_Surface_Rebuilt.MI_Surface_Rebuilt'),source.get_path_name()
    bound=source.get_texture_parameter_value('VelocityDensityBuffer')
    assert bound==rt,('Stale/default texture binding',str(bound),rt.get_path_name())
    counts=copy_parameters(source,STATE['mid']);STATE['mid'].set_texture_parameter_value('VelocityDensityBuffer',rt)
    return source,rt,counts

def probes(w,rt):
    width=rt.get_editor_property('size_x');height=rt.get_editor_property('size_y');rows=[]
    for fy in [0.25,0.5,0.75]:
        for fx in [0.25,0.5,0.75]:
            x,y=int(width*fx),int(height*fy);c=u.RenderingLibrary.read_render_target_raw_pixel(w,rt,x,y,False)
            rows.append({'pixel':[x,y],'rgba':[c.r,c.g,c.b,c.a]})
    return rows

def capture():
    w=STATE['world'];mid=STATE['mid'];cap=STATE['capture'];rt_out=STATE['capture_rt']
    source,rt,counts=sync();results=[]
    for mode in [0,1,2]:
        mid.set_scalar_parameter_value('DebugMode',mode);mid.set_scalar_parameter_value('RebuildHeightScale',1)
        cap.capture_scene();pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(w,rt_out,0,0,64,64,False)
        assert len(pixels)==4096 and all(math.isfinite(v) for c in pixels for v in [c.r,c.g,c.b])
        results.append({'mode':mode,'max_abs_rgb':[max(abs(getattr(c,k)) for c in pixels) for k in ['r','g','b']]})
    return {'world_time':u.GameplayStatics.get_time_seconds(w),'activation':bool(STATE['sim'].get_editor_property('PawnInsideActivationBounds')),
        'source_mid':source.get_path_name(),'source_parent':source.get_editor_property('parent').get_path_name(),
        'rt':rt.get_path_name(),'rt_size':[rt.get_editor_property('size_x'),rt.get_editor_property('size_y')],
        'synced_override_counts':counts,'comparisons':results,'probes':probes(w,rt),'field':field_probe(w,rt)}

def write():
    (OUT/'dynamic_comparison.json').write_text(json.dumps(STATE['data'],ensure_ascii=False,indent=2),encoding='utf-8')

def finish(error=None):
    if STATE.get('handle') is not None:u.unregister_slate_post_tick_callback(STATE.pop('handle'))
    data=STATE['data']
    try:
        if not error:
            source,rt,counts=sync();mid=STATE['mid'];mid.set_scalar_parameter_value('DebugMode',1);mid.set_scalar_parameter_value('RebuildHeightScale',0)
            STATE['capture'].capture_scene();pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(STATE['world'],STATE['capture_rt'],0,0,64,64,False)
            data['height_zero_control_max']=max(max(abs(c.r),abs(c.g),abs(c.b)) for c in pixels)
    except Exception as e:error=e
    finally:
        movement=STATE.get('movement')
        if movement:movement.set_movement_mode(STATE['old_mode'],STATE['old_custom'])
        if STATE.get('capture'):STATE['capture'].set_editor_property('texture_target',None)
        if STATE.get('mid'):
            STATE['mid'].set_scalar_parameter_value('RebuildHeightScale',1)
            STATE['mid'].set_scalar_parameter_value('DebugMode',0)
    data['complete']=error is None
    if error:data['error']=str(error)
    if data['complete']:
        samples=data['captures'];base=samples[0]['probes']
        changed=sum(any(abs(a-b)>1e-6 for a,b in zip(p['rgba'],base[i]['rgba'])) for i,p in enumerate(samples[-1]['probes']))
        data['changed_end_probe_count']=changed
        data['max_probe_delta_any_capture']=max(abs(p['rgba'][j]-base[i]['rgba'][j]) for s in samples for i,p in enumerate(s['probes']) for j in range(4))
        max_color=max(max(s['comparisons'][0]['max_abs_rgb']) for s in samples)
        max_normal=max(max(s['comparisons'][1]['max_abs_rgb']) for s in samples)
        max_r=max(s['comparisons'][2]['max_abs_rgb'][0] for s in samples);max_spec=max(s['comparisons'][2]['max_abs_rgb'][1] for s in samples);max_pdo=max(s['comparisons'][2]['max_abs_rgb'][2] for s in samples)
        data['max_errors']={'color':max_color,'normal':max_normal,'roughness':max_r,'specular':max_spec,'pdo':max_pdo}
        data['max_field_delta']=max(s['field']['max_delta'] for s in samples)
        data['max_field_changed_pixels']=max(s['field']['changed_pixels'] for s in samples)
        data['pass']=len(samples)>=5 and all(s['activation'] for s in samples) and data['max_field_changed_pixels']>8 and data['max_field_delta']>0.001 and max_color<0.002 and max_normal<0.01 and max(max_r,max_spec)<0.002 and max_pdo<0.05 and data['height_zero_control_max']>0.001
    write()

def tick(delta):
    try:
        w=STATE['world'];now=u.GameplayStatics.get_time_seconds(w)
        if now==STATE.get('last_time'):return
        STATE['last_time']=now;t=now-STATE['start_time'];data=STATE['data']
        a=0 if t<1 else min(1,(t-1)/4) if t<7 else max(0,1-(t-7)/4)
        requested=u.Vector(-7491.45+600*a,11187.57,STATE['pawn_z'])
        STATE['pawn'].set_actor_location(requested,False,True)
        if t-STATE['last_telemetry']>=0.2:
            STATE['last_telemetry']=t;data['trajectory'].append({'elapsed':t,'requested':vec(requested),'actual':vec(STATE['pawn'].get_actor_location())})
        if t>=STATE['next_capture']:
            data['captures'].append(capture());STATE['next_capture']+=2;write()
        if t>=13:finish()
    except Exception as e:finish(e)

def start():
    assert STATE.get('handle') is None,'Already running'
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    assert w and w.get_name()==MAP,'Start normal PIE on copied comparison map'
    actor=find_actor(w);sim=actor.get_editor_property('NinjaLiveComponent');rt=sim.get_editor_property('RT_VelocityDensity')
    assert rt and sim.get_editor_property('PawnInsideActivationBounds'),'Activate source first'
    pawn=u.GameplayStatics.get_player_pawn(w,0);movement=pawn.get_component_by_class(u.CharacterMovementComponent)
    STATE.clear();OUT.mkdir(exist_ok=True)
    STATE.update({'world':w,'sim':sim,'pawn':pawn,'movement':movement,'old_mode':movement.get_editor_property('movement_mode'),
        'old_custom':movement.get_editor_property('custom_movement_mode'),'pawn_z':pawn.get_actor_location().z,
        'last_telemetry':-1,'next_capture':0,'start_time':u.GameplayStatics.get_time_seconds(w),
        'data':{'scope':__doc__,'world':w.get_path_name(),'complete':False,'captures':[],'trajectory':[],
            'schedule':'hold1s; +X600cm in4s; hold2s; return in4s; hold2s',
            'limits':['Original solver retained','Other original scene movers remain active','No fixed timestep/random seed forced']}})
    position=sim.get_editor_property('SimulationPosition');position=u.Vector(position.x+3500,position.y,position.z)
    probe=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor) if a.get_actor_label()=='Stage4_ComparisonPlane');probe.set_actor_location(position,False,True);mesh=probe.get_component_by_class(u.StaticMeshComponent)
    mesh.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);mesh.set_editor_property('generate_overlap_events',False)
    mesh.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'));mesh.set_relative_scale3d(u.Vector(20,20,1));probe.set_actor_rotation(actor.get_actor_rotation(),True)
    mid=u.MaterialLibrary.create_dynamic_material_instance(w,u.load_asset(MATERIALS+'MI_Surface_Difference'));mesh.set_material(0,mid)
    cap_actor=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor) if a.get_actor_label()=='Stage4_Capture');cap_actor.set_actor_location(u.Vector(position.x,position.y-2050,position.z+1800),False,True);cap_actor.set_actor_rotation(u.Rotator(pitch=-41.28,yaw=90,roll=0),True)
    cap=cap_actor.get_component_by_class(u.SceneCaptureComponent2D);cap_rt=u.RenderingLibrary.create_render_target2d(w,64,64,u.TextureRenderTargetFormat.RTF_RGBA16F,u.LinearColor(0,0,0,1),False,False)
    cap.set_editor_property('texture_target',cap_rt);cap.set_editor_property('capture_every_frame',False);cap.set_editor_property('capture_on_movement',False);cap.set_editor_property('fov_angle',50)
    cap.set_editor_property('primitive_render_mode',u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST);cap.show_only_actor_components(probe)
    flags=[]
    for name in ['Fog','Atmosphere','Bloom','EyeAdaptation','TemporalAA','Tonemapper']:
        flag=u.EngineShowFlagsSetting();flag.set_editor_property('show_flag_name',name);flag.set_editor_property('enabled',False);flags.append(flag)
    cap.set_editor_property('show_flag_settings',flags)
    STATE.update({'probe_actor':probe,'capture_actor':cap_actor,'capture':cap,'capture_rt':cap_rt,'mid':mid})
    STATE['field_mid']=u.MaterialLibrary.create_dynamic_material_instance(w,u.load_asset(MATERIALS+'M_LiveRT_Probe'))
    STATE['field_rt']=u.RenderingLibrary.create_render_target2d(w,64,64,u.TextureRenderTargetFormat.RTF_RGBA16F,u.LinearColor(0,0,0,1),False,False)
    sync();movement.disable_movement();STATE['handle']=u.register_slate_post_tick_callback(tick);write()
    return {'started':True,'duration_world_seconds':13,'output':str(OUT/'dynamic_comparison.json')}
