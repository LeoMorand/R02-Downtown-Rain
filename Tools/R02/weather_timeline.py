"""Drive the R02 WeatherArtController along a fixed timeline for repeatable recording.

Run in the open editor (R02 map, viewport Realtime on), from the Output Log's Cmd box:
    py "D:/aco/unreal/Stormfall/Tools/R02/weather_timeline.py"          start / restart
    py "D:/aco/unreal/Stormfall/Tools/R02/weather_timeline.py" 3        same timeline, 3x slower
    py "D:/aco/unreal/Stormfall/Tools/R02/weather_timeline.py" stop     stop and restore
Works in the editor world (manual mode). Original controller values are restored at the end;
nothing is saved. Do not save the map while it runs.
"""
import sys
import time
import unreal as u

# (seconds, wetness, rain, puddles). Values are linearly interpolated between keys.
KEYS = [
    (0.0,  0.0, 0.0, 0.0),   # dry street
    (3.0,  0.0, 0.0, 0.0),
    (8.0,  0.0, 1.0, 0.0),   # rain arrives
    (18.0, 1.0, 1.0, 0.0),   # surfaces darken and gloss up
    (28.0, 1.0, 1.0, 1.0),   # puddles grow and ripple
    (36.0, 1.0, 1.0, 1.0),   # hold for the ripple shot
]
CONTROLLER_CLASS = 'BP_WeatherArtController_C'
NAMES = ['UseManualControl', 'ManualWetness', 'ManualRain', 'ManualPuddles']
STATE_KEY = '_stormfall_weather_timeline'


def sample(t):
    if t <= KEYS[0][0]:
        return KEYS[0][1:]
    for (t0, *a), (t1, *b) in zip(KEYS, KEYS[1:]):
        if t <= t1:
            w = (t - t0) / (t1 - t0)
            return tuple(x + (y - x) * w for x, y in zip(a, b))
    return KEYS[-1][1:]


def find_controller():
    actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    found = [a for a in actors if a.get_class().get_name() == CONTROLLER_CLASS]
    if len(found) != 1:
        raise RuntimeError('Expected one %s in the open level, found %d' % (CONTROLLER_CLASS, len(found)))
    return found[0]


def apply(controller, values):
    for name, value in values.items():
        controller.set_editor_property(name, value)
    controller.call_method('ApplyArtistControls')


def activate_rain():
    # The weather pack only activates its rain emitter on BeginPlay; in the editor it starts inactive.
    actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    for actor in actors:
        if actor.get_class().get_name().startswith('WeatherManagmentBP_C'):
            for comp in actor.get_components_by_class(u.NiagaraComponent):
                if comp.get_name() == 'Rain':
                    comp.activate(True)
                    return True
    u.log_warning('[WeatherTimeline] rain Niagara component not found; rain will not show in the editor')
    return False


def stop():
    state = getattr(u, STATE_KEY, None)
    if not state:
        return
    u.unregister_slate_post_tick_callback(state['handle'])
    apply(state['controller'], state['original'])
    setattr(u, STATE_KEY, None)
    u.log('[WeatherTimeline] stopped; controller values restored')


def start(stretch=1.0):
    stop()
    controller = find_controller()
    # Wall-clock time, so the timing stays fixed even when the editor throttles or hitches.
    state = {'controller': controller, 'start': time.monotonic(), 'next_key': 1,
             'original': {n: controller.get_editor_property(n) for n in NAMES}}

    def tick(_delta):
        # Timeline time: a stretch of 3 plays the same keys three times slower.
        elapsed = (time.monotonic() - state['start']) / stretch
        wetness, rain, puddles = sample(elapsed)
        apply(controller, {'UseManualControl': True, 'ManualWetness': wetness,
                           'ManualRain': rain, 'ManualPuddles': puddles})
        if state['next_key'] < len(KEYS) and elapsed >= KEYS[state['next_key']][0]:
            u.log('[WeatherTimeline] %.1f s: wetness %.2f rain %.2f puddles %.2f' % (elapsed, wetness, rain, puddles))
            state['next_key'] += 1
        if elapsed > KEYS[-1][0]:
            stop()

    activate_rain()
    state['handle'] = u.register_slate_post_tick_callback(tick)
    setattr(u, STATE_KEY, state)
    u.log('[WeatherTimeline] started: %.0f s' % (KEYS[-1][0] * stretch))


if len(sys.argv) > 1 and sys.argv[1] == 'stop':
    stop()
else:
    start(float(sys.argv[1]) if len(sys.argv) > 1 else 1.0)
