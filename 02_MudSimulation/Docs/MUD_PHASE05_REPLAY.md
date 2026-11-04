# Phase05：可重放交互与采集

已建立原生 Sequencer 轨迹，并完成两次实际运行和一次可复核的自动采集：直行、转弯、停留、返回、越界及停止均被记录。此轮完成的是重放基础与采样验证；预览采集约3Hz，不是可投递的流畅成片，也不是新版本性能验收。

## 运行入口

研究工程 `D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy/FluidNinjaLive.uproject`。

- `/Game/MudStudy/Professional/Phase05/L_Mud_Replay`
- `/Game/MudStudy/Professional/Phase05/LS_Mud_Replay`

打开关卡运行会自动播放60秒序列，在终点保持。Integrated_Brush 为碰撞开启的球体，缩放0.4、中心Z=20，底部接近地面；这是物体交互夹具，不是人物步行动画。

主泥浆 Actor 继续使用 Phase04 的材质。BrushActors 明确只绑定该球体，TrackPlayer=false，BrushPositionRandom=0，InputRandomSeed=12345。相位测试速度默认关闭，流动时钟使用实时钟。序列每次从同样的位置和时间开始，不循环；重新启动 PIE 才是清空模拟后重放。仅倒回时间轴不会清除已有泥浆历史。

轨迹单位为秒与厘米：0–3秒停留；3–9直行；9–15两段转弯；15–18停留；18–36返回；36–42停留；42–48移动到X=1150越过显示区域边界；48–52退回X=800；52–60停止。采用线性关键帧，转角速度不平滑，作为检查刺激而非人物表演。

## 实际结果

最终成功采集：`Verification/MudProfessional/phase05-replay/20261029T105850318316Z/`。

- 192个带时间的位置样本和192张画面，覆盖约63.73秒游戏时间。
- 原生物体位置与同一时刻的关键帧插值最大误差约2.27e-13cm；采样路径长度约4969.76cm，采样最大X约1144.11cm。关键帧本身的最大X为1150，采样不一定落在峰值时刻。
- 所有样本的点输入数量为1；直行、转弯、停留、返回、边界和终点均有记录。
- 11次GPU局部读回，每次状态和派生法线各256像素：全部有限，源B与法线A最大差为0，材质法线绑定正确；局部最大速度约0.15210。它证明轨迹产生了真实模拟运动，不能扩大为全纹理、全时刻或严格无边缘伪影检查。
- 验证入口和临时设置已恢复，退出PIE，脏包为零。原基线和前四阶段共123个文件哈希未变。新关卡、序列快照在本目录Assets，仍依赖研究工程已有资源。

第一轮自动采集 `20261029T105236643992Z` 也完成了路径和高度一致性记录，但读回区域过大：UE5.8的 ReadRenderTargetRawPixelArea 将名为MaxX/MaxY的参数直接传给以Width/Height命名的内部函数。本轮第二次运行显式传16/16，并检查实际像素数为256。第一轮保留作诊断记录，不套用第二轮的局部区域结论。

脚本启动阶段的接口适配失败会保留为失败目录或run.json错误；没有计入成功。Unreal未导出EditorPerformanceSettings的Python类/蛇形属性别名，现通过反射类与原始属性名读写；采集Actor在编辑关卡内由原生工具创建，PIE中使用克隆实例。

## 采集与视频

轨迹和自动播放由原生 UE MCP 创建；因运行插件缺少逐帧采集/replay工具，使用受限 UE Python `mud_replay_capture.py` 注册Slate回调作记录。脚本只在指定研究工程和Phase05地图执行，不写求解器或材质资产。

临时关闭的是研究进程内 EditorPerformanceSettings 的后台节流选项，并设置t.MaxFPS=60；没有SaveConfig，结束恢复原值。仍观测到约0.333秒的采集间隔，说明录制约3Hz的问题尚未解决，不能把60的设置值当作实测60FPS。引擎源码显示隐藏窗口还有独立节流路径；尝试打开研究材质编辑器也未改善采集频率，根因仍待进一步验证。

画面640×360、固定机位(0,1250,600)、Pitch=-28/Yaw=-90、FOV55，手动曝光、关闭物理相机曝光。采集包含SceneCapture和同步读回，影响运行成本。没有通过这次记录测无干扰性能。

原始PNG可显示，但部分文件IEND后带多余数据，使视频解码报错。复核脚本验证所有PNG块CRC，保留原始frames，在clean_frames生成仅截止IEND的副本；PNG像素数据不变。这些副本用于编码。原始导出有尾部数据的问题尚未在引擎侧修复。

`replay_preview_clean.mp4` 是本轮技术预览：按每帧实际游戏时间差编码VFR，没有补帧或加速伪装成高帧率。视频已全量解码检查通过；低帧率、低分辨率和目前的灯光/背景尚不满足正式投递成片要求。原始失败编码文件不属于交付入口。

## 复核

在目标关卡、退出PIE后，UE Python导入 `Tools/MudStudy/mud_replay_capture.py` 并调用start()。原生轨迹自动开始，脚本运行到64秒游戏时间后停止、恢复设置并退出PIE，输出唯一目录。若中断可调用stop()执行清理。测试脚本和流程不应直接搬到Stormfall/R02执行。

`python Tools/MudStudy/verify_replay_capture.py <采集目录>` 重算已有采集记录，验证位置、阶段覆盖、GPU采样及脚本哈希，生成validation.json、干净PNG副本和frames.ffconcat。它不会启动UE。可用ffmpeg的concat输入、VFR编码生成技术预览。

run.json、冻结harness.py、validation.json、原始与清理后帧分别保留输入、采集代码和检查证据。通过项passed只代表轨迹和采样一致性；smooth_preview_capture=false明确保留成片采集失败状态。

下一步优先解决研究编辑器隐藏/后台采集频率，或迁移到独立运行入口再录制；随后固定同一轨迹比较关闭/开启流动细节的代表场景GPU成本，并制作可读的连续镜头。完整人物交互成片与当前版本打包仍未验收。
