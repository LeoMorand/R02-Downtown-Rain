"""Compare zero-interaction original and authored solvers at matching reset/frame counts.

Only PIE instance properties are changed. End PIE restores the source scene.
"""
import unreal as u,json,math
from pathlib import Path
OUT=Path('D:/aco/unreal/Stormfall/Verification/MudSolver');STATE={}

def read(rt,index):
    w=STATE['world'];mid=STATE['mids'][index];small=STATE['targets'][index]
    mid.set_texture_parameter_value('Buffer',rt)
    u.RenderingLibrary.draw_material_to_render_target(w,small,mid)
    pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(w,small,0,0,64,64,False)
    return [[p.r,p.g,p.b] for p in pixels]

def start_zero_input():
    assert not STATE.get('handle')
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();assert w
    actors=u.GameplayStatics.get_all_actors_of_class(w,u.Actor)
    source=next(a for a in actors if a.get_actor_label()=='NinjaLive_Mud1').get_editor_property('NinjaLiveComponent')
    own=next(a for a in actors if a.get_actor_label()=='Mud_Rebuilt_Runtime')
    assert source.get_editor_property('RT_VelocityDensity'),'Activate original first'
    source.set_editor_property('BrushStrength',0)
    source.set_editor_property('EnableMeshDistanceFieldReader',False)
    own.set_editor_property('brush_actors',[]);own.set_editor_property('track_player',False)
    material=u.load_asset('/Game/MudStudy/Rebuild/Materials/M_LiveRT_Probe');assert material
    mids=[u.MaterialLibrary.create_dynamic_material_instance(w,material) for _ in range(2)]
    targets=[u.RenderingLibrary.create_render_target2d(w,64,64,u.TextureRenderTargetFormat.RTF_RGBA32F,u.LinearColor(0,0,0,0),False,False) for _ in range(2)]
    STATE.clear();STATE.update(world=w,source=source,own=own,mids=mids,targets=targets,
        start=u.GameplayStatics.get_time_seconds(w),reset=False,frame=0,last_time=-1,samples=[])
    def tick(dt):
        try:
            now=u.GameplayStatics.get_time_seconds(w)
            if not STATE['reset']:
                if now-STATE['start']<2:return
                source.reinitialize_system();own.rebuild_simulation()
                STATE['reset']=True;STATE['last_time']=now;return
            if now==STATE['last_time']:return
            STATE['last_time']=now;STATE['frame']+=1
            if STATE['frame'] not in [1,4,16,64,128,256]:return
            a=read(source.get_editor_property('RT_VelocityDensity'),0)
            b=read(own.get_editor_property('output'),1)
            errors=[[abs(x-y) for x,y in zip(p,q)] for p,q in zip(a,b)]
            row={'frame':STATE['frame'],'finite':all(math.isfinite(v) for image in [a,b] for p in image for v in p),
                'max_rgb_error':[max(p[k] for p in errors) for k in range(3)],
                'mean_rgb_error':[sum(p[k] for p in errors)/len(errors) for k in range(3)],
                'original_range_b':[min(p[2] for p in a),max(p[2] for p in a)],
                'rebuilt_range_b':[min(p[2] for p in b),max(p[2] for p in b)]}
            STATE['samples'].append(row)
            (OUT/'paired_zero_input.json').write_text(json.dumps({'complete':STATE['frame']==256,'samples':STATE['samples']},indent=2))
            if STATE['frame']==256:
                u.unregister_slate_post_tick_callback(STATE['handle']);STATE['handle']=None
        except Exception as e:
            u.unregister_slate_post_tick_callback(STATE['handle']);STATE['handle']=None
            (OUT/'paired_zero_input.json').write_text(json.dumps({'complete':False,'error':str(e),'samples':STATE['samples']},indent=2))
    STATE['handle']=u.register_slate_post_tick_callback(tick)
    return {'scheduled':True,'frames':256,'changes':'PIE-only brush strength and SDF disable for controlled comparison'}
