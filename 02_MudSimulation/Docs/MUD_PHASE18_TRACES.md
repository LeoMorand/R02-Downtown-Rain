# Phase18：更明显的行走痕迹

地图：`/Game/MudStudy/Professional/Phase18/L_Mud_VisibleTrails`，当前研究编辑器已打开并退出测试，直接普通Play。

本轮开始时 Phase15 有用户未保存的修改，包括池深50cm、起伏12cm、黏稠感0.998539。先将完整当前场景另存为Phase18，随后保存原Phase15以保留这些用户修改，再正常加载新场景。没有丢弃用户修改，也没有回滚至旧默认。其他新增材质、Niagara及模块均在Phase18独立目录中。

## 调整入口

选择 `Mud_ThinSurface` 或 `Mud_DeepPool` 的 `Simulation` 组件，在用户参数中搜索：

- `TrailStrength`：默认0.65。控制痕迹对显示高度的影响，并同时缩放颜色遮罩。0关闭加强效果，1更强。
- `TrailHalfLifeSeconds`：默认8。痕迹保留的半衰期目标，越大留得越久。实际GPU半精度存储会影响衰减曲线，不是精确秒表。
- `TrailImprintGain`：默认1.35。脚步写入遮罩的强度，过大容易形成饱和印记。

`MI_Surface_Trace_Flow` / `MI_Surface_Trace_Static` 的 `TrailColorContrast` 默认0.85；仅控制印记变暗程度，不改变角色移动、泥浆求解或池深。原来的 ArtistControls / MudControls 继续调颜色、深度、起伏和轮廓。

## 实现

原泥面的输运和褶皱与脚步形变混在一起，单独放大整体起伏也会放大背景。本版在Painter已有且未被当前后续物理解算消费的W通道中保留局部交互遮罩。遮罩来自移动笔刷的核，并筛选靠近泥面的接触输入。薄层脚踝/脚骨原点高于鞋底，因此接触权重在20cm内保持完整，20–40cm逐渐淡出；跳离交互范围的输入不会持续写入。深池沿用既有两个腿部泥面交点。

历史遮罩按 `exp2(-dt / halfLife)` 衰减，并与本次落脚遮罩取最大值，不随流体速度搬运。Painter XYZ、Composite、密度反馈、速度反馈与压力解算保持原链路。此处使用已有网格通道，不增加独立RenderTarget或模拟阶段。

新的导出协议为 RG=原速度、B=加入局部印记的显示高度、A=颜色印记遮罩。只影响表面重建，未把显示凹陷写回物理密度。计算法线继续由B生成。两套独立新材质在同一POM UV上采样A，将原BaseColor乘以印记变暗系数；原有颜色、流动、法线、粗糙度和轮廓连接保留。旧版资产和协议不做迁移。

源码镜像：`Reference/PainterTraceHistory.hlsl`、`Reference/ExportTraceRelief.hlsl`、`Reference/TraceColorContrast.hlsl`。图编辑记录与编译报告位于 `Verification/MudProfessional/phase18-visible-trails/`。

## 已验证

- 新系统5个脚本编译成功、失败0；GPU状态为 `NCS_ComputeUpToDateWithWarnings`，工具未提供具体警告事件文本，不能称为无警告编译。
- 薄层和用户当前50cm池子均完成真实Enhanced Input步行，池内角色中心Z约42.2cm。运行时材质均来自Phase18新实例。
- 两块各自2048输出和法线绑定正确；两处64×64读回中，计算法线A与来源高度B的最大误差为0。
- 两块远离行走路径的64×64区域，印记A最大值为0；局部痕迹有限且有非零覆盖。不会因本功能把全场统一染黑。
- 薄层最新落脚后的局部遮罩峰值约0.613，池子约0.575。角色离开后，薄层8.067秒的GPU遮罩总量降至约43.4%，证实能保留并逐渐消退。
- 同一暂停状态下切换 `TrailColorContrast=0/0.85` 的截图用于检查局部颜色路径。早期 `thin-trace-on/off.png` 为仅高度的诊断，两个参数状态之间有一个额外Niagara步，不是同状态严格算法对照。`thin-final-on.png` 与 `thin-final-color-off.png` 才是新增颜色对比检查；不应将它们描述为整套旧版/新版全部差异。

检查脚本仅在PIE测试期间运行，不参与正常工程运行。结束后已停止测试，地图和资产已保存、脏包为0。此前Phase17视频不会自动包含本轮新功能；本版没有重新录制视频，也未重测整体性能或Shipping。
