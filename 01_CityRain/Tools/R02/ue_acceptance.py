"""R02 acceptance worker. Run only via Run.ps1 with exclusive project access.

Audits never save assets. Captures/benchmark modify only a disposable process's
in-memory controller and restore its properties on completion or exception.
"""
import hashlib
import itertools
import json
import os
import shutil
import time
import traceback
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CFG = json.loads((HERE / 'acceptance.json').read_text(encoding='utf-8'))
MODE = os.environ.get('STORMFALL_R02_MODE', 'audit')
OUT = Path(os.environ['STORMFALL_R02_OUTPUT']).resolve()
OUT.mkdir(parents=True, exist_ok=True)
L = u.MaterialEditingLibrary
EA = u.EditorAssetLibrary
STATE = {'mode': MODE, 'status': 'running', 'errors': [], 'samples': [], 'captures': [],
         'time_basis': 'wall seconds; not deterministic scene time', 'saved_assets': []}
CONTROL_NAMES = ['UseManualControl', 'UseManualControlInPlay', 'ManualWetness', 'ManualRain',
                 'ManualPuddles', 'RippleSizeScale', 'RippleDensityScale', 'RippleSpeedScale',
                 'RippleStrengthScale', 'RippleRandomness']
BASE = {}
HANDLE = None
CAMERA = None
CSV_ACTIVE = False
PIE_ACTIVE = False
CONTROLLER = None
WORLD = None
MPC = None
TICK_ACTIVE = False


def write(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def read_controls():
    return {k: CONTROLLER.get_editor_property(k) for k in CONTROL_NAMES}


def rotation(values):
    # Unreal's reflected struct constructor positional field order is not P/Y/R.
    return u.Rotator(pitch=values[0], yaw=values[1], roll=values[2])


def apply(values):
    for k, value in values.items():
        CONTROLLER.set_editor_property(k, value)
    CONTROLLER.call_method('ApplyArtistControls')


def snapshot():
    return {'controls': read_controls(), 'mpc': {k: u.MaterialLibrary.get_scalar_parameter_value(WORLD, MPC, k)
            for k in ['Humidity', 'RainAmount', 'ManualMode', 'ManualWetness', 'ManualRain',
                      'ManualPuddles', 'RippleStrengthScale', 'RippleRandomness']}}


def material_record(mat):
    nodes = list(L.get_material_function_expressions(mat) if isinstance(mat, u.MaterialFunction)
                 else L.get_material_expressions(mat))
    custom = []
    for node in nodes:
        if isinstance(node, u.MaterialExpressionCustom):
            code = str(node.get_editor_property('code'))
            custom.append({'object': node.get_path_name(), 'description': str(node.get_editor_property('desc')),
                           'code': code, 'sha256': hashlib.sha256(code.encode()).hexdigest(),
                           'inputs': [str(p.get_editor_property('input_name')) for p in node.get_editor_property('inputs')]})
    return {'path': mat.get_path_name(), 'node_count': len(nodes), 'custom': custom}


def audit():
    actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    records = []
    for actor in actors:
        for comp in actor.get_components_by_class(u.MeshComponent):
            for slot in range(comp.get_num_materials()):
                mat = comp.get_material(slot)
                records.append({'actor': actor.get_path_name(), 'label': actor.get_actor_label(),
                                'component': comp.get_name(), 'slot': slot,
                                'material': mat.get_path_name() if mat else None,
                                'class': comp.get_class().get_name()})
    masters = [CFG['ground_master'], '/Game/Stormfall/Weather/M_Ground_Soil_Weather',
               '/Game/Stormfall/Weather/M_Ground_Special_Weather', '/Game/Stormfall/Weather/Objects/M_WindowGlass_Rain',
               '/Game/Stormfall/Weather/Objects/M_Object_Default_Weather',
               '/Game/Stormfall/Weather/Objects/M_Object_Building_Weather']
    graphs = []
    for path in masters:
        mat = u.load_asset(path)
        if not mat:
            raise RuntimeError('Required material missing: ' + path)
        graphs.append(material_record(mat))
    for path in ['/Game/Stormfall/Weather/Objects/MF_SurfaceRainWorld',
                 '/Game/Stormfall/Weather/Objects/MF_ObjectWorldSlideUV',
                 '/Game/Stormfall/Weather/Objects/MF_GlassWorldSlideUV']:
        function = u.load_asset(path)
        if function:
            graphs.append(material_record(function))
    write('material-code.json', graphs)
    write('component-slots.json', records)
    write('baseline.json', {'world': WORLD.get_path_name(), 'state': snapshot(),
                            'actor_count': len(actors), 'material_slot_count': len(records),
                            'shader_compile': 'not_requested',
                            'missing_camera_families': sorted(set(CFG['required_camera_families']) -
                                                              {c['name'] for c in CFG['cameras']})})


def finish(success):
    global HANDLE, CSV_ACTIVE
    if CSV_ACTIVE:
        u.SystemLibrary.execute_console_command(WORLD, 'csvprofile STOP')
        CSV_ACTIVE = False
    try:
        if MODE != 'audit' and BASE and CONTROLLER:
            apply(BASE)
            STATE['restored_controls'] = read_controls()
            STATE['restore_matches'] = all(STATE['restored_controls'][k] == v for k, v in BASE.items())
            if not STATE['restore_matches']:
                success = False
    except Exception:
        STATE['errors'].append('Restore failed: ' + traceback.format_exc())
        success = False
    if os.environ.get('STORMFALL_R02_MATERIAL_TIME'):
        u.SystemLibrary.execute_console_command(None, 'stormfall.QA.MaterialTime -1')
    if CAMERA:
        u.get_editor_subsystem(u.EditorActorSubsystem).destroy_actor(CAMERA)
    if PIE_ACTIVE:
        u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    STATE['status'] = 'completed' if success else 'failed'
    STATE['elapsed_seconds'] = time.monotonic() - START
    write('result.json', STATE)
    if HANDLE is not None:
        u.unregister_slate_post_tick_callback(HANDLE)
        HANDLE = None
    u.EditorPythonScripting.set_keep_python_script_alive(False)


def capture_tasks():
    defaults = {k: BASE[k] for k in CONTROL_NAMES if k.startswith('Ripple')}
    states = CFG['states']
    if os.environ.get('STORMFALL_R02_QUICK') == '1':
        states = [s for s in states if s['name'] in ('dry', 'pooled', 'ripple-off')]
    cameras = CFG['cameras']
    requested_camera = os.environ.get('STORMFALL_R02_CAMERA', '')
    if requested_camera:
        cameras = [c for c in cameras if c['name'] == requested_camera]
        if not cameras:
            raise ValueError('Unknown requested camera: ' + requested_camera)
    # Pinned material time (StormfallQATime.cpp) makes ripple phase repeatable between runs. It is pinned only for
    # the screenshot itself: zero delta also freezes eye adaptation and stalls full streaming, so settling stays live.
    material_time = os.environ.get('STORMFALL_R02_MATERIAL_TIME', '')
    pin = lambda value: u.SystemLibrary.execute_console_command(None, 'stormfall.QA.MaterialTime ' + str(value))
    # The first capture of every run drifted (exposure and lighting still converging): warm up once before it.
    warmup = CFG.get('first_capture_warmup_seconds', 0)
    for camera, state in itertools.product(cameras, states):
        values = dict(defaults, UseManualControl=True, ManualWetness=state['wetness'],
                      ManualRain=state['rain'], ManualPuddles=state['puddles'])
        values.update({k: v for k, v in state.items() if k.startswith('Ripple')})
        apply(values)
        CAMERA.set_actor_location(u.Vector(*camera['location']), False, False)
        CAMERA.set_actor_rotation(rotation(camera['rotation']), False)
        CAMERA.get_component_by_class(u.CameraComponent).set_editor_property('field_of_view', camera['fov'])
        camera_component = CAMERA.get_component_by_class(u.CameraComponent)
        post = camera_component.get_editor_property('post_process_settings')
        post.set_editor_property('override_auto_exposure_bias', True)
        post.set_editor_property('auto_exposure_bias', 2.0)
        camera_component.set_editor_property('post_process_settings', post)
        camera_component.set_editor_property('post_process_blend_weight', 1.0)
        u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(
            u.Vector(*camera['location']), rotation(camera['rotation']))
        until = time.monotonic() + CFG['settle_seconds'] + warmup
        warmup = 0
        while time.monotonic() < until:
            yield
        filename = OUT / (camera['name'] + '--' + state['name'] + '.png')
        # As UE's automation screenshots do: flush loading, finish shaders, force every mip resident.
        # Without it, wide shots differed run to run by whichever texture mips had streamed in.
        if os.environ.get('STORMFALL_R02_FINISH_LOADING', '1') == '1':
            u.AutomationLibrary.finish_loading_before_screenshot()
        if material_time:
            pin(float(material_time))
            for _ in range(3):
                yield
        task = u.AutomationLibrary.take_high_res_screenshot(*CFG['resolution'], str(filename), camera=CAMERA, delay=1.0)
        screenshot_deadline = time.monotonic() + 45
        while not task.is_task_done():
            if time.monotonic() > screenshot_deadline:
                raise TimeoutError('Screenshot task did not complete: ' + str(filename))
            yield
        if material_time:
            pin(-1)
        if not filename.is_file() or filename.stat().st_size < 1024:
            raise RuntimeError('Missing or empty screenshot: ' + str(filename))
        STATE['captures'].append({'file': str(filename), 'camera': camera, 'scenario': state,
                                  'qa_exposure_bias_ev': 2.0,
                                  'material_time': float(material_time) if material_time else None,
                                  'finished_loading': os.environ.get('STORMFALL_R02_FINISH_LOADING', '1') == '1',
                                  'actual_rotation': {k: getattr(CAMERA.get_actor_rotation(), k) for k in ('pitch','yaw','roll')},
                                  'state': snapshot(), 'visual_approval': 'pending',
                                  'sha256': hashlib.sha256(filename.read_bytes()).hexdigest()})
        write('progress.json', STATE)
        yield


def cycle_tasks():
    global PIE_ACTIVE, WORLD, CONTROLLER, BASE
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    # Only the disposable editor instance is changed; no save follows.
    CONTROLLER.set_editor_property('UseManualControlInPlay', False)
    levels.editor_request_begin_play()
    PIE_ACTIVE = True
    timeout = time.monotonic() + 45
    while not editor.get_game_world():
        if time.monotonic() > timeout:
            raise TimeoutError('PIE did not become ready')
        yield
    WORLD = editor.get_game_world()
    actors = u.GameplayStatics.get_all_actors_of_class(WORLD, u.Actor)
    controllers = [a for a in actors if a.get_class().get_name() == CFG['controller_class']]
    managers = [a for a in actors if a.get_class().get_name().startswith('WeatherManagmentBP_C')]
    if len(controllers) != 1 or len(managers) != 1:
        raise RuntimeError('PIE requires exactly one controller and one weather manager')
    CONTROLLER = controllers[0]
    BASE = read_controls()
    until = time.monotonic() + 2
    while time.monotonic() < until:
        yield
    STATE['cycle_initial'] = snapshot()
    if STATE['cycle_initial']['mpc']['ManualMode'] > 0.01:
        raise RuntimeError('PIE started in manual mode')
    managers[0].call_method('SwitchWeather')
    began = u.GameplayStatics.get_time_seconds(WORLD)
    stop_sent = False
    next_sample = 0.0
    settings = CFG['cycle']
    while True:
        elapsed = u.GameplayStatics.get_time_seconds(WORLD) - began
        if not stop_sent and elapsed >= settings['stop_rain_at_seconds']:
            managers[0].call_method('SwitchWeather')
            stop_sent = True
            STATE['stop_rain_game_seconds'] = elapsed
        if elapsed >= next_sample:
            STATE['samples'].append({'game_seconds': elapsed, **snapshot()})
            next_sample = elapsed + settings['sample_interval_seconds']
            write('progress.json', STATE)
        if elapsed >= settings['duration_seconds']:
            break
        yield
    humidity = [r['mpc']['Humidity'] for r in STATE['samples']]
    rain = [r['mpc']['RainAmount'] for r in STATE['samples']]
    STATE['cycle_checks'] = {
        'automatic_mode_throughout': all(r['mpc']['ManualMode'] < 0.01 for r in STATE['samples']),
        'starts_dry': STATE['cycle_initial']['mpc']['Humidity'] < 0.05,
        'becomes_wet': max(humidity) > 0.8,
        'rain_starts': max(rain) > 0.8,
        'rain_stops': rain[-1] < 0.05,
        'dries_after_rain': humidity[-1] < 0.1}
    STATE['cycle_visual_approval'] = 'pending; parameter readbacks do not certify animation quality'
    if not all(STATE['cycle_checks'].values()):
        raise RuntimeError('Automatic weather cycle failed one or more readback checks')


def benchmark_tasks():
    global CSV_ACTIVE
    settings = CFG['benchmark']
    order = settings['order'][:2] if os.environ.get('STORMFALL_R02_QUICK') == '1' else settings['order']
    STATE['expected_order'] = order
    camera = CFG['cameras'][0]
    u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(
        u.Vector(*camera['location']), rotation(camera['rotation']))
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    viewport = levels.get_active_viewport_config_key()
    levels.set_level_viewport_fov(camera['fov'], viewport)
    STATE['viewport_fov_readback'] = str(levels.get_level_viewport_fov(viewport))
    # Editor viewport timing includes editor cost; never label it packaged or standalone.
    STATE['benchmark_scope'] = 'editor viewport diagnostic; no standalone performance claim'
    STATE['camera'] = camera
    for cmd in ['r.VSync 0', 't.MaxFPS 0', 't.IdleWhenNotForeground 0', 'Slate.bAllowThrottling 0',
                'r.DynamicRes.OperationMode 0', 'r.ScreenPercentage ' + str(settings['screen_percentage']),
                'r.GPUCsvStatsEnabled 1', 'csv.CompressionMode 0']:
        u.SystemLibrary.execute_console_command(WORLD, cmd)
    for index, variant in enumerate(order):
        apply(dict(BASE, UseManualControl=True, ManualWetness=1.0, ManualRain=1.0, ManualPuddles=1.0,
                   RippleStrengthScale=0.0 if variant == 'off' else float(BASE['RippleStrengthScale'])))
        if variant == 'on' and float(BASE['RippleStrengthScale']) <= 0:
            raise RuntimeError('Baseline ripple strength is zero; cannot produce an on/off comparison.')
        until = time.monotonic() + settings['warmup_seconds']
        while time.monotonic() < until:
            yield
        csv_name = '%s-%02d-%s.csv' % (OUT.name, index, variant)
        # UE 5.8 CsvProfiler.cpp reads STARTFILE= separately and compares START/STOP
        # case-sensitively. An absolute -filename argument is ignored by this API.
        u.SystemLibrary.execute_console_command(WORLD, 'csvprofile STARTFILE=' + csv_name)
        u.SystemLibrary.execute_console_command(WORLD, 'csvprofile START')
        CSV_ACTIVE = True
        began = time.monotonic()
        until = began + settings['sample_seconds']
        while time.monotonic() < until:
            yield
        u.SystemLibrary.execute_console_command(WORLD, 'csvprofile STOP')
        CSV_ACTIVE = False
        STATE['samples'].append({'index': index, 'variant': variant, 'csv_requested': csv_name,
                                 'seconds': time.monotonic()-began, 'state': snapshot()})
        write('progress.json', STATE)
        source = Path(u.Paths.profiling_dir()) / 'CSV' / csv_name
        until = time.monotonic() + 30
        last_size, stable_since = -1, time.monotonic()
        while True:
            size = source.stat().st_size if source.is_file() else 0
            if size != last_size:
                last_size, stable_since = size, time.monotonic()
            if size > 0 and time.monotonic()-stable_since >= 3:
                break
            if time.monotonic() > until:
                raise TimeoutError('CSV did not finish writing: ' + str(source))
            yield
        shutil.copyfile(source, OUT / csv_name)
    STATE['csv_files_observed'] = [str(p) for p in OUT.glob('*.csv')]
    if len(STATE['csv_files_observed']) != len(order):
        raise RuntimeError('CSV output count mismatch; inspect Saved/Profiling/CSV and console output. Do not infer timing.')


def tick(_delta):
    global TICK_ACTIVE
    # Screenshot/streaming flushes can pump Slate and re-enter this callback.
    if TICK_ACTIVE:
        return
    TICK_ACTIVE = True
    try:
        if time.monotonic()-START > 1500:
            raise TimeoutError('Acceptance worker exceeded 1500 seconds')
        if MODE == 'benchmark':
            # Offscreen editors may tick Slate without drawing their level viewport.
            u.get_editor_subsystem(u.LevelEditorSubsystem).editor_invalidate_viewports()
        next(TASKS)
    except StopIteration:
        finish(True)
    except Exception:
        STATE['errors'].append(traceback.format_exc())
        finish(False)
    finally:
        TICK_ACTIVE = False


START = time.monotonic()
try:
    WORLD = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if WORLD.get_path_name().split('.')[0] != CFG['map']:
        raise RuntimeError('Refusing wrong map: ' + WORLD.get_path_name())
    controllers = [a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
                   if a.get_class().get_name() == CFG['controller_class']]
    if len(controllers) != 1:
        raise RuntimeError('Expected one weather controller, found ' + str(len(controllers)))
    CONTROLLER = controllers[0]
    BASE = read_controls()
    MPC = u.load_asset(CFG['mpc'])
    if not MPC:
        raise RuntimeError('Weather MPC missing')
    audit()
    if MODE in ('install', 'survey', 'inspect'):
        import importlib.util
        spec = importlib.util.spec_from_file_location('r02_changes', HERE / 'ue_changes.py')
        changes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(changes)
        STATE['changes'] = changes.run(MODE, ROOT, OUT)
        if MODE == 'install':
            STATE['survey'] = changes.run('survey', ROOT, OUT)
        finish(True)
    elif MODE == 'verify':
        paths = json.loads((ROOT / 'Verification/WeatherReuse/artist-before-graphs.json').read_text(encoding='utf-8'))
        compile_results = []
        for path in paths:
            errors = list(L.recompile_material(u.load_asset(path)))
            compile_results.append({'asset': path, 'errors': errors})
        STATE['material_compile'] = compile_results
        if any(r['errors'] for r in compile_results):
            raise RuntimeError('One or more weather master materials failed compilation')
        finish(True)
    elif MODE == 'audit':
        finish(True)
    else:
        levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
        # UE 5.8 True removes this named override and ensures if it does not exist.
        levels.editor_set_viewport_realtime(False)
        levels.editor_set_viewport_realtime(True)
        levels.editor_set_game_view(True)
        if MODE == 'capture':
            CAMERA = u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(
                u.CameraActor, u.Vector(*CFG['cameras'][0]['location']))
            TASKS = capture_tasks()
        elif MODE == 'benchmark':
            TASKS = benchmark_tasks()
        elif MODE == 'cycle':
            TASKS = cycle_tasks()
        else:
            raise RuntimeError('Unsupported worker mode: ' + MODE)
        u.EditorPythonScripting.set_keep_python_script_alive(True)
        HANDLE = u.register_slate_post_tick_callback(tick)
except Exception:
    STATE['errors'].append(traceback.format_exc())
    finish(False)
