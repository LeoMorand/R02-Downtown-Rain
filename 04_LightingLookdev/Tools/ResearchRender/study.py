"""Controlled MRQ camera study and read-only material diagnosis in a dedicated process."""
import datetime
import hashlib
import json
import time
import traceback
import sys
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent.parent
assert '-ResearchRender' in u.SystemLibrary.get_command_line()
assert Path(u.Paths.get_project_file_path()).resolve()==PROJECT/'Stormfall.uproject'
SPEC=json.loads((ROOT/'study.json').read_text(encoding='utf8'))
RUN=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
OUT=ROOT/'studies'/RUN
OUT.mkdir(parents=True)
DEST='/Game/Control_Dev/CentralResearch/Render/Study_'+RUN
MAP=DEST+'/L_Study'
E=u.get_editor_subsystem(u.EditorActorSubsystem)
LS=u.get_editor_subsystem(u.LevelEditorSubsystem)
LIB=u.MaterialEditingLibrary
ASSET=u.EditorAssetLibrary
TOOLS=u.AssetToolsHelpers.get_asset_tools()
REPORT={'phase':'setup','spec':SPEC,'output_map':MAP,'errors':[],'jobs':[]}
START=time.monotonic()


def write():
    (OUT/'report.json').write_text(json.dumps(REPORT,indent=2),encoding='utf8')
    (ROOT/'study_latest.txt').write_text(str(OUT),encoding='utf8')


def hashes():
    paths=[PROJECT/'Content'/(SPEC['source_map'][6:]+'.umap')]
    for p in ['Control_Assets/Materials','Control_Assets/EP101/Materials','Control_Dev/CentralResearch/Materials']:
        paths.extend((PROJECT/'Content'/p).rglob('*.uasset'))
    source_folder=PROJECT/'Content'/SPEC['source_map'][6:].rsplit('/',1)[0]
    paths.extend(source_folder.rglob('*.uasset'))
    return {str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def geometry():
    return {a.get_actor_label():{'transform':a.get_actor_transform().export_text(),
            'mesh':a.static_mesh_component.static_mesh.get_path_name() if a.static_mesh_component.static_mesh else None,
            'visible':a.static_mesh_component.is_visible(),
            'materials':[m.get_path_name() if m else None for m in a.static_mesh_component.get_materials()]}
            for a in E.get_all_level_actors() if isinstance(a,u.StaticMeshActor)}


def material_audit():
    mats={};parents={};textures={}
    for a in E.get_all_level_actors():
        for c in a.get_components_by_class(u.StaticMeshComponent):
            for i,m in enumerate(c.get_materials()):
                if not m:continue
                path=m.get_path_name()
                if path not in mats:
                    row={'users':[],'scalar':{},'vector':{},'textures':{}}
                    base=m.get_base_material();bp=base.get_path_name();row['base']=bp
                    if bp not in parents:
                        graph={'properties':{},'outputs':{},'nodes':[]}
                        for n in ['blend_mode','two_sided','shading_model','opacity_mask_clip_value']:
                            graph['properties'][n]=str(base.get_editor_property(n))
                        for n,prop in [('base_color',u.MaterialProperty.MP_BASE_COLOR),('roughness',u.MaterialProperty.MP_ROUGHNESS),
                                       ('specular',u.MaterialProperty.MP_SPECULAR),('normal',u.MaterialProperty.MP_NORMAL),
                                       ('metallic',u.MaterialProperty.MP_METALLIC)]:
                            node=LIB.get_material_property_input_node(base,prop)
                            graph['outputs'][n]={'node':node.get_name() if node else None,
                                'output':LIB.get_material_property_input_node_output_name(base,prop)}
                        for node in LIB.get_material_expressions(base):
                            info={'name':node.get_name(),'class':node.get_class().get_name()}
                            for n in ['parameter_name','sampler_type','const_a','const_b','const_r','const_g','const_b','default_value','texture']:
                                try:info[n]=str(node.get_editor_property(n))
                                except Exception:pass
                            graph['nodes'].append(info)
                        parents[bp]=graph
                    if isinstance(m,u.MaterialInstanceConstant):
                        for n in LIB.get_scalar_parameter_names(base):row['scalar'][str(n)]=LIB.get_material_instance_scalar_parameter_value(m,n)
                        for n in LIB.get_vector_parameter_names(base):
                            v=LIB.get_material_instance_vector_parameter_value(m,n);row['vector'][str(n)]=[v.r,v.g,v.b,v.a]
                        for n in LIB.get_texture_parameter_names(base):
                            t=LIB.get_material_instance_texture_parameter_value(m,n)
                            row['textures'][str(n)]=t.get_path_name() if t else None
                            if t and t.get_path_name() not in textures:
                                data={}
                                for p in ['srgb','compression_settings','flip_green_channel','virtual_texture_streaming']:
                                    try:data[p]=str(t.get_editor_property(p))
                                    except Exception:pass
                                try:data['source_file']=t.get_editor_property('asset_import_data').get_first_filename()
                                except Exception:pass
                                textures[t.get_path_name()]=data
                    mats[path]=row
                mats[path]['users'].append({'actor':a.get_actor_label(),'component':c.get_name(),'slot':i})
    (OUT/'material_audit.json').write_text(json.dumps({'materials':mats,'parents':parents,'textures':textures},indent=2),encoding='utf8')
    REPORT['audit_counts']={'materials':len(mats),'parents':len(parents),'textures':len(textures)}


def sequence(name,camera):
    seq=TOOLS.create_asset('LS_'+name,DEST,u.LevelSequence,u.LevelSequenceFactoryNew())
    assert seq
    seq.set_display_rate(u.FrameRate(24,1));seq.set_playback_start(0);seq.set_playback_end(1)
    binding=seq.add_possessable(camera)
    track=seq.add_track(u.MovieSceneCameraCutTrack);section=track.add_section();section.set_range(0,1)
    bid=u.MovieSceneObjectBindingID();bid.set_editor_property('guid',binding.get_id());section.set_camera_binding_id(bid)
    assert ASSET.save_loaded_asset(seq)
    return seq


def config(job,name):
    cfg=job.get_configuration()
    cfg.find_or_add_setting_by_class(u.MoviePipelineDeferredPassBase)
    cfg.find_or_add_setting_by_class(u.MoviePipelineImageSequenceOutput_PNG)
    out=cfg.find_or_add_setting_by_class(u.MoviePipelineOutputSetting)
    out.output_resolution=u.IntPoint(1280,720);out.output_directory=u.DirectoryPath(str(OUT/name))
    out.file_name_format='{sequence_name}.{frame_number}'
    aa=cfg.find_or_add_setting_by_class(u.MoviePipelineAntiAliasingSetting)
    aa.spatial_sample_count=1;aa.temporal_sample_count=8
    aa.engine_warm_up_count=64;aa.render_warm_up_count=32;aa.render_warm_up_frames=True


def finished(executor,success):
    REPORT['executor_success']=bool(success)
    missing=[]
    for job in REPORT['jobs']:
        images=list((OUT/job['name']).glob('*.png'))
        job['images']=[str(p) for p in images if p.stat().st_size>1000]
        if not job['images']:missing.append(job['name'])
    REPORT['source_files_unchanged']=hashes()==REPORT['source_hashes']
    REPORT['phase']='complete' if success and not missing and REPORT['source_files_unchanged'] else 'failed'
    REPORT['missing_outputs']=missing;REPORT['elapsed_seconds']=time.monotonic()-START
    write();u.SystemLibrary.quit_editor()


try:
    write();REPORT['source_hashes']=hashes()
    assert LS.load_level(SPEC['source_map'])
    original=geometry();material_audit()
    anchor=next(a for a in E.get_all_level_actors() if a.get_actor_label()=='CR_04486_research_sector_lobby_main_new')
    p=anchor.get_actor_location();offset=[p.x-4000,p.y-15200,p.z]
    assert abs(anchor.get_actor_rotation().yaw)<.01
    REPORT['anchor_offset']=offset
    SUB=u.get_editor_subsystem(u.MoviePipelineQueueSubsystem);QUEUE=SUB.get_queue()
    if SPEC['mode']=='refine':
        sys.path.insert(0,str(ROOT))
        import refine
        refine.setup(globals())
    else:
        cameras=[]
        for shot in SPEC['shots']:
            loc=u.Vector(*[shot['location'][i]+offset[i] for i in range(3)])
            target=u.Vector(*[shot['target'][i]+offset[i] for i in range(3)])
            rot=u.MathLibrary.find_look_at_rotation(loc,target)
            cam=E.spawn_actor_from_class(u.CameraActor,loc,rot);cam.set_actor_label('Study_'+shot['name'])
            cam.camera_component.set_field_of_view(shot['fov']);cam.set_folder_path('ResearchRender/StudyCameras')
            cameras.append((shot,cam))
        assert geometry()==original,'Scouting must not change source mesh/materials'
        assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),MAP)
        assert LS.load_level(MAP)
        assert geometry()==original,'Saved/reloaded scene differs'
        REPORT['geometry_verified']=len(original)
        for shot,_ in cameras:
            cam=next(a for a in E.get_all_level_actors() if a.get_actor_label()=='Study_'+shot['name'])
            seq=sequence(shot['name'],cam)
            job=QUEUE.allocate_new_job(u.MoviePipelineExecutorJob);job.job_name=shot['name']
            job.map=u.SoftObjectPath(MAP);job.sequence=u.SoftObjectPath(seq.get_path_name());config(job,shot['name'])
            REPORT['jobs'].append({'name':shot['name'],'sequence':seq.get_path_name(),'camera':shot})
    u.AutomationLibrary.finish_loading_before_screenshot()
    REPORT['phase']='rendering';write()
    EXECUTOR=u.MoviePipelinePIEExecutor();EXECUTOR.on_executor_finished_delegate.add_callable_unique(finished)
    u.EditorPythonScripting.set_keep_python_script_alive(True)
    SUB.render_queue_with_executor_instance(EXECUTOR)
except Exception:
    REPORT['phase']='failed';REPORT['errors'].append(traceback.format_exc());write();u.SystemLibrary.quit_editor()
