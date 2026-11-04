"""ABAB GPU comparison of two reviewed ripple candidates in the R02 standalone benchmark.

Reproduces Run.ps1 -Mode install and RuntimeBenchmark.ps1 (full) with identical arguments, for hosts
without PowerShell 7. Each benchmark interleaves ripple off/on, so the per-run on-off delta is the
ripple cost; comparing deltas between candidates cancels slow drift between runs.

usage: python Tools/R02/ab_ripple.py [--plan]
"""
import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = Path('D:/aco/UE_5.8/Engine/Binaries/Win64')
PROJECT = ROOT / 'Stormfall.uproject'
MAP = '/Game/TA_Demos/R02_Downtown_Rain'
A, B = 'ripple_candidate_v1.hlsl', 'ripple_candidate_v2.hlsl'
# B is compiled for the first time after its first install: a discarded quick run absorbs that.
SEQUENCE = [('install', A), ('bench', 'A1'), ('install', B), ('warm', 'B0'), ('bench', 'B1'),
            ('install', A), ('bench', 'A2'), ('install', B), ('bench', 'B2')]


def stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')[:-3] + 'Z'


def assert_closed():
    # Only editors that have this project open block a run (same rule as Tools/Common.ps1).
    query = ("Get-CimInstance Win32_Process -Filter \"Name like 'UnrealEditor%'\" | "
             "ForEach-Object { $_.CommandLine }")
    result = subprocess.run(['powershell', '-NoProfile', '-Command', query], capture_output=True, text=True)
    if result.returncode != 0:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq UnrealEditor*'], capture_output=True, text=True).stdout
        if 'UnrealEditor' in out:
            raise SystemExit('Cannot inspect Unreal command lines; close Unreal editors before the run.')
        return
    project = str(PROJECT).replace('\\', '/').lower()
    if any(project in line.replace('\\', '/').lower() for line in result.stdout.splitlines()):
        raise SystemExit('This project is open in Unreal. Save your work and close it before the run.')


def gpu_snapshot():
    try:
        return subprocess.run(['nvidia-smi', '--query-gpu=name,utilization.gpu,memory.used,power.draw,'
                               'clocks.current.graphics,temperature.gpu', '--format=csv'],
                              capture_output=True, text=True, timeout=20).stdout.splitlines()
    except Exception:
        return ['unavailable']


def launch(exe, args, out, env, timeout):
    out.mkdir(parents=True)
    (out / 'command.json').write_text(json.dumps({'executable': str(exe), 'arguments': args,
                                                  'env': {k: env[k] for k in env if k.startswith('STORMFALL_R02')}},
                                                 indent=1), encoding='utf-8')
    (out / 'environment.json').write_text(json.dumps({'utc': stamp(), 'gpu': gpu_snapshot()}, indent=1), encoding='utf-8')
    proc = subprocess.Popen([str(exe)] + args, cwd=ROOT, env=env)
    try:
        code = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise SystemExit(f'Timed out; only PID {proc.pid} started here was stopped: {out}')
    return code


def install(candidate):
    out = ROOT / 'Verification/R02' / f'{stamp()}-{uuid.uuid4().hex[:6]}-install'
    args = [str(PROJECT), MAP, f'-ExecutePythonScript={ROOT}/Tools/R02/ue_acceptance.py', '-unattended', '-nosplash',
            '-nosound', '-nop4', '-NoLiveCoding', '-stdout', '-DisablePlugins=UE_MCP_Bridge,ModelContextProtocol,MudRuntime,MudAuthoring',
            f'-abslog={out}/Engine.log']
    env = dict(os.environ, STORMFALL_R02_MODE='install', STORMFALL_R02_OUTPUT=str(out), STORMFALL_R02_QUICK='0',
               STORMFALL_R02_CAMERA='', STORMFALL_R02_CANDIDATE=candidate)
    code = launch(ENGINE / 'UnrealEditor-Cmd.exe', args, out, env, 1800)
    result = json.loads((out / 'result.json').read_text(encoding='utf-8')) if (out / 'result.json').is_file() else {}
    if code != 0 or result.get('status') != 'completed':
        raise SystemExit(f'Install of {candidate} failed ({code}): {out}')
    return out


def bench(label, quick):
    out = ROOT / 'Verification/R02' / f'{stamp()}-runtime-benchmark-{label}'
    seconds = 180 if quick else 600
    variant = 'quick' if quick else 'full'
    args = [str(PROJECT), MAP, '-game', '-windowed', '-RenderOffscreen', '-ResX=1920', '-ResY=1080', '-ForceRes',
            '-NoVSync', '-NoLiveCoding', '-nosound', '-unattended', '-csvGpuStats', '-csvCompression=0',
            '-DisablePlugins=UE_MCP_Bridge,ModelContextProtocol,MudRuntime,MudAuthoring', f'-abslog={out}/Game.log', f'-seconds={seconds}',
            f'-ExecCmds=R02.Benchmark {out} {variant}']
    code = launch(ENGINE / 'UnrealEditor.exe', args, out, dict(os.environ), seconds + 900)
    result = json.loads((out / 'result.json').read_text(encoding='utf-8')) if (out / 'result.json').is_file() else {}
    if code != 0 or result.get('status') != 'completed' or result.get('width') != 1920 or result.get('height') != 1080:
        raise SystemExit(f'Benchmark {label} invalid ({code}): {out}')
    if not quick:
        if subprocess.run([sys.executable, str(ROOT / 'Tools/R02/summarize.py'), str(out)]).returncode != 0:
            raise SystemExit(f'Sample quality check failed: {out}')
    return out


def capture(camera, label, material_time=None, quick=False, extra_env=None):
    """Run.ps1 -Mode capture for one camera (all acceptance states); material_time pins ripple phase."""
    out = ROOT / 'Verification/R02' / f'{stamp()}-{uuid.uuid4().hex[:6]}-capture-{label}'
    args = [str(PROJECT), MAP, f'-ExecutePythonScript={ROOT}/Tools/R02/ue_acceptance.py', '-unattended', '-nosplash',
            '-nosound', '-nop4', '-NoLiveCoding', '-stdout', '-DisablePlugins=UE_MCP_Bridge,ModelContextProtocol,MudRuntime,MudAuthoring',
            f'-abslog={out}/Engine.log', '-RenderOffscreen', '-ResX=1920', '-ResY=1080', '-ForceRes', '-NoVSync']
    env = dict(os.environ, STORMFALL_R02_MODE='capture', STORMFALL_R02_OUTPUT=str(out), STORMFALL_R02_QUICK='0',
               STORMFALL_R02_CAMERA=camera)
    if material_time is not None:
        env['STORMFALL_R02_MATERIAL_TIME'] = str(material_time)
    if quick:
        env['STORMFALL_R02_QUICK'] = '1'
    env.update(extra_env or {})
    code = launch(ENGINE / 'UnrealEditor.exe', args, out, env, 1800)
    result = json.loads((out / 'result.json').read_text(encoding='utf-8')) if (out / 'result.json').is_file() else {}
    if code != 0 or result.get('status') != 'completed':
        raise SystemExit(f'Capture {label} failed ({code}): {out}')
    return out


def install_tier(tier):
    """Install or switch the baked/procedural ripple tier (install_ripple_flipbook.py)."""
    out = ROOT / 'Verification/R02' / f'{stamp()}-{uuid.uuid4().hex[:6]}-tier-{tier}'
    args = [str(PROJECT), f'-ExecutePythonScript={ROOT}/Tools/R02/install_ripple_flipbook.py', '-unattended',
            '-nosplash', '-nosound', '-nop4', '-NoLiveCoding', '-stdout',
            '-DisablePlugins=UE_MCP_Bridge,ModelContextProtocol,MudRuntime,MudAuthoring', f'-abslog={out}/Engine.log']
    env = dict(os.environ, STORMFALL_R02_OUTPUT=str(out), STORMFALL_RIPPLE_TIER=tier)
    code = launch(ENGINE / 'UnrealEditor-Cmd.exe', args, out, env, 1800)
    result = json.loads((out / 'result.json').read_text(encoding='utf-8')) if (out / 'result.json').is_file() else {}
    if code != 0 or result.get('status') != 'completed':
        raise SystemExit(f'Tier {tier} install failed ({code}): {out}')
    return out


# Procedural (P) vs baked (K) tier: same ABAB scheme; K gets a discarded warm-up for shader compilation.
TIER_SEQUENCE = [('tier', 'procedural'), ('bench', 'P1'), ('tier', 'baked'), ('warm', 'K0'), ('bench', 'K1'),
                 ('tier', 'procedural'), ('bench', 'P2'), ('tier', 'baked'), ('bench', 'K2'),
                 ('capture', 'K')]


# Visual check: B is installed after the A/B run. Capture B, switch to A, capture A, restore B.
CAPTURE_SEQUENCE = [('capture', 'B'), ('install', A), ('capture', 'A'), ('install', B)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--capture', metavar='CAMERA')
    parser.add_argument('--tiers', action='store_true', help='procedural vs baked flipbook ABAB')
    parser.add_argument('--single', metavar='CAMERA', help='one capture run of CAMERA; prints its folder')
    parser.add_argument('--label', default='single')
    parser.add_argument('--material-time', type=float, default=None, help='pin material time (seconds) for repeatable ripples')
    options = parser.parse_args()
    if options.plan:
        print(json.dumps(SEQUENCE)); return
    assert_closed()
    if options.single:
        print(capture(options.single, options.label, options.material_time))
        return
    if options.tiers:
        log = ROOT / 'Verification/R02' / f'{stamp()}-ripple-tier-ab.json'
        record = {'sequence': TIER_SEQUENCE, 'steps': []}
        for kind, value in TIER_SEQUENCE:
            if kind == 'tier':
                out = install_tier(value)
            elif kind == 'capture':
                out = capture('asphalt', value)
            else:
                out = bench(value, quick=(kind == 'warm'))
            record['steps'].append({'kind': kind, 'value': value, 'output': str(out), 'utc': stamp()})
            log.write_text(json.dumps(record, indent=1), encoding='utf-8')
            print(kind, value, out, flush=True)
        print('done', log)
        return
    if options.capture:
        log = ROOT / 'Verification/R02' / f'{stamp()}-ripple-capture-ab.json'
        record = {'camera': options.capture, 'sequence': CAPTURE_SEQUENCE, 'steps': []}
        for kind, value in CAPTURE_SEQUENCE:
            out = install(value) if kind == 'install' else capture(options.capture, value)
            record['steps'].append({'kind': kind, 'value': value, 'output': str(out), 'utc': stamp()})
            log.write_text(json.dumps(record, indent=1), encoding='utf-8')
            print(kind, value, out, flush=True)
        print('done', log)
        return
    log = ROOT / 'Verification/R02' / f'{stamp()}-ripple-ab.json'
    record = {'a': A, 'b': B, 'sequence': SEQUENCE, 'steps': []}
    for kind, value in SEQUENCE:
        out = install(value) if kind == 'install' else bench(value, quick=(kind == 'warm'))
        record['steps'].append({'kind': kind, 'value': value, 'output': str(out), 'utc': stamp()})
        log.write_text(json.dumps(record, indent=1), encoding='utf-8')
        print(kind, value, out, flush=True)
    print('done', log)


if __name__ == '__main__':
    main()
