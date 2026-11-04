"""Read-only asset/texture audit for the completed integration."""
import unreal, json
from pathlib import Path

root = Path('D:/aco/unreal/Stormfall')
base = '/Game/Stormfall/ShirtTrial'
dest = base + '/Wetness'
L = unreal.MaterialEditingLibrary
source = unreal.load_asset('/Game/Stormfall/Weather/Cloth/Reference/M_Cloth_Reference_NodesOnly')
master = unreal.load_asset(dest + '/Materials/M_Shirt_ReferenceWet')
source_nodes = list(L.get_material_expressions(source))
nodes = list(L.get_material_expressions(master))
source_layout = [(e.get_name(), e.get_editor_property('material_expression_editor_x'), e.get_editor_property('material_expression_editor_y')) for e in source_nodes]
copy_layout = [(e.get_name(), e.get_editor_property('material_expression_editor_x'), e.get_editor_property('material_expression_editor_y')) for e in nodes[:len(source_nodes)]]
assert source_layout == copy_layout
visited, textures, empty = set(), {}, []

def walk(asset):
    path = asset.get_path_name()
    if path in visited: return
    visited.add(path)
    exprs = L.get_material_function_expressions(asset) if isinstance(asset, unreal.MaterialFunction) else L.get_material_expressions(asset)
    for e in exprs:
        if isinstance(e, unreal.MaterialExpressionTextureSample):
            t = e.get_editor_property('texture')
            if not t: empty.append(e.get_path_name())
            else: textures[t.get_path_name()] = t
        if isinstance(e, unreal.MaterialExpressionMaterialFunctionCall):
            f = e.get_editor_property('material_function')
            assert f, e.get_path_name()
            walk(f)

walk(master)
assert not empty, empty
region_reports = []
for region in ['Front','Back','Sleeve_Left','Sleeve_Right','Cuffs_Boundry']:
    mi = unreal.load_asset(dest + '/Materials/MI_ShirtWet_' + region)
    maps = {}
    for param in ['Garment Albedo','Garment Normal','Garment Glossiness','Garment AO','Garment Specular']:
        t = L.get_material_instance_texture_parameter_value(mi, param)
        assert t, (region,param)
        assert bool(t.get_editor_property('srgb')) == (param == 'Garment Albedo'), t.get_path_name()
        if param == 'Garment Normal':
            assert t.get_editor_property('compression_settings') == unreal.TextureCompressionSettings.TC_NORMALMAP
        textures[t.get_path_name()] = t
        maps[param] = t.get_path_name()
    scalars = {p:float(L.get_material_instance_scalar_parameter_value(mi,p)) for p in ['Wetness','Wet Roughness','Wet Albedo Multiplier','Weave Normal Strength','Fuzz Normal Strength']}
    assert abs(scalars['Wetness']) < 1e-5
    assert abs(scalars['Wet Roughness']-.46) < 1e-5
    assert abs(scalars['Wet Albedo Multiplier']-.48) < 1e-5
    region_reports.append({'region':region,'textures':maps,'scalars':scalars})

texture_reports = []
for path,t in sorted(textures.items()):
    info = {'path':path,'srgb':bool(t.get_editor_property('srgb')),
            'compression':str(t.get_editor_property('compression_settings')),
            'max_texture_size':int(t.get_editor_property('max_texture_size'))}
    if 'Normalmap' in info['compression'] or t.get_name().endswith('_Normal'):
        info['flip_green_channel'] = bool(t.get_editor_property('flip_green_channel'))
    texture_reports.append(info)

mesh_reports = []
for name in ['SK_MotionStudio_Shirt_Manny','SK_Manny_MotionStudio_Shirt']:
    mesh = unreal.load_asset(base + '/' + name)
    slots=[]
    for slot in mesh.get_editor_property('materials'):
        label = str(slot.get_editor_property('material_slot_name'))
        material = slot.get_editor_property('material_interface')
        assert material
        if label.startswith('MS_Shirt_') and label != 'MS_Shirt_Bottons':
            assert material.get_path_name().startswith(dest+'/Materials/MI_ShirtWet_'), (name,label)
        slots.append({'slot':label,'material':material.get_path_name()})
    mesh_reports.append({'mesh':mesh.get_path_name(),'skeleton':mesh.get_editor_property('skeleton').get_path_name(),'slots':slots})

report = {'passed':True,'original_reference_layout_preserved':True,
          'reference_expression_count':len(source_nodes),'shirt_expression_count':len(nodes),
          'recursive_empty_texture_samples':empty,'visited_functions_and_material':sorted(visited),
          'textures':texture_reports,'regions':region_reports,'meshes':mesh_reports,
          'statistics':str(L.get_statistics(master)),
          'note':'Cloth fuzz uses the material ClearCoat storage field, which is CustomData0 for the Cloth shading model. No clear-coat shading model was added.'}
(root/'Verification/ShirtWetness/final_assets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SHIRT_ASSET_AUDIT_PASSED '+json.dumps({'regions':len(region_reports),'textures':len(textures),'functions_and_materials':len(visited),'statistics':report['statistics']}))
