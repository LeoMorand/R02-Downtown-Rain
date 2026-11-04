"""Check captured GPU slope-blend fixture against analytic height gradients.

Rechecks saved evidence; does not launch UE or recapture GPU output.
"""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/MudProfessional/phase03-detail'
data = json.loads((OUT / 'gpu_blend_readback.json').read_text(encoding='utf-8'))
asset_record = json.loads((OUT / 'final_editor_state.json').read_text(encoding='utf-8'))
assert data['readback']['success']
assert data['readback']['returnValues']['ReturnValue'] == 'True'
samples = [[float(v) for v in re.findall(r'[RGB]=([-+\d.eE]+)', s)]
           for s in data['readback']['returnValues']['OutLinearSamples']]
assert len(samples) == 20 and all(len(v) == 3 and all(map(math.isfinite, v)) for v in samples)
errors = []
for y in range(5):
    for x in range(4):
        gx, gy = x * .2, x * .1
        # Gradient of the summed base + detail heightfields, independently of
        # the implementation's homogeneous normal-vector construction.
        if y in (2, 3):
            gx, gy = gx - .12, gy + .08
        if y == 4:
            gx = gy = 0
        length = math.sqrt(gx * gx + gy * gy + 1)
        expected = [.5 - gx / length / 2, .5 - gy / length / 2, .5 + 1 / length / 2]
        errors.extend(abs(a - b) for a, b in zip(samples[y * 4 + x], expected))
report = dict(pixels=20, tolerance=.001, max_encoded_rgb_error=max(errors),
              zero_strength_matches_zero_detail=samples[:4] == samples[4:8],
              changing_detail_z_from_1_to_999_has_no_effect=samples[8:12] == samples[12:16],
              opposite_slopes_cancel=all(v == [.5, .5, 1] for v in samples[16:]),
              source_matches_asset_record=(ROOT / 'Tools/MudStudy/Reference/ComputedDetailSlopeBlend.hlsl').read_text().strip() == data['blend_code'].strip() == asset_record['blend_readback']['code'].strip(),
              scope='GPU blend arithmetic with synthetic inputs; not full material, dynamic flow, or performance acceptance')
report['passed'] = (max(errors) < .001 and all(report[k] for k in [
    'zero_strength_matches_zero_detail', 'changing_detail_z_from_1_to_999_has_no_effect',
    'opposite_slopes_cancel', 'source_matches_asset_record']))
(OUT / 'blend_results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
raise SystemExit(0 if report['passed'] else 1)
