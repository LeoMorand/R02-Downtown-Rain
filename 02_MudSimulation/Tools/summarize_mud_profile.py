"""Summarize frame-aligned CSV data without printing event payloads."""
import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Verification/MudWholeProfile'
csv.field_size_limit(10**7)


def main():
    run = json.loads((OUT / 'verified_run.json').read_text(encoding='utf-8-sig'))
    smoke = json.loads((OUT / 'verified_smoke.json').read_text(encoding='utf-8-sig'))
    path = max((OUT / 'Verified60').rglob('*.csv'), key=lambda p: p.stat().st_mtime)
    with path.open(newline='', encoding='utf-8-sig') as f:
        rows = list(csv.reader(f))
    # UE appends columns as stats appear, then writes the authoritative header
    # at the end. Early rows may have fewer trailing columns.
    header = rows[-2] if rows[-2] and rows[-2][0] == 'EVENTS' else rows[0]
    frame_index = header.index('FrameTime')
    frames = []
    for row in rows[1:]:
        if len(row) > len(header) or len(row) <= frame_index:
            continue
        try:
            float(row[frame_index])
        except ValueError:
            continue
        frames.append(row + ['0'] * (len(header) - len(row)))
    measured = frames[run['warmup_frames']:]
    metrics = {}
    for name in ['FrameTime', 'GPUTime', 'GameThreadTime', 'RenderThreadTime',
                 'GPU/NiagaraGPUSimulation', 'GPU/Basepass', 'GPU/FXSystemPostRenderOpaque', 'GPU/TemporalSuperResolution']:
        values = sorted(float(row[header.index(name)]) for row in measured)
        nonzero = [v for v in values if v > 0]
        metrics[name] = {'samples': len(values), 'nonzero_samples': len(nonzero),
                         'median_ms': statistics.median(values), 'p95_ms': values[int(.95 * (len(values)-1))],
                         'max_ms': max(values), 'active_frame_median_ms': statistics.median(nonzero) if nonzero else None}
    report = {'pass': run['exit_code'] == 0 and smoke['pass'] and len(frames) == 900,
              'run': run, 'csv': str(path.relative_to(ROOT)), 'frames_recorded': len(frames),
              'warmup_frames_discarded': run['warmup_frames'], 'measured_frames': len(measured),
              'metrics': metrics, 'gpu_smoke': smoke,
              'scope': 'One static-brush minimal host; scene GPU and engine stage counters, not a POM-only microbenchmark or multi-object worst-case budget.',
              'limitations': ['CSV-enabled runs still return 777003 after a complete write and a logged exit status 0, including the empty control. Treat these stage timings as provisional.',
                              'FrameTime includes the 60Hz limiter; do not invert it into uncapped performance.',
                              'GPU/Basepass includes both planes and material work including POM; it is not isolated POM cost.',
                              'GPU scopes can be nested; medians must not be added to derive total GPU time.',
                              'Initial ExitAfterCsvProfiling runs returned 777003 including the empty control; retained only as diagnostic evidence.',
                              'This final run ends CSV first, then exits through the checked GPU smoke path.',
                              'Single local laptop run; no cross-hardware guarantee.']}
    (OUT / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'pass': report['pass'], 'frames': len(measured), 'metrics': metrics}))


if __name__ == '__main__':
    main()
