"""Validate paired standalone profile runs; never interpret offline cadence as FPS."""
import argparse
import json
import math
import statistics
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('directory',type=Path)
    args=ap.parse_args()
    manifest=json.loads((args.directory/'runs.json').read_text(encoding='utf-8-sig'))
    rows=[]
    paths=[]
    for run in manifest['runs']:
        data=json.loads((args.directory/run['report']).read_text(encoding='utf-8-sig'))
        assert run['exit_code']==0 and data['passed'], run
        assert data['frames']==900 and data['warmup_frames']==180
        assert len(data['samples'])==720 and data['pixels']==512*512
        assert data['contact']==run['contact'] and data['flow']==run['flow']
        assert data['viewport']==[1280,720] and data['camera_valid']
        log=(args.directory/run['log']).read_text(encoding='utf-8-sig',errors='replace')
        assert 'LogD3D12RHI:' in log and 'PCD3D_SM6' in log, 'Wrong rendering backend'
        assert data['height_cm']==data['radius_cm']==20 and data['height_copy_error']==0
        samples=data['samples']
        gpu=[s[3] for s in samples]
        assert all(math.isfinite(x) and x>0 for x in gpu), 'No valid RHI GPU timing'
        brush=data['brush_samples']
        assert len(brush)==30 and math.dist(brush[3][1:3],brush[10][1:3])>100
        assert all(abs(p[3]-20)<.001 for p in brush)
        points=[(0,-600,-250),(3,-600,-250),(9,0,-250),(12,300,0),(15,450,300),
                (18,450,300),(24,0,500),(30,-500,250),(36,-600,-250)]
        def expected(t):
            for a,b in zip(points,points[1:]):
                if t<=b[0]:
                    f=max(0,min(1,(t-a[0])/(b[0]-a[0])))
                    return [a[1]+f*(b[1]-a[1]),a[2]+f*(b[2]-a[2]),20]
            return list(points[-1][1:])+[20]
        # Allow a constant +/-3-frame phase between actor and sequence tick.
        offsets=[(max(math.dist(p[1:],expected(p[0]/30+shift/30)) for p in brush),shift)
                 for shift in range(-3,4)]
        route_error,offset=min(offsets)
        assert route_error<.01, ('Wrong trajectory',route_error)
        paths.append(brush)
        rows.append(dict(contact=run['contact'],flow=run['flow'],report=run['report'],
                         gpu_median_ms=statistics.median(gpu),
                         gpu_p95_ms=sorted(gpu)[int(.95*(len(gpu)-1))],
                         frame_wall_median_ms=statistics.median(s[2] for s in samples),
                         route_error_cm=route_error,sequence_phase_offset_frames=offset))
    path_error=max(math.dist(a[1:],b[1:]) for p in paths for a,b in zip(p,paths[0]))
    assert path_error<.01, ('Replay mismatch',path_error)
    cases=[]
    for contact,flow in ((False,False),(True,False),(False,True),(True,True)):
        measured=[r['gpu_median_ms'] for r in rows if r['contact']==contact and r['flow']==flow]
        assert len(measured)>=2, 'Need repeats for every case'
        cases.append(dict(contact=contact,flow=flow,runs=len(measured),gpu_median_of_run_medians_ms=statistics.median(measured),
                          run_median_range_ms=[min(measured),max(measured)]))
    def compare(target,base,label):
        t=next(c for c in cases if (c['contact'],c['flow'])==target)
        b=next(c for c in cases if (c['contact'],c['flow'])==base)
        interval=[t['run_median_range_ms'][0]-b['run_median_range_ms'][1],t['run_median_range_ms'][1]-b['run_median_range_ms'][0]]
        return dict(feature=label,delta_ms=t['gpu_median_of_run_medians_ms']-b['gpu_median_of_run_medians_ms'],
                    observed_difference_range_ms=interval,range_excludes_zero=interval[0]>0 or interval[1]<0,
                    note='Observed repeat range, not a confidence interval or causal shader-only cost')
    comparisons=[compare((True,False),(False,False),'contact with static detail'),
                 compare((True,True),(False,True),'contact with flowing detail'),
                 compare((False,True),(False,False),'flow with contact off'),
                 compare((True,True),(True,False),'flow with contact on')]
    result=dict(passed=True,scope='Standalone editor -game RHI total GPU frame timing, not Shipping or isolated shader cost',
                path_match_max_cm=path_error,cases=cases,runs=rows,
                comparisons=comparisons,
                caveats=['RHI GPU counters can lag the game thread.',
                         'Fixed simulation steps ensure matching trajectories; no realtime FPS claim.',
                         'Other applications and laptop power/temperature can affect repeated runs.',
                         'Feature deltas include changed shading, geometry position and shadows; not a shader-only microbenchmark.'])
    (args.directory/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='runs'},indent=2))


if __name__=='__main__': main()
