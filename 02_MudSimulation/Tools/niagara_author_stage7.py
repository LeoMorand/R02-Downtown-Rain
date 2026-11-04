"""Create plain Niagara module graphs using the owned authoring helper.

The resulting scripts contain only engine types and inspectable HLSL/pins.
No runtime dependency on the MudAuthoring editor plugin is introduced.
"""
import unreal as u,json
from pathlib import Path
OUT=Path('D:/aco/unreal/Stormfall/Verification/MudSolver')

def status():
    return {'helper_loaded':hasattr(u,'MudAuthoringLibrary'),'world':u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_name()}

def create_module(path,body,inputs,outputs):
    assert path.startswith('/Game/MudStudy/')
    script=u.load_asset(path);assert script,'Create a module factory scaffold first'
    source=script.get_editor_property('latest_source') if False else None
    # Factory-owned source subobject is Source_0; resolve without protected access.
    source=u.find_object(script,'NiagaraScriptSource_0')
    assert source,script.get_path_name()
    graph=u.find_object(source,'NiagaraGraph_0');assert graph
    signature={'inputs':[{'name':n,'type':t} for n,t,b in inputs],'outputs':[{'name':n,'type':t} for n,t,b in outputs]}
    nodes=[{'name':'MudInput','class':'/Script/NiagaraEditor.NiagaraNodeInput','x':-900,'y':0,'variable':{'property':'Input','name':'InputMap','type':'map'},'properties':{'Usage':'Parameter'}},
        {'name':'MudGet','class':'/Script/NiagaraEditor.NiagaraNodeParameterMapGet','x':-600,'y':100},
        {'name':'MudHlsl','class':'/Script/NiagaraEditor.NiagaraNodeCustomHlsl','x':-200,'y':100,'signature':signature,'properties':{'CustomHlsl':body}},
        {'name':'MudSet','class':'/Script/NiagaraEditor.NiagaraNodeParameterMapSet','x':200,'y':0},
        {'name':'MudOutput','class':'/Script/NiagaraEditor.NiagaraNodeOutput','x':600,'y':0,'outputVariables':[{'name':'OutputMap','type':'map'}],'properties':{'ScriptType':'Module'}}]
    pins=[];links=[{'from':'MudInput','out':'Input','to':'MudGet','in':'Source'},
        {'from':'MudInput','out':'Input','to':'MudSet','in':'Source'},
        {'from':'MudSet','out':'Dest','to':'MudOutput','in':'OutputMap'}]
    for name,typ,binding in inputs:
        pins.append({'node':'MudGet','name':binding,'type':typ,'direction':'output'})
        links.append({'from':'MudGet','out':binding,'to':'MudHlsl','in':name})
    for name,typ,binding in outputs:
        pins.append({'node':'MudSet','name':binding,'type':typ,'direction':'input'})
        links.append({'from':'MudHlsl','out':name,'to':'MudSet','in':binding})
    spec={'clear':True,'nodes':nodes,'pins':pins,'links':links}
    result=json.loads(u.MudAuthoringLibrary.edit_graph(graph.get_path_name(),json.dumps(spec)))
    assert result['success'],result
    saved=json.loads(u.MudAuthoringLibrary.save_owned_object(script.get_path_name()));assert saved['success'],saved
    return {'path':script.get_path_name(),'graph':graph.get_path_name(),'result':result}

def grid_proof():
    return create_module('/Game/MudStudy/Rebuild/Niagara/NM_GridProof',
        'Value=float4(0,0,0,0);\n#if GPU_SIMULATION\nfloat2 uv; Grid.ExecutionIndexToUnit(uv); Value=float4(uv,0.5,1);\n#endif',
        [('Grid','/Script/Niagara.NiagaraDataInterfaceGrid2DCollection','Emitter.StateGrid')],
        [('Value','float4','StackContext.State')])

def configure_proof():
    system='/Game/MudStudy/Rebuild/Niagara/NS_Mud_FromScratch.NS_Mud_FromScratch'
    defaults=json.dumps({'NumCellsX':'32','NumCellsY':'32','NumAttributes':'4','SetGridFromMaxAxis':'false','WorldBBoxSize':'(X=20,Y=20)','bOverrideFormat':'true','OverrideBufferFormat':'Float'})
    result=json.loads(u.MudAuthoringLibrary.add_user_parameter(system,'User.StateGrid','/Script/Niagara.NiagaraDataInterfaceGrid2DCollection',defaults));assert result['success'],result
    graph=system+':NE_Mud_FromScratch.NiagaraScriptSource_0.NiagaraGraph_0'
    spec={'nodes':[{'name':'MudGridProofCall','class':'/Script/NiagaraEditor.NiagaraNodeFunctionCall','x':0,'y':1000,
        'properties':{'FunctionScript':"/Script/Niagara.NiagaraScript'/Game/MudStudy/Rebuild/Niagara/NM_GridProof.NM_GridProof'"}}],
        'links':[{'from':'NiagaraNodeInput_4','out':'Input','to':'MudGridProofCall','in':'InputMap'},
            {'from':'MudGridProofCall','out':'OutputMap','to':'NiagaraNodeOutput_4','in':'OutParamMap'}]}
    edit=json.loads(u.MudAuthoringLibrary.edit_graph(graph,json.dumps(spec)));assert edit['success'],edit
    return {'graph':graph,'result':edit,'save':u.MudAuthoringLibrary.save_owned_object(system)}

def grid_init():
    script=u.load_asset('/Game/MudStudy/Rebuild/Niagara/NM_GridInit')
    graph=u.find_object(u.find_object(script,'NiagaraScriptSource_0'),'NiagaraGraph_0')
    di='/Script/Niagara.NiagaraDataInterfaceGrid2DCollection'
    spec={'clear':True,'nodes':[
        {'name':'InitInput','class':'/Script/NiagaraEditor.NiagaraNodeInput','x':-600,'y':0,'variable':{'property':'Input','name':'InputMap','type':'map'},'properties':{'Usage':'Parameter'}},
        {'name':'InitGet','class':'/Script/NiagaraEditor.NiagaraNodeParameterMapGet','x':-300,'y':100},
        {'name':'InitSet','class':'/Script/NiagaraEditor.NiagaraNodeParameterMapSet','x':0,'y':0},
        {'name':'InitOutput','class':'/Script/NiagaraEditor.NiagaraNodeOutput','x':400,'y':0,'outputVariables':[{'name':'OutputMap','type':'map'}],'properties':{'ScriptType':'Module'}}],
        'pins':[{'node':'InitGet','name':'User.StateGrid','type':di,'direction':'output'},
            {'node':'InitSet','name':'Emitter.StateGrid','type':di,'direction':'input'}],
        'links':[{'from':'InitInput','out':'Input','to':'InitGet','in':'Source'},
            {'from':'InitInput','out':'Input','to':'InitSet','in':'Source'},
            {'from':'InitGet','out':'User.StateGrid','to':'InitSet','in':'Emitter.StateGrid'},
            {'from':'InitSet','out':'Dest','to':'InitOutput','in':'OutputMap'}]}
    result=json.loads(u.MudAuthoringLibrary.edit_graph(graph.get_path_name(),json.dumps(spec)));assert result['success'],result
    return u.MudAuthoringLibrary.save_owned_object(script.get_path_name())

def grid_export(source_grid='StateGrid',output_protocol=False):
    system='/Game/MudStudy/Rebuild/Niagara/NS_Mud_FromScratch.NS_Mud_FromScratch'
    helper=u.MudAuthoringLibrary
    for name,typ,default in [('User.OutputTexture','/Script/Engine.TextureRenderTarget',''),
        ('User.OutputTarget','/Script/Niagara.NiagaraDataInterfaceRenderTarget2D',json.dumps({'bInheritUserParameterSettings':'true','RenderTargetUserParameter':'(Parameter=(Name="User.OutputTexture"))'}))]:
        result=json.loads(helper.add_user_parameter(system,name,typ,default));assert result['success'],result
    script=u.load_asset('/Game/MudStudy/Rebuild/Niagara/NM_GridExport')
    graph=u.find_object(u.find_object(script,'NiagaraScriptSource_0'),'NiagaraGraph_0')
    body='''#if GPU_SIMULATION
int x,y;Target.ExecToIndex(x,y);float2 uv;Target.ExecToUnit(uv);
float4 value;Grid.SamplePreviousGridVector4Value<Attribute=State>(uv,value);
Target.SetRenderTargetValue(true,x,y,value);
#endif'''
    if output_protocol:
        body=body.replace('Target.SetRenderTargetValue(true,x,y,value);',
            'float edge=saturate(10-0.01-max(abs(uv.x*20-10),abs(uv.y*20-10)));\nvalue=float4(value.xy*edge,1-value.z,max(1-value.z,0.01));\nTarget.SetRenderTargetValue(true,x,y,value);')
    signature={'inputs':[{'name':'MapIn','type':'map'},{'name':'Grid','type':'/Script/Niagara.NiagaraDataInterfaceGrid2DCollection'},{'name':'Target','type':'/Script/Niagara.NiagaraDataInterfaceRenderTarget2D'}],
        'outputs':[{'name':'MapOut','type':'map'}]}
    spec={'clear':True,'nodes':[
        {'name':'ExportInput','class':'/Script/NiagaraEditor.NiagaraNodeInput','x':-600,'y':0,'variable':{'name':'InputMap','type':'map','property':'Input'},'properties':{'Usage':'Parameter'}},
        {'name':'ExportGet','class':'/Script/NiagaraEditor.NiagaraNodeParameterMapGet','x':-400,'y':100},
        {'name':'ExportHlsl','class':'/Script/NiagaraEditor.NiagaraNodeCustomHlsl','x':0,'y':0,'signature':signature,'properties':{'CustomHlsl':body}},
        {'name':'ExportOutput','class':'/Script/NiagaraEditor.NiagaraNodeOutput','x':500,'y':0,'outputVariables':[{'name':'OutputMap','type':'map'}],'properties':{'ScriptType':'Module'}}],
        'pins':[{'node':'ExportGet','name':'Emitter.'+source_grid,'type':'/Script/Niagara.NiagaraDataInterfaceGrid2DCollection','direction':'output'},
            {'node':'ExportGet','name':'User.OutputTarget','type':'/Script/Niagara.NiagaraDataInterfaceRenderTarget2D','direction':'output'}],
        'links':[{'from':'ExportInput','out':'Input','to':'ExportGet','in':'Source'},{'from':'ExportInput','out':'Input','to':'ExportHlsl','in':'MapIn'},
            {'from':'ExportGet','out':'Emitter.'+source_grid,'to':'ExportHlsl','in':'Grid'},{'from':'ExportGet','out':'User.OutputTarget','to':'ExportHlsl','in':'Target'},
            {'from':'ExportHlsl','out':'MapOut','to':'ExportOutput','in':'OutputMap'}]}
    result=json.loads(helper.edit_graph(graph.get_path_name(),json.dumps(spec)));assert result['success'],result
    helper.save_owned_object(script.get_path_name())
    sysgraph=system+':NE_Mud_FromScratch.NiagaraScriptSource_0.NiagaraGraph_0'
    call={'nodes':[{'name':'MudGridExportCall','class':'/Script/NiagaraEditor.NiagaraNodeFunctionCall','x':0,'y':1400,'properties':{'FunctionScript':"/Script/Niagara.NiagaraScript'/Game/MudStudy/Rebuild/Niagara/NM_GridExport.NM_GridExport'"}}],
        'links':[{'from':'NiagaraNodeInput_5','out':'Input','to':'MudGridExportCall','in':'InputMap'},{'from':'MudGridExportCall','out':'OutputMap','to':'NiagaraNodeOutput_5','in':'OutParamMap'}]}
    result=json.loads(helper.edit_graph(sysgraph,json.dumps(call)));assert result['success'],result
    return helper.save_owned_object(system)

def tracking_debug():
    grid_export('TrackingGrid',False)
    script=u.load_asset('/Game/MudStudy/Rebuild/Niagara/NM_GridExport')
    graph=u.find_object(u.find_object(script,'NiagaraScriptSource_0'),'NiagaraGraph_0')
    body='''#if GPU_SIMULATION
int x,y;Target.ExecToIndex(x,y);float4 value=0;
if(x%4==0)Grid.GetPreviousVector4Value<Attribute=TrackedPosition>(0,0,value);
if(x%4==1)Grid.GetPreviousVector4Value<Attribute=TrackedPrevious>(0,0,value);
if(x%4==2)Grid.GetPreviousVector4Value<Attribute=TrackedVelocity>(0,0,value);
if(x%4==3)Grid.GetPreviousVector4Value<Attribute=TrackedWorld>(0,0,value);
Target.SetRenderTargetValue(true,x,y,value);
#endif'''
    result=json.loads(u.MudAuthoringLibrary.edit_graph(graph.get_path_name(),json.dumps({'nodes':[{'name':'ExportHlsl','class':'/Script/NiagaraEditor.NiagaraNodeCustomHlsl','properties':{'CustomHlsl':body}}]})))
    assert result['success'],result
    return u.MudAuthoringLibrary.save_owned_object(script.get_path_name())

def setup_proof_actor():
    u.MudAuthoringLibrary.save_owned_object('/Game/MudStudy/Rebuild/Niagara/NS_Mud_FromScratch.NS_Mud_FromScratch')
    sub=u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert sub.load_level('/Game/MudStudy/Maps/L_Mud_RealtimeCompare')
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    actor=next((a for a in actors.get_all_level_actors() if a.get_actor_label()=='Mud_Rebuilt_Simulation'),None)
    if actor is None:actor=actors.spawn_actor_from_class(u.NiagaraActor,u.Vector(-3500,15000,-500));actor.set_actor_label('Mud_Rebuilt_Simulation')
    comp=actor.get_component_by_class(u.NiagaraComponent)
    comp.set_asset(u.load_asset('/Game/MudStudy/Rebuild/Niagara/NS_Mud_FromScratch'))
    assert sub.save_current_level()
    return {'actor':actor.get_path_name(),'component':comp.get_path_name()}

def inspect_proof():
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    actor=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor) if a.get_actor_label()=='Mud_Rebuilt_Simulation')
    comp=actor.get_component_by_class(u.NiagaraComponent)
    # Runtime interfaces are protected inside OverrideParameters. Inspect owned
    # subobjects by path rather than bypassing Python's protected-property gate.
    interfaces=[u.find_object(comp,'NiagaraDataInterfaceGrid2DCollection_'+str(i)) for i in range(32)]
    rows=[]
    for di in interfaces:
        if di:
            row={'path':di.get_path_name(),'class':di.get_class().get_name()}
            if di.get_class().get_name()=='NiagaraDataInterfaceGrid2DCollection':
                raw_size=di.get_raw_texture_size(comp);row['raw_size']=str(raw_size)
                sx,sy=raw_size
                rt=u.RenderingLibrary.create_render_target2d(w,sx,sy,u.TextureRenderTargetFormat.RTF_R32F,u.LinearColor(0,0,0,0),False,False)
                row['size']=str(di.get_texture_size(comp))
                row['fill']=str(di.fill_raw_texture2d(comp,rt))
                pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(w,rt,0,0,sx,sy,False)
                row['first_pixel']=[pixels[0].r,pixels[0].g,pixels[0].b,pixels[0].a]
                row['max_rgb']=max(max(c.r,c.g,c.b) for c in pixels)
            rows.append(row)
    result={'actor':actor.get_path_name(),'active':comp.is_active(),'interfaces':rows}
    (OUT/'niagara_grid_proof.json').write_text(json.dumps(result,indent=2))
    return result

def verify_export_start():
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    actor=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor) if a.get_actor_label()=='Mud_Rebuilt_Simulation')
    comp=actor.get_component_by_class(u.NiagaraComponent)
    rt=u.RenderingLibrary.create_render_target2d(w,32,32,u.TextureRenderTargetFormat.RTF_RGBA32F,u.LinearColor(0,0,0,0),False,True)
    comp.reinitialize_system();comp.set_variable_texture_render_target('User.OutputTexture',rt)
    start=u.GameplayStatics.get_time_seconds(w);state={}
    def tick(delta):
        try:
            if u.GameplayStatics.get_time_seconds(w)-start<2:return
            u.unregister_slate_post_tick_callback(state['handle'])
            pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(w,rt,0,0,32,32,False)
            assert len(pixels)==1024
            error=max(max(abs(c.r-(i%32+.5)/32),abs(c.g-(i//32+.5)/32),abs(c.b-.5),abs(c.a-1)) for i,c in enumerate(pixels))
            result={'complete':True,'size':[32,32],'source':'New empty-engine emitter and authored NM_GridInit/NM_GridProof/NM_GridExport; no vendor modules',
                'max_rgba_error':error,'first_pixel':[pixels[0].r,pixels[0].g,pixels[0].b,pixels[0].a],
                'last_pixel':[pixels[-1].r,pixels[-1].g,pixels[-1].b,pixels[-1].a],'pass':error<1e-5}
            (OUT/'niagara_export_proof.json').write_text(json.dumps(result,indent=2))
        except Exception as e:
            try:u.unregister_slate_post_tick_callback(state['handle'])
            except Exception:pass
            (OUT/'niagara_export_proof.json').write_text(json.dumps({'complete':False,'error':str(e)},indent=2))
    state['handle']=u.register_slate_post_tick_callback(tick)
    return {'started':True,'output':str(OUT/'niagara_export_proof.json'),'rt':rt.get_path_name()}
