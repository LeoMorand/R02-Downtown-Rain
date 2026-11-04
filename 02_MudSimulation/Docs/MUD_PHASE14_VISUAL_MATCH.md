# 自研深泥的起伏恢复与外观校准

研究工程：`D:/codex/2026-10-18/new-chat/outputs/FluidNinjaStudy/FluidNinjaLive.uproject`。

最新自研地图：`/Game/MudStudy/Professional/Phase14/L_Mud_VisualMatch`。当前已打开并运行，角色站在80cm深泥中，点击视口后用WASD、鼠标、空格体验。停止Play后选 `Integrated_Mud_GlobalNormal` 的 `ArtistControls` 调颜色、黏稠感、泥层深度和分辨率。默认2048显示分辨率、黏稠感.5、亮度.25。

## 已定位的原因

Phase12的“黏稠感”把默认 User.VelocityFeedback 改为.88。自研原有输运代码是 `transported.xyz * Feedback`，这同时衰减速度XY和密度Z。配合密度累积1.217，内部无边界近似下每步保留从原版 `.9 * (.5 + .5 * 1.217) = .99765` 降为 `.88 * (.5 + .5 * 1.217) = .97548`。这是重复施加的反馈，不能理解为视觉上只少2%。

检查同一中心64×64区域：旧默认B范围约.9683–.9956；只将反馈恢复到.9、其余沿用测试配置，B范围变为约.7617–.9683，并出现明显成片褶皱。采样来自不同时刻，非冻结状态逐像素误差对照；它结合代码与实图支持反馈联动是主要原因之一。

## 实际改动

新建独立资产 NS_Mud_VisualMatch 与 NM_Advection_SeparatedDensity。输运改成：

```hlsl
Value = float4(transported.xy * Feedback,
               transported.z * DensityFeedback,
               transported.w);
```

User.DensityFeedback 独立设为.9。原 ArtistControls 继续以黏稠感调速度反馈.94–.82和模拟速度，密度保留不再跟着变。源码镜像为 `Tools/MudStudy/Reference/AdvectionSeparatedDensity.hlsl`，完整图编辑规格与GPU读回在本轮 evidence.json。

新增 Flow/Static 两个材质实例，仍使用自研HLSL父材质、POM、流动细节和计算法线；没有把原版材质或原版Niagara藏在自研入口里。校准参数：亮度.7→.25、颜色对比ColorPow 1→10、TileMapRoughness .035→.1、Specular .3→.2。亮度由ArtistControls控制，ColorPow在新材质实例中。

比较场的可选行走阻力默认关闭，以400cm/s接近Phase13原版对比角色；需要泥中减速时可重新打开。80cm底面与出入坡道继续沿用，颜色、表面起伏和三档显示分辨率入口保留。

## 验证与边界

- 新Niagara系统5个脚本编译通过，失败0。GPU脚本状态为NCS_ComputeUpToDateWithWarnings，工具没有返回错误或警告事件文本；不将其描述为无警告编译。
- 实际GPU输入包含独立DensityFeedback=.9，速度反馈仍由黏稠感控制。
- 黏稠感0/1下，GPU速度反馈分别.94/.82，密度反馈均.9；远离角色的同一64×64区域，B最小/最大值两次均为.635742/.982422，未出现旧版的密度塌平或饱和现象。这是两次局部读回，不是整场长期稳定性验收。
- 普通Play真实IA_Walk走入80cm泥层，胶囊中心约Z=12.15，走动样本无跌落；两个腿部交点输入有效。
- 2048输出、2048计算法线与材质绑定正确，UseComputedNormal仍为True。

证据：`Verification/MudProfessional/phase14-visual-match/`。最终图 `self-fixed-walk.png`；`material-only.png` 是旧反馈下只改外观的诊断；`feedback-only.png` 是旧系统恢复.9的诊断；`walk-visual-match.json` 为输入测试记录。临时 `mud_visual_test.py` 只用于逐帧输入和截图前暂停，不参与工程运行。

这版已经恢复明显的成片起伏、湿亮细节，并保留自研链路。原版Phase13与本版的最终角色姿态、位置、模拟年龄及输入采样仍不同，尚未证明完整动态等价，也没有重测性能或打包版。下一步若继续收敛，应对相同运动轨迹检查局部推挤、拖尾和恢复时间，不能直接把截图差异全部归到某一算法。
