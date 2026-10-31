"""Entry points for bounded verification in the already-open R02 editor."""
import json
import os
import runpy
import shutil
import gc
from datetime import datetime, timezone
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]


def cancel_capture(output_path):
    expected = Path(output_path).resolve()
    if expected.parent != ROOT / 'Verification/R02':
        raise ValueError('Only this tool verification directory is allowed')
    contexts = []
    for obj in gc.get_objects():
        if isinstance(obj, dict) and obj.get('MODE') == 'capture' and 'TICK_ACTIVE' in obj and 'finish' in obj:
            if str(obj.get('OUT', '')) == str(expected):
                contexts.append(obj)
    if len(contexts) != 1:
        raise RuntimeError('Expected exactly one matching capture callback context, found ' + str(len(contexts)))
    context = contexts[0]
    context['STATE']['errors'].append('Interactive capture cancelled: viewport realtime override prevented screenshot completion. Rerun in standalone rendering worker.')
    context['finish'](False)
    return {'cancelled': str(expected), 'restore_matches': context['STATE'].get('restore_matches')}


def begin(mode='capture', quick=True, camera=''):
    if mode not in ('capture', 'benchmark', 'cycle', 'audit', 'inspect'):
        raise ValueError('Unsupported interactive verification mode')
    out = ROOT / 'Verification/R02' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-native-' + mode)
    os.environ['STORMFALL_R02_MODE'] = mode
    os.environ['STORMFALL_R02_OUTPUT'] = str(out)
    os.environ['STORMFALL_R02_QUICK'] = '1' if quick else '0'
    os.environ['STORMFALL_R02_CAMERA'] = camera
    runpy.run_path(str(ROOT / 'Tools/R02/ue_acceptance.py'), run_name='r02_acceptance')
    return {'output': str(out), 'mode': mode, 'asynchronous': mode in ('capture','benchmark','cycle')}


def refresh_instance_cache(path):
    if path != '/Game/Downtown_West/Assets/foliage/tree_narrowleaf/MI_Foliage_TreeNarrowleaf':
        raise ValueError('This repair is scoped to the one remaining stale dependency')
    asset = u.load_asset(path)
    if not isinstance(asset, u.MaterialInstanceConstant):
        raise TypeError('Expected MaterialInstanceConstant')
    fields = ['scalar_parameter_values', 'vector_parameter_values', 'texture_parameter_values']
    before = {k: str(asset.get_editor_property(k)) for k in fields}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = ROOT / 'Saved/Revisions' / ('Before_R02_OneCache_' + stamp)
    backup.mkdir(parents=True)
    disk = ROOT / ('Content/' + path.removeprefix('/Game/') + '.uasset')
    shutil.copy2(disk, backup / disk.name)
    u.MaterialEditingLibrary.update_material_instance(asset)
    after = {k: str(asset.get_editor_property(k)) for k in fields}
    if before != after:
        raise RuntimeError('Authored parameters changed unexpectedly; refusing save')
    if not u.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Save failed')
    report = {'asset': path, 'backup': str(backup), 'authored_parameters_preserved': True,
              'missing_import_remaining': b'/Game/ProceduralNtr_vol2/pnp_v2_assets/Textures/Wind/wind_normal' in disk.read_bytes()}
    (ROOT / 'Verification/R02/one-cache-repair.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
