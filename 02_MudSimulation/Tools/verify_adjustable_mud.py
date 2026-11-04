"""Recheck recorded Phase10 live values and rendered silhouettes; does not run UE."""
import json
import math
import subprocess
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/MudProfessional/phase10-adjustable'


def vector(value):
    return [float(part.split('=')[1]) for part in value.strip('()').split(',')]


def distance(x, y, shape, size, center=(0, 0), yaw=0, amount=.2, seed=3):
    x, y = x-center[0], y-center[1]
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    x, y = c*x+s*y, -s*x+c*y
    half = np.array(size)/2
    if shape == 1:
        radius = .2*min(half)
        qx, qy = np.abs(x)-(half[0]-radius), np.abs(y)-(half[1]-radius)
        return radius-np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))-np.minimum(np.maximum(qx, qy), 0)
    nx, ny = x/half[0], y/half[1]
    theta = np.arctan2(ny, nx)
    radial = np.ones_like(x)
    if shape == 3:
        radial += amount*(.5*np.sin(3*theta+seed)+.3*np.sin(5*theta-1.7*seed)+.2*np.sin(9*theta+.7*seed))
    return (radial-np.hypot(nx, ny))*min(half)


def main():
    data = json.loads((OUT/'runtime-readback.json').read_text(encoding='utf-8'))
    checks = {}
    for name, sample in data['samples'].items():
        assert sample['success'] and sample['matched'] == 1
        row = sample['rows'][0]
        assert not row.get('errors'), row.get('errors')
        v = row['values']
        height = v['MudControls.ThicknessCm']
        checks[name+'_contract'] = v['MudControls.ContractValid']
        checks[name+'_height_sync'] = v['NormalPass.HeightScale'] == height == v['MudControls.ContactMID.K2_GetScalarParameterValue(ContactHeightCm)']
        checks[name+'_pom_sync'] = abs(v['SurfaceMID.K2_GetScalarParameterValue(ParallaxHeight)']-height/2000) < 1e-7
        checks[name+'_region_sync'] = v['SurfaceMID.K2_GetScalarParameterValue(MudRegionShape)'] == v['MudControls.ContactMID.K2_GetScalarParameterValue(MudRegionShape)'] and v['SurfaceMID.K2_GetVectorParameterValue(MudRegionSize)'] == v['MudControls.ContactMID.K2_GetVectorParameterValue(MudRegionSize)']
        checks[name+'_live_texture'] = v['SurfaceMID.K2_GetTextureParameterValue(MudNormalBuffer)'] == v['MudControls.ContactMID.K2_GetTextureParameterValue(MudNormalBuffer)'] and 'UEDPIE_' in v['SurfaceMID.K2_GetTextureParameterValue(MudNormalBuffer)']
    val = lambda name: data['samples'][name]['rows'][0]['values']
    checks['three_thicknesses'] = [val(n)['MudControls.ThicknessCm'] for n in ['thin', 'reset', 'thick']] == [5, 20, 40]
    checks['static_parent'] = 'Static' in val('red_static')['SurfaceMID.Parent']
    checks['flow_parent_restored'] = 'Flow' in val('red_flow')['SurfaceMID.Parent']
    checks['switch_preserves_parameters'] = all(val('red_static')[k] == val('red_flow')[k] for k in val('red_static') if k != 'SurfaceMID.Parent')
    checks['rectangle_transform'] = np.allclose(vector(val('rectangle')['SurfaceMID.K2_GetVectorParameterValue(MudRegionCenter)'])[:2], [120, -50]) and abs(vector(val('rectangle')['SurfaceMID.K2_GetVectorParameterValue(MudRegionSettings)'])[0]-math.radians(25)) < 1e-5
    images = {}
    pixel_cm = 2*2500*math.tan(math.radians(55)/2)/1280
    xx, yy = np.meshgrid((np.arange(1280)+.5-640)*pixel_cm, (np.arange(720)+.5-360)*pixel_cm)
    configs = [
        ('ellipse-default.png', 2, (1600, 1300), (0, 0), 0, .2),
        ('irregular.png', 3, (1400, 1100), (0, 0), 0, .3),
        ('rectangle-rotated.png', 1, (1100, 750), (120, -50), 25, .3),
        ('red-static.png', 1, (1100, 750), (120, -50), 25, .3),
    ]
    ratios = {}
    for filename, shape, size, center, yaw, amount in configs:
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(OUT/filename),
                              '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'],
                             check=True, stdout=subprocess.PIPE).stdout
        rgb = np.frombuffer(raw, dtype=np.uint8).reshape(720, 1280, 3).astype(float)
        assert rgb.shape == (720, 1280, 3)
        d = distance(xx, yy, shape, size, center, yaw, amount)
        expected = d >= 0
        observed = (rgb[:, :, 0] > rgb[:, :, 2]+10) & (rgb[:, :, 0] > rgb[:, :, 1]+5)
        iou = float(np.count_nonzero(expected & observed)/np.count_nonzero(expected | observed))
        outside_leak = float(np.mean(observed[d < -10]))
        images[filename] = {'silhouette_iou': iou, 'outside_leak_fraction_beyond_10cm': outside_leak}
        # Sky is blue; this segmentation is specific to these fixed research captures.
        checks[filename+'_outline'] = iou > .95 and outside_leak < .002
        ratios[filename] = float(rgb[d > 30, 0].mean()/max(rgb[d > 30, 1].mean(), 1))
    checks['visible_color_change'] = ratios['red-static.png'] > 1.5*ratios['rectangle-rotated.png']
    persisted = json.loads((OUT/'persistence.json').read_text(encoding='utf-8'))['rows'][0]['values']
    checks['saved_region_reloaded'] = persisted['MudControls.RegionShape'] == 'Irregular' and persisted['MudControls.EditorSurfaceMID.K2_GetScalarParameterValue(MudRegionShape)'] == 3
    report = {'passed': all(checks.values()), 'checks': checks, 'images': images, 'color_r_over_g': ratios,
              'scope': 'Recorded live parameter contracts, fixed-camera rendered region/color and map reload. Not continuous contact, viscosity, real-time performance or packaged-build certification.'}
    (OUT/'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    assert report['passed'], [name for name, passed in checks.items() if not passed]


if __name__ == '__main__':
    main()
