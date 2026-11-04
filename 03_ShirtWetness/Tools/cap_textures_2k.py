"""Cap Downtown_West textures larger than 2048 to 2048 via MaxTextureSize (source art is kept).
Idempotent. Writes the touched list with old values so restore=True puts them back.
"""
import json, os, unreal

ROOT = '/Game/Downtown_West'
CAP = 2048
LOG = os.path.join(unreal.Paths.project_dir(), 'Verification/ShirtWetness/Look/texture_cap_2k.json')

def run(restore=False):
    if restore:
        for path, old in json.load(open(LOG)).items():
            t = unreal.load_asset(path); t.set_editor_property('max_texture_size', old)
            unreal.EditorAssetLibrary.save_loaded_asset(t, False)
        return 'restored'
    done = json.load(open(LOG)) if os.path.exists(LOG) else {}
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    flt = unreal.ARFilter(package_paths=[ROOT], recursive_paths=True,
                          class_paths=[unreal.TopLevelAssetPath('/Script/Engine', 'Texture2D')])
    for data in reg.get_assets(flt):
        path = str(data.package_name)
        t = unreal.load_asset(path)
        if max(t.blueprint_get_size_x(), t.blueprint_get_size_y()) <= CAP: continue
        old = t.get_editor_property('max_texture_size')
        if old and old <= CAP: continue
        done.setdefault(path, old)
        t.set_editor_property('max_texture_size', CAP)
        unreal.EditorAssetLibrary.save_loaded_asset(t, False)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    json.dump(done, open(LOG, 'w'), indent=1)
    return len(done)
