"""Idempotent wet-cotton look pass on M_Shirt_ReferenceWet (run after upgrade_production.py).
Adds an irregular wet front, saturated/darker wet albedo with skin show-through and a tide line,
and fibre-broken wet roughness. Original nodes are kept; only BaseColor and Roughness are rewired.
"""
import unreal, json
from pathlib import Path

ROOT = Path('D:/aco/unreal/Stormfall')
DEST = '/Game/Stormfall/ShirtTrial/Wetness'
A = unreal.EditorAssetLibrary
L = unreal.MaterialEditingLibrary
master = unreal.load_asset(DEST+'/Materials/M_Shirt_ReferenceWet')
assert master
by = {str(e.get_editor_property('desc')): e for e in L.get_material_expressions(master)}
GROUP = '04 Wet Cotton Look'

def create(kind, label, x, y, **props):
    e = by.get(label)
    if e is None:
        e = L.create_material_expression(master, getattr(unreal, 'MaterialExpression'+kind), x, y)
        e.set_editor_property('desc', label)
        by[label] = e
    for k, v in props.items(): e.set_editor_property(k, v)
    return e

def wire(a, b, pin='', output=''):
    assert L.connect_material_expressions(a, output, b, pin), (str(a), str(b), pin)

def custom(label, x, y, shader, inputs, output_type):
    node = create('Custom', label, x, y, code=(ROOT/'Shaders'/shader).read_text(encoding='utf-8'),
                  output_type=output_type)
    pins = []
    for name in inputs:
        item = unreal.CustomInput(); item.set_editor_property('input_name', name); pins.append(item)
    node.set_editor_property('inputs', pins)
    return node

def scalar(label, name, value, x, y, priority):
    return create('ScalarParameter', label, x, y, parameter_name=name, default_value=value,
                  group=GROUP, sort_priority=priority)

F2 = unreal.CustomMaterialOutputType.CMOT_FLOAT2
F1 = unreal.CustomMaterialOutputType.CMOT_FLOAT1
F3 = unreal.CustomMaterialOutputType.CMOT_FLOAT3
local = by['Wetness Mesh Local Position']
wetness = by['Bound color wetness']

front = custom('Wet front breakup', 3400, 3900, 'ShirtWetFront.hlsl', ['W', 'P', 'Breakup'], F2)
wire(wetness, front, 'W'); wire(local, front, 'P')
wire(scalar('Wet Front Breakup', 'Wet Front Breakup', 1.0, 3100, 3800, 0), front, 'Breakup')

color = custom('Wet cotton color', 3900, 4100, 'ShirtWetColor.hlsl',
               ['Dry', 'WF', 'P', 'Absorption', 'Saturation', 'Skin', 'ShowThrough', 'Edge'], F3)
wire(by['Base Color Final Add'], color, 'Dry'); wire(front, color, 'WF'); wire(local, color, 'P')
wire(by['Wet Albedo Multiplier'], color, 'Absorption')
wire(scalar('Wet Saturation', 'Wet Saturation', 1.4, 3500, 4250, 1), color, 'Saturation')
skin = create('VectorParameter', 'Skin Under Cloth', 3500, 4400, parameter_name='Skin Under Cloth',
              default_value=unreal.LinearColor(0.55, 0.36, 0.28, 1), group=GROUP, sort_priority=2)
wire(skin, color, 'Skin')
wire(scalar('Skin Show Through', 'Skin Show Through', 0.6, 3500, 4600, 3), color, 'ShowThrough')
wire(scalar('Wet Edge Darkening', 'Wet Edge Darkening', 0.6, 3500, 4750, 4), color, 'Edge')
assert L.connect_material_property(color, '', unreal.MaterialProperty.MP_BASE_COLOR)

rough = custom('Wet cotton roughness', 3900, 3400, 'ShirtWetRoughness.hlsl',
               ['DryRoughness', 'WF', 'WetRoughness', 'FilmRoughness', 'FilmAmount'], F1)
wire(by['Roughness Add'], rough, 'DryRoughness'); wire(front, rough, 'WF')
wet_rough = by['Wet Roughness']; wet_rough.set_editor_property('default_value', 0.68)
wire(wet_rough, rough, 'WetRoughness')
wire(scalar('Wet Film Roughness', 'Wet Film Roughness', 0.3, 3500, 3300, 5), rough, 'FilmRoughness')
wire(scalar('Wet Film Amount', 'Wet Film Amount', 0.3, 3500, 3450, 6), rough, 'FilmAmount')
assert L.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)

L.recompile_material(master)
A.save_loaded_asset(master)

# Instances carried the satin-era overrides (Wet Roughness 0.46, Albedo 0.48); move them to the new look.
report = {}
for part in ['Front', 'Back', 'Sleeve_Left', 'Sleeve_Right', 'Cuffs_Boundry']:
    mi = unreal.load_asset(DEST+'/Materials/MI_ShirtWet_'+part)
    L.set_material_instance_scalar_parameter_value(mi, 'Wet Roughness', 0.68)
    L.set_material_instance_scalar_parameter_value(mi, 'Wet Albedo Multiplier', 0.55)
    L.update_material_instance(mi)
    A.save_loaded_asset(mi)
    report[part] = {n: L.get_material_instance_scalar_parameter_value(mi, n)
                    for n in ['Wet Roughness', 'Wet Albedo Multiplier', 'Wet Saturation', 'Skin Show Through']}
out = ROOT/'Verification/ShirtWetness/Look'; out.mkdir(parents=True, exist_ok=True)
(out/'look_parameters.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
