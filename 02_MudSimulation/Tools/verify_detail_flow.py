"""Recheck saved GPU flow arithmetic using an analytic height field.

Does not launch UE. GPU fixture substitutes analytic heights for texture reads;
the actual material's filtering and spatially varying velocity need scene tests.
"""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/MudProfessional/phase04-flow'
TIMES = [0, .125, .25, .375, .5, .4999, .5001, .9999, 1.0001, .625, .875, 1.125]
VELOCITIES = [(-.5, 0), (0, 0), (.5, 0), (0, -.5), (0, .5)]
RATE = 8 / (2048 * .01667)


def reference(velocity, time, rate=RATE):
    phase = time % 1
    ramp = 1 - abs(2 * phase - 1)
    weight = ramp * ramp * (3 - 2 * ramp)
    def h(x, y):
        return .5 + .25 * math.sin(2 * math.pi * x) + .125 * math.cos(2 * math.pi * y)
    def slopes(q):
        x = .37 - velocity[0] * rate * 5 * (q - .5)
        y = .43 - velocity[1] * rate * 3 * (q - .5)
        return [-10 * (h(x + .0014, y) - h(x, y)), -10 * (h(x, y + .0014) - h(x, y))]
    s0, s1 = slopes(phase), slopes((phase + .5) % 1)
    return [.5 + .5 * (a * weight + b * (1 - weight)) for a, b in zip(s0, s1)] + [1]


def main():
    data = json.loads((OUT / 'gpu_fixture_final.json').read_text(encoding='utf-8'))
    result = data['readback']
    assert result['success'] and result['returnValues']['ReturnValue'] == 'True'
    actual = [[float(v) for v in re.findall(r'[RGB]=([-+\d.eE]+)', s)] for s in result['returnValues']['OutLinearSamples']]
    assert len(actual) == 60 and all(len(v) == 3 and all(map(math.isfinite, v)) for v in actual)
    worst = max(abs(a - b) for row, velocity in enumerate(VELOCITIES) for col, time in enumerate(TIMES)
                for a, b in zip(actual[row * 12 + col], reference(velocity, time)))
    boundary = max(abs(a - b) for row in range(5) for l, r in [(5, 6), (7, 8)]
                   for a, b in zip(actual[row * 12 + l], actual[row * 12 + r]))
    zero = all(v == actual[12] for v in actual[12:24])
    periodic = all(actual[row * 12 + 1] == actual[row * 12 + 11] for row in range(5))
    sign_difference = max(abs(a - b) for col in [1, 3, 9, 10] for l, r in [(0, 2), (3, 4)]
                          for a, b in zip(actual[l * 12 + col], actual[r * 12 + col]))
    cpu_boundary = max(abs(a - b) for v in VELOCITIES for t in [.5, 1.]
                       for a, b in zip(reference(v, t - 1e-5), reference(v, t + 1e-5)))
    rate_zero = max(abs(a - b) for v in VELOCITIES for t in TIMES
                    for a, b in zip(reference(v, t, 0), reference((0, 0), 0)))
    source_match = all((ROOT / 'Tools/MudStudy/Reference' / name).read_text().strip() == data[key].strip()
                       for name, key in [('DetailFlowPhases.hlsl', 'pack_code'), ('FlowDetailNormal.hlsl', 'normal_code')])
    audit = json.loads((OUT / 'final_audit.json').read_text(encoding='utf-8'))
    source_match = (source_match and audit['phase_expression']['code'].strip() == data['pack_code'].strip()
                    and audit['normal_expression']['code'].strip() == data['normal_code'].strip())
    metrics = json.loads((OUT / 'image_metrics.json').read_text(encoding='utf-8'))
    metrics = {m['comparison']: m for m in metrics}
    controlled_effect = metrics['controlled_flow_time_change']['mean_abs_rgb_8bit'] > .1
    controlled_zero = metrics['controlled_zero_rate_control']['mean_abs_rgb_8bit'] == 0
    state = json.loads((OUT / 'controlled_runtime_evidence.json').read_text(encoding='utf-8'))['restored']['rows'][0]['values']
    restored = (state['SurfaceMID.K2_GetScalarParameterValue(DetailFlowTimeOverride)'] == -1
                and state['SurfaceMID.K2_GetVectorParameterValue(DetailFlowTestVelocity)'] == '(R=0.000000,G=0.000000,B=0.000000,A=0.000000)'
                and abs(state['SurfaceMID.K2_GetScalarParameterValue(DetailFlowUVRate)'] - RATE) < 1e-7)
    report = dict(pixels=60, max_encoded_rgb_error=worst, tolerance=.001,
                  zero_velocity_time_invariant=zero, one_period_repeat_equal=periodic,
                  signed_velocity_output_difference=sign_difference, gpu_boundary_pair_difference=boundary,
                  cpu_boundary_difference_at_epsilon_1e_5=cpu_boundary,
                  cpu_zero_rate_difference=rate_zero, source_matches_record=source_match,
                  real_material_controlled_time_effect=controlled_effect,
                  real_material_zero_rate_invariant=controlled_zero, validation_controls_restored=restored,
                  solver_uv_per_second_per_velocity_unit=RATE,
                  scope='Frozen signed velocity, analytic heights, shader flow arithmetic; no persistent transported microheight')
    report['passed'] = (worst < .001 and boundary < .001 and zero and periodic
                        and sign_difference > .0005 and cpu_boundary < 1e-5
                        and rate_zero < 1e-12 and source_match and controlled_effect and controlled_zero and restored)
    (OUT / 'flow_results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
