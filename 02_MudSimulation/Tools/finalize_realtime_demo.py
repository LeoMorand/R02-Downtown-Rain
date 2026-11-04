"""Trim recorder lead/tail only; preserve real-time speed and native UE HUD."""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageOps

ROOT=Path('D:/aco/unreal/Stormfall')
FF=Path('C:/Users/78107/AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe')
FP=FF.with_name('ffprobe.exe')
p=argparse.ArgumentParser();p.add_argument('--take',default='take03');a=p.parse_args()
src=ROOT/'Verification/MudProfessional/phase17-runtime'/a.take
out=ROOT/'Deliverables/MudFullFeatures_20261030';out.mkdir(parents=True,exist_ok=True)
def read(name):return json.loads((src/name).read_text(encoding='utf8'))
run=read('run.json');rec=read('recording.json');start=read('timeline_start.json');ready=read('ready.json')
assert run['complete'] and run['error'] is None,run['error']
assert rec['encoder_exit']==0 and rec['window_only']
lead=start['monotonic']-ready['monotonic'];duration=sum(d for _,d in run['stages'])
assert rec['duration']>=lead+duration-.1,(rec['duration'],lead+duration)
samples=run['samples']; stages={name:[s for s in samples if s['stage']==name] for name,_ in run['stages']}
assert all(stages.values()),[n for n,s in stages.items() if not s]
assert all(s['override_fps']==0 for s in samples)
assert any(s['falling'] for s in stages['thin'])
assert min(s['position'][2] for s in stages['pool'])<20
assert max(s['position'][0] for s in stages['pool'])>2600
assert {5,50,90}<={round(s['depth']) for s in stages['depth']}
assert {0,20,40}<={round(s['relief']) for s in stages['relief']}
assert {0,1}<={round(s['viscosity']) for s in stages['viscosity']}
assert {False,True}<={s['drag'] for s in stages['viscosity']}
assert {False,True}<={s['flow'] for s in stages['flow']}
assert {0,3}<={round(s['detail_flow_multiplier']) for s in stages['poolflow']}
assert len({s['shape'] for s in stages['shapes']})==4
assert {5,20,40}<={round(s['thin_thickness']) for s in stages['presets']}
assert {512,1024,2048}=={s['output_size'] for s in stages['quality']}
assert all(s['output_size']==s['normal_size'] for s in samples)
assert len({tuple(s['light']) for s in stages['color']})>=3
assert len({round(s['roughness'],2) for s in stages['roughness']})>=3
master=out/'Mud_FullFeatures_Runtime_1080p30.mp4'
subprocess.run([str(FF),'-y','-hide_banner','-loglevel','warning','-ss',f'{lead:.6f}',
    '-i',str(src/'runtime_raw.mp4'),'-t',str(duration),'-an','-c:v','libx264',
    '-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(master)],check=True)
probe=json.loads(subprocess.check_output([str(FP),'-v','error','-show_streams','-show_format','-of','json',str(master)]))
v=next(s for s in probe['streams'] if s['codec_type']=='video')
assert (v['width'],v['height'],v['avg_frame_rate'])==(1920,1080,'30/1')
assert abs(float(probe['format']['duration'])-duration)<.1
assert len(probe['streams'])==1
decode=subprocess.run([str(FF),'-v','error','-i',str(master),'-f','null','-'],capture_output=True,text=True)
assert decode.returncode==0 and not decode.stderr,decode.stderr
review=src/'review';review.mkdir(exist_ok=True)
times=[2,13,33,51,56,66,77,88,93,99,106,112,117,122,127,132,137,141,146,151,157,162,167,173,178,183,188,193,199,203,207,213,221,229,237,246]
for i,t in enumerate(times):
    subprocess.run([str(FF),'-v','error','-ss',str(t),'-i',str(master),'-frames:v','1',
                    '-update','1',str(review/f'{i:02d}_{t:03d}.png')],check=True)
thumbs=[ImageOps.contain(Image.open(q).convert('RGB'),(384,216)) for q in sorted(review.glob('*.png'))]
sheet=Image.new('RGB',(384*6,216*6),(14,18,22))
for i,im in enumerate(thumbs):sheet.paste(im,((i%6)*384,(i//6)*216))
sheet.save(out/'Review_ContactSheet.jpg',quality=94)
shutil.copy2(review/'02_033.png',out/'Preview.png')
shutil.copy2(src/'run.json',out/'runtime_parameters.json')
gaps=[b['wall_seconds']-a0['wall_seconds'] for a0,b in zip(samples,samples[1:])]
validation={'complete':True,'encoder_exit':rec['encoder_exit'],'decoded_without_errors':True,
    'duration_seconds':duration,'width':1920,'height':1080,'fps':30,'frames':int(v['nb_frames']),
    'native_ue_fps_and_unit_stats':True,'window_only':True,'runtime_parameter_samples':len(samples),
    'postproduced_titles':False,'subtitles':False,'audio':False,'speed_multiplier':1,
    'trim_lead_seconds':lead,'largest_parameter_sample_gap_seconds':max(gaps),
    'wall_game_elapsed_difference_seconds':samples[-1]['wall_seconds']-samples[-1]['game_seconds'],
    'coverage':[{'name':n,'duration':d,'samples':len(stages[n])} for n,d in run['stages']],
    'scope':'Whole research-editor PIE frame under recording load; native engine stats are not an isolated mud-solver benchmark.'}
(out/'video_validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf8')
offset=0;timelines=[]
labels=['双区总览','薄层行走、转向、跳跃','深池进入与退出','双颜色与亮度','粗糙度','细节强度与密度',
        '表面起伏','5 / 50 / 90 cm 深度预设','黏稠感与可选行走阻力','薄层流动开关与速度','深池细节流动倍率',
        '四种轮廓','宽高、偏移、旋转与圆角','不规则程度与种子','薄湿 / 厚重预设与恢复',
        '512 / 1024 / 2048 输出与法线分辨率','两块泥浆独立调色','总览']
for (name,d),label in zip(run['stages'],labels):
    timelines.append(f'- {int(offset)//60:02d}:{int(offset)%60:02d} {label}');offset+=d
text='''# 泥浆全功能实时演示

主片：`Mud_FullFeatures_Runtime_1080p30.mp4`，4分09秒，1920×1080，30 fps，无音轨。

仅裁掉录制前后的准备时间。没有片头、章节标题、后期字幕、技术图卡或变速；左侧为 UE 运行时直接读回的参数，右侧为原生 `stat fps` / `stat unit`。世界中的英文说明牌在本次 PIE 隐藏，工程资产未改。

'''+'\n'.join(timelines)+'''

运行画面来自研究工程的 Phase15 双区地图。用真实 Enhanced Input 驱动 Manny 与 CharacterMovement；参数调节由 PIE 脚本定时触发。录制的是变化后的实际运行画面和参数读数，不包含编辑器 Details 鼠标拖动。

性能数字来自录制当时的完整编辑器 PIE，包含两块泥浆、角色、环境、参数读数和窗口采集负载；不等于泥浆求解器的单独成本或独立打包性能。30 fps 是视频采样率，游戏实际 FPS 以画面右侧为准。视口 1920×1084、100% 渲染，中心裁切至 1920×1080；UE 原生统计的 RenderRes 长行在窗口右边缘有少量裁切。其余核心时间、显存与 draw call 读数保留。

池深是泥面到可行走底面的距离，表面起伏是 POM/法线控制。黏稠感是艺术联动，未按物理黏度标定。区域形状只裁切可见表面；512/1024/2048 调整输出和计算法线 RT，内部主模拟网格仍为 2048。运行时切换显示质量会重建模拟并清空痕迹。

对应源码：`Tools/MudStudy/mud_realtime_demo.py`、`record_realtime_window.py`、`finalize_realtime_demo.py`。完整运行参数记录及视频检查结果见同目录 JSON。原始采集与排查版本保存在 `Verification/MudProfessional/phase17-runtime/`，take03 为本片来源。
'''
(out/'README.md').write_text(text,encoding='utf8')
hashes=[]
for f in sorted(out.iterdir()):
    if f.is_file() and f.name!='CHECKSUMS.sha256': hashes.append(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name)
(out/'CHECKSUMS.sha256').write_text('\n'.join(hashes)+'\n',encoding='utf8')
print(json.dumps({'output':str(master),'bytes':master.stat().st_size,'validation':validation},ensure_ascii=False))
