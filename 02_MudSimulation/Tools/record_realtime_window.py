"""Window-only WGC capture, sampled on the wall clock. Never captures desktop."""
import argparse, ctypes, json, subprocess, sys, threading, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent/'_capture_deps'))
from windows_capture import WindowsCapture, Frame, InternalCaptureControl
import numpy as np
from PIL import Image

p=argparse.ArgumentParser()
p.add_argument('--out',required=True)
p.add_argument('--seconds',type=float,default=8)
p.add_argument('--probe',action='store_true')
a=p.parse_args()
out=Path(a.out).resolve(); out.mkdir(parents=True,exist_ok=True)
cap=WindowsCapture(cursor_capture=False,draw_border=False,minimum_update_interval=16,
                   window_name='FluidNinjaLive Preview [NetMode: Standalone 0]')
lock=threading.Lock(); latest=None; arrivals=[]
@cap.event
def on_frame_arrived(frame:Frame,control:InternalCaptureControl):
    global latest
    with lock:
        latest=frame.frame_buffer.copy()
        arrivals.append(time.monotonic())
@cap.event
def on_closed():
    pass
control=cap.start_free_threaded()
deadline=time.monotonic()+30
while latest is None and time.monotonic()<deadline: time.sleep(.02)
if latest is None:
    control.stop(); raise RuntimeError('No target window frames')
Image.fromarray(latest[:,:,[2,1,0,3]]).save(out/'window_probe.png')
print(json.dumps({'shape':latest.shape,'ready':True}),flush=True)
if a.probe:
    control.stop(); sys.exit()
# WGC includes the Slate window. These measured offsets remove its chrome.
height,width=latest.shape[:2]
assert (width,height)==(1932,1160),(width,height)
ff=Path('C:/Users/78107/AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe')
log=(out/'encoder.log').open('w',encoding='utf8')
proc=subprocess.Popen([str(ff),'-y','-hide_banner','-loglevel','warning','-f','rawvideo',
    '-pixel_format','bgra','-video_size','1920x1080','-framerate','30','-i','pipe:0',
    '-an','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p',
    '-movflags','+faststart',str(out/'runtime_raw.mp4')],stdin=subprocess.PIPE,stderr=log)
started=time.monotonic(); frames=0; sampling=[]
(out/'ready.json').write_text(json.dumps({'monotonic':started,'seconds':a.seconds}))
try:
    while time.monotonic()-started<a.seconds and not (out/'stop').exists():
        target=started+frames/30
        delay=target-time.monotonic()
        if delay>0: time.sleep(delay)
        with lock: selected=latest[72:1152,6:1926].copy()
        proc.stdin.write(selected.tobytes())
        sampling.append(time.monotonic()-started); frames+=1
finally:
    proc.stdin.close(); proc.wait(); control.stop(); log.close()
    (out/'recording.json').write_text(json.dumps({'frames':frames,'duration':frames/30,
        'wall_seconds':time.monotonic()-started,'capture_arrivals':len(arrivals),
        'sampling':sampling,'arrival_monotonic':arrivals,'encoder_exit':proc.returncode,
        'window_only':True,'crop':[6,72,1920,1080]},indent=2))
print(json.dumps({'done':True,'frames':frames,'encoder_exit':proc.returncode}),flush=True)
