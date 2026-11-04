"""Idempotent, additive upgrade of the existing shirt graph and demonstration level.
Run in the Stormfall editor after compiling the native component. Never rebuild the old graph.
"""
import unreal, json, hashlib
from pathlib import Path

ROOT = Path('D:/aco/unreal/Stormfall')
DEST = '/Game/Stormfall/ShirtTrial/Wetness'
A = unreal.EditorAssetLibrary
L = unreal.MaterialEditingLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
master = unreal.load_asset(DEST+'/Materials/M_Shirt_ReferenceWet')
assert master
nodes = list(L.get_material_expressions(master))
by = {str(e.get_editor_property('desc')): e for e in nodes}
source = (ROOT/'Shaders/ShirtSpatialWetness.hlsl').read_text(encoding='utf-8')

def create(kind, label, x, y, **props):
    e = by.get(label)
    if e is None:
        e = L.create_material_expression(master, getattr(unreal, 'MaterialExpression'+kind), x, y)
        e.set_editor_property('desc', label)
        by[label]=e
    for k,v in props.items(): e.set_editor_property(k,v)
    return e

def wire(a,b,pin='',output=''):
    assert L.connect_material_expressions(a,output,b,pin), (str(a),str(b),pin)

def upgrade_graph():
    legacy = by['Wetness']
    mask = create('Custom','Persistent Spatial Wetness',-2900,-1300,
                  code=source,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    names = ['P','Enable','LegacyWetness']+['A'+str(i) for i in range(12)]
    ins=[]
    for name in names:
        item=unreal.CustomInput(); item.set_editor_property('input_name',name);ins.append(item)
    mask.set_editor_property('inputs',ins)
    world = create('WorldPosition','Wetness Position Without WPO',-4100,-1450)
    world.set_editor_property('world_position_shader_offset',unreal.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    local = create('TransformPosition','Wetness Mesh Local Position',-3700,-1450,
                   transform_source_type=unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
                   transform_type=unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
    wire(world,local);wire(local,mask,'P')
    enabled=create('ScalarParameter','Spatial Wetness Enable',-3700,-1600,
                   parameter_name='SpatialWetnessEnable',default_value=0,group='03 Runtime Spatial Wetness')
    wire(enabled,mask,'Enable');wire(legacy,mask,'LegacyWetness')
    for i in range(12):
        param=create('VectorParameter','Persistent Wet Anchor '+str(i),-4100,-1200+i*160,
                     parameter_name='WetAnchor'+str(i),default_value=unreal.LinearColor(0,0,0,0),
                     group='03 Runtime Spatial Wetness')
        # Vector parameter unnamed output is RGB. Custom needs RGBA, including stored wetness.
        wire(param,mask,'A'+str(i),'RGBA')
    # Bypass UV-gradient weights only in runtime mode; original reference preview stays identical.
    for label in ['Bound color wetness','Bound roughness wetness']:
        bound=by[label]
        inputs=list(bound.get_editor_property('inputs'))
        for name in ['LocalWetness','SpatialEnable']:
            if not any(str(inp.get_editor_property('input_name'))==name for inp in inputs):
                inp=unreal.CustomInput();inp.set_editor_property('input_name',name);inputs.append(inp)
        bound.set_editor_property('inputs',inputs)
        bound.set_editor_property('code','return lerp(saturate(W),saturate(LocalWetness),step(0.5,SpatialEnable));')
        wire(mask,bound,'LocalWetness');wire(enabled,bound,'SpatialEnable')

upgrade_graph()
L.set_material_usage(master,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
L.set_material_usage(master,unreal.MaterialUsage.MATUSAGE_CLOTHING)
L.recompile_material(master)
A.save_loaded_asset(master)

levels.load_level(DEST+'/L_ShirtWetness')
existing={a.get_actor_label():a for a in actors.get_all_level_actors()}
baseline=existing['Shirt_Dry']
base_mesh=baseline.get_component_by_class(unreal.SkeletalMeshComponent)
mesh=base_mesh.get_editor_property('skeletal_mesh_asset')
assert mesh
physics_mesh_path=DEST+'/Physics/SK_ShirtWeatherProxy'
physics_mesh=unreal.load_asset(physics_mesh_path)
if not physics_mesh:
    physics_mesh=A.duplicate_asset(mesh.get_path_name(),physics_mesh_path)
assert physics_mesh
assert unreal.SkeletalMeshEditorSubsystem.get_lod_count(physics_mesh)>=2, (
    'Prepare proxy with native asset(generate_skeletal_mesh_lods): lodCount=2, trianglePercentages=[8]. '
    'LOD1 is the simulation source; original LOD0 remains the render mesh.')
if not physics_mesh.get_editor_property('physics_asset'):
    body_physics=unreal.load_asset('/Game/Characters/UE5_Mannequins/Rigs/PA_Mannequin')
    if body_physics:physics_mesh.set_editor_property('physics_asset',body_physics)
cloth_result=unreal.StormfallClothTools.build_wet_shirt_hem(physics_mesh)
if cloth_result.startswith(('OK:','EXISTS:')):
    finalized=unreal.StormfallClothTools.finalize_wet_shirt_hem(physics_mesh)
    assert finalized.startswith('EXISTS:'),finalized
print('SHIRT_CLOTH_AUTHORING '+cloth_result)
if cloth_result.startswith(('OK:','EXISTS:')):
    A.save_loaded_asset(physics_mesh)
    mesh=physics_mesh
reference_pose=base_mesh.get_editor_property('animation_data')
reference_mode=base_mesh.get_editor_property('animation_mode')
weather=unreal.load_asset('/Game/MPC_RoadWeather')
anchor_records=[]

def configure_anchors(component, skeletal_component):
    arr=list(component.get_editor_property('anchors'))
    # Place paired torso cells on the front/back of the reference shirt.
    # Convert component-space offsets through the actual reference bone transforms.
    for i, anchor in enumerate(arr):
        bone=str(anchor.get_editor_property('bone'))
        if i<6:
            t=skeletal_component.get_socket_transform(bone,unreal.RelativeTransformSpace.RTS_COMPONENT)
            centre=t.translation
            # Keep paired cells 18cm apart across the Manny reference torso thickness.
            delta=unreal.Vector(0, -9 if i%2==0 else 9, 0)
            desired=centre+delta
            local=unreal.MathLibrary.inverse_transform_location(t,desired)
            anchor.set_editor_property('bone_offset',local)
        else:
            anchor.set_editor_property('bone_offset',unreal.Vector(0,0,0))
    component.set_editor_property('anchors',arr)
    return [{'bone':str(a.get_editor_property('bone')),'offset':str(a.get_editor_property('bone_offset'))} for a in arr]

demo_reports=[]
for i,(name,scenario) in enumerate([
    ('Shirt_Runtime_Rain',unreal.StormfallShirtDemo.RAIN),
    ('Shirt_Runtime_Shelter',unreal.StormfallShirtDemo.SHELTER),
    ('Shirt_Runtime_Water',unreal.StormfallShirtDemo.WATER),
    ('Shirt_Runtime_Impacts',unreal.StormfallShirtDemo.IMPACTS)]):
    actor=existing.get(name)
    if not actor:
        # Separate studio bay avoids overlapping silhouettes in front/back captures.
        loc=baseline.get_actor_location()+unreal.Vector(2200,0,0)
        loc.x += i*180
        actor=actors.spawn_actor_from_class(unreal.StormfallShirtWeatherDemo,loc,baseline.get_actor_rotation())
        actor.set_actor_label(name)
    actor.set_actor_location(unreal.Vector(1900+i*180,0,0),False,False)
    actor.set_editor_property('scenario',scenario)
    shirt=actor.get_editor_property('shirt')
    shirt.set_skeletal_mesh_asset(mesh)
    shirt.set_editor_property('forced_lod_model',1)
    shirt.set_animation_mode(reference_mode)
    shirt.set_editor_property('animation_data',reference_pose)
    shirt.set_editor_property('visibility_based_anim_tick_option',unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    component=actor.get_editor_property('wetness')
    component.set_editor_property('weather_collection',weather)
    component.set_editor_property('read_weather_collection',False)
    component.set_editor_property('initial_wetness',0)
    component.set_editor_property('drive_cloth_response',cloth_result.startswith(('OK:','EXISTS:')))
    anchor_records=configure_anchors(component,shirt)
    demo_reports.append({'actor':name,'scenario':str(scenario),'location':str(actor.get_actor_location())})

for old_camera in unreal.GameplayStatics.get_all_actors_of_class(actors.get_all_level_actors()[0].get_world(),unreal.CameraActor):
    if old_camera.get_actor_label()!='Shirt_Runtime_OverviewCamera':
        old_camera.set_editor_property('tags',['ShirtComparisonCamera'])
camera=existing.get('Shirt_Runtime_OverviewCamera')
if not camera:
    camera=actors.spawn_actor_from_class(unreal.CameraActor,unreal.Vector(2170,830,160),unreal.Rotator(pitch=-4,yaw=-90,roll=0))
    camera.set_actor_label('Shirt_Runtime_OverviewCamera')
    camera.get_component_by_class(unreal.CameraComponent).set_field_of_view(48)
camera.set_editor_property('tags',['ShirtRuntimeCamera'])
camera.set_actor_location(unreal.Vector(2170,830,160),False,False)
camera.set_actor_rotation(unreal.Rotator(pitch=-4,yaw=-90,roll=0),False)

for source_label in ['Shirt_Key','Shirt_Fill','Shirt_Rim','Shirt_StudioFloor']:
    target_label='Shirt_Runtime_'+source_label.removeprefix('Shirt_')
    if target_label not in existing:
        duplicate=actors.duplicate_actor(existing[source_label],offset=unreal.Vector(2200,0,0))
        duplicate.set_actor_label(target_label)

for i,caption in enumerate(['RAIN / ABSORPTION','CANOPY / SHELTER','WATER / HISTORY','IMPACT / SPREAD']):
    label='Shirt_Runtime_Label_'+str(i)
    text=existing.get(label)
    if not text:
        text=actors.spawn_actor_from_class(unreal.TextRenderActor,unreal.Vector(1900+i*180,0,210),unreal.Rotator(pitch=0,yaw=90,roll=0))
        text.set_actor_label(label)
    render=text.get_component_by_class(unreal.TextRenderComponent)
    text.set_actor_location(unreal.Vector(1900+i*180,0,210),False,False)
    text.set_actor_rotation(unreal.Rotator(pitch=0,yaw=90,roll=0),False)
    render.set_text(caption);render.set_world_size(9)
    render.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)

hint=existing.get('Shirt_Runtime_Controls')
if not hint:
    hint=actors.spawn_actor_from_class(unreal.TextRenderActor,unreal.Vector(2170,0,260),unreal.Rotator(pitch=0,yaw=90,roll=0))
    hint.set_actor_label('Shirt_Runtime_Controls')
hint.get_component_by_class(unreal.TextRenderComponent).set_text('PLAY: 1 COMPARE / 2 WEATHER   |   48s LOOP')
hint.set_actor_location(unreal.Vector(2170,0,260),False,False)
hint.set_actor_rotation(unreal.Rotator(pitch=0,yaw=90,roll=0),False)
hint.get_component_by_class(unreal.TextRenderComponent).set_world_size(12)
hint.get_component_by_class(unreal.TextRenderComponent).set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)

sheltered=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='Shirt_Runtime_Shelter')
canopy=existing.get('Shirt_Runtime_Canopy')
if not canopy:
    canopy=actors.spawn_actor_from_class(unreal.StaticMeshActor,sheltered.get_actor_location()+unreal.Vector(0,0,235))
    canopy.set_actor_label('Shirt_Runtime_Canopy')
    sm=canopy.get_component_by_class(unreal.StaticMeshComponent)
    sm.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    canopy.set_actor_scale3d(unreal.Vector(1.5,1.4,.08))
    sm.set_collision_profile_name('BlockAll')
canopy.set_actor_location(sheltered.get_actor_location()+unreal.Vector(0,0,235),False,False)

# Standalone reusable Blueprint wrapper: no Python or bridge dependency at runtime.
bp_path=DEST+'/BP_ShirtWeatherRuntime'
runtime_bp=unreal.load_asset(bp_path)
if not runtime_bp:
    factory=unreal.BlueprintFactory()
    factory.set_editor_property('parent_class',unreal.StormfallShirtWeatherDemo)
    runtime_bp=unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_ShirtWeatherRuntime',DEST,unreal.Blueprint,factory)
    cdo=unreal.get_default_object(runtime_bp.generated_class())
    cdo.set_editor_property('run_scenario',False)
    cdo.get_editor_property('shirt').set_skeletal_mesh_asset(mesh)
    cdo.get_editor_property('shirt').set_editor_property('animation_data',reference_pose)
    cdo.get_editor_property('shirt').set_animation_mode(reference_mode)
    c=cdo.get_editor_property('wetness')
    c.set_editor_property('weather_collection',weather)
    c.set_editor_property('read_weather_collection',True)
    c.set_editor_property('rain_absorption_seconds',18)
    c.set_editor_property('drying_seconds',90)
    c.set_editor_property('drive_cloth_response',cloth_result.startswith(('OK:','EXISTS:')))
    configure_anchors(c,cdo.get_editor_property('shirt'))
    unreal.BlueprintEditorLibrary.compile_blueprint(runtime_bp)
    A.save_loaded_asset(runtime_bp)

# Keep an already-created wrapper on the optimized physics mesh without resetting artist controls.
runtime_defaults=unreal.get_default_object(runtime_bp.generated_class())
runtime_defaults.get_editor_property('shirt').set_skeletal_mesh_asset(mesh)
runtime_defaults.get_editor_property('shirt').set_editor_property('forced_lod_model',1)
unreal.BlueprintEditorLibrary.compile_blueprint(runtime_bp)
A.save_loaded_asset(runtime_bp)

levels.save_current_level()
stats=L.get_statistics(master)
report={'material':master.get_path_name(),'hlsl_sha256':hashlib.sha256(source.encode()).hexdigest(),
        'anchors':anchor_records,'demos':demo_reports,'runtime_blueprint':bp_path,
        'statistics':str(stats),'expression_count':len(L.get_material_expressions(master)),
        'cloth_result':cloth_result,
        'cloth_assets':[str(a) for a in mesh.get_editor_property('mesh_clothing_assets')],
        'physics_asset':str(mesh.get_editor_property('physics_asset'))}
out=ROOT/'Verification/ShirtWetness/Production';out.mkdir(parents=True,exist_ok=True)
(out/'upgrade.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SHIRT_PRODUCTION_UPGRADE '+json.dumps(report))
