"""Accept the exposure review and restart only the first directed shot."""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u
import mud_dual_capture as mdc

s = mdc.STATE
assert s.get('waiting_review') and s['stage_name'] == 'hero'
out = s['out'].resolve()
assert out.is_relative_to(Path('D:/aco/unreal/Stormfall/Verification/MudProfessional/phase16-video'))
old = out/'frames'
preview = out/'preview_exposure0'
assert not preview.exists()
preview.mkdir()
for frame in s['frames']:
    p = out/frame['file']
    assert p.is_file() and p.resolve().is_relative_to(old.resolve())
    p.rename(preview/p.name)
(preview/'review.json').write_text(json.dumps({'exposure_bias': 0, 'frames': len(s['frames']),
                                              'reason': 'Retake with brighter manual camera exposure.'}, indent=2), encoding='utf-8')
s['frames'].clear()
s['samples'].clear()
s['stage_frame'] = 0
s['stage_settle'] = 10
s['capture_settings']['exposure_bias'] = .75
s['capture_settings']['runtime_override_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
pp = s['cap'].get_editor_property('post_process_settings')
pp.set_editor_property('auto_exposure_bias', .75)
s['cap'].set_editor_property('post_process_settings', pp)
s['cap'].set_editor_property('bCameraCutThisFrame', True)
shutil.copy2(mdc.__file__, out/'harness.py')
shutil.copy2(__file__, out/'runtime_adjustments.py')
mdc.resume()
