"""Idempotent showcase dressing for L_ShirtWetness_Street (a copy of R02_Downtown_Rain).
Places the weather-driven shirt character on the R02 street in front of the verified street-wide
hero camera, swaps the chrome mannequin body for matte skin, plays an idle loop and adds a close
camera with key/rim lights. Re-running updates the labelled actors instead of adding new ones.
"""
import math, unreal

LEVEL = '/Game/Stormfall/ShirtTrial/Wetness/L_ShirtWetness_Street'
HERO_CAM = unreal.Vector(5100, 850, 170)        # R02 'street-wide' camera, yaw 20
HERO_YAW = 20.0
DISTANCE = 600.0                                # character distance along the hero view
CLOSE = {'distance': 340.0, 'height': 150.0, 'fov': 26.0, 'target': 135.0}   # waist-up: no trousers mesh
SKIN = '/Game/Stormfall/ShirtTrial/Wetness/Materials/M_ShirtShowcase_Skin'
TROUSERS = '/Game/Stormfall/ShirtTrial/Wetness/Materials/M_ShirtShowcase_Trousers'
TROUSER_SLOT = None                              # slot 0 = hands, slot 1 = head+torso+legs: no legs-only slot
IDLE = '/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle'
BP = '/Game/Stormfall/ShirtTrial/Wetness/BP_ShirtWeatherRuntime'
RAIN = '/Game/Stormfall/Weather/Rain/NS_R02_RainFollowView'
CLOSE_RAIN = {'along': 0.6, 'height': 500.0, 'rate': 10.0}   # fraction camera->feet, spawn Z, rate multiplier

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_path_name().startswith(LEVEL), world.get_path_name()

def labelled(label, cls, location, rotation=unreal.Rotator()):
    for a in actors.get_all_level_actors():
        if a.get_actor_label() == label: break
    else:
        a = actors.spawn_actor_from_class(cls, location, rotation)
        a.set_actor_label(label)
    a.set_actor_location_and_rotation(location, rotation, False, True)
    return a

def ground(x, y):
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 2000), unreal.Vector(x, y, -2000),
                                                 unreal.TraceTypeQuery.ECC_VISIBILITY, False, [],
                                                 unreal.DrawDebugTrace.NONE, True)
    assert hit, (x, y)
    return hit.to_tuple()[4].z                  # ImpactPoint

def look_at(src, dst):
    d = dst - src
    return unreal.Rotator(roll=0, pitch=math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))),
                          yaw=math.degrees(math.atan2(d.y, d.x)))

f = unreal.Vector(math.cos(math.radians(HERO_YAW)), math.sin(math.radians(HERO_YAW)), 0)
x, y = HERO_CAM.x + f.x*DISTANCE, HERO_CAM.y + f.y*DISTANCE
feet = unreal.Vector(x, y, ground(x, y))
# The shirt mesh faces actor +Y (as in L_ShirtWetness), so yaw = direction-to-camera - 90.
hero = labelled('Shirt_Street_Hero', unreal.load_asset(BP).generated_class(), feet,
                unreal.Rotator(roll=0, pitch=0, yaw=HERO_YAW + 180 - 90))

skin = unreal.load_asset(SKIN)
idle = unreal.load_asset(IDLE)
for mesh in hero.get_components_by_class(unreal.SkeletalMeshComponent):
    for slot in (0, 1):                                              # MI_Manny_02 / MI_Manny_01 body slots
        mesh.set_material(slot, unreal.load_asset(TROUSERS) if slot == TROUSER_SLOT else skin)
    mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    data = unreal.SingleAnimationPlayData(); data.set_editor_property('anim_to_play', idle)
    data.set_editor_property('saved_looping', True); data.set_editor_property('saved_playing', True)
    mesh.set_editor_property('animation_data', data)

# This copy should rain from the first frame of Play: the R02 controller's manual values (1/1/1).
controller = [a for a in actors.get_all_level_actors() if a.get_actor_label() == 'WeatherArtController'][0]
controller.set_editor_property('UseManualControlInPlay', True)

chest = feet + unreal.Vector(0, 0, CLOSE['target'])
cam_pos = feet - f*CLOSE['distance'] + unreal.Vector(0, 0, CLOSE['height'])
cam = labelled('Shirt_Street_Camera', unreal.CameraActor, cam_pos, look_at(cam_pos, chest))
cam.camera_component.set_editor_property('field_of_view', CLOSE['fov'])

side = unreal.Vector(-f.y, f.x, 0)              # left of the hero view
key_pos = feet - f*220 + side*180 + unreal.Vector(0, 0, 260)
rim_pos = feet + f*200 - side*160 + unreal.Vector(0, 0, 230)
# The view-following R02 rain spawns ~15 m above the camera and is too sparse to read in a close-up,
# so a second copy sits between camera and character at a higher spawn rate.
rain_pos = cam_pos + (feet - cam_pos) * CLOSE_RAIN['along']
rain = labelled('Shirt_Street_RainClose', unreal.NiagaraActor,
                unreal.Vector(rain_pos.x, rain_pos.y, CLOSE_RAIN['height']))
rain.niagara_component.set_asset(unreal.load_asset(RAIN))
rain.niagara_component.set_variable_float('SpawnRateMultiplyer', CLOSE_RAIN['rate'])

for label, pos, intensity, color in [('Shirt_Street_Key', key_pos, 70.0, unreal.LinearColor(1.0, 0.86, 0.72)),
                                     ('Shirt_Street_Rim', rim_pos, 250.0, unreal.LinearColor(0.62, 0.78, 1.0))]:
    light = labelled(label, unreal.SpotLight, pos, look_at(pos, chest))
    c = light.spot_light_component
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_intensity_units(unreal.LightUnits.CANDELAS)
    c.set_intensity(intensity); c.set_light_color(color)
    c.set_editor_property('outer_cone_angle', 28.0); c.set_editor_property('attenuation_radius', 900.0)

unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
print({'feet': str(feet), 'camera': str(cam_pos), 'hero_yaw': hero.get_actor_rotation().yaw})
