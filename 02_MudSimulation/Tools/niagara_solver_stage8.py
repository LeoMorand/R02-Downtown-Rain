"""Source-authored Niagara solver modules. No vendor graph dependencies."""
import sys,json
from pathlib import Path
import unreal as u
sys.path.insert(0,'D:/aco/unreal/Stormfall/Tools/MudStudy')
from niagara_author_stage7 import create_module
ROOT='/Game/MudStudy/Rebuild/Niagara/'
GRID='/Script/Niagara.NiagaraDataInterfaceGrid2DCollection'

def typed_default(typ,value):
    if typ=='bool':return '(Value='+('-1' if value=='true' else '0')+')'
    if typ in ['float','int']:return '(Value='+value+')'
    return value

def advection():
    return create_module(ROOT+'NM_Advection', '''Value=0;
#if GPU_SIMULATION
float2 uv; Destination.ExecutionIndexToUnit(uv);
int nx,ny; Destination.GetNumCells(nx,ny);float2 cell=1.0/float2(nx,ny);
float4 center; Source.SamplePreviousGridVector4Value<Attribute=State>(uv,center);
float2 back=uv-center.xy*cell*SimSpeed;
if(!AreaClamp)back=frac(back);
float4 transported;Source.SamplePreviousGridVector4Value<Attribute=State>(back,transported);
Value=float4(transported.xyz*Feedback,transported.w);
#endif''',
    [('Destination',GRID,'Emitter.AdvectionGrid'),('Source',GRID,'Emitter.CompositeGrid'),
     ('SimSpeed','float','User.SimSpeed'),('Feedback','float','User.VelocityFeedback'),('AreaClamp','bool','User.AreaClamp')],
    [('Value','float4','StackContext.State')])

def divergence():
    return create_module(ROOT+'NM_Divergence', '''Value=0;
#if GPU_SIMULATION
float2 uv;Destination.ExecutionIndexToUnit(uv);
int nx,ny;Source.GetNumCells(nx,ny);float2 cell=1.0/float2(nx,ny);
float2 stepUV=cell*SimSpeed;
float4 r,l,t,b,painter,pressure;
Source.SamplePreviousGridVector4Value<Attribute=State>(uv+float2(stepUV.x,0),r);
Source.SamplePreviousGridVector4Value<Attribute=State>(uv-float2(stepUV.x,0),l);
Source.SamplePreviousGridVector4Value<Attribute=State>(uv+float2(0,stepUV.y),t);
Source.SamplePreviousGridVector4Value<Attribute=State>(uv-float2(0,stepUV.y),b);
int px,py;Painter.UnitToIndex(uv,px,py);
Painter.GetPreviousVector4Value<Attribute=State>(px,py,painter);
PreviousPressure.SamplePreviousGridVector4Value<Attribute=State>(uv+WorldOffsetDelta,pressure);
float multiplier=CrudeSolver?min(0.5,DivergenceMult):DivergenceMult;
float d=clamp(multiplier*(r.x-l.x+t.y-b.y+BrushPuncture*0.01*painter.z),-2,2);
Value=float4(pressure.x,d,0,0);
#endif''',
    [('Destination',GRID,'Emitter.DivergenceGrid'),('Source',GRID,'Emitter.AdvectionGrid'),
     ('Painter',GRID,'Emitter.PainterGrid'),('PreviousPressure',GRID,'Emitter.PressureGrid'),
     ('SimSpeed','float','User.SimSpeed'),('WorldOffsetDelta','float2','User.WorldOffsetDelta'),
     ('CrudeSolver','bool','User.CrudeSolver'),('DivergenceMult','float','User.DivergenceMult'),('BrushPuncture','float','User.BrushPuncture')],
    [('Value','float4','StackContext.State')])

def configure_parameters():
    system=ROOT+'NS_Mud_FromScratch.NS_Mud_FromScratch'
    helper=u.MudAuthoringLibrary
    params=[('User.SimSpeed','float','8'),('User.VelocityFeedback','float','0.9'),
        ('User.AreaClamp','bool','true'),('User.WorldOffsetDelta','float2','(X=0,Y=0)'),
        ('User.CrudeSolver','bool','false'),('User.DivergenceMult','float','0.1'),('User.BrushPuncture','float','0.05')]
    for name in ['CompositeGrid','AdvectionGrid','DivergenceGrid','PainterGrid','PressureGrid']:
        params.append(('User.'+name,GRID,json.dumps({'NumCellsX':'32','NumCellsY':'32','NumAttributes':'4','SetGridFromMaxAxis':'false','WorldBBoxSize':'(X=20,Y=20)','bOverrideFormat':'true','OverrideBufferFormat':'Float'})))
    results=[]
    for name,typ,value in params:
        result=json.loads(helper.add_user_parameter(system,name,typ,typed_default(typ,value)));assert result['success'],result
        results.append(name)
    helper.save_owned_object(system)
    return results

def init_aliases():
    script=u.load_asset(ROOT+'NM_GridInit')
    graph=u.find_object(u.find_object(script,'NiagaraScriptSource_0'),'NiagaraGraph_0')
    names=['CompositeGrid','AdvectionGrid','DivergenceGrid','PainterGrid','PressureGrid']
    spec={'pins':[],'links':[]}
    for n in names:
        spec['pins'] += [{'node':'InitGet','name':'User.'+n,'type':GRID,'direction':'output'},
            {'node':'InitSet','name':'Emitter.'+n,'type':GRID,'direction':'input'}]
        spec['links'].append({'from':'InitGet','out':'User.'+n,'to':'InitSet','in':'Emitter.'+n})
    result=json.loads(u.MudAuthoringLibrary.edit_graph(graph.get_path_name(),json.dumps(spec)));assert result['success'],result
    return u.MudAuthoringLibrary.save_owned_object(script.get_path_name())

def connect_advection():
    system=ROOT+'NS_Mud_FromScratch.NS_Mud_FromScratch'
    spec={'nodes':[{'name':'MudAdvectionCall','class':'/Script/NiagaraEditor.NiagaraNodeFunctionCall',
        'x':0,'y':1800,'properties':{'FunctionScript':"/Script/Niagara.NiagaraScript'"+ROOT+"NM_Advection.NM_Advection'"}}],
        'links':[{'from':'NiagaraNodeInput_6','out':'Input','to':'MudAdvectionCall','in':'InputMap'},
                 {'from':'MudAdvectionCall','out':'OutputMap','to':'NiagaraNodeOutput_6','in':'OutParamMap'}]}
    result=json.loads(u.MudAuthoringLibrary.edit_graph(system+':NE_Mud_FromScratch.NiagaraScriptSource_0.NiagaraGraph_0',json.dumps(spec)));assert result['success'],result
    return u.MudAuthoringLibrary.save_owned_object(system)

def connect_divergence():
    system=ROOT+'NS_Mud_FromScratch.NS_Mud_FromScratch'
    spec={'nodes':[{'name':'MudDivergenceCall','class':'/Script/NiagaraEditor.NiagaraNodeFunctionCall',
        'x':0,'y':2200,'properties':{'FunctionScript':"/Script/Niagara.NiagaraScript'"+ROOT+"NM_Divergence.NM_Divergence'"}}],
        'links':[{'from':'NiagaraNodeInput_7','out':'Input','to':'MudDivergenceCall','in':'InputMap'},
                 {'from':'MudDivergenceCall','out':'OutputMap','to':'NiagaraNodeOutput_7','in':'OutParamMap'}]}
    result=json.loads(u.MudAuthoringLibrary.edit_graph(system+':NE_Mud_FromScratch.NiagaraScriptSource_0.NiagaraGraph_0',json.dumps(spec)));assert result['success'],result
    return u.MudAuthoringLibrary.save_owned_object(system)

def pressure_modules():
    source=Path('D:/aco/unreal/Stormfall/Tools/MudStudy/Reference/PressureStage6.hlsl').read_text()
    # Preserve selected 1.6 source indices and inclusive loop for GPU A/B.
    # In particular, do not silently repair the preset's negative kernel row.
    body=source[source.index('float2 WeightedAverage'):]
    body=body.replace('SampledColor=Texture2DSampleLevel(Pressure,PressureSampler,frac(min(max(OffsetCenterUV + Direction * ( ix - Direction ),Clamp-1),2-Clamp)),0).rg;',
        'float4 sample4;Source.SamplePreviousGridVector4Value<Attribute=State>(frac(min(max(OffsetCenterUV + Direction * ( ix - Direction ),Clamp-1),2-Clamp)),sample4);SampledColor=sample4.xy;')
    body=body.replace('return float3(WeightedAverage*0.999*float2(PressureFeedback,DivergenceFeedback),0);',
        'Value=float4(WeightedAverage*0.999*float2(PressureFeedback,DivergenceFeedback),0,0);')
    results=[]
    for vertical in [False,True]:
        header='''Value=0;
#if GPU_SIMULATION
float2 UV;Destination.ExecutionIndexToUnit(UV);
int nx,ny;Destination.GetNumCells(nx,ny);float2 TexelSize=SimSpeed/float2(nx,ny);
float2 CenterUV=UV;
int KernelIndex=(int)ceil((15-clamp(15*KernelMult,5,15))*0.5);
int GaussKernelIndexOffset=(int)clamp(KernelOffset,min(5-KernelIndex,KernelOffset),max(-KernelIndex,KernelOffset));
float Clamp=AreaClamp?1:0;
int StepIndex=STEP;
'''.replace('STEP','1' if vertical else '0')
        dest='PressureGrid' if vertical else 'PressureHGrid'
        src='PressureHGrid' if vertical else 'DivergenceGrid'
        results.append(create_module(ROOT+('NM_PressureVertical' if vertical else 'NM_PressureHorizontal'),header+body+'\n#endif',
            [('Destination',GRID,'Emitter.'+dest),('Source',GRID,'Emitter.'+src),
             ('SimSpeed','float','User.SimSpeed'),('AreaClamp','bool','User.AreaClamp'),
             ('KernelMult','float','User.KernelMult'),('KernelOffset','float','User.KernelOffset'),
             ('PressureFeedback','float','User.PressureFeedback'),('DivergenceFeedback','float','User.DivergenceFeedback')],
            [('Value','float4','StackContext.State')]))
    return results

def pressure_parameters():
    system=ROOT+'NS_Mud_FromScratch.NS_Mud_FromScratch';helper=u.MudAuthoringLibrary
    for name,typ,value in [('User.KernelMult','float','1'),('User.KernelOffset','float','-1'),
        ('User.PressureFeedback','float','1'),('User.DivergenceFeedback','float','1'),
        ('User.PressureHGrid',GRID,json.dumps({'NumCellsX':'32','NumCellsY':'32','NumAttributes':'4','SetGridFromMaxAxis':'false','WorldBBoxSize':'(X=20,Y=20)','bOverrideFormat':'true','OverrideBufferFormat':'Float'}))]:
        result=json.loads(helper.add_user_parameter(system,name,typ,typed_default(typ,value)));assert result['success'],result
    script=u.load_asset(ROOT+'NM_GridInit');graph=u.find_object(u.find_object(script,'NiagaraScriptSource_0'),'NiagaraGraph_0')
    spec={'pins':[{'node':'InitGet','name':'User.PressureHGrid','type':GRID,'direction':'output'},
        {'node':'InitSet','name':'Emitter.PressureHGrid','type':GRID,'direction':'input'}],
        'links':[{'from':'InitGet','out':'User.PressureHGrid','to':'InitSet','in':'Emitter.PressureHGrid'}]}
    result=json.loads(helper.edit_graph(graph.get_path_name(),json.dumps(spec)));assert result['success'],result
    helper.save_owned_object(script.get_path_name());return helper.save_owned_object(system)

def connect_pressure():
    system=ROOT+'NS_Mud_FromScratch.NS_Mud_FromScratch'
    spec={'nodes':[],'links':[]}
    for index,kind in [(8,'Horizontal'),(9,'Vertical')]:
        name='MudPressure'+kind+'Call'
        spec['nodes'].append({'name':name,'class':'/Script/NiagaraEditor.NiagaraNodeFunctionCall',
            'x':0,'y':index*400,'properties':{'FunctionScript':"/Script/Niagara.NiagaraScript'"+ROOT+'NM_Pressure'+kind+'.NM_Pressure'+kind+"'"}})
        spec['links'] += [{'from':'NiagaraNodeInput_'+str(index),'out':'Input','to':name,'in':'InputMap'},
            {'from':name,'out':'OutputMap','to':'NiagaraNodeOutput_'+str(index),'in':'OutParamMap'}]
    result=json.loads(u.MudAuthoringLibrary.edit_graph(system+':NE_Mud_FromScratch.NiagaraScriptSource_0.NiagaraGraph_0',json.dumps(spec)));assert result['success'],result
    return u.MudAuthoringLibrary.save_owned_object(system)

def transport_fixture():
    return create_module(ROOT+'NM_GridProof', '''Value=0;
#if GPU_SIMULATION
float2 uv;Grid.ExecutionIndexToUnit(uv);Value=float4(uv*0.02,0.2+0.3*uv.x+0.1*uv.y,0.7);
#endif''',[('Grid',GRID,'Emitter.CompositeGrid')],[('Value','float4','StackContext.State')])

def verify_transport_start():
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    actor=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor) if a.get_actor_label()=='Mud_Rebuilt_Simulation')
    comp=actor.get_component_by_class(u.NiagaraComponent)
    rt=u.RenderingLibrary.create_render_target2d(w,32,32,u.TextureRenderTargetFormat.RTF_RGBA32F,u.LinearColor(0,0,0,0),False,True)
    comp.reinitialize_system();comp.set_variable_texture_render_target('User.OutputTexture',rt)
    start=u.GameplayStatics.get_time_seconds(w);handle=[None]
    def capture(dt):
        if u.GameplayStatics.get_time_seconds(w)-start<2:return
        try:
            pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(w,rt,0,0,32,32,False)
            rows=[];error=0
            for i,c in enumerate(pixels):
                x=i%32;y=i//32;uv=[(x+0.5)/32,(y+0.5)/32]
                back=[uv[k]-uv[k]*0.02/32*8 for k in range(2)]
                # D3D linear filter uses eight-bit quantized subtexel weights.
                quant=[]
                for v in back:
                    p=v*32-0.5;lo=int(p//1);f=round((p-lo)*256)/256
                    a=max(0,min(31,lo));b=max(0,min(31,lo+1))
                    quant.append(((a+0.5)*(1-f)+(b+0.5)*f)/32)
                expected=[quant[0]*0.02*0.9,quant[1]*0.02*0.9,(0.2+0.3*quant[0]+0.1*quant[1])*0.9,0.7]
                actual=[c.r,c.g,c.b,c.a];e=max(abs(a-b) for a,b in zip(actual,expected));error=max(error,e)
                if i in [0,511,1023]:rows.append({'index':i,'actual':actual,'expected':expected,'error':e})
            result={'pixels':len(pixels),'max_rgba_error':error,'pass':len(pixels)==1024 and error<2e-6,'samples':rows}
            Path('D:/aco/unreal/Stormfall/Verification/MudSolver/niagara_transport_verification.json').write_text(json.dumps(result,indent=2))
        finally:u.unregister_slate_post_tick_callback(handle[0])
    handle[0]=u.register_slate_post_tick_callback(capture)
    return {'scheduled':True,'target':rt.get_path_name()}

def composite():
    return create_module(ROOT+'NM_Composite',Path('D:/aco/unreal/Stormfall/Tools/MudStudy/Reference/CompositeStage8.hlsl').read_text(),
        [('Destination',GRID,'Emitter.CompositeGrid'),('Advection',GRID,'Emitter.AdvectionGrid'),
         ('Pressure',GRID,'Emitter.PressureGrid'),('Painter',GRID,'Emitter.PainterGrid'),
         ('PainterTexture',GRID,'Emitter.PainterTextureGrid'),
         ('DensityNoiseTexture','/Script/Niagara.NiagaraDataInterfaceTexture','User.DensityNoiseTexture'),
         ('AmplitudeNoiseTexture','/Script/Niagara.NiagaraDataInterfaceTexture','User.AmplitudeNoiseTexture'),
         ('AmplitudeNoiseEnabled','bool','User.AmplitudeNoiseEnabled'),('SimTime','float','Engine.Time'),
         ('SimSpeed','float','User.SimSpeed'),('WorldOffsetDelta','float2','User.WorldOffsetDelta'),
         ('WorldOffset','float2','User.WorldOffset'),('AreaClamp','bool','User.AreaClamp'),
         ('EraserStrength','float','User.EraserStrength'),('DensityAccumulation','float','User.DensityAccumulation'),
         ('VeloFromBrushMotion','float','User.VeloFromBrushMotion'),('VelocityClamp','float','User.VelocityClamp'),
         ('WetFeedback','float','User.WetFeedback')],[('Value','float4','StackContext.State')])

def amplitude_parameters():
    system=ROOT+'NS_Mud_FromScratch.NS_Mud_FromScratch'
    for name,typ,value in [('User.AmplitudeNoiseEnabled','bool','(Value=-1)'),
        ('User.AmplitudeNoiseTexture','/Script/Niagara.NiagaraDataInterfaceTexture',json.dumps({'Texture':"/Script/Engine.Texture2D'/Game/FluidNinjaLive/Core/Assets/T_NoiseTemplate1_128px.T_NoiseTemplate1_128px'"}))]:
        result=json.loads(u.MudAuthoringLibrary.add_user_parameter(system,name,typ,value));assert result['success'],result
    return u.MudAuthoringLibrary.save_owned_object(system)

def composite_parameters():
    system=ROOT+'NS_Mud_FromScratch.NS_Mud_FromScratch';helper=u.MudAuthoringLibrary
    params=[('User.WorldOffset','float2','(X=0,Y=0)'),('User.EraserStrength','float','0'),
        ('User.DensityAccumulation','float','1.217'),('User.VeloFromBrushMotion','float','8'),
        ('User.VelocityClamp','float','50'),('User.WetFeedback','float','0.93'),
        ('User.DensityNoiseTexture','/Script/Niagara.NiagaraDataInterfaceTexture',json.dumps({'Texture':"/Script/Engine.Texture2D'/Game/FluidNinjaLive/Core/Assets/T_Noise3_128px.T_Noise3_128px'"})),
        ('User.PainterTextureGrid',GRID,json.dumps({'NumCellsX':'32','NumCellsY':'32','NumAttributes':'4','SetGridFromMaxAxis':'false','WorldBBoxSize':'(X=20,Y=20)','bOverrideFormat':'true','OverrideBufferFormat':'Float'}))]
    for name,typ,value in params:
        result=json.loads(helper.add_user_parameter(system,name,typ,typed_default(typ,value)));assert result['success'],result
    script=u.load_asset(ROOT+'NM_GridInit');graph=u.find_object(u.find_object(script,'NiagaraScriptSource_0'),'NiagaraGraph_0')
    spec={'pins':[{'node':'InitGet','name':'User.PainterTextureGrid','type':GRID,'direction':'output'},
        {'node':'InitSet','name':'Emitter.PainterTextureGrid','type':GRID,'direction':'input'}],
        'links':[{'from':'InitGet','out':'User.PainterTextureGrid','to':'InitSet','in':'Emitter.PainterTextureGrid'}]}
    result=json.loads(helper.edit_graph(graph.get_path_name(),json.dumps(spec)));assert result['success'],result
    helper.save_owned_object(script.get_path_name());return helper.save_owned_object(system)

def connect_composite():
    system=ROOT+'NS_Mud_FromScratch.NS_Mud_FromScratch'
    spec={'nodes':[{'name':'MudCompositeCall','class':'/Script/NiagaraEditor.NiagaraNodeFunctionCall',
        'x':0,'y':4200,'properties':{'FunctionScript':"/Script/Niagara.NiagaraScript'"+ROOT+"NM_Composite.NM_Composite'"}}],
        'links':[{'from':'NiagaraNodeInput_10','out':'Input','to':'MudCompositeCall','in':'InputMap'},
                 {'from':'MudCompositeCall','out':'OutputMap','to':'NiagaraNodeOutput_10','in':'OutParamMap'}]}
    result=json.loads(u.MudAuthoringLibrary.edit_graph(system+':NE_Mud_FromScratch.NiagaraScriptSource_0.NiagaraGraph_0',json.dumps(spec)));assert result['success'],result
    return u.MudAuthoringLibrary.save_owned_object(system)

def painter():
    tools=Path('D:/aco/unreal/Stormfall/Tools/MudStudy')
    shape=(tools/'Reference/BrushShapeStage5b.hlsl').read_text().replace('return float3(kernel,mask,radius);','')
    packing=(tools/'Reference/StrokePackingStage5c.hlsl').read_text().replace('return OutputAlpha>0.5 ? float3(opacity,opacity,opacity) : result;','')
    packing=packing.replace('float velocityWeight=pow(max(mask-feedback*0.1,0)', 'float velocityWeight=pow(max((strokeIndex==0?mask:field)-feedback*0.1,0)')
    header='''Value=0;
#if GPU_SIMULATION
float2 UV;Grid.ExecutionIndexToUnit(UV);
int nx,ny;Grid.GetNumCells(nx,ny);float2 Aspect=float2(nx,ny)/max(nx,ny);
float2 WorldExtents=float2(2000,2000),OffsetDelta=-WorldOffsetDelta;
float4 accumulator=0;
int count;Positions.Length(count);
int strokeIndex=0;
// AutoAdjustNeighborCellNumber uses world centimetres / 100 for this 20m preset.
float2 neighborCenter=(floor(UV*20)+0.5)/20;
for(int index=0;index<count;index++){
float4 positionRecord,previousRecord,velocityRecord;
Tracker.GetPreviousVector4Value<Attribute=TrackedPosition>(index,0,positionRecord);
Tracker.GetPreviousVector4Value<Attribute=TrackedPrevious>(index,0,previousRecord);
Tracker.GetPreviousVector4Value<Attribute=TrackedVelocity>(index,0,velocityRecord);
float2 Position=positionRecord.xy,PreviousPosition=previousRecord.xy;
float PositionZ=positionRecord.z,ObjectSize=positionRecord.w;
// Match Hash-1's active interaction volume and Hash-2's local candidate list.
if(any(positionRecord.xy<=0)||any(positionRecord.xy>=1)||PositionZ<0.475||PositionZ>0.525)continue;
float2 neighborSegment=Position-PreviousPosition;
float segmentT=saturate(dot(neighborCenter-PreviousPosition,neighborSegment)/max(dot(neighborSegment,neighborSegment),1e-20));
float neighborDistance=length(neighborCenter-(PreviousPosition+neighborSegment*segmentT));
float neighborRadius=ObjectSize*0.01;
if(round((neighborDistance-neighborRadius)*5)/5>=2*neighborRadius)continue;
if(strokeIndex>=256)break;
float3 Velocity=velocityRecord.xyz;float Age=velocityRecord.w;
float VelocityClamp=2,NegativePuncture=0,Puncture=0.05,BrushSize=1;
float InterpolationLimit=100,Interpolate=1,Hardness=0,HardnessBySize=0;
float ZFadeScale=5,FadeByZ=0,FieldHeight=0;
float VelocityPower=1.6,VelocityZMultiplier=1,VelocityXYMultiplier=1;
float SlowVelocityThreshold=0.4,BrushStrength=1,DensityEnable=1,InputFeedback=0.05;
float2 noiseUV=UV+WorldOffset;
float4 velocityNoiseSample,densityNoiseSample;
NoiseTexture.SampleTexture2D(noiseUV*30+SimTime*0.1,0,velocityNoiseSample);
NoiseTexture.SampleTexture2D(noiseUV*3+trunc(SimTime*40)*0.1,0,densityNoiseSample);
float2 VelocityNoise=(velocityNoiseSample.xy-0.5)*0.1*VelocityNoiseAmount;
float DensityNoise=max(pow(max(densityNoiseSample.r,0),2),1-DensityNoiseAmount);
'''
    footer='''
if(strokeIndex>0)opacity=saturate(density+10*density*pow(1-InputFeedback,3));
// SelectivelyKillDensity is initialized to 1 before entering the loop.
// With SimplePainterMode=false and ForceAdditiveStrokeBlending=false,
// the original takes TranslucentBlend even for the first input stroke.
accumulator.xyz=result*opacity+accumulator.xyz*(1-opacity);
accumulator.w=max(accumulator.w,opacity);
strokeIndex++;
}
float4 history;Grid.SamplePreviousGridVector4Value<Attribute=State>(UV+WorldOffsetDelta,history);
if(strokeIndex==0)accumulator=float4(0,0,0,pow(0.95,3));
// Runtime GPU inspection: InputFeedback is .05 after preset initialization.
float3 painted=accumulator.xyz*accumulator.w+history.xyz*(1-accumulator.w);
float4 mesh;Sdf.SamplePreviousGridVector4Value<Attribute=State>(UV,mesh);
painted.xy=mesh.xy*mesh.z+painted.xy*(1-mesh.z);painted.z=max(mesh.z,painted.z);
float edgeValue=saturate(100-0.01-max(abs(UV.x*200-100),abs(UV.y*200-100)));
Value=float4(painted,mesh.w)*(edgeValue>=1?1:0);
#endif'''
    array='/Script/Niagara.NiagaraDataInterfaceArrayFloat4'
    return create_module(ROOT+'NM_Painter',header+shape+packing+footer,
        [('Grid',GRID,'Emitter.PainterGrid'),('Sdf',GRID,'Emitter.SdfGrid'),('Tracker',GRID,'Emitter.TrackingGrid'),
         ('Positions',array,'User.BrushWorldPositions'),
         ('NoiseTexture','/Script/Niagara.NiagaraDataInterfaceTexture','User.BrushNoiseTexture'),
         ('VelocityNoiseAmount','float','User.BrushVelocityNoise'),('DensityNoiseAmount','float','User.BrushDensityNoise'),
         ('WorldOffsetDelta','float2','User.WorldOffsetDelta'),('WorldOffset','float2','User.WorldOffset'),
         ('SimTime','float','Engine.Time')],[('Value','float4','StackContext.State')])

def painter_parameters():
    system=ROOT+'NS_Mud_FromScratch.NS_Mud_FromScratch';helper=u.MudAuthoringLibrary
    array='/Script/Niagara.NiagaraDataInterfaceArrayFloat4'
    for name,typ,value in [('User.BrushVelocityNoise','float','(Value=0.5)'),('User.BrushDensityNoise','float','(Value=0.4)'),
        ('User.BrushPositions',array,'{}'),('User.BrushPrevious',array,'{}'),('User.BrushVelocities',array,'{}'),
        ('User.BrushNoiseTexture','/Script/Niagara.NiagaraDataInterfaceTexture',json.dumps({'Texture':"/Script/Engine.Texture2D'/Game/FluidNinjaLive/Core/Assets/T_NoiseTemplate2.T_NoiseTemplate2'"}))]:
        result=json.loads(helper.add_user_parameter(system,name,typ,value));assert result['success'],result
    return helper.save_owned_object(system)

def connect_painter():
    system=ROOT+'NS_Mud_FromScratch.NS_Mud_FromScratch'
    spec={'nodes':[{'name':'MudPainterCall','class':'/Script/NiagaraEditor.NiagaraNodeFunctionCall',
        'x':0,'y':4600,'properties':{'FunctionScript':"/Script/Niagara.NiagaraScript'"+ROOT+"NM_Painter.NM_Painter'"}}],
        'links':[{'from':'NiagaraNodeInput_11','out':'Input','to':'MudPainterCall','in':'InputMap'},
                 {'from':'MudPainterCall','out':'OutputMap','to':'NiagaraNodeOutput_11','in':'OutParamMap'}]}
    result=json.loads(u.MudAuthoringLibrary.edit_graph(system+':NE_Mud_FromScratch.NiagaraScriptSource_0.NiagaraGraph_0',json.dumps(spec)));assert result['success'],result
    return u.MudAuthoringLibrary.save_owned_object(system)

def sdf():
    return create_module(ROOT+'NM_Sdf',Path('D:/aco/unreal/Stormfall/Tools/MudStudy/Reference/SdfStage8.hlsl').read_text(),
        [('Grid',GRID,'Emitter.SdfGrid'),('Query','/Script/Niagara.NiagaraDataInterfaceRigidMeshCollisionQuery','User.SdfQuery'),
         ('SimCenter','position','User.SimCenter'),('DeltaTime','float','Engine.DeltaTime')],[('Value','float4','StackContext.State')])

def sdf_parameters():
    system=ROOT+'NS_Mud_FromScratch.NS_Mud_FromScratch';helper=u.MudAuthoringLibrary
    for name,typ,value in [('User.SimCenter','position','(X=-3500,Y=15000,Z=-500)'),
        ('User.SdfQuery','/Script/Niagara.NiagaraDataInterfaceRigidMeshCollisionQuery',json.dumps({'ActorTags':'(SDFSource)','GlobalSearchAllowed':'true','GlobalSearchForced':'true'})),
        ('User.SdfGrid',GRID,json.dumps({'NumCellsX':'32','NumCellsY':'32','NumAttributes':'4','SetGridFromMaxAxis':'false','WorldBBoxSize':'(X=20,Y=20)','bOverrideFormat':'true','OverrideBufferFormat':'Float'}))]:
        result=json.loads(helper.add_user_parameter(system,name,typ,typed_default(typ,value)));assert result['success'],result
    script=u.load_asset(ROOT+'NM_GridInit');graph=u.find_object(u.find_object(script,'NiagaraScriptSource_0'),'NiagaraGraph_0')
    spec={'pins':[{'node':'InitGet','name':'User.SdfGrid','type':GRID,'direction':'output'},
        {'node':'InitSet','name':'Emitter.SdfGrid','type':GRID,'direction':'input'}],
        'links':[{'from':'InitGet','out':'User.SdfGrid','to':'InitSet','in':'Emitter.SdfGrid'}]}
    result=json.loads(helper.edit_graph(graph.get_path_name(),json.dumps(spec)));assert result['success'],result
    helper.save_owned_object(script.get_path_name());return helper.save_owned_object(system)

def painter_texture():
    return create_module(ROOT+'NM_PainterTexture','''Value=0;
#if GPU_SIMULATION
float2 uv;Grid.ExecutionIndexToUnit(uv);
float4 paint,bitmap;
Painter.SamplePreviousGridVector4Value<Attribute=State>(uv,paint);
Bitmap.SampleTexture2D(uv+WorldOffset,0,bitmap);
Value=float4(0,0,(1-saturate(paint.z))*0.025*bitmap.r,0);
#endif''', [('Grid',GRID,'Emitter.PainterTextureGrid'),('Painter',GRID,'Emitter.PainterGrid'),
        ('Bitmap','/Script/Niagara.NiagaraDataInterfaceTexture','User.DensityBitmap'),
        ('WorldOffset','float2','User.WorldOffset')],[('Value','float4','StackContext.State')])

def bitmap_parameter():
    system=ROOT+'NS_Mud_FromScratch.NS_Mud_FromScratch';helper=u.MudAuthoringLibrary
    result=json.loads(helper.add_user_parameter(system,'User.DensityBitmap','/Script/Niagara.NiagaraDataInterfaceTexture',
        json.dumps({'Texture':"/Script/Engine.Texture2D'/Game/FluidNinjaLive/Textures/T_Crumple_MultiLevel.T_Crumple_MultiLevel'"})));assert result['success'],result
    return helper.save_owned_object(system)

def connect_stage(module,index):
    system=ROOT+'NS_Mud_FromScratch.NS_Mud_FromScratch';name='Mud'+module+'Call'
    spec={'nodes':[{'name':name,'class':'/Script/NiagaraEditor.NiagaraNodeFunctionCall',
        'x':0,'y':index*400,'properties':{'FunctionScript':"/Script/Niagara.NiagaraScript'"+ROOT+'NM_'+module+'.NM_'+module+"'"}}],
        'links':[{'from':'NiagaraNodeInput_'+str(index),'out':'Input','to':name,'in':'InputMap'},
                 {'from':name,'out':'OutputMap','to':'NiagaraNodeOutput_'+str(index),'in':'OutParamMap'}]}
    result=json.loads(u.MudAuthoringLibrary.edit_graph(system+':NE_Mud_FromScratch.NiagaraScriptSource_0.NiagaraGraph_0',json.dumps(spec)));assert result['success'],result
    return u.MudAuthoringLibrary.save_owned_object(system)

def verify_chain_start():
    import math
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    actor=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor) if a.get_actor_label()=='Mud_Rebuilt_Simulation')
    comp=actor.get_component_by_class(u.NiagaraComponent)
    rt=u.RenderingLibrary.create_render_target2d(w,32,32,u.TextureRenderTargetFormat.RTF_RGBA32F,u.LinearColor(0,0,0,0),False,True)
    comp.reinitialize_system();comp.set_variable_texture_render_target('User.OutputTexture',rt)
    start=u.GameplayStatics.get_time_seconds(w);state={'step':0,'samples':[],'images':[]}
    def arrays(pos,prev,vel):
        for name,value in [('BrushPositions',pos),('BrushPrevious',prev),('BrushVelocities',vel)]:
            u.NiagaraDataInterfaceArrayFunctionLibrary.set_niagara_array_vector4(comp,'User.'+name,value)
    arrays([],[],[])
    def capture(dt):
        elapsed=u.GameplayStatics.get_time_seconds(w)-start
        if elapsed<(state['step']+1)*3:return
        try:
            pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(w,rt,0,0,32,32,False)
            image=[[p.r,p.g,p.b,p.a] for p in pixels];finite=all(math.isfinite(v) for p in image for v in p)
            row={'phase':['baseline','brush_active','brush_released'][state['step']],
                'world_time':elapsed,'finite':finite,'pixel_count':len(image),
                'min_rgba':[min(p[k] for p in image) for k in range(4)],'max_rgba':[max(p[k] for p in image) for k in range(4)]}
            if state['images']:
                baseline=state['images'][0];diff=[max(abs(a-b) for a,b in zip(p,q)) for p,q in zip(image,baseline)]
                row['changed_pixels_from_baseline']=sum(d>1e-5 for d in diff);row['max_delta_from_baseline']=max(diff)
            state['samples'].append(row);state['images'].append(image)
            if state['step']==0:
                arrays([u.Vector4(0.55,0.5,0.5,0.05)],[u.Vector4(0.4,0.5,0.5,0.05)],[u.Vector4(0.3,0.05,0,2)])
            elif state['step']==1:arrays([],[],[])
            state['step']+=1
            if state['step']==3:
                passed=all(r['finite'] and r['pixel_count']==1024 for r in state['samples']) and state['samples'][1]['changed_pixels_from_baseline']>0
                result={'scope':'Independent full-chain smoke test, not original-vs-rebuild equivalence','pass':passed,'samples':state['samples'],'images':state['images']}
                Path('D:/aco/unreal/Stormfall/Verification/MudSolver/niagara_chain_smoke.json').write_text(json.dumps(result,indent=2))
                u.unregister_slate_post_tick_callback(state['handle'])
        except Exception as e:
            u.unregister_slate_post_tick_callback(state['handle'])
            Path('D:/aco/unreal/Stormfall/Verification/MudSolver/niagara_chain_smoke.json').write_text(json.dumps({'pass':False,'error':str(e)}))
    state['handle']=u.register_slate_post_tick_callback(capture)
    return {'scheduled':True,'world_seconds':9}

def save_solver():
    assert u.EditorAssetLibrary.save_directory(ROOT,False,True)
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    return {'saved':'owned Niagara assets and copied map'}

def setup_runtime_actor():
    levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert levels.load_level('/Game/MudStudy/Maps/L_Mud_RealtimeCompare')
    sub=u.get_editor_subsystem(u.EditorActorSubsystem)
    cls=u.load_class(None,'/Script/MudRuntime.MudRebuildActor');assert cls,'MudRuntime plugin did not load'
    old=next((a for a in sub.get_all_level_actors() if a.get_actor_label()=='Mud_Rebuilt_Runtime'),None)
    actor=old or sub.spawn_actor_from_class(cls,u.Vector(-3500,15000,-500),u.Rotator(pitch=0,yaw=0,roll=0))
    actor.set_actor_rotation(u.Rotator(pitch=0,yaw=0,roll=0),False)
    actor.set_actor_label('Mud_Rebuilt_Runtime')
    actor.set_editor_property('solver',u.load_asset(ROOT+'NS_Mud_FromScratch'))
    material=u.load_asset('/Game/MudStudy/Rebuild/Materials/MI_Surface_Rebuilt');assert material
    actor.set_editor_property('surface_material',material)
    proof=next((a for a in sub.get_all_level_actors() if a.get_actor_label()=='Mud_Rebuilt_Simulation'),None)
    if proof:
        comp=proof.get_component_by_class(u.NiagaraComponent);comp.deactivate();comp.set_editor_property('auto_activate',False)
    assert levels.save_current_level()
    return {'actor':actor.get_path_name(),'class':cls.get_path_name(),'material':material.get_path_name()}

def inspect_runtime():
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    cls=u.load_class(None,'/Script/MudRuntime.MudRebuildActor')
    actor=u.GameplayStatics.get_all_actors_of_class(w,cls)[0]
    output=actor.get_editor_property('output');mid=actor.get_editor_property('surface_mid');comp=actor.get_editor_property('simulation')
    assert output and mid
    sample=[]
    for x,y in [(0,0),(128,128),(256,256),(384,384),(511,511)]:
        c=u.RenderingLibrary.read_render_target_raw_pixel(w,output,x,y,False)
        sample.append({'xy':[x,y],'rgba':[c.r,c.g,c.b,c.a]})
    result={'actor':actor.get_path_name(),'output':output.get_path_name(),'size':[output.get_editor_property('size_x'),output.get_editor_property('size_y')],
        'active':comp.is_active(),'material_output_matches':mid.get_texture_parameter_value('VelocityDensityBuffer')==output,'samples':sample}
    Path('D:/aco/unreal/Stormfall/Verification/MudSolver/runtime_actor_inspection.json').write_text(json.dumps(result,indent=2))
    return result

def configure_resolution(resolution=512):
    assert resolution in [32,128,256,512,1024,2048]
    system=ROOT+'NS_Mud_FromScratch.NS_Mud_FromScratch';helper=u.MudAuthoringLibrary
    for name in ['CompositeGrid','AdvectionGrid','DivergenceGrid','PainterGrid','PressureGrid','PressureHGrid','PainterTextureGrid','SdfGrid']:
        settings=json.dumps({'NumCellsX':str(resolution),'NumCellsY':str(resolution),'NumAttributes':'4','SetGridFromMaxAxis':'false','WorldBBoxSize':'(X=20,Y=20)','bOverrideFormat':'true','OverrideBufferFormat':'Float'})
        result=json.loads(helper.add_user_parameter(system,'User.'+name,GRID,settings));assert result['success'],result
    return helper.save_owned_object(system)

def configure_original_grid_layout():
    # Captured from the live original with InspectGpuInputs, not inferred from RT sizes.
    layout={'CompositeGrid':(2048,'HalfFloat'),'AdvectionGrid':(2048,'HalfFloat'),
        'DivergenceGrid':(2048,'HalfFloat'),'PressureGrid':(2048,'HalfFloat'),
        'PressureHGrid':(2048,'HalfFloat'),'PainterGrid':(1024,'HalfFloat'),
        'PainterTextureGrid':(1024,'HalfFloat'),'SdfGrid':(512,'Float')}
    system=ROOT+'NS_Mud_FromScratch.NS_Mud_FromScratch';helper=u.MudAuthoringLibrary
    for name,(size,fmt) in layout.items():
        settings=json.dumps({'NumCellsX':str(size),'NumCellsY':str(size),'NumAttributes':'4',
            'SetGridFromMaxAxis':'false','WorldBBoxSize':'(X=2000,Y=2000)','bOverrideFormat':'true','OverrideBufferFormat':fmt})
        result=json.loads(helper.add_user_parameter(system,'User.'+name,GRID,settings));assert result['success'],result
    # Composite clamp is distinct from the brush's local clamp of 2.
    result=json.loads(helper.add_user_parameter(system,'User.VelocityClamp','float','(Value=50)'));assert result['success'],result
    sub=u.get_editor_subsystem(u.EditorActorSubsystem)
    runtime=next(a for a in sub.get_all_level_actors() if a.get_actor_label()=='Mud_Rebuilt_Runtime')
    runtime.set_editor_property('output_resolution',2048)
    runtime.set_actor_rotation(u.Rotator(pitch=0,yaw=0,roll=0),False)
    helper.save_owned_object(system)
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    return layout
