import unreal as u
import json
from pathlib import Path

def inspect(activate=False):
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    actor=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor) if a.get_actor_label()=='NinjaLive_Mud1')
    sim=actor.get_editor_property('NinjaLiveComponent')
    pawn=u.GameplayStatics.get_player_pawn(w,0)
    if activate:pawn.set_actor_location(u.Vector(-7191.45,11187.57,-400),False,True)
    data={'world':w.get_path_name(),'pawn':str(pawn.get_actor_location())}
    for name in ['InitDone','PawnInsideActivationBounds','MI_Output','RT_VelocityDensity','PrimaryOutputMaterialSelected']:
        v=sim.get_editor_property(name);data[name]=str(v)
    data['num_materials']=sim.get_num_materials()
    data['materials']=[str(sim.get_material(i)) for i in range(data['num_materials'])]
    Path('D:/aco/unreal/Stormfall/Verification/MudRealtime/live_inspection.json').write_text(json.dumps(data,indent=2))
    return data
