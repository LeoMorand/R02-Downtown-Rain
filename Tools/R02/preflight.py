"""Read-only disk preflight. Standard library only; never loads or edits UE assets."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((Path(__file__).with_name('acceptance.json')).read_text(encoding='utf-8'))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = ROOT / 'Verification/R02' / stamp
    out.mkdir(parents=True, exist_ok=False)
    paths = [ROOT / 'Content/TA_Demos/R02_Downtown_Rain.umap',
             ROOT / 'Content/MPC_RoadWeather.uasset',
             ROOT / 'Content/Downtown_West/Materials/M_Ground_Master_Weather.uasset']
    paths += sorted((ROOT / 'Content/Stormfall/Weather').rglob('*.uasset'))
    paths += sorted((ROOT / 'Tools/R02').rglob('*.hlsl'))
    files = [{'path': p.relative_to(ROOT).as_posix(), 'exists': p.is_file(),
              **({'bytes': p.stat().st_size, 'sha256': digest(p)} if p.is_file() else {})}
             for p in paths]
    game = (ROOT / 'Config/DefaultGame.ini').read_text(encoding='utf-8-sig')
    logpath = ROOT / 'Saved/Logs/Stormfall.log'
    log = logpath.read_text(encoding='utf-8-sig', errors='replace') if logpath.exists() else ''
    missing = sorted(set(re.findall(r"Skipped package (/[\w/]+) has a valid", log)))
    camera_names = {c['name'] for c in CONFIG['cameras']}
    report = {
        'schema': 1, 'utc': stamp, 'scope': 'disk-only; no UE execution',
        'files': files,
        'map_in_packaging_ini': CONFIG['map'] in game,
        'game_feature_scan_declared': 'PrimaryAssetType="GameFeatureData"' in game,
        'unconfigured_camera_families': [k for k in CONFIG['required_camera_families'] if k not in camera_names],
        'missing_dependencies_in_last_log': missing,
        'wind_texture_candidate_exists': (ROOT / 'Content/Downtown_West/Textures/Wind/T_wind_normal.uasset').is_file(),
        'log_source': {'path': str(logpath), 'mtime_ns': logpath.stat().st_mtime_ns if logpath.exists() else None},
        'acceptance': {'shader_compile': 'not_run', 'visual': 'not_run', 'automatic_cycle': 'not_run',
                       'gpu_abba': 'not_run', 'cook': 'not_run', 'packaged_smoke': 'not_run'},
        'notes': ['Hashes are a preflight snapshot, not proof of exclusive access.',
                  'Existing log findings can belong to earlier sessions; verify in a dedicated R02 run.',
                  'Texture candidate presence does not prove channel/sampler equivalence.']}
    (out / 'preflight.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'report': str(out / 'preflight.json'), 'files': len(files),
                      'missing_assets': sum(not p['exists'] for p in files),
                      'missing_log_dependencies': missing, 'acceptance': report['acceptance']}, ensure_ascii=False))
    return report


if __name__ == '__main__':
    main()
