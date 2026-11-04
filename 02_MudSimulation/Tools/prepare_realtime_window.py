"""Temporarily select floating PIE and invoke only the research editor's Play shortcut."""
import ctypes
import os
from ctypes import wintypes
import unreal as u

assert 'FluidNinjaStudy' in u.Paths.get_project_file_path()
rt_play_settings = u.get_default_object(u.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
rt_play_before = {k: rt_play_settings.get_editor_property(k) for k in
                  ['NewWindowWidth', 'NewWindowHeight', 'NewWindowPosition',
                   'CenterNewWindow']}
rt_play_settings.set_editor_property('NewWindowWidth', 1920)
rt_play_settings.set_editor_property('NewWindowHeight', 1080)
rt_play_settings.set_editor_property('NewWindowPosition', u.IntPoint(100, 100))
rt_play_settings.set_editor_property('CenterNewWindow', False)
rt_user32 = ctypes.windll.user32
rt_windows = []


@ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
def rt_find(hwnd, unused):
    pid = wintypes.DWORD()
    rt_user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    text = ctypes.create_unicode_buffer(512)
    rt_user32.GetWindowTextW(hwnd, text, 512)
    if pid.value == os.getpid() and 'FluidNinjaLive' in text.value and 'Unreal Editor' in text.value:
        rt_windows.append(int(hwnd))
    return True


rt_user32.EnumWindows(rt_find, 0)
assert len(rt_windows) == 1, rt_windows
rt_main_hwnd = rt_windows[0]
rt_user32.ShowWindow(rt_main_hwnd, 9)
rt_user32.SetForegroundWindow(rt_main_hwnd)
assert int(rt_user32.GetForegroundWindow()) == rt_main_hwnd, 'Research editor not focused; no keys sent'
rt_user32.keybd_event(0x12, 0, 0, 0)
rt_user32.keybd_event(0x50, 0, 0, 0)
rt_user32.keybd_event(0x50, 0, 2, 0)
rt_user32.keybd_event(0x12, 0, 2, 0)
