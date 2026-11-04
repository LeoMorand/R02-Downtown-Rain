"""Add the baked ripple tier to M_Ground_Master_Weather behind a static switch. Idempotent.

Run inside a disposable UnrealEditor-Cmd (-ExecutePythonScript) with the project otherwise closed.
STORMFALL_RIPPLE_TIER = baked | procedural sets the switch default (A/B). Output: result.json in
STORMFALL_R02_OUTPUT. The procedural Custom node is kept; only its consumer is re-routed.
"""
import json
import os
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ['STORMFALL_R02_OUTPUT'])
TIER = os.environ.get('STORMFALL_RIPPLE_TIER', 'baked')
MATERIAL = '/Game/Downtown_West/Materials/M_Ground_Master_Weather'
TEXTURE_DIR, TEXTURE_NAME = '/Game/Stormfall/Weather/Ripples', 'T_RippleFlipbook'
SWITCH = 'RippleUseBakedFlipbook'
DESC = 'Baked ripple tier: Tools/R02/ripple_flipbook.hlsl'
L = u.MaterialEditingLibrary
EAL = u.EditorAssetLibrary


def import_texture():
    path = TEXTURE_DIR + '/' + TEXTURE_NAME
    task = u.AssetImportTask()
    for key, value in [('filename', str(ROOT / 'Tools/R02/RippleBake/T_RippleFlipbook.png')),
                       ('destination_path', TEXTURE_DIR), ('destination_name', TEXTURE_NAME),
                       ('automated', True), ('replace_existing', True), ('save', False)]:
        task.set_editor_property(key, value)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = u.load_asset(path)
    if not tex:
        raise RuntimeError('Texture import failed')
    # Two-channel linear data: BC5, no sRGB. Raw RG in [0,1] is decoded in the shader.
    tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP)
    tex.set_editor_property('srgb', False)
    tex.set_editor_property('flip_green_channel', False)
    EAL.save_loaded_asset(tex, only_if_is_dirty=False)
    return tex


def inputs_of(mat, node):
    names = [str(n) for n in L.get_material_expression_input_names(node)]
    sources = L.get_inputs_for_material_expression(mat, node)
    return dict(zip(names, sources))


def run():
    mat = u.load_asset(MATERIAL)
    nodes = list(L.get_material_expressions(mat))
    customs = [n for n in nodes if isinstance(n, u.MaterialExpressionCustom)]
    procedural = [n for n in customs if 'ArtistRandomness' in str(n.get_editor_property('code'))]
    if len(procedural) != 1:
        raise RuntimeError('Cannot uniquely identify the procedural ripple node')
    procedural = procedural[0]
    switch = [n for n in nodes if isinstance(n, u.MaterialExpressionStaticSwitchParameter)
              and str(n.get_editor_property('parameter_name')) == SWITCH]
    result = {'material': MATERIAL, 'tier': TIER}

    if not switch:
        relative = 'Content/' + MATERIAL.removeprefix('/Game/') + '.uasset'
        backup = ROOT / 'Saved/Revisions' / ('Before_RippleFlipbook_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')) / relative
        backup.parent.mkdir(parents=True)
        shutil.copy2(ROOT / relative, backup)
        result['backup'] = str(backup)
        # Consumers of the procedural output (expected: the rain-scale Custom node).
        consumers = []
        for n in nodes:
            for pin, src in inputs_of(mat, n).items():
                if src == procedural:
                    consumers.append((n, pin))
        if not consumers:
            raise RuntimeError('Procedural ripple output is not connected')
        sources = inputs_of(mat, procedural)
        tex = import_texture()
        x = procedural.get_editor_property('material_expression_editor_x')
        y = procedural.get_editor_property('material_expression_editor_y')
        tex_node = L.create_material_expression(mat, u.MaterialExpressionTextureObject, x, y + 420)
        tex_node.set_editor_property('texture', tex)
        tex_node.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        baked = L.create_material_expression(mat, u.MaterialExpressionCustom, x + 260, y + 360)
        baked.set_editor_property('code', (ROOT / 'Tools/R02/ripple_flipbook.hlsl').read_text(encoding='utf-8'))
        baked.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
        baked.set_editor_property('description', DESC)
        pins = ['WorldPos', 'Seconds', 'ArtistSpeed', 'ArtistStrength', 'ArtistDensity', 'Flipbook']
        custom_inputs = []
        for name in pins:
            ci = u.CustomInput(); ci.set_editor_property('input_name', name); custom_inputs.append(ci)
        baked.set_editor_property('inputs', custom_inputs)
        for name in pins[:-1]:
            if not L.connect_material_expressions(sources[name], '', baked, name):
                raise RuntimeError('Could not connect ' + name)
        if not L.connect_material_expressions(tex_node, '', baked, 'Flipbook'):
            raise RuntimeError('Could not connect Flipbook')
        sw = L.create_material_expression(mat, u.MaterialExpressionStaticSwitchParameter, x + 520, y + 120)
        sw.set_editor_property('parameter_name', SWITCH)
        sw.set_editor_property('group', 'PuddleRipples')
        L.connect_material_expressions(baked, '', sw, 'True')
        L.connect_material_expressions(procedural, '', sw, 'False')
        for consumer, pin in consumers:
            if not L.connect_material_expressions(sw, '', consumer, pin):
                raise RuntimeError('Could not re-route ' + pin)
        switch = [sw]
        result['created'] = True
        result['consumers'] = [c.get_name() + '.' + p for c, p in consumers]
    else:
        # Keep the installed HLSL and texture in sync with the source files (re-baked presets).
        import_texture()
        result['texture_reimported'] = True
        baked = [n for n in customs if str(n.get_editor_property('description')) == DESC][0]
        baked.set_editor_property('code', (ROOT / 'Tools/R02/ripple_flipbook.hlsl').read_text(encoding='utf-8'))
        # Nodes installed before the density off switch lack the ArtistDensity pin: add it, then wire it
        # to the same source as the procedural node. Re-setting inputs drops links, so reconnect all.
        existing = inputs_of(mat, baked)
        if 'ArtistDensity' not in existing:
            sources = inputs_of(mat, procedural)
            custom_inputs = list(baked.get_editor_property('inputs'))
            ci = u.CustomInput(); ci.set_editor_property('input_name', 'ArtistDensity')
            custom_inputs.insert(len(custom_inputs) - 1, ci)
            baked.set_editor_property('inputs', custom_inputs)
            for name, src in list(existing.items()) + [('ArtistDensity', sources['ArtistDensity'])]:
                if src is None or not L.connect_material_expressions(src, '', baked, name):
                    raise RuntimeError('Could not connect ' + name)
            result['added_pin'] = 'ArtistDensity'
        wired = inputs_of(mat, baked)
        if wired.get('ArtistDensity') is None or wired.get('ArtistDensity') != inputs_of(mat, procedural).get('ArtistDensity'):
            raise RuntimeError('ArtistDensity is not wired to the procedural source')

    switch[0].set_editor_property('default_value', TIER == 'baked')
    L.recompile_material(mat)
    errors = [str(e) for e in L.get_material_compile_errors(mat)] if hasattr(L, 'get_material_compile_errors') else []
    if errors:
        raise RuntimeError('Material compile errors: ' + '; '.join(errors))
    if not EAL.save_loaded_asset(mat, only_if_is_dirty=False):
        raise RuntimeError('Material save failed')
    result.update(status='completed', switch_default=TIER == 'baked', compile_errors=errors)
    return result


OUT.mkdir(parents=True, exist_ok=True)
try:
    data = run()
except Exception:
    data = {'status': 'failed', 'error': traceback.format_exc()}
(OUT / 'result.json').write_text(json.dumps(data, indent=1), encoding='utf-8')
