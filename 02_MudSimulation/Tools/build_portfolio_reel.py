"""Build the portfolio reel from verified UE captures. No synthetic scene imagery."""
import argparse
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
FFMPEG=Path('C:/Users/78107/AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe')
FONT='C:/Windows/Fonts/msyh.ttc'
W,H=1920,1080
BG=(14,18,22); FG=(237,242,246); DIM=(166,180,189); ACC=(210,174,119)


def font(n): return ImageFont.truetype(FONT,n)


def text(draw,xy,value,size=32,fill=FG): draw.text(xy,value,font=font(size),fill=fill)


def graphics(out):
    out.mkdir(parents=True,exist_ok=True)
    for name in ('intro','pipeline','evidence'):
        im=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(im)
        d.rectangle((96,118,104,190),fill=ACC)
        if name=='intro':
            text(d,(132,122),'TECHNICAL ART STUDY',32,ACC)
            text(d,(124,310),'交互泥浆',100)
            text(d,(132,464),'高度场重建 · 速度驱动细节 · GPU视觉贴合',42)
            text(d,(132,598),'Unreal Engine 5.8  /  Niagara  /  HLSL  /  C++',30,DIM)
            text(d,(132,828),'基于参考实现的研究性重建与扩展',29,DIM)
        elif name=='pipeline':
            text(d,(132,122),'从输入到表面的数据链',48)
            nodes=[('输入轨迹','位置 / 尺寸'),('Niagara模拟','速度 / 密度'),('状态纹理','RG速度 / B高度'),('表面重建','法线 / POM / 流动'),('视觉贴合','GPU球体支撑')]
            for i,(a,b) in enumerate(nodes):
                x=96+i*352
                d.rectangle((x,370,x+314,585),outline=(67,78,85),width=2)
                text(d,(x+20,410),a,32,ACC); text(d,(x+20,485),b,24)
                if i<4: text(d,(x+322,448),'→',26,DIM)
            text(d,(100,712),'统一高度单位     POM采样点对齐     双相细节     可重放A/B验证',32)
            text(d,(100,820),'接触修正只移动可见网格；输入与碰撞根轨迹保持原配置。',27,DIM)
        else:
            text(d,(132,122),'把效果做成可复核的工程案例',48)
            for y,title,body in [
                (330,'完整回放检查','直行、转向、停留、返回、出入边界与末尾停留'),
                (480,'独立性能对照','Phase08：8轮同轨迹A/B；5760个有效GPU样本'),
                (630,'来源与实现边界','参考/共享资源：FluidNinja、UE Engine；增量实现见技术说明')]:
                text(d,(110,y),title,34,ACC); text(d,(110,y+65),body,29)
            text(d,(110,846),'性能基线为720p / D3D12 SM6；不代表本片1080p预设的实时帧率。',25,DIM)
        text(d,(100,1008),'离线采集 · 30Hz模拟步进 · 算法与验证范围见随附说明',23,DIM)
        im.save(out/(name+'.png'))
    labels={
        'hero':('高度场驱动形变','同一状态用于表面、计算法线与视觉接触'),
        'contact':('近景：球体与泥面的视觉贴合','运行时在GPU完成球体支撑计算'),
        'hold':('停留与残留形变','输入停止后继续观察表面状态'),
        'boundary':('边界测试：离开与重新进入区域','接触补偿在边缘平滑退出；不包含区域外刚体支撑'),
        'contact_ab':('同状态对照：视觉接触','冻结同一模拟时刻、相同机位；只切换接触修正'),
        'flow_ab':('同轨迹回放：细节流动','相同输入回放；两次独立采集，不宣称像素级状态等价')}
    for name,(title,subtitle) in labels.items():
        im=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
        d.rectangle((0,0,W,106),fill=(10,15,20,190))
        text(d,(44,22),title,34,FG)
        text(d,(1450,32),'离线录制 / 30Hz步进',23,DIM)
        d.rectangle((0,998,W,H),fill=(10,15,20,200))
        text(d,(44,1016),subtitle,25,FG)
        if name in ('contact_ab','flow_ab'):
            a,b=('关闭视觉贴合','开启视觉贴合') if name=='contact_ab' else ('静态细节','速度驱动双相细节')
            text(d,(84,155),a,32,DIM); text(d,(1044,155),b,32,ACC)
        im.save(out/(name+'.png'))


def run(args,log):
    p=subprocess.run([str(FFMPEG),'-hide_banner','-loglevel','warning','-nostdin','-y']+args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
    log.write_text(p.stdout,encoding='utf-8')
    if p.returncode: raise RuntimeError(f'ffmpeg failed; see {log}')


def codec():
    return ['-an','-c:v','libx264','-threads','4','-preset','medium','-crf','18','-pix_fmt','yuv420p','-r','30','-g','60','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart']


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('full',type=Path); ap.add_argument('static',type=Path); ap.add_argument('flow',type=Path)
    args=ap.parse_args()
    for p in (args.full,args.static,args.flow): assert json.loads((p/'validation.json').read_text())['passed']
    out=ROOT/'Deliverables/MudPortfolio_20261029'; work=out/'.build'; work.mkdir(parents=True,exist_ok=True)
    graphics(work)
    segments=[]
    def finish(inputs,filters,duration,name):
        dest=work/(name+'.mp4')
        run(['-filter_complex_threads','1']+inputs+['-filter_complex',filters,'-map','[v]','-t',str(duration)]+codec()+[str(dest)],work/(name+'.log'))
        segments.append(dest)
    def card(name,seconds):
        finish(['-loop','1','-framerate','30','-i',str(work/(name+'.png'))],'[0:v]setsar=1,format=yuv420p[v]',seconds,name)
    def clip(name,start,seconds):
        finish(['-framerate','30','-start_number',str(round(start*30)),'-i',str(args.full/'frames/frame_%06d.jpg'),'-loop','1','-i',str(work/(name+'.png'))],
               '[0:v]setsar=1[b];[b][1:v]overlay=0:0,format=yuv420p[v]',seconds,name)
    card('intro',4)
    clip('hero',8,16)
    clip('contact',24,12)
    finish(['-loop','1','-framerate','30','-i',str(args.full/'evidence/contact_off.jpg'),'-loop','1','-framerate','30','-i',str(args.full/'evidence/contact_on.jpg'),'-loop','1','-i',str(work/'contact_ab.png')],
           '[0:v]crop=1000:700:460:230,scale=960:672,setsar=1[a];[1:v]crop=1000:700:460:230,scale=960:672,setsar=1[b];[a][b]hstack=inputs=2,pad=1920:1080:0:230:color=0x0e1216[c];[c][2:v]overlay=0:0,format=yuv420p[v]',8,'contact_ab')
    finish(['-framerate','30','-start_number','120','-i',str(args.static/'frames/frame_%06d.jpg'),'-framerate','30','-start_number','120','-i',str(args.flow/'frames/frame_%06d.jpg'),'-loop','1','-i',str(work/'flow_ab.png')],
           '[0:v]crop=1000:700:460:230,scale=960:672,setsar=1[a];[1:v]crop=1000:700:460:230,scale=960:672,setsar=1[b];[a][b]hstack=inputs=2,pad=1920:1080:0:230:color=0x0e1216[c];[c][2:v]overlay=0:0,format=yuv420p[v]',8,'flow_ab')
    clip('hold',36,6)
    clip('boundary',46,6)
    card('pipeline',6)
    card('evidence',7)
    concat=work/'reel.ffconcat'
    concat.write_text('ffconcat version 1.0\n'+'\n'.join("file '"+p.name+"'" for p in segments)+'\n',encoding='utf-8')
    final=out/'Mud_Portfolio_73s_1080p30.mp4'
    run(['-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(final)],work/'concat.log')
    # Also retain a continuous full replay, independently of the edited reel.
    run(['-framerate','30','-i',str(args.full/'frames/frame_%06d.jpg'),'-loop','1','-i',str(work/'hero.png'),'-filter_complex_threads','1','-filter_complex','[0:v][1:v]overlay=0:0,format=yuv420p[v]','-map','[v]','-t','64']+codec()+[str(out/'Full_Replay_64s_1080p30.mp4')],work/'full_replay.log')
    manifest=dict(reel=str(final),duration_seconds=73,source_runs={k:str(v) for k,v in vars(args).items()},chapters=[(0,'intro'),(4,'hero'),(20,'contact'),(32,'contact A/B'),(40,'flow A/B'),(48,'hold'),(54,'boundary'),(60,'pipeline'),(66,'evidence')],scope='Offline 30Hz simulation capture; no realtime FPS claim')
    (out/'edit_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__': main()
