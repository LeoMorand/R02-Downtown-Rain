"""Execute in the main editor after saving its current map."""
import json
from pathlib import Path
import unreal as u

root=Path(u.Paths.project_dir()).resolve()/'Tools/ResearchRender'
run=Path((root/'latest.txt').read_text(encoding='utf8'))
report=json.loads((run/'report.json').read_text(encoding='utf8'))
assert report['phase']=='complete', 'Latest run is incomplete; see report.json'
assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Save the current map before opening the render study'
assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(report['output_map'])
cam=report['preset']['camera'];loc=u.Vector(*cam['location'])
rot=u.MathLibrary.find_look_at_rotation(loc,u.Vector(*cam['target']))
u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(loc,rot)
print('Opened '+report['output_map'])
