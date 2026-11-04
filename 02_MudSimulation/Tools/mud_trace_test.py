"""Temporary PIE walking test for Phase18. No saved asset edits."""
import json,traceback
from pathlib import Path
import unreal as u
OUT=Path('D:/aco/unreal/Stormfall/Verification/MudProfessional/phase18-visible-trails')
S={}

def start(input_path,area='thin',move_away=True):
    assert not S.get('handle')
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    assert w and 'UEDPIE_' in w.get_path_name() and 'L_Mud_VisibleTrails' in w.get_path_name()
    pawn=u.GameplayStatics.get_player_pawn(w,0)
    sub=u.find_object(None,input_path);assert sub
    movement=pawn.get_component_by_class(u.CharacterMovementComponent)
    movement.stop_movement_immediately()
    pawn.set_actor_location(u.Vector(-2750 if area=='thin' else 1750,0,93 if area=='thin' else 42.2),False,True)
    pawn.set_actor_rotation(u.Rotator(),True)
    u.GameplayStatics.get_player_controller(w,0).set_control_rotation(u.Rotator())
    S.clear();S.update(world=w,pawn=pawn,input=sub,move=u.load_asset('/Game/FluidNinjaLive/Meshes/Mannequin/Input/IA_Walk'),
        start=u.GameplayStatics.get_time_seconds(w),samples=[],area=area,away=False,move_away=move_away)
    u.GameplayStatics.set_game_paused(w,False)
    S['handle']=u.register_slate_post_tick_callback(tick)

def finish(error=None):
    h=S.pop('handle',None)
    if h:u.unregister_slate_post_tick_callback(h)
    S['input'].inject_input_vector_for_action(S['move'],u.Vector(),[],[])
    u.GameplayStatics.set_game_paused(S['world'],True)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/(S['area']+'-walk.json')).write_text(json.dumps({'complete':not error,'error':error,'samples':S['samples']},indent=2))

def tick(dt):
    try:
        t=u.GameplayStatics.get_time_seconds(S['world'])-S['start']
        if t>5:finish();return
        if t<4:
            S['input'].inject_input_vector_for_action(S['move'],u.Vector(0,.5,0),[],[])
        elif not S['away']:
            S['input'].inject_input_vector_for_action(S['move'],u.Vector(),[],[])
            S['pawn'].get_component_by_class(u.CharacterMovementComponent).stop_movement_immediately()
            if S['move_away']:
                S['pawn'].set_actor_location(u.Vector(-3700,1400,94),False,True)
            else:
                u.GameplayStatics.get_player_controller(S['world'],0).set_control_rotation(u.Rotator(pitch=-20,yaw=180,roll=0))
            S['away']=True
        if not S['samples'] or t-S['samples'][-1]['seconds']>.1:
            p=S['pawn'].get_actor_location();v=S['pawn'].get_velocity()
            S['samples'].append({'seconds':t,'position':[p.x,p.y,p.z],'velocity':[v.x,v.y,v.z]})
    except Exception:finish(traceback.format_exc())
