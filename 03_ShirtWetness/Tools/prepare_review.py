"""Set a deterministic PIE review state. Called through entryPoint=prepare, args=[state]."""
import unreal,json
from pathlib import Path

def prepare(state='rain'):
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    assert world
    for label in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.TextRenderActor):
        label.set_actor_hidden_in_game(state!='showcase')
    rows=[]
    for a in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.StormfallShirtWeatherDemo):
        a.set_editor_property('run_scenario',False)
        c=a.get_editor_property('wetness');c.set_component_tick_enabled(False)
        c.set_uniform_wetness(0)
        local_state=state
        if state=='showcase':
            local_state={'Shirt_Runtime_Rain':'rain','Shirt_Runtime_Shelter':'rain',
                         'Shirt_Runtime_Water':'water','Shirt_Runtime_Impacts':'impact'}[a.get_actor_label()]
        if local_state=='wet':c.set_uniform_wetness(1)
        if local_state=='half':c.set_uniform_wetness(.5)
        if local_state=='impact':
            p=c.get_anchor_positions()
            c.add_wet_impact(p[3],24,1)
            c.add_wet_impact(p[7],18,.8)
        if local_state=='water':
            c.set_editor_property('diffusion_rate',0)
            c.set_editor_property('rain_amount',0)
            p=c.get_anchor_positions(); low=min(v.z for v in p);high=max(v.z for v in p)
            c.set_water_contact(True,low+(high-low)*.52,1)
            c.advance_wetness(4);c.apply_to_materials()
        if local_state=='rain':
            c.set_editor_property('rain_amount',1 if a.get_actor_label()!='Shirt_Runtime_Impacts' else 0)
            c.refresh_environment();c.advance_wetness(12);c.apply_to_materials()
        rows.append({'actor':a.get_actor_label(),'wetness':list(c.get_editor_property('wetness_values')),
                     'cloth':int(c.get_editor_property('driven_cloth_count'))})
    out=Path('D:/aco/unreal/Stormfall/Verification/ShirtWetness/Production')
    (out/('review_state_'+state+'.json')).write_text(json.dumps(rows,indent=2),encoding='utf-8')
    return rows
