"""Read the original vendor scene; write study evidence only in Stormfall."""
import json
from pathlib import Path
import unreal as u

OUT=Path('D:/aco/unreal/Stormfall/Verification/MudStudy')

def value(v):
    if v is None or isinstance(v,(bool,int,float,str)):return v
    if isinstance(v,u.Object):return v.get_path_name()
    try:return [value(x) for x in v]
    except TypeError:return str(v)

def read(obj,names):
    result={}
    for name in names:
        try:result[name]=value(obj.get_editor_property(name))
        except Exception:pass
    return result

def material_functions():
    function=u.load_asset('/Game/FluidNinjaLive/OutputMaterials/Base/MF_NinjaOutput_BaseFunction_SURFACE')
    rows=[]
    for kind in ['MaterialExpressionMaterialFunctionCall','MaterialExpressionCustom','MaterialExpressionComment']:
        for i in range(250):
            node=u.find_object(function,f'{kind}_{i}')
            if not node:continue
            item={'name':node.get_name(),'class':kind}
            item.update(read(node,['material_function','description','text','code']))
            rows.append(item)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'surface_function_inventory.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
    return {'functions':[r for r in rows if 'material_function' in r],'customHlslCount':sum('code' in r for r in rows)}

def audit():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    worlds=[('editor',editor.get_editor_world()),('runtime',editor.get_game_world())]
    result={}
    for mode,world in worlds:
        if not world:continue
        rows=[]
        for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
            if actor.get_actor_label() not in ['NinjaLive_Mud1','NinjaLive_Mud_Landscape']:continue
            sim=actor.get_editor_property('NinjaLiveComponent')
            fields=['Preset','InitSystemStateFromPreset','ContinouslyUpdateSystemStateFromPreset','SimSpeed',
                'VelocityFeedback','DensityAccumulation','VeloFromBrushMotion','GlobalBrushScale','VeloDirNoise',
                'ResolutionX','ResolutionY','PressureIterations','PressureSolveIterations','PressureDissipation',
                'OverlapBasedInteraction','InteractionWithOwnerActor','ComponentActivatedByPawnProximity',
                'PawnInsideActivationBounds','DisableComponent','TickBlocker','UseUnrealNativeTick','TickRateCustom',
                'ForceHideVisualizationMesh','ExtentsXYZ','Clamp','VelocityDensityBuffer','PressureDivergenceBuffer',
                'PaintBuffer','MI_Output','MI_SecondaryOutput','PrimaryOutputMaterials','SecondaryOutputMaterials',
                'InitDone','OwnerIsNinjaLiveActor','TrackedPositions','TrackedParams','OverlappingComponents',
                'DirectDriveTags','ActorTags','ComponentTags','StaticMeshTags','SkeletalMeshTags']
            row={'label':actor.get_actor_label(),'class':actor.get_class().get_path_name(),
                'location':value(actor.get_actor_location()),'rotation':value(actor.get_actor_rotation()),
                'actor':read(actor,['InteractionVolumeSize','ActivationVolumeSize']),
                'simulation':read(sim,fields),'system':value(sim.get_asset())}
            materials=sim.get_editor_property('PrimaryOutputMaterials')
            row['materials']=[]
            for mat in materials:
                if not mat:continue
                item={'path':mat.get_path_name(),'class':mat.get_class().get_name()}
                for kind in ['scalar','vector','texture','static_switch']:
                    try:
                        values=mat.get_editor_property(kind+'_parameter_values')
                        item[kind]=[{'name':str(x.get_editor_property('parameter_info').get_editor_property('name')),
                            'value':value(x.get_editor_property('parameter_value'))} for x in values]
                    except Exception:pass
                row['materials'].append(item)
            rows.append(row)
        result[mode]={'world':world.get_path_name(),'actors':rows}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'source_scene.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    return {'saved':str(OUT/'source_scene.json'),'worlds':list(result),'actors':{k:[a['label'] for a in v['actors']] for k,v in result.items()}}
