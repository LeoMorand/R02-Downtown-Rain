"""Keep input history inside the fixed-step Niagara simulation."""
import sys,json
from pathlib import Path
import unreal as u
sys.path.insert(0,'D:/aco/unreal/Stormfall/Tools/MudStudy')
from niagara_author_stage7 import create_module
ROOT='/Game/MudStudy/Rebuild/Niagara/'
SYSTEM=ROOT+'NS_Mud_FromScratch.NS_Mud_FromScratch'
GRID='/Script/Niagara.NiagaraDataInterfaceGrid2DCollection'

def parameters():
    helper=u.MudAuthoringLibrary
    settings=json.dumps({'NumCellsX':'16384','NumCellsY':'1','NumAttributes':'20','SetGridFromMaxAxis':'false','WorldBBoxSize':'(X=2000,Y=2000)','bOverrideFormat':'true','OverrideBufferFormat':'Float'})
    for name,typ,value in [('User.TrackingGrid',GRID,settings),('User.BrushWorldPositions','/Script/Niagara.NiagaraDataInterfaceArrayFloat4','{}'),
        ('User.BrushRandom','float','(Value=1)'),('User.MotionOffset','float','(Value=0.5)'),('User.TrackingRandomSeed','int','(Value=12345)')]:
        r=json.loads(helper.add_user_parameter(SYSTEM,name,typ,value));assert r['success'],r
    script=u.load_asset(ROOT+'NM_GridInit');graph=u.find_object(u.find_object(script,'NiagaraScriptSource_0'),'NiagaraGraph_0')
    spec={'pins':[{'node':'InitGet','name':'User.TrackingGrid','type':GRID,'direction':'output'},
        {'node':'InitSet','name':'Emitter.TrackingGrid','type':GRID,'direction':'input'}],
        'links':[{'from':'InitGet','out':'User.TrackingGrid','to':'InitSet','in':'Emitter.TrackingGrid'}]}
    r=json.loads(helper.edit_graph(graph.get_path_name(),json.dumps(spec)));assert r['success'],r
    helper.save_owned_object(script.get_path_name());return helper.save_owned_object(SYSTEM)

def build():
    return create_module(ROOT+'NM_Tracking',Path('D:/aco/unreal/Stormfall/Tools/MudStudy/Reference/TrackingStage11.hlsl').read_text(),
        [('Grid',GRID,'Emitter.TrackingGrid'),('Inputs','/Script/Niagara.NiagaraDataInterfaceArrayFloat4','User.BrushWorldPositions'),
         ('SimCenter','position','User.SimCenter'),('DeltaTime','float','Engine.DeltaTime'),('BrushRandom','float','User.BrushRandom'),
         ('MotionOffset','float','User.MotionOffset'),('RandomSeed','int','User.TrackingRandomSeed')],
        [('Position','float4','StackContext.TrackedPosition'),('Previous','float4','StackContext.TrackedPrevious'),
         ('Velocity','float4','StackContext.TrackedVelocity'),('World','float4','StackContext.TrackedWorld'),
         ('RawVelocity','float4','StackContext.TrackedRawVelocity')])
