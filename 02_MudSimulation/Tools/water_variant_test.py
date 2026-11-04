"""PIE-only water interaction checks. Uses real Enhanced Input; no asset writes."""
import json,traceback
from pathlib import Path
import unreal as u
OUT=Path('D:/aco/unreal/Stormfall/Verification/MudProfessional/phase19-water')
S={}

def start(input_path,area='pool'):
    assert not S.get('handle')
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    assert world and 'UEDPIE_' in world.get_path_name() and 'L_Water_PuddleAndPool' in world.get_path_name()
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    pawn=u.GameplayStatics.get_player_pawn(world,0)
    movement=pawn.get_component_by_class(u.CharacterMovementComponent)
    movement.stop_movement_immediately()
    pawn.set_actor_location(u.Vector(1750 if area=='pool' else -2750,0,42.2 if area=='pool' else 93),False,True)
    pawn.set_actor_rotation(u.Rotator(),True)
    u.GameplayStatics.get_player_controller(world,0).set_control_rotation(u.Rotator())
    actor=actors['Mud_DeepPool' if area=='pool' else 'Mud_ThinSurface']
    S.clear();S.update(world=world,pawn=pawn,movement=movement,actor=actor,
        input=u.find_object(None,input_path),move=u.load_asset('/Game/FluidNinjaLive/Meshes/Mannequin/Input/IA_Walk'),
        start=u.GameplayStatics.get_time_seconds(world),area=area,samples=[],last=-1,last_probe=-1,probe=[])
    assert S['input']
    u.GameplayStatics.set_game_paused(world,False)
    S['handle']=u.register_slate_post_tick_callback(tick)

def finish(error=None):
    h=S.pop('handle',None)
    if h:u.unregister_slate_post_tick_callback(h)
    S['input'].inject_input_vector_for_action(S['move'],u.Vector(),[],[])
    u.GameplayStatics.set_game_paused(S['world'],True)
    mid=S['actor'].get_editor_property('surface_mid')
    rt=S['actor'].get_editor_property('output')
    n=S['actor'].get_editor_property('normal_pass').get_editor_property('normal_output')
    result={'complete':not error,'error':error,'samples':S['samples'],'height_probe':S['probe'],
        'material':mid.get_editor_property('parent').get_path_name(),'water_opacity':mid.get_scalar_parameter_value('WaterOpacity'),
        'output_size':[rt.size_x,rt.size_y],'normal_size':[n.size_x,n.size_y],
        'scope':'Actual character movement and live RT readback, not a water-physics equivalence test or performance benchmark.'}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/(S['area']+'-walk.json')).write_text(json.dumps(result,indent=2))

def tick(dt):
    try:
        t=u.GameplayStatics.get_time_seconds(S['world'])-S['start']
        if t>5:finish();return
        S['input'].inject_input_vector_for_action(S['move'],u.Vector(0,.5 if t<4 else 0,0),[],[])
        if t-S['last']>.1:
            p=S['pawn'].get_actor_location();v=S['pawn'].get_velocity()
            controls=next((c for c in S['actor'].get_components_by_class(u.ActorComponent) if c.get_name()=='ArtistControls'),None)
            S['samples'].append({'seconds':t,'position':[p.x,p.y,p.z],'velocity':[v.x,v.y,v.z],
                'falling':S['movement'].is_falling(),'leg_inputs':controls.get_editor_property('active_leg_inputs') if controls else None})
            S['last']=t
        if t-S['last_probe']>1:
            rt=S['actor'].get_editor_property('output')
            pix=u.RenderingLibrary.read_render_target_raw_pixel_area(S['world'],rt,900,992,64,64,False)
            S['probe'].append({'seconds':t,'min_b':min(p.b for p in pix),'max_b':max(p.b for p in pix),'mean_b':sum(p.b for p in pix)/len(pix)})
            S['last_probe']=t
    except Exception:finish(traceback.format_exc())
