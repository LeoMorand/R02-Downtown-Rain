"""Switch R02 between the day and night lighting sublevels in the editor viewport.

Run in the editor with R02 open (Output Log, Cmd box):
    py "D:/aco/unreal/Stormfall/Tools/R02/lighting_look.py" night
    py "D:/aco/unreal/Stormfall/Tools/R02/lighting_look.py" day
Only the editor visibility changes. Nothing is saved, and Play-In-Editor keeps using the streaming
settings (day), so record the night look in the editor viewport.
"""
import sys
import unreal as u

LEVELS = {
    'day': '/Game/Downtown_West/Maps/Sub-Levels/Daytime_Lighting',
    'night': '/Game/Downtown_West/Maps/Sub-Levels/Nightime_Lighting',
}

look = sys.argv[1] if len(sys.argv) > 1 else 'day'
if look not in LEVELS:
    raise SystemExit('usage: lighting_look.py day|night')
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
found = 0
for streaming in u.EditorLevelUtils.get_levels(world):
    package = streaming.get_outermost().get_name()
    for name, path in LEVELS.items():
        if package == path:
            u.EditorLevelUtils.set_level_visibility(streaming, name == look, False)
            found += 1
u.log('[LightingLook] %s (%d sublevels updated)' % (look, found))
