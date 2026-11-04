"""Interaction regression in a new map; never edits the reference gallery.

Raw GPU readbacks and waits are test instrumentation, not runtime features.
"""
import hashlib
import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path
import unreal as u

WORK = Path('D:/aco/unreal/Stormfall')
OUT = WORK / 'Verification/MudRegression/20261027_01'
MAP = '/Game/MudStudy/Maps/L_Mud_Regression_20261027'
BASE = '/Game/MudStudy/Maps/L_Mud_ShaderIntegrated'
STATE = {}
PLAN = [('idle', 8), ('walking', 12), ('fast_movement', 12),
        ('multi_16', 12), ('strong_sdf', 12), ('boundary', 12), ('sustained', 180)]


def freeze():
    assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    research = Path(u.Paths.project_dir()).resolve()
    assert research.name == 'FluidNinjaStudy'
    rows = []
    snapshot = OUT / 'Baseline'
    if (OUT / 'baseline_manifest.json').exists():
        return 'Existing baseline preserved'
    roots = [research / 'Content/MudStudy/Evolution', research / 'Content/MudStudy/ShaderLab']
    files = [p for root in roots for p in root.rglob('*.uasset')]
    files += [research / 'Content/MudStudy/Maps/L_Mud_ShaderIntegrated.umap']
    for plugin in ['MudRuntime', 'MudShaderLab']:
        for part in ['Source', 'Shaders', 'Binaries']:
            root = research / 'Plugins' / plugin / part
            files += [p for p in root.rglob('*') if p.is_file() and p.suffix in ['.h', '.cpp', '.cs', '.usf', '.ush', '.dll', '.modules']]
        files.append(research / 'Plugins' / plugin / (plugin + '.uplugin'))
    for source in files:
        if not source.exists():
            raise RuntimeError('Missing baseline dependency: ' + str(source))
        relative = source.relative_to(research)
        data = source.read_bytes()
        target = snapshot / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        rows.append({'path': str(relative).replace('\\', '/'), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'baseline_manifest.json').write_text(json.dumps({
        'created_utc': datetime.now(timezone.utc).isoformat(), 'project': str(research),
        'scope': 'Selected shader/solver assets, source and deployed binaries; shared engine/vendor dependencies are not a full project backup',
        'files': rows}, indent=2), encoding='utf-8')
    return {'baseline_files': len(rows), 'map': BASE}


def build():
    assert 'FluidNinjaStudy' in u.Paths.project_dir(), 'Select the mud research project.'
    assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    current = editor.get_editor_world()
    if current.get_path_name().startswith(MAP + '.'):
        assert u.EditorLoadingAndSavingUtils.save_map(current, MAP)
    if u.EditorAssetLibrary.does_asset_exist(MAP):
        u.EditorLoadingAndSavingUtils.load_map(MAP)
    else:
        u.EditorLoadingAndSavingUtils.load_map(BASE)
        assert u.EditorLoadingAndSavingUtils.save_map(editor.get_editor_world(), MAP)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    existing = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
    legacy_brush = existing.get('ShaderLab_TestBrush') or existing.get('Integrated_Brush')
    if legacy_brush:
        actors.destroy_actor(legacy_brush)
    mud = next(a for a in actors.get_all_level_actors() if isinstance(a, u.MudShaderPreviewActor))
    mud.set_actor_label('Regression_Mud')
    mud.set_editor_property('brush_position_random', 0)
    mud.set_editor_property('track_player', False)
    mud.set_editor_property('brush_actors', [])
    mud.get_editor_property('normal_pass').set_editor_property('profile_gpu', False)
    character = existing.get('Regression_Character') or actors.spawn_actor_from_class(u.load_class(None, '/Game/FluidNinjaLive/Meshes/ThirdPersonCharacter.ThirdPersonCharacter_C'), u.Vector(-500, 0, 110))
    assert character
    character.set_actor_label('Regression_Character')
    character.set_editor_property('auto_possess_player', u.AutoReceiveInput.PLAYER0)
    character.get_component_by_class(u.CharacterMovementComponent).set_editor_property('run_physics_with_no_controller', True)
    mud.set_editor_property('brush_actors', [character])
    for i in range(16):
        actor = existing.get('Regression_Point_%02d' % i) or actors.spawn_actor_from_class(u.StaticMeshActor, u.Vector(0, 0, -5000))
        actor.set_actor_label('Regression_Point_%02d' % i)
        mesh = actor.get_component_by_class(u.StaticMeshComponent)
        mesh.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'))
        mesh.set_mobility(u.ComponentMobility.MOVABLE)
        actor.set_actor_scale3d(u.Vector(.4, .4, .4))
    sdf = existing.get('Regression_SDF') or actors.spawn_actor_from_class(u.StaticMeshActor, u.Vector(0, 0, -5000))
    sdf.set_actor_label('Regression_SDF')
    sdf.set_editor_property('tags', ['SDFSource'])
    mesh = sdf.get_component_by_class(u.StaticMeshComponent)
    mesh.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
    mesh.set_mobility(u.ComponentMobility.MOVABLE)
    sdf.set_actor_scale3d(u.Vector(4, 4, 1.5))
    assert u.EditorLoadingAndSavingUtils.save_map(editor.get_editor_world(), MAP)
    return MAP


def start(plan=None):
    assert not STATE.get('handle')
    assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    assert u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_path_name().startswith(MAP + '.'), 'Open the dedicated regression map first.'
    OUT.mkdir(parents=True, exist_ok=True)
    STATE.clear()
    STATE.update(start=time.monotonic(), index=-1, rows=[], phase=None, plan=plan or PLAN)
    STATE['harness_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    attempts = [int(p.stem.replace('runtime_attempt', '')) for p in OUT.glob('runtime_attempt*.json')]
    STATE['evidence_file'] = 'runtime_attempt%02d.json' % (max(attempts, default=0) + 1)
    u.EditorLevelLibrary.editor_play_simulate()
    STATE['handle'] = u.register_slate_post_tick_callback(_tick)
    return {'scheduled': True, 'plan': STATE['plan'], 'map': MAP}


def _bind_sdf(mud, fixtures):
    comp = mud.get_editor_property('simulation')
    u.NiagaraDIRigidMeshCollisionFunctionLibrary.set_source_actors(comp, 'User.SdfQuery', fixtures)
    report = json.loads(u.MudAuthoringLibrary.inspect_gpu_inputs(comp, 'User.SdfQuery'))
    assert report.get('success'), report
    row = next(v for v in report['values'] if v['name'] == 'User.SdfQuery')
    query = u.find_object(None, row['object'])
    assert query and query.get_path_name().startswith(comp.get_path_name()), 'Refuse to alter an asset DI'
    query.set_editor_property('GlobalSearchAllowed', False)
    query.set_editor_property('GlobalSearchForced', False)
    query.set_editor_property('ActorTags', [])
    config = json.loads(u.MudAuthoringLibrary.inspect_gpu_inputs(comp, 'DensityAccumulation'))
    text = next(v['value'] for v in config['values'] if v['name'] == 'User.DensityAccumulation')
    accumulation = float(re.search(r'Value=([-+0-9.eE]+)', text).group(1))
    STATE['density_accumulation'] = accumulation
    return {'query': query.get_path_name(), 'explicit_actors': [a.get_name() for a in fixtures],
            'global_search_allowed': False, 'global_search_forced': False}


def _configure(world, mud, character, points, sdf, name):
    for actor in points + [sdf]:
        actor.set_actor_location(u.Vector(0, 0, -5000), False, True)
    character.set_actor_location(u.Vector(-500, 0, 110), False, True)
    character.get_component_by_class(u.CharacterMovementComponent).stop_movement_immediately()
    character.get_component_by_class(u.CharacterMovementComponent).set_editor_property('max_walk_speed', 220 if name == 'walking' else 1600)
    active_character = name in ['walking', 'fast_movement']
    character.set_actor_hidden_in_game(not active_character)
    character.set_actor_enable_collision(active_character)
    if not active_character:
        character.set_actor_location(u.Vector(0, 0, -5000), False, True)
    brush = [character] if active_character else points if name == 'multi_16' else points[:1] if name in ['boundary', 'sustained'] else []
    mud.set_editor_property('brush_actors', brush)
    mud.set_editor_property('track_player', False)
    mud.rebuild_simulation()
    STATE['needs_sdf_bind'] = True
    return {'name': name, 'samples': [], 'character_distance_cm': 0,
            'character_min_z': None, 'character_max_z': None,
            'moving_fixture_distance_cm': 0, 'max_point_inputs': 0,
            'point_input_counts_observed': [], 'fixture_xy_bounds': None,
            'sdf_only': name == 'strong_sdf', 'path': 'character_bones' if active_character else 'mesh_sdf' if name == 'strong_sdf' else 'point_inputs',
            'start_dispatches': mud.get_editor_property('normal_pass').get_editor_property('producer_graph_dispatches')}


def _sample(world, mud):
    source = mud.get_editor_property('output')
    normal = mud.get_editor_property('normal_pass').get_editor_property('normal_output')
    raw = u.RenderingLibrary.read_render_target_raw(world, source, False)
    normals = u.RenderingLibrary.read_render_target_raw(world, normal, False)
    assert len(raw) == len(normals) == 512 * 512
    finite = all(math.isfinite(v) for p in raw for v in (p.r, p.g, p.b, p.a))
    normal_finite = all(math.isfinite(v) for p in normals for v in (p.r, p.g, p.b, p.a))
    height_error = max(abs(a.b - b.a) for a, b in zip(raw, normals))
    max_velocity = max(max(abs(p.r), abs(p.g)) for p in raw)
    min_b, max_b = min(p.b for p in raw), max(p.b for p in raw)
    # Composite saturates before its accumulation gain. Export B is 1-D,
    # so valid high-input states can be slightly negative.
    accumulation = STATE['density_accumulation']
    expected_b_min = 1 - max(1, .5 + .5 * accumulation)
    changed = 0
    prev = STATE.get('previous_B')
    if prev:
        changed = sum(abs(p.b - old) > .001 for p, old in zip(raw, prev))
    STATE['previous_B'] = [p.b for p in raw]
    mid = mud.get_editor_property('surface_mid')
    bound = mid.get_texture_parameter_value('MudNormalBuffer') == normal
    return {'elapsed': time.monotonic() - STATE['phase_start'], 'pixels': len(raw),
            'state_finite': finite, 'normal_finite': normal_finite, 'max_abs_velocity': max_velocity,
            'B_range': [min_b, max_b], 'source_B_vs_normal_A_max_error': height_error,
            'density_accumulation': accumulation, 'expected_B_min': expected_b_min,
            'changed_B_pixels_since_last_sample': changed, 'material_bound': bound,
            'pass': finite and normal_finite and height_error == 0 and bound and max_velocity <= 50.1 and min_b >= expected_b_min - .001 and max_b <= 1.001}


def _persist(complete=False):
    report = {'complete': complete, 'map': MAP, 'output_resolution': 512,
              'harness_sha256': STATE.get('harness_sha256'),
              'evidence_file': STATE.get('evidence_file'),
              'scope': 'Runtime stability and state/derived-normal coherence; not reference dynamic equivalence or a performance benchmark',
              'pass': complete and all(r.get('pass') for r in STATE['rows']),
              'cases': STATE['rows'], 'current_case': STATE.get('phase')}
    (OUT / 'runtime.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if complete and STATE.get('evidence_file'):
        (OUT / STATE['evidence_file']).write_text(json.dumps(report, indent=2), encoding='utf-8')


def _finish_case(mud):
    row = STATE['phase']
    row['dispatch_delta'] = mud.get_editor_property('normal_pass').get_editor_property('producer_graph_dispatches') - row['start_dispatches']
    row['pass'] = bool(row['samples']) and all(s['pass'] for s in row['samples']) and row['dispatch_delta'] > 0
    if row['name'] in ['walking', 'fast_movement']:
        row['pass'] = row['pass'] and row['character_distance_cm'] > (200 if row['name'] == 'walking' else 1000) and row['character_min_z'] > 50
    if row['name'] == 'strong_sdf':
        row['pass'] = row['pass'] and row.get('sdf_binding', {}).get('explicit_actors') and row['max_point_inputs'] == 0 and row['moving_fixture_distance_cm'] > 1000
    if row['name'] == 'multi_16':
        row['pass'] = row['pass'] and 16 in row['point_input_counts_observed'] and 8 in row['point_input_counts_observed']
    if row['name'] == 'boundary':
        limits = row['fixture_xy_bounds']
        row['pass'] = row['pass'] and limits[0] < -1000 and limits[1] > 1000
    row['pass'] = bool(row['pass'])
    STATE['rows'].append(row)
    _persist()
    u.log('MUD_REGRESSION_CASE ' + json.dumps({'name': row['name'], 'pass': row['pass'], 'samples': len(row['samples'])}))


def _tick(dt):
    try:
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if not world:
            if time.monotonic() - STATE['start'] > 60:
                raise RuntimeError('PIE did not start')
            return
        actors = u.GameplayStatics.get_all_actors_of_class(world, u.Actor)
        mud = next(a for a in actors if a.get_actor_label() == 'Regression_Mud')
        character = next(a for a in actors if a.get_actor_label() == 'Regression_Character')
        points = sorted([a for a in actors if a.get_actor_label().startswith('Regression_Point_')], key=lambda a: a.get_actor_label())
        sdf = next(a for a in actors if a.get_actor_label() == 'Regression_SDF')
        now = time.monotonic()
        if STATE['index'] < 0:
            if now - STATE['start'] < 3:
                return
            STATE['index'] = 0
        elif now - STATE['phase_start'] > STATE['plan'][STATE['index']][1]:
            _finish_case(mud)
            STATE['index'] += 1
        if STATE['index'] == len(STATE['plan']):
            STATE['phase'] = None
            _persist(True)
            u.unregister_slate_post_tick_callback(STATE.pop('handle'))
            u.EditorLevelLibrary.editor_end_play()
            return
        name = STATE['plan'][STATE['index']][0]
        if STATE.get('phase') is None or STATE['phase']['name'] != name:
            STATE['phase_start'] = now
            STATE['last_sample'] = now
            STATE['previous_B'] = None
            STATE['previous_character'] = None
            STATE['previous_fixture'] = None
            STATE['phase'] = _configure(world, mud, character, points, sdf, name)
            _persist()
            return
        t = now - STATE['phase_start']
        row = STATE['phase']
        if STATE['needs_sdf_bind'] and t > 1:
            row['sdf_binding'] = _bind_sdf(mud, [sdf] if name == 'strong_sdf' else [])
            STATE['needs_sdf_bind'] = False
        if name in ['walking', 'fast_movement']:
            location = character.get_actor_location()
            direction = STATE.get('walk_direction', 1)
            if location.x > (400 if name == 'walking' else 750):
                direction = -1
            if location.x < (-400 if name == 'walking' else -750):
                direction = 1
            STATE['walk_direction'] = direction
            character.add_movement_input(u.Vector(direction, 0, 0), 1, True)
            previous = STATE['previous_character']
            if previous:
                row['character_distance_cm'] += (location - previous).length()
            STATE['previous_character'] = location
            if t > 2:
                row['character_min_z'] = min(row['character_min_z'] or location.z, location.z)
                row['character_max_z'] = max(row['character_max_z'] or location.z, location.z)
        if name == 'multi_16':
            active = points[:8] if 4 < t < 7 else points
            mud.set_editor_property('brush_actors', active)
            for i, actor in enumerate(active):
                actor.set_actor_location(u.Vector(450 * math.sin(t + i * .6), 450 * math.cos(t * .7 + i * .6), 30), False, True)
        elif name == 'strong_sdf':
            sdf.set_actor_location(u.Vector(500 * math.sin(t * 1.5), 200 * math.cos(t), -10 + 30 * math.sin(t * 2)), False, True)
        elif name == 'boundary':
            points[0].set_actor_location(u.Vector(1300 * math.sin(t * .8), 950 * math.cos(t * .4), 30), False, True)
        elif name == 'sustained':
            points[0].set_actor_location(u.Vector(600 * math.sin(t * .7), 600 * math.cos(t * .5), 30), False, True)
        fixture = sdf if name == 'strong_sdf' else points[0]
        current = fixture.get_actor_location()
        if STATE['previous_fixture']:
            row['moving_fixture_distance_cm'] += (current - STATE['previous_fixture']).length()
        STATE['previous_fixture'] = current
        limits = row['fixture_xy_bounds']
        row['fixture_xy_bounds'] = [min(limits[0], current.x), max(limits[1], current.x), min(limits[2], current.y), max(limits[3], current.y)] if limits else [current.x, current.x, current.y, current.y]
        inputs = u.NiagaraDataInterfaceArrayFunctionLibrary.get_niagara_array_vector4(mud.get_editor_property('simulation'), 'User.BrushWorldPositions')
        row['max_point_inputs'] = max(row['max_point_inputs'], len(inputs))
        if len(inputs) not in row['point_input_counts_observed']:
            row['point_input_counts_observed'].append(len(inputs))
        interval = 10 if name == 'sustained' else 2
        if t > 2 and now - STATE['last_sample'] > interval:
            row['samples'].append(_sample(world, mud))
            STATE['last_sample'] = time.monotonic()
            _persist()
    except Exception as exc:
        STATE.setdefault('rows', []).append({'name': 'harness_error', 'pass': False, 'error': repr(exc)})
        _persist(True)
        handle = STATE.pop('handle', None)
        if handle:
            u.unregister_slate_post_tick_callback(handle)
        u.EditorLevelLibrary.editor_end_play()
        u.log_error('MUD_REGRESSION_ERROR ' + repr(exc))

