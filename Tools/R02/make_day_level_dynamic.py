"""One-off: switch R02's Daytime_Lighting from Always Loaded to Dynamic streaming (still loaded and
visible at start) so the weather controller's Night toggle can hide it in a game world too.
Run in the editor with R02 open:  py "D:/aco/unreal/Stormfall/Tools/R02/make_day_level_dynamic.py"
Python has no set_streaming_class_for_level here, so the sublevel is removed and re-added; the
sublevel asset itself is not touched.
"""
import unreal as u

DAY = '/Game/Downtown_West/Maps/Sub-Levels/Daytime_Lighting'
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
streaming = u.GameplayStatics.get_streaming_level(world, DAY)
if not streaming:
    raise SystemExit('[DayDynamic] Daytime_Lighting streaming level not found')
if isinstance(streaming, u.LevelStreamingAlwaysLoaded):
    level = streaming.get_loaded_level()
    if not u.EditorLevelUtils.remove_level_from_world(level):
        raise SystemExit('[DayDynamic] remove failed')
    streaming = u.EditorLevelUtils.add_level_to_world(world, DAY, u.LevelStreamingDynamic)
    if not streaming:
        raise SystemExit('[DayDynamic] re-add failed')
streaming.set_editor_property('initially_loaded', True)
streaming.set_editor_property('initially_visible', True)
# add_level_to_world makes the sublevel current; save_current_level would silently drop the change.
saved = u.EditorLevelLibrary.save_all_dirty_levels()
u.log('[DayDynamic] class %s, saved %s' % (streaming.get_class().get_name(), saved))
