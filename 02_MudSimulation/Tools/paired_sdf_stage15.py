"""Same raw point input, one explicit 60 Hz step per rendered frame, both solvers."""
import unreal as u,json,re,math
from pathlib import Path
OUT=Path('D:/aco/unreal/Stormfall/Verification/MudSolver');STATE={}

def point(v):return [float(x) for x in re.findall(r'[XYZ]=([-+0-9.eE]+)',v)[:3]]

def start(own_input_lag_steps=0,noise=True,max_steps=256):
    assert not STATE.get('handle')
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    actors=u.GameplayStatics.get_all_actors_of_class(w,u.Actor)
    source=next(a for a in actors if a.get_actor_label()=='NinjaLive_Mud1').get_editor_property('NinjaLiveComponent')
    own=next(a for a in actors if a.get_actor_label()=='Mud_Rebuilt_Runtime')
    gpu=json.loads(u.MudAuthoringLibrary.inspect_gpu_inputs(source,'System.SimPosDouble'))
    assert gpu.get('success'), 'Activate the reference through pawn proximity before testing'
    layout=json.loads(u.MudAuthoringLibrary.inspect_gpu_inputs(source,'CompositeGrid'))
    grids=[v for v in layout.get('values',[]) if 'cellsX' in v]
    assert grids and all(v['cellsX']==2048 and v['cellsY']==2048 for v in grids), 'Reference is not initialized with the mud preset: '+str(grids)
    center=point(next(v['value'] for v in gpu['values'] if v['name']=='System.SimPosDouble'))
    own.set_actor_tick_enabled(False)
    source.set_component_tick_enabled(False)
    source.set_editor_property('BrushStrength',1);source.set_editor_property('EnableMeshDistanceFieldReader',True)
    own.set_actor_location(u.Vector(*center),False,True)
    own.set_editor_property('brush_position_random',0)
    own.rebuild_simulation();comp=own.get_editor_property('simulation');comp.set_component_tick_enabled(False)
    comp.set_variable_float('User.BrushVelocityNoise',0.5 if noise else 0)
    comp.set_variable_float('User.BrushDensityNoise',0.4 if noise else 0)
    source.reinitialize_system()
    # Controller overrides are cleared by ReinitializeSystem: apply them afterwards.
    source.set_variable_float('User.Painter.BrushStrength',1)
    source.set_variable_float('User.Painter.BrushPositionRandom',0)
    source.set_variable_float('User.Painter.BrushVelocityNoise',0.5 if noise else 0)
    source.set_variable_float('User.Painter.BrushDensityNoise',0.4 if noise else 0)
    source.set_variable_bool('User.EnableMeshDistanceFieldReader',True)
    fixture=next(a for a in actors if a.get_actor_label()=='Mud_Rebuilt_InputProbe')
    fixture.set_actor_scale3d(u.Vector(2,2,2))
    fixture.set_actor_location(u.Vector(center[0]-300,center[1],center[2]-10),False,True)
    for target,param in [(source,'User.TrackedMeshesSDF'),(comp,'User.SdfQuery')]:
        u.NiagaraDIRigidMeshCollisionFunctionLibrary.set_source_actors(target,param,[fixture])
        candidates=[u.find_object(target,'NiagaraDataInterfaceRigidMeshCollisionQuery_'+str(i)) for i in range(4)]
        query=next(q for q in candidates if q is not None)
        query.set_editor_property('GlobalSearchAllowed',False)
        query.set_editor_property('GlobalSearchForced',False)
        query.set_editor_property('ActorTags',[])
    assert u.GameplayStatics.set_game_paused(w,True)
    material=u.load_asset('/Game/MudStudy/Rebuild/Materials/M_LiveRT_Probe')
    mids=[u.MaterialLibrary.create_dynamic_material_instance(w,material) for _ in range(2)]
    targets=[u.RenderingLibrary.create_render_target2d(w,64,64,u.TextureRenderTargetFormat.RTF_RGBA32F,u.LinearColor(0,0,0,0),False,False) for _ in range(2)]
    STATE.clear();STATE.update(world=w,source=source,own=own,comp=comp,center=center,own_center=own.get_actor_location(),
        frame=0,mids=mids,targets=targets,samples=[])
    def image(rt,index):
        mids[index].set_texture_parameter_value('Buffer',rt)
        u.RenderingLibrary.draw_material_to_render_target(w,targets[index],mids[index])
        ps=u.RenderingLibrary.read_render_target_raw_pixel_area(w,targets[index],0,0,64,64,False)
        return [[p.r,p.g,p.b] for p in ps]
    def tick(dt):
        try:
            STATE['frame']+=1;n=STATE['frame']
            x=-300+min(max(n-20,0),60)*10
            c=STATE['own_center'];own_x=-300+min(max(n-own_input_lag_steps-20,0),60)*10
            u.NiagaraDataInterfaceArrayFunctionLibrary.set_niagara_array_position(source,'User.TrackedPositions',[])
            u.NiagaraDataInterfaceArrayFunctionLibrary.set_niagara_array_vector4(source,'User.TrackedParams',[])
            u.NiagaraDataInterfaceArrayFunctionLibrary.set_niagara_array_vector4(comp,'User.BrushWorldPositions',[])
            fixture.set_actor_location(u.Vector(center[0]+x,center[1],center[2]-10),False,True)
            source.advance_simulation(1,0.01667);comp.advance_simulation(1,0.01667)
            if n==32:
                (OUT/'paired_point_gpu_at32.json').write_text(u.MudAuthoringLibrary.inspect_gpu_inputs(source,''))
                cache=u.NiagaraSimCacheFunctionLibrary.create_niagara_sim_cache(w)
                parameters=u.NiagaraSimCacheCreateParameters();parameters.set_editor_property('allow_data_interface_caching',False)
                u.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(cache,parameters,source,False,0.01667)
                STATE['cache']=cache
            if n==36:
                cache=STATE['cache'];attributes={}
                for name in ['UnitPosition','Previous.UnitPosition','UnitVelocity','Previous.UnitVelocity']:
                    attributes[name]=[[v.x,v.y,v.z] for v in cache.read_vector_attribute(name,'ArrayReader',0)]
                for name in ['BrushScale','Age']:attributes[name]=list(cache.read_float_attribute(name,'ArrayReader',0))
                (OUT/'paired_point_source_at32.json').write_text(json.dumps(attributes,indent=2))
            if n in [4,16,32,64,96,128,192,256]:
                a=image(source.get_editor_property('RT_VelocityDensity'),0);b=image(own.get_editor_property('output'),1)
                es=[[abs(v-t) for v,t in zip(p,q)] for p,q in zip(a,b)]
                row={'step':n,'finite':all(math.isfinite(v) for im in [a,b] for p in im for v in p),
                    'original_random':str(source.get_variable_float('User.Painter.BrushPositionRandom')),
                    'original_density_noise':str(source.get_variable_float('User.Painter.BrushDensityNoise')),
                    'rebuilt_random':str(comp.get_variable_float('User.BrushRandom')),
                    'rebuilt_density_noise':str(comp.get_variable_float('User.BrushDensityNoise')),
                    'max_rgb_error':[max(p[k] for p in es) for k in range(3)],
                    'mean_rgb_error':[sum(p[k] for p in es)/4096 for k in range(3)],
                    'original_range':[[min(p[k] for p in a),max(p[k] for p in a)] for k in range(3)],
                    'rebuilt_range':[[min(p[k] for p in b),max(p[k] for p in b)] for k in range(3)]}
                STATE['samples'].append(row)
                suffix='' if noise else '_no_noise'
                (OUT/('paired_sdf_lag'+str(own_input_lag_steps)+suffix+'.json')).write_text(json.dumps({'complete':n==max_steps,'source_center':center,'own_input_lag_steps':own_input_lag_steps,'brush_noise':noise,'jitter_disabled_for_comparison':True,'samples':STATE['samples']},indent=2))
            if n==max_steps:
                u.unregister_slate_post_tick_callback(STATE['handle']);STATE['handle']=None
                u.GameplayStatics.set_game_paused(w,False)
        except Exception as e:
            u.unregister_slate_post_tick_callback(STATE['handle']);STATE['handle']=None
            u.GameplayStatics.set_game_paused(w,False)
            (OUT/'paired_manual_point.json').write_text(json.dumps({'complete':False,'error':str(e),'samples':STATE['samples']},indent=2))
    STATE['handle']=u.register_slate_post_tick_callback(tick)
    return {'scheduled':True,'manual_steps':256,'source_center':center,'tick_delta':0.01667}



