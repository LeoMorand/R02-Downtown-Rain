"""Temporary Enhanced Input smoke test for the Phase15 research map only."""
import json
from pathlib import Path
import unreal as u

OUT = Path('D:/aco/unreal/Stormfall/Verification/MudProfessional/phase15-surface-pool')
STATE = {}


def finish(error=None):
    handle = STATE.pop('handle', None)
    if handle:
        u.unregister_slate_post_tick_callback(handle)
    if 'input' in STATE:
        STATE['input'].inject_input_vector_for_action(STATE['move'], u.Vector(), [], [])
    report = {k: STATE[k] for k in ['samples', 'initial_location', 'direction', 'duration'] if k in STATE}
    report.update(complete=True, error=error, scope='Real IA_Walk input, CharacterMovement, skeletal animation; no OS input or asset edits.')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (STATE.get('report', 'walk')+'.json')).write_text(json.dumps(report, indent=2), encoding='utf-8')
    u.GameplayStatics.set_game_paused(STATE['world'], True)
    u.log('MUD_VISUAL_TEST_FINISHED '+str(error))


def start(input_subsystem_path, direction=1, duration=5, report='walk-in'):
    assert 'FluidNinjaStudy' in u.Paths.get_project_file_path()
    assert not STATE.get('handle')
    world = u.EditorLevelLibrary.get_game_world()
    assert world and 'UEDPIE_' in world.get_path_name() and 'L_Mud_SurfaceAndPool' in world.get_path_name()
    pawn = u.GameplayStatics.get_player_pawn(world, 0)
    assert pawn and pawn.get_class().get_name() == 'BP_Mud_Manny_C'
    subsystem = u.find_object(None, input_subsystem_path)
    assert subsystem
    STATE.clear()
    STATE.update(world=world, pawn=pawn, input=subsystem,
                 move=u.load_asset('/Game/FluidNinjaLive/Meshes/Mannequin/Input/IA_Walk'),
                 start_time=u.GameplayStatics.get_time_seconds(world), samples=[], last_sample=-1,
                 direction=direction, duration=duration, report=report)
    p = pawn.get_actor_location()
    STATE['initial_location'] = [p.x, p.y, p.z]
    STATE['handle'] = u.register_slate_post_tick_callback(tick)


def tick(delta):
    try:
        elapsed = u.GameplayStatics.get_time_seconds(STATE['world'])-STATE['start_time']
        if elapsed > STATE['duration']:
            finish()
            return
        pawn = STATE['pawn']
        move = STATE['direction'] if elapsed < STATE['duration'] else 0
        STATE['input'].inject_input_vector_for_action(STATE['move'], u.Vector(0, move, 0), [], [])
        if elapsed-STATE['last_sample'] >= .1:
            STATE['last_sample'] = elapsed
            p, v = pawn.get_actor_location(), pawn.get_velocity()
            mesh = pawn.get_component_by_class(u.SkeletalMeshComponent)
            foot = mesh.get_socket_location('foot_l')
            knee = mesh.get_socket_location('calf_l')
            hip = mesh.get_socket_location('thigh_l')
            movement = pawn.get_component_by_class(u.CharacterMovementComponent)
            STATE['samples'].append({'seconds': elapsed, 'location': [p.x, p.y, p.z],
                                     'velocity': [v.x, v.y, v.z], 'foot_l': [foot.x, foot.y, foot.z],
                                     'knee_l': [knee.x, knee.y, knee.z], 'hip_l': [hip.x, hip.y, hip.z],
                                     'max_walk_speed': movement.get_editor_property('max_walk_speed'),
                                     'animation_instance': mesh.get_anim_instance().get_class().get_name(),
                                     'falling': movement.is_falling()})
    except Exception as exc:
        finish(str(exc))
