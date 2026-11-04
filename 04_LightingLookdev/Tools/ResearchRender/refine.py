"""Scene-private typed texture sampling, bounded roughness, and foliage adaptation.

Called by study.py. Originals and source textures remain untouched.
"""
import hashlib
import json
from types import SimpleNamespace
import unreal as u


def setup(context):
    c=SimpleNamespace(**context)
    L=c.LIB;A=c.ASSET
    shot=c.SPEC['hero'];offset=c.REPORT['anchor_offset']
    loc=u.Vector(*[shot['location'][i]+offset[i] for i in range(3)])
    target=u.Vector(*[shot['target'][i]+offset[i] for i in range(3)])
    cam=c.E.spawn_actor_from_class(u.CameraActor,loc,u.MathLibrary.find_look_at_rotation(loc,target))
    cam.set_actor_label('Study_Hero');cam.camera_component.set_field_of_view(shot['fov'])
    original=c.geometry()
    changes=[];parents={};instances={}

    def add_node(mat,cls,**props):
        n=L.create_material_expression(mat,cls)
        for name,val in props.items():n.set_editor_property(name,val)
        return n

    def wire(a,output,b,pin):
        names=list(L.get_material_expression_input_names(b))
        if pin=='Input' and pin not in names:pin=names[0]
        assert L.connect_material_expressions(a,output,b,pin),(a.get_name(),b.get_name(),pin)

    def scalar(mat,name,value):
        return add_node(mat,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)

    def parent_for(mi,is_leaf):
        source=mi.get_base_material();key=(source.get_path_name(),is_leaf)
        if key in parents:return parents[key]
        dest=c.DEST+'/Materials/M_'+source.get_name()+'_'+('Foliage' if is_leaf else 'Surface')
        mat=A.duplicate_asset(source.get_path_name(),dest);assert mat
        # Ensure sample declarations and defaults agree with the instance texture roles.
        samples=[]
        for n in L.get_material_expressions(mat):
            if not isinstance(n,u.MaterialExpressionTextureSampleParameter2D):continue
            param=n.get_editor_property('parameter_name')
            texture=L.get_material_instance_texture_parameter_value(mi,param)
            if not texture:continue
            n.set_editor_property('texture',texture)
            compression=texture.get_editor_property('compression_settings')
            if compression==u.TextureCompressionSettings.TC_NORMALMAP:
                sampler=u.MaterialSamplerType.SAMPLERTYPE_NORMAL
            elif texture.get_editor_property('srgb'):
                sampler=u.MaterialSamplerType.SAMPLERTYPE_COLOR
            else:sampler=u.MaterialSamplerType.SAMPLERTYPE_MASKS
            n.set_editor_property('sampler_type',sampler)
            samples.append({'parameter':str(param),'texture':texture.get_path_name(),'sampler':str(sampler)})
        # Preserve the original smoothness conversion, then expose a bounded floor.
        rough=L.get_material_property_input_node(mat,u.MaterialProperty.MP_ROUGHNESS)
        assert rough
        output=L.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_ROUGHNESS)
        clamp=add_node(mat,u.MaterialExpressionClamp,min_default=0.,max_default=1.)
        wire(rough,output,clamp,'Input');wire(scalar(mat,'LP_RoughnessFloor',0.),'',clamp,'Min')
        assert L.connect_material_property(clamp,'',u.MaterialProperty.MP_ROUGHNESS)
        spec=L.get_material_property_input_node(mat,u.MaterialProperty.MP_SPECULAR)
        if spec:
            output=L.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_SPECULAR)
            multiply=add_node(mat,u.MaterialExpressionMultiply)
            wire(spec,output,multiply,'A');wire(scalar(mat,'LP_SpecularScale',1.),'',multiply,'B')
            assert L.connect_material_property(multiply,'',u.MaterialProperty.MP_SPECULAR)
        if is_leaf:
            mat.set_editor_property('two_sided',True)
            mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
            base=L.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR)
            output=L.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_BASE_COLOR)
            multiply=add_node(mat,u.MaterialExpressionMultiply)
            wire(base,output,multiply,'A');wire(scalar(mat,'LP_Transmission',.15),'',multiply,'B')
            assert L.connect_material_property(multiply,'',u.MaterialProperty.MP_SUBSURFACE_COLOR)
        L.layout_material_expressions(mat);L.recompile_material(mat)
        assert A.save_loaded_asset(mat)
        parents[key]=mat
        c.REPORT.setdefault('parent_adaptations',[]).append({'source':key[0],'copy':dest,'leaf':is_leaf,'samplers':samples})
        return mat

    def adjust_materials():
        for actor in c.E.get_all_level_actors():
            for comp in actor.get_components_by_class(u.StaticMeshComponent):
                for slot,mi in enumerate(comp.get_materials()):
                    if not isinstance(mi,u.MaterialInstanceConstant):continue
                    names={str(n) for n in L.get_texture_parameter_names(mi.get_base_material())}
                    if 'ControlNormalMap' not in names:continue
                    path=mi.get_path_name();leaf='leaves' in path.lower()
                    normal=L.get_material_instance_texture_parameter_value(mi,'ControlNormalMap')
                    if not normal or normal.get_editor_property('compression_settings')!=u.TextureCompressionSettings.TC_NORMALMAP:
                        skipped=c.REPORT.setdefault('skipped_untyped_normals',[])
                        if path not in skipped:skipped.append(path)
                        continue
                    if path not in instances:
                        parent=parent_for(mi,leaf)
                        dest=c.DEST+'/Materials/'+mi.get_name()+'_'+hashlib.sha256(path.encode()).hexdigest()[:6]
                        new=A.duplicate_asset(path,dest);assert new
                        L.set_material_instance_parent(new,parent)
                        for name in L.get_texture_parameter_names(mi.get_base_material()):
                            texture=L.get_material_instance_texture_parameter_value(mi,name)
                            if texture:L.set_material_instance_texture_parameter_value(new,name,texture)
                        floor=.6 if leaf else .65 if any(k in path.lower() for k in ['trunk','stump']) else .35 if 'concrete' in path.lower() else 0.
                        L.set_material_instance_scalar_parameter_value(new,'LP_RoughnessFloor',floor)
                        L.set_material_instance_scalar_parameter_value(new,'LP_SpecularScale',.8 if leaf else 1.)
                        if leaf:L.set_material_instance_scalar_parameter_value(new,'LP_Transmission',.15)
                        L.update_material_instance(new);assert A.save_loaded_asset(new)
                        assert abs(L.get_material_instance_scalar_parameter_value(new,'LP_RoughnessFloor')-floor)<1e-5
                        # Existing texture overrides must survive reparenting.
                        for name in L.get_texture_parameter_names(mi.get_base_material()):
                            before=L.get_material_instance_texture_parameter_value(mi,name)
                            after=L.get_material_instance_texture_parameter_value(new,name)
                            assert (before.get_path_name() if before else None)==(after.get_path_name() if after else None),(path,str(name))
                        instances[path]=new
                    comp.set_material(slot,instances[path])
                    changes.append({'actor':actor.get_actor_label(),'component':comp.get_name(),'slot':slot,
                                    'before':path,'after':instances[path].get_path_name()})

    def queue_stage(name,map_path,diagnostic=False):
        hero=next(a for a in c.E.get_all_level_actors() if a.get_actor_label()=='Study_Hero')
        seq=c.sequence(name,hero)
        job=c.QUEUE.allocate_new_job(u.MoviePipelineExecutorJob);job.job_name=name
        job.map=u.SoftObjectPath(map_path);job.sequence=u.SoftObjectPath(seq.get_path_name());c.config(job,name)
        cfg=job.get_configuration();out=cfg.find_or_add_setting_by_class(u.MoviePipelineOutputSetting)
        out.output_resolution=u.IntPoint(1920,1080)
        if diagnostic:
            out.file_name_format='{sequence_name}.{render_pass}.{frame_number}'
            render=cfg.find_or_add_setting_by_class(u.MoviePipelineDeferredPassBase)
            passes=[]
            for pass_name in ['BaseColor','Roughness','WorldNormal']:
                path='/Engine/BufferVisualization/'+pass_name+'.'+pass_name
                assert u.load_asset(path)
                passes.append(u.MoviePipelinePostProcessPass(enabled=True,name=pass_name,material=u.load_asset(path)))
            render.additional_post_process_materials=passes
            render.disable_multisample_effects=True
            aa=cfg.find_or_add_setting_by_class(u.MoviePipelineAntiAliasingSetting)
            aa.temporal_sample_count=1;aa.spatial_sample_count=1
        c.REPORT['jobs'].append({'name':name,'map':map_path,'sequence':seq.get_path_name(),'camera':shot,'diagnostic':diagnostic})

    def save_reload(path,expected):
        assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),path)
        assert c.LS.load_level(path)
        assert c.geometry()==expected,'Saved/reloaded mesh or material mismatch'

    baseline=c.DEST+'/L_Baseline'
    save_reload(baseline,original);queue_stage('Baseline',baseline)
    adjust_materials()
    expected=c.geometry()
    def without_materials(s):return {k:{n:v for n,v in x.items() if n!='materials'} for k,x in s.items()}
    assert without_materials(expected)==without_materials(original),'Geometry changed'
    material_map=c.DEST+'/L_Material'
    save_reload(material_map,expected);queue_stage('MaterialOnly',material_map)
    # A separate same-camera data view; no quantitative PBR claims from display PNGs.
    queue_stage('MaterialDiagnostics',material_map,True)
    for actor in c.E.get_all_level_actors():
        if isinstance(actor,u.Light) and actor.get_actor_label().startswith('RR_'):
            actor.get_component_by_class(u.LightComponent).set_intensity(0.)
        if isinstance(actor,u.PostProcessVolume):
            s=actor.settings;s.set_editor_property('override_ambient_cubemap_intensity',True)
            s.set_editor_property('ambient_cubemap_intensity',c.SPEC['look']['ambient']);actor.settings=s
    for light in c.SPEC['look']['lights']:
        loc=u.Vector(*[light['location'][i]+offset[i] for i in range(3)])
        target=u.Vector(*[light['target'][i]+offset[i] for i in range(3)])
        actor=c.E.spawn_actor_from_class(u.RectLight,loc,u.MathLibrary.find_look_at_rotation(loc,target))
        actor.set_actor_label('LP_'+light['name']);actor.set_folder_path('Lookdev/Lighting')
        lc=actor.get_component_by_class(u.RectLightComponent);lc.set_mobility(u.ComponentMobility.MOVABLE)
        lc.set_editor_property('intensity_units',u.LightUnits.LUMENS);lc.set_intensity(light['lumens'])
        lc.set_light_color(u.LinearColor(*light['color'],1.));lc.set_attenuation_radius(light['radius'])
        lc.set_editor_property('source_width',light['width']);lc.set_editor_property('source_height',light['height'])
        lc.set_editor_property('cast_shadows',True)
    look_map=c.DEST+'/L_Lookdev'
    save_reload(look_map,expected);queue_stage('Lookdev',look_map)
    c.REPORT['output_map']=look_map;c.REPORT['geometry_verified']=len(original)
    c.REPORT['material_instances_created']=len(instances);c.REPORT['material_slots_adjusted']=len(changes)
    (c.OUT/'material_changes.json').write_text(json.dumps(changes,indent=2),encoding='utf8')
