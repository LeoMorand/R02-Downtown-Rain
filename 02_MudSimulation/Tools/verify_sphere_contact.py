"""Recheck recorded GPU arithmetic and independently sample continuous support.

Does not run UE. Analytic GPU fields bypass texture filtering; runtime captures
and bindings are separate evidence. Curved support is a finite approximation.
"""
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'Verification/MudProfessional/phase07-contact'


def field(case, x, y):
    if case == 0:
        return 0.0, 0.0, 0.0
    if case == 2:
        return -10+.2*x-.1*y, .2, -.1
    if case == 3:
        qx = x-12
        b = 8*math.exp(-(qx*qx+y*y)/18)
        return -10+b, -qx*b/9, -y*b/9
    if case == 4:
        b = -12*math.exp(-(x*x+y*y)/18)
        return -2+b, -x*b/9, -y*b/9
    return -10.0, 0.0, 0.0


def support(case, radius, rings, directions):
    if case in (5, 6, 7):
        return 0.0
    h, gx, gy = field(case, 0, 0)
    value = h+radius
    norm = math.sqrt(1+gx*gx+gy*gy)
    x, y, nz = radius*gx/norm, radius*gy/norm, 1/norm
    value = max(value, field(case, x, y)[0]+radius*nz)
    for ring in range(1, rings+1):
        r = radius*ring/rings
        cap = math.sqrt(max(radius*radius-r*r, 0))
        for direction in range(directions):
            angle = direction*math.tau/directions
            value = max(value, field(case, r*math.cos(angle), r*math.sin(angle))[0]+cap)
    return value-radius


def main():
    source = OUT/'gpu_fixture.json'
    data = json.loads(source.read_text(encoding='utf-8'))
    readback = data['readback']
    assert readback['success'] and readback['returnValues']['ReturnValue'] == 'True'
    pixels = readback['returnValues']['OutLinearSamples']
    assert len(pixels) == 36
    rows = []
    for index, pixel in enumerate(pixels):
        encoded = float(re.search(r'R=([-+\d.eE]+)', pixel).group(1))
        assert math.isfinite(encoded)
        radius = (5,10,20,40)[index%4]
        case = index//4
        gpu = (encoded-.5)*64
        sampled = support(case, radius, 4, 16)
        # Independent much denser disk sample; not a formal global bound.
        dense = support(case, radius, 192, 720)
        analytic = (-10+radius*(math.sqrt(1.05)-1)) if case == 2 else None
        assert abs(gpu-sampled) < .04, (index, gpu, sampled)
        if analytic is not None:
            assert abs(gpu-analytic) < .04
        rows.append(dict(case=case, radius_cm=radius, gpu_offset_cm=gpu,
                         sampled_offset_cm=sampled, dense_offset_cm=dense,
                         gpu_error_cm=abs(gpu-sampled),
                         undersupport_cm=max(dense-sampled, 0)))
    result = dict(passed=True, cases=len(rows),
                  max_gpu_arithmetic_error_cm=max(x['gpu_error_cm'] for x in rows),
                  max_curved_undersupport_cm=max(x['undersupport_cm'] for x in rows),
                  scope='Analytic-field GPU arithmetic, not texture filtering, physical collision or full dynamic parity',
                  dense_reference='192 radial rings x 720 angles plus center/normal candidate; approximate reference',
                  source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), rows=rows)
    (OUT/'contact_results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}, indent=2))


if __name__ == '__main__':
    main()
