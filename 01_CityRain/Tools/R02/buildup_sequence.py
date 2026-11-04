"""Build R02 up layer by layer for a before/after recording, from the bare street to the final look.

Run in the open editor (R02 map, day lighting, viewport Realtime on), from the Output Log's Cmd box:
    py "D:/aco/unreal/Stormfall/Tools/R02/buildup_sequence.py"        start / restart (6 s per step)
    py "D:/aco/unreal/Stormfall/Tools/R02/buildup_sequence.py" 10     10 s per step
    py "D:/aco/unreal/Stormfall/Tools/R02/buildup_sequence.py" stop   stop and restore
    py "D:/aco/unreal/Stormfall/Tools/R02/buildup_sequence.py" still 3   hold step 3 for a still (1-6)
Each step fades in over the first third of its time, then holds. Fog, light and controller values are
restored at the end; nothing is saved. Do not save the map while it runs.
"""
import sys
import time
import unreal as u

# Each step adds one layer on top of the previous one. The last step is the shipped look.
FIELDS = ['fog_density', 'fog_extinction', 'shafts', 'rain', 'wetness', 'puddles']
STEPS = [
    ('1 Original: no fog, no light shafts, dry', (0.005, 0.0, 0.0, 0.0, 0.0, 0.0)),
    ('2 + Height and volumetric fog',             (0.025, 4.0, 0.0, 0.0, 0.0, 0.0)),
    ('3 + Light shafts (volumetric scattering)',  (0.025, 4.0, 6.0, 0.0, 0.0, 0.0)),
    ('4 + Rain',                                  (0.025, 4.0, 6.0, 1.0, 0.0, 0.0)),
    ('5 + Wet surfaces',                          (0.025, 4.0, 6.0, 1.0, 1.0, 0.0)),
    ('6 + Puddles and ripples (final)',           (0.025, 4.0, 6.0, 1.0, 1.0, 1.0)),
]
FADE_FRACTION = 1.0 / 3.0
CONTROLLER_CLASS = 'BP_WeatherArtController_C'
CONTROLLER_NAMES = ['UseManualControl', 'ManualWetness', 'ManualRain', 'ManualPuddles']
DAY_LEVEL = 'Daytime_Lighting'
STATE_KEY = '_stormfall_buildup_sequence'


def find_targets():
    actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    controllers = [a for a in actors if a.get_class().get_name() == CONTROLLER_CLASS]
    fogs = [a for a in actors if isinstance(a, u.ExponentialHeightFog) and DAY_LEVEL in a.get_path_name()]
    lights = [a for a in actors if isinstance(a, u.DirectionalLight) and DAY_LEVEL in a.get_path_name()]
    if len(controllers) != 1 or len(fogs) != 1 or len(lights) != 1:
        raise RuntimeError('Expected one controller, day fog and day sun; found %d, %d, %d'
                           % (len(controllers), len(fogs), len(lights)))
    return (controllers[0], fogs[0].get_component_by_class(u.ExponentialHeightFogComponent),
            lights[0].get_component_by_class(u.DirectionalLightComponent))


def sample(t, step_seconds):
    index = min(int(t // step_seconds), len(STEPS) - 1)
    target = STEPS[index][1]
    previous = STEPS[index - 1][1] if index > 0 else target
    w = min((t - index * step_seconds) / (step_seconds * FADE_FRACTION), 1.0)
    return index, dict(zip(FIELDS, (a + (b - a) * w for a, b in zip(previous, target))))


def apply(targets, v):
    controller, fog, sun = targets
    fog.set_fog_density(v['fog_density'])
    fog.set_volumetric_fog_extinction_scale(v['fog_extinction'])
    sun.set_volumetric_scattering_intensity(v['shafts'])
    for name, value in (('UseManualControl', True), ('ManualWetness', v['wetness']),
                        ('ManualRain', v['rain']), ('ManualPuddles', v['puddles'])):
        controller.set_editor_property(name, value)
    controller.call_method('ApplyArtistControls')


def stop():
    state = getattr(u, STATE_KEY, None)
    if not state:
        return
    u.unregister_slate_post_tick_callback(state['handle'])
    controller, fog, sun = state['targets']
    original = state['original']
    fog.set_fog_density(original['fog_density'])
    fog.set_volumetric_fog_extinction_scale(original['fog_extinction'])
    sun.set_volumetric_scattering_intensity(original['shafts'])
    for name in CONTROLLER_NAMES:
        controller.set_editor_property(name, original[name])
    controller.call_method('ApplyArtistControls')
    setattr(u, STATE_KEY, None)
    u.log('[Buildup] stopped; fog, sun and controller values restored')


def start(step_seconds):
    stop()
    targets = find_targets()
    controller, fog, sun = targets
    original = {n: controller.get_editor_property(n) for n in CONTROLLER_NAMES}
    original.update(fog_density=fog.get_editor_property('fog_density'),
                    fog_extinction=fog.get_editor_property('volumetric_fog_extinction_scale'),
                    shafts=sun.get_editor_property('volumetric_scattering_intensity'))
    # Wall-clock time, so the timing stays fixed even when the editor throttles or hitches.
    state = {'targets': targets, 'original': original, 'start': time.monotonic(), 'shown': -1}

    def tick(_delta):
        elapsed = time.monotonic() - state['start']
        index, values = sample(elapsed, step_seconds)
        apply(targets, values)
        if index != state['shown']:
            u.log('[Buildup] %.1f s: %s' % (elapsed, STEPS[index][0]))
            state['shown'] = index
        if elapsed > step_seconds * len(STEPS):
            stop()

    state['handle'] = u.register_slate_post_tick_callback(tick)
    setattr(u, STATE_KEY, state)
    u.log('[Buildup] started: %d steps x %.0f s' % (len(STEPS), step_seconds))


if len(sys.argv) > 1 and sys.argv[1] == 'stop':
    stop()
elif len(sys.argv) > 2 and sys.argv[1] == 'still':
    # Hold one step for a still capture. Step 6 equals the shipped look, so end on it.
    stop()
    apply(find_targets(), dict(zip(FIELDS, STEPS[int(sys.argv[2]) - 1][1])))
    u.log('[Buildup] holding %s' % STEPS[int(sys.argv[2]) - 1][0])
else:
    start(float(sys.argv[1]) if len(sys.argv) > 1 else 6.0)
