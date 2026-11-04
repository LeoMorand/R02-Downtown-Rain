"""Rebuild the selected material slice; replace FluidNinja functions with HLSL.

Original surface function is used only by reference/difference assets.
"""
import json,re,sys,math
from pathlib import Path
import unreal as u
TOOLS=Path('D:/aco/unreal/Stormfall/Tools/MudStudy')
if str(TOOLS) not in sys.path:sys.path.insert(0,str(TOOLS))
from build_display_stage1 import Graph,world,SNAPSHOT,HLSL as NORMAL_CODE
from build_pom_stage2 import custom,CODE as POM_CODE
from material_equations import Equations
from trace_material import refs
ROOT=Path('D:/aco/unreal/Stormfall/Verification/MudRebuildSurface')
PACKAGE='/Game/MudStudy/Rebuild/Materials'
SURFACE='/Game/FluidNinjaLive/OutputMaterials/Base/MF_NinjaOutput_BaseFunction_SURFACE'
PARAMS=json.loads((TOOLS.parents[1]/'Verification/MudMaterial/resolved_parameters.json').read_text())
FLOW_CODE=(TOOLS/'Reference/FlowStage3.hlsl').read_text()

def output_name(node,index):
    names=u.MaterialEditingLibrary.get_material_expression_output_names(node)
    if index==0:return ''
    assert index<len(names),(node.get_name(),index,names)
    return str(names[index])

def make_instance(name,mat,full=False):
    path=PACKAGE+'/'+name
    mi=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset(name,PACKAGE,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    u.MaterialEditingLibrary.set_material_instance_parent(mi,mat)
    if full:
        for key,value in PARAMS['static'].items():
            u.MaterialEditingLibrary.set_material_instance_static_switch_parameter_value(mi,key,value,u.MaterialParameterAssociation.GLOBAL_PARAMETER,False)
        for key,value in (PARAMS['scalar']|PARAMS['dynamicScalarOverrides']).items():u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi,key,value)
        for key,value in PARAMS['vector'].items():u.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi,key,u.LinearColor(*value))
        for key,value in PARAMS['texture'].items():
            if key not in ['VelocityDensityBuffer','PressureDivergenceBuffer','PaintBuffer'] and value:u.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mi,key,u.load_asset(value))
        u.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mi,'VelocityDensityBuffer',u.load_asset(SNAPSHOT))
    u.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi,'ForceLocalSpace',1)
    u.MaterialEditingLibrary.update_material_instance(mi)
    assert u.EditorAssetLibrary.save_loaded_asset(mi)
    return path

def build():
    world();ROOT.mkdir(exist_ok=True);rows=[]
    g=Graph('M_Surface_Reference',False);g.mat.set_editor_property('two_sided',True);outs=reference(g)
    for slot,prop in [('BaseColor','BASE_COLOR'),('Normal','NORMAL'),('Roughness','ROUGHNESS'),('Specular','SPECULAR')]:g.output(outs[slot][0],prop,outs[slot][1])
    row=g.finish();row['instance']=make_instance('MI_Surface_Reference',g.mat,True);row['pendingNativeDepthConnection']={'expression':g.nodes['OriginalAttributes'].get_name(),'output':'PixelDepthOffset'};rows.append(row)
    g=Graph('M_Surface_Rebuilt',False);g.mat.set_editor_property('two_sided',True)
    g.mat.set_editor_property('used_with_niagara_mesh_particles',True)
    clone=Rebuild(g);outs=clone.outputs()
    for slot,prop in [('BaseColor','BASE_COLOR'),('Normal','NORMAL'),('Roughness','ROUGHNESS'),('Specular','SPECULAR')]:g.output(outs[slot][0],prop,outs[slot][1])
    row=g.finish();row['instance']=make_instance('MI_Surface_Rebuilt',g.mat);row['replacements']=clone.audit;row['pendingNativeDepthConnection']={'expression':g.nodes[outs['PixelDepthOffset'][0]].get_name(),'output':outs['PixelDepthOffset'][1]};rows.append(row)
    g=Graph('M_Surface_Difference');original=reference(g);clone=Rebuild(g);rebuilt=clone.outputs()
    g.node('DebugMode','ScalarParameter',parameter_name='DebugMode',default_value=0)
    code='''if (Mode < 0.5) return abs(C0-C1);
if (Mode < 1.5) return abs(N0-N1);
return float3(abs(R0-R1),abs(S0-S1),abs(P0-P1));'''
    pins=['Mode','C0','C1','N0','N1','R0','R1','S0','S1','P0','P1'];custom(g,'Compare',code,pins)
    g.link('DebugMode','Compare','Mode')
    for short,slot in [('C','BaseColor'),('N','Normal'),('R','Roughness'),('S','Specular'),('P','PixelDepthOffset')]:
        clone.wire(original[slot],'Compare',short+'0');clone.wire(rebuilt[slot],'Compare',short+'1')
    g.output('Compare','EMISSIVE_COLOR');row=g.finish();row['instance']=make_instance('MI_Surface_Difference',g.mat,True);rows.append(row)
    (ROOT/'build_manifest.json').write_text(json.dumps({'scope':__doc__,'materials':rows},indent=2),encoding='utf-8')
    return {'materials':[{'path':r['path'],'nodes':len(r['nodes'])} for r in rows]}

def reference(g):
    g.node('OriginalSurface','MaterialFunctionCall');assert g.nodes['OriginalSurface'].set_material_function(u.load_asset(SURFACE))
    g.node('OriginalAttributes','BreakMaterialAttributes');g.link('OriginalSurface','OriginalAttributes','','MaterialAttributes')
    return {slot:('OriginalAttributes',name) for slot,name in [('BaseColor','BaseColor'),('Normal','Normal'),('Roughness','Roughness'),('Specular','Specular'),('PixelDepthOffset','PixelDepthOffset')]}

def probe_reference():
    world();ROOT.mkdir(exist_ok=True)
    g=Graph('M_Surface_Reference',False);reference(g)
    return {'outputs':[str(x) for x in u.MaterialEditingLibrary.get_material_expression_output_names(g.nodes['OriginalAttributes'])]}

class Rebuild:
    def __init__(self,g):self.g=g;self.e=Equations();self.cache={};self.nodes={};self.audit=[]
    def wire(self,source,target,pin):
        pin={'Exponent':'Exp'}.get(pin,pin)
        names=[str(x) for x in u.MaterialEditingLibrary.get_material_expression_input_names(self.g.nodes[target])]
        if pin=='Input' and names and names[0] in ['None','']:pin=''
        if pin and pin not in names:
            matches=[x for x in names if x.replace(' ','').lower()==pin.replace(' ','').lower()]
            if matches:pin=matches[0]
            elif len(names)==1:pin=''
        try:self.g.link(source[0],target,pin,source[1])
        except AssertionError as exc:raise AssertionError((str(exc),'available_inputs',names))
    def function_args(self,p):
        result={}
        for part in p['FunctionInputs'].split('ExpressionInputId=')[1:]:
            name=re.search(r'InputName="([^"]*)"',part);rr=refs(part)
            if name and rr:result[name[1]]=rr[0]
        return result
    def call(self,key,p,index):
        name=p['MaterialFunction'].split('.')[-1];args=self.function_args(p);g=self.g
        if name=='BreakOutFloat2Components':
            n=key+'_component_'+str(index);g.node(n,'ComponentMask',r=index==0,g=index==1,b=False,a=False)
            self.wire(self.make(*next(iter(args.values()))),n,'');return n,''
        if key in self.nodes:
            node=self.nodes[key]
        elif name=='MF_GetAspect':
            node=key;custom(g,node,'uint w,h; Tex.GetDimensions(w,h); return float2(min((float)w/h,1.0),min((float)h/w,1.0));',['Tex'],u.CustomMaterialOutputType.CMOT_FLOAT2)
            self.wire(self.make(*args['TextureObj']),node,'Tex');self.nodes[key]=node
        elif name.startswith('MF_NormalFromHeightmap'):
            node=key;code=NORMAL_CODE;pins=['Height','UV','Offset','Strength']
            if name=='MF_NormalFromHeightmap':code=code.replace('return float3(', 'return TileScale * float3(');pins+=['TileScale']
            custom(g,node,code,pins)
            for pin,arg in [('Height','Height Map'),('UV','Coordinates'),('Offset','Height Map UV Offset'),('Strength','Normal Map Intensity')]:self.wire(self.make(*args[arg]),node,pin)
            if name=='MF_NormalFromHeightmap':g.node(key+'_tileScale','ScalarParameter',parameter_name='RebuildTileNormalScale',default_value=1);g.link(key+'_tileScale',node,'TileScale')
            self.nodes[key]=node
        elif name=='MF_FlowMapFunction':
            node=key;custom(g,node,FLOW_CODE,['FlowTexture','FlowVector','DensityMultiplier','Strength','Speed','TimeValue','UV'])
            mapping={'FlowTexture':'FlowTargetTexture','FlowVector':'FlowInputVector','DensityMultiplier':'FlowMultiplyByDensity','Strength':'InputFlowStrength','Speed':'FlowSpeed','UV':'UV'}
            for pin,arg in mapping.items():self.wire(self.make(*args[arg]),node,pin)
            g.node(key+'_time','Time');g.link(key+'_time',node,'TimeValue');self.nodes[key]=node
        elif name=='MF_ParallaxOcclusionMappingSimple':
            node=key
            g.node(key+'_view','CameraVectorWS');g.node(key+'_tangent','Transform',transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT);g.link(key+'_view',key+'_tangent')
            g.node(key+'_normal','VertexNormalWS');g.node(key+'_world','WorldPosition');g.node(key+'_forward','MaterialFunctionCall')
            assert g.nodes[key+'_forward'].set_material_function(u.load_asset('/Engine/Functions/Engine_MaterialFunctions02/Utility/CameraDirectionVector'))
            g.node(key+'_min','Constant',r=8);g.node(key+'_scale','ScalarParameter',parameter_name='RebuildHeightScale',default_value=1)
            pins=['Height','UV','HeightRatio','ReferencePlane','MinSteps','MaxSteps','ViewTS','ViewWS','VertexNormal','WorldPos','CameraForward','RebuildHeightScale'];custom(g,node,POM_CODE,pins)
            for pin,arg in [('Height','Heightmap Texture'),('UV','UVs'),('HeightRatio','Height Ratio'),('ReferencePlane','Reference Plane'),('MaxSteps','Max Steps')]:self.wire(self.make(*args[arg]),node,pin)
            for pin,source in [('MinSteps',key+'_min'),('ViewTS',key+'_tangent'),('ViewWS',key+'_view'),('VertexNormal',key+'_normal'),('WorldPos',key+'_world'),('CameraForward',key+'_forward'),('RebuildHeightScale',key+'_scale')]:g.link(source,node,pin)
            self.nodes[key]=node
        else:raise ValueError(('Unhandled function',name))
        if name=='MF_ParallaxOcclusionMappingSimple':
            mask=key+'_port_'+str(index)
            if mask not in g.nodes:g.node(mask,'ComponentMask',r=index==0,g=index==0,b=index==2,a=False);g.link(node,mask)
            assert index in [0,2],index
            return mask,''
        self.audit.append({'source':key,'function':name,'replacement':node})
        return node,''
    def make(self,key,index=0):
        key,index=self.e.resolve(key,index);tag=(key,index)
        if tag in self.cache:return self.cache[tag]
        n=self.e.t.nodes[key];p=n['props'];kind=n['className'].replace('MaterialExpression','');g=self.g
        if kind=='MaterialFunctionCall':result=self.call(key,p,index);self.cache[tag]=result;return result
        if key not in self.nodes:
            props={}
            if kind=='ScalarParameter':props={'parameter_name':p['ParameterName'],'default_value':self.e.t.scalar[p['ParameterName']]}
            elif kind=='VectorParameter':props={'parameter_name':p['ParameterName'],'default_value':u.LinearColor(*PARAMS['vector'][p['ParameterName']])}
            elif kind=='StaticBoolParameter':props={'parameter_name':p['ParameterName'],'default_value':PARAMS['static'][p['ParameterName']]}
            elif kind=='TextureObjectParameter':
                path=SNAPSHOT if p['ParameterName']=='VelocityDensityBuffer' else PARAMS['texture'][p['ParameterName']]
                tex=u.load_asset(path);props={'parameter_name':p['ParameterName'],'texture':tex,'sampler_type':u.MaterialSamplerType.SAMPLERTYPE_COLOR if tex.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR}
            else:
                names={'ConstA':'const_a','ConstB':'const_b','ConstExponent':'const_exponent','ConstMin':'const_min','ConstMax':'const_max','ConstAlpha':'const_alpha','UTiling':'u_tiling','VTiling':'v_tiling'}
                for a,b in names.items():
                    if a in p:props[b]=p[a]
                for a in ['R','G','B','A']:
                    if a in p and isinstance(p[a],(bool,float,int)):props[a.lower()]=p[a]
                if 'Constant' in p:
                    values=[float(v) for v in re.findall(r'[RGBA]=([-\d.eE+]+)',p['Constant'])];props['constant']=u.LinearColor(*values)
                if kind=='TextureSample':
                    target=self.e.t.nodes[refs(p['TextureObject'])[0][0]]['props']['ParameterName'];tex=u.load_asset(SNAPSHOT if target=='VelocityDensityBuffer' else PARAMS['texture'][target]);props.update(texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if tex.get_editor_property('srgb') else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
            g.node(key,kind,**props);self.nodes[key]=key
            for pin,ref in self.e.t.edges(key,index):
                if pin in ['FunctionOutputs','Texture','ParameterName']:continue
                target_pin={'Coordinates':'UVs','TextureObject':'Tex'}.get(pin,pin)
                self.wire(self.make(*ref),key,target_pin)
        result=(key,output_name(g.nodes[key],index));self.cache[tag]=result;return result
    def outputs(self):
        attrs=self.e.t.nodes['MaterialExpressionMakeMaterialAttributes_0']['props']
        return {slot:self.make(*refs(attrs[slot])[0]) for slot in ['BaseColor','Normal','Roughness','Specular','PixelDepthOffset']}

def label_graph():
    world();mat=u.load_asset(PACKAGE+'/M_Surface_Rebuilt');pending=[];seen=set()
    for prop in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_SPECULAR]:
        node=u.MaterialEditingLibrary.get_material_property_input_node(mat,prop)
        if node:pending.append(node)
    labels={'MaterialExpressionMaterialFunctionCall_31':'POM: UV + PDO',
        'MaterialExpressionMaterialFunctionCall_9':'Main density normal',
        'MaterialExpressionMaterialFunctionCall_15':'Tile 1 normal',
        'MaterialExpressionMaterialFunctionCall_16':'Tile 2 normal',
        'MaterialExpressionMaterialFunctionCall_0':'Flow: two-phase sampling',
        'MaterialExpressionMaterialFunctionCall_1':'Texture aspect ratio'}
    while pending:
        node=pending.pop()
        if node.get_path_name() in seen:continue
        seen.add(node.get_path_name());desc=node.get_editor_property('desc')
        if desc in labels:node.set_editor_property('desc',labels[desc]+' | '+desc)
        pending.extend(n for n in u.MaterialEditingLibrary.get_inputs_for_material_expression(mat,node) if n)
    u.MaterialEditingLibrary.layout_material_expressions(mat)
    assert u.EditorAssetLibrary.save_loaded_asset(mat)
    return {'visited':len(seen),'labeled_sections':list(labels.values())}

def layout():
    w=world();sub=u.get_editor_subsystem(u.EditorActorSubsystem);actors={a.get_actor_label():a for a in sub.get_all_level_actors()}
    for label,x,material,text in [('Surface_Reference',-700,'MI_Surface_Reference','S1 Original surface'),('Surface_Rebuilt',0,'MI_Surface_Rebuilt','S2 Independent surface'),('Surface_Difference',700,'MI_Surface_Difference','S3 Attribute difference')]:
        actor=actors.get(label)
        if actor is None:actor=sub.spawn_actor_from_class(u.StaticMeshActor,u.Vector(x,2700,5));actor.set_actor_label(label)
        mesh=actor.get_component_by_class(u.StaticMeshComponent);mesh.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'));mesh.set_relative_scale3d(u.Vector(6,6,1));mesh.set_material(0,u.load_asset(PACKAGE+'/'+material))
        title=actors.get(label+'_Label')
        if title is None:title=sub.spawn_actor_from_class(u.TextRenderActor,u.Vector(x,2270,50));title.set_actor_label(label+'_Label')
        title.set_actor_rotation(u.Rotator(pitch=0,yaw=-90,roll=0),False)
        comp=title.get_component_by_class(u.TextRenderComponent);comp.set_text(u.Text(text));comp.set_world_size(30);comp.set_horizontal_alignment(u.HorizTextAligment.EHTA_CENTER)
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
    return {'row_y':2700,'map':w.get_path_name()}

def verify_gpu():
    w=world();sub=u.get_editor_subsystem(u.EditorActorSubsystem)
    target=next(a for a in sub.get_all_level_actors() if a.get_actor_label()=='Surface_Difference')
    mesh=target.get_component_by_class(u.StaticMeshComponent);old=u.load_asset(PACKAGE+'/MI_Surface_Difference')
    mid=u.MaterialLibrary.create_dynamic_material_instance(w,old);mid.set_texture_parameter_value('VelocityDensityBuffer',u.load_asset(SNAPSHOT));mesh.set_material(0,mid)
    rt=u.RenderingLibrary.create_render_target2d(w,64,64,u.TextureRenderTargetFormat.RTF_RGBA16F,u.LinearColor(0,0,0,1),False,False)
    actor=None;rows=[]
    try:
        actor=sub.spawn_actor_from_class(u.SceneCapture2D,u.Vector(700,2000,605));actor.set_actor_label('Stage3_TransientCapture')
        cap=actor.get_component_by_class(u.SceneCaptureComponent2D);cap.set_editor_property('texture_target',rt);cap.set_editor_property('fov_angle',50)
        cap.set_editor_property('capture_every_frame',False);cap.set_editor_property('capture_on_movement',False)
        cap.set_editor_property('primitive_render_mode',u.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST);cap.show_only_actor_components(target)
        flags=[]
        for name in ['Fog','Atmosphere','Bloom','EyeAdaptation','TemporalAA','Tonemapper']:
            flag=u.EngineShowFlagsSetting();flag.set_editor_property('show_flag_name',name);flag.set_editor_property('enabled',False);flags.append(flag)
        cap.set_editor_property('show_flag_settings',flags)
        for label,back,height in [('near',700,600),('fade_transition',1400,700),('far',1800,1400)]:
            actor.set_actor_location(u.Vector(700,2700-back,5+height),False,False)
            actor.set_actor_rotation(u.Rotator(pitch=-math.degrees(math.atan2(height,back)),yaw=90,roll=0),False)
            results=[]
            for mode in [0,1,2]:
                mid.set_scalar_parameter_value('DebugMode',mode)
                for scale in [1,0]:
                    mid.set_scalar_parameter_value('RebuildHeightScale',scale);cap.capture_scene()
                    pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(w,rt,0,0,64,64,False)
                    values=[(c.r,c.g,c.b) for c in pixels]
                    assert len(values)==4096 and all(math.isfinite(v) for c in values for v in c)
                    maxima=[max(abs(c[i]) for c in values) for i in range(3)]
                    results.append({'mode':mode,'height_scale':scale,'max_abs_rgb':maxima})
            mid.set_scalar_parameter_value('RebuildHeightScale',1);mid.set_scalar_parameter_value('DebugMode',1)
            mid.set_scalar_parameter_value('RebuildTileNormalScale',0);cap.capture_scene()
            tile_pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(w,rt,0,0,64,64,False)
            tile_error=max(max(abs(c.r),abs(c.g),abs(c.b)) for c in tile_pixels)
            mid.set_scalar_parameter_value('RebuildTileNormalScale',1)
            rows.append({'case':label,'back_cm':back,'height_cm':height,'results':results,'tile_normals_disabled_error':tile_error})
    finally:
        mesh.set_material(0,old)
        if actor:sub.destroy_actor(actor)
    result={'scope':'Original full surface function vs independent selected-variant reconstruction; frozen source texture; three distances; color/normal/roughness/specular/PDO',
        'cases':rows}
    def valid_case(row):
        base=[r for r in row['results'] if r['height_scale']==1]
        control=[r for r in row['results'] if r['height_scale']==0 and r['mode']==1]
        return max(base[0]['max_abs_rgb'])<0.002 and max(base[1]['max_abs_rgb'])<0.01 and max(base[2]['max_abs_rgb'][:2])<0.002 and base[2]['max_abs_rgb'][2]<0.05 and max(control[0]['max_abs_rgb'])>0.001
    result['pass']=all(valid_case(r) for r in rows) and rows[-1]['tile_normals_disabled_error']>0.001
    (ROOT/'gpu_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    assert result['pass'],result
    return result

def build_flow_test():
    world();ROOT.mkdir(exist_ok=True);g=Graph('M_Surface_FlowDifference')
    g.node('OriginalFlow','MaterialFunctionCall');assert g.nodes['OriginalFlow'].set_material_function(u.load_asset('/Game/FluidNinjaLive/OutputMaterials/Base/Functions/MF_FlowMapFunction'))
    texture=u.load_asset(PARAMS['texture']['FlowMapTexture'])
    g.node('FlowTex','TextureObjectParameter',parameter_name='FlowTexture',texture=texture,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    g.node('FlowUV','TextureCoordinate');g.node('Velocity','VectorParameter',parameter_name='Velocity',default_value=u.LinearColor(0.4,-0.7,0,0))
    for name,value in [('DensityMultiplier',1),('Strength',2),('Speed',3),('TimeValue',0.07),('RebuildFlowScale',1)]:g.node(name,'ScalarParameter',parameter_name=name,default_value=value)
    g.node('SignedRange','StaticBool',value=False)
    mapping={'FlowTex':'FlowTargetTexture','FlowUV':'UV','Velocity':'FlowInputVector','DensityMultiplier':'FlowMultiplyByDensity','Strength':'InputFlowStrength','Speed':'FlowSpeed','TimeValue':'CustomTime','SignedRange':'InputRangeIs-0-to-1'}
    for source,pin in mapping.items():g.link(source,'OriginalFlow',pin)
    custom(g,'IndependentFlow',FLOW_CODE,['FlowTexture','FlowVector','DensityMultiplier','Strength','Speed','TimeValue','UV'])
    for source,pin in [('FlowTex','FlowTexture'),('FlowUV','UV'),('Velocity','FlowVector'),('DensityMultiplier','DensityMultiplier'),('Strength','Strength'),('Speed','Speed'),('TimeValue','TimeValue')]:g.link(source,'IndependentFlow',pin)
    g.node('ScaleFlow','Multiply');g.link('IndependentFlow','ScaleFlow','A');g.link('RebuildFlowScale','ScaleFlow','B')
    g.node('Subtract','Subtract');g.link('OriginalFlow','Subtract','A');g.link('ScaleFlow','Subtract','B');g.node('Abs','Abs');g.link('Subtract','Abs');g.output('Abs','EMISSIVE_COLOR')
    row=g.finish();(ROOT/'flow_build_manifest.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
    return {'path':row['path'],'nodes':len(row['nodes'])}

def verify_flow():
    w=world();mid=u.MaterialLibrary.create_dynamic_material_instance(w,u.load_asset(PACKAGE+'/M_Surface_FlowDifference'))
    rt=u.RenderingLibrary.create_render_target2d(w,64,64,u.TextureRenderTargetFormat.RTF_RGBA16F,u.LinearColor(0,0,0,1),False,False)
    cases=[((0.4,-0.7),0.07,1,2),((2,1.25),0.31,1,2),((-0.9,0.6),0.79,0.25,2),((0.4,-0.7),0.43,1,0)]
    rows=[]
    for velocity,time,density,strength in cases:
        mid.set_vector_parameter_value('Velocity',u.LinearColor(*velocity,0,0));mid.set_scalar_parameter_value('TimeValue',time);mid.set_scalar_parameter_value('DensityMultiplier',density);mid.set_scalar_parameter_value('Strength',strength)
        errors=[]
        for scale in [1,0]:
            mid.set_scalar_parameter_value('RebuildFlowScale',scale);u.RenderingLibrary.draw_material_to_render_target(w,rt,mid)
            pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(w,rt,0,0,64,64,False)
            assert len(pixels)==4096 and all(math.isfinite(v) for c in pixels for v in [c.r,c.g,c.b])
            errors.append(max(max(abs(c.r),abs(c.g),abs(c.b)) for c in pixels))
        rows.append({'velocity':velocity,'time':time,'density_multiplier':density,'strength':strength,'normal_max_error':errors[0],'zero_output_control_error':errors[1]})
    result={'scope':'Original Flow function vs independent HLSL; signed-input variant; explicit nonzero velocities and times; 64x64 per case','cases':rows,'pass':all(r['normal_max_error']<0.0001 and r['zero_output_control_error']>0.001 for r in rows)}
    (ROOT/'flow_gpu_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');assert result['pass'],result
    return result
