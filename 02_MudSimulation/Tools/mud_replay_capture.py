"""Research-only instrumentation for the native Phase05 Sequencer replay.

Does not author the path, edit solver/material assets, or benchmark performance.
All temporary process settings and capture actors are restored on completion.
"""
import hashlib
import json
import math
import shutil
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
import unreal as u
import research_window

MAP = '/Game/MudStudy/Professional/Phase05/L_Mud_Replay'
OUT = Path('D:/aco/unreal/Stormfall/Verification/MudProfessional/phase05-replay')
POINTS = [(0,-600,-250),(3,-600,-250),(9,0,-250),(12,300,0),(15,450,300),
          (18,450,300),(24,0,500),(30,-500,250),(36,-600,-250),(42,-600,-250),
          (48,1150,-250),(52,800,-250),(60,800,-250)]
STATE = {}


def expected(seconds):
    for a, b in zip(POINTS, POINTS[1:]):
        if seconds <= b[0]:
            f = max(0, min(1, (seconds-a[0])/(b[0]-a[0])))
            return [a[1]+f*(b[1]-a[1]), a[2]+f*(b[2]-a[2]), 20]
    return [800, -250, 20]


def sequence_time(player):
    q = player.get_current_time()
    return (q.time.frame_number.value + q.time.sub_frame) * q.rate.denominator / q.rate.numerator


def _save(complete=False, error=None):
    report = {k: STATE.get(k) for k in ['map','source_sha256','trajectory','samples','frames','gpu_samples',
              'settings_before','settings_restored','window_before','capture_settings','contact_contract','evidence','wall_start_utc','elapsed_wall_seconds']}
    report.update(complete=complete, error=error,
                  scope='Instrumented native replay and capture; not a GPU performance benchmark or reference equivalence')
    (STATE['out']/'run.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


def _finish(error=None):
    handle = STATE.pop('handle', None)
    if handle:
        u.unregister_slate_post_tick_callback(handle)
    cleanup_errors = []
    capture = STATE.pop('capture', None)
    if capture:
        try:
            capture.destroy_actor()
        except Exception as exc:
            cleanup_errors.append(str(exc))
    try:
        STATE['settings'].set_editor_property('bThrottleCPUWhenNotForeground', STATE['settings_before']['background_throttle'])
        u.SystemLibrary.execute_console_command(STATE['editor_world'], 't.MaxFPS '+str(STATE['settings_before']['max_fps']))
        u.SystemLibrary.execute_console_command(STATE['editor_world'], 't.OverrideFPS '+str(STATE['settings_before']['override_fps']))
    except Exception as exc:
        cleanup_errors.append(str(exc))
    try:
        research_window.restore_previous()
    except Exception as exc:
        cleanup_errors.append(str(exc))
    STATE['settings_restored'] = not cleanup_errors
    STATE['elapsed_wall_seconds'] = time.monotonic()-STATE['wall_start']
    _save(True, error or ('; '.join(cleanup_errors) if cleanup_errors else None))
    u.EditorLevelLibrary.editor_end_play()
    u.log('MUD_REPLAY_FINISHED '+str(STATE['out']))


def stop():
    if STATE.get('handle'):
        _finish('Stopped by caller')


def start(width=640, height=360, frame_interval=.1, duration=64, output_group='phase05-replay', fixed_fps=0,
          map_path=MAP, exposure_bias=0, camera_mode='wide', detail_flow=None, capture_evidence=False):
    assert not STATE.get('handle'), 'Capture already running'
    assert Path(u.Paths.project_dir()).resolve().name == 'FluidNinjaStudy', 'Wrong project'
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    assert not editor.get_game_world(), 'End PIE before capture'
    world = editor.get_editor_world()
    assert map_path in [MAP,'/Game/MudStudy/Professional/Phase06/L_Mud_Showcase',
                        '/Game/MudStudy/Professional/Phase07/L_Mud_Contact',
                        '/Game/MudStudy/Professional/Phase08/L_Mud_Controlled',
                        '/Game/MudStudy/Professional/Phase09/L_Mud_Portfolio']
    assert world.get_path_name().startswith(map_path+'.'), 'Open dedicated replay/showcase map'
    assert camera_mode in ['wide','showcase','showcase_short','contact_only']
    assert output_group in ['phase05-replay','phase06-capture','phase07-contact','phase09-delivery']
    assert 1/60 <= frame_interval <= 1 and 1 <= duration <= 120
    out = OUT.parent / output_group / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    (out/'frames').mkdir(parents=True, exist_ok=False)
    settings_class = u.load_class(None, '/Script/UnrealEd.EditorPerformanceSettings')
    assert settings_class, 'EditorPerformanceSettings class not loaded'
    settings = u.get_default_object(settings_class)
    before = dict(background_throttle=settings.get_editor_property('bThrottleCPUWhenNotForeground'),
                  max_fps=u.SystemLibrary.get_console_variable_float_value('t.MaxFPS'),
                  override_fps=u.SystemLibrary.get_console_variable_float_value('t.OverrideFPS'))
    STATE.clear()
    STATE.update(out=out, map=map_path, editor_world=world, settings=settings, settings_before=before,
                 settings_restored=False, wall_start=time.monotonic(),
                 wall_start_utc=datetime.now(timezone.utc).isoformat(),
                 source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 trajectory=POINTS, samples=[], frames=[], gpu_samples=[], evidence=[], next_frame=0,
                 requested_flow=detail_flow, capture_evidence=capture_evidence,
                 frame_interval=frame_interval,duration=duration,
                 next_sample=0, next_gpu=0, next_boundary=0, capture_settings=dict(width=width,height=height,fov=55,
                 output_format='JPG 95 via asynchronous ImageWriteQueue',target_capture_hz=1/frame_interval,
                 fixed_fps=fixed_fps,clock_mode='fixed-step offline capture; not realtime FPS' if fixed_fps else 'realtime game clock',
                 exposure_bias=exposure_bias,camera_mode=camera_mode,
                 main_viewport='temporarily Wireframe, realtime off; capture retains independent Lit flags',
                 location=[0,1250,600],rotation=[-28,-90,0],
                 exposure='Manual exposure, bias=%g, physical camera exposure off'%exposure_bias,
                 duration_game_seconds=duration))
    try:
        if research_window._saved is not None:
            STATE['window_before'] = dict(research_window._saved)
        else:
            STATE['window_before'] = research_window.restore_for_capture()
        shutil.copy2(__file__,out/'harness.py')
        shutil.copy2(research_window.__file__,out/'research_window.py')
        settings.set_editor_property('bThrottleCPUWhenNotForeground', False)
        u.SystemLibrary.execute_console_command(world, 't.MaxFPS 60')
        if fixed_fps:
            u.SystemLibrary.execute_console_command(world, 't.OverrideFPS '+str(fixed_fps))
        _save()
        u.EditorLevelLibrary.editor_play_simulate()
        STATE['handle'] = u.register_slate_post_tick_callback(_tick)
    except Exception:
        _finish(traceback.format_exc())
        raise
    return dict(scheduled=True, output=str(out), duration_game_seconds=duration)


def _setup(world):
    actors = u.GameplayStatics.get_all_actors_of_class(world, u.Actor)
    by_label = {a.get_actor_label():a for a in actors}
    STATE['mud'] = by_label['Integrated_Mud_GlobalNormal']
    STATE['brush'] = by_label['Integrated_Brush']
    STATE['controller'] = by_label['Mud_Replay_Controller']
    controls = next((c for c in STATE['mud'].get_components_by_class(u.ActorComponent)
                     if c.get_name()=='ProfessionalControls'),None)
    STATE['controls']=controls
    if STATE['requested_flow'] is not None:
        assert controls, 'Flow comparison requires the central controller'
        controls.set_editor_property('detail_flow_enabled',STATE['requested_flow'])
        assert controls.apply_parameters()
    if any(stage in STATE['map'] for stage in ['/Phase07/','/Phase08/','/Phase09/']):
        proxy = STATE['mud'].get_editor_property('normal_preview')
        mid = proxy.get_material(0)
        assert mid.get_name().startswith(('MID_M_Sphere_Contact','MID_M_Sphere_Portfolio')), 'Wrong contact material'
        STATE['contact_mid'] = mid
        STATE['contact_contract'] = dict(
            material=mid.get_path_name(), radius_cm=mid.get_scalar_parameter_value('ContactRadiusCm'),
            height_cm=mid.get_scalar_parameter_value('ContactHeightCm'),
            enabled=mid.get_scalar_parameter_value('ContactEnabled'),
            detail_flow_enabled=controls.get_editor_property('detail_flow_enabled') if controls else None,
            edge_blend_radius_multiplier=4 if mid.get_name().startswith('MID_M_Sphere_Portfolio') else 0,
            root_z_cm=20, correction='GPU WPO on visual proxy only; collision/input root unchanged')
    actor = by_label['Mud_Replay_Capture']
    STATE['capture'] = actor
    comp = actor.get_component_by_class(u.SceneCaptureComponent2D)
    rt = u.RenderingLibrary.create_render_target2d(world,STATE['capture_settings']['width'],STATE['capture_settings']['height'],u.TextureRenderTargetFormat.RTF_RGBA8,
                                                   u.LinearColor(0,0,0,1),False,False)
    comp.set_editor_property('texture_target',rt)
    comp.set_editor_property('capture_source',u.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    comp.set_editor_property('capture_every_frame',False)
    comp.set_editor_property('capture_on_movement',False)
    comp.set_editor_property('fov_angle',55)
    pp = comp.get_editor_property('post_process_settings')
    for name, value in [('override_auto_exposure_method',True),('auto_exposure_method',u.AutoExposureMethod.AEM_MANUAL),
                        ('override_auto_exposure_bias',True),('auto_exposure_bias',STATE['capture_settings']['exposure_bias']),
                        ('override_auto_exposure_apply_physical_camera_exposure',True),('auto_exposure_apply_physical_camera_exposure',False)]:
        pp.set_editor_property(name,value)
    comp.set_editor_property('post_process_settings',pp)
    comp.set_editor_property('post_process_blend_weight',1)
    comp.set_editor_property('bAlwaysPersistRenderingState',True)
    options = u.ImageWriteOptions()
    options.set_editor_property('format',u.DesiredImageFormat.JPG)
    options.set_editor_property('compression_quality',95)
    options.set_editor_property('overwrite_file',False)
    options.set_editor_property('bAsync',True)
    STATE.update(capture_component=comp, capture_rt=rt,image_options=options)


def _frames_finished():
    for frame in STATE['frames']:
        path = STATE['out']/frame['file']
        if not path.is_file() or path.stat().st_size<4:
            return False
        with path.open('rb') as stream:
            if stream.read(2)!=b'\xff\xd8':
                return False
            stream.seek(-2,2)
            if stream.read(2)!=b'\xff\xd9':
                return False
    return True


def _camera(seconds, location, mode_override=None):
    mode = mode_override or STATE['capture_settings']['camera_mode']
    short = mode=='showcase_short'
    if mode=='contact_only':
        shot='contact'; position=location+u.Vector(100,300,130)
        rotation=u.Rotator(pitch=math.degrees(math.atan2(-140,math.hypot(100,300))),
                           yaw=math.degrees(math.atan2(-300,-100)),roll=0)
    elif mode=='wide' or seconds<(8 if short else 16):
        shot='wide'; position=u.Vector(0,1250,600); rotation=u.Rotator(pitch=-28,yaw=-90,roll=0)
    elif seconds<(16 if short else 38):
        shot='contact'; offset=u.Vector(100,300,130); position=location+offset
        rotation=u.Rotator(pitch=math.degrees(math.atan2(-140,math.hypot(100,300))),
                           yaw=math.degrees(math.atan2(-300,-100)),roll=0)
    elif not short and seconds<52:
        shot='boundary'; position=u.Vector(0,1800,1000); rotation=u.Rotator(pitch=-29,yaw=-90,roll=0)
    else:
        shot='grazing'; offset=u.Vector(160,360,100); position=location+offset
        rotation=u.Rotator(pitch=math.degrees(math.atan2(-110,math.hypot(160,360))),
                           yaw=math.degrees(math.atan2(-360,-160)),roll=0)
    if STATE.get('shot')!=shot:
        STATE['capture_component'].set_editor_property('bCameraCutThisFrame',True)
        STATE['shot']=shot
    STATE['capture'].set_actor_location(position,False,True)
    STATE['capture'].set_actor_rotation(rotation,False)
    return dict(shot=shot,location=[position.x,position.y,position.z],rotation=[rotation.pitch,rotation.yaw,rotation.roll])


def _contact_prediction(pixels, x, y, location):
    """CPU prediction from RT samples, not a GPU WPO position readback."""
    uv=(location.x/2000+.5,location.y/2000+.5)
    inside=all(0<=v<=1 for v in uv)
    if not inside:
        return dict(domain_inside=False,predicted_visual_z_cm=location.z,predicted_offset_z_cm=0)
    mid=STATE['contact_mid']
    radius=mid.get_scalar_parameter_value('ContactRadiusCm')
    height=mid.get_scalar_parameter_value('ContactHeightCm')
    assert abs(radius-20)<.001 and abs(height-20)<.001, 'Prediction is scoped to this preset'
    def sample(p):
        px=max(0,min(511,p[0]*512-.5)); py=max(0,min(511,p[1]*512-.5))
        ix,iy=math.floor(px),math.floor(py); fx,fy=px-ix,py-iy
        rows=[]
        for dy in (0,1):
            for dx in (0,1):
                sx,sy=min(511,ix+dx)-x,min(511,iy+dy)-y
                assert 0<=sx<16 and 0<=sy<16, 'Support sample outside saved patch'
                v=pixels[sy*16+sx]
                rows.append(((fx if dx else 1-fx)*(fy if dy else 1-fy),(v.r,v.g,v.b,v.a)))
        return [sum(w*v[k] for w,v in rows) for k in range(4)]
    center=sample(uv); support=(center[3]-1)*height+radius
    n=[2*v-1 for v in center[:3]]; length=math.sqrt(sum(v*v for v in n))
    if length>1e-6:
        n=[v/length for v in n]
        probe=(uv[0]-radius*n[0]/2000,uv[1]-radius*n[1]/2000)
        if n[2]>0 and all(0<=v<=1 for v in probe):
            support=max(support,(sample(probe)[3]-1)*height+radius*n[2])
    for ring in range(1,5):
        r=radius*ring*.25; cap=math.sqrt(max(radius*radius-r*r,0))
        for i in range(16):
            a=i*math.tau/16
            probe=(uv[0]+r*math.cos(a)/2000,uv[1]+r*math.sin(a)/2000)
            if all(0<=v<=1 for v in probe):
                support=max(support,(sample(probe)[3]-1)*height+cap)
    blend=STATE['contact_contract'].get('edge_blend_radius_multiplier',0)
    if blend:
        edge_cm=min(uv[0],uv[1],1-uv[0],1-uv[1])*2000
        t=max(0,min(1,edge_cm/(radius*blend)))
        support=location.z+(support-location.z)*t*t*(3-2*t)
    return dict(domain_inside=True,predicted_visual_z_cm=support,predicted_offset_z_cm=support-location.z)


def _evidence_tick(world, seconds, location):
    stages=[('contact_off',False,True),('contact_on',True,True),
            ('flow_static',True,False),('flow_advected',True,True)]
    stage=STATE['evidence_stage']; controls=STATE['controls']
    if stage>=len(stages):
        controls.set_editor_property('contact_enabled',STATE['evidence_before'][0])
        controls.set_editor_property('detail_flow_enabled',STATE['evidence_before'][1])
        assert controls.apply_parameters()
        STATE.pop('evidence_stage'); STATE['evidence_done']=True
        u.GameplayStatics.set_game_paused(world,False); _save()
        return
    name,contact,flow=stages[stage]
    if STATE['evidence_wait']==0:
        controls.set_editor_property('contact_enabled',contact)
        controls.set_editor_property('detail_flow_enabled',flow)
        assert controls.apply_parameters()
        STATE['shot']=None
    camera=_camera(seconds,location,'contact_only')
    STATE['capture_component'].capture_scene()
    STATE['evidence_wait']+=1
    if STATE['evidence_wait']<4:
        return
    filename='evidence/'+name+'.jpg'
    (STATE['out']/'evidence').mkdir(exist_ok=True)
    u.ImageWriteBlueprintLibrary.export_to_disk(STATE['capture_rt'],str(STATE['out']/filename),STATE['image_options'])
    STATE['evidence'].append(dict(name=name,file=filename,sequence_seconds=seconds,
        game_seconds=u.GameplayStatics.get_time_seconds(world),camera=camera,
        contact_enabled=contact,detail_flow_enabled=flow,
        scope='Frozen state, same camera; captured after three settling renders'))
    STATE['evidence_stage']+=1; STATE['evidence_wait']=0


def _gpu_sample(world, seconds, location):
    mud = STATE['mud']
    output = mud.get_editor_property('output')
    normal_pass = mud.get_editor_property('normal_pass')
    normal = normal_pass.get_editor_property('normal_output')
    x = max(0,min(496,int((location.x/2000+.5)*512)-8))
    y = max(0,min(496,int((location.y/2000+.5)*512)-8))
    # UE 5.8 forwards the arguments named MaxX/MaxY as WIDTH/HEIGHT to
    # ReadRenderTargetHelper. Keep this version-specific quirk explicit.
    source = u.RenderingLibrary.read_render_target_raw_pixel_area(world,output,x,y,16,16,False)
    derived = u.RenderingLibrary.read_render_target_raw_pixel_area(world,normal,x,y,16,16,False)
    assert len(source) == len(derived) == 256
    finite = all(math.isfinite(v) for row in source+derived for v in (row.r,row.g,row.b,row.a))
    error = max(abs(a.b-b.a) for a,b in zip(source,derived))
    contact = STATE.get('contact_mid')
    STATE['gpu_samples'].append(dict(sequence_seconds=seconds,rect=[x,y,x+16,y+16],pixels=len(source),
        finite=finite, max_abs_velocity=max(max(abs(p.r),abs(p.g)) for p in source),
        B_min=min(p.b for p in source),B_max=max(p.b for p in source),height_copy_error=error,
        material_normal_bound=mud.get_editor_property('surface_mid').get_texture_parameter_value('MudNormalBuffer') == normal,
        normal_dispatches=normal_pass.get_editor_property('producer_graph_dispatches'),
        contact_normal_bound=contact.get_texture_parameter_value('MudNormalBuffer') == normal if contact else None,
        contact_prediction=_contact_prediction(derived,x,y,location) if contact else None))


def _tick(dt):
    try:
        if time.monotonic()-STATE['wall_start'] > 900:
            raise RuntimeError('Capture exceeded wall-clock timeout')
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if not world:
            if STATE.get('mud'):
                raise RuntimeError('PIE ended before capture completed')
            return
        if not STATE.get('mud'):
            _setup(world)
        mud, brush = STATE['mud'], STATE['brush']
        player = STATE['controller'].get_editor_property('sequence_player')
        seconds = sequence_time(player)
        game_seconds = u.GameplayStatics.get_time_seconds(world)
        if 'evidence_stage' in STATE:
            _evidence_tick(world,seconds,brush.get_actor_location())
            return
        if STATE.get('recording_finished'):
            if _frames_finished():
                _finish()
            return
        location = brush.get_actor_location()
        if game_seconds >= STATE['next_sample']:
            inputs = u.NiagaraDataInterfaceArrayFunctionLibrary.get_niagara_array_vector4(mud.get_editor_property('simulation'),'User.BrushWorldPositions')
            wanted = expected(seconds)
            STATE['samples'].append(dict(game_seconds=game_seconds,sequence_seconds=seconds,
                location=[location.x,location.y,location.z],expected=wanted,
                path_error_cm=math.sqrt(sum((a-b)**2 for a,b in zip([location.x,location.y,location.z],wanted))),
                input_count=len(inputs), playing=player.is_playing()))
            STATE['next_sample'] = game_seconds+.1
        if game_seconds+1e-6 >= STATE['next_frame']:
            index = len(STATE['frames'])
            filename = 'frame_%06d.jpg'%index
            enqueue_start=time.perf_counter()
            camera=_camera(seconds,location)
            STATE['capture_component'].capture_scene()
            u.ImageWriteBlueprintLibrary.export_to_disk(STATE['capture_rt'],str(STATE['out']/'frames'/filename),STATE['image_options'])
            STATE['frames'].append(dict(file='frames/'+filename,game_seconds=game_seconds,sequence_seconds=seconds,
                                        enqueue_cpu_ms=(time.perf_counter()-enqueue_start)*1000,camera=camera))
            STATE['next_frame'] += STATE['frame_interval']
            if STATE['next_frame'] <= game_seconds:
                STATE['next_frame'] = game_seconds+STATE['frame_interval']
        boundary_due=46<=seconds<=53 and game_seconds>=STATE['next_boundary']
        if (game_seconds >= STATE['next_gpu'] or boundary_due) and game_seconds > 1:
            _gpu_sample(world,seconds,location)
            STATE['next_gpu'] = game_seconds+6
            STATE['next_boundary'] = game_seconds+1/30
            _save()
        if STATE['capture_evidence'] and seconds>=12 and not STATE.get('evidence_done'):
            assert STATE['controls'], 'Evidence requires the central controller'
            STATE['evidence_before']=(STATE['controls'].get_editor_property('contact_enabled'),
                                      STATE['controls'].get_editor_property('detail_flow_enabled'))
            STATE.update(evidence_stage=0,evidence_wait=0)
            u.GameplayStatics.set_game_paused(world,True)
        if game_seconds >= STATE['duration']:
            STATE['recording_finished'] = True
            _save()
    except Exception:
        _finish(traceback.format_exc())
