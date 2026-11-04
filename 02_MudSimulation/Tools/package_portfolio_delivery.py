"""Verify and package the local portfolio media without publishing it."""
import hashlib,json,math,shutil,subprocess,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Deliverables/MudPortfolio_20261029'
BASE=ROOT/'Verification/MudProfessional/phase09-delivery'
FF=Path('C:/Users/78107/AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe')
FP=FF.with_name('ffprobe.exe')


def main():
    videos=[]
    for name,frames,duration in [('Mud_Portfolio_73s_1080p30.mp4',2190,73),('Mud_Portfolio_73s_Submit.mp4',2190,73),('Full_Replay_64s_1080p30.mp4',1920,64)]:
        path=OUT/name
        meta=json.loads(subprocess.check_output([str(FP),'-v','error','-show_entries','stream=codec_name,width,height,r_frame_rate,nb_frames','-show_entries','format=duration,size','-of','json',str(path)]))
        s=meta['streams'][0]; assert s['width']==1920 and s['height']==1080 and s['r_frame_rate']=='30/1'
        assert int(s['nb_frames'])==frames and abs(float(meta['format']['duration'])-duration)<.001
        decoded=subprocess.run([str(FF),'-hide_banner','-loglevel','error','-nostdin','-threads','2','-xerror','-i',str(path),'-f','null','-'],capture_output=True)
        assert decoded.returncode==0,decoded.stderr.decode(errors='replace')
        videos.append(dict(file=name,frames=frames,duration_seconds=duration,width=1920,height=1080,fps=30,decode_exit_code=decoded.returncode,bytes=path.stat().st_size))
        print('Verified '+name,flush=True)
    (OUT/'video_validation.json').write_text(json.dumps(dict(passed=True,videos=videos,chapter_frames_visually_inspected=[2,12,27,36,44,56,63,69]),indent=2))
    full=BASE/'20261030T021251128855Z'
    replay=json.loads((full/'validation.json').read_text()); boundary=json.loads((full/'boundary_validation.json').read_text())
    edge=json.loads((BASE/'edge_fixture_validation.json').read_text())
    assert replay['passed'] and boundary['passed'] and edge['passed']
    static=json.loads((BASE/'20261030T020930848796Z/run.json').read_text()); flow=json.loads((BASE/'20261030T021114055249Z/run.json').read_text())
    assert static['contact_contract']['detail_flow_enabled'] is False and flow['contact_contract']['detail_flow_enabled'] is True
    path_error=max(math.dist(a['location'],b['location']) for a,b in zip(static['samples'],flow['samples']))
    clock=max(abs(a['sequence_seconds']-b['sequence_seconds']) for a,b in zip(static['frames'],flow['frames']))
    assert path_error<.01 and clock<.0001
    evidence=dict(full_replay=replay,boundary_prediction=boundary,edge_gpu_fixture=edge,
        flow_comparison=dict(path_difference_cm=path_error,sequence_clock_difference_seconds=clock,scope='Independent captures with matching input path, not pixel-identical simulation proof'),
        performance_reference='Phase08 / 720p / D3D12 SM6; not a benchmark of the final 1080p presentation preset',
        limits=['Offline video is not a realtime FPS test.','Visual mesh correction does not modify CPU collision.','The finite-domain blend can relax contact in its transition band.','Full dynamic equivalence and new Shipping acceptance remain unverified.'])
    (OUT/'EVIDENCE.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    shutil.copy2(OUT/'.build/pipeline.png',OUT/'技术链路.png')
    shutil.copy2(OUT/'.build/qa_27s.jpg',OUT/'预览.jpg')
    files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!='CHECKSUMS.sha256')
    checksums='\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in files)+'\n'
    (OUT/'CHECKSUMS.sha256').write_text(checksums,encoding='utf-8')
    selected=['Mud_Portfolio_73s_Submit.mp4','技术说明.md','面试讲述.md','技术链路.png','预览.jpg','EVIDENCE.json','video_validation.json']
    package_readme='# 交互泥浆投递素材包\n\n先播放Mud_Portfolio_73s_Submit.mp4（73秒、1080p30），再看技术说明与面试提纲。视频采用离线采集，不是实时FPS证明。\n\n参考/共享资源：FluidNinja、UE Engine；个人增量与限制见技术说明。\n\n本ZIP仅含上传主片与说明。高码率主片和连续64秒回放保留在本地完整素材文件夹中。未包含完整工程或新版Shipping程序。\n'
    package=OUT.parent/'MudPortfolio_20261029_Submit.zip'
    with zipfile.ZipFile(package,'w') as z:
        z.writestr('README.md',package_readme,compress_type=zipfile.ZIP_DEFLATED)
        for name in selected: z.write(OUT/name,name,compress_type=zipfile.ZIP_STORED if name.endswith('.mp4') else zipfile.ZIP_DEFLATED)
        sums='\n'.join(hashlib.sha256((OUT/name).read_bytes()).hexdigest()+'  '+name for name in selected)+'\n'
        z.writestr('SHA256SUMS.txt',sums,compress_type=zipfile.ZIP_DEFLATED)
        assert z.testzip() is None
    print(json.dumps(dict(package=str(package),bytes=package.stat().st_size,videos_verified=len(videos)),indent=2))


if __name__=='__main__': main()
