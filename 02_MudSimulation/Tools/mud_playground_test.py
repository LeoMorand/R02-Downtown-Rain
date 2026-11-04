"""Temporary, research-only Enhanced Input test. Does not author assets."""
import json
from pathlib import Path
import unreal as u

OUT = Path('D:/aco/unreal/Stormfall/Verification/MudProfessional/phase11-playground')
STATE = {}


def finish(error=None):
    handle = STATE.pop('handle', None)
    if handle:
        u.unregister_slate_post_tick_callback(handle)
    if 'input' in STATE:
        STATE['input'].inject_input_vector_for_action(STATE['move'], u.Vector(), [], [])
        STATE['input'].inject_input_vector_for_action(STATE['jump'], u.Vector(), [], [])
        STATE['input'].inject_input_vector_for_action(STATE['look'], u.Vector(), [], [])
    report = {k: STATE[k] for k in ['stage', 'samples', 'initial_location'] if k in STATE}
    report.update(complete=True, error=error, scope='Enhanced Input action injection, actual CharacterMovement and animation. No OS keyboard or asset edits.')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'input-test.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    u.log('MUD_PLAYGROUND_TEST_FINISHED '+str(error))


def start(input_subsystem_path):
    assert 'FluidNinjaStudy' in u.Paths.get_project_file_path()
    assert not STATE.get('handle')
    world = u.EditorLevelLibrary.get_game_world()
    assert world and 'UEDPIE_' in world.get_path_name() and 'L_Mud_Playground' in world.get_path_name()
    pc = u.GameplayStatics.get_player_controller(world, 0)
    pawn = u.GameplayStatics.get_player_pawn(world, 0)
    assert pawn and pawn.get_class().get_name() == 'BP_Mud_Manny_C'
    subsystem = u.find_object(None, input_subsystem_path)
    assert subsystem
    STATE.clear()
    STATE.update(world=world, pc=pc, pawn=pawn, input=subsystem,
                 move=u.load_asset('/Game/FluidNinjaLive/Meshes/Mannequin/Input/IA_Walk'),
                 jump=u.load_asset('/Game/FluidNinjaLive/Meshes/Mannequin/Input/IA_Jump'),
                 look=u.load_asset('/Game/FluidNinjaLive/Meshes/Mannequin/Input/IA_Look'),
                 start_time=u.GameplayStatics.get_time_seconds(world), stage='walk', samples=[], last_sample=-1)
    p = pawn.get_actor_location()
    STATE['initial_location'] = [p.x, p.y, p.z]
    STATE['handle'] = u.register_slate_post_tick_callback(tick)


def tick(delta):
    try:
        elapsed = u.GameplayStatics.get_time_seconds(STATE['world'])-STATE['start_time']
        if elapsed > 7:
            finish()
            return
        subsystem, pawn = STATE['input'], STATE['pawn']
        # Forward through the real IA_Walk graph. Finish well within the mud bay.
        move = 1 if elapsed < 2.7 else 0
        jump = 1 if 3.4 <= elapsed < 3.5 else 0
        look = .12 if 5.0 <= elapsed < 5.2 else 0
        STATE['stage'] = 'walk' if move else ('jump' if 3.4 <= elapsed < 4.9 else 'look_or_settle')
        subsystem.inject_input_vector_for_action(STATE['move'], u.Vector(0, move, 0), [], [])
        subsystem.inject_input_vector_for_action(STATE['jump'], u.Vector(jump, 0, 0), [], [])
        subsystem.inject_input_vector_for_action(STATE['look'], u.Vector(look, 0, 0), [], [])
        if elapsed-STATE['last_sample'] >= .1:
            STATE['last_sample'] = elapsed
            p, v = pawn.get_actor_location(), pawn.get_velocity()
            r = STATE['pc'].get_control_rotation()
            mesh = pawn.get_component_by_class(u.SkeletalMeshComponent)
            foot = mesh.get_socket_location('foot_l')
            STATE['samples'].append({'seconds': elapsed, 'location': [p.x, p.y, p.z],
                                     'velocity': [v.x, v.y, v.z], 'control_rotation': [r.pitch, r.yaw, r.roll],
                                     'foot_l': [foot.x, foot.y, foot.z], 'animation_instance': mesh.get_anim_instance().get_class().get_name(),
                                     'falling': pawn.get_component_by_class(u.CharacterMovementComponent).is_falling()})
    except Exception as exc:
        finish(str(exc))
