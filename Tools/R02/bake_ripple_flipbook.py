"""Bake the R02 procedural ripple into a seamlessly tiling, looping flipbook of ripple slopes.

The ripple math is a float32 port of ripple_candidate_v2.hlsl (without culling, which does not
change the result). Two changes make the output periodic:
  - cell indices wrap modulo CELLS, so the tile repeats in space;
  - event indices wrap modulo EVENTS_PER_LOOP, so the animation repeats every LOOP_SECONDS.

Output: RG = ripple slope (x, y) encoded as slope / SLOPE_RANGE * 0.5 + 0.5, B unused.
Strength and the final slope clamp are applied at runtime (ripple_flipbook.hlsl).

usage: python -I Tools/R02/bake_ripple_flipbook.py   (needs numpy and Pillow)
"""
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image

f32 = np.float32
U = np.uint32
OUT = Path(__file__).resolve().parent / 'RippleBake'

# Scene values read back from R02 on 2026-10-25 (material defaults + WeatherArtController).
SPACING_CM, RADIUS_CM, RATE, DENSITY = 18.0, 7.0, 1.5, 0.85
ARTIST_SIZE, ARTIST_DENSITY, ARTIST_SPEED, RANDOMNESS = 0.873118, 0.552331, 0.767253, 0.85

FRAME_PX = 256
COLUMNS, ROWS = 8, 4         # 32 frames in one atlas
SLOPE_RANGE = 0.5            # encoded slope range; runtime clamps to 0.18 * strength anyway
LAYERS = 2                   # runtime overlays two rotated layers; each carries 1/LAYERS of the events
TILE_CM = 121.0996           # kept fixed so the runtime constant does not change between presets

# 'scene' reproduces the procedural tier's look (about 16 impacts per m^2 per second: drizzle).
# 'downpour' targets heavy rain (about 150). Offline cost is irrelevant, so it uses a finer grid,
# more past events per lane and rings up to 0.9 cell (3x3 neighbours still cover any ring <= 1 cell).
PRESETS = {
    'scene':    dict(cells=5,  speed=None, events_per_loop=3, prev=2, radius_cells=.48, amplitude=1.0),
    'downpour': dict(cells=10, speed=3.07, events_per_loop=8, prev=4, radius_cells=.9,  amplitude=1.6),
}
PRESET = PRESETS[os.environ.get('RIPPLE_PRESET', 'downpour')]


def mix(h):
    h = h ^ (h >> U(16)); h = h * U(2146121005)
    h = h ^ (h >> U(15)); h = h * U(2221713035)
    return h ^ (h >> U(16))


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def bake():
    scatter = f32(RANDOMNESS)
    CELLS = PRESET['cells']
    cell_size = f32(TILE_CM / CELLS)
    radius_max = f32(min(max(RADIUS_CM * np.clip(ARTIST_SIZE, .25, 2.0), 1.0), cell_size * PRESET['radius_cells']))
    base_rate = f32(np.clip(RATE, .2, 3.0))
    speed = f32(PRESET['speed'] or np.clip(ARTIST_SPEED, .1, 2.0) * base_rate)   # events per second per lane
    # Ring age in seconds is (clock - event) / rate; downpour uses its own event rate as the time base.
    rate = speed if PRESET['speed'] else base_rate
    tile_cm = CELLS * cell_size
    EVENTS_PER_LOOP = PRESET['events_per_loop']
    loop_seconds = EVENTS_PER_LOOP / speed
    frames = COLUMNS * ROWS
    pixel_cm = tile_cm / FRAME_PX
    width = f32(max(1.0, pixel_cm * .6))                          # footprint of one baked texel
    footprint = pixel_cm

    ys, xs = np.mgrid[0:FRAME_PX, 0:FRAME_PX]
    P = np.stack([(xs + .5) * pixel_cm, (ys + .5) * pixel_cm], -1).reshape(-1, 2).astype(f32)
    base = np.floor(P / cell_size)
    atlas = np.zeros((ROWS * FRAME_PX, COLUMNS * FRAME_PX, 3), np.uint8)
    peak = 0.0
    for frame in range(frames):
        seconds = f32(frame / frames * loop_seconds)
        slope = np.zeros_like(P)
        for iy in (-1, 0, 1):
            for ix in (-1, 0, 1):
                c = base + np.array([ix, iy], f32)
                wrapped = np.mod(c, CELLS).astype(np.int64).astype(U)   # spatial period
                for lane in (0, 1):
                    keep_p = f32(1 - .5 * scatter) if lane == 0 else f32(.5 * scatter)
                    ch = wrapped[:, 0] * U(1597334677) ^ wrapped[:, 1] * U(3812015801) ^ U(lane) * U(2798796415)
                    phase_off = (mix(ch ^ U(2246822519)) & U(0xffffff)).astype(f32) / f32(16777216)
                    clock = seconds * speed + phase_off
                    cycle = np.floor(clock)
                    for prev in range(PRESET['prev']):
                        ei = cycle - prev
                        age = (clock - ei) / rate
                        ei_wrapped = np.mod(ei, EVENTS_PER_LOOP).astype(np.int64).astype(U)  # time period
                        h = mix((ch ^ ei_wrapped * U(3266489917))[:, None] ^ np.array([2747636419, 668265263, 374761393], U))
                        r = (h & U(0xffffff)).astype(f32) / f32(16777216)
                        v = (mix(h ^ np.array([1274126177, 42595009, 197830471], U)) & U(0xffffff)).astype(f32) / f32(16777216)
                        keep = (v[:, 0] < keep_p).astype(f32)
                        life = np.minimum((.65 + r[:, 2] * .25) * (1 - scatter) + (.48 + v[:, 1] * .42) * scatter, (PRESET['prev'] - .05) / rate)
                        phase = np.clip(age / life, 0, 1)
                        alive = (age <= life) * (r[:, 2] <= DENSITY / LAYERS) * keep
                        off = (.15 + r[:, :2] * .7) * (1 - scatter) + (.02 + r[:, :2] * .96) * scatter
                        delta = P - (c + off) * cell_size
                        d = np.maximum(np.sqrt((delta ** 2).sum(1)), .001)
                        event_radius = radius_max * (1 + (.6 + v[:, 2] * .65 - 1) * scatter)
                        x = d - event_radius * (.12 + .88 * phase)
                        envelope = np.exp(-x * x / (width * width))
                        fade = smooth(0, .12, phase) * (1 - phase)
                        aa = 1 - smooth(event_radius * .35, event_radius, footprint)
                        derivative = (-2 * x / (width * width)) * envelope
                        amplitude = 1 + (.55 + v[:, 1] * .9 - 1) * scatter
                        slope += delta / d[:, None] * (derivative * .18 * PRESET['amplitude'] * amplitude * fade * alive * aa)[:, None]
        peak = max(peak, float(np.abs(slope).max()))
        rg = np.clip(slope / SLOPE_RANGE * .5 + .5, 0, 1)
        img = np.zeros((FRAME_PX * FRAME_PX, 3), np.uint8)
        img[:, :2] = np.round(rg * 255).astype(np.uint8)
        col, row = frame % COLUMNS, frame // COLUMNS
        atlas[row * FRAME_PX:(row + 1) * FRAME_PX, col * FRAME_PX:(col + 1) * FRAME_PX] = img.reshape(FRAME_PX, FRAME_PX, 3)

    OUT.mkdir(exist_ok=True)
    Image.fromarray(atlas, 'RGB').save(OUT / 'T_RippleFlipbook.png')
    meta = {'preset': os.environ.get('RIPPLE_PRESET', 'downpour'), 'impacts_per_m2_s': float(speed * DENSITY / (cell_size / 100) ** 2), 'tile_cm': float(tile_cm), 'cell_cm': float(cell_size), 'cells': CELLS, 'frames': frames,
            'columns': COLUMNS, 'rows': ROWS, 'frame_px': FRAME_PX, 'loop_seconds': float(loop_seconds),
            'slope_range': SLOPE_RANGE, 'layers': LAYERS, 'baked_speed': float(speed), 'peak_abs_slope': peak, 'clipped': peak > SLOPE_RANGE,
            'params': {'SpacingCm': SPACING_CM, 'RadiusCm': RADIUS_CM, 'Rate': RATE, 'Density': DENSITY,
                       'ArtistSize': ARTIST_SIZE, 'ArtistDensity': ARTIST_DENSITY,
                       'ArtistSpeed': ARTIST_SPEED, 'ArtistRandomness': RANDOMNESS}}
    (OUT / 'T_RippleFlipbook.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    print(json.dumps(meta, indent=1))


if __name__ == '__main__':
    bake()
