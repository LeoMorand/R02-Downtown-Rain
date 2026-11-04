"""Build a clean playable map using the reconstructed solver and ordinary actors."""
import unreal as u,json
from pathlib import Path
OUT=Path('D:/aco/unreal/Stormfall/Verification/MudSolver')
LEVEL='/Game/MudStudy/Maps/L_Mud_Rebuilt_Playground'
STATE={}

def comparison():
    assert u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is None
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/MudStudy/Maps/L_Mud_RealtimeCompare')
    return {'map':'L_Mud_RealtimeCompare'}

def verify_walk():
    import sys
    sys.path.insert(0,'D:/aco/unreal/Stormfall/Tools/MudStudy')
    import runtime_probe_stage9 as probe
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    player=u.GameplayStatics.get_player_pawn(w,0);assert player
    runtime=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor) if a.get_actor_label()=='Mud_Rebuilt_Runtime')
    start=u.GameplayStatics.get_time_seconds(w)
    probe.STATE.clear();probe.STATE.update(world=w,runtime=runtime,start=start,baseline=None)
    STATE.clear();STATE.update(samples=[],initial=player.get_actor_location())
    def tick(dt):
        try:
            elapsed=u.GameplayStatics.get_time_seconds(w)-start
            if 2<elapsed<3:player.add_movement_input(u.Vector(1,0,0),1,True)
            if len(STATE['samples'])<int(elapsed):
                row=probe.sample();p=player.get_actor_location();row['player_position']=[p.x,p.y,p.z]
                STATE['samples'].append(row)
            if elapsed>=9:
                u.unregister_slate_post_tick_callback(STATE['handle'])
                STATE['handle']=None
                distance=(player.get_actor_location()-STATE['initial']).length()
                report={'map':LEVEL,'player_class':player.get_class().get_path_name(),'distance_cm':distance,
                        'pass':distance>100 and all(50<s['player_position'][2]<200 for s in STATE['samples']) and any(s['input_count']>1 for s in STATE['samples']),
                        'samples':STATE['samples']}
                (OUT/'playground_walk.json').write_text(json.dumps(report,indent=2))
        except Exception as e:
            u.unregister_slate_post_tick_callback(STATE['handle']);STATE['handle']=None
            (OUT/'playground_walk.json').write_text(json.dumps({'pass':False,'error':str(e)}))
    STATE['handle']=u.register_slate_post_tick_callback(tick)
    return {'scheduled':True,'seconds':9}

def lighting():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    assert editor.get_game_world() is None
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    existing=actors.get_all_level_actors()
    atmosphere=next((a for a in existing if a.get_actor_label()=='Mud_Atmosphere'),None)
    if atmosphere is None:
        atmosphere=actors.spawn_actor_from_class(u.SkyAtmosphere,u.Vector(0,0,0))
        atmosphere.set_actor_label('Mud_Atmosphere')
    sun=next(a for a in existing if a.get_actor_label()=='Mud_Sun').get_component_by_class(u.DirectionalLightComponent)
    sun.set_editor_property('atmosphere_sun_light',True)
    sun.set_editor_property('intensity',10.0)
    sky=next(a for a in existing if a.get_actor_label()=='Mud_SkyLight').get_component_by_class(u.SkyLightComponent)
    sky.set_editor_property('real_time_capture',True)
    sky.set_editor_property('intensity',1.0)
    # Keep the area below the mud empty: PDO moves its visible depth downwards.
    old=next((a for a in actors.get_all_level_actors() if a.get_actor_label()=='Mud_SurroundingFloor'),None)
    if old:old.set_actor_label('Mud_Floor_West')
    for side,x,y,sx,sy in [('West',-2000,0,20,60),('East',2000,0,20,60),('North',0,2000,20,20),('South',0,-2000,20,20)]:
        label='Mud_Floor_'+side
        floor=next((a for a in actors.get_all_level_actors() if a.get_actor_label()==label),None)
        if floor is None:floor=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(x,y,-11))
        floor.set_actor_label(label)
        floor.set_actor_location(u.Vector(x,y,-11),False,True)
        mesh=floor.get_component_by_class(u.StaticMeshComponent)
        mesh.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
        mesh.set_world_scale3d(u.Vector(sx,sy,0.2))
        mesh.set_collision_profile_name('BlockAll')
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    return {'atmosphere':atmosphere.get_path_name(),'sun_intensity':10,'sky_capture':True}

def build():
    levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    assert editor.get_game_world() is None,'End PIE before building the playground'
    world=editor.get_editor_world()
    mode=world.get_world_settings().get_editor_property('default_game_mode')
    mode_path=mode.get_path_name() if mode else None
    pawn_class=next((a.get_class() for a in actors.get_all_level_actors() if a.get_class().get_name().startswith('ThirdPersonCharacter')),None)
    assert pawn_class,'Ordinary playable third-person actor was not found'
    assert not u.EditorAssetLibrary.does_asset_exist(LEVEL),'Refuse to overwrite an existing playground'
    assert levels.new_level(LEVEL)
    world=editor.get_editor_world()
    if mode:world.get_world_settings().set_editor_property('default_game_mode',mode)
    player=actors.spawn_actor_from_class(pawn_class,u.Vector(-500,0,110))
    player.set_actor_label('Mud_Player')
    player.set_editor_property('auto_possess_player',u.AutoReceiveInput.PLAYER0)
    runtime=actors.spawn_actor_from_class(u.load_class(None,'/Script/MudRuntime.MudRebuildActor'),u.Vector(0,0,0))
    runtime.set_actor_label('Mud_Rebuilt_Runtime')
    runtime.set_editor_property('output_resolution',2048)
    runtime.set_editor_property('track_player',True)
    runtime.set_editor_property('track_physics_bones',True)
    start=actors.spawn_actor_from_class(u.PlayerStart,u.Vector(-500,0,110),u.Rotator(yaw=0))
    start.set_actor_label('Mud_PlayerStart')
    sun=actors.spawn_actor_from_class(u.DirectionalLight,u.Vector(0,0,1000),u.Rotator(pitch=-45,yaw=-35))
    sun.set_actor_label('Mud_Sun')
    sun.get_component_by_class(u.DirectionalLightComponent).set_editor_property('intensity',3.0)
    sky=actors.spawn_actor_from_class(u.SkyLight,u.Vector(0,0,700))
    sky.set_actor_label('Mud_SkyLight')
    sky.get_component_by_class(u.SkyLightComponent).set_editor_property('intensity',0.7)
    probe=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(350,350,30))
    probe.set_actor_label('Mud_Rebuilt_InputProbe')
    mesh=probe.get_component_by_class(u.StaticMeshComponent)
    mesh.set_mobility(u.ComponentMobility.MOVABLE)
    mesh.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'))
    mesh.set_world_scale3d(u.Vector(0.5,0.5,0.5))
    mesh.set_collision_profile_name('BlockAll')
    runtime.set_editor_property('brush_actors',[probe])
    assert levels.save_current_level()
    report={'map':LEVEL,'solver':runtime.get_editor_property('solver').get_path_name(),
            'game_mode':mode_path,'source_fluid_actors':0,
            'actors':[a.get_actor_label() for a in actors.get_all_level_actors()]}
    (OUT/'playground_build.json').write_text(json.dumps(report,indent=2))
    return report


