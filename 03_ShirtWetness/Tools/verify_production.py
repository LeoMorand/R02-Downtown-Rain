"""PIE integration assertions. Changes only runtime actors; stop PIE to reset scenarios."""
import unreal, json, math
from pathlib import Path

ROOT=Path('D:/aco/unreal/Stormfall')
OUT=ROOT/'Verification/ShirtWetness/Production'
OUT.mkdir(parents=True,exist_ok=True)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world and 'L_ShirtWetness' in world.get_path_name(), 'Start PIE in the shirt level'
actors=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.StormfallShirtWeatherDemo)
assert len(actors)==4, len(actors)
by={a.get_actor_label():a for a in actors}
rows=[]
for a in actors:
    a.set_editor_property('run_scenario',False)
    c=a.get_editor_property('wetness');mesh=a.get_editor_property('shirt')
    assert mesh.is_visible(), 'Cloth warmup must complete and reveal the garment'
    assert c.get_editor_property('material_count')==6,c.get_editor_property('binding_status')
    assert c.get_editor_property('driven_cloth_count')==2, 'Both front/back Chaos interactors must be live'
    row={'actor':a.get_actor_label(),'initial_average':float(c.get_editor_property('average_wetness')),
         'initial_exposure':float(c.get_editor_property('rain_exposure')),
         'driven_cloth_count':int(c.get_editor_property('driven_cloth_count')),
         'slots':[]}
    for i in [2,3,4,5,6,8]:
        mid=mesh.get_material(i)
        assert isinstance(mid,unreal.MaterialInstanceDynamic)
        assert abs(mid.get_scalar_parameter_value('SpatialWetnessEnable')-1)<1e-5
        row['slots'].append(mid.get_path_name())
    rows.append(row)

rain=by['Shirt_Runtime_Rain'].get_editor_property('wetness')
shelter=by['Shirt_Runtime_Shelter'].get_editor_property('wetness')
for c in [rain,shelter]:
    c.set_uniform_wetness(0)
    c.set_editor_property('rain_amount',1)
    c.set_editor_property('diffusion_rate',0)
    c.refresh_environment();c.advance_wetness(12);c.apply_to_materials()
assert rain.get_editor_property('rain_exposure')>.99
assert shelter.get_editor_property('rain_exposure')<.01
assert rain.get_editor_property('average_wetness')>.8
assert shelter.get_editor_property('average_wetness')<.001
shelter.set_uniform_wetness(.7);shelter.advance_wetness(1);shelter.apply_to_materials()
assert .5<shelter.get_editor_property('average_wetness')<.7
checks={'rain_absorbs':True,'actual_canopy_shelters':True,'shelter_preserves_history':True}

water=by['Shirt_Runtime_Water'].get_editor_property('wetness')
water.set_editor_property('rain_amount',0);water.set_editor_property('diffusion_rate',0)
water.set_uniform_wetness(0)
positions=water.get_anchor_positions()
low=min(p.z for p in positions);high=max(p.z for p in positions)
water.set_water_contact(True,(low+high)/2,1)
water.advance_wetness(3);water.apply_to_materials()
values=list(water.get_editor_property('wetness_values'))
assert max(values)>.8 and min(values)<.001,values
checks['partial_immersion']=values
before=float(water.get_editor_property('average_wetness'))
water.set_water_contact(False,0,0);water.advance_wetness(1);water.apply_to_materials()
assert 0<water.get_editor_property('average_wetness')<before
checks['water_exit_keeps_history']=True

impact_actor=by['Shirt_Runtime_Impacts'];impact=impact_actor.get_editor_property('wetness')
impact.set_editor_property('diffusion_rate',0);impact.set_uniform_wetness(0)
points=impact.get_anchor_positions()
impact.add_wet_impact(points[8],5,.8)
values=list(impact.get_editor_property('wetness_values'))
assert values[8]>.79 and values[11]<.001,values
checks['localized_impact']=values
snapshot=impact.capture_wetness();impact.set_uniform_wetness(0)
assert impact.restore_wetness(snapshot)
assert abs(impact.get_editor_property('wetness_values')[8]-.8)<1e-5
checks['snapshot_restore']=True

# Translation must not leave wetness behind in the level or introduce large world-coordinate error.
mesh=impact_actor.get_editor_property('shirt')
mid=mesh.get_material(2)
v0=mid.get_vector_parameter_value('WetAnchor8')
location=impact_actor.get_actor_location()
impact_actor.set_actor_location(location+unreal.Vector(10000,-20000,5000),False,False)
impact.apply_to_materials()
v1=mid.get_vector_parameter_value('WetAnchor8')
assert max(abs(getattr(v0,k)-getattr(v1,k)) for k in ['r','g','b','a'])<.02,(v0,v1)
impact_actor.set_actor_location(location,False,False);impact.apply_to_materials()
checks['component_space_follows_character']=True

before_ids=[mesh.get_material(i).get_path_name() for i in [2,3,4,5,6,8]]
for _ in range(120):impact.apply_to_materials()
assert before_ids==[mesh.get_material(i).get_path_name() for i in [2,3,4,5,6,8]]
checks['mid_reuse_120_updates']=True

# Verify the actual global weather collection contract, restoring every modified value.
collection=unreal.load_asset('/Game/MPC_RoadWeather')
parameters=['RainAmount','Humidity','ManualMode','ManualRain']
saved={p:unreal.MaterialLibrary.get_scalar_parameter_value(world,collection,p) for p in parameters}
try:
    rain.set_editor_property('read_weather_collection',True)
    for p,v in [('RainAmount',.25),('Humidity',.65),('ManualMode',0),('ManualRain',.9)]:
        unreal.MaterialLibrary.set_scalar_parameter_value(world,collection,p,v)
    rain.refresh_environment()
    assert abs(rain.get_editor_property('rain_amount')-.25)<1e-5
    assert abs(rain.get_editor_property('air_humidity')-.65)<1e-5
    unreal.MaterialLibrary.set_scalar_parameter_value(world,collection,'ManualMode',1)
    rain.refresh_environment()
    assert abs(rain.get_editor_property('rain_amount')-.9)<1e-5
    checks['mpc_automatic_and_manual_rain']=True
finally:
    for p,v in saved.items():unreal.MaterialLibrary.set_scalar_parameter_value(world,collection,p,v)
    rain.set_editor_property('read_weather_collection',False)

report={'passed':True,'world':world.get_path_name(),'actors':rows,'checks':checks}
(OUT/'runtime.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SHIRT_PRODUCTION_RUNTIME_PASSED '+json.dumps(report))
