"""Fresh-process readback and final MRQ output for the accepted same-camera study."""
import hashlib
import json
import traceback
from pathlib import Path
import unreal as u

assert '-ResearchRender' in u.SystemLibrary.get_command_line()
ROOT=Path(__file__).resolve().parent
OUT=Path((ROOT/'study_latest.txt').read_text(encoding='utf8').strip())
REPORT=json.loads((OUT/'report.json').read_text(encoding='utf8'))
CHECK={'success':False,'errors':[]}


def write():
    (OUT/'final_verification.json').write_text(json.dumps(CHECK,indent=2),encoding='utf8')


def finished(executor,success):
    images=list((OUT/'Final4K').glob('*.png'))
    CHECK['executor_success']=bool(success)
    CHECK['images']=[str(p) for p in images if p.stat().st_size>1000]
    CHECK['success']=bool(success and CHECK['images'] and not CHECK['errors'])
    CHECK['phase']='complete' if CHECK['success'] else 'failed'
    write();u.SystemLibrary.quit_editor()


try:
    assert REPORT['phase']=='complete' and REPORT['source_files_unchanged']
    job_spec=next(j for j in REPORT['jobs'] if j['name']=='Lookdev')
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(job_spec['map'])
    E=u.get_editor_subsystem(u.EditorActorSubsystem);L=u.MaterialEditingLibrary
    actors={a.get_actor_label():a for a in E.get_all_level_actors()}
    changes=json.loads((OUT/'material_changes.json').read_text(encoding='utf8'))
    instances={}
    for row in changes:
        actor=actors[row['actor']]
        comp=next(x for x in actor.get_components_by_class(u.StaticMeshComponent) if x.get_name()==row['component'])
        mi=comp.get_material(row['slot'])
        assert mi.get_path_name()==row['after'],row
        instances[mi.get_path_name()]=mi
    parent_count=0
    for adaptation in REPORT['parent_adaptations']:
        mat=u.load_asset(adaptation['copy']);assert mat
        nodes={str(n.get_editor_property('parameter_name')):n for n in L.get_material_expressions(mat)
               if isinstance(n,u.MaterialExpressionTextureSampleParameter2D)}
        for sample in adaptation['samplers']:
            assert str(nodes[sample['parameter']].get_editor_property('sampler_type'))==sample['sampler']
        if adaptation['leaf']:
            assert mat.get_editor_property('two_sided')
            assert mat.get_editor_property('shading_model')==u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE
        parent_count+=1
    for path,mi in instances.items():
        original=next(row['before'] for row in changes if row['after']==path)
        old=u.load_asset(original)
        for name in L.get_texture_parameter_names(old.get_base_material()):
            a=L.get_material_instance_texture_parameter_value(old,name)
            b=L.get_material_instance_texture_parameter_value(mi,name)
            assert (a.get_path_name() if a else None)==(b.get_path_name() if b else None)
    project=Path(u.Paths.project_dir()).resolve()
    for path,wanted in REPORT['source_hashes'].items():
        assert hashlib.sha256((project/path).read_bytes()).hexdigest()==wanted,path
    CHECK.update(material_slots_verified=len(changes),instances_verified=len(instances),parents_verified=parent_count,
                 source_packages_verified=len(REPORT['source_hashes']),map=job_spec['map'],phase='rendering')
    SUB=u.get_editor_subsystem(u.MoviePipelineQueueSubsystem);QUEUE=SUB.get_queue()
    JOB=QUEUE.allocate_new_job(u.MoviePipelineExecutorJob);JOB.job_name='Lookdev4K'
    JOB.map=u.SoftObjectPath(job_spec['map']);JOB.sequence=u.SoftObjectPath(job_spec['sequence'])
    cfg=JOB.get_configuration();cfg.find_or_add_setting_by_class(u.MoviePipelineDeferredPassBase)
    cfg.find_or_add_setting_by_class(u.MoviePipelineImageSequenceOutput_PNG)
    output=cfg.find_or_add_setting_by_class(u.MoviePipelineOutputSetting)
    output.output_resolution=u.IntPoint(3840,2160);output.output_directory=u.DirectoryPath(str(OUT/'Final4K'))
    output.file_name_format='{sequence_name}.{frame_number}'
    aa=cfg.find_or_add_setting_by_class(u.MoviePipelineAntiAliasingSetting)
    aa.spatial_sample_count=1;aa.temporal_sample_count=8;aa.engine_warm_up_count=64
    aa.render_warm_up_count=32;aa.render_warm_up_frames=True
    u.AutomationLibrary.finish_loading_before_screenshot()
    EXECUTOR=u.MoviePipelinePIEExecutor();EXECUTOR.on_executor_finished_delegate.add_callable_unique(finished)
    u.EditorPythonScripting.set_keep_python_script_alive(True)
    write();SUB.render_queue_with_executor_instance(EXECUTOR)
except Exception:
    CHECK['errors'].append(traceback.format_exc());write();u.SystemLibrary.quit_editor()
