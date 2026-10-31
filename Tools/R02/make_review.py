"""Build a local evidence index from real completed capture manifests."""
import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def build(folders):
    output = ROOT / 'Preview/R02/index.html'
    output.parent.mkdir(parents=True, exist_ok=True)
    sections = []
    for folder in folders:
        manifest = json.loads((folder / 'result.json').read_text(encoding='utf-8-sig'))
        if manifest.get('status') != 'completed' or manifest.get('mode') != 'capture':
            raise ValueError('Only completed capture runs are accepted: ' + str(folder))
        images = []
        for record in manifest['captures']:
            path = Path(record['file'])
            if not path.is_file():
                raise FileNotFoundError(path)
            relative = Path('../../Verification/R02') / folder.name / path.name
            label = record['camera']['name'] + ' / ' + record['scenario']['name']
            images.append('<figure><a href="%s"><img loading="lazy" src="%s" alt="%s"></a><figcaption>%s</figcaption></figure>' %
                          (html.escape(relative.as_posix()), html.escape(relative.as_posix()), html.escape(label), html.escape(label)))
        sections.append('<section><h2>%s</h2><p>%d captures · restoration %s · exposure bias +2 EV · actual engine-time snapshots</p><div class="grid">%s</div></section>' %
                        (html.escape(folder.name), len(images), manifest.get('restore_matches'), ''.join(images)))
    document = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>R02 weather acceptance evidence</title><style>
body{margin:32px;background:#17191c;color:#e9e9e9;font:15px/1.6 system-ui,sans-serif}h1{font-size:26px}h2{font-size:18px;margin-top:32px}
p{color:#bbc0c8}a{color:inherit}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}figure{margin:0}img{width:100%;display:block}figcaption{padding:7px 0;font-family:monospace}
@media(max-width:900px){.grid{grid-template-columns:1fr}}
</style><h1>R02 天气材质 · 实际截图证据</h1><p>点击图片查看原始 1920×1080 PNG。这里展示参数状态与材质外观；截图采用实际引擎时间，不用于逐像素同步差分，也不证明实时 FPS 或完整动态验收。</p>''' + ''.join(sections) + '</html>'
    output.write_text(document, encoding='utf-8')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folders', type=Path, nargs='+')
    args = parser.parse_args()
    print(build([p.resolve() for p in args.folders]))
