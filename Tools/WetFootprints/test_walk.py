"""PIE smoke test for wet footprints: walk the player character forward, then report the prints.

Run in the editor while PIE is running:  py "D:/aco/unreal/Stormfall/Tools/WetFootprints/test_walk.py"
Walks for WALK_SECONDS by feeding forward movement input every frame (no Enhanced Input needed),
then logs how many footprint decals exist. Read the result in the Output Log: [WetFootprintTest].
"""
import time
import unreal as u

WALK_SECONDS = 6.0
KEY = '_stormfall_footprint_test'


def pie_world():
    worlds = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    return worlds


def count_prints(world):
    settings = world.get_world_settings()
    decals = [c for c in settings.get_components_by_class(u.DecalComponent)]
    return len(decals)


def start():
    world = pie_world()
    if not world:
        u.log_warning('[WetFootprintTest] PIE is not running')
        return
    pawn = u.GameplayStatics.get_player_pawn(world, 0)
    if not pawn:
        u.log_warning('[WetFootprintTest] no player pawn')
        return
    mesh = pawn.get_component_by_class(u.SkeletalMeshComponent)
    state = {'start': time.monotonic(), 'pawn': pawn, 'world': world, 'begin': pawn.get_actor_location(),
             'heights': {'foot_l': [], 'foot_r': []}}

    def foot_heights():
        # Bone height above the ground under it, the same measure AStormfallWetFootprints uses.
        for bone, samples in state['heights'].items():
            p = mesh.get_socket_location(bone)
            hit = u.SystemLibrary.line_trace_single(state['world'], p, p - u.Vector(0, 0, 200),
                                                   u.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [state['pawn']],
                                                   u.DrawDebugTrace.NONE, True)
            if hit:
                samples.append(p.z - hit.to_tuple()[4].z)

    def finish(message):
        u.unregister_slate_post_tick_callback(state['handle'])
        u.log('[WetFootprintTest] ' + message)

    def tick(_delta):
        try:
            elapsed = time.monotonic() - state['start']
            if elapsed < WALK_SECONDS:
                state['pawn'].add_movement_input(state['pawn'].get_actor_forward_vector(), 1.0, True)
                foot_heights()
                return
            moved = (state['pawn'].get_actor_location() - state['begin']).length()
            stats = ', '.join('%s min %.1f max %.1f cm' % (b, min(s), max(s)) for b, s in state['heights'].items() if s)
            finish('walked %.0f cm, footprint decals alive: %d; foot heights: %s' % (moved, count_prints(state['world']), stats))
        except Exception as error:   # PIE ended or pawn gone: never leave a failing callback registered
            finish('stopped: %s' % error)

    state['handle'] = u.register_slate_post_tick_callback(tick)
    u.log('[WetFootprintTest] walking for %.0f s' % WALK_SECONDS)


start()
