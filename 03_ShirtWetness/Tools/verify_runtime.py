"""Run during PIE in L_ShirtWetness. Tests the actual compiled Blueprint/MIDs."""
import unreal, json, math
from pathlib import Path

out = Path('D:/aco/unreal/Stormfall/Verification/ShirtWetness')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world, 'Start PIE first'
cls = unreal.load_class(None, '/Game/Stormfall/ShirtTrial/Wetness/BP_ShirtWetness.BP_ShirtWetness_C')
actors = unreal.GameplayStatics.get_all_actors_of_class(world, cls)
actor = next(a for a in actors if a.get_actor_label() == 'Shirt_AutoCycle')
comp = actor.get_component_by_class(unreal.SkeletalMeshComponent)
cloth_slots = [2, 3, 4, 5, 6, 8]
before_ids = [comp.get_material(i).get_path_name() for i in cloth_slots]

def verify(expected):
    actual = float(actor.get_editor_property('Wetness'))
    values = [float(comp.get_material(i).get_scalar_parameter_value('Wetness')) for i in cloth_slots]
    assert abs(actual-expected) < 1e-5, (actual, expected)
    assert all(abs(v-expected) < 1e-5 for v in values), values
    return {'actor':actual, 'material_values':values, 'passed':True}

clamps = []
for value, expected in [(-0.5,0), (0.25,.25), (.5,.5), (1.5,1), (1,1), (0,0)]:
    actor.call_method('SetShirtWetness', args=(value,))
    assert not actor.get_editor_property('AutoCycle')
    clamps.append({'input':value, 'expected':expected, **verify(expected)})

# Execute the actual Tick graph at deterministic phase positions, rather than
# duplicating its math in a separate implementation and testing that instead.
actor.set_editor_property('AutoCycle', True)
actor.set_editor_property('CycleSeconds', 40.0)
phases = []
previous = float(actor.get_editor_property('ElapsedSeconds'))
cycle_start = math.ceil(previous / 40.0) * 40.0
for elapsed, expected in [(0,0), (5,0), (10,.5), (15,1), (20,1), (25,1), (30,.5), (35,0), (40,0), (50,.5)]:
    target = cycle_start + elapsed
    actor.call_method('ReceiveTick', args=(target - previous,))
    previous = target
    phases.append({'cycle_elapsed':elapsed, 'expected':expected, **verify(expected)})

after_ids = [comp.get_material(i).get_path_name() for i in cloth_slots]
assert before_ids == after_ids, 'Updating wetness must reuse existing dynamic instances'
actor.call_method('SetShirtWetness', args=(0.0,))
report = {'world':world.get_path_name(), 'clamp_tests':clamps, 'cycle_phase_tests':phases,
          'dynamic_material_instances_reused':True, 'cloth_slots':cloth_slots,
          'real_tick_observed_separately':True, 'passed':True}
(out/'runtime_tests.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('SHIRT_RUNTIME_TESTS_PASSED: 6 clamp cases, 10 actual Blueprint tick phase cases; 6 cloth slots each, stable MIDs.')
