"""Read-only diagnosis of runtime pose, cloth, and material bindings."""
import unreal,json
from pathlib import Path
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
result=[]
for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.StormfallShirtWeatherDemo):
    mesh=a.get_editor_property('shirt');c=a.get_editor_property('wetness')
    asset=mesh.get_editor_property('skeletal_mesh_asset')
    info={'actor':a.get_actor_label(),'mesh':asset.get_path_name(),
          'bindings':c.get_editor_property('binding_status'),'driven':c.get_editor_property('driven_cloth_count'),
          'simulation_methods':[x for x in dir(mesh) if 'cloth' in x.lower()],
          'cloth_assets':[]}
    for prop in ['disable_cloth_simulation','clothing_simulation_factory','clothing_simulation_factory_class','component_tick','visibility_based_anim_tick_option']:
        try:info[prop]=str(mesh.get_editor_property(prop))
        except Exception:pass
    for cloth in asset.get_editor_property('mesh_clothing_assets'):
        cl={'name':cloth.get_name(),'config':str(cloth.get_editor_property('cloth_configs'))}
        try:
            interactor=mesh.get_clothing_simulation_interactor(cloth.get_name())
            cl['interactor']=str(interactor)
            if interactor:
                cl['cloth_interactor']=str(interactor.get_clothing_interactor(cloth.get_name()))
                for fn in ['get_num_cloths','get_num_kinematic_particles','get_num_dynamic_particles','get_simulation_time']:
                    try:cl[fn]=getattr(interactor,fn)()
                    except Exception:pass
        except Exception as e:cl['error']=str(e)
        info['cloth_assets'].append(cl)
    result.append(info)
Path('D:/aco/unreal/Stormfall/Verification/ShirtWetness/Production/cloth_runtime.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
