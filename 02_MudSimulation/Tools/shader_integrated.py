"""Author only ShaderLab assets; preserve the existing mud reference gallery."""
import json
import math
import time
import statistics
from pathlib import Path
import unreal as u

ROOT = '/Game/MudStudy/ShaderLab'
MAP = '/Game/MudStudy/Maps/L_Mud_ShaderIntegrated'
OUT = Path('D:/aco/unreal/Stormfall/Verification/MudShaderIntegrated')


def _node(mat, cls, **props):
    node = u.MaterialEditingLibrary.create_material_expression(mat, cls)
    for key, value in props.items():
        node.set_editor_property(key, value)
    return node


def _inputs(names):
    result = []
    for name in names:
        value = u.CustomInput()
        value.set_editor_property('input_name', name)
        result.append(value)
    return result


def build_material():
    path = ROOT + '/M_Surface_GlobalNormal'
    if u.EditorAssetLibrary.does_asset_exist(ROOT + '/MI_Surface_GlobalNormal'):
        return u.load_asset(ROOT + '/MI_Surface_GlobalNormal')
    if u.EditorAssetLibrary.does_asset_exist(path):
        assert u.EditorAssetLibrary.delete_asset(path), 'Remove incomplete new lab parent only'
    source = '/Game/MudStudy/Evolution/Materials/M_Surface_Rebuilt'
    mat = u.EditorAssetLibrary.duplicate_asset(source, path)
    assert mat
    original = u.MaterialEditingLibrary.get_material_property_input_node(mat, u.MaterialProperty.MP_NORMAL)
    pin = u.MaterialEditingLibrary.get_material_property_input_node_output_name(mat, u.MaterialProperty.MP_NORMAL)
    assert original
    texture = _node(mat, u.MaterialExpressionTextureObjectParameter,
                    parameter_name='MudNormalBuffer',
                    texture=u.load_asset('/Game/MudStudy/Rebuild/Textures/T_SourceVelocityDensity_20261025'),
                    sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    position = _node(mat, u.MaterialExpressionWorldPosition)
    center = _node(mat, u.MaterialExpressionVectorParameter, parameter_name='MudSimCenter', default_value=u.LinearColor(0, 0, 0, 0))
    size = _node(mat, u.MaterialExpressionVectorParameter, parameter_name='MudWorldSize', default_value=u.LinearColor(2000, 2000, 0, 0))
    read = _node(mat, u.MaterialExpressionCustom,
                 code='float2 uv=(World.xy-Center.xy)/max(Size.xy,float2(0.001,0.001))+0.5;\nreturn normalize(Texture2DSampleLevel(NormalTexture,NormalTextureSampler,uv,0).rgb*2-1);',
                 output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,
                 inputs=_inputs(['NormalTexture', 'World', 'Center', 'Size']))
    for node, name in [(texture, 'NormalTexture'), (position, 'World'), (center, 'Center'), (size, 'Size')]:
        assert u.MaterialEditingLibrary.connect_material_expressions(node, '', read, name)
    transform = _node(mat, u.MaterialExpressionTransform,
                      transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
                      transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
    assert u.MaterialEditingLibrary.connect_material_expressions(read, '', transform, '')
    weight = _node(mat, u.MaterialExpressionScalarParameter, parameter_name='UseGlobalNormal', default_value=1)
    blend = _node(mat, u.MaterialExpressionCustom,
                  code='return normalize(lerp(Original,Computed,saturate(Weight)));',
                  output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,
                  inputs=_inputs(['Original', 'Computed', 'Weight']))
    assert u.MaterialEditingLibrary.connect_material_expressions(original, pin, blend, 'Original')
    assert u.MaterialEditingLibrary.connect_material_expressions(transform, '', blend, 'Computed')
    assert u.MaterialEditingLibrary.connect_material_expressions(weight, '', blend, 'Weight')
    assert u.MaterialEditingLibrary.connect_material_property(blend, '', u.MaterialProperty.MP_NORMAL)
    u.MaterialEditingLibrary.recompile_material(mat)
    u.EditorAssetLibrary.save_loaded_asset(mat)
    mi = u.EditorAssetLibrary.duplicate_asset('/Game/MudStudy/Evolution/Materials/MI_Surface_Rebuilt', ROOT + '/MI_Surface_GlobalNormal')
    assert mi
    u.MaterialEditingLibrary.set_material_instance_parent(mi, mat)
    u.MaterialEditingLibrary.update_material_instance(mi)
    u.EditorAssetLibrary.save_loaded_asset(mi)
    return mi


def build():
    assert 'FluidNinjaStudy' in u.Paths.project_dir()
    mat = build_material()
    if u.EditorAssetLibrary.does_asset_exist(MAP):
        u.EditorLoadingAndSavingUtils.load_map(MAP)
        return MAP
    assert u.EditorLevelLibrary.new_level(MAP)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    mud = actors.spawn_actor_from_class(u.MudShaderPreviewActor, u.Vector(0, 0, 0))
    mud.set_actor_label('Integrated_Mud_GlobalNormal')
    mud.set_editor_property('solver', u.load_asset('/Game/MudStudy/Evolution/Niagara/NS_Evolution_Current'))
    mud.set_editor_property('surface_material', mat)
    mud.set_editor_property('normal_preview_material', u.load_asset(ROOT + '/M_NormalDiagnostic'))
    mud.set_editor_property('output_resolution', 512)
    mud.set_editor_property('track_player', False)
    comp = mud.get_editor_property('normal_pass')
    comp.set_editor_property('height_scale', 30)
    comp.set_editor_property('profile_gpu', True)
    brush = actors.spawn_actor_from_class(u.StaticMeshActor, u.Vector(-400, 0, 30))
    brush.set_actor_label('Integrated_Brush')
    mesh = brush.get_component_by_class(u.StaticMeshComponent)
    mesh.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'))
    mesh.set_mobility(u.ComponentMobility.MOVABLE)
    brush.set_actor_scale3d(u.Vector(0.4, 0.4, 0.4))
    mud.set_editor_property('brush_actors', [brush])
    sun = actors.spawn_actor_from_class(u.DirectionalLight, u.Vector(0, 0, 1500))
    sun.set_actor_rotation(u.Rotator(pitch=-50, yaw=20, roll=0), False)
    sun.get_component_by_class(u.DirectionalLightComponent).set_mobility(u.ComponentMobility.MOVABLE)
    sun.get_component_by_class(u.DirectionalLightComponent).set_intensity(8)
    sky = actors.spawn_actor_from_class(u.SkyLight, u.Vector(0, 0, 1500))
    sc = sky.get_component_by_class(u.SkyLightComponent)
    sc.set_mobility(u.ComponentMobility.MOVABLE)
    sc.set_editor_property('source_type', u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sc.set_editor_property('cubemap', u.load_asset('/Engine/MapTemplates/Sky/SunsetAmbientCubemap'))
    sc.set_intensity(5)
    # A real camera is also the packaged game's default presentation.
    camera = actors.spawn_actor_from_class(u.CameraActor, u.Vector(1200, 2600, 3500))
    camera.set_actor_rotation(u.Rotator(pitch=-54, yaw=-90, roll=0), False)
    camera.set_editor_property('auto_activate_for_player', u.AutoReceiveInput.PLAYER0)
    u.EditorLevelLibrary.set_level_viewport_camera_info(u.Vector(1200, 2600, 3500), u.Rotator(pitch=-54, yaw=-90, roll=0))
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert u.EditorLoadingAndSavingUtils.save_map(world, MAP)
    return MAP


_handle = None
_begin = 0


def verify():
    global _handle, _begin
    _begin = time.monotonic()
    u.EditorLevelLibrary.editor_play_simulate()
    _handle = u.register_slate_post_tick_callback(_verify_tick)


def _verify_tick(dt):
    global _handle
    elapsed = time.monotonic() - _begin
    try:
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if not world:
            if elapsed > 90:
                raise RuntimeError('PIE did not start')
            return
        mud = u.GameplayStatics.get_all_actors_of_class(world, u.MudShaderPreviewActor)[0]
        comp = mud.get_editor_property('normal_pass')
        for actor in u.GameplayStatics.get_all_actors_of_class(world, u.StaticMeshActor):
            if actor.get_actor_label() == 'Integrated_Brush':
                actor.set_actor_location(u.Vector(400 * math.sin(elapsed), 100 * math.cos(elapsed), 30), False, False)
        count = comp.get_editor_property('producer_graph_dispatches')
        if elapsed < 8 or count < 5:
            if elapsed > 90:
                raise RuntimeError('No producer-graph normal dispatches')
            return
        output = comp.get_editor_property('normal_output')
        mid = mud.get_editor_property('surface_mid')
        # Both readbacks occur between render frames on the game thread.
        source = u.RenderingLibrary.read_render_target_raw(world, mud.get_editor_property('output'))
        normal = u.RenderingLibrary.read_render_target_raw(world, output)
        assert len(source) == len(normal) == 512 * 512
        height_error = max(abs(a.b - b.a) for a, b in zip(source, normal))
        bound = mid.get_texture_parameter_value('MudNormalBuffer') == output
        report = {'pass': bound and count > 5 and height_error == 0,
                  'producer_graph_dispatches': count, 'source_B_vs_normal_A_max_error': height_error,
                  'lit_material_normal_bound': bound,
                  'normal_switch': mid.get_scalar_parameter_value('UseGlobalNormal'),
                  'last_gpu_ms': comp.get_editor_property('last_gpu_time_ms'),
                  'gpu_timing_samples': comp.get_editor_property('gpu_timing_samples'),
                  'scope': 'Niagara post-simulation RDG dependency; opaque display may consume the pair next frame'}
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / 'runtime.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        u.unregister_slate_post_tick_callback(_handle)
        _handle = None
        u.EditorLevelLibrary.editor_end_play()
        u.log('MUD_INTEGRATED_RESULT ' + json.dumps(report))
    except Exception as exc:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / 'runtime.json').write_text(json.dumps({'pass': False, 'error': str(exc)}), encoding='utf-8')
        if _handle:
            u.unregister_slate_post_tick_callback(_handle)
            _handle = None
        u.EditorLevelLibrary.editor_end_play()
        u.log_error(str(exc))


_profile_handle = None
_profile_index = -1
_profile_begin = 0
_profile_rows = []
_profile_values = []
_profile_last_counter = -1
_profile_plan = [(512, False), (512, True), (256, True), (1024, True)]


def profile():
    global _profile_handle, _profile_index, _profile_rows
    _profile_index = -1
    _profile_rows = []
    if not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        u.EditorLevelLibrary.editor_play_simulate()
    _profile_handle = u.register_slate_post_tick_callback(_profile_tick)


def _profile_tick(dt):
    global _profile_handle, _profile_index, _profile_begin, _profile_values, _profile_last_counter
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    if not world:
        return
    mud = u.GameplayStatics.get_all_actors_of_class(world, u.MudShaderPreviewActor)[0]
    comp = mud.get_editor_property('normal_pass')
    now = time.monotonic()
    if _profile_index < 0 or now - _profile_begin > 8:
        if _profile_index >= 0:
            values = sorted(_profile_values)
            _profile_rows.append({'resolution': _profile_plan[_profile_index][0],
                                  'moving_input': _profile_plan[_profile_index][1],
                                  'samples': len(values),
                                  'median_ms': statistics.median(values) if values else None,
                                  'p95_ms': values[min(int(len(values) * .95), len(values)-1)] if values else None,
                                  'min_ms': min(values) if values else None,
                                  'max_ms': max(values) if values else None})
        _profile_index += 1
        if _profile_index == len(_profile_plan):
            OUT.mkdir(parents=True, exist_ok=True)
            (OUT / 'gpu_profile.json').write_text(json.dumps({
                'scope': 'GPU timestamps around height-normal dispatch only; not total simulation/material/frame cost',
                'rhi': 'D3D12 SM6', 'gpu': 'RTX 4060 Laptop GPU',
                'warmup_seconds_per_case': 4, 'measurement_seconds_per_case': 4,
                'solver_grid_unchanged': True, 'query_quantization_us': 1,
                'samples_are_latest_completed_query_per_game_tick': True,
                'rows': _profile_rows}, indent=2), encoding='utf-8')
            u.unregister_slate_post_tick_callback(_profile_handle)
            _profile_handle = None
            u.EditorLevelLibrary.editor_end_play()
            return
        _profile_begin = now
        _profile_values = []
        _profile_last_counter = -1
        mud.set_editor_property('output_resolution', _profile_plan[_profile_index][0])
        mud.rebuild_simulation()
        comp.set_editor_property('profile_gpu', True)
    elapsed = now - _profile_begin
    if _profile_plan[_profile_index][1]:
        for actor in u.GameplayStatics.get_all_actors_of_class(world, u.StaticMeshActor):
            if actor.get_actor_label() == 'Integrated_Brush':
                actor.set_actor_location(u.Vector(400 * math.sin(elapsed), 100 * math.cos(elapsed), 30), False, False)
    counter = comp.get_editor_property('gpu_timing_samples')
    value = comp.get_editor_property('last_gpu_time_ms')
    if elapsed >= 4 and counter != _profile_last_counter and value >= 0:
        _profile_values.append(value)
        _profile_last_counter = counter


def studio_preview():
    """Only the dedicated integration material; no reference assets are edited."""
    mi = u.load_asset(ROOT + '/MI_Surface_GlobalNormal')
    u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi, 'ColorPow', 1)
    u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi, 'ColorMult', 1)
    u.MaterialEditingLibrary.update_material_instance(mi)
    u.EditorAssetLibrary.save_loaded_asset(mi)
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    if world:
        for mud in u.GameplayStatics.get_all_actors_of_class(world, u.MudShaderPreviewActor):
            mid = mud.get_editor_property('surface_mid')
            mid.set_scalar_parameter_value('ColorPow', 1)
            mid.set_scalar_parameter_value('ColorMult', 1)
            mud.set_editor_property('use_computed_normal', True)
    return 'Dedicated integration preset: ColorPow=1, ColorMult=1'


def frozen_normal_mode(use_computed):
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    assert world
    mud = u.GameplayStatics.get_all_actors_of_class(world, u.MudShaderPreviewActor)[0]
    if not u.GameplayStatics.is_game_paused(world):
        assert u.GameplayStatics.set_game_paused(world, True)
    mid = mud.get_editor_property('surface_mid')
    mid.set_scalar_parameter_value('UseGlobalNormal', 1 if use_computed else 0)
    return {'paused': u.GameplayStatics.is_game_paused(world),
            'UseGlobalNormal': mid.get_scalar_parameter_value('UseGlobalNormal')}

