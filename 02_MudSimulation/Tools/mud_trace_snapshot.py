"""Transient same-camera capture and trace readback; no UE assets saved."""
import json,math
from pathlib import Path
import unreal as u
OUT=Path('D:/aco/unreal/Stormfall/Verification/MudProfessional/phase18-visible-trails')

def snapshot(name,area='thin'):
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    capactor=actors['Mud_Replay_Capture'];cap=capactor.get_component_by_class(u.SceneCaptureComponent2D)
    rt=u.RenderingLibrary.create_render_target2d(world,1280,720,u.TextureRenderTargetFormat.RTF_RGBA8,u.LinearColor(0,0,0,1),False,False)
    center=-2320 if area=='thin' else 2200
    pos=u.Vector(center,950,700);delta=u.Vector(center,0,0)-pos
    capactor.set_actor_location(pos,False,True)
    capactor.set_actor_rotation(u.Rotator(pitch=math.degrees(math.atan2(delta.z,math.hypot(delta.x,delta.y))),yaw=-90,roll=0),False)
    cap.set_editor_property('texture_target',rt)
    cap.set_editor_property('capture_source',u.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    cap.set_editor_property('capture_every_frame',False);cap.set_editor_property('capture_on_movement',False)
    cap.set_editor_property('fov_angle',65)
    pp=cap.get_editor_property('post_process_settings')
    for k,v in [('override_auto_exposure_method',True),('auto_exposure_method',u.AutoExposureMethod.AEM_MANUAL),
                ('override_auto_exposure_bias',True),('auto_exposure_bias',2.75),
                ('override_auto_exposure_apply_physical_camera_exposure',True),('auto_exposure_apply_physical_camera_exposure',False)]:
        pp.set_editor_property(k,v)
    cap.set_editor_property('post_process_settings',pp);cap.set_editor_property('post_process_blend_weight',1)
    cap.capture_scene()
    options=u.ImageWriteOptions()
    options.set_editor_property('format',u.DesiredImageFormat.PNG)
    options.set_editor_property('bAsync',False);options.set_editor_property('overwrite_file',True)
    u.ImageWriteBlueprintLibrary.export_to_disk(rt,str(OUT/(name+'.png')),options)
    cap.set_editor_property('texture_target',None)
    return str(OUT/(name+'.png'))

def roi(actor):
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    rt=actor.get_editor_property('output')
    # UE 5.8 implementation passes MaxX/MaxY through as width/height.
    pixels=u.RenderingLibrary.read_render_target_raw_pixel_area(world,rt,400,930,1150,190,False)
    values=[p.a for p in pixels]
    return {'count':len(values),'max':max(values),'sum':sum(values),'mean':sum(values)/len(values),
            'positive_pixels':sum(v>.01 for v in values),'finite':all(math.isfinite(v) for v in values)}

REC={}
def recover(actor,seconds=8):
    w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    REC.clear();REC.update(actor=actor,world=w,start=u.GameplayStatics.get_time_seconds(w),before=roi(actor),seconds=seconds)
    def tick(dt):
        elapsed=u.GameplayStatics.get_time_seconds(w)-REC['start']
        if elapsed<seconds:return
        u.unregister_slate_post_tick_callback(REC['handle'])
        u.GameplayStatics.set_game_paused(w,True)
        after=roi(actor);before=REC['before']
        result={'before':before,'after':after,'elapsed_game_seconds':elapsed,'sum_ratio':after['sum']/before['sum'],
                'max_ratio':after['max']/before['max'],'half_life_seconds':8,'scope':'GPU output A from persistent Painter W; no character remains in the mud.'}
        (OUT/'recovery.json').write_text(json.dumps(result,indent=2))
    REC['handle']=u.register_slate_post_tick_callback(tick)
    u.GameplayStatics.set_game_paused(w,False)
