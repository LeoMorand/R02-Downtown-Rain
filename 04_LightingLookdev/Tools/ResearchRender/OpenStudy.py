"""Open the verified study in an already-running Stormfall editor."""
import json
from pathlib import Path
import unreal as u

root=Path(u.Paths.project_dir()).resolve()/'Tools/ResearchRender'
run=Path((root/'study_latest.txt').read_text(encoding='utf8').strip())
report=json.loads((run/'report.json').read_text(encoding='utf8'))
verified=json.loads((run/'final_verification.json').read_text(encoding='utf8'))
assert report['phase']=='complete' and verified['success']
assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),'Save the current map before switching'
assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(report['output_map'])
hero=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label()=='Study_Hero')
u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(hero.get_actor_location(),hero.get_actor_rotation())
print('Opened verified study: '+report['output_map'])
