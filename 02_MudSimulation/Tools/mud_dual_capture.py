"""PIE-only directed portfolio capture. Fixed 30 Hz game clock; not realtime FPS.

No Unreal assets are authored or saved. Character shots use Enhanced Input and
CharacterMovement; cut boundaries reset the pawn. All process settings restore.
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

ROOT = Path('D:/aco/unreal/Stormfall')
MAP = '/Game/MudStudy/Professional/Phase15/L_Mud_SurfaceAndPool'
STAGES = [('hero', 8), ('thin', 12), ('pool', 16), ('color', 6),
          ('depth', 9), ('visc_low', 4), ('visc_high', 4), ('overview', 3)]
STATE = {}


def vec(v):
    return [float(v.x), float(v.y), float(v.z)]


def component(actor, name):
    return next(c for c in actor.get_components_by_class(u.ActorComponent) if c.get_name() == name)


def save(complete=False, error=None):
    keep = ['settings_before', 'settings_restored', 'frames', 'samples', 'stages',
            'source_sha256', 'started_utc', 'world_path', 'warmup_frames',
            'source_assets', 'capture_settings', 'queue_errors', 'game_deltas']
    result = {k: STATE.get(k) for k in keep}
    result.update(complete=complete, error=error,
                  elapsed_wall_seconds=time.monotonic()-STATE['wall_start'],
                  waiting_review=STATE.get('waiting_review', False),
                  stage=STATE.get('stage_name'), frame_count=len(STATE['frames']),
                  target_frames=sum(int(s*30) for _, s in STAGES),
                  scope='Directed UE PIE imagery, actual Enhanced Input movement, offline 30Hz game stepping. No realtime FPS, original equivalence or physically calibrated viscosity claim.')
    (STATE['out']/'run.json').write_text(json.dumps(result, indent=2), encoding='utf-8')


def console(command):
    # CVars only, using the editor world; no PIE player ConsoleCommand call.
    u.SystemLibrary.execute_console_command(STATE['editor_world'], command)


def start(input_subsystem_path, output_path, width=1920, height=1080, review_after=30):
    assert not STATE.get('handle'), 'Capture already active'
    assert Path(u.Paths.project_dir()).resolve().name == 'FluidNinjaStudy'
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    world = editor.get_game_world()
    assert world and 'UEDPIE_' in world.get_path_name() and 'L_Mud_SurfaceAndPool' in world.get_path_name()
    out = Path(output_path).resolve()
    assert out.is_relative_to(ROOT/'Verification/MudProfessional/phase16-video')
    out.mkdir(parents=True, exist_ok=False)
    (out/'frames').mkdir()
    actors = {a.get_actor_label(): a for a in u.GameplayStatics.get_all_actors_of_class(world, u.Actor)}
    pawn = u.GameplayStatics.get_player_pawn(world, 0)
    assert pawn and pawn.get_class().get_name() == 'BP_Mud_Manny_C'
    settings = u.get_default_object(u.load_class(None, '/Script/UnrealEd.EditorPerformanceSettings'))
    before = dict(background_throttle=settings.get_editor_property('bThrottleCPUWhenNotForeground'),
                  max_fps=u.SystemLibrary.get_console_variable_float_value('t.MaxFPS'),
                  override_fps=u.SystemLibrary.get_console_variable_float_value('t.OverrideFPS'),
                  slate_throttling=u.SystemLibrary.get_console_variable_float_value('Slate.bAllowThrottling'))
    controls = component(actors['Mud_DeepPool'], 'ArtistControls')
    STATE.clear()
    STATE.update(out=out, world=world, editor_world=editor.get_editor_world(), settings=settings,
                 settings_before=before, settings_restored=False, wall_start=time.monotonic(),
                 started_utc=datetime.now(timezone.utc).isoformat(),
                 source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 world_path=world.get_path_name(), pawn=pawn,
                 pc=u.GameplayStatics.get_player_controller(world, 0),
                 mesh=pawn.get_component_by_class(u.SkeletalMeshComponent),
                 movement=pawn.get_component_by_class(u.CharacterMovementComponent),
                 input=u.find_object(None, input_subsystem_path),
                 move=u.load_asset('/Game/FluidNinjaLive/Meshes/Mannequin/Input/IA_Walk'),
                 thin=actors['Mud_ThinSurface'], pool=actors['Mud_DeepPool'], controls=controls,
                 capture=actors['Mud_Replay_Capture'], frames=[], samples=[], stages=[],
                 queue_errors=[], game_deltas=[], last_game_time=None,
                 warmup_frames=480, warmup_left=480, stage_index=-1,
                 review_after=review_after, waiting_review=False, reviewed=False,
                 stage_name='warmup', stage_frame=0, stage_settle=0,
                 source_assets={'solver': str(actors['Mud_DeepPool'].get_editor_property('solver').get_path_name()),
                                'map': MAP, 'thin_relief_cm': 20, 'pool_depth_cm': 80},
                 capture_settings={'width': width, 'height': height, 'fps': 30, 'fov': 55,
                                   'format': 'JPEG95 ImageWriteQueue', 'exposure_bias': .75,
                                   'clock': 'offline fixed game delta 1/30; Niagara retains its fixed solver step'})
    assert STATE['input']
    # UE property structs may be live views. Keep immutable numeric copies.
    STATE['colors'] = tuple(tuple(float(getattr(controls.get_editor_property(name), k)) for k in ['r','g','b','a'])
                            for name in ['light_color', 'dark_color'])
    shutil.copy2(__file__, out/'harness.py')
    try:
        try:
            STATE['window_before'] = research_window.restore_for_capture()
        except Exception as exc:
            STATE['window_restore_note'] = str(exc)
        settings.set_editor_property('bThrottleCPUWhenNotForeground', False)
        console('t.OverrideFPS 30')
        console('t.MaxFPS 0')
        console('Slate.bAllowThrottling 0')
        cap = STATE['capture'].get_component_by_class(u.SceneCaptureComponent2D)
        rt = u.RenderingLibrary.create_render_target2d(world, width, height,
                  u.TextureRenderTargetFormat.RTF_RGBA8, u.LinearColor(0, 0, 0, 1), False, False)
        cap.set_editor_property('texture_target', rt)
        cap.set_editor_property('capture_source', u.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        cap.set_editor_property('capture_every_frame', False)
        cap.set_editor_property('capture_on_movement', False)
        cap.set_editor_property('fov_angle', 55)
        cap.set_editor_property('bAlwaysPersistRenderingState', True)
        pp = cap.get_editor_property('post_process_settings')
        for name, value in [('override_auto_exposure_method', True), ('auto_exposure_method', u.AutoExposureMethod.AEM_MANUAL),
                            ('override_auto_exposure_bias', True), ('auto_exposure_bias', .75),
                            ('override_auto_exposure_apply_physical_camera_exposure', True), ('auto_exposure_apply_physical_camera_exposure', False),
                            ('override_motion_blur_amount', True), ('motion_blur_amount', .2)]:
            pp.set_editor_property(name, value)
        cap.set_editor_property('post_process_settings', pp)
        cap.set_editor_property('post_process_blend_weight', 1)
        options = u.ImageWriteOptions()
        for name, value in [('format', u.DesiredImageFormat.JPG), ('compression_quality', 95),
                            ('overwrite_file', False), ('bAsync', True)]:
            options.set_editor_property(name, value)
        STATE.update(cap=cap, rt=rt, image_options=options)
        controls.set_editor_property('enable_movement_drag', False)
        controls.set_editor_property('viscosity_feel', .5)
        u.GameplayStatics.set_game_paused(world, False)
        save()
        STATE['handle'] = u.register_slate_post_tick_callback(tick)
    except Exception:
        finish(traceback.format_exc())
        raise
    return {'scheduled': True, 'output': str(out), 'raw_duration_seconds': sum(s for _, s in STAGES)}


def set_controls(**values):
    for key, value in values.items():
        STATE['controls'].set_editor_property(key, value)


def reset_pawn(x, y, z):
    STATE['input'].inject_input_vector_for_action(STATE['move'], u.Vector(), [], [])
    STATE['movement'].stop_movement_immediately()
    STATE['pawn'].set_actor_location(u.Vector(x, y, z), False, True)
    STATE['pawn'].set_actor_rotation(u.Rotator(), True)
    STATE['pc'].set_control_rotation(u.Rotator())


def begin_stage():
    STATE['stage_index'] += 1
    if STATE['stage_index'] >= len(STAGES):
        STATE['stage_name'] = 'draining'
        STATE['drain_start'] = time.monotonic()
        STATE['input'].inject_input_vector_for_action(STATE['move'], u.Vector(), [], [])
        u.GameplayStatics.set_game_paused(STATE['world'], True)
        save()
        return
    name, duration = STAGES[STATE['stage_index']]
    STATE.update(stage_name=name, stage_frame=0, stage_settle=10)
    set_controls(layer_depth_cm=80, surface_relief_cm=20, viscosity_feel=.5,
                 enable_movement_drag=False, light_color=u.LinearColor(*STATE['colors'][0]), dark_color=u.LinearColor(*STATE['colors'][1]))
    if name == 'thin':
        reset_pawn(-2900, -150, 93)
    elif name == 'pool':
        reset_pawn(950, 0, 94)
    elif name in ['color', 'depth']:
        reset_pawn(2200, 0, 12.2)
    elif name.startswith('visc_'):
        reset_pawn(1900, -100, 12.2)
        set_controls(enable_movement_drag=True, viscosity_feel=0 if name == 'visc_low' else 1)
    STATE['cap'].set_editor_property('bCameraCutThisFrame', True)
    STATE['stages'].append({'name': name, 'duration_seconds': duration, 'first_frame': len(STATE['frames']),
                            'cut_resets_pawn': name in ['thin', 'pool', 'color', 'depth', 'visc_low', 'visc_high']})


def camera(position, target, fov=55):
    delta = target-position
    rotation = u.Rotator(pitch=math.degrees(math.atan2(delta.z, math.hypot(delta.x, delta.y))),
                         yaw=math.degrees(math.atan2(delta.y, delta.x)), roll=0)
    STATE['capture'].set_actor_location(position, False, True)
    STATE['capture'].set_actor_rotation(rotation, False)
    STATE['cap'].set_editor_property('fov_angle', fov)
    return {'location': vec(position), 'rotation': [rotation.pitch, rotation.yaw, rotation.roll], 'fov': fov}


def action_and_camera():
    name = STATE['stage_name']
    seconds = STATE['stage_frame']/30
    move = u.Vector()
    p = STATE['pawn'].get_actor_location()
    if name == 'hero':
        f = seconds/8
        cam = camera(u.Vector(-2560+320*f, 520-80*f, 150), u.Vector(-2200, -80, -5))
    elif name == 'thin':
        if .8 <= seconds < 3.8:
            move = u.Vector(0, .5, 0)
        elif 3.8 <= seconds < 6.3:
            move = u.Vector(.5, 0, 0)
        elif 6.3 <= seconds < 8.8:
            move = u.Vector(0, -.5, 0)
        cam = camera(p+u.Vector(-430, 360, 180), p+u.Vector(0, 0, 10))
    elif name == 'pool':
        if .8 <= seconds < 6.8:
            move = u.Vector(0, .55, 0)
        elif 7.8 <= seconds < 13.8:
            move = u.Vector(0, -.55, 0)
        cam = camera(p+u.Vector(-430, 360, 180), p+u.Vector(0, 0, 35))
    elif name == 'color':
        green = 2 <= seconds < 4
        set_controls(light_color=u.LinearColor(.035, .055, .045, 1) if green else u.LinearColor(*STATE['colors'][0]),
                     dark_color=u.LinearColor(.008, .016, .012, 1) if green else u.LinearColor(*STATE['colors'][1]))
        cam = camera(u.Vector(1800, 360, 240), u.Vector(2200, 0, 30))
    elif name == 'depth':
        depth = 20 if seconds < 3 else (50 if seconds < 6 else 90)
        set_controls(layer_depth_cm=depth)
        cam = camera(u.Vector(1800, 360, 240), u.Vector(2200, 0, 30))
    elif name.startswith('visc_'):
        if .6 <= seconds < 3.6:
            move = u.Vector(0, .55, 0)
        cam = camera(u.Vector(2200, 750, 350), u.Vector(2200, 0, 25), 70)
    else:
        cam = camera(u.Vector(0, 6500, 6500), u.Vector(0, 0, 0), 70)
    STATE['input'].inject_input_vector_for_action(STATE['move'], move, [], [])
    return cam, vec(move)


def files_finished():
    for frame in STATE['frames']:
        p = STATE['out']/frame['file']
        if not p.is_file() or p.stat().st_size < 100:
            return False
        with p.open('rb') as f:
            if f.read(2) != b'\xff\xd8':
                return False
            f.seek(-2, 2)
            if f.read(2) != b'\xff\xd9':
                return False
    return True


def resume():
    assert STATE.get('waiting_review')
    STATE.update(waiting_review=False, reviewed=True)
    u.GameplayStatics.set_game_paused(STATE['world'], False)
    save()


def finish(error=None):
    handle = STATE.pop('handle', None)
    if handle:
        u.unregister_slate_post_tick_callback(handle)
    errors = []
    try:
        STATE['input'].inject_input_vector_for_action(STATE['move'], u.Vector(), [], [])
        STATE['cap'].set_editor_property('texture_target', None)
    except Exception as exc:
        errors.append(str(exc))
    try:
        STATE['settings'].set_editor_property('bThrottleCPUWhenNotForeground', STATE['settings_before']['background_throttle'])
        for name, key in [('t.OverrideFPS', 'override_fps'), ('t.MaxFPS', 'max_fps'), ('Slate.bAllowThrottling', 'slate_throttling')]:
            console(name+' '+str(STATE['settings_before'][key]))
        research_window.restore_previous()
    except Exception as exc:
        errors.append(str(exc))
    STATE['settings_restored'] = not errors
    save(True, error or ('; '.join(errors) if errors else None))
    u.EditorLevelLibrary.editor_end_play()
    u.log('MUD_DUAL_CAPTURE_FINISHED '+str(STATE['out']))


def tick(dt):
    try:
        if STATE.get('waiting_review'):
            return
        if STATE['stage_name'] == 'draining':
            if files_finished():
                finish()
            elif time.monotonic()-STATE['drain_start'] > 90:
                finish('ImageWriteQueue did not finish within 90 seconds')
            return
        clock = u.GameplayStatics.get_time_seconds(STATE['world'])
        previous = STATE['last_game_time']
        if previous is not None and clock <= previous+1e-7:
            return
        STATE['last_game_time'] = clock
        if previous is not None:
            STATE['game_deltas'].append(clock-previous)
        if STATE['warmup_left']:
            STATE['warmup_left'] -= 1
            if not STATE['warmup_left']:
                begin_stage()
            elif STATE['warmup_left'] % 60 == 0:
                save()
            return
        cam, move = action_and_camera()
        STATE['cap'].capture_scene()
        if STATE['stage_settle']:
            STATE['stage_settle'] -= 1
            return
        index = len(STATE['frames'])
        filename = 'frames/frame_%06d.jpg' % index
        u.ImageWriteBlueprintLibrary.export_to_disk(STATE['rt'], str(STATE['out']/filename), STATE['image_options'])
        STATE['frames'].append({'file': filename, 'game_seconds': clock,
                                'stage': STATE['stage_name'], 'stage_frame': STATE['stage_frame'], 'camera': cam})
        if STATE['stage_frame'] % 6 == 0:
            p = STATE['pawn'].get_actor_location()
            c = STATE['controls']
            STATE['samples'].append({'frame': index, 'game_seconds': clock, 'stage': STATE['stage_name'],
                                     'location': vec(p), 'velocity': vec(STATE['pawn'].get_velocity()),
                                     'foot_l': vec(STATE['mesh'].get_socket_location('foot_l')),
                                     'falling': STATE['movement'].is_falling(), 'input': move,
                                     'depth_cm': c.get_editor_property('layer_depth_cm'),
                                     'viscosity': c.get_editor_property('viscosity_feel'),
                                     'light_color': [float(getattr(c.get_editor_property('light_color'), k)) for k in ['r','g','b','a']],
                                     'movement_drag': c.get_editor_property('enable_movement_drag'),
                                     'max_walk_speed': STATE['movement'].get_editor_property('max_walk_speed'),
                                     'active_pool_inputs': c.get_editor_property('active_leg_inputs'),
                                     'pool_output': STATE['pool'].get_editor_property('output').get_path_name(),
                                     'normal_output': STATE['pool'].get_editor_property('normal_pass').get_editor_property('normal_output').get_path_name()})
        STATE['stage_frame'] += 1
        if len(STATE['frames']) % 30 == 0:
            save()
        if STATE['stage_frame'] >= STAGES[STATE['stage_index']][1]*30:
            begin_stage()
        if not STATE['reviewed'] and len(STATE['frames']) >= STATE['review_after']:
            STATE['waiting_review'] = True
            u.GameplayStatics.set_game_paused(STATE['world'], True)
            save()
    except Exception:
        finish(traceback.format_exc())
