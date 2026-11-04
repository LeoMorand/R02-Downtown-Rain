"""PIE-only repeatable pawn sweep. Writes telemetry, never saves source assets.

Run start via UE-MCP editor.run_python_file; a Slate callback records actual world
times. This is a controlled input trace, not a bit-identical deterministic test:
the original scene's other moving objects and random state remain active.
"""
import json
from pathlib import Path
import unreal as u

OUT=Path('D:/aco/unreal/Stormfall/Verification/MudBaseline')
STATE={}

def vec(v):return {'x':v.x,'y':v.y,'z':v.z}
def safe(obj,name):
    try:
        v=obj.get_editor_property(name)
        if isinstance(v,u.Object):return v.get_path_name()
        if isinstance(v,(bool,float,int,str)) or v is None:return v
        return str(v)
    except Exception as e:return {'error':str(e)}

def probes(world,sim):
    rt=sim.get_editor_property('RT_VelocityDensity')
    rows=[]
    # Only nine individual pixels. Avoid RawPixelArea in this engine build:
    # its MaxX/MaxY arguments are forwarded as width/height internally.
    for x,y in [(512,512),(1024,512),(1536,512),(512,1024),(1024,1024),
                (1536,1024),(512,1536),(1024,1536),(1536,1536)]:
        c=u.RenderingLibrary.read_render_target_raw_pixel(world,rt,x,y,False)
        rows.append({'x':x,'y':y,'rgba':[c.r,c.g,c.b,c.a]})
    return rows

def write():
    data={k:v for k,v in STATE.items() if k not in ['world','pawn','sim','movement','handle','old_mode','old_custom_mode']}
    (OUT/'07_controlled_sweep.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

def stop(error=None):
    if STATE.get('handle') is not None:
        u.unregister_slate_post_tick_callback(STATE.pop('handle'))
    if STATE.get('movement'):
        STATE['movement'].set_movement_mode(STATE['old_mode'],STATE['old_custom_mode'])
    STATE['complete']=error is None
    if error:STATE['error']=str(error)
    write()

def tick(delta):
    try:
        world,pawn,sim=STATE['world'],STATE['pawn'],STATE['sim']
        now=u.GameplayStatics.get_time_seconds(world)
        if now==STATE.get('last_world_time'):return
        STATE['last_world_time']=now
        t=now-STATE['start_world_time']
        start,end=STATE['start_location'],STATE['end_location']
        a=0 if t<1 else min(1,(t-1)/4) if t<7 else max(0,1-(t-7)/4)
        location=u.Vector(start['x']+(end['x']-start['x'])*a,start['y'],start['z'])
        pawn.set_actor_location(location,False,True)
        STATE['tick_count']+=1
        if t-STATE['last_sample']>=0.1:
            STATE['last_sample']=t
            STATE['samples'].append({'elapsed':t,'world_time':now,'delta':delta,
                'requested':vec(location),'actual':vec(pawn.get_actor_location()),
                'activation':safe(sim,'PawnInsideActivationBounds'),
                'tracked_positions':safe(sim,'TrackedPositions'),
                'tracked_params':safe(sim,'TrackedParams')})
        if t>=13:
            STATE['end_world_time']=now
            STATE['end_probes']=probes(world,sim)
            stop()
    except Exception as e:stop(e)

def start():
    if STATE.get('handle') is not None:raise RuntimeError('Sweep already running')
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    if not world:raise RuntimeError('Start normal PIE first')
    pawn=u.GameplayStatics.get_player_pawn(world,0)
    if not pawn:raise RuntimeError('Controlled pawn is required')
    actor=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if a.get_actor_label()=='NinjaLive_Mud1')
    sim=actor.get_editor_property('NinjaLiveComponent')
    if not sim.get_editor_property('RT_VelocityDensity'):raise RuntimeError('Activate original mud first')
    movement=pawn.get_component_by_class(u.CharacterMovementComponent)
    pos=pawn.get_actor_location()
    STATE.clear()
    STATE.update({'world':world,'pawn':pawn,'sim':sim,'movement':movement,
        'old_mode':movement.get_editor_property('movement_mode'),
        'old_custom_mode':movement.get_editor_property('custom_movement_mode'),
        'world_path':world.get_path_name(),'pawn_path':pawn.get_path_name(),
        'original_location':vec(pos),'start_location':{'x':-7491.45,'y':11187.57,'z':pos.z},
        'end_location':{'x':-6891.45,'y':11187.57,'z':pos.z},
        'schedule':'hold 1s; +X 600cm in 4s; hold 2s; -X 600cm in 4s; hold 2s',
        'duration_seconds':13,'complete':False,'tick_count':0,'samples':[],
        'last_sample':-1,'start_world_time':u.GameplayStatics.get_time_seconds(world),
        'start_probes':probes(world,sim),
        'limits':['Other demo objects continue moving','Random state not reset',
                  'No fixed timestep forced','Nine pixels are sparse samples, not a complete field']})
    movement.disable_movement()
    STATE['handle']=u.register_slate_post_tick_callback(tick)
    write()
    return {'started':True,'path':str(OUT/'07_controlled_sweep.json'),'duration_seconds':13}
