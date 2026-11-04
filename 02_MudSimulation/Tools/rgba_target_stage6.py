"""Verify true signed RGBA material writes for the standalone RT solver."""
import sys,json
from pathlib import Path
import unreal as u
TOOLS=Path(__file__).parent
if str(TOOLS) not in sys.path:sys.path.insert(0,str(TOOLS))
from build_display_stage1 import Graph
from build_painter_stage5 import world,target
OUT=TOOLS.parents[1]/'Verification/MudSolver'
def configure_rgba(g,rgb,alpha,rgb_port='',alpha_port=''):
    g.mat.set_editor_property('blend_mode',u.BlendMode.BLEND_ALPHA_COMPOSITE)
    g.mat.set_editor_property('allow_negative_emissive_color',True)
    g.output(rgb,'EMISSIVE_COLOR',rgb_port);g.output(alpha,'OPACITY',alpha_port)
def build():
    world();g=Graph('M_Solver_RGBAWriteFixture')
    g.node('Value','VectorParameter',parameter_name='Value',default_value=u.LinearColor(-.2,.3,.7,.4))
    configure_rgba(g,'Value','Value',alpha_port='A')
    return g.finish()
def verify():
    w=world();rt=target(w);mid=u.MaterialLibrary.create_dynamic_material_instance(w,u.load_asset('/Game/MudStudy/Rebuild/Materials/M_Solver_RGBAWriteFixture'))
    rows=[]
    for value in [(-.2,.3,.7,.4),(1.5,-2,.01,1),(0,0,.5,0),(-.5,.8,.2,.01)]:
        u.RenderingLibrary.clear_render_target2d(w,rt,u.LinearColor(0,0,0,0))
        mid.set_vector_parameter_value('Value',u.LinearColor(*value));u.RenderingLibrary.draw_material_to_render_target(w,rt,mid)
        pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(w,rt,0,0,32,32,False)
        error=max(max(abs(getattr(c,k)-value[j]) for j,k in enumerate(['r','g','b','a'])) for c in pixels)
        rows.append({'value':value,'actual':[pixels[0].r,pixels[0].g,pixels[0].b,pixels[0].a],'max_error':error})
    result={'cases':rows,'pass':all(r['max_error']<1e-5 for r in rows)}
    (OUT/'rgba_write_verification.json').write_text(json.dumps(result,indent=2));assert result['pass'],result
    return result
