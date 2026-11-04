# Phase06：流畅离线录制与展示预览

本轮已经生成两份可播放视频：完整64秒轨迹和24秒三机位预览，均为1280×720、30帧/秒；每帧对应实际模拟步骤，没有插值补帧。**采用固定时间步离线录制，不代表实时30FPS或新版性能验收。** 视频内有OFFLINE标注。

## 当前入口

研究工程：`D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy/FluidNinjaLive.uproject`。

展示关卡：`/Game/MudStudy/Professional/Phase06/L_Mud_Showcase`，序列 `LS_Mud_Showcase`。它们复制/重建自Phase05，轨迹仍为原来的60秒；运行会自动播放。使用Phase04材质，算法没有因拍摄而更换。

- **24秒预览**：`Verification/MudProfessional/phase06-capture/20261029T115117299189Z/showcase_720p30_offline.mp4`。
- **64秒完整轨迹**：`Verification/MudProfessional/phase06-capture/20261029T113604578794Z/replay_720p30_offline.mp4`。

两份均通过完整解码检查。ffprobe确认短片720帧、24秒，长片1920帧、64秒，H.264、30/1帧率。

## 为什么之前只有3帧

通过研究UE进程内部枚举自身HWND，确认主窗口确实最小化。UE5.8 EditorEngine.cpp 的ShouldThrottleCPUUsage除普通后台节流设置外，还检查AreAllWindowsHidden；GetMaxTickRate在节流时返回3。仅修改bThrottleCPUWhenNotForeground不足以处理最小化。

新增 `research_window.py`，只查找当前PID、标题完全匹配的研究编辑器主窗口；采集期间以SW_SHOWNOACTIVATE恢复，结束用SW_SHOWMINNOACTIVE恢复原最小化状态。不操作Stormfall或其他进程，不要求前台激活。它通过execute_python使用Win32 API，因为当前桥接缺少相应窗口控制。

恢复窗口后，实际时钟采集仍有明显掉帧。关闭主视口实时绘制并暂用Wireframe可降低重复渲染负担；采集相机使用独立Lit显示标志，输出图像仍有光照和材质。诊断曾观测主视口绘制时约120ms、暂停主视口绘制后编辑器约16.7ms，但这些数值不等于泥浆的独占GPU成本，也不能代替当前移动场景的无干扰测量。

## 录制方法及边界

使用UE内置t.OverrideFPS=30固定模拟时间步，并以每1/30秒一次的相机采集保存独立图像；实际墙钟可以更慢。完整64秒录制用约343.812秒，24秒展示录制用约40.25秒。此方法是离线记录效果，而不是用设置值替代实测实时帧率。结束已恢复t.OverrideFPS=0、t.MaxFPS=0、Slate.bAllowThrottling=1和原后台节流选项。

同步RenderingLibrary PNG导出替换为ImageWriteQueue异步JPG95；结束等待每个文件头尾完整后才宣布完成。JPEG及H.264均为有损编码，图像不用于逐像素算法精度比较。数值验证仍来自单独GPU读回。原先PNG尾部多余数据的问题没有在引擎中修改，新录制流程避开了旧导出函数。

临时关闭主视口实时绘制、使用Wireframe仅用于采集期间减轻重复绘制。结束恢复Lit、重新启用视口实时更新；原先四视口实时状态不一致，原生工具按组设置，结束四视口统一启用。没有保存全局配置。研究窗口已恢复最小化。

## 展示变化

新关卡的SkyLight由SunsetAmbientCubemap切换为引擎DaylightAmbientCubemap，并加入匹配背景球；背景关闭阴影和碰撞。均为引擎资源，不是个人制作的HDR。捕获采用手动曝光，补偿+1.25，关闭物理相机曝光。

短片0–8秒为全景，8–16秒为跟随近景，16–24秒为掠射跟随近景。各帧camera字段保留实际位置、角度和镜头名；镜头切换重置相机历史，持续捕获状态用于TAA/速度历史。灯光、曝光、机位变化使其不能直接与旧暗场截图作算法画质差异量化。

近景暴露出待解决问题：POM改变虚拟表面的深度，但球体轨迹的几何接触高度仍基于平面，部分位置可见间隙。此轮没有把球体手动下沉来宣称接触正确，也没有实现高度场碰撞。球体还是调试夹具，不是人物步态演示；背景可读性、干湿层次与最终场景构图仍有改进空间。

## 已检查的证据

完整轨迹：1920帧，640个位置样本，路径最大误差约2.27e-13cm；直行、转弯、停留、返回、越界和终点均覆盖。11次局部GPU读回（状态和法线各256像素），有限值、高度复制和纹理绑定检查通过；最大采样速度约2.46875。完整记录不保证所有像素/所有时刻、帧率无关性或与原版动态等价。

短片：720帧、240个位置样本，路径最大误差约6.36e-14cm；覆盖直行、转弯、停留、再次移动。4次256像素局部GPU检查通过，最大采样速度约0.341797。使用short-preview验证范围，不声称短片覆盖边界和全程停留。

两份帧时间间隔均为约0.033333335秒，没有重复帧补足采样。旧3Hz、实际时钟及适配失败记录保留，不计入最终成片验证。实时钟720p试录目录20261029T113233282687Z虽有500帧，但最大间隔约0.417秒，不能当作稳定30Hz采集通过。

run.json、冻结harness.py/research_window.py、validation.json、原始JPG、字幕滤镜与MP4都保留。新关卡/序列快照及完整性记录位于本阶段Assets/integrity.json。此前125个基线及阶段资产哈希未变；当前只新增Phase06关卡和序列，没有修改引擎、插件或Shader代码。

## 重跑

先在研究工程打开对应地图、退出PIE。采集时主视口临时使用Wireframe并关闭实时绘制；独立相机保持Lit。导入 `mud_replay_capture`：

`start(width=1280,height=720,frame_interval=1/30,duration=24,output_group='phase06-capture',fixed_fps=30,map_path='/Game/MudStudy/Professional/Phase06/L_Mud_Showcase',exposure_bias=1.25,camera_mode='showcase_short')`

完整轨迹用Phase05地图，duration=64、camera_mode='wide'、exposure_bias=0。采集脚本会恢复窗口、时钟及其自身临时设置；主视口模式/实时及手动改动的Slate设置需按上面的记录另行恢复。若中断可调用stop()清理。禁止在R02工程直接执行。

`python Tools/MudStudy/verify_replay_capture.py <目录> --scope short-preview` 检查短片；完整轨迹省略scope。仅复核已有记录，不启动UE。固定步录制使用 `ffmpeg -framerate 30 -i frames/frame_%06d.jpg`，直接编码已采集帧，并叠加OFFLINE标识。

下一步优先修复视觉深度与物体接触高度的关系，再对当前版本做脱离采集的代表场景成本比较；目前还不能用这份视频证明实时30FPS。
