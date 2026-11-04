"""Close-up A/B review of the wet cotton look in PIE. Call after prepare_review.prepare(state).
frame(label): fixed close-up camera in front of one runtime demo actor.
look(enabled): False reproduces the previous satin-era response on that actor's MIDs, so before/after
use the same actor, pose, camera, lighting and wetness state.
"""
import unreal

CLOSE = {'location': (0, 300, 118), 'fov': 38.0}
OLD = {'Wet Saturation': 1.0, 'Skin Show Through': 0.0, 'Wet Edge Darkening': 0.0, 'Wet Front Breakup': 0.0,
       'Wet Film Amount': 0.0, 'Wet Roughness': 0.46, 'Wet Albedo Multiplier': 0.48}
NEW = {'Wet Saturation': 1.4, 'Skin Show Through': 0.6, 'Wet Edge Darkening': 0.6, 'Wet Front Breakup': 1.0,
       'Wet Film Amount': 0.3, 'Wet Roughness': 0.68, 'Wet Albedo Multiplier': 0.55}

def _world():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    assert world
    return world

def _actor(world, label):
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StormfallShirtWeatherDemo):
        if a.get_actor_label() == label: return a
    raise ValueError(label)

def frame(label='Shirt_Runtime_Shelter'):
    world = _world()
    target = _actor(world, label).get_actor_location()
    x, y, z = CLOSE['location']
    # Reuse the PIE copy of the runtime overview camera; the saved level is untouched.
    cam = [c for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor)
           if c.get_actor_label() == 'Shirt_Runtime_OverviewCamera'][0]
    cam.set_actor_location_and_rotation(unreal.Vector(target.x+x, target.y+y, target.z+z),
                                        unreal.Rotator(roll=0, pitch=-2, yaw=-90), False, True)
    cam.camera_component.set_editor_property('field_of_view', CLOSE['fov'])
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    pc.set_view_target_with_blend(cam, 0.0)
    return str(cam.get_actor_location())

def view(camera_label='Shirt_Street_Camera'):
    """Use a placed camera as the PIE view (street showcase)."""
    world = _world()
    cam = [c for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor)
           if c.get_actor_label() == camera_label][0]
    unreal.GameplayStatics.get_player_controller(world, 0).set_view_target_with_blend(cam, 0.0)
    return camera_label

def soak(seconds=30.0, label='Shirt_Street_Hero'):
    """Step the wetness simulation under the current PIE weather (real accumulation, not a preset)."""
    world = _world()
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if a.get_actor_label() != label: continue
        c = a.get_component_by_class(unreal.StormfallShirtWetnessComponent)
        c.refresh_environment(); c.advance_wetness(seconds); c.apply_to_materials()
        return list(c.get_editor_property('wetness_values'))
    raise ValueError(label)

def look(enabled=True, label='Shirt_Runtime_Shelter', overrides=None, tint=None):
    """tint=[r,g,b] multiplies the garment albedo on the PIE MIDs only (e.g. a light shirt check)."""
    world = _world()
    actor = _actor(world, label)
    values = dict(NEW if enabled else OLD, **(overrides or {}))
    for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        if tint: comp.set_vector_parameter_value_on_materials('Base Color', unreal.Vector(*tint))
        for name, v in values.items():
            comp.set_scalar_parameter_value_on_materials(name, v)
    return values
