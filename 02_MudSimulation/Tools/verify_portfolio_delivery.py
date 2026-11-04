"""Check final capture evidence, including frame-adjacent finite-domain handoff."""
import argparse,json,math
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('directory',type=Path); args=ap.parse_args()
    p=args.directory; d=json.loads((p/'run.json').read_text()); v=json.loads((p/'validation.json').read_text())
    assert v['passed'] and len(d['frames'])==1920 and d['capture_settings']['width']==1920 and d['capture_settings']['height']==1080
    assert d['contact_contract']['edge_blend_radius_multiplier']==4
    transitions=[]
    for a,b in zip(d['gpu_samples'],d['gpu_samples'][1:]):
        ca,cb=a['contact_prediction'],b['contact_prediction']
        assert all(math.isfinite(ca[k]) for k in ('predicted_visual_z_cm','predicted_offset_z_cm'))
        if ca['domain_inside']!=cb['domain_inside']:
            dt=b['sequence_seconds']-a['sequence_seconds']
            assert dt<.034, 'Boundary crossing needs adjacent rendered-frame samples'
            transitions.append(dict(from_time=a['sequence_seconds'],to_time=b['sequence_seconds'],sample_interval_seconds=dt,
                predicted_step_cm=abs(ca['predicted_visual_z_cm']-cb['predicted_visual_z_cm'])))
    assert len(transitions)==2 and max(t['predicted_step_cm'] for t in transitions)<1
    assert len(d['evidence'])==4 and len({e['game_seconds'] for e in d['evidence']})==1
    result=dict(passed=True,transitions=transitions,max_predicted_crossing_step_cm=max(t['predicted_step_cm'] for t in transitions),
        gpu_patch_samples=len(d['gpu_samples']),frozen_evidence_time=d['evidence'][0]['game_seconds'],
        scope='CPU support prediction from GPU RT samples, not direct WPO position readback or rigid-body contact')
    (p/'boundary_validation.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))


if __name__=='__main__': main()
