# 美术参数与可走入的深泥浆

研究工程：`D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy/FluidNinjaLive.uproject`。

打开 `/Game/MudStudy/Professional/Phase12/L_Mud_ArtistDeep`，选择 `Integrated_Mud_GlobalNormal`，在详情面板上方的组件列表点击 **ArtistControls**。参数有中文名称，展开 `Mud Artist` 下的 Color、Surface、Depth、Motion、Quality。普通 Play 后，WASD 移动、鼠标转向、空格跳跃；从出生点朝前沿坡道进入泥浆，也可沿原路退出。

默认是棕色、80cm 泥层深度、0.5 黏稠感、2048 显示分辨率。停止 Play 后改参数并保存可持久化；Play 内改动只影响本次运行。

## 美术怎么调

- **浅色 / 深色 / 亮度**：控制泥浆配色；不是灯光颜色。
- **粗糙度**：控制反光表现；数值越低通常越湿亮。
- **表面细节强度 / 密度**：控制细碎纹理和法线的强弱、疏密。
- **表面起伏深度 (cm)**：放大 POM 与计算法线的凹凸，范围 0–40cm。它不是角色浸入深度；薄泥层会自动限制实际起伏，避免露出底板。状态里的“实际起伏深度”显示生效值。
- **泥浆层深度 (cm)**：泥面到可走底板的距离，范围 2–120cm，滑条到 100cm。底板与东西两侧坡道联动，角色实际站到泥面以下。提供浅泥 5cm、没膝 50cm、漫腿 90cm 三个按钮；按钮也会配套调整表面起伏。
- **黏稠感（艺术控制）**：0–1，联动模拟输运、速度衰减、细节流动及可选行走阻力。0 对应 SimSpeed=10、VelocityFeedback=.94、泥中移动倍率 .85；1 对应 3、.82、.45。默认 .5 对应 6.5、.88、.65。出泥恢复原有移动速度，可关闭行走阻力。
- **细节流动倍率**：额外控制表面细节漂移，0 可停止细节漂移；不等于停止主模拟。
- **显示分辨率**：512 / 1024 / 2048，联动输出 RT 和计算法线 RT。20m 泥区对应约 3.91 / 1.95 / 0.98cm 的输出像素间距。运行中切档会重建并清空当前模拟痕迹。

大范围形态仍在旁边的 `MudControls` 中：RegionShape、RegionSizeCm、RegionOffsetCm、RegionRotationDegrees、CornerRoundness、Irregularity、ShapeSeed。它们裁切可见轮廓，不会重做凹槽和坡道；这个深泥测试场推荐保留 FullPlane。颜色、厚度、流动以 ArtistControls 为准，因为该组件会同步覆盖 MudControls 中对应的外观值。

## 实现链路与边界

新增组件 `UMudArtistControls`，源码镜像在 `Tools/MudStudy/Runtime/MudArtistControls.h/.cpp`；研究工程真实源码在 `Plugins/MudShaderLab/Source/MudShaderIntegration/Public` 和 `Private`。

1. 角色脚、膝、髋骨位置 → 求腿部线段与水平泥面的交点 → 写入两个稳定的 Niagara 世界坐标输入槽；出界时尺寸归零。
2. 原有 Niagara 模拟继续计算速度/密度，艺术参数写入 User.SimSpeed 与 User.VelocityFeedback。
3. 输出 RT → 原有计算法线 → 原有可调泥浆材质；颜色、细节及 POM 起伏同步。
4. 层深同步改变底板、坡道；泥面取消阻挡，CharacterMovement 沿实际碰撞底面行走。泥中阻力与可见区域、脚底高度联动。

深泥来自“较低的可走底面 + 泥面遮挡 + 腿部交互”，仍然是水平二维场的场景实现，不是三维体积流体、浮力、泥浆包裹身体或以 Pa·s 标定的物理黏度。只支持本测试场的水平、轴对齐 2000×2000cm 泥区；任意地形与旋转缩放不是本版验收范围。Setup 的三个对象已接好，不能随意删除。

显示档位不改变内部主要模拟网格；当前主网格仍为 2048，Painter 1024、SDF 512。分辨率提高不等于获得物理黏度或体积厚度，也不能从旧版 GPU 耗时推算本版整帧性能。

## 本轮验证

模块单独编译成功。普通 Play 使用真实 IA_Walk 与角色动画，从平台走入 80cm 泥层，再沿坡道退出：入泥速度 260cm/s，出泥恢复 400cm/s，记录中未出现跌落。角色胶囊中心从约 Z=93.25cm 到 Z=12.15cm，底板顶面为 Z=-80cm；两条腿继续送入泥面交点。

已验证 5/50/90cm 预设、颜色材质读回及截图；512/1024/2048 三档的输出尺寸、法线尺寸、材质纹理绑定均正确。黏稠感两端的 Niagara 参数实际读回有效。静止腿附近 96×64 输出区域出现密度扰动（B 最低约 .966）；该读回不是移动速度测试。地图保存重载后配置有效。

证据位于 `Verification/MudProfessional/phase12-artist/`：`evidence.json`、`walk-in.json`、`walk-out.json`、`walk-in-again.json`、`deep80.png`、`leg90.png`、`knee50.png`、`color-green.png`。`mud_artist_test.py` 是临时逐帧 Enhanced Input 测试辅助，不参与运行时工程。

本轮没有重新验收打包版、整帧性能、动态脚部 IK、飞溅或原版完整动态等价。
