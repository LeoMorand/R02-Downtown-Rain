"""Build M_WetFootprint and place one AStormfallWetFootprints actor in R02. Idempotent.

Run in a disposable UnrealEditor-Cmd (-ExecutePythonScript) with the project otherwise closed.
Writes result.json to STORMFALL_R02_OUTPUT.
"""
import json
import os
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[2]
# Defaults to Saved/ so the script can also be run inside an open editor with the py command.
OUT = Path(os.environ.get('STORMFALL_R02_OUTPUT', str(ROOT / 'Saved/WetFootprintsInstall')))
MAP = '/Game/TA_Demos/R02_Downtown_Rain'
MAT_DIR, MAT_NAME = '/Game/Stormfall/Weather/Footprints', 'M_WetFootprint'
ACTOR_LABEL = 'WetFootprints'
L = u.MaterialEditingLibrary
EAL = u.EditorAssetLibrary


def decal_material(name):
    """New deferred-decal material. Blend mode must be set before the domain: switching the domain
    while the material is still Opaque fails to compile and the default material is used in game."""
    path = MAT_DIR + '/' + name
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)   # rebuilt from source every time; nothing hand-authored lives here
    mat = u.AssetToolsHelpers.get_asset_tools().create_asset(name, MAT_DIR, u.Material, u.MaterialFactoryNew())
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('material_domain', u.MaterialDomain.MD_DEFERRED_DECAL)
    if (mat.get_editor_property('blend_mode') != u.BlendMode.BLEND_TRANSLUCENT or
            mat.get_editor_property('material_domain') != u.MaterialDomain.MD_DEFERRED_DECAL):
        raise RuntimeError(name + ': decal domain / translucent blend did not stick')
    return mat


def build_material():
    mat = decal_material(MAT_NAME)

    def node(cls, x, y, **props):
        n = L.create_material_expression(mat, cls, x, y)
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n

    def scalar(name, value, y):
        return node(u.MaterialExpressionScalarParameter, -700, y, parameter_name=name, default_value=value, group='WetFootprint')

    uv = node(u.MaterialExpressionTextureCoordinate, -700, -200)
    life = node(u.MaterialExpressionDecalLifetimeOpacity, -700, -80)
    wet_amount = scalar('WetAmount', 0.85, 40)
    softness = scalar('EdgeSoftness', 0.25, 160)
    roughness = scalar('WetRoughness', 0.12, 300)
    custom = node(u.MaterialExpressionCustom, -350, -80,
                  code=(ROOT / 'Tools/WetFootprints/footprint_decal.hlsl').read_text(encoding='utf-8'),
                  output_type=u.CustomMaterialOutputType.CMOT_FLOAT1,
                  description='Tools/WetFootprints/footprint_decal.hlsl')
    pins = []
    for name in ['UV', 'Lifetime', 'WetAmount', 'EdgeSoftness']:
        ci = u.CustomInput(); ci.set_editor_property('input_name', name); pins.append(ci)
    custom.set_editor_property('inputs', pins)
    for src, pin in [(uv, 'UV'), (life, 'Lifetime'), (wet_amount, 'WetAmount'), (softness, 'EdgeSoftness')]:
        if not L.connect_material_expressions(src, '', custom, pin):
            raise RuntimeError('Could not connect ' + pin)
    # Wet ground reads darker and glossier: blend towards near-black albedo and low roughness.
    dark = node(u.MaterialExpressionConstant3Vector, -350, 120, constant=u.LinearColor(0.02, 0.02, 0.02, 1))
    L.connect_material_property(dark, '', u.MaterialProperty.MP_BASE_COLOR)
    L.connect_material_property(roughness, '', u.MaterialProperty.MP_ROUGHNESS)
    L.connect_material_property(custom, '', u.MaterialProperty.MP_OPACITY)
    L.recompile_material(mat)
    EAL.save_loaded_asset(mat, only_if_is_dirty=False)
    return mat


def build_ripple_material():
    mat = decal_material('M_FootstepRipple')
    uv = L.create_material_expression(mat, u.MaterialExpressionTextureCoordinate, -700, -200)
    life = L.create_material_expression(mat, u.MaterialExpressionDecalLifetimeOpacity, -700, -80)
    strength = L.create_material_expression(mat, u.MaterialExpressionScalarParameter, -700, 40)
    strength.set_editor_property('parameter_name', 'RippleStrength')
    strength.set_editor_property('default_value', 1.0)
    custom = L.create_material_expression(mat, u.MaterialExpressionCustom, -350, -80)
    custom.set_editor_property('code', (ROOT / 'Tools/WetFootprints/footstep_ripple_decal.hlsl').read_text(encoding='utf-8'))
    custom.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
    custom.set_editor_property('description', 'Tools/WetFootprints/footstep_ripple_decal.hlsl')
    pins = []
    for pin in ['UV', 'Lifetime', 'Strength']:
        ci = u.CustomInput(); ci.set_editor_property('input_name', pin); pins.append(ci)
    custom.set_editor_property('inputs', pins)
    extra = u.CustomOutput(); extra.set_editor_property('output_name', 'Opacity')
    extra.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT1)
    custom.set_editor_property('additional_outputs', [extra])
    for src, pin in [(uv, 'UV'), (life, 'Lifetime'), (strength, 'Strength')]:
        if not L.connect_material_expressions(src, '', custom, pin):
            raise RuntimeError('Could not connect ' + pin)
    # Normal only: the decal bends the water's reflection without touching its colour or roughness.
    L.connect_material_property(custom, '', u.MaterialProperty.MP_NORMAL)
    L.connect_material_property(custom, 'Opacity', u.MaterialProperty.MP_OPACITY)
    L.recompile_material(mat)
    EAL.save_loaded_asset(mat, only_if_is_dirty=False)
    return mat


def run():
    mat = build_material()
    ripple = build_ripple_material()
    cls = u.load_class(None, '/Script/Stormfall.StormfallWetFootprints')
    if not cls:
        raise RuntimeError('AStormfallWetFootprints class not found; build the C++ module first')
    # Reloading the map that is already open, right after its decal materials were deleted and
    # recreated, crashed the editor (access violation). Only load when a different map is open.
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if not world or world.get_path_name().split('.')[0] != MAP:
        if not u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(MAP):
            raise RuntimeError('Could not load ' + MAP)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    existing = [a for a in actors.get_all_level_actors() if a.get_actor_label() == ACTOR_LABEL]
    actor = existing[0] if existing else actors.spawn_actor_from_class(cls, u.Vector(0, 0, 0))
    actor.set_actor_label(ACTOR_LABEL)
    actor.set_editor_property('decal_material', mat)
    actor.set_editor_property('ripple_material', ripple)
    actor.set_editor_property('log_foot_heights', os.environ.get('WET_FOOTPRINTS_LOG_HEIGHTS') == '1')
    if not u.EditorLoadingAndSavingUtils.save_current_level():
        raise RuntimeError('Level save failed')
    return {'status': 'completed', 'material': mat.get_path_name(), 'actor': actor.get_path_name(),
            'created_actor': not existing}


OUT.mkdir(parents=True, exist_ok=True)
try:
    data = run()
except Exception:
    data = {'status': 'failed', 'error': traceback.format_exc()}
(OUT / 'result.json').write_text(json.dumps(data, indent=1), encoding='utf-8')
