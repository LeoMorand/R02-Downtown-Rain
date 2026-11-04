"""Summarize one completed R02 ABBA diagnostic. Reject missing/nonfinite GPU data."""
import argparse
import csv
import json
import math
import statistics
from pathlib import Path


def percentile(values, fraction):
    values = sorted(values)
    position = (len(values)-1)*fraction
    lo, hi = math.floor(position), math.ceil(position)
    return values[lo] + (values[hi]-values[lo])*(position-lo)


def read_csv(path, require_scene=False):
    captured, rendered = 0, 0
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        metrics = {}
        fields = reader.fieldnames or []
        consumed = {'FrameTime', 'GPUTime', 'GameThreadTime', 'RenderThreadTime', 'DrawCall/Basepass'}
        # UE can repeat unrelated shadow-cache counters. Never accept an
        # ambiguous timing, scene-coverage or GPU field used by this summary.
        ambiguous = {key for key in fields if fields.count(key) > 1
                     and (key in consumed or key.startswith('GPU/'))}
        if ambiguous:
            raise ValueError('Duplicate measured CSV columns: ' + str(sorted(ambiguous)))
        for row in reader:
            try:
                frame = float(row['FrameTime'])
                if not math.isfinite(frame) or frame <= 0:
                    continue
            except (KeyError, ValueError, TypeError):
                continue
            captured += 1
            try:
                scene_drawn = float(row.get('DrawCall/Basepass') or 0) > 0
            except (ValueError, TypeError):
                scene_drawn = False
            rendered += int(scene_drawn)
            if require_scene and not scene_drawn:
                continue
            for key, value in row.items():
                if key not in ('FrameTime', 'GPUTime', 'GameThreadTime', 'RenderThreadTime', 'DrawCall/Basepass') and not str(key).startswith('GPU/'):
                    continue
                try:
                    number = float(value)
                    if math.isfinite(number) and number >= 0:
                        metrics.setdefault(key, []).append(number)
                except (TypeError, ValueError):
                    pass
    result = {k: ({'count': len(v), 'median_draw_calls': statistics.median(v),
                 'nonzero_count': sum(x > 0 for x in v)} if k == 'DrawCall/Basepass' else
                {'count': len(v), 'median_ms': statistics.median(v), 'p95_ms': percentile(v, .95)})
            for k, v in metrics.items() if v}
    if require_scene:
        result['SceneFrameCoverage'] = {'captured_count': captured, 'rendered_count': rendered,
                                       'ratio': rendered/captured if captured else 0,
                                       'excluded_ui_only_frames': captured-rendered}
    return result


def summarize(folder):
    manifest = json.loads((folder / 'result.json').read_text(encoding='utf-8-sig'))
    if manifest.get('mode') != 'benchmark' or manifest.get('status') != 'completed':
        raise ValueError('A completed benchmark result is required')
    entries = manifest['samples']
    expected = ['off', 'on', 'on', 'off', 'on', 'off', 'off', 'on']
    if [e['variant'] for e in entries] != expected:
        raise ValueError('Incomplete or unexpected ABBA sequence')
    runs = []
    for entry in entries:
        name = entry['csv_requested']
        if Path(name).name != name or '\\' in name or '/' in name:
            raise ValueError('CSV must be a local basename')
        metrics = read_csv(folder / name, require_scene=True)
        coverage = metrics['SceneFrameCoverage']
        if coverage['ratio'] < 0.9:
            raise ValueError('Insufficient scene-rendered frames: require >=90% scene coverage before excluding UI-only rows: ' + name)
        gpu = metrics.get('GPUTime')
        if not gpu or gpu['median_ms'] <= 0 or gpu['count'] < 120:
            raise ValueError('Missing/insufficient GPUTime samples: ' + name)
        runs.append({'variant': entry['variant'], 'metrics': metrics, 'csv': name})
    # Four adjacent matched pairs, correcting sign for reversed acquisition order.
    deltas = []
    for a, b in zip(runs[::2], runs[1::2]):
        by_variant = {r['variant']: r['metrics']['GPUTime']['median_ms'] for r in (a, b)}
        deltas.append(by_variant['on'] - by_variant['off'])
    return {'scope': manifest.get('benchmark_scope', 'unknown'), 'runs': runs,
            'paired_gpu_median_deltas_ms': deltas,
            'median_paired_gpu_delta_ms': statistics.median(deltas),
            'sign_consistent': all(d > 0 for d in deltas) or all(d < 0 for d in deltas),
            'performance_acceptance': 'pending; review warmup, GPU clocks, PSO misses, camera FOV and viewport size',
            'frame_filter': 'Only rows with DrawCall/Basepass > 0 contribute timings; original coverage and excluded counts are reported. At least 90% of captured rows must render the scene. GPU counters can lag rendering.',
            'note': 'Nested GPU scopes cannot be summed. Capture scope comes from the manifest; Development results do not certify Shipping performance.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    result = summarize(args.folder)
    output = args.folder / 'summary.json'
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(output)
