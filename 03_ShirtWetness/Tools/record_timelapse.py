"""Record a dry -> soaked timelapse in PIE on L_ShirtWetness_Street.
Each captured frame advances the real wetness simulation by STEP seconds under the level's rain,
so the clip shows the component's own accumulation, not a keyed parameter. Run start() in PIE;
frames land in Saved/Timelapse/frame_NNNN.png and wetness per frame in wetness.json.
"""
import json, os, sys, unreal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import look_review

OUT = os.path.join(unreal.Paths.project_saved_dir(), 'Timelapse')
FRAMES, STEP, TICKS_PER_FRAME = 144, 0.25, 4      # 36 s of simulated rain
_state = {}

def _tick(dt):
    s = _state
    s['tick'] += 1
    if s['tick'] % TICKS_PER_FRAME: return
    i = s['frame']
    if i >= FRAMES:
        unreal.unregister_slate_post_tick_callback(s['handle'])
        json.dump(s['w'], open(os.path.join(OUT, 'wetness.json'), 'w'))
        return
    if i:                                         # frame 0 is the dry state
        s['comp'].advance_wetness(STEP)
        s['comp'].apply_to_materials()
    v = list(s['comp'].get_editor_property('wetness_values'))
    s['w'].append(sum(v) / len(v))
    unreal.AutomationLibrary.take_high_res_screenshot(1280, 720, os.path.join(OUT, 'frame_%04d.png' % i))
    s['frame'] += 1

def start():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    unreal.SystemLibrary.execute_console_command(world, 'DisableAllScreenMessages')
    look_review.view()
    hero = [a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
            if a.get_actor_label() == 'Shirt_Street_Hero'][0]
    comp = hero.get_component_by_class(unreal.StormfallShirtWetnessComponent)
    comp.refresh_environment(); comp.set_uniform_wetness(0.0); comp.apply_to_materials()
    _state.update(comp=comp, tick=0, frame=0, w=[])
    _state['handle'] = unreal.register_slate_post_tick_callback(_tick)
    return OUT

def status():
    return {'frame': _state.get('frame'), 'of': FRAMES}
