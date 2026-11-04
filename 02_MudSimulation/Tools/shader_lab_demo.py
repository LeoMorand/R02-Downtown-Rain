"""Build a separate map and verify the global shader consumes live mud output.

Run in FluidNinjaStudy only, after installing Plugins/MudShaderLab.
This never edits the Evolution comparison map or the vendor blueprint.
"""
import json
import math
import time
from pathlib import Path
import unreal as u

OUT = Path('D:/aco/unreal/Stormfall/Verification/MudShaderLab')
MAP = '/Game/MudStudy/Maps/L_Mud_ShaderLab'
MAT = '/Game/MudStudy/ShaderLab/M_NormalDiagnostic'
_callback = None
_started = None
_samples = []


def build_state_material():
    path = '/Game/MudStudy/ShaderLab/M_StateDiagnostic'
    mat = u.load_asset(path)
    if mat is None:
        mat = u.AssetToolsHelpers.get_asset_tools().create_asset(
            'M_StateDiagnostic', '/Game/MudStudy/ShaderLab', u.Material, u.MaterialFactoryNew())
    u.MaterialEditingLibrary.delete_all_material_expressions(mat)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    node = u.MaterialEditingLibrary.create_material_expression(mat, u.MaterialExpressionTextureSampleParameter2D)
    node.set_editor_property('parameter_name', 'VelocityDensityBuffer')
    node.set_editor_property('texture', u.load_asset('/Game/MudStudy/Rebuild/Textures/T_SourceVelocityDensity_20261025'))
    node.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    assert u.MaterialEditingLibrary.connect_material_property(node, 'B', u.MaterialProperty.MP_EMISSIVE_COLOR)
    u.MaterialEditingLibrary.recompile_material(mat)
    u.EditorAssetLibrary.save_loaded_asset(mat)
    return mat


def build():
    assert 'FluidNinjaStudy' in u.Paths.project_dir(), 'Select the mud research project.'
    assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    cls = u.load_class(None, '/Script/MudShaderIntegration.MudShaderPreviewActor')
    assert cls, 'MudShaderLab plugin must be installed before editor startup.'
    mat = u.load_asset(MAT)
    if mat is None:
        mat = u.AssetToolsHelpers.get_asset_tools().create_asset(
            'M_NormalDiagnostic', '/Game/MudStudy/ShaderLab', u.Material, u.MaterialFactoryNew())
        mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
        mat.set_editor_property('two_sided', True)
        node = u.MaterialEditingLibrary.create_material_expression(mat, u.MaterialExpressionTextureSampleParameter2D)
        node.set_editor_property('parameter_name', 'MudNormalBuffer')
        node.set_editor_property('texture', u.load_asset('/Game/MudStudy/Rebuild/Textures/T_SourceVelocityDensity_20261025'))
        node.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        u.MaterialEditingLibrary.connect_material_property(node, 'RGB', u.MaterialProperty.MP_EMISSIVE_COLOR)
        u.MaterialEditingLibrary.recompile_material(mat)
        u.EditorAssetLibrary.save_loaded_asset(mat)

    if u.EditorAssetLibrary.does_asset_exist(MAP):
        u.EditorLoadingAndSavingUtils.load_map(MAP)
        return MAP
    assert u.EditorLevelLibrary.new_level(MAP)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    mud = actors.spawn_actor_from_class(cls, u.Vector(0, 0, 0))
    mud.set_actor_label('ShaderLab_LiveMud_And_RDGNormal')
    mud.set_editor_property('solver', u.load_asset('/Game/MudStudy/Evolution/Niagara/NS_Evolution_Current'))
    mud.set_editor_property('surface_material', build_state_material())
    assert mud.get_editor_property('solver') and mud.get_editor_property('surface_material')
    mud.set_editor_property('normal_preview_material', mat)
    mud.set_editor_property('output_resolution', 512)
    mud.set_editor_property('track_player', False)
    mud.get_editor_property('normal_pass').set_editor_property('height_scale', 100)
    brush = actors.spawn_actor_from_class(u.StaticMeshActor, u.Vector(-400, 0, 30))
    brush.set_actor_label('ShaderLab_TestBrush')
    mesh = brush.get_component_by_class(u.StaticMeshComponent)
    mesh.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'))
    mesh.set_mobility(u.ComponentMobility.MOVABLE)
    brush.set_actor_scale3d(u.Vector(0.4, 0.4, 0.4))
    mud.set_editor_property('brush_actors', [brush])
    light = actors.spawn_actor_from_class(u.DirectionalLight, u.Vector(0, 0, 1500))
    light.set_actor_rotation(u.Rotator(pitch=-50, yaw=20, roll=0), False)
    light.get_component_by_class(u.DirectionalLightComponent).set_intensity(10)
    sky = actors.spawn_actor_from_class(u.SkyLight, u.Vector(0, 0, 1500))
    sky_comp = sky.get_component_by_class(u.SkyLightComponent)
    sky_comp.set_editor_property('source_type', u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sky_comp.set_editor_property('cubemap', u.load_asset('/Engine/MapTemplates/Sky/SunsetAmbientCubemap'))
    sky_comp.set_intensity(3)
    for label, pos in [('LIVE STATE / B HEIGHT', u.Vector(0, 1100, 60)),
                       ('GLOBAL COMPUTE / RDG NORMAL', u.Vector(2400, 1100, 60))]:
        text = actors.spawn_actor_from_class(u.TextRenderActor, pos)
        text.text_render.set_text(label)
        text.text_render.set_world_size(60)
        text.set_actor_rotation(u.Rotator(pitch=0, yaw=90, roll=0), False)
    u.EditorLevelLibrary.set_level_viewport_camera_info(u.Vector(1200, 2600, 3500), u.Rotator(pitch=-54, yaw=-90, roll=0))
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert u.EditorLoadingAndSavingUtils.save_map(world, MAP)
    return MAP


def verify():
    global _callback, _started, _samples
    _started = time.monotonic()
    _samples = []
    u.EditorLevelLibrary.editor_play_simulate()
    _callback = u.register_slate_post_tick_callback(_tick)


def _tick(delta):
    global _callback
    elapsed = time.monotonic() - _started
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    try:
        if elapsed > 90:
            raise RuntimeError('Timed out waiting for live shader output')
        if not world:
            return
        muds = u.GameplayStatics.get_all_actors_of_class(world, u.MudShaderPreviewActor)
        if not muds:
            return
        mud = muds[0]
        for a in u.GameplayStatics.get_all_actors_of_class(world, u.StaticMeshActor):
            if a.get_actor_label() == 'ShaderLab_TestBrush':
                a.set_actor_location(u.Vector(400 * math.sin(elapsed), 100 * math.cos(elapsed), 30), False, False)
        normal_pass = mud.get_editor_property('normal_pass')
        output = normal_pass.get_editor_property('normal_output')
        if elapsed < 8 or not output or not normal_pass.get_editor_property('last_dispatch_accepted'):
            return
        if len(_samples) < 3:
            pixels = u.RenderingLibrary.read_render_target_raw(world, output)
            count = len(pixels)
            deviation = max((abs(p.r - 0.5) + abs(p.g - 0.5) for p in pixels), default=0)
            _samples.append({'pixels': count, 'max_xy_deviation': deviation})
            return
        preview_mid = mud.get_editor_property('normal_preview').get_material(0)
        bound = isinstance(preview_mid, u.MaterialInstanceDynamic) and preview_mid.get_texture_parameter_value('MudNormalBuffer') == output
        source_mid = mud.get_editor_property('surface_mid')
        source_bound = bool(source_mid) and source_mid.get_texture_parameter_value('VelocityDensityBuffer') == mud.get_editor_property('output')
        result = {'map': MAP, 'output': output.get_path_name(), 'dispatch_accepted': True,
                  'preview_bound': bound, 'source_bound': source_bound, 'samples': _samples,
                  'pass': bound and source_bound and all(s['pixels'] == 512 * 512 for s in _samples)
                      and any(s['max_xy_deviation'] > 0.001 for s in _samples)}
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / 'live_binding.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        u.unregister_slate_post_tick_callback(_callback)
        _callback = None
        u.EditorLevelLibrary.editor_end_play()
        u.log('MUD_SHADER_LIVE_RESULT ' + json.dumps(result))
    except Exception as exc:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / 'live_binding.json').write_text(json.dumps({'pass': False, 'error': str(exc)}), encoding='utf-8')
        if _callback:
            u.unregister_slate_post_tick_callback(_callback)
            _callback = None
        u.EditorLevelLibrary.editor_end_play()
        u.log_error(str(exc))


