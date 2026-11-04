# 原版完整链路的深泥对比场

研究工程：`D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy/FluidNinjaLive.uproject`。

地图：`/Game/MudStudy/Professional/Phase13/L_Mud_OriginalDeep`。普通 Play 后用 WASD、鼠标、空格游玩；沿出生点前方坡道进入中央泥池，池底在泥面以下 80cm。当前留在普通 Play，角色已进入泥池。

通过原生 EditorActorSubsystem.DuplicateActor，复制原地图 Viscous_Blood_Mud 中已配置好的 NinjaLive_Mud1 实例，移到平台中央并水平放正。使用原版 NinjaLive 蓝图、NinjaLiveComponent、NinjaLiveCore Niagara 和 MI_Mud1_WorldSpace 材质，保持 SimSpeed=8、VelocityFeedback=.9、DensityAccumulation=1.217、GlobalBrushScale=1.4、2048×2048 输出。Phase13 已删除自研 MudShaderPreviewActor；原版资产本身未编辑。

沿用 Phase12 的平台、灯光、80cm 槽底与坡道。专用 BP_Mud_Original_Manny 和 BP_Mud_Original_GameMode 复制自 Phase11，角色网格开启 Generate Overlap Events，让原版重叠采集能取得骨骼位置。角色网格、动画和相机沿用现有设置；这里行走速度保持400cm/s，自研 Phase12 泥中默认260cm/s，不能当作同速度、同状态的单项算法对照。

普通 Play 重新启动后，确认使用专用角色；沿真实 IA_Walk 从平台走到池底，角色胶囊中心约 Z=12.15cm，底面 Z=-80cm。继续运行时原版收到17个骨骼位置，包括泥面以下约30cm的膝部及约80cm的足部。暂停时原版会清空临时输入数组，恢复运行后重新填入，检查输入以 evidence.json 的 unpausedInteraction 为准。

最终截图：`Verification/MudProfessional/phase13-original-deep/original-deep-verified.png`；走入记录：`original-walk-verified.json`；参数和输入读回：`evidence.json`。`original-deep-walk.png` 和 `original-walk-in.json` 是开启网格重叠前的初查记录，不作为最终交互验收。测试使用临时 Python 逐帧 Enhanced Input 注入，场景与配置通过原生编辑接口完成。

原版可见起伏、湿亮细节和不规则泥面比上一轮自研静态截图明显。这是完整原版在深槽中的体验对照，未隔离模拟器、输入、材质各自贡献，也没有重测性能。80cm 深度仍由较低碰撞底面配合泥面遮挡实现，未新增三维体积流体。

自研场景保留在 `/Game/MudStudy/Professional/Phase12/L_Mud_ArtistDeep`，可分别打开查看。
