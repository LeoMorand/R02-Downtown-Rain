"""Validate recorded Phase11 action-driven movement and cold-start evidence."""
import json
import math
import re
from pathlib import Path

OUT = Path(__file__).resolve().parents[2]/'Verification/MudProfessional/phase11-playground'


def main():
    read = lambda name: json.loads((OUT/name).read_text(encoding='utf-8'))
    test, cold, gpu = read('input-test.json'), read('cold-start.json'), read('gpu-input-readback.json')
    samples = test['samples']
    first, last = test['initial_location'], samples[-1]
    distance = math.dist(first[:2], last['location'][:2])
    peak_speed = max(math.hypot(*s['velocity'][:2]) for s in samples)
    jump_rise = max(s['location'][2] for s in samples)-first[2]
    local_foot_x = [s['foot_l'][0]-s['location'][0] for s in samples if s['seconds'] < 2.7]
    camera = cold['camera']['rows'][0]['values']
    mud = cold['mud']['rows'][0]['values']
    brushes = [[float(x) for x in re.findall(r'[-+]?\d+(?:\.\d+)?', row)] for row in gpu['brushes']['returnValues']['ReturnValue']]
    checks = {
        'test_completed_without_error': test['complete'] and test['error'] is None,
        'movement_over_eight_metres': distance > 800,
        'speed_matches_four_metres_per_second': 380 < peak_speed < 410,
        'jump_rose_over_one_metre': jump_rise > 100,
        'jump_landed': any(s['falling'] for s in samples) and not last['falling'] and abs(last['location'][2]-first[2]) < 3,
        'walking_animation_active': all(s['animation_instance'] == 'ABP_Unarmed_C' for s in samples),
        'foot_animated_relative_to_root': max(local_foot_x)-min(local_foot_x) > 20,
        'look_action_rotated_camera': abs(last['control_rotation'][1]) > 1,
        'cold_start_spawns_manny': cold['pawn']['success'] and cold['pawn']['class'].endswith('BP_Mud_Manny_C'),
        'cold_start_camera_follows_manny': camera['GetViewTarget'] == cold['pawn']['path'],
        'cold_start_mud_contract_valid': mud['MudControls.ContractValid'],
        'player_bones_feed_mud': mud['TrackPlayer'] and mud['TrackPhysicsBones'] and len(brushes) >= 2,
        'two_low_foot_inputs_present': sum(0 <= b[2] < 20 for b in brushes) >= 2,
        'old_demo_sphere_hidden': not mud['NormalPreview.bVisible'] and mud['BrushActors'] == [],
        'output_sample_changed': gpu['stats']['maxDensityDelta'] > .01 and gpu['stats']['changedDensityPixels'] > 100,
    }
    report = {'passed': all(checks.values()), 'checks': checks, 'samples': len(samples),
              'distance_cm': distance, 'peak_speed_cm_s': peak_speed, 'jump_rise_cm': jump_rise,
              'foot_relative_x_range_cm': max(local_foot_x)-min(local_foot_x),
              'scope': 'Actual action-driven CharacterMovement/animation and editor cold-start. GPU before/after frames differ in time; not a controlled causal comparison, physical mud collision/foot IK, or performance certification.'}
    (OUT/'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    assert report['passed'], [k for k, v in checks.items() if not v]


if __name__ == '__main__':
    main()
