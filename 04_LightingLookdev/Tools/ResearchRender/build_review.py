"""Build a local, dependency-free review page from actual MRQ outputs. No image edits."""
import html
import json
import os
import struct
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=Path((ROOT/'study_latest.txt').read_text(encoding='utf8').strip())
report=json.loads((OUT/'report.json').read_text(encoding='utf8'))
assert report['phase']=='complete'
verification=json.loads((OUT/'final_verification.json').read_text(encoding='utf8'))
assert verification['success']
pngs=list(OUT.rglob('*.png'))
dimensions={}
for p in pngs:
    with p.open('rb') as f:header=f.read(24)
    assert header[:8]==b'\x89PNG\r\n\x1a\n',p
    dimensions[p.relative_to(OUT).as_posix()]=list(struct.unpack('>II',header[16:24]))
assert dimensions['Final4K/LS_Lookdev.0000.png']==[3840,2160]
for name in ['Baseline','MaterialOnly','Lookdev']:
    assert dimensions[f'{name}/LS_{name}.0000.png']==[1920,1080]
diagnostic=list((OUT/'MaterialDiagnostics').glob('*.png'))
assert len(diagnostic)==4
validation={'pngs_verified':len(pngs),'dimensions':dimensions,'source_files_unchanged':report['source_files_unchanged'],
            'fresh_process_verification':verification}
(OUT/'delivery_validation.json').write_text(json.dumps(validation,indent=2),encoding='utf8')

shots=[]
for run in sorted((ROOT/'studies').iterdir()):
    path=run/'report.json'
    if not path.exists():continue
    r=json.loads(path.read_text(encoding='utf8'))
    if r.get('phase')!='complete' or r['spec']['mode']!='scout':continue
    for job in r['jobs']:
        image=Path(job['images'][0]);rel=os.path.relpath(image,OUT).replace('\\','/')
        shots.append(f'<figure><a href="{html.escape(rel)}"><img loading="lazy" src="{html.escape(rel)}" alt="{html.escape(job["name"])}"></a><figcaption>{html.escape(job["name"])}</figcaption></figure>')
data=[]
for p in diagnostic:
    if 'FinalImage.' in p.name:continue
    label=p.name.split('FinalImage',1)[1].split('.')[0]
    data.append(f'<figure><a href="MaterialDiagnostics/{p.name}"><img loading="lazy" src="MaterialDiagnostics/{p.name}" alt="{label}"></a><figcaption>{label} · 显示用途，非线性数值测量</figcaption></figure>')
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Central Research · 主镜头与材质验证</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#151515;color:#ddd;font:15px/1.65 system-ui,sans-serif}main{max-width:1500px;margin:auto;padding:28px}h1{font-size:26px;margin:0}h2{font-size:20px;margin-top:36px}p{max-width:1000px;color:#bbb}a{color:#bad0e0}button,select,input{font:inherit}button,select{background:#292929;color:#eee;border:1px solid #555;padding:7px 12px;margin:0 8px 8px 0}.compare{position:relative;aspect-ratio:16/9;background:#000;overflow:hidden}.compare img{position:absolute;width:100%;height:100%;object-fit:contain}.before{clip-path:inset(0 50% 0 0)}.tag{position:absolute;top:12px;background:#111d;padding:4px 10px}.tag.right{right:12px}input{width:100%;margin:14px 0}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}figure{margin:0}figure img{display:block;width:100%}figcaption{font-size:13px;color:#bbb;padding:5px 0}.evidence{border-top:1px solid #444;border-bottom:1px solid #444;padding:14px 0}li{margin:8px 0}@media(max-width:800px){main{padding:16px}.grid{grid-template-columns:1fr}}
</style><main>
<h1>Central Research · 主镜头与材质验证</h1>
<p>本轮完成机位筛选、材质适配和静态灯光验证。不是作品集最终验收，也未验证实时性能。源场景与源纹理未覆盖。</p>
<p>远端平台机位保留楼梯引导线和树木尺度，避免原镜头近距离树干遮挡。下方三组是同相机、同曝光、同分辨率 MRQ 输出。</p>
<button onclick="choose('MaterialOnly')">仅材质：检查修正影响</button><button onclick="choose('Lookdev')">材质＋灯光：当前方案</button>
<div class="compare"><img id="after" src="Lookdev/LS_Lookdev.0000.png" alt="当前灯光材质"><img id="before" class="before" src="Baseline/LS_Baseline.0000.png" alt="上一版相同机位"><span class="tag">左：上一版同机位</span><span id="rightLabel" class="tag right">右：材质＋灯光</span></div>
<label>拖动分界线<input id="split" type="range" min="0" max="100" value="50"></label>
<p><a href="Final4K/LS_Lookdev.0000.png">打开当前 3840×2160 原图</a> · <a href="report.json">本轮记录</a> · <a href="final_verification.json">新进程验证</a> · <a href="delivery_validation.json">输出检查</a></p>
<div class="evidence">__EVIDENCE__</div>
<h2>实际完成的技术调整</h2><ul>
<li>在独立父材质中按实际纹理设置 Normal / Masks / Color 采样器，保留原纹理绑定和光滑度转粗糙度逻辑。</li>
<li>提供 LP_RoughnessFloor 与 LP_SpecularScale；只对树叶增加双面植被着色和 LP_Transmission。它们是 UE 适配与艺术控制，不是原 Northlight 着色器的完整复现。</li>
<li>保留同机位 Baseline、MaterialOnly、Lookdev 三份独立关卡，以区分材质与光照的影响。</li>
</ul>
<h2>材质诊断</h2><div class="grid">__DIAGNOSTICS__</div>
<p>诊断输出关闭了多采样效果以便观察缓冲，不用于和美观图逐像素作数值误差比较。Base Color 图中植被墙本身已有浅色叶片，不能把所有浅色都当作曝光或高光错误。</p>
<h2>机位试拍 · 相同基础光照</h2><div class="grid">__SHOTS__</div>
<h2>尚未通过的验收</h2><ul>
<li>树干仍有源几何／UV 接缝，材质适配没有修复网格。</li>
<li>上层大面积黑区、局部材质重复和灯光焦点仍需继续处理。</li>
<li>一个电梯材质因缺少合适法线输入未自动适配；旧验证玻璃材质仍有工程既有编译警告。</li>
<li>尚无动态镜头稳定性、GPU 帧时、显存预算或跨场景工具验收；不能宣称已达到生产交付标准。</li>
</ul><p>资产来源：《Control》；本轮贡献为 UE 材质适配、灯光、相机、自动化与验证。原资产权利归原作者。</p>
<p>方法参考：<a href="https://dev.epicgames.com/documentation/unreal-engine/physically-based-materials-in-unreal-engine">Epic PBR 材质文档</a>。实际验收以本工程输出和记录为准。</p>
</main><script>
const split=document.getElementById('split');split.oninput=()=>document.getElementById('before').style.clipPath='inset(0 '+(100-split.value)+'% 0 0)';
function choose(name){document.getElementById('after').src=name+'/LS_'+name+'.0000.png';document.getElementById('rightLabel').textContent=name==='MaterialOnly'?'右：仅材质修正':'右：材质＋灯光';}
</script></html>'''
evidence=f"已验证：{verification['material_slots_verified']} 个材质槽 · {verification['instances_verified']} 个私有实例 · {verification['parents_verified']} 个父材质 · {verification['source_packages_verified']} 个源文件哈希未变。新进程回读与 4K MRQ 输出成功。"
page=page.replace('__EVIDENCE__',evidence).replace('__SHOTS__',''.join(shots)).replace('__DIAGNOSTICS__',''.join(data))
(OUT/'review.html').write_text(page,encoding='utf8')
print(json.dumps({'review':str(OUT/'review.html'),'pngs_verified':len(pngs),'scout_views':len(shots)},ensure_ascii=False))
