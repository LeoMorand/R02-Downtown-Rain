"""Annotate the user's R02 node recording; input media stays untouched."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT=Path('D:/aco/unreal/Stormfall')
OUT=ROOT/'Deliverables/R02_Annotated_20261031_095317'
WORK=OUT/'Work'
SOURCE=Path('D:/OBS/2026-10-31 09-53-17.mkv')
WORK.mkdir(parents=True,exist_ok=True)
segments=[
 (0,2.68,'天气美术控制｜BP_WeatherArtController','统一应用美术参数，连接天气系统与表面材质。'),
 (2.70,4.63,'天气管理｜WeatherManagmentBP · SetRain','管理雨量，并向相关组件同步状态。'),
 (4.65,9.72,'统一天气状态｜MF_WeatherArtistState','集中处理湿度、雨量与手动模式，供不同材质读取。'),
 (9.75,12.83,'干湿混合｜MF_GroundWetness','湿度驱动颜色与粗糙度变化，保留底材纹理。'),
 (12.86,15.60,'物体表面函数｜MF_SurfaceRain','封装可复用的干湿颜色与粗糙度计算。'),
 (15.65,17.70,'玻璃表面函数｜MF_GlassSurfaceRain','为玻璃材质提供独立的湿润响应入口。'),
 (17.75,26.48,'物体天气材质｜M_Object_Default_Weather','将原物体材质接入湿润响应与表面水痕。'),
 (26.52,30.80,'雨痕玻璃材质｜M_WindowGlass_Rain','整合玻璃原有材质与雨痕、表面法线。'),
 (30.83,32.58,'全局参数集合｜MPC_RoadWeather','集中传递天气状态，连接控制逻辑与材质。'),
 (32.62,38.48,'物体水痕坐标｜MF_ObjectWorldSlideUV','使用世界位置构建流动 UV，让水痕沿世界向下。'),
 (38.52,46.73,'玻璃水痕坐标｜MF_GlassWorldSlideUV','将世界高度与时间偏移结合，生成向下滑动的采样坐标。'),
 (46.77,52.55,'土壤天气材质｜M_Ground_Soil_Weather','接入统一湿润状态，保留原有地表纹理细节。'),
 (52.60,56.50,'特殊地面材质｜M_Ground_Special_Weather','在原材质结构上接入共享天气响应。'),
 (56.55,59.60,'建筑天气材质｜M_Object_Building_Weather','保留建筑底材，叠加干湿变化与表面水痕。'),
 (59.65,63.56,'硬质地面母材质｜M_Ground_Master_Weather','整合地面湿润、积水遮罩与涟漪法线。'),
]
def ass_time(t):
    v=round(t*100);return f'{v//360000}:{v//6000%60:02d}:{v//100%60:02d}.{v%100:02d}'
def srt_time(t):
    v=round(t*1000);return f'{v//3600000:02d}:{v//60000%60:02d}:{v//1000%60:02d},{v%1000:03d}'
header='''[Script Info]
ScriptType: v4.00+
PlayResX: 3200
PlayResY: 2000
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,Microsoft YaHei,48,&H00F3EEE8,&H000000FF,&H00100E0B,&H00000000,-1,0,0,0,100,100,0,0,1,1,0,7,0,0,0,1
Style: Description,Microsoft YaHei,44,&H00D8D8D8,&H000000FF,&H00100E0B,&H00000000,0,0,0,0,100,100,0,0,1,1,0,7,0,0,0,1
Style: Panel,Arial,20,&H00201B16,&H000000FF,&H00201B16,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
events=[];srt=[]
for i,(start,end,title,desc) in enumerate(segments,1):
    a,b=ass_time(start),ass_time(end)
    events.append(f'Dialogue: 0,{a},{b},Panel,,0,0,0,,{{\\an7\\pos(665,1732)\\p1\\alpha&H10&}}m 0 0 l 2455 0 2455 192 0 192{{\\p0}}')
    events.append(f'Dialogue: 1,{a},{b},Panel,,0,0,0,,{{\\an7\\pos(695,1763)\\p1\\c&HE0C36E&}}m 0 0 l 6 0 6 128 0 128{{\\p0}}')
    events.append(f'Dialogue: 2,{a},{b},Title,,0,0,0,,{{\\pos(733,1755)}}{title}')
    events.append(f'Dialogue: 2,{a},{b},Description,,0,0,0,,{{\\pos(733,1829)}}{desc}')
    srt.append(f'{i}\n{srt_time(start)} --> {srt_time(end)}\n{title}\n{desc}\n')
(OUT/'R02_Annotations.ass').write_text(header+'\n'.join(events)+'\n',encoding='utf-8-sig')
(OUT/'R02_Annotations.srt').write_text('\n'.join(srt),encoding='utf-8-sig')
(OUT/'annotation-timeline.json').write_text(json.dumps([dict(start=s,end=e,title=t,description=d) for s,e,t,d in segments],ensure_ascii=False,indent=2),encoding='utf-8')
fonts=WORK/'Fonts';fonts.mkdir(exist_ok=True)
for name in ['msyh.ttc','msyhbd.ttc']:
    dest=fonts/name
    if not dest.exists():shutil.copy2(Path('C:/Windows/Fonts')/name,dest)
probe=['ffmpeg','-hide_banner','-loglevel','error','-ss','10','-i',str(SOURCE),'-t','0.5','-vf','ass=R02_Annotations.ass:fontsdir=Work/Fonts','-an','-c:v','h264_nvenc','-preset','p4','-cq','19','-pix_fmt','yuv420p','-y','Work/encoder-probe.mp4']
result=subprocess.run(probe,cwd=OUT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
encoder=['-c:v','h264_nvenc','-preset','p5','-cq','18','-b:v','0'] if result.returncode==0 else ['-c:v','libx264','-preset','veryfast','-crf','18','-threads','8']
if result.returncode: print('NVENC unavailable; CPU encoding:',result.stderr.decode(errors='replace')[-500:],flush=True)
cmd=['ffmpeg','-hide_banner','-loglevel','warning','-i',str(SOURCE),'-map','0:v:0','-map','0:a?','-vf','ass=R02_Annotations.ass:fontsdir=Work/Fonts',*encoder,'-pix_fmt','yuv420p','-c:a','copy','-fps_mode','passthrough','-movflags','+faststart','-progress','Work/render-progress.txt','-y','R02_Nodes_Annotated.mp4']
print('Rendering with '+encoder[1],flush=True)
with (WORK/'render.log').open('w',encoding='utf-8') as log:
    subprocess.run(cmd,cwd=OUT,stdout=log,stderr=log,check=True)
metadata=dict(source=str(SOURCE),sourceSha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),output=str(OUT/'R02_Nodes_Annotated.mp4'),encoder=encoder[1],annotationSegments=len(segments),scope='Chinese visual annotations added to the original editor recording; no cuts, retiming, dubbed narration, performance numbers or runtime simulation claims added.')
(OUT/'render-info.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(metadata,ensure_ascii=False),flush=True)
