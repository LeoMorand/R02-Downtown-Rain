"""Verify saved native replay captures. Does not launch UE or measure cost."""
import argparse
import hashlib
import json
import math
import statistics
import struct
import zlib
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--scope', choices=['full','short-preview','comparison'],default='full')
    args = parser.parse_args()
    data = json.loads((args.directory/'run.json').read_text(encoding='utf-8'))
    samples, frames, gpu = data['samples'], data['frames'], data['gpu_samples']
    assert samples and frames and gpu, 'Missing captured evidence'
    positions = [s['location'] for s in samples]
    distance = sum(math.dist(a,b) for a,b in zip(positions,positions[1:]))
    gaps = [b['game_seconds']-a['game_seconds'] for a,b in zip(frames,frames[1:])]
    phases = {name:any(lo <= s['sequence_seconds'] <= hi for s in samples)
              for name,lo,hi in [('straight',4,8),('turn',10,14),('hold',15.2,17.8),
                                ('return',25,35),('stationary',37,41),('boundary',47.6,48.4),('end_hold',54,60)]}
    if args.scope=='short-preview':
        phases = {name:any(lo<=s['sequence_seconds']<=hi for s in samples) for name,lo,hi in
                  [('straight',4,7.8),('turn',10,14),('hold',15.2,17.8),('moving_again',19,23)]}
    if args.scope=='comparison':
        phases={name:any(lo<=s['sequence_seconds']<=hi for s in samples) for name,lo,hi in
                [('straight',4,8),('turn',10,11.8)]}
    path_error = max(s['path_error_cm'] for s in samples)
    finite = all(s['finite'] for s in gpu)
    copied = max(s['height_copy_error'] for s in gpu)
    moving = max(s['max_abs_velocity'] for s in gpu)
    source = args.directory/'harness.py'
    report = dict(complete=data['complete'],error=data.get('error'),settings_restored=data['settings_restored'],
                  sampled_positions=len(samples),captured_frames=len(frames),
                  first_game_seconds=frames[0]['game_seconds'],last_game_seconds=frames[-1]['game_seconds'],
                  duration_game_seconds=frames[-1]['game_seconds']-frames[0]['game_seconds'],
                  median_capture_interval_seconds=statistics.median(gaps),max_capture_interval_seconds=max(gaps),
                  measured_capture_cadence_hz=1/statistics.median(gaps),
                  capture_clock_mode=data['capture_settings'].get('clock_mode','realtime game clock'),
                  elapsed_wall_seconds=data['elapsed_wall_seconds'],
                  fixed_step_offline_fps=data['capture_settings'].get('fixed_fps',0),
                  path_error_max_cm=path_error,sampled_path_distance_cm=distance,
                  x_range=[min(p[0] for p in positions),max(p[0] for p in positions)],phase_coverage=phases,
                  input_counts=sorted(set(s['input_count'] for s in samples)),
                  gpu_samples=len(gpu),readback_pixels_per_sample=[s['pixels'] for s in gpu],
                  gpu_sampled_values_finite=finite,max_height_copy_error=copied,max_abs_sampled_velocity=moving,
                  frames_exist=all((args.directory/f['file']).is_file() for f in frames),
                  harness_hash_matches=source.is_file() and hashlib.sha256(source.read_bytes()).hexdigest()==data['source_sha256'],
                  scope='Path playback and sampled state coherence. Instrumented cadence is not uninstrumented runtime FPS.')
    report['passed'] = (data['complete'] and not data.get('error') and data['settings_restored']
                        and all(phases.values()) and path_error<.01 and distance>({'comparison':500,'short-preview':1000}.get(args.scope,3000))
                        and report['x_range'][1]>({'comparison':250,'short-preview':400}.get(args.scope,1000)) and finite and copied<.001 and moving>.001
                        and all(s['material_normal_bound'] for s in gpu)
                        and report['input_counts']==[1] and report['frames_exist'] and report['harness_hash_matches'])
    report['smooth_preview_capture'] = report['median_capture_interval_seconds']<=1/24 and max(gaps)<.2
    if any(stage in data['map'] for stage in ['/Phase07/','/Phase08/','/Phase09/']):
        contract = data.get('contact_contract') or {}
        report['contact_visual_proxy_validated'] = (
            contract.get('radius_cm') == 20 and contract.get('height_cm') == 20
            and contract.get('enabled') == 1 and contract.get('root_z_cm') == 20
            and all(s.get('contact_normal_bound') is True for s in gpu))
        report['passed'] = report['passed'] and report['contact_visual_proxy_validated']
    report['validation_scope'] = args.scope
    # The engine export writes valid PNGs followed by stale allocation bytes in
    # this installation. Preserve originals, validate every chunk CRC and copy
    # only the valid PNG container through IEND. Pixel data is unchanged.
    clean = args.directory/'clean_frames'
    clean.mkdir(exist_ok=True)
    removed = []
    encode_paths = []
    for frame in frames:
        raw = (args.directory/frame['file']).read_bytes()
        if Path(frame['file']).suffix.lower() in ['.jpg','.jpeg']:
            assert raw[:2]==b'\xff\xd8' and raw[-2:]==b'\xff\xd9', 'Incomplete JPEG'
            encode_paths.append(frame['file'])
            continue
        assert raw[:8] == b'\x89PNG\r\n\x1a\n'
        offset = 8
        while True:
            assert offset+12 <= len(raw)
            size = struct.unpack('>I',raw[offset:offset+4])[0]
            kind = raw[offset+4:offset+8]
            payload = raw[offset+8:offset+8+size]
            assert offset+12+size <= len(raw)
            crc = struct.unpack('>I',raw[offset+8+size:offset+12+size])[0]
            assert zlib.crc32(kind+payload)&0xffffffff == crc, 'PNG chunk CRC failure'
            offset += size+12
            if kind == b'IEND':
                assert size == 0
                break
        removed.append(len(raw)-offset)
        (clean/Path(frame['file']).name).write_bytes(raw[:offset])
        encode_paths.append('clean_frames/'+Path(frame['file']).name)
    report['png_tail_bytes_removed_total'] = sum(removed)
    report['original_png_files_preserved'] = True
    (args.directory/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    # Vary frame durations to preserve the captured GAME timeline, even if the
    # editor is throttled. Never imply a higher captured frame rate by renaming.
    lines=['ffconcat version 1.0']
    for index,frame in enumerate(frames):
        lines += ["file '"+encode_paths[index]+"'",'duration %.9f'%(gaps[index] if index<len(gaps) else statistics.median(gaps))]
    lines += ["file '"+encode_paths[-1]+"'"]
    (args.directory/'frames.ffconcat').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__=='__main__':
    main()
