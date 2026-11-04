"""Dedicated editor: inspect v04, capture baseline, build private lighting, capture result.

Run with Launch.ps1. Never execute this entry point in the artist's editor.
All UE access happens on the editor thread; capture warmup spans real ticks.
"""
import datetime
import hashlib
import json
import time
import traceback
import sys
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent
assert '-ResearchRender' in u.SystemLibrary.get_command_line(), 'Dedicated process required'
u.EditorPythonScripting.set_keep_python_script_alive(True)
assert Path(u.Paths.get_project_file_path()).resolve() == PROJECT / 'Stormfall.uproject'
SPEC = json.loads((ROOT / 'preset.json').read_text(encoding='utf8'))
RUN_ID = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
OUT = ROOT / 'runs' / RUN_ID
OUT.mkdir(parents=True)
DEST = '/Game/Control_Dev/CentralResearch/Render/R_' + RUN_ID
MAP = DEST + '/L_ResearchRender'
E = u.get_editor_subsystem(u.EditorActorSubsystem)
LS = u.get_editor_subsystem(u.LevelEditorSubsystem)
LIB = u.MaterialEditingLibrary
STATE = {'phase':'initializing','run':RUN_ID,'source':SPEC['source_map'],
         'output_map':MAP,'errors':[],'captures':[], 'preset':SPEC}
HANDLE = None
CAPTURE = None
RT = None
BUSY = False
STARTED = time.monotonic()
SINCE = STARTED


def write():
    (OUT / 'report.json').write_text(json.dumps(STATE,indent=2),encoding='utf8')
    (ROOT / 'latest.txt').write_text(str(OUT),encoding='utf8')


def source_hashes():
    paths = [PROJECT / 'Content' / (SPEC['source_map'][6:]+'.umap')]
    paths += list((PROJECT/'Content/Control_Assets/Materials').rglob('*.uasset'))
    paths += list((PROJECT/'Content/Control_Assets/EP101/Materials').rglob('*.uasset'))
    paths += list((PROJECT/'Content/Control_Dev/CentralResearch/Materials').rglob('*.uasset'))
    return {str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def snapshot():
    result={}
    for a in E.get_all_level_actors():
        if not isinstance(a,u.StaticMeshActor):continue
        c=a.static_mesh_component
        result[a.get_actor_label()]={'transform':a.get_actor_transform().export_text(),
            'mesh':c.static_mesh.get_path_name() if c.static_mesh else None,
            'visible':c.is_visible(),
            'materials':[m.get_path_name() if m else None for m in c.get_materials()]}
    return result


def audit():
    mats={}; lights=[]
    for a in E.get_all_level_actors():
        if isinstance(a,u.Light):
            c=a.get_component_by_class(u.LightComponent)
            lights.append({'label':a.get_actor_label(),'class':a.get_class().get_name(),
                           'intensity':c.get_editor_property('intensity')})
        for c in a.get_components_by_class(u.StaticMeshComponent):
            for i,m in enumerate(c.get_materials()):
                path=m.get_path_name() if m else '<None>'
                if path not in mats:
                    item={'users':[], 'scalar':{},'vector':{},'textures':{}}
                    if isinstance(m,u.MaterialInstanceConstant):
                        item['parent']=m.get_editor_property('parent').get_path_name()
                        for n in LIB.get_scalar_parameter_names(m.get_base_material()):
                            item['scalar'][str(n)]=LIB.get_material_instance_scalar_parameter_value(m,n)
                        for n in LIB.get_vector_parameter_names(m.get_base_material()):
                            v=LIB.get_material_instance_vector_parameter_value(m,n)
                            item['vector'][str(n)]=[v.r,v.g,v.b,v.a]
                        for n in LIB.get_texture_parameter_names(m.get_base_material()):
                            t=LIB.get_material_instance_texture_parameter_value(m,n)
                            item['textures'][str(n)]=t.get_path_name() if t else None
                    mats[path]=item
                mats[path]['users'].append({'actor':a.get_actor_label(),'component':c.get_name(),'slot':i})
    (OUT/'inventory.json').write_text(json.dumps({'materials':mats,'lights':lights},indent=2),encoding='utf8')
    STATE['unique_materials']=len(mats)


def resolve_frame():
    anchor=next(a for a in E.get_all_level_actors() if a.get_actor_label()=='CR_04486_research_sector_lobby_main_new')
    p=anchor.get_actor_location();offset=[p.x-4000,p.y-15200,p.z]
    assert abs(anchor.get_actor_rotation().yaw)<0.01,'Rotated anchor needs explicit frame conversion'
    def shift(v):return [v[i]+offset[i] for i in range(3)]
    SPEC['camera']['location']=shift(SPEC['camera']['location'])
    SPEC['camera']['target']=shift(SPEC['camera']['target'])
    for light in SPEC['lights']:
        light['location']=shift(light['location']);light['target']=shift(light['target'])
    STATE['anchor_offset']=offset


def capture_setup():
    global CAPTURE,RT
    v=SPEC['camera'];loc=u.Vector(*v['location']);target=u.Vector(*v['target'])
    CAPTURE=E.spawn_actor_from_class(u.SceneCapture2D,loc)
    CAPTURE.set_actor_label('RR_TransientCapture')
    CAPTURE.set_actor_rotation(u.MathLibrary.find_look_at_rotation(loc,target),False)
    c=CAPTURE.capture_component2d
    c.capture_every_frame=True;c.capture_on_movement=False
    c.set_editor_property('always_persist_rendering_state',True)
    c.fov_angle=v['fov']
    RT=u.RenderingLibrary.create_render_target2d(
        u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),
        SPEC['width'],SPEC['height'],u.TextureRenderTargetFormat.RTF_RGBA8)
    c.texture_target=RT;c.capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR
    # Explicit opt-in for Lumen in this capture; not a global CVar mutation.
    s=c.post_process_settings
    for name,value in [('dynamic_global_illumination_method',u.DynamicGlobalIlluminationMethod.LUMEN),
                       ('reflection_method',u.ReflectionMethod.LUMEN)]:
        s.set_editor_property('override_'+name,True);s.set_editor_property(name,value)
    c.post_process_settings=s
    u.AutomationLibrary.finish_loading_before_screenshot()


def capture(name):
    c=CAPTURE.capture_component2d;c.capture_scene()
    u.RenderingLibrary.export_render_target(
        u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),RT,str(OUT),name+'.png')
    assert (OUT/(name+'.png')).is_file()
    STATE['captures'].append(name+'.png')


def apply_look():
    # Only diagnostics in the private map are changed. Original geometry and textures stay intact.
    for a in E.get_all_level_actors():
        if isinstance(a,u.Light) and a.get_actor_label().startswith('Diagnostic_'):
            a.get_component_by_class(u.LightComponent).set_intensity(0.)
        if isinstance(a,u.PostProcessVolume):
            s=a.settings
            for name,value in [('auto_exposure_min_brightness',1.),('auto_exposure_max_brightness',1.),
                               ('auto_exposure_bias',SPEC['exposure_bias']),('ambient_cubemap_intensity',SPEC['ambient_intensity']),
                               ('motion_blur_amount',0.)]:
                s.set_editor_property('override_'+name,True);s.set_editor_property(name,value)
            a.settings=s
    for light in SPEC['lights']:
        loc=u.Vector(*light['location']);rot=u.MathLibrary.find_look_at_rotation(loc,u.Vector(*light['target']))
        a=E.spawn_actor_from_class(u.RectLight,loc,rot);a.set_actor_label('RR_'+light['name'])
        a.set_folder_path('ResearchRender/Lights')
        c=a.get_component_by_class(u.RectLightComponent);c.set_mobility(u.ComponentMobility.MOVABLE)
        c.set_editor_property('intensity_units',u.LightUnits.LUMENS)
        c.set_intensity(light['lumens']);c.set_light_color(u.LinearColor(*light['color'],1.))
        c.set_attenuation_radius(light['radius']);c.set_editor_property('source_width',light['width'])
        c.set_editor_property('source_height',light['height']);c.set_editor_property('cast_shadows',True)
    # Store a real camera alongside the reproducible capture pose.
    v=SPEC['camera'];loc=u.Vector(*v['location'])
    cam=E.spawn_actor_from_class(u.CameraActor,loc,u.MathLibrary.find_look_at_rotation(loc,u.Vector(*v['target'])))
    cam.set_actor_label('RR_Hero');cam.camera_component.set_field_of_view(v['fov'])
    u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(loc,cam.get_actor_rotation())


def apply_material_groups():
    replacements={};assignments=[];unsupported=set()
    for a in E.get_all_level_actors():
        for c in a.get_components_by_class(u.StaticMeshComponent):
            for i,m in enumerate(c.get_materials()):
                if not isinstance(m,u.MaterialInstanceConstant):continue
                path=m.get_path_name()
                group=next((g for g in SPEC.get('material_groups',[]) if any(k in path.lower() for k in g['contains'])),None)
                if not group:continue
                if path not in replacements:
                    names={str(n) for n in LIB.get_vector_parameter_names(m.get_base_material())}
                    param=next((n for n in ['ControlColorMultiplier','CR_Color'] if n in names),None)
                    if not param:
                        unsupported.add(path);continue
                    dest=DEST+'/Materials/'+m.get_name()+'_'+hashlib.sha256(path.encode()).hexdigest()[:8]
                    mi=u.EditorAssetLibrary.duplicate_asset(path,dest)
                    assert mi,'Material instance duplication failed'
                    v=LIB.get_material_instance_vector_parameter_value(m,param);t=group['tint']
                    wanted=u.LinearColor(v.r*t[0],v.g*t[1],v.b*t[2],v.a)
                    LIB.set_material_instance_vector_parameter_value(mi,param,wanted)
                    LIB.update_material_instance(mi)
                    actual=LIB.get_material_instance_vector_parameter_value(mi,param)
                    assert max(abs(x-y) for x,y in zip([actual.r,actual.g,actual.b,actual.a],[wanted.r,wanted.g,wanted.b,wanted.a]))<1e-5
                    assert u.EditorAssetLibrary.save_loaded_asset(mi)
                    replacements[path]=mi
                c.set_material(i,replacements[path])
                assignments.append({'actor':a.get_actor_label(),'component':c.get_name(),'slot':i,
                                    'original':path,'replacement':replacements[path].get_path_name()})
    (OUT/'material_assignments.json').write_text(json.dumps(assignments,indent=2),encoding='utf8')
    STATE['material_instances_created']=len(replacements)
    STATE['material_slots_adjusted']=len(assignments)
    STATE['unsupported_materials']=sorted(unsupported)


def geometry_only(snap):
    return {k:{n:v for n,v in row.items() if n!='materials'} for k,row in snap.items()}


def finish(error=None):
    if error:STATE['errors'].append(error)
    STATE['phase']='failed' if error else 'complete'
    STATE['elapsed_seconds']=time.monotonic()-STARTED
    write()
    if HANDLE:u.unregister_slate_post_tick_callback(HANDLE)
    u.SystemLibrary.quit_editor()


def tick(delta):
    global BUSY,SINCE,CAPTURE,RT
    if BUSY:return
    BUSY=True
    try:
        now=time.monotonic()
        if now-STARTED>600:raise RuntimeError('Render warmup/capture timed out')
        phase=STATE['phase']
        if phase=='initializing':
            STATE['source_hashes']=source_hashes()
            assert LS.load_level(SPEC['source_map'])
            resolve_frame()
            STATE['source_geometry']=snapshot();audit()
            capture_setup();STATE['phase']='baseline_warmup';SINCE=time.monotonic();write()
        elif phase=='baseline_warmup' and now-SINCE>SPEC['warmup_seconds']:
            capture('before')
            E.destroy_actor(CAPTURE);CAPTURE=None;RT=None
            assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),MAP)
            assert LS.load_level(MAP)
            apply_look()
            assert snapshot()==STATE['source_geometry'],'Unexpected changes before material adjustment'
            apply_material_groups()
            expected=snapshot()
            assert geometry_only(expected)==geometry_only(STATE['source_geometry']),'Geometry changed'
            assert LS.save_current_level()
            assert LS.load_level(MAP)
            assert snapshot()==expected,'Saved/reloaded geometry or material mismatch'
            sys.path.insert(0,str(ROOT))
            try:
                import mrq
                hero=next(a for a in E.get_all_level_actors() if a.get_actor_label()=='RR_Hero')
                STATE['mrq']=mrq.prepare(DEST,MAP,hero,OUT)
            except Exception:
                STATE['mrq_unavailable']=traceback.format_exc()
            capture_setup();STATE['phase']='look_warmup';SINCE=time.monotonic();write()
        elif phase=='look_warmup' and now-SINCE>SPEC['warmup_seconds']:
            capture('after')
            E.destroy_actor(CAPTURE);CAPTURE=None
            STATE['source_files_unchanged']=source_hashes()==STATE['source_hashes']
            assert STATE['source_files_unchanged'],'Source package changed'
            STATE['geometry_verified']=len(STATE.pop('source_geometry'))
            if 'mrq' in STATE:
                # Keep this warmed process: no second editor startup for the real preview.
                STATE['phase']='complete';STATE['elapsed_seconds']=time.monotonic()-STARTED;write()
                u.unregister_slate_post_tick_callback(HANDLE)
                global _MRQ_SESSION
                _MRQ_SESSION={'__file__':str(ROOT/'final.py'),'FORCE_DRAFT':True}
                exec(compile((ROOT/'final.py').read_text(encoding='utf8'),str(ROOT/'final.py'),'exec'),_MRQ_SESSION)
            else:finish()
    except Exception:finish(traceback.format_exc())
    finally:BUSY=False


write()
HANDLE=u.register_slate_post_tick_callback(tick)
