import unreal as u,json
from pathlib import Path
def run():
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    rows=[];sdf=[]
    for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
        tags=[str(t) for t in a.get_editor_property('tags')]
        components=[]
        for c in a.get_components_by_class(u.ActorComponent):
            ct=[str(t) for t in c.get_editor_property('component_tags')]
            if ct:components.append({'name':c.get_name(),'tags':ct})
            if 'SDFSource' in ct:sdf.append(c.get_path_name())
        if tags or components:rows.append({'actor':a.get_actor_label(),'tags':tags,'components':components})
        if 'SDFSource' in tags:sdf.append(a.get_path_name())
    result={'world':w.get_path_name(),'sdf_tagged':sdf,'tagged_actors':rows}
    (Path('D:/aco/unreal/Stormfall/Verification/MudSolver')/'scene_input_tags.json').write_text(json.dumps(result,indent=2))
    return {'sdf_sources':sdf,'tagged_actor_count':len(rows)}
