"""Bounded R02 changes. Only executed by the exclusive disposable UE worker."""
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
import unreal as u


def run(mode, root, out):
    out.mkdir(parents=True, exist_ok=True)
    editor = u.get_editor_subsystem(u.EditorActorSubsystem)
    actors = editor.get_all_level_actors()
    lib = u.MaterialEditingLibrary
    ea = u.EditorAssetLibrary
    cfg = json.loads((root / 'Tools/R02/acceptance.json').read_text(encoding='utf-8'))
    if mode == 'install':
        mat = u.load_asset(cfg['ground_master'])
        nodes = list(lib.get_material_expressions(mat))
        matches = [n for n in nodes if isinstance(n, u.MaterialExpressionCustom) and
                   'ArtistRandomness' in str(n.get_editor_property('code'))]
        if len(matches) != 1:
            raise RuntimeError('Cannot uniquely identify current ripple node')
        node = matches[0]
        old = str(node.get_editor_property('code'))
        # STORMFALL_R02_CANDIDATE selects a reviewed version for A/B switching (default: ripple_candidate.hlsl).
        candidate_name = os.environ.get('STORMFALL_R02_CANDIDATE', 'ripple_candidate.hlsl')
        if candidate_name not in ('ripple_candidate.hlsl', 'ripple_candidate_v1.hlsl', 'ripple_candidate_v2.hlsl'):
            raise RuntimeError('Unknown ripple candidate: ' + candidate_name)
        candidate = (root / 'Tools/R02' / candidate_name).read_text(encoding='utf-8').strip()
        known = {(root / p).read_text(encoding='utf-8').strip() for p in
                 ['Verification/WeatherReuse/WorldPuddleRipples_Scatter.hlsl',
                  'Tools/R02/ripple_candidate_v1.hlsl', 'Tools/R02/ripple_candidate_v2.hlsl']}
        if old.strip() == candidate:
            return {'unchanged': True, 'asset': mat.get_path_name(), 'candidate': candidate_name}
        if old.strip() not in known:
            raise RuntimeError('Live ripple differs from every reviewed source. Refusing overwrite.')
        before_names = [n.get_name() for n in nodes]
        inputs = [str(i.get_editor_property('input_name')) for i in node.get_editor_property('inputs')]
        backup = root / 'Saved/Revisions' / ('Before_R02_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        relative = 'Content/' + cfg['ground_master'].removeprefix('/Game/') + '.uasset'
        source = root / relative
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=False)
        shutil.copy2(source, destination)
        (out / 'ripple-before.hlsl').write_text(old, encoding='utf-8')
        node.set_editor_property('code', candidate)
        errors = list(lib.recompile_material(mat))
        if errors:
            node.set_editor_property('code', old)
            lib.recompile_material(mat)
            raise RuntimeError('Candidate compilation failed; unsaved code restored: ' + str(errors))
        assert before_names == [n.get_name() for n in lib.get_material_expressions(mat)]
        assert inputs == [str(i.get_editor_property('input_name')) for i in node.get_editor_property('inputs')]
        assert str(node.get_editor_property('code')) == candidate
        if not ea.save_loaded_asset(mat, only_if_is_dirty=False):
            raise RuntimeError('Target material save failed')
        return {'asset': mat.get_path_name(), 'node': node.get_name(), 'backup': str(backup),
                'compile_errors': errors, 'nodes_preserved': True, 'inputs_preserved': inputs,
                'before_sha256': hashlib.sha256(old.encode()).hexdigest(),
                'after_sha256': hashlib.sha256(candidate.encode()).hexdigest(),
                'candidate': candidate_name, 'saved_assets': [mat.get_path_name()]}
    rows = []
    for actor in actors:
        origin, extent = actor.get_actor_bounds(False)
        materials = sorted({m.get_path_name() for comp in actor.get_components_by_class(u.MeshComponent)
                            for m in comp.get_materials() if m})
        if not materials:
            continue
        rows.append({'label': actor.get_actor_label(), 'path': actor.get_path_name(),
                     'origin': [origin.x, origin.y, origin.z], 'extent': [extent.x, extent.y, extent.z],
                     'materials': materials})
    (out / 'scene-survey.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    foliage = []
    for asset in ea.list_assets('/Game/Downtown_West/Materials', recursive=True):
        if 'Foliage' not in asset:
            continue
        mat = u.load_asset(asset)
        if not isinstance(mat, u.Material):
            continue
        for node in lib.get_material_expressions(mat):
            if isinstance(node, u.MaterialExpressionTextureSampleParameter):
                texture = node.get_editor_property('texture')
                foliage.append({'material': asset, 'node': node.get_name(),
                                'parameter': str(node.get_editor_property('parameter_name')),
                                'sampler_type': str(node.get_editor_property('sampler_type')),
                                'texture': texture.get_path_name() if texture else None})
    candidate = u.load_asset('/Game/Downtown_West/Textures/Wind/T_wind_normal')
    texture = {'path': candidate.get_path_name(), 'compression': str(candidate.get_editor_property('compression_settings')),
               'srgb': candidate.get_editor_property('srgb'), 'width': candidate.blueprint_get_size_x(),
               'height': candidate.blueprint_get_size_y()} if candidate else None
    (out / 'foliage-textures.json').write_text(json.dumps({'nodes': foliage, 'candidate': texture}, indent=2), encoding='utf-8')
    overrides = []
    for path in ea.list_assets('/Game/Downtown_West/Assets/foliage', recursive=True):
        if not path.rsplit('/', 1)[-1].startswith('MI_'):
            continue
        instance = u.load_asset(path)
        if not isinstance(instance, u.MaterialInstanceConstant):
            continue
        for parameter in instance.get_editor_property('texture_parameter_values'):
            name = str(parameter.get_editor_property('parameter_info').get_editor_property('name'))
            value = parameter.get_editor_property('parameter_value')
            if 'wind' in name.lower() or value is None:
                overrides.append({'instance': path, 'parameter': name,
                                  'texture': value.get_path_name() if value else None})
    (out / 'foliage-overrides.json').write_text(json.dumps(overrides, indent=2), encoding='utf-8')
    functions = []
    for path in ['/Game/Stormfall/Weather/Objects/MF_SurfaceRain',
                 '/Game/Stormfall/Weather/Objects/MF_GlassSurfaceRain',
                 '/Game/Stormfall/Weather/Objects/MF_GlassWorldSlideUV']:
        fn = u.load_asset(path)
        expressions = []
        for node in lib.get_material_function_expressions(fn):
            record = {'name': node.get_name(), 'class': node.get_class().get_name(),
                      'desc': str(node.get_editor_property('desc')),
                      'pins': list(lib.get_material_expression_input_names(node)),
                      'sources': [n.get_name() if n else None for n in lib.get_inputs_for_material_function_expression(fn, node)]}
            if isinstance(node, u.MaterialExpressionMaterialFunctionCall):
                called = node.get_editor_property('material_function')
                record['function'] = called.get_path_name() if called else None
            if isinstance(node, u.MaterialExpressionFunctionInput):
                record['input_name'] = str(node.get_editor_property('input_name'))
            expressions.append(record)
        functions.append({'path': path, 'expressions': expressions})
    (out / 'object-functions.json').write_text(json.dumps(functions, indent=2), encoding='utf-8')
    return {'survey_count': len(rows), 'foliage_texture_nodes': len(foliage), 'candidate': texture, 'saved_assets': []}
