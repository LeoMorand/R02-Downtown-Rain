"""Dedicated MRQ executor, uses the last successful study and exits on completion."""
import json
from pathlib import Path
import unreal as u

assert '-ResearchRender' in u.SystemLibrary.get_command_line()
ROOT=Path(__file__).resolve().parent
OUT=Path((ROOT/'latest.txt').read_text(encoding='utf8'))
REPORT=json.loads((OUT/'report.json').read_text(encoding='utf8'))
assert REPORT['phase']=='complete' and 'mrq' in REPORT,'Successful MRQ preparation required'
SUB=u.get_editor_subsystem(u.MoviePipelineQueueSubsystem)
QUEUE=SUB.get_queue()
JOB=QUEUE.allocate_new_job(u.MoviePipelineExecutorJob)
JOB.job_name='ResearchRender_Hero4K'
JOB.map=u.SoftObjectPath(REPORT['mrq']['map'])
JOB.sequence=u.SoftObjectPath(REPORT['mrq']['sequence'])
JOB.set_configuration(u.load_asset(REPORT['mrq']['config']))
DRAFT='-RRDraft' in u.SystemLibrary.get_command_line() or globals().get('FORCE_DRAFT',False)
if DRAFT:
    settings=JOB.get_configuration().find_or_add_setting_by_class(u.MoviePipelineOutputSetting)
    settings.output_resolution=u.IntPoint(1600,900)
    settings.output_directory=u.DirectoryPath(str(OUT/'Draft'))
EXECUTOR=u.MoviePipelinePIEExecutor()


def finished(executor,success):
    folder='Draft' if DRAFT else 'Final4K'
    (OUT/('draft_result.json' if DRAFT else 'final_result.json')).write_text(json.dumps({'success':bool(success),'output':str(OUT/folder)}),encoding='utf8')
    u.SystemLibrary.quit_editor()


EXECUTOR.on_executor_finished_delegate.add_callable_unique(finished)
u.EditorPythonScripting.set_keep_python_script_alive(True)
try:
    SUB.render_queue_with_executor_instance(EXECUTOR)
except Exception:
    import traceback
    (OUT/'final_result.json').write_text(json.dumps({'success':False,'error':traceback.format_exc()}),encoding='utf8')
    u.SystemLibrary.quit_editor()
