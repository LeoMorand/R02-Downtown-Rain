"""Stage 1: independent UV/B/height-normal materials in the learning map only.

Original material functions are not called. Snapshot is captured from original
simulation; this stage does not rebuild the solver, POM, Flow or final mixing.
"""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/aco/unreal/Stormfall/Verification/MudRebuildStage1')
PACKAGE='/Game/MudStudy/Rebuild/Materials'
SNAPSHOT='/Game/MudStudy/Rebuild/Textures/T_SourceVelocityDensity_20261025'
HLSL='''float h0 = Texture2DSample(Height, HeightSampler, UV).b;
float hx = Texture2DSample(Height, HeightSampler, UV + float2(Offset,0)).b;
float hy = Texture2DSample(Height, HeightSampler, UV + float2(0,Offset)).b;
return float3(-(hx-h0)*Strength, -(hy-h0)*Strength, 1);'''
MATS={}

def world():
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if w.get_name()!='L_Mud_FromScratch':raise RuntimeError('Open learning map first; original map is protected')
    return w

class Graph:
    def __init__(self,name,unlit=True):
        self.path=PACKAGE+'/'+name
        self.mat=u.load_asset(self.path) if u.EditorAssetLibrary.does_asset_exist(self.path) else u.AssetToolsHelpers.get_asset_tools().create_asset(name,PACKAGE,u.Material,u.MaterialFactoryNew())
        # UE 5.8 DeleteAllMaterialExpressions range-iterates the same array that
        # DeleteMaterialExpression removes from, so one pass can skip entries.
        # This stage owns these assets and creates <=26 nodes per asset. Repeat
        # enough passes to clear even a heavily repeated earlier stage build.
        for unused in range(12):
            u.MaterialEditingLibrary.delete_all_material_expressions(self.mat)
        self.mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT if unlit else u.MaterialShadingModel.MSM_DEFAULT_LIT)
        self.nodes={};self.links=[];self.outputs=[]
    def node(self,name,kind,**props):
        n=u.MaterialEditingLibrary.create_material_expression(self.mat,getattr(u,'MaterialExpression'+kind),-1000+(len(self.nodes)%6)*230,(len(self.nodes)//6)*220)
        n.set_editor_property('desc',name)
        for k,v in props.items():n.set_editor_property(k,v)
        self.nodes[name]=n;return name
    def link(self,a,b,pin='',out=''):
        assert u.MaterialEditingLibrary.connect_material_expressions(self.nodes[a],out,self.nodes[b],pin),(a,out,b,pin)
        self.links.append([a,out,b,pin])
    def output(self,a,prop,out=''):
        assert u.MaterialEditingLibrary.connect_material_property(self.nodes[a],out,getattr(u.MaterialProperty,'MP_'+prop)),(a,prop,out)
        self.outputs.append([a,out,prop])
    def finish(self):
        u.MaterialEditingLibrary.layout_material_expressions(self.mat)
        u.MaterialEditingLibrary.recompile_material(self.mat)
        assert u.EditorAssetLibrary.save_loaded_asset(self.mat)
        return {'path':self.path,'nodes':{k:v.get_class().get_name() for k,v in self.nodes.items()},'connections':self.links,'outputs':self.outputs}

def common(g):
    tex=u.load_asset(SNAPSHOT)
    g.node('UV','TextureCoordinate')
    g.node('FrozenSim','TextureObjectParameter',parameter_name='FrozenVelocityDensity',texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    g.node('Offset','ScalarParameter',parameter_name='NormalOffset',default_value=0.0005)
    g.node('Intensity','ScalarParameter',parameter_name='NormalMultiplier',default_value=40.0)
    g.node('CustomStrengthScale','ScalarParameter',parameter_name='CustomStrengthScale',default_value=1.0)
    g.node('ScaledIntensity','Multiply');g.link('Intensity','ScaledIntensity','A');g.link('CustomStrengthScale','ScaledIntensity','B')
    custom_inputs=[]
    for name in ['Height','UV','Offset','Strength']:
        pin=u.CustomInput()
        pin.set_editor_property('input_name',name)
        custom_inputs.append(pin)
    g.node('IndependentNormal','Custom',code=HLSL,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,
        inputs=custom_inputs)
    for a,p in [('FrozenSim','Height'),('UV','UV'),('Offset','Offset'),('ScaledIntensity','Strength')]:g.link(a,'IndependentNormal',p)

def build():
    world();ROOT.mkdir(exist_ok=True)
    assert u.load_asset(SNAPSHOT),'Snapshot missing'
    results=[]
    g=Graph('M_Rebuild_UV');g.node('UV','TextureCoordinate');g.node('Zero','Constant',r=0.0);g.node('UVColor','AppendVector')
    g.link('UV','UVColor','A');g.link('Zero','UVColor','B');g.output('UVColor','EMISSIVE_COLOR');results.append(g.finish())
    g=Graph('M_Rebuild_DensityB');g.node('UV','TextureCoordinate');g.node('ReadSim','TextureSampleParameter2D',parameter_name='FrozenVelocityDensity',texture=u.load_asset(SNAPSHOT),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    g.link('UV','ReadSim','UVs');g.output('ReadSim','EMISSIVE_COLOR','B');results.append(g.finish())
    g=Graph('M_Rebuild_DensityNormal',False);common(g)
    g.node('Brown','Constant3Vector',constant=u.LinearColor(0.14536,0.073858,0.040263,1));g.output('Brown','BASE_COLOR');g.output('IndependentNormal','NORMAL')
    g.node('Roughness','Constant',r=0.1);g.output('Roughness','ROUGHNESS');g.node('Specular','Constant',r=0.2);g.output('Specular','SPECULAR');results.append(g.finish())
    g=Graph('M_Rebuild_NormalDifference');common(g)
    g.node('Zero','Constant',r=0.0)
    for name,a,b in [('OffsetX','Offset','Zero'),('OffsetY','Zero','Offset')]:
        g.node(name,'AppendVector');g.link(a,name,'A');g.link(b,name,'B')
    for axis in ['X','Y']:
        g.node('UV'+axis,'Add');g.link('UV','UV'+axis,'A');g.link('Offset'+axis,'UV'+axis,'B')
    for name,uv in [('H0','UV'),('HX','UVX'),('HY','UVY')]:
        g.node(name,'TextureSample',texture=u.load_asset(SNAPSHOT),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        g.link('FrozenSim',name,'Tex');g.link(uv,name,'UVs')
    for axis in ['X','Y']:
        g.node('Delta'+axis,'Subtract');g.link('H'+axis,'Delta'+axis,'A','B');g.link('H0','Delta'+axis,'B','B')
        g.node('Slope'+axis,'Multiply');g.link('Delta'+axis,'Slope'+axis,'A');g.link('Intensity','Slope'+axis,'B')
        g.node('Basis'+axis,'Constant2Vector',r=1.0 if axis=='X' else 0.0,g=0.0 if axis=='X' else 1.0)
        g.node('Tangent'+axis,'AppendVector');g.link('Basis'+axis,'Tangent'+axis,'A');g.link('Slope'+axis,'Tangent'+axis,'B')
    g.node('OriginalCross','CrossProduct');g.link('TangentX','OriginalCross','A');g.link('TangentY','OriginalCross','B')
    g.node('Difference','Subtract');g.link('OriginalCross','Difference','A');g.link('IndependentNormal','Difference','B')
    g.node('AbsDifference','Abs');g.link('Difference','AbsDifference');g.output('AbsDifference','EMISSIVE_COLOR');results.append(g.finish())
    (ROOT/'build_manifest.json').write_text(json.dumps({'snapshot':SNAPSHOT,'hlsl':HLSL,'materials':results},ensure_ascii=False,indent=2),encoding='utf-8')
    return {'materials':[{ 'path':r['path'],'nodes':len(r['nodes'])} for r in results]}

def layout():
    w=world();sub=u.get_editor_subsystem(u.EditorActorSubsystem)
    actors={a.get_actor_label():a for a in sub.get_all_level_actors()}
    panels=[('Study_01_UV',-700,0,'M_Rebuild_UV'),('Study_02_DensityB',0,0,'M_Rebuild_DensityB'),('MudSurface',700,0,'M_Rebuild_DensityNormal'),('Study_04_NormalDifference',0,800,'M_Rebuild_NormalDifference')]
    for label,x,y,name in panels:
        a=actors.get(label)
        if a is None:a=sub.spawn_actor_from_class(u.StaticMeshActor,u.Vector(x,y,5));a.set_actor_label(label)
        a.set_actor_location(u.Vector(x,y,5),False,False)
        mesh=a.get_component_by_class(u.StaticMeshComponent)
        mesh.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'))
        mesh.set_relative_scale3d(u.Vector(6,6,1))
        mesh.set_material(0,u.load_asset(PACKAGE+'/'+name))
    captions=[('Stage1_Label_UV',-700,0,'01  UV'),('Stage1_Label_B',0,0,'02  Density B'),
              ('Stage1_Label_Normal',700,0,'03  Density normal'),('Stage1_Label_Diff',0,800,'04  Difference: black = match')]
    for label,x,y,text in captions:
        a=actors.get(label)
        if a is None:a=sub.spawn_actor_from_class(u.TextRenderActor,u.Vector(x,y-345,65));a.set_actor_label(label)
        a.set_actor_location(u.Vector(x,y-430,50),False,False)
        a.set_actor_rotation(u.Rotator(pitch=0,yaw=-90,roll=0),False)
        comp=a.get_component_by_class(u.TextRenderComponent)
        comp.set_text(u.Text(text));comp.set_world_size(30)
        comp.set_horizontal_alignment(u.HorizTextAligment.EHTA_CENTER)
    # The original source map is never saved by this script.
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    return {'map':w.get_path_name(),'panels':[p[0] for p in panels]}

def collect():
    u.SystemLibrary.collect_garbage()
    return {'collected':True}

def reload_saved():
    names=['M_Rebuild_UV','M_Rebuild_DensityB','M_Rebuild_DensityNormal','M_Rebuild_NormalDifference']
    packages=[u.load_asset(PACKAGE+'/'+n).get_outer() for n in names]
    result=u.EditorLoadingAndSavingUtils.reload_packages(packages,u.ReloadPackagesInteractionMode.ASSUME_POSITIVE)
    return {'reload':str(result)}

def verify_gpu():
    w=world();mat=u.load_asset(PACKAGE+'/M_Rebuild_NormalDifference')
    rt=u.RenderingLibrary.create_render_target2d(w,32,32,u.TextureRenderTargetFormat.RTF_RGBA16F,u.LinearColor(0,0,0,1),False,False)
    mid=u.MaterialLibrary.create_dynamic_material_instance(w,mat)
    rows=[]
    for scale in [1.0,0.0]:
        mid.set_scalar_parameter_value('CustomStrengthScale',scale)
        u.RenderingLibrary.draw_material_to_render_target(w,rt,mid)
        # With origin 0, engine's MaxX/MaxY-as-width bug does not enlarge this area.
        pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(w,rt,0,0,32,32,False)
        assert len(pixels)==1024,len(pixels)
        mx=max(max(abs(c.r),abs(c.g),abs(c.b)) for c in pixels)
        rows.append({'custom_strength_scale':scale,'pixels':len(pixels),'max_abs_rgb_difference':mx})
    result={'scope':'GPU graph-vs-independent-HLSL density normal, no POM; frozen source snapshot; 32x32 UV raster',
        'readbacks':rows,'pass':rows[0]['max_abs_rgb_difference']<0.0001 and rows[1]['max_abs_rgb_difference']>0.001}
    (ROOT/'gpu_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    assert result['pass'],result
    return result
