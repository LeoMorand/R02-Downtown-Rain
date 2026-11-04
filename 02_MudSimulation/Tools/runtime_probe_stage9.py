"""Exercise the permanent runtime controller with an actual moving mesh actor."""
import unreal as u,json,math
from pathlib import Path
OUT=Path('D:/aco/unreal/Stormfall/Verification/MudSolver')
STATE={}

def setup():
    levels=u.get_editor_subsystem(u.LevelEditorSubsystem);sub=u.get_editor_subsystem(u.EditorActorSubsystem)
    runtime=next(a for a in sub.get_all_level_actors() if a.get_actor_label()=='Mud_Rebuilt_Runtime')
    actor=next((a for a in sub.get_all_level_actors() if a.get_actor_label()=='Mud_Rebuilt_InputProbe'),None)
    if actor is None:actor=sub.spawn_actor_from_class(u.StaticMeshActor,u.Vector(-4000,15000,-470))
    actor.set_actor_label('Mud_Rebuilt_InputProbe')
    comp=actor.get_component_by_class(u.StaticMeshComponent);comp.set_mobility(u.ComponentMobility.MOVABLE)
    comp.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'))
    comp.set_world_scale3d(u.Vector(0.5,0.5,0.5));comp.set_collision_profile_name('BlockAll')
    runtime.set_editor_property('brush_actors',[actor]);runtime.set_editor_property('track_player',True)
    assert levels.save_current_level()
    return {'runtime':runtime.get_path_name(),'input':actor.get_path_name()}

def sample():
    w=STATE['world'];runtime=STATE['runtime'];rt=runtime.get_editor_property('output')
    probe=u.load_asset('/Game/MudStudy/Rebuild/Materials/M_LiveRT_Probe');assert probe
    if 'mid' not in STATE:
        STATE['mid']=u.MaterialLibrary.create_dynamic_material_instance(w,probe)
        STATE['small']=u.RenderingLibrary.create_render_target2d(w,64,64,u.TextureRenderTargetFormat.RTF_RGBA32F,u.LinearColor(0,0,0,0),False,False)
    STATE['mid'].set_texture_parameter_value('Buffer',rt)
    u.RenderingLibrary.draw_material_to_render_target(w,STATE['small'],STATE['mid'])
    pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(w,STATE['small'],0,0,64,64,False)
    values=[[p.r,p.g,p.b] for p in pixels]
    comp=runtime.get_editor_property('simulation')
    positions=u.NiagaraDataInterfaceArrayFunctionLibrary.get_niagara_array_vector4(comp,'User.BrushPositions')
    velocities=u.NiagaraDataInterfaceArrayFunctionLibrary.get_niagara_array_vector4(comp,'User.BrushVelocities')
    raw=u.NiagaraDataInterfaceArrayFunctionLibrary.get_niagara_array_vector4(comp,'User.BrushWorldPositions')
    result={'raw_world_inputs':[[p.x,p.y,p.z,p.w] for p in raw],'component_active':comp.is_active(),'component_tick':comp.is_component_tick_enabled(),'time':u.GameplayStatics.get_time_seconds(w)-STATE['start'],
        'finite':all(math.isfinite(v) for p in values for v in p),
        'input_count':len(positions),'positions':[[p.x,p.y,p.z,p.w] for p in positions],
        'velocities':[[p.x,p.y,p.z,p.w] for p in velocities],
        'min_rgb':[min(p[k] for p in values) for k in range(3)],'max_rgb':[max(p[k] for p in values) for k in range(3)]}
    if STATE['baseline'] is None:STATE['baseline']=values
    differences=[max(abs(x-y) for x,y in zip(a,b)) for a,b in zip(values,STATE['baseline'])]
    result['changed_samples']=sum(v>1e-4 for v in differences);result['max_delta']=max(differences)
    return result

def start():
    assert not STATE.get('handle')
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    actors=u.GameplayStatics.get_all_actors_of_class(w,u.Actor)
    runtime=next(a for a in actors if a.get_actor_label()=='Mud_Rebuilt_Runtime')
    actor=next(a for a in actors if a.get_actor_label()=='Mud_Rebuilt_InputProbe')
    actor.set_actor_location(u.Vector(-4000,15000,-470),False,True)
    STATE.clear();STATE.update(world=w,runtime=runtime,actor=actor,start=u.GameplayStatics.get_time_seconds(w),baseline=None,samples=[],next=1)
    def tick(dt):
        try:
            elapsed=u.GameplayStatics.get_time_seconds(w)-STATE['start']
            distance=max(0,min(1,(elapsed-2)/3))*1000
            actor.set_actor_location(u.Vector(-4000+distance,15000,-470),False,True)
            if elapsed>=STATE['next']:
                STATE['samples'].append(sample());STATE['next']+=1
            if elapsed>=9:
                u.unregister_slate_post_tick_callback(STATE['handle']);STATE['handle']=None
                rows=STATE['samples'];result={'scope':'Permanent C++ input controller -> authored Niagara -> RT -> material',
                    'pass':all(r['finite'] for r in rows) and any(r['input_count']>0 and r['max_delta']>1e-3 for r in rows),
                    'resolution':runtime.get_editor_property('output_resolution'),'samples':rows}
                (OUT/'runtime_probe_verification.json').write_text(json.dumps(result,indent=2))
        except Exception as e:
            u.unregister_slate_post_tick_callback(STATE['handle']);STATE['handle']=None
            (OUT/'runtime_probe_verification.json').write_text(json.dumps({'pass':False,'error':str(e)}))
    STATE['handle']=u.register_slate_post_tick_callback(tick)
    return {'scheduled':True,'seconds':9}

