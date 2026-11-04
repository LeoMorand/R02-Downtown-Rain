"""Read actual GPU-bound inputs from original and reconstructed runtime instances."""
import unreal as u,json
from pathlib import Path
OUT=Path('D:/aco/unreal/Stormfall/Verification/MudSolver')

def noise_textures():
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    source=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor) if a.get_actor_label()=='NinjaLive_Mud1').get_editor_property('NinjaLiveComponent')
    own=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor) if a.get_actor_label()=='Mud_Rebuilt_Runtime').get_editor_property('simulation')
    data=json.loads(u.MudAuthoringLibrary.inspect_gpu_inputs(own,'Amplitude'))
    for row in data.get('values',[]):
        if row.get('object'):
            obj=u.find_object(None,row['object'])
            row['texture']=str(obj.get_editor_property('Texture'))
    return {'source':{name:str(source.get_editor_property(name.replace('User.',''))) for name in ['User.VeloAmplitudeNoiseTexture','User.DensityNoiseTexture']},'own':data}

def grid_packing():
    raise RuntimeError('Disabled: this UE query crashed on internal/reference grid instances; use authored attribute metadata')
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    results=[]
    for actor in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
        if actor.get_actor_label() not in ['NinjaLive_Mud1','Mud_Rebuilt_Runtime']:continue
        comp=actor.get_editor_property('NinjaLiveComponent') if actor.get_actor_label()=='NinjaLive_Mud1' else actor.get_editor_property('simulation')
        data=json.loads(u.MudAuthoringLibrary.inspect_gpu_inputs(comp,''))
        for row in data.get('values',[]):
            if row.get('type')!='NiagaraDataInterfaceGrid2DCollection':continue
            obj=u.find_object(None,row['object'])
            results.append({'actor':actor.get_actor_label(),'name':row['name'],'size':str(obj.get_texture_size(comp)),
                            'raw':str(obj.get_raw_texture_size(comp))})
    (OUT/'grid_packing.json').write_text(json.dumps(results,indent=2))
    return results

def stage_bindings():
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    results=[]
    for actor in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
        if actor.get_actor_label() not in ['NinjaLive_Mud1','Mud_Rebuilt_Runtime']:continue
        comp=actor.get_editor_property('NinjaLiveComponent') if actor.get_actor_label()=='NinjaLive_Mud1' else actor.get_editor_property('simulation')
        data=json.loads(u.MudAuthoringLibrary.inspect_gpu_inputs(comp,''))
        results.append({'actor':actor.get_actor_label(),'bindings':[v for v in data.get('values',[]) if v.get('source')=='RendererBoundVariables']})
    (OUT/'runtime_stage_bindings.json').write_text(json.dumps(results,indent=2))
    return results

def precise_transforms():
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    source=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor) if a.get_actor_label()=='NinjaLive_Mud1').get_editor_property('NinjaLiveComponent')
    data=json.loads(u.MudAuthoringLibrary.inspect_gpu_inputs(source,''))
    rows=[v for v in data.get('values',[]) if v.get('float32') and not v['name'].startswith('PREV') and any(s in v['name'] for s in ['WorldToUnit','UnitToWorld','SimPosDouble'])]
    (OUT/'precise_runtime_transforms.json').write_text(json.dumps(rows,indent=2))
    return rows

def activate_original():
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    pawn=u.GameplayStatics.get_player_pawn(w,0);assert pawn
    pawn.set_actor_location(u.Vector(-7191.45,11187.57,-400),False,True)
    return {'pawn':pawn.get_path_name(),'inspector_available':hasattr(u.MudAuthoringLibrary,'inspect_gpu_inputs')}

def inspect():
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    rows=[]
    for actor in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
        if actor.get_actor_label() not in ['NinjaLive_Mud1','Mud_Rebuilt_Runtime']:continue
        for comp in actor.get_components_by_class(u.NiagaraComponent):
            result=json.loads(u.MudAuthoringLibrary.inspect_gpu_inputs(comp,''))
            rows.append({'actor':actor.get_actor_label(),'component':comp.get_path_name(),'inspection':result})
            if result.get('success'):
                suffix='original' if actor.get_actor_label()=='NinjaLive_Mud1' else 'rebuilt'
                (OUT/('runtime_gpu_inputs_'+suffix+'.json')).write_text(json.dumps(rows[-1],indent=2))
    (OUT/'runtime_gpu_inputs.json').write_text(json.dumps(rows,indent=2))
    return [{'actor':r['actor'],'component':r['component'],'success':r['inspection'].get('success'),
        'parameters':len(r['inspection'].get('values',[])),
        'grids':[v for v in r['inspection'].get('values',[]) if 'cellsX' in v],
        'world':[v for v in r['inspection'].get('values',[]) if any(s in v['name'] for s in ['WorldOffset','WorldGridExtents','KernelIndex','KernelMult'])]} for r in rows]


