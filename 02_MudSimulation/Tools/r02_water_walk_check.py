"""Short, PIE-only R02 water placement check; never writes Unreal assets."""
import json
import time
import traceback
from pathlib import Path
import unreal as u

OUT = Path('D:/aco/unreal/Stormfall/Verification/MudProfessional/phase20-r02-water')
S = {}

def finish(error=None):
    handle = S.pop('handle', None)
    if handle:
        u.unregister_slate_post_tick_callback(handle)
    S['input'].inject_input_vector_for_action(S['move'], u.Vector(), [], [])
    S['movement'].stop_movement_immediately()
    u.GameplayStatics.set_game_paused(S['world'], True)
    actor = S['actor']
    rt = actor.get_editor_property('output')
    normal = actor.get_editor_property('normal_pass').get_editor_property('normal_output')
    result = dict(complete=error is None, error=error, samples=S['samples'], probes=S['probes'],
        output_size=[rt.size_x, rt.size_y], normal_size=[normal.size_x, normal.size_y],
        material=actor.get_editor_property('surface_material').get_path_name(),
        scope='Actual Enhanced Input walk and live RT samples; not a performance or physical water validation.')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'walk-check.json').write_text(json.dumps(result, indent=2), encoding='utf-8')

def tick(dt):
    try:
        elapsed = u.GameplayStatics.get_time_seconds(S['world']) - S['start']
        pos = S['pawn'].get_actor_location()
        if elapsed > 6 or pos.x > 5800 or time.monotonic() - S['wall_start'] > 55:
            finish()
            return
        S['input'].inject_input_vector_for_action(S['move'], u.Vector(0, .5 if elapsed > 1 else 0, 0), [], [])
        if elapsed - S['last_sample'] > .1:
            vel = S['pawn'].get_velocity()
            S['samples'].append(dict(seconds=elapsed, position=[pos.x, pos.y, pos.z], velocity=[vel.x, vel.y, vel.z], falling=S['movement'].is_falling()))
            S['last_sample'] = elapsed
        if elapsed - S['last_probe'] > .65:
            rt = S['actor'].get_editor_property('output')
            pixels = u.RenderingLibrary.read_render_target_raw_pixel_area(S['world'], rt, 992, 992, 64, 64, False)
            S['probes'].append(dict(seconds=elapsed, min_b=min(p.b for p in pixels), max_b=max(p.b for p in pixels), mean_b=sum(p.b for p in pixels)/len(pixels), mean_abs_velocity=sum(abs(p.r)+abs(p.g) for p in pixels)/len(pixels)))
            S['last_probe'] = elapsed
    except Exception:
        finish(traceback.format_exc())

def start(input_path):
    assert not S.get('handle')
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    assert world and 'UEDPIE_' in world.get_path_name() and 'L_R02_WaterPreview' in world.get_path_name()
    actor = next(a for a in u.GameplayStatics.get_all_actors_of_class(world, u.Actor) if a.get_actor_label() == 'R02_InteractiveWater')
    pawn = u.GameplayStatics.get_player_pawn(world, 0)
    movement = pawn.get_component_by_class(u.CharacterMovementComponent)
    movement.stop_movement_immediately()
    actor.set_actor_location(u.Vector(5650, -450, 2.57704544), False, True)
    actor.get_editor_property('surface').set_visibility(True, False)
    pawn.set_actor_location(u.Vector(5300, -450, 100), False, True)
    pawn.set_actor_rotation(u.Rotator(), True)
    u.GameplayStatics.get_player_controller(world, 0).set_control_rotation(u.Rotator(pitch=-28))
    input_system = u.find_object(None, input_path)
    assert input_system
    S.clear()
    S.update(world=world, actor=actor, pawn=pawn, movement=movement, input=input_system,
        move=u.load_asset('/Game/WeatherSystem/Input/Actions/IA_Move'),
        start=u.GameplayStatics.get_time_seconds(world), wall_start=time.monotonic(),
        samples=[], probes=[], last_sample=-1, last_probe=-1)
    u.GameplayStatics.set_game_paused(world, False)
    S['handle'] = u.register_slate_post_tick_callback(tick)
