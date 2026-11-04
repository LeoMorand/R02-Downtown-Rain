"""Verify captured UE GPU data and POM height units. Standard library only.

This does not run UE or claim GPU validation of POM. The GPU checks use actual
ReadRenderTargetRaw output; the POM checks compare CPU marching to analytic rays.
"""
import argparse
import json
import math
import re
from pathlib import Path


def colors(result):
    if not result.get('success'):
        raise ValueError(f'Readback failed: {result}')
    samples = result['returnValues']['OutLinearSamples']
    rows = [[float(x) for x in re.findall(r'[RGBA]=([-+\d.eE]+)', s)] for s in samples]
    if len(rows) != 256 or any(len(v) != 4 or not all(map(math.isfinite, v)) for v in rows):
        raise ValueError('Expected 256 finite RGBA samples')
    return rows


def encoded_normal(dx, dy):
    inv = 1 / math.sqrt(dx * dx + dy * dy + 1)
    return [0.5 - dx * inv / 2, 0.5 - dy * inv / 2, 0.5 + inv / 2]


def fixture(x, y):
    if (x, y) == (4, 12):
        return 1.0
    if (x, y) == (12, 12):
        return 0.0
    return (x + 2 * y) / 64 if y < 8 else 0.5


def verify_gpu(data):
    source = colors(data['source'])
    fixture_error = max(abs(source[y * 16 + x][2] - fixture(x, y)) for y in range(16) for x in range(16))
    results = []
    expected_cases = [(0, [2000, 2000]), (20, [2000, 2000]), (30, [2000, 2000]), (20, [32, 64])]
    if [(c['height_cm'], c['world_size_cm']) for c in data['cases']] != expected_cases:
        raise ValueError('Calibration cases missing or reordered')
    for case in data['cases']:
        if case['dispatch']['returnValues'].get('ReturnValue') != 'True':
            raise ValueError('GPU dispatch not accepted')
        actual = colors(case['readback'])
        height = case['height_cm']
        sx, sy = [v / 16 for v in case['world_size_cm']]
        errors, alpha_errors = [], []
        for y in range(16):
            for x in range(16):
                left, right = max(x - 1, 0), min(x + 1, 15)
                down, up = max(y - 1, 0), min(y + 1, 15)
                h = lambda px, py: source[py * 16 + px][2]
                dx = height * (h(right, y) - h(left, y)) / ((right - left) * sx)
                dy = height * (h(x, up) - h(x, down)) / ((up - down) * sy)
                expected = encoded_normal(dx, dy)
                errors.extend(abs(a - b) for a, b in zip(actual[y * 16 + x][:3], expected))
                alpha_errors.append(abs(actual[y * 16 + x][3] - h(x, y)))
        # Closed-form plane normal, independent of neighbor-index implementation.
        ramp = encoded_normal(height * 0.25 / case['world_size_cm'][0], height * 0.5 / case['world_size_cm'][1])
        ramp_error = max(abs(a - b) for a, b in zip(actual[2 * 16 + 2][:3], ramp))
        passed = max(errors) < 0.001 and max(alpha_errors) == 0 and ramp_error < 0.001
        if height == 0:
            passed = passed and all(v[:3] == [0.5, 0.5, 1.0] for v in actual)
        results.append(dict(height_cm=height, world_size_cm=case['world_size_cm'], pixels=256,
                            max_encoded_rgb_error=max(errors), max_height_copy_error=max(alpha_errors),
                            analytic_ramp_error=ramp_error, passed=passed))
    return dict(source_fixture_max_error=fixture_error, cases=results,
                passed=fixture_error == 0 and all(r['passed'] for r in results))


def verify_pom_math():
    """Closed-form ray/plane intersection checks a CPU translation of POM UVs.

    No texture filtering, screen derivatives, PDO, temporal effects or GPU POM
    validation are covered here. All tested intersections stay within [0,1].
    """
    worst = 0.0
    count = 0
    for a, b, c in [(0.5, 0, 0), (0.25, 0.125, 0.25), (0.6, -0.3, 0.15)]:
        for ratio in [0.0, 0.01, 0.015]:
            for vx, vy, vz in [(0, 0, 1), (0.4, -0.25, 0.8), (-0.6, 0.3, 0.4)]:
                uv = [0.45, 0.55]
                reference = 0.9
                travel = [-ratio * vx / vz, -ratio * vy / vz]
                q = b * travel[0] + c * travel[1]
                hit = (a + b * uv[0] + c * uv[1] + q * reference) / (1 + q)
                expected = [uv[k] + travel[k] * (reference - hit) for k in range(2)]
                start = [uv[k] - (1 - reference) * travel[k] for k in range(2)]
                for steps in [8, 32]:
                    ray = prev_ray = prev_h = 1.0
                    offset = [0.0, 0.0]
                    found = False
                    for _ in range(steps + 2):
                        sampled = a + b * (start[0] + offset[0]) + c * (start[1] + offset[1])
                        if ray < sampled:
                            weight = (sampled - ray) / ((prev_ray - prev_h) + sampled - ray)
                            offset = [offset[k] - weight * travel[k] / steps for k in range(2)]
                            found = True
                            break
                        prev_ray, prev_h = ray, sampled
                        ray -= 1 / steps
                        offset = [offset[k] + travel[k] / steps for k in range(2)]
                    if not found:
                        raise ValueError('Analytic POM test missed the plane')
                    worst = max(worst, *(abs(start[k] + offset[k] - expected[k]) for k in range(2)))
                    count += 1
    return dict(scope='CPU POM UV algebra only; no GPU POM/PDO validation', cases=count,
                max_uv_error=worst, passed=worst < 1e-12)


def verify_mesh(data):
    section = data['mesh']['sections'][0]
    residual = max(max(abs(uv['u'] - (p['x'] / 100 + 0.5)), abs(uv['v'] - (p['y'] / 100 + 0.5)))
                   for p, uv in zip(section['positions'], section['uvs']))
    scale = data['baseline_actor']['rows'][0]['values']['Surface.RelativeScale3D']
    return dict(uv_world_affine_max_error=residual, world_span_cm=[100 * scale['x'], 100 * scale['y']],
                passed=residual < 1e-9 and scale == dict(x=20, y=20, z=1))


def verify_runtime(data):
    values = data['runtime']['rows'][0]['values']
    spans = [float(x) for x in re.findall(r'[XY]=([-+\d.eE]+)', values['NormalPass.WorldSize'])]
    ratio = values['SurfaceMID.K2_GetScalarParameterValue(ParallaxHeight)']
    multiplier = values['SurfaceMID.K2_GetScalarParameterValue(RebuildHeightScale)']
    compute = values['NormalPass.HeightScale']
    if len(spans) != 2:
        raise ValueError('Missing runtime world size')
    inferred = ratio * multiplier * spans[0]
    binding = values['NormalPass.NormalOutput'] == values['SurfaceMID.K2_GetTextureParameterValue(MudNormalBuffer)']
    passed = (abs(inferred - compute) < 1e-5 and spans == [2000, 2000]
              and abs(compute - 20) < 1e-6 and binding
              and values['Surface.RelativeScale3D'] == dict(x=20, y=20, z=1)
              and values['SurfaceMID.K2_GetScalarParameterValue(NormalAlignToPOM)'] == 1
              and values['SurfaceMID.K2_GetScalarParameterValue(UseGlobalNormal)'] == 1
              and values['NormalPass.LastDispatchAccepted']
              and int(values['NormalPass.ProducerGraphDispatches']) > 0)
    return dict(pom_height_cm=inferred, compute_height_cm=compute,
                height_difference_cm=abs(inferred - compute), normal_texture_binding_matches=binding, passed=bool(passed))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parents[2] / 'Verification/MudProfessional/phase02-height')
    args = parser.parse_args()
    data = json.loads((args.directory / 'gpu_readbacks_verified.json').read_text(encoding='utf-8'))
    runtime = json.loads((args.directory / 'runtime_evidence.json').read_text(encoding='utf-8'))
    report = dict(gpu=verify_gpu(data), pom_math=verify_pom_math(), mesh=verify_mesh(data), runtime=verify_runtime(runtime))
    report['height_contract'] = dict(pom_ratio=0.01, rebuild_height_scale=1, world_span_cm=2000,
                                     inferred_pom_height_cm=20, old_compute_height_cm=30,
                                     calibrated_compute_height_cm=20, old_slope_multiplier=1.5,
                                     scope='Current axis-aligned square plane, unit UV coverage')
    report['passed'] = all(report[k]['passed'] for k in ['gpu', 'pom_math', 'mesh', 'runtime'])
    (args.directory / 'calibration_results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
