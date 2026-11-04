"""Encode real Phase15 UE captures into a 70-second silent portfolio reel."""
import argparse
import hashlib
import json
import statistics
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FF = Path('C:/Users/78107/AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe')
FP = FF.with_name('ffprobe.exe')
FONT = 'C:/Windows/Fonts/msyh.ttc'
MONO = 'C:/Windows/Fonts/consola.ttf'
W, H = 1920, 1080
FG, DIM, ACC = (240, 244, 247), (183, 195, 204), (225, 188, 130)


def text(draw, position, value, size=32, fill=FG, mono=False):
    draw.text(position, value, font=ImageFont.truetype(MONO if mono else FONT, size), fill=fill)


def caption(path, title, detail, tag=''):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 116), fill=(10, 15, 20, 212))
    d.rectangle((48, 29, 54, 82), fill=ACC)
    text(d, (76, 24), title, 38)
    text(d, (78, 73), detail, 23, DIM)
    if tag:
        text(d, (1450, 37), tag, 28, ACC)
    d.rectangle((0, 1018, W, H), fill=(10, 15, 20, 220))
    text(d, (46, 1032), 'UE 场景采集 · 离线 30Hz 步进 · 非实时帧率证明', 24, DIM)
    im.save(path)


def technical_card(path):
    im = Image.new('RGB', (W, H), (14, 19, 25))
    d = ImageDraw.Draw(im)
    d.rectangle((80, 100, 87, 170), fill=ACC)
    text(d, (114, 102), '从角色交互到泥面呈现', 52)
    text(d, (116, 185), 'Unreal Engine 5.8  /  Niagara Grid2D  /  HLSL  /  C++', 29, DIM)
    nodes = [('角色输入', '骨骼位置 / 泥面交点'), ('Niagara 模拟', '输运 / 压力 / 密度'),
             ('状态纹理', '速度 / 密度输出'), ('表面呈现', '计算法线 / POM / 细节流动')]
    for i, (a, b) in enumerate(nodes):
        x = 80+i*455
        d.rounded_rectangle((x, 322, x+390, 514), radius=12, fill=(25, 33, 42), outline=(77, 91, 104), width=2)
        text(d, (x+24, 354), a, 36, ACC)
        text(d, (x+24, 430), b, 24, DIM)
        if i < 3:
            text(d, (x+405, 389), '→', 32, DIM)
    text(d, (90, 605), '输运阶段：速度与密度分别保留，避免黏稠感联动压平泥面', 32)
    d.rounded_rectangle((80, 674, 1840, 856), radius=10, fill=(9, 14, 20))
    text(d, (112, 698), 'Value = float4(transported.xy * Feedback,', 34, mono=True)
    text(d, (112, 756), '               transported.z * DensityFeedback, transported.w);', 34, mono=True)
    text(d, (88, 926), '参考 FluidNinja 的效果与算法；共享纹理及 UE Manny 角色资源。研究性重建与扩展。', 26, DIM)
    text(d, (88, 1008), '演示镜头由脚本调度与离线采集；未宣称完整动态等价。', 23, DIM)
    im.save(path)


def run(command, log):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            encoding='utf-8', errors='replace')
    log.write_text(result.stdout, encoding='utf-8')
    if result.returncode:
        raise RuntimeError('Command failed: '+str(log))
    return result.stdout


def codec():
    return ['-an', '-c:v', 'libx264', '-threads', '6', '-preset', 'fast', '-crf', '20',
            '-pix_fmt', 'yuv420p', '-r', '30', '-g', '60', '-color_primaries', 'bt709',
            '-color_trc', 'bt709', '-colorspace', 'bt709', '-movflags', '+faststart']


def validate_raw(source):
    data = json.loads((source/'run.json').read_text())
    assert data['complete'] and not data['error'], data.get('error')
    assert data['settings_restored']
    assert data['frame_count'] == 1860 and len(data['frames']) == 1860
    assert data['capture_settings']['width'] == W and data['capture_settings']['height'] == H
    assert abs(statistics.median(data['game_deltas'])-1/30) < 1e-6
    for i, row in enumerate(data['frames']):
        assert row['file'] == 'frames/frame_%06d.jpg' % i
        with Image.open(source/row['file']) as im:
            assert im.size == (W, H)
            im.verify()
    samples = data['samples']
    thin = [s for s in samples if s['stage'] == 'thin']
    pool = [s for s in samples if s['stage'] == 'pool']
    assert max(s['location'][0] for s in thin)-min(s['location'][0] for s in thin) > 300
    assert max(s['location'][1] for s in thin)-min(s['location'][1] for s in thin) > 200
    assert min(s['location'][2] for s in pool) < 20 and max(s['location'][2] for s in pool) > 85
    depths = {s['depth_cm'] for s in samples if s['stage'] == 'depth'}
    assert depths == {20, 50, 90}, depths
    low = [s for s in samples if s['stage'] == 'visc_low']
    high = [s for s in samples if s['stage'] == 'visc_high']
    assert any(abs(s['max_walk_speed']-340) < .1 for s in low)
    assert any(abs(s['max_walk_speed']-180) < .1 for s in high)
    colors = [s for s in samples if s['stage'] == 'color']
    assert len(colors) == 30
    for s in colors:
        local = s['frame']-next(x['first_frame'] for x in data['stages'] if x['name']=='color')
        expected = [.035,.055,.045,1] if 60 <= local < 120 else [.14536,.073858,.040263,1]
        assert max(abs(a-b) for a,b in zip(s['light_color'], expected)) < 1e-5, s
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source', type=Path)
    ap.add_argument('output', type=Path)
    args = ap.parse_args()
    source, out = args.source.resolve(), args.output.resolve()
    data = validate_raw(source)
    out.mkdir(parents=True, exist_ok=False)
    work = out/'.build'
    work.mkdir()
    technical_card(work/'technical.png')
    takes = []
    starts = {s['name']: s['first_frame'] for s in data['stages']}
    def take(key, seconds, title, detail, tag='', offset=0, frames=None):
        takes.append({'key': key, 'seconds': seconds, 'title': title, 'detail': detail,
                      'tag': tag, 'first_frame': starts[key]+offset, 'frames': frames or int(seconds*30)})
    take('hero', 8, '交互泥浆｜薄层与深池', 'Niagara 模拟 · HLSL 表面 · 计算法线 · C++ 交互')
    take('thin', 12, '薄层交互', '直行 → 转向 → 返回 → 停留；保留原平面行走方式', '表面起伏 20 cm')
    take('pool', 16, '深池交互', '沿坡道走入、停留、返回；腿部交点持续驱动泥浆', '池深 80 cm')
    for offset, title in [(0, '棕色'), (60, '墨绿色'), (120, '恢复棕色')]:
        take('color', 2, '美术参数｜颜色', '同一机位切换浅色与深色参数', title, offset, 60)
    for offset, depth in [(0, 20), (90, 50), (180, 90)]:
        take('depth', 3, '美术参数｜池深', '可行走底面随深度调整；泥面保持原高度', str(depth)+' cm', offset, 90)
    take('visc_low', 4, '美术参数｜黏稠感 0', '相同输入时长；本段开启泥中行走阻力', '移动倍率 0.85')
    take('visc_high', 4, '美术参数｜黏稠感 1', '相同输入时长；速度与密度保留分别控制', '移动倍率 0.45')
    take('overview', 3, '同一场景，两种使用方式', '左：薄层表面　右：可进入的深池')
    segments, chapters = [], []
    duration = 0
    for index, item in enumerate(takes):
        name = '%02d_%s' % (index, item['key'])
        caption(work/(name+'.png'), item['title'], item['detail'], item['tag'])
        dest = work/(name+'.mp4')
        command = [str(FF), '-hide_banner', '-loglevel', 'warning', '-nostdin', '-y',
                   '-filter_complex_threads', '1', '-framerate', '30', '-start_number', str(item['first_frame']),
                   '-i', str(source/'frames/frame_%06d.jpg'), '-loop', '1', '-framerate', '30',
                   '-i', str(work/(name+'.png')), '-filter_complex', '[0:v][1:v]overlay=0:0,format=yuv420p[v]',
                   '-map', '[v]', '-frames:v', str(item['frames'])]+codec()+[str(dest)]
        run(command, work/(name+'.log'))
        segments.append(dest)
        chapters.append({'seconds': duration, 'title': item['title'], 'duration': item['seconds'],
                         'source_first_frame': item['first_frame']})
        duration += item['seconds']
        print(json.dumps({'encoded': name, 'seconds': duration}), flush=True)
    dest = work/'technical.mp4'
    run([str(FF), '-hide_banner', '-loglevel', 'warning', '-nostdin', '-y', '-loop', '1', '-framerate', '30',
         '-i', str(work/'technical.png'), '-frames:v', '240']+codec()+[str(dest)], work/'technical.log')
    segments.append(dest)
    chapters.append({'seconds': duration, 'title': '技术链路', 'duration': 8})
    duration += 8
    concat = work/'reel.ffconcat'
    concat.write_text('ffconcat version 1.0\n'+'\n'.join("file '"+p.name+"'" for p in segments)+'\n', encoding='utf-8')
    final = out/'Mud_SurfacePool_70s_1080p30.mp4'
    run([str(FF), '-hide_banner', '-loglevel', 'warning', '-nostdin', '-y', '-f', 'concat', '-safe', '0',
         '-i', str(concat), '-c', 'copy', '-movflags', '+faststart', str(final)], work/'concat.log')
    probe = subprocess.check_output([str(FP), '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(final)], encoding='utf-8')
    video = json.loads(probe)
    stream = next(s for s in video['streams'] if s['codec_type'] == 'video')
    assert stream['width'] == W and stream['height'] == H and stream['nb_frames'] == '2100'
    assert stream['avg_frame_rate'] == '30/1' and abs(float(video['format']['duration'])-70) < .1
    run([str(FF), '-hide_banner', '-loglevel', 'error', '-nostdin', '-i', str(final), '-f', 'null', '-'], out/'decode.log')
    manifest = {'file': final.name, 'duration_seconds': duration, 'frames': 2100, 'source': str(source),
                'chapters': chapters, 'scope': 'Real UE PIE captures; offline 30Hz stepping. Silent. No realtime FPS claim.',
                'capture_settings': data['capture_settings'], 'source_run_sha256': hashlib.sha256((source/'run.json').read_bytes()).hexdigest(),
                'video_sha256': hashlib.sha256(final.read_bytes()).hexdigest()}
    (out/'edit_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (out/'video_validation.json').write_text(json.dumps({'passed': True, 'width': W, 'height': H, 'frames': 2100,
        'fps': 30, 'seconds': 70, 'decode_errors': 0, 'source_frames_verified': 1860, 'raw_checks': 'movement, depth, viscosity, fixed game delta, complete JPEG sequence'}, indent=2), encoding='utf-8')
    (out/'ffprobe.json').write_text(probe, encoding='utf-8')
    # Review the encoded film, including the labels that will actually be delivered.
    contact = Image.new('RGB', (1920, 1080), (14, 19, 25))
    review_times = [3, 11, 16, 23, 28, 33, 38.5, 46, 49, 53, 57, 65]
    for i, seconds in enumerate(review_times):
        thumb = work/('review_%02d.jpg' % i)
        run([str(FF), '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-ss', str(seconds), '-i', str(final),
             '-frames:v', '1', '-vf', 'scale=480:270', str(thumb)], work/('review_%02d.log' % i))
        with Image.open(thumb) as im:
            contact.paste(im, ((i % 4)*480, (i//4)*360))
        ImageDraw.Draw(contact).text(((i % 4)*480+12, (i//4)*360+282), '%.1fs' % seconds,
                                   font=ImageFont.truetype(FONT, 24), fill=FG)
    contact.save(out/'Review_ContactSheet.jpg', quality=92)
    with Image.open(source/'frames/frame_000120.jpg') as im:
        im.resize((1280, 720)).save(out/'Preview.jpg', quality=92)
    print(json.dumps({'complete': True, 'file': str(final), 'bytes': final.stat().st_size}), flush=True)


if __name__ == '__main__':
    main()
