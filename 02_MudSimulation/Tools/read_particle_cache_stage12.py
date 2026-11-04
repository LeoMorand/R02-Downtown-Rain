import unreal as u,json
from pathlib import Path
STATE={}

def capture():
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    source=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor) if a.get_actor_label()=='NinjaLive_Mud1').get_editor_property('NinjaLiveComponent')
    cache=u.NiagaraSimCacheFunctionLibrary.create_niagara_sim_cache(w)
    params=u.NiagaraSimCacheCreateParameters();params.set_editor_property('allow_data_interface_caching',False)
    result=u.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(cache,params,source,False,0.01667)
    STATE['cache']=cache
    u._mud_study_particle_cache=cache
    return {'result':str(result),'cache':cache.get_path_name(),'doc':u.NiagaraSimCache.read_vector_attribute.__doc__}

def read():
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    cache=STATE.get('cache') or getattr(u,'_mud_study_particle_cache',None) or u.find_object(w,'NiagaraSimCache_0')
    assert cache,'Capture again before reading'
    result={'emitters':[str(n) for n in cache.get_emitter_names()],'frames':cache.get_num_frames(),'attributes':{}}
    for n in ['UnitPosition','Previous.UnitPosition','UnitVelocity','Previous.UnitVelocity']:
        values=cache.read_vector_attribute(n,'ArrayReader',0)
        result['attributes'][n]=[[v.x,v.y,v.z] for v in values]
    for n in ['BrushScale','Age']:
        result['attributes'][n]=list(cache.read_float_attribute(n,'ArrayReader',0))
    Path('D:/aco/unreal/Stormfall/Verification/MudSolver/original_particle_cache.json').write_text(json.dumps(result,indent=2))
    return result
