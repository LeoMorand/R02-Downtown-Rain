"""Temporarily restore only the current research UE window, without activation."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import unreal as u

_saved = None


def restore_for_capture():
    global _saved
    assert Path(u.Paths.project_dir()).resolve().name == 'FluidNinjaStudy'
    assert _saved is None, 'Window restoration already active'
    user32 = ctypes.windll.user32
    user32.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindowAsync.restype = wintypes.BOOL
    candidates = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    def collect(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        title = ctypes.create_unicode_buffer(512)
        if pid.value == os.getpid():
            user32.GetWindowTextW(hwnd,title,512)
            if title.value == 'FluidNinjaLive - Unreal Editor':
                candidates.append((int(hwnd),bool(user32.IsIconic(hwnd))))
        return True
    user32.EnumWindows(collect,0)
    assert len(candidates)==1, 'Expected exactly one research editor main window'
    hwnd, minimized = candidates[0]
    _saved = dict(hwnd=hwnd, was_minimized=minimized, pid=os.getpid())
    if minimized:
        # SW_SHOWNOACTIVATE: restore size/position without requesting focus.
        assert user32.ShowWindowAsync(hwnd,4), 'ShowWindowAsync failed'
    return dict(_saved)


def restore_previous():
    global _saved
    if _saved is None:
        return True
    user32 = ctypes.windll.user32
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(_saved['hwnd'],ctypes.byref(pid))
    assert pid.value == _saved['pid'] == os.getpid(), 'Window owner changed'
    if _saved['was_minimized']:
        # SW_SHOWMINNOACTIVE: return to the initial minimized state.
        assert user32.ShowWindowAsync(_saved['hwnd'],7), 'Minimize restore failed'
    _saved = None
    return True
