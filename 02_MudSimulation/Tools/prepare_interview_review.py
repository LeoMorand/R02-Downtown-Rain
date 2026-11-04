"""Prepare review screenshots and copied source; never modifies the research project."""
import hashlib
import io
import json
import shutil
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from pygments import highlight
from pygments.lexers import CppLexer
from pygments.formatters import ImageFormatter

WORK = Path('D:/aco/unreal/Stormfall')
PROJECT = Path('D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy')
OUT = WORK / 'Deliverables/MudInterview_20261031'
SHOTS = OUT / 'Screenshots'
PACK = OUT / 'SourceAndAssets_Review'
SHOTS.mkdir(parents=True, exist_ok=True)
PACK.mkdir(parents=True, exist_ok=True)
manifest = []

def copy_file(source, relative):
    target = PACK / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    manifest.append(dict(path=relative.as_posix(), source=str(source), sha256=hashlib.sha256(target.read_bytes()).hexdigest(), bytes=target.stat().st_size))

for plugin in ['MudRuntime', 'MudShaderLab', 'MudAuthoring']:
    folder = PROJECT / 'Plugins' / plugin
    for source in folder.rglob('*'):
        rel = source.relative_to(folder)
        if source.is_file() and (rel.parts[0] in ['Source', 'Shaders'] or source.suffix == '.uplugin'):
            copy_file(source, source.relative_to(PROJECT))
for source in (PROJECT / 'Content/MudStudy/Professional/Phase18').glob('*'):
    if source.is_file(): copy_file(source, source.relative_to(PROJECT))
for name in ['BP_Mud_Manny.uasset', 'BP_Mud_GameMode.uasset']:
    source = PROJECT / 'Content/MudStudy/Professional/Phase11' / name
    copy_file(source, source.relative_to(PROJECT))
copy_file(PROJECT / 'FluidNinjaLive.uproject', Path('ProjectReference/FluidNinjaLive.uproject'))
for source in (WORK / 'Tools/MudStudy/Reference').glob('*'):
    if source.is_file(): copy_file(source, Path('Reference_HLSL') / source.name)
for name in ['MUD_PHASE18_TRACES.md', 'MUD_PHASE12_ARTIST.md', 'README_REBUILD.md']:
    copy_file(WORK / 'Tools/MudStudy' / name, Path('Notes') / name)

font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 23)
small = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 18)
cards = []
def code_card(filename, title, source, start=1, end=None, origin='research project source'):
    all_lines = source.read_text(encoding='utf-8-sig').splitlines()
    end = min(end or len(all_lines), len(all_lines))
    code = '\n'.join(all_lines[start-1:end]) + '\n'
    png = highlight(code, CppLexer(), ImageFormatter(font_name='Consolas', font_size=22, style='native', line_numbers=True, line_number_start=start, line_number_chars=4, line_number_pad=16, line_number_bg='#1b222b', line_number_fg='#8c9baa', image_pad=25, line_pad=5))
    body = Image.open(io.BytesIO(png)).convert('RGB')
    relative = source.relative_to(PROJECT) if source.is_relative_to(PROJECT) else source.relative_to(WORK)
    width = max(1550, body.width)
    canvas = Image.new('RGB', (width, body.height+160), '#15191e')
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 20), title, font=font, fill='#f1f5f9')
    label = relative.as_posix()
    if len(label)>110:
        cut = label.rfind('/',0,100)
        label = label[:cut+1]+'\n'+label[cut+1:]
    draw.multiline_text((28, 57), label, font=small, fill='#9dbad0', spacing=4)
    canvas.paste(body, (0, 115))
    draw.text((28, body.height+125), f'{origin} | lines {start}-{end} | source excerpt, not an IDE screenshot', font=small, fill='#9faab7')
    canvas.save(SHOTS / filename)
    cards.append(dict(image=filename, source=str(source), firstLine=start, lastLine=end, sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest()))

code_card('05_CPP_RT_Binding.png', 'C++ | Allocate output RT, bind Niagara, create surface MID', PROJECT/'Plugins/MudRuntime/Source/MudRuntime/Private/MudRuntime.cpp', 33, 53)
code_card('06_CPP_Leg_Interaction.png', 'C++ | Leg / surface intersections and stable input slots', PROJECT/'Plugins/MudShaderLab/Source/MudShaderIntegration/Private/MudArtistControls.cpp', 147, 184)
code_card('07_CPP_Artist_Controls.png', 'C++ | Artist-facing controls and display quality', PROJECT/'Plugins/MudShaderLab/Source/MudShaderIntegration/Public/MudArtistControls.h', 32, 51)
code_card('08_GPU_Height_Normal.png', 'GPU HLSL | Height-field derivatives to world-space normals', PROJECT/'Plugins/MudShaderLab/Shaders/Private/MudHeightNormal.usf')
history = WORK/'Tools/MudStudy/Reference/PainterTraceHistory.hlsl'
count = len(history.read_text().splitlines())
code_card('09_HLSL_Trail_History.png', 'Niagara HLSL | Persistent local imprints and decay', history, count-21, count, 'Niagara Custom HLSL source mirror')
code_card('10_HLSL_Export_Protocol.png', 'Niagara HLSL | Velocity / visual height / imprint export', WORK/'Tools/MudStudy/Reference/ExportTraceRelief.hlsl', origin='Niagara Custom HLSL source mirror')
code_card('11_HLSL_POM_Normal_Alignment.png', 'Material HLSL | Sample normals at the POM hit UV', WORK/'Tools/MudStudy/Reference/ComputedNormalPOMAlignment.hlsl', origin='Material Custom expression source mirror')
code_card('12_HLSL_Detail_Flow.png', 'Material HLSL | Signed velocity and two-phase detail flow', WORK/'Tools/MudStudy/Reference/DetailFlowPhases.hlsl', origin='Material Custom expression source mirror')
(OUT/'source-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
(OUT/'code-image-index.json').write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(dict(copiedFiles=len(manifest), codeImages=len(cards), output=str(OUT)),ensure_ascii=False))
