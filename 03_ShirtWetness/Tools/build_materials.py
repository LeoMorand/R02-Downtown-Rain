"""Adapt a COPY of the user's cloth reference to the fitted Manny shirt.
Run inside the Stormfall editor. Never rebuild/delete the source reference graph.
"""
import unreal, json, math
from pathlib import Path

ROOT = Path('D:/aco/unreal/Stormfall')
BASE = '/Game/Stormfall/ShirtTrial'
DEST = BASE + '/Wetness'
MASTER = DEST + '/Materials/M_Shirt_ReferenceWet'
A = unreal.EditorAssetLibrary
L = unreal.MaterialEditingLibrary
T = unreal.AssetToolsHelpers.get_asset_tools()
assert 'stormfall' in unreal.Paths.project_dir().lower()
m = unreal.load_asset(MASTER)
assert m, MASTER
old = list(L.get_material_expressions(m))
by = {str(e.get_editor_property('desc')): e for e in old}
assert 'Shirt Albedo' not in by, 'Already adapted. Inspect; do not append twice.'
positions = {e.get_name(): [e.get_editor_property('material_expression_editor_x'), e.get_editor_property('material_expression_editor_y')] for e in old}

def node(typ, label, x, y, **props):
    e = L.create_material_expression(m, getattr(unreal, 'MaterialExpression' + typ), x, y)
    e.set_editor_property('desc', label)
    for k, v in props.items(): e.set_editor_property(k, v)
    return e

def wire(src, target, pin='', output=''):
    assert L.connect_material_expressions(src, output, target, pin), (src.get_name(), target.get_name(), pin, output)

def prop(src, name, output=''):
    assert L.connect_material_property(src, output, getattr(unreal.MaterialProperty, 'MP_' + name)), name

def scalar(label, default, x, y, group='02 Wetness'):
    return node('ScalarParameter', label, x, y, parameter_name=label, default_value=default, group=group)

def texture(label, suffix, y, normal=False):
    tex = unreal.load_asset(BASE + '/Textures/T_MSShirt_Front_' + suffix)
    assert tex
    return node('TextureSampleParameter2D', label, 400, y, parameter_name=label,
                texture=tex, group='01 Shirt Textures',
                sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else
                unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if suffix == 'Diffuse' else unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)

# Use the actual shirt maps, rather than replacing its authored appearance.
albedo = texture('Garment Albedo', 'Diffuse', 4600)
baked = texture('Garment Normal', 'Normal', 5000, True)
gloss = texture('Garment Glossiness', 'Glossiness', 5500)
ao = texture('Garment AO', 'AmbientOcclusion', 5900)
albedo.set_editor_property('desc', 'Shirt Albedo')
tint = node('Multiply', 'Shirt Albedo Tint', 850, 4600)
wire(albedo, tint, 'A', 'RGB'); wire(by['Base Color'], tint, 'B')
wire(tint, by['Base Color Add'], 'A')
cavity = node('Multiply', 'Subtle textile cavity', 850, 4800, const_b=0.15)
wire(by['Detail Cloth / Self Made'], cavity, 'A', 'Detail Cavity')
wire(cavity, by['Base Color Add'], 'B')
zero = node('Constant', 'Remove duplicate albedo addition', 1250, 4600, r=0.0)
wire(zero, by['Base Color Final Add'], 'B')
by['Base Color'].set_editor_property('default_value', unreal.LinearColor(1, 1, 1, 1))

# Gloss is data, so invert in linear space; retain its spatial variation.
inv = node('OneMinus', 'Gloss to roughness', 850, 5500)
wire(gloss, inv, '', 'R')
scale = node('Multiply', 'Shirt roughness scale', 1050, 5500)
wire(inv, scale, 'A'); wire(by['Roughness'], scale, 'B')
lo = node('Max', 'Dry roughness minimum', 1250, 5500, const_b=0.62)
hi = node('Min', 'Dry roughness maximum', 1450, 5500, const_b=0.92)
wire(scale, lo, 'A'); wire(lo, hi, 'A'); wire(hi, by['Roughness Add'], 'A')
wet_rough = scalar('Wet Roughness', 0.38, 1700, 5700)
wire(wet_rough, by['Roughness Lerp'], 'B')
prop(ao, 'AMBIENT_OCCLUSION', 'R')

# Keep the source's supplementary folds/weave, layer the shirt bake beneath them.
blend_fn = unreal.load_asset('/Engine/Functions/Engine_MaterialFunctions02/Utility/BlendAngleCorrectedNormals')
blend = node('MaterialFunctionCall', 'Shirt baked and detail normals', 3300, 5000, material_function=blend_fn)
wire(baked, blend, 'BaseNormal', 'RGB'); wire(by['Normal Blend 3'], blend, 'AdditionalNormal')
prop(blend, 'NORMAL')
by['Base Normal Intensity'].set_editor_property('default_value', 0.96)
by['Crumple Normal Intensity'].set_editor_property('default_value', 0.98)
by['Roughness'].set_editor_property('default_value', 1.0)
by['Wetness'].set_editor_property('default_value', 0.0)
by['Metallic'].set_editor_property('default_value', 0.0)

# Explicit defaults, including the four-channel exclusion input.
detail_masks = node('Constant4Vector', 'Detail exclusion zero means cloth', 2150, 4750, constant=unreal.LinearColor(0, 0, 0, 0))
wire(detail_masks, by['Detail Cloth / Self Made'], 'Detail Masks')
fuzz_param = next(e for e in old if isinstance(e, unreal.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name')) == 'Cloth Fuzz Amount')
fuzz_param.set_editor_property('default_value', 0.12)
fade = node('LinearInterpolate', 'Wet fibers reduce fuzz', 2450, 4500, const_a=1.0, const_b=0.2)
wire(by['Bound color wetness'], fade, 'Alpha')
fuzz = node('Multiply', 'Wet cloth fuzz amount', 2850, 4500)
wire(fade, fuzz, 'A'); wire(fuzz_param, fuzz, 'B')
# Cloth CustomData0 is not exposed by this build's Python MaterialProperty enum.
# This build stores Cloth CustomData0 in EditorOnlyData.ClearCoat. Finalize with
# the native editor.set_property command emitted below, then recompile/save.

# Parameterize absorption without destroying the original wet-color node.
absorption = scalar('Wet Albedo Multiplier', 0.55, 1400, 4100)
wetcolor = by['Absorbed wet color']
inputs = list(wetcolor.get_editor_property('inputs'))
extra = unreal.CustomInput(); extra.set_editor_property('input_name', 'Absorption')
wetcolor.set_editor_property('inputs', inputs + [extra])
wetcolor.set_editor_property('code', 'return max(Dry,0)*clamp(Absorption,0.05,1.0);')
wire(absorption, wetcolor, 'Absorption')

# The authored specular map controls a bounded dielectric response.
regions = {'Front':'Shirt Front', 'Back':'Shirt Back', 'Sleeve_Left':'Left Sleeve',
           'Sleeve_Right':'Right Sleeve', 'Cuffs_Boundry':'Shirt Texture Black'}
specular_maps = {}
source = ROOT / 'ImportStaging/Shirt/Source/Custom Textures/Shirt Custom Textures'
for region, stem in regions.items():
    name = 'T_Shirt_' + region + '_Specular'
    path = DEST + '/Textures/' + name
    tex = unreal.load_asset(path)
    if not tex:
        task = unreal.AssetImportTask(); task.filename = str(source / (stem + '_Specular.jpg'))
        task.destination_path = DEST + '/Textures'; task.destination_name = name
        task.automated = True; task.save = True
        T.import_asset_tasks([task]); tex = unreal.load_asset(path)
    assert tex, path
    tex.set_editor_property('srgb', False)
    tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property('max_texture_size', 2048)
    A.save_loaded_asset(tex); specular_maps[region] = tex
spec = node('TextureSampleParameter2D', 'Garment Specular', 400, 6300,
            parameter_name='Garment Specular', texture=specular_maps['Front'],
            group='01 Shirt Textures', sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
spec_scale = node('Multiply', 'Dielectric specular variation', 850, 6300, const_b=0.25)
spec_bias = node('Add', 'Dielectric specular floor', 1100, 6300, const_b=0.25)
wire(spec, spec_scale, 'A', 'R'); wire(spec_scale, spec_bias, 'A'); prop(spec_bias, 'SPECULAR')

comment = node('Comment', 'Shirt adaptation', 250, 4400,
               text='SHIRT INPUTS: original UV0 albedo / DirectX normal / gloss / AO / specular. Reference wetness and detail branches retained. Plastic buttons remain separate.')
m.set_editor_property('two_sided', True)
L.set_material_usage(m, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
L.recompile_material(m)
assert positions == {e.get_name(): [e.get_editor_property('material_expression_editor_x'), e.get_editor_property('material_expression_editor_y')] for e in old}
for e in L.get_material_expressions(m):
    if isinstance(e, unreal.MaterialExpressionTextureSample): assert e.get_editor_property('texture'), e.get_name()
A.save_loaded_asset(m)

instances = {}
for region in regions:
    name = 'MI_ShirtWet_' + region
    mi = unreal.load_asset(DEST + '/Materials/' + name)
    if not mi: mi = T.create_asset(name, DEST + '/Materials', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(mi, m)
    for param, suffix in [('Garment Albedo','Diffuse'), ('Garment Normal','Normal'), ('Garment Glossiness','Glossiness'), ('Garment AO','AmbientOcclusion')]:
        tex = unreal.load_asset(BASE + '/Textures/T_MSShirt_' + region + '_' + suffix)
        assert tex
        assert bool(tex.get_editor_property('srgb')) == (suffix == 'Diffuse'), tex.get_path_name()
        L.set_material_instance_texture_parameter_value(mi, param, tex)
    L.set_material_instance_texture_parameter_value(mi, 'Garment Specular', specular_maps[region])
    for param, value in [('Wetness',0), ('Wet Roughness',0.46), ('Wet Albedo Multiplier',0.48), ('Weave Normal Strength',0.12), ('Fuzz Normal Strength',0.06), ('Weave Tiling',24), ('Fuzz Tiling',48)]:
        L.set_material_instance_scalar_parameter_value(mi, param, value)
    L.update_material_instance(mi); A.save_loaded_asset(mi); instances[region] = mi

# Use the cuff's black fabric for fine sewing threads. Keep actual plastic buttons.
meshes = []
for mesh_name in ['SK_MotionStudio_Shirt_Manny', 'SK_Manny_MotionStudio_Shirt']:
    mesh = unreal.load_asset(BASE + '/' + mesh_name); mats = list(mesh.get_editor_property('materials')); slots = []
    for slot in mats:
        slot_name = str(slot.get_editor_property('material_slot_name'))
        region = slot_name.removeprefix('MS_Shirt_')
        if region in instances: slot.set_editor_property('material_interface', instances[region])
        elif region == 'Bottons_Threads': slot.set_editor_property('material_interface', instances['Cuffs_Boundry'])
        slots.append({'slot':slot_name,'material':slot.get_editor_property('material_interface').get_path_name()})
    mesh.set_editor_property('materials', mats); A.save_loaded_asset(mesh)
    meshes.append({'mesh':mesh.get_path_name(),'slots':slots})

report = {'master':m.get_path_name(), 'reference':'/Game/Stormfall/Weather/Cloth/Reference/M_Cloth_Reference_NodesOnly',
          'original_positions_preserved':True, 'empty_texture_samples':0,
          'instances':{k:v.get_path_name() for k,v in instances.items()}, 'meshes':meshes,
          'statistics':str(L.get_statistics(m)), 'source_reference_modified':False,
          'normal_convention':'Existing shirt imports already flip green to DirectX; no second flip.',
          'dry_roughness_range':[0.62,0.92], 'master_wet_roughness':0.38, 'master_wet_albedo_multiplier':0.55,
          'shirt_instance_wet_roughness':0.46, 'shirt_instance_wet_albedo_multiplier':0.48}
(ROOT/'Verification/ShirtWetness/materials.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
finalize = {'action':'set_property', 'args':{
    'objectPath':m.get_editor_property('editor_only_data').get_path_name(),
    'propertyName':'ClearCoat',
    'value':"(Expression=MaterialExpressionMultiply'"+fuzz.get_path_name()+"',OutputIndex=0)"}}
(ROOT/'Verification/ShirtWetness/native_finalize.json').write_text(json.dumps(finalize,indent=2),encoding='utf-8')
print('SHIRT_MATERIALS_COMPLETE ' + json.dumps(report))
