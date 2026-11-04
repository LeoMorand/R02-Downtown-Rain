"""PIE-only demonstration. Wall-clock scheduling, native HUD, no offline stepping."""
import hashlib, json, math, time, traceback
from pathlib import Path
import unreal as u

ROOT=Path('D:/aco/unreal/Stormfall')
STAGES=[('overview',6),('thin',18),('pool',22),('color',16),('roughness',10),
        ('detail',12),('relief',12),('depth',18),('viscosity',20),('flow',9),('poolflow',6),
        ('shapes',20),('transform',16),('irregular',12),('presets',12),
        ('quality',24),('independent',10),('ending',6)]
S={}

def comp(actor,name):
    return next(c for c in actor.get_components_by_class(u.ActorComponent) if c.get_name()==name)

def val(obj,k): return obj.get_editor_property(k)
def vec(v): return [float(v.x),float(v.y),float(v.z)]
def color(c): return [float(getattr(c,k)) for k in ['r','g','b','a']]
def put(obj,**values):
    for k,v in values.items(): obj.set_editor_property(k,v)

def console(cmd): u.SystemLibrary.execute_console_command(S['editor_world'],cmd)

def camera(pos,target,fov=55):
    d=target-pos
    r=u.Rotator(pitch=math.degrees(math.atan2(d.z,math.hypot(d.x,d.y))),yaw=math.degrees(math.atan2(d.y,d.x)),roll=0)
    S['camera'].set_actor_location(pos,False,True)
    S['camera'].set_actor_rotation(r,False)
    S['cam'].set_editor_property('field_of_view',fov)

def reset_pawn(x,y,z):
    S['input'].inject_input_vector_for_action(S['move'],u.Vector(),[],[])
    S['movement'].stop_movement_immediately()
    S['pawn'].set_actor_location(u.Vector(x,y,z),False,True)
    S['pawn'].set_actor_rotation(u.Rotator(),True)
    S['pc'].set_control_rotation(u.Rotator())

def default_controls():
    c=S['artist']; m=S['thin_ctrl']
    put(c,layer_depth_cm=80,surface_relief_cm=20,viscosity_feel=.5,enable_movement_drag=False,
        light_color=u.LinearColor(*S['colors'][0]),dark_color=u.LinearColor(*S['colors'][1]),
        brightness=.25,roughness=.1,detail_strength=.6,detail_density=1,detail_flow_multiplier=1,
        display_quality=u.MudDisplayQuality.HIGH2048)
    put(m,thickness_cm=20,light_color=u.LinearColor(*S['colors'][0]),dark_color=u.LinearColor(*S['colors'][1]),
        brightness=.25,roughness=.1,detail_strength=.6,detail_density=1,enable_detail_flow=True,flow_speed=1,
        region_shape=u.MudRegionShape.FULL_PLANE,region_size_cm=u.Vector2D(1600,1300),
        region_offset_cm=u.Vector2D(),region_rotation_degrees=0,corner_roundness=.2,irregularity=.2,shape_seed=3)
    m.apply_appearance(); c.apply_artist_controls()

def start(input_path,out):
    assert not S.get('handle')
    assert 'FluidNinjaStudy' in u.Paths.get_project_file_path()
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem); world=ed.get_game_world()
    assert world and 'UEDPIE_' in world.get_path_name() and 'L_Mud_SurfaceAndPool' in world.get_path_name()
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    pawn=u.GameplayStatics.get_player_pawn(world,0)
    c=comp(actors['Mud_DeepPool'],'ArtistControls')
    out=Path(out).resolve(); assert out.is_relative_to(ROOT/'Verification/MudProfessional/phase17-runtime')
    out.mkdir(parents=True,exist_ok=True)
    settings=u.get_default_object(u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
    before={k:u.SystemLibrary.get_console_variable_float_value(k) for k in
            ['t.OverrideFPS','t.MaxFPS','Slate.bAllowThrottling','r.ScreenPercentage']}
    S.clear(); S.update(world=world,editor_world=ed.get_editor_world(),out=out,pawn=pawn,
        pc=u.GameplayStatics.get_player_controller(world,0),input=u.find_object(None,input_path),
        move=u.load_asset('/Game/FluidNinjaLive/Meshes/Mannequin/Input/IA_Walk'),
        jump=u.load_asset('/Game/FluidNinjaLive/Meshes/Mannequin/Input/IA_Jump'),
        movement=pawn.get_component_by_class(u.CharacterMovementComponent),
        pool=actors['Mud_DeepPool'],thin=actors['Mud_ThinSurface'],artist=c,
        thin_ctrl=comp(actors['Mud_ThinSurface'],'MudControls'),settings=settings,
        before=before,background_before=val(settings,'bThrottleCPUWhenNotForeground'),
        samples=[],events=[],index=-1,last_sample=-10,last_variant=None,complete=False,
        started=time.monotonic(),game_start=u.GameplayStatics.get_time_seconds(world),
        colors=tuple(tuple(color(val(c,k))) for k in ['light_color','dark_color']))
    assert S['input']
    settings.set_editor_property('bThrottleCPUWhenNotForeground',False)
    for cmd in ['t.OverrideFPS 0','t.MaxFPS 0','Slate.bAllowThrottling 0','r.ScreenPercentage 100']:
        console(cmd)
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.TextRenderActor): actor.set_actor_hidden_in_game(True)
    capture=actors.get('Mud_Replay_Capture')
    if capture:
        cc=capture.get_component_by_class(u.SceneCaptureComponent2D)
        put(cc,capture_every_frame=False,capture_on_movement=False,texture_target=None)
    ca=u.find_object(None,world.get_path_name()+':PersistentLevel.CameraActor_0')
    assert ca, 'Spawn a PIE CameraActor with the native reflection tool first'
    cam=ca.get_component_by_class(u.CameraComponent)
    pp=val(cam,'post_process_settings')
    for k,v in [('override_auto_exposure_method',True),('auto_exposure_method',u.AutoExposureMethod.AEM_MANUAL),
                ('override_auto_exposure_bias',True),('auto_exposure_bias',.75),
                ('override_auto_exposure_apply_physical_camera_exposure',True),('auto_exposure_apply_physical_camera_exposure',False),
                ('override_motion_blur_amount',True),('motion_blur_amount',.15)]: pp.set_editor_property(k,v)
    put(cam,post_process_settings=pp,post_process_blend_weight=1,constrain_aspect_ratio=False)
    S.update(camera=ca,cam=cam)
    S['pc'].set_view_target_with_blend(ca,0)
    default_controls(); reset_pawn(-2700,0,93)
    camera(u.Vector(0,6500,6500),u.Vector(0,0,0),70)
    u.GameplayStatics.set_game_paused(world,False)
    S['armed']=False
    S['handle']=u.register_slate_post_tick_callback(tick)
    save()
    return {'ready':True,'seconds':sum(d for _,d in STAGES),'stages':STAGES}

def arm():
    S.update(armed=True,started=time.monotonic(),game_start=u.GameplayStatics.get_time_seconds(S['world']))
    (S['out']/'timeline_start.json').write_text(json.dumps({'monotonic':S['started'],'seconds':sum(d for _,d in STAGES)}))
    return {'started':True}

def begin_stage(index,name):
    S.update(index=index,name=name,last_variant=None)
    default_controls()
    reset_pawn(-2700,0,93) if name in ['thin','flow','shapes','transform','irregular','presets','independent'] else reset_pawn(2100,-100,12.2)
    if name=='pool': reset_pawn(950,0,94)
    S['events'].append({'stage':name,'wall':time.monotonic()-S['started'],'game':u.GameplayStatics.get_time_seconds(S['world'])-S['game_start']})

def variant(key,fn):
    if S['last_variant']!=key:
        fn(); S['last_variant']=key
        S['events'].append({'stage':S['name'],'variant':str(key),'wall':time.monotonic()-S['started']})

def apply_stage(name,t):
    c=S['artist']; m=S['thin_ctrl']; move=u.Vector(); pawn=S['pawn']; pos=pawn.get_actor_location()
    pool_stage=name in ['color','roughness','detail','relief','depth','viscosity','quality','poolflow']
    if name in ['overview','ending']:
        camera(u.Vector(0,6500,6500),u.Vector(0,0,0),70)
    elif name=='thin':
        if 1<t<4: move=u.Vector(0,.5,0)
        elif 4<t<7: move=u.Vector(.5,0,0)
        elif 7<t<10: move=u.Vector(0,-.5,0)
        elif 12<t<15: move=u.Vector(-.5,0,0)
        S['input'].inject_input_vector_for_action(S['jump'],u.Vector(1 if 10.5<t<10.7 else 0,0,0),[],[])
        camera(pos+u.Vector(-500,410,245),pos+u.Vector(0,0,5),60)
    elif name=='pool':
        if 1<t<10: move=u.Vector(0,.5,0)
        elif 12<t<21: move=u.Vector(0,-.5,0)
        camera(pos+u.Vector(-540,430,240),pos+u.Vector(0,0,30),60)
    elif pool_stage:
        camera(u.Vector(1560,720,430),u.Vector(2200,0,0),60)
        # Moving target on a small loop keeps the real leg inputs active in view.
        if name not in ['depth','relief']:
            goal=u.Vector(2200+190*math.sin(t*.6),100*math.cos(t*.6),0)
            dx=goal.x-pos.x; dy=goal.y-pos.y; length=max(1,math.hypot(dx,dy))
            move=u.Vector(dy/length*.38,dx/length*.38,0) if length>35 else u.Vector()
        if name=='color':
            k=min(3,int(t/4))
            def colors():
                pairs=[S['colors'],((.035,.12,.065,1),(.008,.028,.014,1)),((.28,.11,.035,1),(.07,.018,.006,1)),S['colors']]
                pair=pairs[k]; put(c,light_color=u.LinearColor(*pair[0]),dark_color=u.LinearColor(*pair[1]),brightness=[.25,.25,.25,.55][k])
            variant(k,colors)
        elif name=='roughness':
            k=min(2,int(t/3.33)); variant(k,lambda:put(c,roughness=[.03,.85,.1][k]))
        elif name=='detail':
            k=min(3,int(t/3)); variant(k,lambda:put(c,detail_strength=[0,1.4,1.4,.6][k],detail_density=[1,1,4,1][k]))
        elif name=='relief':
            k=min(2,int(t/4)); variant(k,lambda:put(c,surface_relief_cm=[0,20,40][k]))
            move=u.Vector(.28*math.cos(t),.28*math.sin(t),0)
            camera(u.Vector(1670,580,210),u.Vector(2200,0,-5),60)
        elif name=='depth':
            k=min(2,int(t/6))
            def depth():
                [c.preset_shallow,c.preset_knee_deep,c.preset_leg_deep][k]()
                reset_pawn(2200,0,94-[5,50,90][k])
            variant(k,depth)
            move=u.Vector(.22*math.cos(t),.22*math.sin(t),0)
        elif name=='viscosity':
            k=min(3,int(t/5))
            def visc():
                put(c,viscosity_feel=[0,1,0,1][k],enable_movement_drag=k>=2)
                reset_pawn(1800,-100,12.2)
            variant(k,visc); move=u.Vector(0,.35,0) if t%5<3.5 else u.Vector()
            camera(u.Vector(2200,1150,650),u.Vector(2200,0,0),65)
        elif name=='poolflow':
            k=min(1,int(t/3)); variant(k,lambda:put(c,detail_flow_multiplier=[0,3][k]))
        elif name=='quality':
            k=min(2,int(t/8)); variant(k,lambda:put(c,display_quality=[u.MudDisplayQuality.PREVIEW512,u.MudDisplayQuality.STANDARD1024,u.MudDisplayQuality.HIGH2048][k]))
    else:
        camera(u.Vector(-2200,2300,2500),u.Vector(-2200,0,0),65)
        move=u.Vector(.24*math.cos(t*.8),.24*math.sin(t*.8),0)
        if name=='flow':
            k=min(2,int(t/3)); variant(k,lambda:put(m,enable_detail_flow=k>0,flow_speed=[0,.3,3][k]))
            camera(u.Vector(-2670,580,240),u.Vector(-2200,0,0),65)
        elif name=='shapes':
            k=min(3,int(t/5)); variant(k,lambda:put(m,region_shape=list(u.MudRegionShape)[k]))
        elif name=='transform':
            k=min(3,int(t/4))
            variant(k,lambda:put(m,region_shape=u.MudRegionShape.RECTANGLE,
                region_size_cm=u.Vector2D(*[(1500,800),(900,1500),(900,1500),(1300,1000)][k]),
                region_offset_cm=u.Vector2D(*[(0,0),(0,0),(300,-150),(0,0)][k]),
                region_rotation_degrees=[0,0,35,-30][k],corner_roundness=[0,0,.15,1][k]))
        elif name=='irregular':
            k=min(2,int(t/4)); variant(k,lambda:put(m,region_shape=u.MudRegionShape.IRREGULAR,irregularity=[0,.45,.45][k],shape_seed=[3,3,17][k]))
        elif name=='presets':
            k=min(2,int(t/4)); variant(k,lambda:m.call_method(['PresetThinWet','PresetThickRough','ResetAppearance'][k]))
        elif name=='independent':
            k=min(1,int(t/5))
            variant(k,lambda:put(m,light_color=u.LinearColor(.05,.18,.1,1),dark_color=u.LinearColor(.01,.035,.018,1),brightness=.4))
            camera(u.Vector(0,6500,6500),u.Vector(0,0,0),70)
    S['input'].inject_input_vector_for_action(S['move'],move,[],[])

def hud_and_sample(elapsed,name):
    c=S['artist']; thin=name in ['thin','flow','shapes','transform','irregular','presets','independent']
    m=S['thin_ctrl'] if thin else c
    actor=S['thin'] if thin else S['pool']
    rt=val(actor,'output'); normal=val(val(actor,'normal_pass'),'normal_output')
    lines=[('薄层' if thin else '深池')+'  |  输出 %d × %d  |  法线 %d × %d'%(rt.size_x,rt.size_y,normal.size_x,normal.size_y),
           '厚度 / 实际起伏 %.1f cm'%(val(m,'thickness_cm') if thin else val(c,'applied_relief_cm')),
           '粗糙度 %.2f  |  细节 %.2f  |  密度 %.2f'%(val(m,'roughness'),val(m,'detail_strength'),val(m,'detail_density'))]
    if not thin: lines+=['池深 %.1f cm  |  黏稠感 %.2f'%(val(c,'layer_depth_cm'),val(c,'viscosity_feel')),
        '行走阻力 '+('开启' if val(c,'enable_movement_drag') else '关闭')+'  |  移动倍率 %.2f'%val(c,'applied_movement_multiplier'),
        '模拟速度 %.2f  |  速度保留 %.2f'%(val(c,'applied_sim_speed'),val(c,'applied_velocity_feedback')),
        '细节流动倍率 %.2f  |  腿部输入 %d'%(val(c,'detail_flow_multiplier'),val(c,'active_leg_inputs'))]
    else:
        shape=['完整平面','圆角矩形','椭圆','不规则泥潭'][val(m,'region_shape').value]
        size=val(m,'region_size_cm'); off=val(m,'region_offset_cm')
        lines+=['细节流动 '+('开启' if val(m,'enable_detail_flow') else '关闭')+'  |  速度 %.2f'%val(m,'flow_speed'),
                '轮廓 '+shape+'  |  宽高 %.0f × %.0f cm'%(size.x,size.y),
                '偏移 %.0f, %.0f cm  |  旋转 %.0f°'%(off.x,off.y,val(m,'region_rotation_degrees')),
                '圆角 %.2f  |  不规则 %.2f  |  种子 %d'%(val(m,'corner_roundness'),val(m,'irregularity'),val(m,'shape_seed'))]
    rgb=color(val(m,'light_color'))[:3]; dark=color(val(m,'dark_color'))[:3]
    lines+=['浅色 %.3f, %.3f, %.3f'%tuple(rgb),'深色 %.3f, %.3f, %.3f'%tuple(dark),
            '亮度 %.2f  |  内部主网格 2048'%val(m,'brightness')]
    u.SystemLibrary.print_string(S['world'],'\n'.join(lines)+'\n'*30,True,False,u.LinearColor(.93,1,.96,1),.6,'MudRuntimeValues')
    record={'wall_seconds':elapsed,'game_seconds':u.GameplayStatics.get_time_seconds(S['world'])-S['game_start'],
            'stage':name,'thin':thin,'position':vec(S['pawn'].get_actor_location()),
            'velocity':vec(S['pawn'].get_velocity()),'falling':S['movement'].is_falling(),
            'light':rgb,'dark':dark,'brightness':val(m,'brightness'),'roughness':val(m,'roughness'),
            'detail_strength':val(m,'detail_strength'),'detail_density':val(m,'detail_density'),
            'depth':val(c,'layer_depth_cm'),'relief':val(c,'applied_relief_cm'),'viscosity':val(c,'viscosity_feel'),
            'drag':val(c,'enable_movement_drag'),'walk_speed':val(S['movement'],'max_walk_speed'),
            'flow':val(S['thin_ctrl'],'enable_detail_flow'),'flow_speed':val(S['thin_ctrl'],'flow_speed'),
            'detail_flow_multiplier':val(c,'detail_flow_multiplier'),'thin_thickness':val(S['thin_ctrl'],'thickness_cm'),
            'shape':str(val(S['thin_ctrl'],'region_shape')),'size':[val(S['thin_ctrl'],'region_size_cm').x,val(S['thin_ctrl'],'region_size_cm').y],
            'offset':[val(S['thin_ctrl'],'region_offset_cm').x,val(S['thin_ctrl'],'region_offset_cm').y],
            'rotation':val(S['thin_ctrl'],'region_rotation_degrees'),'roundness':val(S['thin_ctrl'],'corner_roundness'),
            'irregularity':val(S['thin_ctrl'],'irregularity'),'seed':val(S['thin_ctrl'],'shape_seed'),
            'output_size':rt.size_x,'normal_size':normal.size_x,'active_legs':val(c,'active_leg_inputs'),
            'override_fps':u.SystemLibrary.get_console_variable_float_value('t.OverrideFPS')}
    S['samples'].append(record)

def save(error=None):
    result={k:S.get(k) for k in ['events','samples','before','background_before','complete','restored']}
    result.update(error=error,stages=STAGES,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Real-time PIE, window-only WGC; native UE stat fps/unit. No offline stepping, titles or simulated performance metrics.')
    (S['out']/'run.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')

def finish(error=None):
    handle=S.pop('handle',None)
    if handle: u.unregister_slate_post_tick_callback(handle)
    S['input'].inject_input_vector_for_action(S['move'],u.Vector(),[],[])
    S['input'].inject_input_vector_for_action(S['jump'],u.Vector(),[],[])
    S['complete']=not error
    (S['out']/'timeline_end.json').write_text(json.dumps({'monotonic':time.monotonic(),'error':error}))
    # Leave the final frame visible until external encoder is stopped.
    save(error)

def restore():
    if S.get('handle'): finish('Stopped before timeline completion')
    for k,v in S['before'].items(): console(k+' '+str(v))
    S['settings'].set_editor_property('bThrottleCPUWhenNotForeground',S['background_before'])
    S['restored']=True; save()

def tick(dt):
    try:
        if not S.get('armed'):
            if time.monotonic()-S.get('last_hud',0)>.2:
                hud_and_sample(0,'overview'); S['last_hud']=time.monotonic()
            return
        elapsed=time.monotonic()-S['started']; boundary=0
        for index,(name,duration) in enumerate(STAGES):
            if elapsed<boundary+duration: break
            boundary+=duration
        else: finish(); return
        if index!=S['index']: begin_stage(index,name)
        apply_stage(name,elapsed-boundary)
        if elapsed-S['last_sample']>=.2:
            hud_and_sample(elapsed,name); S['last_sample']=elapsed
            if elapsed-S.get('last_save',-10)>=3:
                save(); S['last_save']=elapsed
    except Exception: finish(traceback.format_exc())
