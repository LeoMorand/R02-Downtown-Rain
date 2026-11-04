"""MRQ preparation for a static hero frame; no console-variable quality shotgun."""
from pathlib import Path
import unreal as u


def prepare(dest, map_path, camera, output_dir):
    tools=u.AssetToolsHelpers.get_asset_tools()
    seq=tools.create_asset('LS_Hero',dest,u.LevelSequence,u.LevelSequenceFactoryNew())
    assert seq
    seq.set_display_rate(u.FrameRate(24,1));seq.set_playback_start(0);seq.set_playback_end(1)
    binding=seq.add_possessable(camera)
    cuts=seq.add_track(u.MovieSceneCameraCutTrack)
    section=cuts.add_section();section.set_range(0,1)
    camera_id=u.MovieSceneObjectBindingID()
    camera_id.set_editor_property('guid',binding.get_id())
    section.set_camera_binding_id(camera_id)
    assert u.EditorAssetLibrary.save_loaded_asset(seq)
    config=tools.create_asset('MRQ_Hero4K',dest,u.MoviePipelinePrimaryConfig,u.MoviePipelinePrimaryConfigFactory())
    assert config
    config.find_or_add_setting_by_class(u.MoviePipelineDeferredPassBase)
    config.find_or_add_setting_by_class(u.MoviePipelineImageSequenceOutput_PNG)
    output=config.find_or_add_setting_by_class(u.MoviePipelineOutputSetting)
    output.output_resolution=u.IntPoint(3840,2160)
    output.output_directory=u.DirectoryPath(str(Path(output_dir)/'Final4K'))
    output.file_name_format='{sequence_name}.{frame_number}'
    aa=config.find_or_add_setting_by_class(u.MoviePipelineAntiAliasingSetting)
    aa.spatial_sample_count=1;aa.temporal_sample_count=8
    aa.engine_warm_up_count=64;aa.render_warm_up_count=32
    aa.render_warm_up_frames=True
    assert u.EditorAssetLibrary.save_loaded_asset(config)
    return {'sequence':seq.get_path_name(),'config':config.get_path_name(),'map':map_path,
            'resolution':[3840,2160],'note':'Static hero frame; validate final render visually, independently of draft capture.'}
