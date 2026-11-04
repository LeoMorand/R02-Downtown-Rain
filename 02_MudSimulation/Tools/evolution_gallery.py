"""Preserved stage assets + explicitly reconstructed comparison exhibit.

Creates only /Game/MudStudy/Evolution and L_Mud_EvolutionCompare.
The live vendor actor comes from a COPY of the existing owned comparison map.
"""
import unreal as u,json
from pathlib import Path
ROOT='/Game/MudStudy/Evolution'
MAP='/Game/MudStudy/Maps/L_Mud_EvolutionCompare'
OLD='/Game/MudStudy/Rebuild'
OUT=Path('D:/aco/unreal/Stormfall/Verification/MudEvolution')

def duplicate(src,dst):
    assert dst.startswith(ROOT+'/')
    asset=u.load_asset(dst)
    if asset:return asset
    asset=u.EditorAssetLibrary.duplicate_asset(src,dst)
    assert asset,(src,dst)
    return asset

def inspect():
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    actors=u.GameplayStatics.get_all_actors_of_class(w,u.Actor)
    source=next(a for a in actors if a.get_actor_label()=='Evolution_06_OriginalSolver_RebuiltSurface')
    comp=source.get_editor_property('NinjaLiveComponent')
    data={'source_actor':str(source.get_actor_location()),'source_component':str(comp.get_world_location()),
          'pawn':str(u.GameplayStatics.get_player_pawn(w,0).get_actor_location()),'active':comp.is_active(),'properties':{},'meshes':[]}
    for name in ['InitDone','ComponentActivatedByPawnProximity','ShowOutputMaterials','ForceHideVisualizationMesh','MI_Output','RT_VelocityDensity','TraceMesh']:
        try:data['properties'][name]=str(comp.get_editor_property(name))
        except Exception:pass
    for c in source.get_components_by_class(u.StaticMeshComponent):
        data['meshes'].append({'name':c.get_name(),'position':str(c.get_world_location()),'visible':c.is_visible(),'material':str(c.get_material(0))})
    own=next(a for a in actors if a.get_actor_label()=='Evolution_07_IndependentSolver')
    data['own_solver']=own.get_editor_property('solver').get_path_name()
    data['own_output']=str(own.get_editor_property('output'))
    plane=next(a for a in actors if a.get_actor_label()=='Evolution_06_Display')
    material=plane.get_component_by_class(u.StaticMeshComponent).get_material(0)
    rt=comp.get_editor_property('RT_VelocityDensity')
    data['source_display_material']=str(material)
    data['source_live_binding']=isinstance(material,u.MaterialInstanceDynamic) and material.get_texture_parameter_value('VelocityDensityBuffer')==rt
    own_mid=own.get_editor_property('surface_mid')
    data['own_live_binding']=bool(own_mid) and own_mid.get_texture_parameter_value('VelocityDensityBuffer')==own.get_editor_property('output')
    p=u.GameplayStatics.get_player_pawn(w,0).get_actor_location()
    data['player_on_surface']=50<p.z<200
    data['pass']=data['source_live_binding'] and data['own_live_binding'] and data['player_on_surface']
    (OUT/'runtime.json').write_text(json.dumps(data,indent=2));return data

def finish_layout():
    assert u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is None
    sub=u.get_editor_subsystem(u.EditorActorSubsystem)
    text_material=u.load_asset(ROOT+'/Materials/M_EvolutionText')
    if text_material is None:
        text_material=u.AssetToolsHelpers.get_asset_tools().create_asset('M_EvolutionText',ROOT+'/Materials',u.Material,u.MaterialFactoryNew())
        text_material.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
        text_material.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
        text_material.set_editor_property('two_sided',True)
        glyph=u.MaterialEditingLibrary.create_material_expression(text_material,u.MaterialExpressionFontSampleParameter,-400,100)
        glyph.set_editor_property('font',u.load_asset('/Engine/EngineFonts/RobotoDistanceField'))
        glyph.set_editor_property('parameter_name','Font')
        color=u.MaterialEditingLibrary.create_material_expression(text_material,u.MaterialExpressionVertexColor,-400,-100)
        assert u.MaterialEditingLibrary.connect_material_property(glyph,'R',u.MaterialProperty.MP_OPACITY_MASK)
        assert u.MaterialEditingLibrary.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
        u.MaterialEditingLibrary.recompile_material(text_material)
    glyph=u.find_object(text_material,'MaterialExpressionFontSampleParameter_0')
    assert glyph
    mask=u.find_object(text_material,'MaterialExpressionLinearInterpolate_0')
    if mask is None:mask=u.MaterialEditingLibrary.create_material_expression(text_material,u.MaterialExpressionLinearInterpolate,-100,100)
    # Match Engine DefaultTextMaterialOpaque's distance-field contrast.
    mask.set_editor_property('const_a',-90.0);mask.set_editor_property('const_b',90.0)
    assert u.MaterialEditingLibrary.connect_material_expressions(glyph,'R',mask,'Alpha')
    assert u.MaterialEditingLibrary.connect_material_property(mask,'',u.MaterialProperty.MP_OPACITY_MASK)
    u.MaterialEditingLibrary.recompile_material(text_material)
    board_material=u.load_asset(ROOT+'/Materials/M_ExhibitLabelBoard')
    if board_material is None:
        board_material=u.AssetToolsHelpers.get_asset_tools().create_asset('M_ExhibitLabelBoard',ROOT+'/Materials',u.Material,u.MaterialFactoryNew())
        board_material.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
        board_material.set_editor_property('two_sided',True)
        color=u.MaterialEditingLibrary.create_material_expression(board_material,u.MaterialExpressionConstant3Vector)
        color.set_editor_property('constant',u.LinearColor(0.003,0.003,0.003,1))
        assert u.MaterialEditingLibrary.connect_material_property(color,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
        u.MaterialEditingLibrary.recompile_material(board_material)
    actors=list(sub.get_all_level_actors())
    source=next(a for a in actors if a.get_actor_label()=='Evolution_06_OriginalSolver_RebuiltSurface')
    plane=next((a for a in actors if a.get_actor_label()=='Evolution_06_Display'),None)
    if plane is None:plane=sub.spawn_actor_from_class(u.StaticMeshActor,u.Vector(1500,2000,0))
    source.set_actor_location(u.Vector(1500,2000,0),False,True)
    plane.set_actor_location(u.Vector(1500,2000,0),False,True)
    own=next(a for a in actors if a.get_actor_label()=='Evolution_07_IndependentSolver')
    own.set_actor_location(u.Vector(-1500,2000,0),False,True)
    own.get_editor_property('surface').set_material(0,u.load_asset(ROOT+'/Materials/MI_Surface_Rebuilt'))
    player=next(a for a in actors if a.get_actor_label()=='Evolution_Player')
    player.set_actor_location(u.Vector(1500,1500,110),False,True)
    plane.set_actor_label('Evolution_06_Display');plane.set_folder_path('06_Live_OriginalSolver')
    plane.set_editor_property('tags',['EvolutionOutput06'])
    mesh=plane.get_component_by_class(u.StaticMeshComponent);mesh.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'))
    mesh.set_world_scale3d(u.Vector(20,20,1));mesh.set_collision_profile_name('BlockAll')
    mesh.set_material(0,u.load_asset(ROOT+'/Materials/MI_Surface_Rebuilt'))
    comp=source.get_editor_property('NinjaLiveComponent')
    comp.set_editor_property('Apply1stOutMatToActorsWithTag','EvolutionOutput06')
    comp.set_editor_property('RecollectOutputMaterialTargetsDuringGameTime',True)
    for a in sub.get_all_level_actors():
        if isinstance(a,u.TextRenderActor):
            a.set_actor_rotation(u.Rotator(yaw=-90),False)
            c=a.get_component_by_class(u.TextRenderComponent)
            c.set_text_material(text_material)
            c.set_cast_shadow(False)
            c.set_text(u.Text(str(c.get_editor_property('text')).replace('\n','<br>')))
            c.set_text_render_color(u.Color(255,255,255,255))
            c.set_world_size(40 if a.get_actor_label().startswith('Label_') else 55)
        label=a.get_actor_label()
        for i in range(1,6):
            if label.startswith('Evolution_0'+str(i)+'_') or label=='Label_'+str(i):
                p=a.get_actor_location();a.set_actor_location(u.Vector((3-i)*900,p.y,p.z),False,True)
        if label=='Label_06':a.set_actor_location(u.Vector(1500,850,100),False,True)
        if label=='Label_07':a.set_actor_location(u.Vector(-1500,850,100),False,True)
    for text_actor in list(sub.get_all_level_actors()):
        if not isinstance(text_actor,u.TextRenderActor) or not text_actor.get_actor_label().startswith('Label_'):continue
        label='Board_'+text_actor.get_actor_label();p=text_actor.get_actor_location()
        board=next((a for a in sub.get_all_level_actors() if a.get_actor_label()==label),None)
        if board is None:board=sub.spawn_actor_from_class(u.StaticMeshActor,u.Vector(p.x,p.y+5,p.z+50),u.Rotator(roll=90))
        board.set_actor_label(label);board.set_folder_path('00_ExhibitLabels')
        c=board.get_component_by_class(u.StaticMeshComponent);c.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'))
        c.set_world_scale3d(u.Vector(12 if text_actor.get_actor_label() in ['Label_06','Label_07'] else 7,1.7,1))
        c.set_material(0,board_material);c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);c.set_cast_shadow(False)
    assert u.EditorAssetLibrary.save_directory(ROOT,False,True)
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    return {'source_display':plane.get_path_name(),'binding':'vendor tagged output material binding','saved':True}

def snapshots():
    materials={}
    for name in ['M_Rebuild_UV','M_Rebuild_DensityB','M_Rebuild_DensityNormal','M_POM_Rebuilt','M_Surface_Rebuilt']:
        materials[name]=duplicate(OLD+'/Materials/'+name,ROOT+'/Materials/'+name)
    instances={}
    for name,parent in [('MI_POM_Rebuilt','M_POM_Rebuilt'),('MI_Surface_Rebuilt','M_Surface_Rebuilt')]:
        mi=duplicate(OLD+'/Materials/'+name,ROOT+'/Materials/'+name)
        u.MaterialEditingLibrary.set_material_instance_parent(mi,materials[parent])
        u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi,'ForceLocalSpace',1)
        u.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mi,'VelocityDensityBuffer',u.load_asset(OLD+'/Textures/T_SourceVelocityDensity_20261025'))
        u.MaterialEditingLibrary.update_material_instance(mi)
        instances[name]=mi
    scripts={}
    for name in ['GridInit','GridProof','Tracking','Sdf','Painter','PainterTexture','Composite','Advection','Divergence','PressureHorizontal','PressureVertical','GridExport']:
        scripts['NM_'+name]=duplicate(OLD+'/Niagara/NM_'+name,ROOT+'/Niagara/NM_'+name)
    system=duplicate(OLD+'/Niagara/NS_Mud_FromScratch',ROOT+'/Niagara/NS_Evolution_Current')
    graph=u.find_object(u.find_object(u.find_object(system,'NE_Mud_FromScratch'),'NiagaraScriptSource_0'),'NiagaraGraph_0')
    assert graph,'Missing owned emitter graph'
    updates=[]
    # Node names and their scripts were checked with native asset.read_graph;
    # UEdGraph.Nodes is protected in the Python API.
    for name,script in scripts.items():
        short=name.removeprefix('NM_')
        node_name='NiagaraNodeFunctionCall_7' if short=='GridInit' else 'Mud'+short+'Call'
        assert u.find_object(graph,node_name),node_name
        updates.append({'name':node_name,'class':'/Script/NiagaraEditor.NiagaraNodeFunctionCall',
            'properties':{'FunctionScript':"/Script/Niagara.NiagaraScript'"+script.get_path_name()+"'"}})
    assert len(updates)>=10,('Incomplete snapshot remap',len(updates))
    result=json.loads(u.MudAuthoringLibrary.edit_graph(graph.get_path_name(),json.dumps({'nodes':updates})))
    assert result['success'],result
    assert u.EditorAssetLibrary.save_directory(ROOT,False,True)
    OUT.mkdir(exist_ok=True)
    report={'root':ROOT,'system':system.get_path_name(),'remapped_module_calls':len(updates),
            'status':'Stage reconstruction from retained assets; not a complete historical revision archive'}
    (OUT/'snapshot.json').write_text(json.dumps(report,indent=2))
    return report

def build():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    assert editor.get_game_world() is None,'End PIE first'
    levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert not u.EditorAssetLibrary.does_asset_exist(MAP),'Refuse to overwrite an existing exhibit'
    # World assets must use the map Save As route, not generic asset duplication.
    assert levels.load_level('/Game/MudStudy/Maps/L_Mud_RealtimeCompare')
    assert u.EditorLoadingAndSavingUtils.save_map(editor.get_editor_world(),MAP)
    assert levels.load_level(MAP)
    assert editor.get_editor_world().get_outer().get_path_name()==MAP
    sub=u.get_editor_subsystem(u.EditorActorSubsystem)
    actors=list(sub.get_all_level_actors())
    source=next(a for a in actors if a.get_actor_label()=='NinjaLive_Mud1')
    player=next(a for a in actors if a.get_class().get_name().startswith('ThirdPersonCharacter'))
    keep={source,player}
    for _ in range(5):
        for a in actors:
            if a.get_owner() in keep or a.get_attach_parent_actor() in keep:keep.add(a)
    for a in actors:
        if a not in keep and a.get_class().get_name() not in ['WorldSettings','LevelScriptActor']:
            sub.destroy_actor(a)
    source.set_actor_location(u.Vector(-1500,2000,0),False,True)
    source.set_actor_label('Evolution_06_OriginalSolver_RebuiltSurface')
    source.set_folder_path('06_Live_OriginalSolver')
    sim=source.get_editor_property('NinjaLiveComponent')
    sim.set_editor_property('PrimaryOutputMaterials',[u.load_asset(ROOT+'/Materials/MI_Surface_Rebuilt')])
    sim.set_editor_property('PrimaryOutputMaterialSelected',0)
    sim.set_editor_property('IgnoreSystemRotation',True)
    sim.set_editor_property('PauseSimWhenNotVisible',False)
    player.set_actor_location(u.Vector(-1500,1500,110),False,True)
    player.set_actor_label('Evolution_Player')
    player.set_editor_property('auto_possess_player',u.AutoReceiveInput.PLAYER0)
    runtime=sub.spawn_actor_from_class(u.load_class(None,'/Script/MudRuntime.MudRebuildActor'),u.Vector(1500,2000,0))
    runtime.set_actor_label('Evolution_07_IndependentSolver')
    runtime.set_folder_path('07_Live_IndependentSolver')
    runtime.set_editor_property('solver',u.load_asset(ROOT+'/Niagara/NS_Evolution_Current'))
    runtime.set_editor_property('surface_material',u.load_asset(ROOT+'/Materials/MI_Surface_Rebuilt'))
    runtime.set_editor_property('output_resolution',2048)
    runtime.set_editor_property('track_player',True)
    runtime.set_editor_property('track_physics_bones',True)
    stages=[('01 UV','Coordinate basis','M_Rebuild_UV'),('02 DENSITY','Frozen B channel','M_Rebuild_DensityB'),
            ('03 NORMAL','Height-derived normal','M_Rebuild_DensityNormal'),('04 POM','Parallax + depth','MI_POM_Rebuilt'),
            ('05 SURFACE','Color / roughness / flow','MI_Surface_Rebuilt')]
    def text(label,content,x,y,z,size=32):
        a=sub.spawn_actor_from_class(u.TextRenderActor,u.Vector(x,y,z),u.Rotator(yaw=-90))
        a.set_actor_label(label);a.set_folder_path('00_ExhibitLabels')
        c=a.get_component_by_class(u.TextRenderComponent);c.set_text(u.Text(content))
        c.set_world_size(size);c.set_horizontal_alignment(u.HorizTextAligment.EHTA_CENTER)
        return a
    def cube(label,x,y,sx,sy):
        a=sub.spawn_actor_from_class(u.StaticMeshActor,u.Vector(x,y,-11));a.set_actor_label(label);a.set_folder_path('00_Environment')
        c=a.get_component_by_class(u.StaticMeshComponent);c.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
        c.set_world_scale3d(u.Vector(sx,sy,0.2));c.set_collision_profile_name('BlockAll')
    for i,(title,subtitle,material) in enumerate(stages):
        x=(i-2)*900
        a=sub.spawn_actor_from_class(u.StaticMeshActor,u.Vector(x,-500,200));a.set_actor_label('Evolution_'+title.replace(' ','_'))
        a.set_folder_path('01_05_FrozenStages')
        c=a.get_component_by_class(u.StaticMeshComponent);c.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'))
        c.set_world_scale3d(u.Vector(7,7,1));c.set_material(0,u.load_asset(ROOT+'/Materials/'+material))
        text('Label_'+str(i+1),title+'\n'+subtitle+'\nRETAINED STAGE ASSET',x,-920,230,30)
    text('Evolution_Title','MUD REBUILD / EVOLUTION COMPARISON',0,-1550,340,65)
    text('Evolution_Status','STAGE RECONSTRUCTIONS - NOT COMPLETE HISTORICAL SNAPSHOTS',0,-1720,180,29)
    text('Label_06','06  LIVE MATERIAL INTEGRATION\nORIGINAL SOLVER + REBUILT SURFACE',-1500,850,100,43)
    text('Label_07','07  INDEPENDENT REBUILD\nOWN SOLVER + OWN SURFACE / WIP',1500,850,100,43)
    # Floor surrounds the two live mud panels; keep their underside clear for PDO.
    for p in [('South',0,-400,90,24),('North',0,3800,90,16),('West',-3500,2000,20,24),
              ('East',3500,2000,20,24),('Bridge',0,2000,10,24)]:cube('Evolution_Floor_'+p[0],*p[1:])
    sun=sub.spawn_actor_from_class(u.DirectionalLight,u.Vector(0,0,1200),u.Rotator(pitch=-45,yaw=-35))
    sun.set_actor_label('Evolution_Sun');sun.set_folder_path('00_Environment')
    light=sun.get_component_by_class(u.DirectionalLightComponent);light.set_editor_property('intensity',10.0);light.set_editor_property('atmosphere_sun_light',True)
    sky=sub.spawn_actor_from_class(u.SkyLight,u.Vector(0,0,900));sky.set_actor_label('Evolution_Sky');sky.set_folder_path('00_Environment')
    sky.get_component_by_class(u.SkyLightComponent).set_editor_property('real_time_capture',True)
    atmosphere=sub.spawn_actor_from_class(u.SkyAtmosphere,u.Vector());atmosphere.set_actor_label('Evolution_Atmosphere');atmosphere.set_folder_path('00_Environment')
    assert levels.save_current_level()
    report={'map':MAP,'static_stages':stages,'live_original':source.get_path_name(),'live_independent':runtime.get_path_name(),
            'material_root':ROOT+'/Materials','solver':runtime.get_editor_property('solver').get_path_name()}
    OUT.mkdir(exist_ok=True);(OUT/'gallery.json').write_text(json.dumps(report,indent=2))
    return report
